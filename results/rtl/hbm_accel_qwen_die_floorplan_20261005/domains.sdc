# Qwen3-8B HBM accelerator die clock domains (AGENTS.md clock domains), tools/hbm_accel_die_fp.py --die qwen
create_clock -name clk_stream -period 0.833 [get_pins {sp_core/ck sp_port*/ck sp_scale*/ck sp_loader/ck}]
create_clock -name clk_serial -period 1.111 [get_pins {io_coll/pll}]
create_clock -name clk_hbm    -period 1.024 [get_pins {phy_*/clk svc_*/ck}]
set_clock_uncertainty -setup 0.060 [all_clocks]
set_clock_uncertainty -hold 0.025 [all_clocks]
# no die-wide synchronous tree (32 x 26 mm; qwen_rom_fulldie case d): the core x root launches the corridor with its
# own forwarded clock (64 corridor tracks) through the head chain and every column's abutting tile elements; the tile
# tree words return to the port slices through a mesochronous FIFO (2 periods, charged on the TWS path)
#   H*  stream service (clk_hbm) -> fill bus / status: async FIFO inside the service (2 periods, charged per first
#       access); status counts gray-coded through the vehicle's two-flop synchronisers
#   X*  SU64/SFU and collective (clk_serial) <-> core: ratio CDC 3:4 inside the core
#   L*  collective <-> SerDes, loader <-> UCIe: plesiochronous at the link macro
set_clock_groups -asynchronous -group {clk_stream} -group {clk_serial} -group {clk_hbm}
