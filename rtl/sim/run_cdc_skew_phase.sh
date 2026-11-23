#!/bin/sh
# Phase sweep: tb_cdc_skew_phase.sv = tb_cdc_skew.sv with the destination clock start offset as parameter OFF_PS.
# Full xvlog/xelab/xsim logs per case in logs/. Run from this folder:  sh run_cdc_skew.sh
V=/c/embedded-software/Vivado/2023.1/bin
mkdir -p logs
W() { cmd.exe //c "$(cygpath -w $V/$1.bat)" "${@:2}"; }
W xvlog --sv tb_cdc_skew_phase.sv live_res_cdc_skew.v > logs/xvlog_phase.log 2>&1 || { echo XVLOG FAIL; exit 1; }
run() { # name M_PS SKEW_PS TOG_PS N OFF_PS
  n=$1
  # generics go through an options file: cmd.exe splits command-line arguments at '='
  printf -- '-debug off -timescale 1ps/1ps --mt 2 -generic_top M_PS=%s -generic_top SKEW_PS=%s -generic_top TOG_PS=%s -generic_top N=%s -generic_top OFF_PS=%s tb_cdc_skew_phase -s sim_%s
' $2 $3 $4 $5 $6 $n > logs/${n}_xelab.opt
  W xelab -f logs/${n}_xelab.opt > logs/${n}_xelab.log 2>&1 || { echo "$n XELAB FAIL"; return; }
  W xsim sim_$n -R > logs/${n}_xsim.log 2>&1
  echo "$n: $(grep 'OFF_PS' logs/${n}_xsim.log | grep -v '^#' | tail -1)"
}
CASES=${CASES:-"dac2_default:2034:0:0:3000 dac2_skew4000:2034:4000:0:3000 dac2_skew4500:2034:4500:0:3000"}
for c in $CASES; do IFS=: read n m s t k o <<EOF2
$c
EOF2
  run $n $m $s $t $k $o; done
