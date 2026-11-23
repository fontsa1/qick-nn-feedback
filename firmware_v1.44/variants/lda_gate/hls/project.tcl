# HLS settings for LDA_live 1.0: drop-in replacement for NN_live 1.5 (neural_net4_live576s/project.tcl, same part/clock)
set SRC [file dirname [file normalize [info script]]]   ;# this folder (hls)
set part "xczu48dr-ffvg1517-2-e"
# Runs on clk_adc0_x2 beside axis_dyn_readout_v1_0: 552.96 MHz (as NN_live)
set clock_period 1.808
set clock_uncertainty 12.5%
set version "1.0"
