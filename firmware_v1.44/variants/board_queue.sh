#!/usr/bin/env bash
# Board session for the variant builds on one board, strictly sequential:
#   1. build 1 (tProc at 245.76 MHz): run_board_b1.sh, which ends back on v1.44 and recalibrated
#   2. pulse-gain arms on the full split (v1.44): nominal (gain 0.6) vs zero (gain 0), all 100,000 rows, resumable
#   3. build 2b (LDA_live 1.1) once its bitstream exists: run_board_b2.sh core live1 latency restore
#   R2_BOARD_APPROVED=1 bash firmware_v1.44/variants/board_queue.sh A|B [steps]   (steps default "b1 arms lda")
set -u
[ "${R2_BOARD_APPROVED:-0}" = 1 ] || { echo "board time not approved"; exit 2; }
cd "${QICK_REPO:?set QICK_REPO to the repository root}"
B=$1; ST=${2:-"b1 arms lda"}
case $B in A) H="${QICK_BOARD_A:?set QICK_BOARD_A}";; B) H="${QICK_BOARD_B:?set QICK_BOARD_B}";; *) echo "board A or B"; exit 2;; esac
PY="${PYTHON:-python}"; R=firmware_v1.44/variants; DEP=${QICK_WORK:?set QICK_WORK}/deploy
AR=campaign_v144/final/inloop/arms; mkdir -p $DEP $AR
LOG=$R/board_queue_$B.log; V44="Nov  7 19:57:07"
say() { echo "$(date '+%F %T') $*" | tee -a $LOG; }
banner_of() { grep -o 'TIMESTAMP="[^"]*"' "$1" | head -1 | sed -E 's/TIMESTAMP="[A-Za-z]+ ([A-Za-z]+ +[0-9]+ [0-9:]+) [0-9]+"/\1/'; }
export R2_BOARD_APPROVED=1

for s in $ST; do case $s in
b1)
  for f in bit hwh; do [ -f $DEP/OG_build_v1.44t245.$f ] || cp ${QICK_WORK:?set QICK_WORK}/b1/OG_build_v1.44t245.$f $DEP/; done
  [ "$(sha256sum $DEP/OG_build_v1.44t245.bit | cut -c1-16)" = 0b5c89e82cc09944 ] || { say "b1 bit sha mismatch"; exit 3; }
  say "b1 START"; R2_B1_BANNER='Nov 16 00:41:12' bash $R/build1_tproc245/run_board_b1.sh $B; say "b1 END rc=$?" ;;
arms)
  export QICK_NS_HOST=$H QICK_LIVE_N=576 QICK_BANNER="$V44"
  timeout 300 $PY board_tools/deploy_and_verify.py --expect-banner-contains "$V44" > $AR/${B}_banner.log 2>&1 < /dev/null
  grep -q 'verification PASSED' $AR/${B}_banner.log || { say "arms: v1.44 banner not confirmed"; continue; }
  say "arms START (nominal, zero; rows 0-99,999)"
  timeout 64800 $PY -u campaign_v144/final/inloop/arms/inloop_arms.py --start 0 --shots 100000 --block 250 --arms nominal,zero \
      --out $AR/${B}_arms_full.npz >> $AR/${B}_arms_full.log 2>&1 < /dev/null
  say "arms END rc=$? :: $(tail -n 1 $AR/${B}_arms_full.log)" ;;
lda)
  BB=${QICK_WORK:?set QICK_WORK}/b2b
  for i in $(seq 1 144); do [ -f $BB/OG_build_v1.44lda11.bit ] && [ -f $BB/OG_build_v1.44lda11.hwh ] && break; sleep 300; done
  [ -f $BB/OG_build_v1.44lda11.bit ] || { say "lda: no build 2b bitstream after 12 h"; continue; }
  cp $BB/OG_build_v1.44lda11.bit $BB/OG_build_v1.44lda11.hwh $DEP/
  BN=$(banner_of $DEP/OG_build_v1.44lda11.hwh); say "lda START, 2b bit $(sha256sum $DEP/OG_build_v1.44lda11.bit | cut -c1-16), banner '$BN'"
  R2_B2_BIT=$DEP/OG_build_v1.44lda11.bit R2_B2_HWH=$DEP/OG_build_v1.44lda11.hwh R2_B2_BANNER="$BN" R2_RES_MINUS_LAST=9 \
      bash $R/build2_lda_gate/run_board_b2.sh $B "core live1 latency restore"
  say "lda END rc=$?" ;;
esac; done
say "QUEUE DONE on $B"
