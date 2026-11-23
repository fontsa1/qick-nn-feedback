# BD diff: ${QICK_WORK:?set QICK_WORK}/b1/nnqick.srcs/sources_1/bd/d_1/d_1.bd vs firmware_v1.44/d_1.bd

cells: 118 (v1.44) vs 118 (new); only in v1.44: none; only in new: none

## Cell VLNV / parameter differences
- /clk_core: CLKOUT1_JITTER: '186.982' -> '85.052'
- /clk_core: CLKOUT1_PHASE_ERROR: '353.086' -> '77.902'
- /clk_core: CLKOUT1_REQUESTED_OUT_FREQ: '200' -> '245.76'
- /clk_core: MMCM_CLKFBOUT_MULT_F: '78.125' -> '4.875'
- /clk_core: MMCM_CLKOUT0_DIVIDE_F: '6.000' -> '4.875'
- /clk_core: MMCM_DIVCLK_DIVIDE: '32' -> '2'

## Port nets (compared by their endpoint sets; net names ignored)
64 vs 64; endpoint sets only in v1.44: 0; only in new: 0

## Interface nets (compared by their endpoint sets; net names ignored)
201 vs 201; endpoint sets only in v1.44: 0; only in new: 0

## Address map entries
45 vs 45; differing: 0
