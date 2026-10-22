# Standard combinational mapping of the exact eight initialized SFU ln2 ROMs.
# Preserve the normal keep-register policy and all mutable-memory size checks.
source /work/physical/common_flow/ot_keep_regs.tcl
yosys flatten
yosys memory_collect
yosys select -set pool_sfu_rom {*}{t:$mem_v2 r:WR_PORTS=0 %i r:SIZE=256 %i n:*u_exp*proc_rom* %i}
yosys write_json $::env(RESULTS_DIR)/pool_rom_before_map.json
yosys select -assert-count 8 @pool_sfu_rom
exec python3 /work/tools/s81_dv/rtlgap_sukv_1021/pool_rom_check.py $::env(RESULTS_DIR)/pool_rom_before_map.json
yosys memory_map -rom-only @pool_sfu_rom
yosys select -clear
