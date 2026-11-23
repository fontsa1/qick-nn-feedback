#!/usr/bin/env bash
# R2 build 2 (LDA_live through the same gate): one board session. NOT RUN YET.
# Uses the board only with R2_BOARD_APPROVED=1:   R2_BOARD_APPROVED=1 R2_B2_BANNER='...' bash run_board_b2.sh A|B [phases]
# phases (default "core live1 latency"): any of
#   core     deploy check, functional, safety (binding fault, fail-safe, tProc decision, leak energy), gate slack sweep,
#            20-shot in-loop smoke
#   live1    gate-idle classification of this board's half of the headline mosaic (A rows 0-49,999, B 50,000-99,999),
#            1000-shot chunks, as run_6_3.sh live 1  -> with both boards: the 99,400-row headline set
#   live2    the other half (each board's full split = live1 + live2)
#   latency  box_probe + latency_protocol (gate loop, L_50) with the LDA's 8-cycle result, --sensitivity
#   inloop   in-loop campaign over 100,000 rows (pulse == gate == decision, every shot)
#   restore  redeploy v1.44 (qick67) and recalibrate  (always run last; the default list ends with it)
set -u
[ "${R2_BOARD_APPROVED:-0}" = 1 ] || { echo "board time not approved (set R2_BOARD_APPROVED=1 to use the board)"; exit 2; }
cd "${QICK_REPO:?set QICK_REPO to the repository root}"
B=$1; PH=${2:-"core live1 latency restore"}
case $B in A) H="${QICK_BOARD_A:?set QICK_BOARD_A}"; R1=0; R2=50000;; B) H="${QICK_BOARD_B:?set QICK_BOARD_B}"; R1=50000; R2=0;; *) echo "board A or B"; exit 2;; esac
PY="${PYTHON:-python}"; DG=analysis_scripts/diagnostics; R=firmware_v1.44/variants/build2_lda_gate; O=$R/board
DEP=${QICK_WORK:?set QICK_WORK}/deploy
BIT=${R2_B2_BIT:-$DEP/OG_build_v1.44lda.bit}; HWH=${R2_B2_HWH:-$DEP/OG_build_v1.44lda.hwh}   # build 2b: set both to the OG_build_v1.44lda11 files
BANNER="${R2_B2_BANNER:?set R2_B2_BANNER to the TIMESTAMP in build2 REPORT.md}"
V44="${QICK_BANNER:-Nov  7 19:57:07}"; TOP="${QICK_TOP:-firmware_v1.44}"; ADV=0.1135; SILENCE=900
mkdir -p $O $O/live $O/inloop; LOG=$O/runner_$B.log
export QICK_NS_HOST=$H QICK_LIVE_N=576 QICK_BANNER="$BANNER"
say() { echo "$(date '+%F %T') $*" | tee -a $LOG; }
watch() { # silence watchdog, as run_6_3.sh
  local log=$1 pid winpid age; shift
  "$@" >> "$log" 2>&1 < /dev/null & pid=$!; winpid=$(cat /proc/$pid/winpid 2>/dev/null || echo ""); touch "$log"
  while kill -0 $pid 2>/dev/null; do sleep 20; age=$(( $(date +%s) - $(stat -c %Y "$log") ))
    if [ $age -gt $SILENCE ]; then say "WATCHDOG: $log silent ${age}s, killing pid $pid"; [ -n "$winpid" ] && taskkill //PID "$winpid" //T //F >> $LOG 2>&1; kill -9 $pid 2>/dev/null; break; fi
  done; wait $pid; }
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
  rmdir campaign_v144/final/calib/.lock; say "calibration $1 rc=$rc $(grep -E '\|k\|' $O/${B}_calib_$1.log | tail -1 | cut -c1-100)"; return $rc; }
step() { local n=$1 to=$2; shift 2; timeout $to "$@" > $O/${B}_$n.log 2>&1 < /dev/null; say "$n rc=$?"; }
live() { # live <run> <first row>
  local run=$1 first=$2 s e out lg
  calibrate live$run || return 1
  for ((s = first; s < first + 50000; s += 1000)); do
    e=$((s + 1000)); out=$O/live/${B}_run${run}_${s}_${e}.npz; lg=$O/${B}_live_run${run}.log
    [ -f "$out" ] && continue
    for t in 1 2 3; do
      watch "$lg" $PY -u $DG/box_live_capture.py --x test100k_real_X.npy --y test100k_real_y.npy \
        --scale-ref test20k_real_X.npy --clip-dac --start $s --shots 1000 --out "$out"
      [ -f "$out" ] && break; say "live run$run chunk $s try $t failed"; sleep 30
    done
    [ -f "$out" ] || say "live run$run chunk $s MISSING"
  done
  say "live run$run done"
}

say "START build2 on $B ($H), phases: $PH, bit sha256 $(sha256sum $BIT | cut -c1-16)"
deploy $BIT $HWH qick69 "$BANNER" b2 || { say "BANNER FAILED"; exit 3; }
say "banner confirmed: $BANNER"
for p in $PH; do case $p in
  core)
    step functional 1800 $PY $DG/qick_functional_test.py --out $O/${B}_functional.json
    calibrate core
    step binding_fault 2400 $PY $DG/binding_fault_check.py --cycles 25 --control 40 --out $O/${B}_binding_fault.json
    step fail_safe 1800 $PY $DG/fail_safe_check.py --nn-advance $ADV --out $O/${B}_fail_safe.json
    step tproc_decision 2400 $PY $DG/tproc_decision_check.py --shots 400 --out $O/${B}_tproc_decision.json
    for t in 2000 8; do step leak_thr$t 3000 $PY $DG/leak_energy_check.py --shots 40 --nz-thr $t --out $O/${B}_leak_thr$t.json; done
    step gate_sweep 3000 $PY $DG/gate_probe.py --split --nn-advance $ADV --pre 0.15 \
         --slacks=-0.078,-0.076,-0.074,-0.072,-0.070,-0.068,-0.066,-0.064,-0.062,-0.060,-0.040,0.0 --out $O/${B}_gate_probe_box.npz
    rm -f $O/inloop/${B}_SMOKE.npz $O/inloop/${B}_SMOKE.log
    watch $O/inloop/${B}_SMOKE.log $PY -u audit_fixes/R18/inloop_campaign.py --start 20000 --shots 20 --out $O/inloop/${B}_SMOKE.npz
    grep -q "(correct): 20/20" $O/inloop/${B}_SMOKE.log && say "smoke OK: $(grep '^pulse == gate' $O/inloop/${B}_SMOKE.log | cut -c1-150)" \
      || { say "SMOKE FAILED: $(tail -2 $O/inloop/${B}_SMOKE.log | cut -c1-200)"; exit 3; } ;;
  live1) live 1 $R1 ;;
  live2) live 2 $R2 ;;
  latency)
    calibrate latency
    step box_probe 600 $PY $DG/box_probe.py --out $O/${B}_b2.box_probe.json
    QICK_RES_MINUS_LAST=${R2_RES_MINUS_LAST:-8} step latency 1500 $PY $R/latency_protocol_lda.py --expect-path-adv 1.4 --label b2 \
         --box-json $O/${B}_b2.box_probe.json --expect-banner "$BANNER" --bit $BIT --sens-shots 40 --sensitivity --out $O/${B}_b2_latency.npz
    say "gate loop: $(grep -E '^ +op:' $O/${B}_latency.log)"; grep -E '^  FAIL' $O/${B}_latency.log | tee -a $LOG ;;
  inloop)
    calibrate inloop
    OUT=$O/inloop/${B}_inloop_0_100000.npz; IL=$O/inloop/${B}_inloop_0_100000.log
    for t in 1 2 3 4 5 6; do grep -q "^pulse == gate == NN_live decision" "$IL" 2>/dev/null && break
      res=""; [ -f "$OUT" ] && res="--resume"
      watch "$IL" $PY -u audit_fixes/R18/inloop_campaign.py --start 0 --shots 100000 --out "$OUT" $res; done
    say "in-loop: $(grep '^pulse == gate' "$IL" | tail -1 | cut -c1-170)" ;;
  restore)
    deploy $TOP/OG_build_v1.44.bit $TOP/OG_build_v1.44.hwh qick67 "$V44" restore || { say "RESTORE OF v1.44 FAILED: fix by hand"; exit 4; }
    calibrate restore_v144 ;;
esac; done
$PY $R/check_board_lda.py $O/live > $O/${B}_check_board_lda.log 2>&1; say "check: $(tail -3 $O/${B}_check_board_lda.log | tr '\n' ' ')"
say "DONE build2 on $B"
