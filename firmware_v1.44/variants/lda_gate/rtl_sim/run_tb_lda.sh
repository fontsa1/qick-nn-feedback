#!/bin/bash
# RTL sim of live_window_gate + the HLS-generated LDA_live (tb_lda.sv), run in $QICK_WORK/rtl_sim_lda.
#   bash firmware_v1.44/variants/lda_gate/rtl_sim/run_tb_lda.sh
set -e
SD="$(cd "$(dirname "$0")" && pwd)"
R=${QICK_WORK:?set QICK_WORK}/rtl_sim_lda
HLSV=${1:-${QICK_WORK:?set QICK_WORK}/hls_lda}/LDA_live_prj/solution1/syn/verilog
TAG=${2:-lda}
V=/c/embedded-software/Vivado/2023.1/bin
GATE="${QICK_REPO:?set QICK_REPO}/rtl/live_window_gate.v"
QBUF="${QICK_SRC:?set QICK_SRC to a QICK checkout at commit 779dffa}"/firmware/ip/axis_avg_buffer/src/buffer.sv
cd $R
cp -f $HLSV/*.dat .
$V/xvlog.bat --sv $SD/tb_lda.sv $GATE $QBUF $HLSV/*.v > xvlog_$TAG.txt 2>&1 || { echo XVLOG FAILED; exit 1; }
$V/xelab.bat -debug off -timescale 1ps/1ps tb_lda -s tb_lda_sim > xelab_$TAG.txt 2>&1 || { echo XELAB FAILED; exit 1; }
$V/xsim.bat tb_lda_sim -R > xsim_$TAG.txt 2>&1
cp xsim_$TAG.txt $SD/xsim_$TAG.txt
sed -n '/^result /p;/=== tb_lda ===/,/RESULT/p' xsim_$TAG.txt
