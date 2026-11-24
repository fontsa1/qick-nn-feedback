#!/bin/bash
# RTL sim of live_window_gate + an HLS NN_live with gaps in the input stream (tb_live_gap.sv). Usage, from rtl_sim/:
#   ./run_tb_gap.sh <HLS project dir> <VGAP> [rand]     e.g. ../../neural_net4_live576s 2
# VGAP 1 is the continuous stream of run_tb.sh; VGAP 2 and 3 give one valid sample in 2 or 3 cycles; "rand" gives a
# random half of the cycles. Logs: xsim_gap_<tag>.txt, where <tag> is the project name and the gap setting.
set -e
HLSV=$1/NN_live_prj/solution1/syn/verilog
G=$2; R=${3:-}
TAG=$(basename $1)_g$G${R:+_$R}
V="${VIVADO_BIN:?set VIVADO_BIN to the bin folder of Vivado 2023.1}"
QBUF=../../sim/buffer.sv
# the defines go in a header compiled first, so no argument carries an "=" (cmd.exe splits arguments there)
printf '`define VGAP %s\n' $G > gap_defs_$TAG.vh; [ "$R" = rand ] && printf '`define RANDGAP\n' >> gap_defs_$TAG.vh
cp -f $HLSV/*.dat .
$V/xvlog.bat --sv gap_defs_$TAG.vh tb_live_gap.sv ../../orig/live_window_gate.v $QBUF $HLSV/*.v > xvlog_gap_$TAG.txt 2>&1 || { echo XVLOG FAILED; exit 1; }
$V/xelab.bat -debug off -timescale 1ps/1ps tb_live -s tb_gap_sim > xelab_gap_$TAG.txt 2>&1 || { echo XELAB FAILED; exit 1; }
$V/xsim.bat tb_gap_sim -R > xsim_gap_$TAG.txt 2>&1
sed -n '/=== tb_live ===/,/RESULT/p' xsim_gap_$TAG.txt
