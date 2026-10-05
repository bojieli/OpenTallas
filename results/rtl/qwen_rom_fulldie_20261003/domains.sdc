# Die-level clock domains (AGENTS.md clock domains; HBM service at the streaming controller's CK/2)
create_clock -name clk_stream -period 0.833 [get_pins hub_el/ck]
create_clock -name clk_serial -period 1.111 [get_pins sp_su64_sfu/ck]
create_clock -name clk_hbm    -period 1.024 [get_pins {phy_*/clk}]
set_clock_uncertainty -setup 0.060 [all_clocks]
set_clock_uncertainty -hold 0.025 [all_clocks]
# crossings (each a FIFO; never a timed single-cycle path):
#   X1/X2/X3  hub spine centre, stream <-> serial, ratio CDC FIFO (rtl/common/ot_ratio_cdc_fifo.sv, 3:4)
#   H1-H24    controller band -> row engines (hbm 976.6 MHz -> stream 1.2 GHz), async two-clock FIFO per row engine
#   K1-K4     strip FIFO -> controller (new K/V write), async
#   M1-M4     strip-end link FIFOs: mesochronous (same 1.2 GHz, separate local trees)
#   L1-L2     IO band: UCIe / board SerDes, plesiochronous
set_clock_groups -asynchronous -group {clk_stream} -group {clk_serial} -group {clk_hbm}
