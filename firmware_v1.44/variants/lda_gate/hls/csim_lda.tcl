source [file dirname [info script]]/project.tcl
open_project -reset LDA_live_prj
set_top LDA_live
add_files $SRC/firmware/LDA_live.cpp -cflags "-std=c++14 -I$SRC/firmware"
add_files -tb $SRC/LDA_live_test.cpp -cflags "-std=c++14 -Wno-unknown-pragmas -I$SRC -I$SRC/firmware"
open_solution -reset solution1 -flow_target vivado
set_part $part
create_clock -period $clock_period -name default
set_clock_uncertainty $clock_uncertainty
config_compile -name_max_length 80
config_export -format ip_catalog -version $version -vendor xilinx.com -library hls
csim_design -O
exit
