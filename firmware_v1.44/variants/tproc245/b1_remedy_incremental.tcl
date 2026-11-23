# Build 1 timing remedy, step 2 (incremental compile guided by a known-good placement):
# re-place and re-route v1.44t245_post_opt.dcp with v1.44's routed checkpoint (read-only) as the incremental reference.
# The netlist differs from v1.44 only in clk_core's MMCM settings, so reuse should be high. Known gotcha: with high
# reuse Vivado overrides the route directive and route_design has hung for hours in "Leaf Clock Prog Delay Opt" on large
# netlist deltas; watch log growth (30 min rule) and kill by PID only. Writes v1.44t245i_* and, only if setup and hold
# are met, OG_build_v1.44t245i.bit (+ hwh copy; banner unchanged: Nov 16 00:41:12).
# Run from the build folder ($QICK_WORK/b1):  vivado -mode batch -source <this> -log remedy_incr.log
set_param general.maxThreads 6
set T v1.44t245
set REF $::env(V144_BUILD_DIR)/v1.43_routed.dcp
open_checkpoint ${T}_post_opt.dcp
read_checkpoint -incremental $REF
puts "STEP: place_design (incremental)"
place_design
report_incremental_reuse -file ${T}i_incremental_reuse.rpt
write_checkpoint -force ${T}i_placed.dcp
puts "STEP: phys_opt_design -directive AggressiveExplore (post-place)"
phys_opt_design -directive AggressiveExplore
puts "STEP: route_design -directive Default -tns_cleanup"
route_design -directive Default -tns_cleanup
puts "STEP: phys_opt_design -directive AggressiveExplore (post-route)"
if {[catch {phys_opt_design -directive AggressiveExplore} e]} { puts "WARNING: post-route phys_opt failed ($e)" }
# the build flow's blank-path exception: put the true requirement back before sign-off (as build_nnqick.tcl)
if {[catch {
    set dclk [get_clocks RFDAC2_CLK]
    set blank_cells [get_cells -hier -filter {NAME =~ *dac_gate_0/inst/blank_reg* && IS_SEQUENTIAL}]
    set_max_delay -reset_path -from $dclk -to $blank_cells [get_property PERIOD $dclk]
} e]} { puts "WARNING: blank-path reset failed ($e)" }
write_checkpoint -force ${T}i_routed.dcp
report_timing_summary -file ${T}i_routed_timing.rpt
report_bus_skew -file ${T}i_routed_bus_skew.rpt
report_utilization -file ${T}i_routed_utilization.rpt
report_utilization -hierarchical -file ${T}i_routed_util_hier.rpt
set w [get_property SLACK [get_timing_paths -setup -max_paths 1]]; set h [get_property SLACK [get_timing_paths -hold -max_paths 1]]
set cclk [get_clocks -of_objects [get_pins -hier -filter "NAME =~ d_1_i/clk_core/clk_out1"]]
puts "CORE_CLK_TIMING: period [get_property PERIOD $cclk] WNS [get_property SLACK [get_timing_paths -group $cclk -max_paths 1 -setup]]"
puts "REMEDY_INCR_END WNS $w WHS $h"
if {$w >= 0 && $h >= 0} {
    write_bitstream -force -file OG_build_${T}i.bit
    file copy -force OG_build_${T}.hwh OG_build_${T}i.hwh
    puts "BUILD_COMPLETE_${T}i"
} else { puts "REMEDY_NOT_CLOSED: no bitstream written" }
exit
