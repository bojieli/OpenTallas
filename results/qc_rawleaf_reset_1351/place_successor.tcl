# Diagnostic ECO DPL only. Original kit is mounted read-only at /src.
read_db /src/run/results/asap7/kq_ot_qwen_tile_lsl_rawfault_m3_a0k/base/3_place.odb
source /out/rawleaf_reset_anchor.tcl
detailed_placement
check_placement -verbose
write_db /out/3_place.odb
puts RAWLEAF_RESET_DPL_DONE
