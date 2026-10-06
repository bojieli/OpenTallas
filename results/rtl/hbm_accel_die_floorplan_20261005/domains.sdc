# HBM accelerator die clock domains (AGENTS.md clock domains), tools/hbm_accel_die_fp.py r15 (clk_dom / fwd)
# one PLL output port per domain on hb_coll, ONE logical net per domain to every clocked block (CTS builds a tree per
# clock region from it); one reset net per domain (por_*)
create_clock -name clk_stream -period 0.833 [get_pins hb_coll/pll_stream]
create_clock -name clk_serial -period 1.111 [get_pins hb_coll/pll_serial]
create_clock -name clk_hbm    -period 1.024 [get_pins hb_coll/pll_hbm]
create_clock -name clk_link   -period 0.833 [get_pins hb_coll/pll_link]
set_clock_uncertainty -setup 0.060 [all_clocks]
set_clock_uncertainty -hold 0.025 [all_clocks]
# clock regions (no die-wide synchronous tree):
#   G{SW,SE,NW,NE}{w,e}  SM group halves (2 columns x 2 rows), one local tree each (SMs, multicast / control /
#                        gather stations of the half, row-1 weight meso stations, row-1 request launch stations)
#   HUB-C               centre column (spine + SU / SFU / HC quarters), HUB-Q{SW,SE,NW,NE} scan quadrants (tiles, index)
#   SVC{SW,SE,NW,NE}    stream services (clk_hbm, PHY CK/2), LINK (SerDes / UCIe parallel side, endpoint pclk)
# forwarded links (ot_fwd_link_stage, W512 slices): every chained segment carries its forwarded clocks (one per 512 b
#   slice and direction); a station's flops are clocked by the forwarded clock of its incoming segment, never by a
#   region tree; generated clocks follow the actual forwarded waveform (inverted per stage)
# crossings (each a FIFO, never a timed single-cycle path):
#   M*  forwarded -> region: ot_meso_fifo W512 D4 slices in the meso stations (multicast, control distribution,
#       gather arm entry, row-1 weight line end, link macro end) and inside the receiving hub blocks (cmdproc control
#       upstream, scan quadrant KV / index keys / query, endpoint link rx, loader host rx): 2 periods each,
#       charged once per traversal
#   H*  stream service (clk_hbm) <-> stream: async two-clock FIFOs inside the service
#   X*  SU / SFU / HC / quant (clk_serial) <-> hub stream: ratio CDC 3:4 (inside the SU's HUB_IN / HUB_OUT stages)
#   L*  endpoint core <-> pclk: inside ot_hbm_accel_tu_endpoint
set_clock_groups -asynchronous -group {clk_stream} -group {clk_serial} -group {clk_hbm} -group {clk_link}
