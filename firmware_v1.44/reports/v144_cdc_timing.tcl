# v144_cdc_timing.tcl -- clock-crossing, bus-skew and decision-path timing of the v1.44 routed checkpoint.
# READ-ONLY: opens the checkpoint, writes reports only into firmware_v1.44/reports.
# Never calls write_checkpoint / write_bitstream / save.
# Run with cwd = a scratch folder:
#   vivado -mode batch -log ../logs/v144_cdc_timing.log -journal ../logs/v144_cdc_timing.jou -source ../tcl/v144_cdc_timing.tcl
#
# Checkpoint: the build's routed .dcp (DCP below). The v1.44 build reused the v1.43 build script
# (TAG v1.43), so its files are named v1.43_*; written in the session (build_nnqick_v1.44.log line 5176) that wrote
# OG_build_v1.43.bit (sha256 986c861a...), identical to firmware_v1.44/OG_build_v1.44.bit.

set_param general.maxThreads 4
set DCP $::env(V144_ROUTED_DCP)   ;# the build's v1.43_routed.dcp (not shipped: 1.6 GB)
set R [file normalize ../reports]
file mkdir $R
proc step {m} { puts "STEP [clock format [clock seconds] -format {%H:%M:%S}]: $m"; flush stdout }
proc tryrun {name script} {
    step "begin $name"
    if {[catch {uplevel 1 $script} e]} { puts "WARNING: $name failed: $e" }
    step "end $name"
}

step "open_checkpoint $DCP (size [file size $DCP], mtime [clock format [file mtime $DCP]])"
open_checkpoint $DCP
step "opened: part [get_property PART [current_design]]"

set S [open $R/summary_values.txt w]
proc kv {k v} { global S; puts $S "$k\t$v"; flush $S; puts "KV $k = $v" }
kv dcp $DCP
kv dcp_size [file size $DCP]

# ---------------- clocks
tryrun clocks {
    report_clocks -file $R/v144_clocks.rpt
    report_clock_interaction -delay_type min_max -significant_digits 3 -file $R/v144_clock_interaction.rpt
}
set BD d_1
set aclk [get_clocks -of_objects [get_pins ${BD}_i/live_res_cdc_1/s_aclk]]
set dclk [get_clocks -of_objects [get_pins ${BD}_i/live_res_cdc_1/m_aclk]]
set cclk [get_clocks -of_objects [get_pins ${BD}_i/live_res_cdc_0/m_aclk]]
foreach {n c} [list src_adc0x2 $aclk dst_dac2 $dclk dst_core $cclk] {
    kv clock_$n "[get_property NAME $c] period [get_property PERIOD $c]"
}

# ---------------- timing summary
tryrun timing_summary {
    report_timing_summary -max_paths 10 -report_unconstrained -significant_digits 3 -file $R/v144_timing_summary.rpt
}

# ---------------- worst setup / hold per path group (endpoint clock), and per intra-clock pair
tryrun per_group {
    set f [open $R/v144_worst_per_group.tsv w]
    puts $f "group\tkind\tslack_ns\tstart_clock\tend_clock\tlogic_levels\tdatapath_ns\tstartpoint\tendpoint"
    foreach g [lsort [get_path_groups]] {
        foreach kind {setup hold} {
            set p [get_timing_paths -$kind -max_paths 1 -nworst 1 -group $g]
            if {[llength $p] == 0} continue
            puts $f "$g\t$kind\t[get_property SLACK $p]\t[get_property STARTPOINT_CLOCK $p]\t[get_property ENDPOINT_CLOCK $p]\t[get_property LOGIC_LEVELS $p]\t[get_property DATAPATH_DELAY $p]\t[get_property STARTPOINT_PIN $p]\t[get_property ENDPOINT_PIN $p]"
        }
    }
    close $f
    report_timing -setup -max_paths 1 -nworst 1 -sort_by group -significant_digits 3 -input_pins -file $R/v144_worst_setup_per_group.rpt
}
tryrun worst_overall {
    report_timing -setup -max_paths 20 -nworst 1 -unique_pins -significant_digits 3 -input_pins -file $R/v144_worst20_setup.rpt
}

# ---------------- bus skew and CDC
tryrun bus_skew {
    report_bus_skew -warn_on_violation -max_paths 20 -nworst 4 -significant_digits 3 -file $R/v144_bus_skew.rpt
    report_bus_skew -warn_on_violation -max_paths 70 -nworst 70 -unique_pins -significant_digits 3 -file $R/v144_bus_skew_allbits.rpt
}
tryrun cdc {
    report_cdc -file $R/v144_cdc_summary.rpt
    report_cdc -details -file $R/v144_cdc_details.rpt
    report_cdc -from $aclk -to $dclk -details -file $R/v144_cdc_adc0x2_to_dac2.rpt
    report_cdc -from $aclk -to $cclk -details -file $R/v144_cdc_adc0x2_to_core.rpt
}
tryrun exceptions {
    report_exceptions -file $R/v144_exceptions.rpt
    report_exceptions -ignored -file $R/v144_exceptions_ignored.rpt
    report_exceptions -scope_override -file $R/v144_exceptions_scope_override.rpt
    report_exceptions -from [get_cells ${BD}_i/live_res_cdc_1/*] -file $R/v144_exceptions_live_res_cdc_1.rpt
    report_exceptions -from [get_cells ${BD}_i/live_res_cdc_0/*] -file $R/v144_exceptions_live_res_cdc_0.rpt
}

# CDC data path delays (async groups => these are not timed; report them unconstrained for the record)
tryrun cdc_paths {
    foreach inst {live_res_cdc_0 live_res_cdc_1} {
        set fr [get_cells "${BD}_i/$inst/hold_reg[*] ${BD}_i/$inst/tog_reg"]
        set to [get_cells "${BD}_i/$inst/tog_sync_reg[0] ${BD}_i/$inst/m_axis_tdata_reg[*]"]
        report_timing -from $fr -to $to -max_paths 70 -nworst 1 -unique_pins -significant_digits 3 -file $R/v144_${inst}_crossing_paths_max.rpt
        report_timing -from $fr -to $to -delay_type min -max_paths 70 -nworst 1 -unique_pins -significant_digits 3 -file $R/v144_${inst}_crossing_paths_min.rpt
        # summary per endpoint: datapath delay max/min
        set f [open $R/v144_${inst}_crossing_delays.tsv w]
        puts $f "endpoint\tmax_datapath_ns\tmin_datapath_ns\tmax_exception"
        foreach t [get_cells "${BD}_i/$inst/tog_sync_reg[0] ${BD}_i/$inst/m_axis_tdata_reg[*]"] {
            set pmx [get_timing_paths -from $fr -to $t -max_paths 1 -nworst 1 -delay_type max]
            set pmn [get_timing_paths -from $fr -to $t -max_paths 1 -nworst 1 -delay_type min]
            set ex ""
            catch {set ex [get_property EXCEPTION $pmx]}
            puts $f "$t\t[get_property DATAPATH_DELAY $pmx]\t[get_property DATAPATH_DELAY $pmn]\t$ex"
        }
        close $f
    }
}

# setup / hold requirement of the destination flops (library arcs)
tryrun ff_setup {
    set f [open $R/v144_cdc_dest_ff_setup_hold.tsv w]
    puts $f "cell\tref\tarc_type\tdelay_max_rise\tdelay_max_fall\tdelay_min_rise\tdelay_min_fall"
    foreach inst {live_res_cdc_0 live_res_cdc_1} {
        foreach c [list ${BD}_i/$inst/tog_sync_reg[0] ${BD}_i/$inst/m_axis_tdata_reg[0] ${BD}_i/$inst/m_axis_tdata_reg[63]] {
            set cell [get_cells $c]
            foreach a [get_timing_arcs -of_objects $cell] {
                set ty [get_property TYPE $a]
                if {[string match -nocase "*setup*" $ty] || [string match -nocase "*hold*" $ty]} {
                    puts $f "$c\t[get_property REF_NAME $cell]\t$ty [get_property FROM_PIN $a]->[get_property TO_PIN $a]\t[get_property DELAY_MAX_RISE $a]\t[get_property DELAY_MAX_FALL $a]\t[get_property DELAY_MIN_RISE $a]\t[get_property DELAY_MIN_FALL $a]"
                }
            }
        }
    }
    close $f
}

# ---------------- decision path: boxcar -> window gate -> NN_live -> CDC hold -> [crossing] -> dac_gate -> RFdc
set seg [list \
    boxcar_to_gate     "${BD}_i/boxcar_tap_0/*"   "${BD}_i/live_gate_0/*" \
    gate_to_nnlive     "${BD}_i/live_gate_0/*"    "${BD}_i/NN_live_0/*" \
    nnlive_internal    "${BD}_i/NN_live_0/*"      "${BD}_i/NN_live_0/*" \
    nnlive_to_cdc1     "${BD}_i/NN_live_0/*"      "${BD}_i/live_res_cdc_1/*" \
    nnlive_to_cdc0     "${BD}_i/NN_live_0/*"      "${BD}_i/live_res_cdc_0/*" \
    cdc1_dest_to_gate  "${BD}_i/live_res_cdc_1/*" "${BD}_i/dac_gate_0/*" \
    dacgate_internal   "${BD}_i/dac_gate_0/*"     "${BD}_i/dac_gate_0/*" \
    dacgate_to_rfdc    "${BD}_i/dac_gate_0/*"     "${BD}_i/usp_rf_data_converter_0/*" \
]
tryrun decision_path {
    set f [open $R/v144_decision_path_slack.tsv w]
    puts $f "segment\tkind\tslack_ns\tstart_clock\tend_clock\tlogic_levels\tdatapath_ns\tstartpoint\tendpoint"
    foreach {name a b} $seg {
        set fa [get_cells -hier -filter "NAME =~ $a && IS_PRIMITIVE"]
        set fb [get_cells -hier -filter "NAME =~ $b && IS_PRIMITIVE"]
        foreach kind {setup hold} {
            set p [get_timing_paths -$kind -from $fa -to $fb -max_paths 1 -nworst 1]
            if {[llength $p] == 0} { puts $f "$name\t$kind\tNO_PATH"; continue }
            puts $f "$name\t$kind\t[get_property SLACK $p]\t[get_property STARTPOINT_CLOCK $p]\t[get_property ENDPOINT_CLOCK $p]\t[get_property LOGIC_LEVELS $p]\t[get_property DATAPATH_DELAY $p]\t[get_property STARTPOINT_PIN $p]\t[get_property ENDPOINT_PIN $p]"
        }
        report_timing -setup -from $fa -to $fb -max_paths 10 -nworst 1 -unique_pins -significant_digits 3 -input_pins -file $R/v144_decision_${name}.rpt
    }
    # all paths through NN_live (any end), and through the gate/dac_gate
    foreach {nm pat} [list nn_live_through "${BD}_i/NN_live_0/*" live_gate_through "${BD}_i/live_gate_0/*" dac_gate_through "${BD}_i/dac_gate_0/*" boxcar_through "${BD}_i/boxcar_tap_0/*"] {
        set cs [get_cells -hier -filter "NAME =~ $pat && IS_PRIMITIVE"]
        set p [get_timing_paths -setup -through $cs -max_paths 1 -nworst 1]
        puts $f "$nm\tsetup\t[get_property SLACK $p]\t[get_property STARTPOINT_CLOCK $p]\t[get_property ENDPOINT_CLOCK $p]\t[get_property LOGIC_LEVELS $p]\t[get_property DATAPATH_DELAY $p]\t[get_property STARTPOINT_PIN $p]\t[get_property ENDPOINT_PIN $p]"
        report_timing -setup -through $cs -max_paths 20 -nworst 1 -unique_pins -significant_digits 3 -input_pins -file $R/v144_${nm}.rpt
    }
    close $f
}

# ---------------- slack histogram of the readout clock and the DAC clock (margin context)
tryrun slack_hist {
    set f [open $R/v144_near_critical_counts.tsv w]
    puts $f "group\tthreshold_ns\tendpoints_with_slack_below"
    foreach g [list [get_property NAME $aclk] [get_property NAME $dclk] [get_property NAME $cclk]] {
        foreach th {0.010 0.050 0.100 0.200} {
            set ps [get_timing_paths -setup -group $g -max_paths 100000 -nworst 1 -unique_pins -slack_lesser_than $th]
            puts $f "$g\t$th\t[llength $ps]"
        }
        # which blocks own the endpoints below 0.1 ns
        set ps [get_timing_paths -setup -group $g -max_paths 100000 -nworst 1 -unique_pins -slack_lesser_than 0.100]
        array unset nb
        foreach p $ps { set k [lindex [split [get_property NAME [get_property ENDPOINT_PIN $p]] /] 1]; if {![info exists nb($k)]} {set nb($k) 0}; incr nb($k) }
        foreach k [lsort [array names nb]] { puts $f "$g\tblock<0.1:$k\t$nb($k)" }
    }
    close $f
}

# ---------------- methodology (slow) and utilization (Table III)
tryrun utilization {
    report_utilization -file $R/v144_utilization.rpt
    report_utilization -hierarchical -hierarchical_depth 3 -file $R/v144_util_hier_d3.rpt
}
tryrun methodology {
    report_methodology -file $R/v144_methodology.rpt
}
close $S
step "DONE"
