#!/usr/bin/env bash
# Load-to-load latency study: 100 + 40 shots per bitstream load, plus a sensitivity run on each board's first load.
# Boards alternate so load order is not tied to time.  usage: run_loads.sh <outdir> <label> [<label> ...]
cd "${REPO_ROOT:-$(dirname "$0")/..}"
source campaign_v144/env.sh
D=analysis_scripts/diagnostics; V43="$BANNER"
O=$1; shift; mkdir -p $O
export QICK_LIVE_N=576
one() { # one <board> <host> <label> [--sensitivity]
  n=$1; export QICK_NS_HOST=$2; r=$O/${1}_$3; s=$4
  echo "START $n $3 $(date +%T)"
  timeout 900 $PY board_tools/deploy_and_verify.py --deploy $TOP/OG_build_v1.44.bit $TOP/OG_build_v1.44.hwh qick67 --expect-banner-contains "$V43" > $r.deploy.log 2>&1 < /dev/null
  if ! grep -q 'verification PASSED' $r.deploy.log; then
    timeout 900 $PY board_tools/start_server.py $2 --restart > $r.restart.log 2>&1 < /dev/null
    timeout 300 $PY board_tools/deploy_and_verify.py --expect-banner-contains "$V43" > $r.verify.log 2>&1 < /dev/null
    grep -q 'verification PASSED' $r.verify.log || { echo "BANNER_FAILED $n $3"; return 1; }
  fi
  timeout 900 $PY tools/run_calibration.py > $r.calib.log 2>&1 < /dev/null; echo "  calib rc=$?"
  timeout 600 $PY $D/box_probe.py --out $r.box_probe.json > $r.box_probe.log 2>&1 < /dev/null; echo "  box rc=$?"
  timeout 1500 $PY $D/latency_protocol.py --expect-path-adv 1.4 --label $3 --box-json $r.box_probe.json --expect-banner "$V43" --bit $TOP/OG_build_v1.44.bit --sens-shots 40 $s --out $r.npz > $r.log 2>&1 < /dev/null
  echo "  protocol rc=$?  $(grep -E '^ +op:' $r.log)"
  grep -E '^  FAIL' $r.log
  echo "DONE $n $3 $(date +%T)"
}
first=--sensitivity
for l in "$@"; do
  one A "$(host_of A)" $l $first
  one B "$(host_of B)" $l $first
  first=
done
$PY $D/latency_protocol_summary.py $O --md $O/summary.md
echo LOADS_DONE
