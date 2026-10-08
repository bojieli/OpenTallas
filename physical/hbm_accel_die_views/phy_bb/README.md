# HBM DS die PHY black boxes (OWNER DECISION 2026-10-06 ~19:20; CLAUDE HBM-ABSTRACTS coordinator)

We do not design the off-die PHYs.  Each is a pin-accurate black box in two placed parts (generator r16j):

| PHY | bump / analog field (no digital pins) | digital-facing pin macro (pins on the core face, M4) | die nets |
|---|---|---|---|
| SerDes (switch tier, 2 x) | `hfd_serdes_slab` S (5 macros) / N (4 macros) | `ot_pdie_serdes` x 9 (S81 black box reused): `clk`, `tx[512]`, `rx[512]` | `lk_lk_<S|N><i>_e` 974 b = 487 tx + 487 rx per macro (TU endpoint NPT = 8 ports x (545-b flit + valid + credit) each way, striped over 9 macros) via the link station chain to `hb_coll`; `clk_link` |
| Host | `hfd_host_slab` | `ot_hbm_host_phy` (NEW, `tools/hbm_phy_bb.py`): `clk` + AXI4-Lite BAR target `s_*` (32 b) + 64-bit AXI host DMA `h_dma_*` | `host_e`: 381 b of the 512-b host chain (rest spare) via the host station chain to `hb_loader` `h`; `clk_link` |

Interface contract (both): every PHY-side pin is launched / captured by a PHY flop on the macro's `clk` (die-supplied
PHY-interface clock, the `clk_link` trunk from `hb_coll.pll_link`).  Liberty (interface timing, ns):

| corner | clk->Q | setup | hold | slew |
|---|---|---|---|---|
| TT | 0.218 | 0.050 | 0.050 | 0.020 |
| SS | 0.295 | 0.070 | 0.030 | 0.030 |
| FF | 0.150 | 0.035 | 0.065 | 0.015 |

CDC into the 1.2 GHz core is on our side and already in RTL: SerDes -- `ot_hbm_accel_tu_endpoint` TX / RX
`ot_link_afifo` (core <-> pclk); host -- `ot_hbm_accel_loader_host` clk_host <-> clk_mem crossing.  No controller block
is missing.  Added cycles: 0 (the link / host station chains already register both ends; the PHY interface flops are the
PHY's own).  Host bandwidth: `h_dma` 64 b x 1.2 GHz = 9.6 GB/s.

Files: `ot_hbm_host_phy/{ot_hbm_host_phy.lef, _bb.v, _tt/_ss/_ff.lib, .json}`, `ot_pdie_serdes/ot_pdie_serdes_{ss,ff}.lib`
(the TT view and LEF stay in physical/asap7_v41x_pdie_macros_v2).  Die-context STA (`hbm_die_views.py die --case sta`)
reads these libs, so the link / host chain ends are timed against the PHY flops.
