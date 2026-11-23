# v1.44lda vs v1.44

bit `$QICK_WORK/b2/OG_build_v1.44lda.bit` sha256 `44f9f1deed55c096537be6278e1bbfc3139aefcb1077942af9d76eede5acaf73`
hwh `$QICK_WORK/b2/OG_build_v1.44lda.hwh` sha256 `6be90d147da5f61311894ab62d5521366ca08f499a42dc06f4f3b738b043d538`
hwh TIMESTAMP (banner): `Mon Nov 16 06:48:29 2026` (v1.44: `Sat Nov  7 19:57:07 2026`)

## Timing (routed)

| clock | period ns | WNS | TNS | fail | WHS | THS | v1.44 WNS | v1.44 WHS |
|---|---|---|---|---|---|---|---|---|
| RFADC0_CLK | 3.617 | 2.751 | 0.000 | 0 | 0.041 | 0.000 | 2.755 | 0.048 |
| clk_out1_d_1_clk_adc0_x2_0 | 1.809 | -0.094 | -27.801 | 727 | 0.010 | 0.000 | 0.000 | 0.010 |
| RFDAC2_CLK | 2.035 | 0.008 | 0.000 | 0 | 0.011 | 0.000 | 0.031 | 0.010 |
| clk_out1_d_1_clk_core_0 | 5.001 | 0.251 | 0.000 | 0 | 0.015 | 0.000 | 0.320 | 0.017 |
| clk_pl_0 | 10.0 | 0.416 | 0.000 | 0 | 0.009 | 0.000 | 0.187 | 0.010 |
| dbg_hub/inst/BSCANID.u_xsdbm_id/SWITCH_N_EXT_BSCAN.bscan_inst/SERIES7_BSCAN.bscan_inst/INTERNAL_TCK | 50.0 | 13.644 | 0.000 | 0 | 0.032 | 0.000 | 15.246 | 0.028 |
| sys_clk_ddr4_clk_p | 4.998 | 3.104 | 0.000 | 0 | 0.057 | 0.000 | 2.765 | 0.037 |
| mmcm_clkout0 | 3.332 | 0.009 | 0.000 | 0 | 0.010 | 0.000 | 0.023 | 0.011 |
| mmcm_clkout5 | 13.328 | 10.302 | 0.000 | 0 | 0.028 | 0.000 | 9.431 | 0.025 |
| mmcm_clkout6 | 6.664 | 1.439 | 0.000 | 0 | 0.030 | 0.000 | 0.621 | 0.019 |

Design: WNS -0.094 TNS -27.801 failing 727/788405; WHS 0.009 THS 0.0 failing 0 (v1.44: WNS 0.0 WHS 0.01)

## Bus skew

- id 1 live_res_cdc_0 Slow: requirement 2.0 actual 1.173 slack 0.827
- id 2 live_res_cdc_1 Slow: requirement 2.0 actual 0.931 slack 1.069
- id 3 axis_avg_buffer_0 Slow: requirement 1.809 actual 0.499 slack 1.31
- id 4 axis_avg_buffer_0 Slow: requirement 1.809 actual 0.538 slack 1.271
- id 5 axis_avg_buffer_1 Slow: requirement 1.809 actual 0.401 slack 1.408
- id 6 axis_avg_buffer_1 Slow: requirement 1.809 actual 0.901 slack 0.908
- id 7 axis_cc_avg_0 Slow: requirement 5.001 actual 0.619 slack 4.382
- id 8 axis_cc_avg_0 Slow: requirement 5.001 actual 0.709 slack 4.292
- id 9 axis_cc_avg_1 Slow: requirement 5.001 actual 0.642 slack 4.359
- id 10 axis_cc_avg_1 Slow: requirement 5.001 actual 0.89 slack 4.111
- id 11 axis_cc_avg_2 Slow: requirement 5.001 actual 0.651 slack 4.35
- id 12 axis_cc_avg_2 Slow: requirement 5.001 actual 0.58 slack 4.421
- id 13 axis_cdcsync_v1_0 Slow: requirement 1.809 actual 0.592 slack 1.217
- id 14 axis_cdcsync_v1_0 Slow: requirement 1.809 actual 0.641 slack 1.168
- id 15 ddr4 Slow: requirement 1.809 actual 0.643 slack 1.166
- id 16 ddr4 Slow: requirement 1.809 actual 0.644 slack 1.165
- id 17 axis_weighted_buffer_0 Slow: requirement 1.809 actual 0.87 slack 0.939
- id 18 axis_weighted_buffer_0 Slow: requirement 1.809 actual 0.731 slack 1.078
- id 19 qick_processor_0 Slow: requirement 2.035 actual 0.065 slack 1.97
- id 20 qick_processor_0 Slow: requirement 2.035 actual 0.202 slack 1.833
- id 21 qick_processor_0 Slow: requirement 2.035 actual 0.255 slack 1.78
- id 22 qick_processor_0 Slow: requirement 2.035 actual 0.115 slack 1.92
- id 23 qick_processor_0 Slow: requirement 2.035 actual 0.235 slack 1.8
- id 24 qick_processor_0 Slow: requirement 2.035 actual 0.184 slack 1.851
- id 25 qick_processor_0 Slow: requirement 2.035 actual 0.295 slack 1.74
- id 26 qick_processor_0 Slow: requirement 2.035 actual 0.176 slack 1.859
- id 27 qick_processor_0 Slow: requirement 2.035 actual 0.065 slack 1.97
- id 28 qick_processor_0 Slow: requirement 2.035 actual 0.166 slack 1.869
- id 29 qick_processor_0 Slow: requirement 2.035 actual 0.421 slack 1.614
- id 30 qick_processor_0 Slow: requirement 2.035 actual 0.169 slack 1.866
- id 31 qick_processor_0 Slow: requirement 2.035 actual 0.224 slack 1.811
- id 32 qick_processor_0 Slow: requirement 2.035 actual 0.273 slack 1.762
- id 33 qick_processor_0 Slow: requirement 2.035 actual 0.119 slack 1.916
- id 34 qick_processor_0 Slow: requirement 2.035 actual 0.121 slack 1.914
- id 35 qick_processor_0 Slow: requirement 2.035 actual 0.202 slack 1.833
- id 36 qick_processor_0 Slow: requirement 2.035 actual 0.328 slack 1.707
- id 37 qick_processor_0 Slow: requirement 2.035 actual 0.097 slack 1.938
- id 38 qick_processor_0 Slow: requirement 2.035 actual 0.143 slack 1.892
- id 39 qick_processor_0 Slow: requirement 2.035 actual 0.156 slack 1.879
- id 40 qick_processor_0 Slow: requirement 2.035 actual 0.118 slack 1.917
- id 41 qick_processor_0 Slow: requirement 2.035 actual 0.145 slack 1.89
- id 42 qick_processor_0 Slow: requirement 2.035 actual 0.172 slack 1.863
- id 43 qick_processor_0 Slow: requirement 2.035 actual 0.192 slack 1.843
- id 44 qick_processor_0 Slow: requirement 2.035 actual 0.724 slack 1.311
- id 45 qick_processor_0 Slow: requirement 2.035 actual 0.092 slack 1.943
- id 46 qick_processor_0 Slow: requirement 2.035 actual 0.233 slack 1.802
- id 47 qick_processor_0 Slow: requirement 2.035 actual 0.203 slack 1.832
- id 48 qick_processor_0 Slow: requirement 2.035 actual 0.084 slack 1.951
- id 49 qick_processor_0 Slow: requirement 2.035 actual 0.149 slack 1.886
- id 50 qick_processor_0 Slow: requirement 2.035 actual 0.248 slack 1.787
- id 51 qick_processor_0 Slow: requirement 2.035 actual 0.06 slack 1.975
- id 52 qick_processor_0 Slow: requirement 2.035 actual 0.131 slack 1.904
- id 53 qick_processor_0 Slow: requirement 2.035 actual 0.237 slack 1.798
- id 54 qick_processor_0 Slow: requirement 2.035 actual 0.158 slack 1.877
- id 55 qick_processor_0 Slow: requirement 2.035 actual 0.219 slack 1.816
- id 56 qick_processor_0 Slow: requirement 2.035 actual 0.191 slack 1.844
- id 57 qick_processor_0 Slow: requirement 2.035 actual 0.247 slack 1.788
- id 58 qick_processor_0 Slow: requirement 2.035 actual 0.225 slack 1.81
- id 59 axis_switch_ddr4 Slow: requirement 7.236 actual 1.631 slack 5.605
- id 60 axis_switch_mr Slow: requirement 7.236 actual 0.445 slack 6.791
- id 61 None Slow: requirement 13.328 actual 0.538 slack 12.79
- id 62 None Slow: requirement 13.328 actual 0.323 slack 13.005
- id 63 None Slow: requirement 13.328 actual 0.606 slack 12.722
- id 64 None Slow: requirement 13.328 actual 0.674 slack 12.654
- v1.44: live_res_cdc_0 Slow slack 1.057; live_res_cdc_1 Slow slack -0.352; axis_avg_buffer_0 Slow slack 1.075; axis_avg_buffer_0 Slow slack 0.845; axis_avg_buffer_1 Slow slack 1.371; axis_avg_buffer_1 Slow slack 1.358; axis_cc_avg_0 Slow slack 4.376; axis_cc_avg_0 Slow slack 4.54; axis_cc_avg_1 Slow slack 4.314; axis_cc_avg_1 Slow slack 4.474; axis_cc_avg_2 Slow slack 4.446; axis_cc_avg_2 Slow slack 4.441; axis_cdcsync_v1_0 Slow slack 1.118; axis_cdcsync_v1_0 Slow slack 1.163; ddr4 Slow slack 1.266; ddr4 Slow slack 1.201; axis_weighted_buffer_0 Slow slack 1.185; axis_weighted_buffer_0 Slow slack 1.366; qick_processor_0 Slow slack 1.709; qick_processor_0 Slow slack 1.914; qick_processor_0 Slow slack 1.504; qick_processor_0 Slow slack 0.861; qick_processor_0 Slow slack 1.794; qick_processor_0 Slow slack 0.984; qick_processor_0 Slow slack 1.499; qick_processor_0 Slow slack 1.6; qick_processor_0 Slow slack 1.5; qick_processor_0 Slow slack 1.803; qick_processor_0 Slow slack 1.834; qick_processor_0 Slow slack 1.833; qick_processor_0 Slow slack 1.814; qick_processor_0 Slow slack 1.903; qick_processor_0 Slow slack 1.827; qick_processor_0 Slow slack 1.787; qick_processor_0 Slow slack 1.823; qick_processor_0 Slow slack 1.75; qick_processor_0 Slow slack 1.622; qick_processor_0 Slow slack 1.74; qick_processor_0 Slow slack 1.812; qick_processor_0 Slow slack 1.79; qick_processor_0 Slow slack 1.377; qick_processor_0 Slow slack 1.965; qick_processor_0 Slow slack 1.749; qick_processor_0 Slow slack 1.762; qick_processor_0 Slow slack 1.805; qick_processor_0 Slow slack 1.748; qick_processor_0 Slow slack 1.842; qick_processor_0 Slow slack 1.764; qick_processor_0 Slow slack 1.881; qick_processor_0 Slow slack 1.888; qick_processor_0 Slow slack 1.886; qick_processor_0 Slow slack 1.92; qick_processor_0 Slow slack 1.732; qick_processor_0 Slow slack 1.778; qick_processor_0 Slow slack 1.853; qick_processor_0 Slow slack 1.851; qick_processor_0 Slow slack 1.766; qick_processor_0 Slow slack 1.886; axis_switch_ddr4 Slow slack 6.762; axis_switch_mr Slow slack 6.075; None Slow slack 12.988; None Slow slack 12.854; None Slow slack 12.955; None Slow slack 12.817

## Utilization (routed)

| block | LUT | FF | DSP | RAMB36 | RAMB18 | v1.44 LUT | v1.44 FF | v1.44 DSP |
|---|---|---|---|---|---|---|---|---|
| NN_live_0 | 763 | 669 | 2 | 0 | 1 | 1343 | 1221 | 4 |
| NN_axi_0 | 160870 | 148120 | 14 | 0 | 1 | 160861 | 148120 | 14 |
| boxcar_tap_0 | 1071 | 1781 | 0 | 0 | 0 | 1071 | 1705 | 0 |
| dac_gate_0 | 866 | 2390 | 0 | 0 | 0 | 873 | 2388 | 0 |
| live_gate_0 | 12 | 57 | 0 | 0 | 0 | 12 | 57 | 0 |
| live_res_cdc_0 | 2 | 97 | 0 | 0 | 0 | 2 | 97 | 0 |
| live_res_cdc_1 | 2 | 97 | 0 | 0 | 0 | 2 | 97 | 0 |
| trig_sync_0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 0 |
| seg_stamp_0 | 304 | 912 | 0 | 0 | 0 | 309 | 919 | 0 |
| qick_processor_0 | 8092 | 7254 | 2 | 57 | 1 | 8041 | 7196 | 2 |
| loop logic (Table III b) | 1953 | 4425 | 0 | 0 | 0 | 1960 | 4347 | 0 |

Whole design: LUT 251907 (59.23%), FF 284069, BRAM 500, DSP 540; Table III (v1.44): LUT 252806, FF 285071, BRAM 500, DSP 542

## Build sign-off lines

    NN_live_0 VLNV: xilinx.com:hls:LDA_live:1.0
    BLANK_TIMING: 18 register(s); true slack 0.196 requirement 2.035 (d_1_i/dac_gate_0/inst/mk_sel_reg[10]/C -> d_1_i/dac_gate_0/inst/blank_reg_rep__2_replica/D)
    BUSSKEW_ROUTED: live_res_cdc mentioned 420 time(s); VIOLATED x0
    DAC2_CLK_TIMING: RFDAC2_CLK WNS 0.008; worst through dac_gate_0 0.067
    tProc core clock: clk_out1_d_1_clk_core_0, period 5.001 ns
    CORE_CLK_TIMING: period 5.001 WNS 0.251 WHS 0.015
    TAP_TIMING: rf_tap_0 -0.008; trig_sync_0 out 0.785; NN_live_0 -0.065
    BOXCAR_TIMING: worst through boxcar_tap_0 -0.094
    ADC0X2_FAIL_SPLIT: NN_live_0 5
    ADC0X2_FAIL_SPLIT: axis_avg_buffer_0 30
    ADC0X2_FAIL_SPLIT: axis_avg_buffer_1 51
    ADC0X2_FAIL_SPLIT: axis_cdcsync_v1_0 4
    ADC0X2_FAIL_SPLIT: axis_dyn_readout_v1_0 70
    ADC0X2_FAIL_SPLIT: axis_dyn_readout_v1_1 303
    ADC0X2_FAIL_SPLIT: axis_dyn_readout_v1_2 200
    ADC0X2_FAIL_SPLIT: axis_register_slice_2 12
    ADC0X2_FAIL_SPLIT: axis_weighted_buffer_0 36
    ADC0X2_FAIL_SPLIT: boxcar_tap_0 7
    ADC0X2_FAIL_SPLIT: ddr4 3
    ADC0X2_FAIL_SPLIT: mr_buffer_et_0 3
    ADC0X2_FAIL_SPLIT: rf_tap_0 1
    ADC0X2_FAIL_SPLIT: rst_adc0_x2 1
    ADC0X2_FAIL_SPLIT: seg_stamp_0 1
    ADC0X2_WNS: -0.094 WHS: 0.010
    LIVE_REC_TIMING: worst into live record BRAM 0.038; worst through NN_axi_0 0.416
    BUILD_COMPLETE_v1.44lda
    REPORTS_COMPLETE_v1.44lda
