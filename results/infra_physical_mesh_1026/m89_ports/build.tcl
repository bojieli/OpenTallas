set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $P/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*] { read_liberty $f }
read_def /work/mesh_straps.def
source $P/openRoad/make_tracks.tcl
create_clock -name clk -period 833 [get_ports clk]
write_db /work/mesh_straps.odb
write_def /work/mesh_straps_before.def
write_sdc /work/mesh.sdc
exit
