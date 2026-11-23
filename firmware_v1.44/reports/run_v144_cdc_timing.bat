@echo off
rem Runs v144_cdc_timing.tcl read-only on the v1.44 routed checkpoint. cwd = vivado_cwd (journal/.Xil land there).
cd /d %~dp0..\vivado_cwd
call C:\embedded-software\Vivado\2023.1\bin\vivado.bat -mode batch -log ..\logs\v144_cdc_timing.log -journal ..\logs\v144_cdc_timing.jou -source ..\tcl\v144_cdc_timing.tcl > ..\logs\v144_cdc_timing_stdout.log 2>&1
