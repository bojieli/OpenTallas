set arm $::env(QWEN_SCALE_ARM)
read_db /work/out/${arm}/grt.odb
check_placement -verbose
