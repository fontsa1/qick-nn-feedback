# Build 1 timing remedy, step 1 (the project's standard post-route remedies and the
# build flow's own directives): from v1.44t245_routed.dcp, up to 3 rounds of
#   phys_opt_design -directive AggressiveExplore ; route_design -directive Default -tns_cleanup
# stopping as soon as WNS >= 0 or a round does not improve. Writes v1.44t245r_* files next to the originals and, only if
# setup and hold are met, OG_build_v1.44t245r.bit (+ the unchanged .hwh copied under the same stem).
# Run from the build folder ($QICK_WORK/b1):  vivado -mode batch -source <this> -log remedy1.log
set_param general.maxThreads 6
set T v1.44t245
open_checkpoint ${T}_routed.dcp
proc wns {} { return [get_property SLACK [get_timing_paths -setup -max_paths 1]] }
proc whs {} { return [get_property SLACK [get_timing_paths -hold -max_paths 1]] }
set w0 [wns]; set h0 [whs]
puts "REMEDY_START WNS $w0 WHS $h0"
set best $w0
for {set i 1} {$i <= 3} {incr i} {
    puts "STEP: round $i phys_opt_design -directive AggressiveExplore"
    if {[catch {phys_opt_design -directive AggressiveExplore} e]} { puts "WARNING: phys_opt failed ($e)" }
    puts "REMEDY_ROUND $i after phys_opt WNS [wns]"
    puts "STEP: round $i route_design -directive Default -tns_cleanup"
    route_design -directive Default -tns_cleanup
    set w [wns]; set h [whs]
    puts "REMEDY_ROUND $i after route WNS $w WHS $h"
    write_checkpoint -force ${T}r_round${i}.dcp
    if {$w >= 0 && $h >= 0} { break }
    if {$w <= $best} { puts "REMEDY: round $i did not improve ($w vs $best); stopping"; break }
    set best $w
}
report_timing_summary -file ${T}r_routed_timing.rpt
report_bus_skew -file ${T}r_routed_bus_skew.rpt
report_utilization -file ${T}r_routed_utilization.rpt
report_utilization -hierarchical -file ${T}r_routed_util_hier.rpt
set cclk [get_clocks -of_objects [get_pins -hier -filter "NAME =~ d_1_i/clk_core/clk_out1"]]
set wp [get_timing_paths -group $cclk -max_paths 1 -setup]; set whp [get_timing_paths -group $cclk -max_paths 1 -hold]
puts "CORE_CLK_TIMING: period [get_property PERIOD $cclk] WNS [get_property SLACK $wp] WHS [get_property SLACK $whp]"
set aclk [get_clocks clk_out1_d_1_clk_adc0_x2_0]
puts "ADC0X2_WNS: [get_property SLACK [get_timing_paths -setup -max_paths 1 -group $aclk]] WHS: [get_property SLACK [get_timing_paths -hold -max_paths 1 -group $aclk]]"
set w [wns]; set h [whs]
puts "REMEDY_END WNS $w WHS $h (start $w0 / $h0)"
if {$w >= 0 && $h >= 0} {
    write_checkpoint -force ${T}r_routed.dcp
    write_bitstream -force -file OG_build_${T}r.bit
    file copy -force OG_build_${T}.hwh OG_build_${T}r.hwh
    puts "BUILD_COMPLETE_${T}r"
} else {
    puts "REMEDY_NOT_CLOSED: no bitstream written"
}
exit
