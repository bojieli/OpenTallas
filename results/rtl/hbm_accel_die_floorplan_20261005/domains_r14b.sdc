# HBM accelerator die clock domains (AGENTS.md clock domains), tools/hbm_accel_die_fp.py
create_clock -name clk_stream -period 0.833 [get_pins {hb_vm/ck sm*/ck hb_cmdproc/ck hb_coll/pll}]
create_clock -name clk_serial -period 1.111 [get_pins {hb_su_*/ck hb_sfu_*/ck hb_hc_*/ck hb_quant/ck}]
create_clock -name clk_hbm    -period 1.024 [get_pins {phy_*/clk svc_*/ck}]
set_clock_uncertainty -setup 0.060 [all_clocks]
set_clock_uncertainty -hold 0.025 [all_clocks]
# clock regions (no die-wide synchronous tree: 25.6 x 19.5 mm, qwen_rom_fulldie case d):
#   G{SW,SE,NW,NE}{w,e}  SM group halves (2 columns x 2 rows, <= 4.9 x 4.7 mm), one local tree each
#   HUB-C               centre column (spine + SU / SFU / HC quarters), HUB-Q{SW,SE,NW,NE} scan quadrants
#   SVC{SW,SE,NW,NE}    stream services (clk_hbm, PHY CK/2), STRIP-W/E link macros (own clocks)
# crossings (each a FIFO, never a timed single-cycle path):
#   M*  hub <-> group-half mesochronous FIFOs on every die-level trunk (x multicast, result gather, control, expert
#       request): 2 periods each (results/uarch/meso_fifo_20261004), charged once per hub <-> group traversal
#   H*  stream service (clk_hbm) -> SM weight lines / KV / index rows: async two-clock FIFOs inside the service
#   X*  SU / SFU / HC / quant (clk_serial) <-> hub stream: ratio CDC 3:4 (inside the SU's HUB_IN / HUB_OUT stages)
#   L*  endpoint <-> SerDes / host: plesiochronous at the link macro
set_clock_groups -asynchronous -group {clk_stream} -group {clk_serial} -group {clk_hbm}
