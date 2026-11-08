set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_db /b/3_2_place_iop.odb
foreach f [glob $P/lib/NLDM/asap7sc7p5t_*RVT_TT_nldm*.lib*] { if {![string match *FAKE* $f]} { read_liberty $f } }
read_liberty /work/macros/ot_sram_1r1w_128x256_m1_r2c2_tt.lib
read_sdc /b/3_place.sdc
set ::env(OT_HPAD_PROBE) 1; set ::env(OT_HPAD_DRY) 1; set ::env(OT_HPAD_WRITE) /p/hpad_list.txt
source /p/hold_pad_struct.tcl
