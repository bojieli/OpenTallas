set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach s {AO_RVT_FF_nldm_211120.lib.gz INVBUF_RVT_FF_nldm_220122.lib.gz OA_RVT_FF_nldm_211120.lib.gz SEQ_RVT_FF_nldm_220123.lib SIMPLE_RVT_FF_nldm_211120.lib.gz} { puts "read_liberty $L/asap7sc7p5t_$s"; read_liberty $L/asap7sc7p5t_$s }
foreach f [lsort [glob -nocomplain /work/macros/*_ff.lib]] { puts "read_liberty $f"; read_liberty $f }
read_db /work/run/results/asap7/hd_elemA_rb/base/6_final.odb
read_sdc /work/run/results/asap7/hd_elemA_rb/base/6_final.sdc
read_spef /work/run/results/asap7/hd_elemA_rb/base/6_final.spef
write_timing_model /out/ot_s81hd_elemA_cv_ff.lib
puts OT_CORNER_LIB_DONE
