#!/bin/bash
# RTL sim of live_window_gate + an HLS NN_live (tb_live.sv). Usage, from rtl_sim/:
#   ./run_tb.sh <HLS project dir>     e.g. ../../neural_net4_live576s
set -e
HLSV=$1/NN_live_prj/solution1/syn/verilog
TAG=$(basename $1)
V="${VIVADO_BIN:?set VIVADO_BIN to the bin folder of Vivado 2023.1}"
QBUF="${QICK_ROOT:?set QICK_ROOT to a QICK checkout at commit 779dffa}/firmware/ip/axis_avg_buffer/src/buffer.sv"
cp -f $HLSV/*.dat .
$V/xvlog.bat --sv tb_live.sv ../../orig/live_window_gate.v $QBUF $HLSV/*.v > xvlog_$TAG.txt 2>&1 || { echo XVLOG FAILED; exit 1; }
$V/xelab.bat -debug off -timescale 1ps/1ps tb_live -s tb_live_sim > xelab_$TAG.txt 2>&1 || { echo XELAB FAILED; exit 1; }
$V/xsim.bat tb_live_sim -R > xsim_$TAG.txt 2>&1
sed -n '/=== tb_live ===/,/RESULT/p' xsim_$TAG.txt
