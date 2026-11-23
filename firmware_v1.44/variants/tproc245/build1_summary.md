# v1.44t245 vs v1.44

bit `$QICK_WORK/b1/OG_build_v1.44t245.bit` sha256 `0b5c89e82cc09944530e20914cf98983c8135e38930db42b561dae5482c79346`
hwh `$QICK_WORK/b1/OG_build_v1.44t245.hwh` sha256 `d25b2e4ff913ce6b5ca28c5c04b6a56f6a727ac2e2c68b0789ba95d8fce15a78`
hwh TIMESTAMP (banner): `Mon Nov 16 00:41:12 2026` (v1.44: `Sat Nov  7 19:57:07 2026`)

## Timing (routed)

| clock | period ns | WNS | TNS | fail | WHS | THS | v1.44 WNS | v1.44 WHS |
|---|---|---|---|---|---|---|---|---|
| RFADC0_CLK | 3.617 | 2.633 | 0.000 | 0 | 0.048 | 0.000 | 2.755 | 0.048 |
| clk_out1_d_1_clk_adc0_x2_0 | 1.809 | -0.035 | -9.375 | 658 | 0.002 | 0.000 | 0.000 | 0.010 |
| RFDAC2_CLK | 2.035 | 0.006 | 0.000 | 0 | 0.011 | 0.000 | 0.031 | 0.010 |
| clk_out1_d_1_clk_core_0 | 4.07 | 0.024 | 0.000 | 0 | 0.012 | 0.000 | 0.320 | 0.017 |
| clk_pl_0 | 10.0 | 0.114 | 0.000 | 0 | 0.010 | 0.000 | 0.187 | 0.010 |
| dbg_hub/inst/BSCANID.u_xsdbm_id/SWITCH_N_EXT_BSCAN.bscan_inst/SERIES7_BSCAN.bscan_inst/INTERNAL_TCK | 50.0 | 13.857 | 0.000 | 0 | 0.028 | 0.000 | 15.246 | 0.028 |
| sys_clk_ddr4_clk_p | 4.998 | 2.802 | 0.000 | 0 | 0.041 | 0.000 | 2.765 | 0.037 |
| mmcm_clkout0 | 3.332 | 0.044 | 0.000 | 0 | 0.010 | 0.000 | 0.023 | 0.011 |
| mmcm_clkout5 | 13.328 | 10.522 | 0.000 | 0 | 0.020 | 0.000 | 9.431 | 0.025 |
| mmcm_clkout6 | 6.664 | 1.369 | 0.000 | 0 | 0.022 | 0.000 | 0.621 | 0.019 |

Design: WNS -0.035 TNS -9.375 failing 658/788412; WHS 0.002 THS 0.0 failing 0 (v1.44: WNS 0.0 WHS 0.01)

## Bus skew

- id 1 live_res_cdc_0 Slow: requirement 2.0 actual 0.789 slack 1.211
- id 2 live_res_cdc_1 Slow: requirement 2.0 actual 1.015 slack 0.985
- id 3 axis_avg_buffer_0 Slow: requirement 1.809 actual 0.846 slack 0.963
- id 4 axis_avg_buffer_0 Slow: requirement 1.809 actual 0.73 slack 1.079
- id 5 axis_avg_buffer_1 Slow: requirement 1.809 actual 0.597 slack 1.212
- id 6 axis_avg_buffer_1 Slow: requirement 1.809 actual 0.786 slack 1.023
- id 7 axis_cc_avg_0 Slow: requirement 4.07 actual 0.424 slack 3.646
- id 8 axis_cc_avg_0 Slow: requirement 4.07 actual 0.617 slack 3.453
- id 9 axis_cc_avg_1 Slow: requirement 4.07 actual 0.289 slack 3.781
- id 10 axis_cc_avg_1 Slow: requirement 4.07 actual 0.477 slack 3.593
- id 11 axis_cc_avg_2 Slow: requirement 4.07 actual 0.501 slack 3.569
- id 12 axis_cc_avg_2 Slow: requirement 4.07 actual 0.625 slack 3.445
- id 13 axis_cdcsync_v1_0 Slow: requirement 1.809 actual 0.275 slack 1.534
- id 14 axis_cdcsync_v1_0 Slow: requirement 1.809 actual 0.379 slack 1.43
- id 15 ddr4 Slow: requirement 1.809 actual 0.54 slack 1.269
- id 16 ddr4 Slow: requirement 1.809 actual 0.383 slack 1.426
- id 17 axis_weighted_buffer_0 Slow: requirement 1.809 actual 0.57 slack 1.239
- id 18 axis_weighted_buffer_0 Slow: requirement 1.809 actual 0.533 slack 1.276
- id 19 qick_processor_0 Slow: requirement 2.035 actual 0.093 slack 1.942
- id 20 qick_processor_0 Slow: requirement 2.035 actual 0.167 slack 1.868
- id 21 qick_processor_0 Slow: requirement 2.035 actual 0.241 slack 1.794
- id 22 qick_processor_0 Slow: requirement 2.035 actual 0.674 slack 1.361
- id 23 qick_processor_0 Slow: requirement 2.035 actual 0.745 slack 1.29
- id 24 qick_processor_0 Slow: requirement 2.035 actual 0.168 slack 1.867
- id 25 qick_processor_0 Slow: requirement 2.035 actual 0.237 slack 1.798
- id 26 qick_processor_0 Slow: requirement 2.035 actual 0.144 slack 1.891
- id 27 qick_processor_0 Slow: requirement 2.035 actual 0.093 slack 1.942
- id 28 qick_processor_0 Slow: requirement 2.035 actual 0.216 slack 1.819
- id 29 qick_processor_0 Slow: requirement 2.035 actual 0.123 slack 1.912
- id 30 qick_processor_0 Slow: requirement 2.035 actual 0.306 slack 1.729
- id 31 qick_processor_0 Slow: requirement 2.035 actual 0.172 slack 1.863
- id 32 qick_processor_0 Slow: requirement 2.035 actual 0.107 slack 1.928
- id 33 qick_processor_0 Slow: requirement 2.035 actual 0.18 slack 1.855
- id 34 qick_processor_0 Slow: requirement 2.035 actual 0.223 slack 1.812
- id 35 qick_processor_0 Slow: requirement 2.035 actual 0.213 slack 1.822
- id 36 qick_processor_0 Slow: requirement 2.035 actual 0.209 slack 1.826
- id 37 qick_processor_0 Slow: requirement 2.035 actual 0.163 slack 1.872
- id 38 qick_processor_0 Slow: requirement 2.035 actual 0.154 slack 1.881
- id 39 qick_processor_0 Slow: requirement 2.035 actual 0.23 slack 1.805
- id 40 qick_processor_0 Slow: requirement 2.035 actual 0.243 slack 1.792
- id 41 qick_processor_0 Slow: requirement 2.035 actual 0.213 slack 1.822
- id 42 qick_processor_0 Slow: requirement 2.035 actual 0.188 slack 1.847
- id 43 qick_processor_0 Slow: requirement 2.035 actual 0.097 slack 1.938
- id 44 qick_processor_0 Slow: requirement 2.035 actual 0.449 slack 1.586
- id 45 qick_processor_0 Slow: requirement 2.035 actual 0.188 slack 1.847
- id 46 qick_processor_0 Slow: requirement 2.035 actual 0.271 slack 1.764
- id 47 qick_processor_0 Slow: requirement 2.035 actual 0.124 slack 1.911
- id 48 qick_processor_0 Slow: requirement 2.035 actual 0.093 slack 1.942
- id 49 qick_processor_0 Slow: requirement 2.035 actual 0.202 slack 1.833
- id 50 qick_processor_0 Slow: requirement 2.035 actual 0.395 slack 1.64
- id 51 qick_processor_0 Slow: requirement 2.035 actual 0.157 slack 1.878
- id 52 qick_processor_0 Slow: requirement 2.035 actual 0.203 slack 1.832
- id 53 qick_processor_0 Slow: requirement 2.035 actual 0.159 slack 1.876
- id 54 qick_processor_0 Slow: requirement 2.035 actual 0.252 slack 1.783
- id 55 qick_processor_0 Slow: requirement 2.035 actual 0.174 slack 1.861
- id 56 qick_processor_0 Slow: requirement 2.035 actual 0.17 slack 1.865
- id 57 qick_processor_0 Slow: requirement 2.035 actual 0.118 slack 1.917
- id 58 qick_processor_0 Slow: requirement 2.035 actual 1.049 slack 0.986
- id 59 axis_switch_ddr4 Slow: requirement 7.236 actual 0.756 slack 6.48
- id 60 axis_switch_mr Slow: requirement 7.236 actual 0.419 slack 6.817
- id 61 None Slow: requirement 13.328 actual 0.413 slack 12.915
- id 62 None Slow: requirement 13.328 actual 0.557 slack 12.771
- id 63 None Slow: requirement 13.328 actual 0.453 slack 12.875
- id 64 None Slow: requirement 13.328 actual 0.458 slack 12.87
- v1.44: live_res_cdc_0 Slow slack 1.057; live_res_cdc_1 Slow slack -0.352; axis_avg_buffer_0 Slow slack 1.075; axis_avg_buffer_0 Slow slack 0.845; axis_avg_buffer_1 Slow slack 1.371; axis_avg_buffer_1 Slow slack 1.358; axis_cc_avg_0 Slow slack 4.376; axis_cc_avg_0 Slow slack 4.54; axis_cc_avg_1 Slow slack 4.314; axis_cc_avg_1 Slow slack 4.474; axis_cc_avg_2 Slow slack 4.446; axis_cc_avg_2 Slow slack 4.441; axis_cdcsync_v1_0 Slow slack 1.118; axis_cdcsync_v1_0 Slow slack 1.163; ddr4 Slow slack 1.266; ddr4 Slow slack 1.201; axis_weighted_buffer_0 Slow slack 1.185; axis_weighted_buffer_0 Slow slack 1.366; qick_processor_0 Slow slack 1.709; qick_processor_0 Slow slack 1.914; qick_processor_0 Slow slack 1.504; qick_processor_0 Slow slack 0.861; qick_processor_0 Slow slack 1.794; qick_processor_0 Slow slack 0.984; qick_processor_0 Slow slack 1.499; qick_processor_0 Slow slack 1.6; qick_processor_0 Slow slack 1.5; qick_processor_0 Slow slack 1.803; qick_processor_0 Slow slack 1.834; qick_processor_0 Slow slack 1.833; qick_processor_0 Slow slack 1.814; qick_processor_0 Slow slack 1.903; qick_processor_0 Slow slack 1.827; qick_processor_0 Slow slack 1.787; qick_processor_0 Slow slack 1.823; qick_processor_0 Slow slack 1.75; qick_processor_0 Slow slack 1.622; qick_processor_0 Slow slack 1.74; qick_processor_0 Slow slack 1.812; qick_processor_0 Slow slack 1.79; qick_processor_0 Slow slack 1.377; qick_processor_0 Slow slack 1.965; qick_processor_0 Slow slack 1.749; qick_processor_0 Slow slack 1.762; qick_processor_0 Slow slack 1.805; qick_processor_0 Slow slack 1.748; qick_processor_0 Slow slack 1.842; qick_processor_0 Slow slack 1.764; qick_processor_0 Slow slack 1.881; qick_processor_0 Slow slack 1.888; qick_processor_0 Slow slack 1.886; qick_processor_0 Slow slack 1.92; qick_processor_0 Slow slack 1.732; qick_processor_0 Slow slack 1.778; qick_processor_0 Slow slack 1.853; qick_processor_0 Slow slack 1.851; qick_processor_0 Slow slack 1.766; qick_processor_0 Slow slack 1.886; axis_switch_ddr4 Slow slack 6.762; axis_switch_mr Slow slack 6.075; None Slow slack 12.988; None Slow slack 12.854; None Slow slack 12.955; None Slow slack 12.817

## Utilization (routed)

| block | LUT | FF | DSP | RAMB36 | RAMB18 | v1.44 LUT | v1.44 FF | v1.44 DSP |
|---|---|---|---|---|---|---|---|---|
| NN_live_0 | 1342 | 1222 | 4 | 0 | 1 | 1343 | 1221 | 4 |
| NN_axi_0 | 160867 | 148120 | 14 | 0 | 1 | 160861 | 148120 | 14 |
| boxcar_tap_0 | 1071 | 1701 | 0 | 0 | 0 | 1071 | 1705 | 0 |
| dac_gate_0 | 862 | 2374 | 0 | 0 | 0 | 873 | 2388 | 0 |
| live_gate_0 | 12 | 57 | 0 | 0 | 0 | 12 | 57 | 0 |
| live_res_cdc_0 | 2 | 97 | 0 | 0 | 0 | 2 | 97 | 0 |
| live_res_cdc_1 | 2 | 97 | 0 | 0 | 0 | 2 | 97 | 0 |
| trig_sync_0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 0 |
| seg_stamp_0 | 300 | 912 | 0 | 0 | 0 | 309 | 919 | 0 |
| qick_processor_0 | 8131 | 7219 | 2 | 57 | 1 | 8041 | 7196 | 2 |
| loop logic (Table III b) | 1949 | 4329 | 0 | 0 | 0 | 1960 | 4347 | 0 |

Whole design: LUT 252209 (59.3%), FF 284732, BRAM 500, DSP 542; Table III (v1.44): LUT 252806, FF 285071, BRAM 500, DSP 542

## Build sign-off lines

    NN_live_0 VLNV: xilinx.com:hls:NN_live:1.5
    BLANK_TIMING: 16 register(s); true slack 0.182 requirement 2.035 (d_1_i/dac_gate_0/inst/mk_sel_reg[8]/C -> d_1_i/dac_gate_0/inst/blank_reg_rep__1/D)
    BUSSKEW_ROUTED: live_res_cdc mentioned 420 time(s); VIOLATED x0
    DAC2_CLK_TIMING: RFDAC2_CLK WNS 0.006; worst through dac_gate_0 0.047
    tProc core clock: clk_out1_d_1_clk_core_0, period 4.070 ns
    CORE_CLK_TIMING: period 4.070 WNS 0.024 WHS 0.012
    TAP_TIMING: rf_tap_0 0.078; trig_sync_0 out 1.277; NN_live_0 -0.001
    BOXCAR_TIMING: worst through boxcar_tap_0 -0.008
    ADC0X2_FAIL_SPLIT: axis_avg_buffer_0 5
    ADC0X2_FAIL_SPLIT: axis_avg_buffer_1 2
    ADC0X2_FAIL_SPLIT: axis_cdcsync_v1_0 3
    ADC0X2_FAIL_SPLIT: axis_dyn_readout_v1_0 219
    ADC0X2_FAIL_SPLIT: axis_dyn_readout_v1_1 261
    ADC0X2_FAIL_SPLIT: axis_dyn_readout_v1_2 142
    ADC0X2_FAIL_SPLIT: axis_register_slice_2 5
    ADC0X2_FAIL_SPLIT: axis_register_slice_3 1
    ADC0X2_FAIL_SPLIT: axis_weighted_buffer_0 4
    ADC0X2_FAIL_SPLIT: live_res_cdc_1 1
    ADC0X2_FAIL_SPLIT: seg_stamp_0 15
    ADC0X2_WNS: -0.035 WHS: 0.002
    LIVE_REC_TIMING: worst into live record BRAM 0.091; worst through NN_axi_0 0.114
    BUILD_COMPLETE_v1.44t245
    REPORTS_COMPLETE_v1.44t245
