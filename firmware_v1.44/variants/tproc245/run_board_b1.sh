#!/usr/bin/env bash
# R2 build 1 (tProc core at QICK's stock 245.76 MHz): one board session. NOT RUN YET.
# Uses the board only with BOARD_APPROVED=1:   BOARD_APPROVED=1 bash run_board_b1.sh A|B
# One board per process; A and B may run in parallel (calibration is serialised by the lock, as run_6_3.sh does).
# Steps (BOARD_PLAN.md): deploy qick68 + banner, functional (core 245.76), calibrate, tproc_decision, box_probe +
# latency_protocol (gate loop must be unchanged), tProc path on boxcar and FIR (wider margin sweep), QICK threshold
# feedback (read_and_jump), then restore v1.44 (qick67) and recalibrate.
set -u
[ "${BOARD_APPROVED:-0}" = 1 ] || { echo "board time not approved (set BOARD_APPROVED=1 to use the board)"; exit 2; }
cd "${QICK_REPO:?set QICK_REPO to the repository root}"
B=$1
case $B in A) H="${QICK_BOARD_A:?set QICK_BOARD_A}";; B) H="${QICK_BOARD_B:?set QICK_BOARD_B}";; *) echo "board A or B"; exit 2;; esac
PY="${PYTHON:-python}"; DG=analysis_scripts/diagnostics; R=firmware_v1.44/variants/tproc245; O=$R/board
DEP=${QICK_WORK:?set QICK_WORK}/deploy
BIT=$DEP/OG_build_v1.44t245.bit; HWH=$DEP/OG_build_v1.44t245.hwh
BANNER="${B1_BANNER:?set B1_BANNER to the TIMESTAMP in build1 REPORT.md (date part, e.g. 'Nov 16 00:3x:xx')}"
V44="${QICK_BANNER:-Nov  7 19:57:07}"; TOP="${QICK_TOP:-firmware_v1.44}"
mkdir -p $O; LOG=$O/runner_$B.log
export QICK_NS_HOST=$H QICK_LIVE_N=576 QICK_BANNER="$BANNER"
say() { echo "$(date '+%F %T') $*" | tee -a $LOG; }
deploy() { # deploy <bit> <hwh> <stem> <banner> <tag>
  timeout 900 $PY board_tools/deploy_and_verify.py --deploy $1 $2 $3 --expect-banner-contains "$4" > $O/${B}_$5.deploy.log 2>&1 < /dev/null
  if ! grep -q 'verification PASSED' $O/${B}_$5.deploy.log; then   # board B: the server kernel has no notebook session
    timeout 900 $PY board_tools/start_server.py $H --restart > $O/${B}_$5.restart.log 2>&1 < /dev/null
    timeout 300 $PY board_tools/deploy_and_verify.py --expect-banner-contains "$4" > $O/${B}_$5.verify.log 2>&1 < /dev/null
    grep -q 'verification PASSED' $O/${B}_$5.verify.log || return 1
  fi
}
calibrate() { until mkdir campaign_v144/final/calib/.lock 2>/dev/null; do sleep 10; done
  timeout 1200 $PY run_calibration.py > $O/${B}_calib_$1.log 2>&1 < /dev/null; local rc=$?
  rmdir campaign_v144/final/calib/.lock; say "calibration $1 rc=$rc $(grep -E '\|k\|' $O/${B}_calib_$1.log | tail -1 | cut -c1-100)"; }
step() { local n=$1 to=$2; shift 2; timeout $to "$@" > $O/${B}_$n.log 2>&1 < /dev/null; say "$n rc=$?"; }

say "START build1 on $B ($H), bit sha256 $(sha256sum $BIT | cut -c1-16)"
deploy $BIT $HWH qick68 "$BANNER" b1 || { say "BANNER FAILED"; exit 3; }
say "banner confirmed: $BANNER"
QICK_EXPECT_FCORE=245.76 step functional 1800 $PY $R/qick_functional_test_fcore.py --out $O/${B}_functional.json
calibrate b1
step tproc_decision 2400 $PY $DG/tproc_decision_check.py --shots 400 --out $O/${B}_tproc_decision.json
step box_probe 600 $PY $DG/box_probe.py --out $O/${B}_b1.box_probe.json
step latency 1500 $PY $DG/latency_protocol.py --expect-path-adv 1.4 --label b1 --box-json $O/${B}_b1.box_probe.json \
     --expect-banner "$BANNER" --bit $BIT --sens-shots 40 --out $O/${B}_b1_latency.npz
say "gate loop: $(grep -E '^ +op:' $O/${B}_latency.log)"; grep -E '^  FAIL' $O/${B}_latency.log | tee -a $LOG
step tproc_box 3600 $PY -u $DG/tproc_path_v143.py --path box --variants nobranch,qick \
     --margins 0.0,0.005,0.01,0.015,0.02,0.025,0.03,0.035,0.04,0.045,0.05,0.055,0.06 --shots 100 --n-force 25 --out $O/${B}_tproc_box_t245.json
say "tproc box: $(grep 'earliest' $O/${B}_tproc_box.log | tr '\n' ';')"
step tproc_fir 3600 $PY -u $DG/tproc_path_v143.py --path fir --variants nobranch \
     --margins 0.0,0.005,0.01,0.015,0.02,0.025,0.03,0.035,0.04,0.045,0.05 --shots 40 --n-force 20 --out $O/${B}_tproc_fir_t245.json
say "tproc fir: $(grep 'earliest' $O/${B}_tproc_fir.log | tr '\n' ';')"
step threshold 3600 $PY -u campaign_v144/final/board3/threshold/threshold_baseline.py \
     --nn-margins 0.0,0.01,0.02,0.03,0.04,0.05,0.06,0.07,0.08 --out $O/${B}_threshold_t245.json
say "threshold: $(grep -iE 'earliest' $O/${B}_threshold.log | tr '\n' ';' | cut -c1-300)"
# ---- leave the board on v1.44
deploy $TOP/OG_build_v1.44.bit $TOP/OG_build_v1.44.hwh qick67 "$V44" restore || say "RESTORE OF v1.44 FAILED: fix by hand"
calibrate restore_v144
say "DONE build1 on $B"
