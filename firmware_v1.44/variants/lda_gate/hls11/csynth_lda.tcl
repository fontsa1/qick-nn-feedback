source [file dirname [info script]]/project.tcl
open_project LDA_live_prj
set_top LDA_live
open_solution solution1
csynth_design
puts "CSYNTH DONE"
exit
