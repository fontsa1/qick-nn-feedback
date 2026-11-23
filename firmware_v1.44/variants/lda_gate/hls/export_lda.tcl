source [file dirname [info script]]/project.tcl
open_project LDA_live_prj
set_top LDA_live
open_solution solution1
export_design -format ip_catalog -version $version -vendor xilinx.com -library hls
exit
