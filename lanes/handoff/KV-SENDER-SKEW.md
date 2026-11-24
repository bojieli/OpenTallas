# KV-SENDER-SKEW handoff (updated 11-24 00:0x PST; supersedes the 23:2x version)
STATUS: cause measured, fix NOT ready. Nothing for A6 yet. No bind result exists.
## Established (4_cts seamhold kits, placement RC)
- 67 rows in fam-late-export.tsv (brief said 68; 68 lines include the header). 66: export BUFx24 at a stale far source_clock_port, 2-12 wire repeaters. 1 (io_ft_v1 ft3_o): kit SDC tap window only.
- Launch flop exists on every checked ring; none is a pure feedthrough. Some (pv_v12 / v6n ft) last launch flops sit ~365-380 um from the port (median ck-port), so a ring spreads up to 421 ps between fstart and data bits.
- Only 40 rings (all pv_v12) read min < -365 (=-385 contract + 20). The other 26 are inside the -385 contract; on hgi_v7 / io_ft_v1 / phy_v1 the m includes a 80-120 ps kit tap window.
## What-if (min AND max of data - fclk; kits rerouted only by estimate, not a rebuild)
- Nearest tap: pv_v12 hold -650 -> -31, but max 161 -> 481; 38 of 53 exceed the receiver kit max input delay 166.6.
- Best tap within 290 um (KV-SENDER-SKEW-whatif.tsv): pv_v12 min -650 -> -50, max 161 -> 410 (2 > 390 about T/2; 32 > 166.6). hgi_v7 / io_ft_v1 max also grows (222 -> 267, 181 -> 247): moving them makes setup worse and they are not contract violations.
- kv3_phy_v1 not measured by a valid method (only leaf on clk_t9 is far; first phy result discarded).
- Discarded and not evidence: eco.tcl runs 1-4, eco2 phy_v1, and the pv_v6n ft0 leaf result.
## Row
- ROWS_KV-SENDER-SKEW.py d9eaf03a6470 (1895 exports / 89 types) is WITHDRAWN: blind nearest-tap moves break setup.
- PRE on A5 95c853437992 + row: 27 findings, same classes as A5 (only a name count 1512 -> 1516). Elab and strict bind REFUSED by PRE (base RSTREACH / DERIVEDNAME); not overridden.
## Next
1. Ruling on the setup bound (default: 166.6, the receiver kit max). Then pv_v12: near tap + a port launch station for rings over it (+1 cycle, LATCHECK).
2. Bind needs a base that passes PRE (ALLFIX A5r/A5s). FABLE order: sender row first, then seam values re-derived on the same compose.
3. PRECHECK STALE-EXPORT-TAP (source > 300 um with a nearer tap = FAIL) would push all 1461 pins to near taps: same setup hazard, die-wide.
