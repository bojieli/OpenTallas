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
## 00:3x PST update (pv_v12 row draft; everything here is on A5 95c853437992 geometry, not A5s)
- Per ring (3 launch points, all 53): 22 o_* bus rings + ft53 launch at the port; 30 ft rings launch from the last station 345-389 um out (data 514-732 ps), so near tap alone gives d +200..+480. Placed S0 is ~31 um inside the face, so hop 0 is 3-160 um (slack is real).
- Row epyc10 /srv/opentallas-scratch2/claude/kv-sender-skew/ROWS_KV-SENDER-SKEW-PV12.py 26b81eb53c03 (cwd = private fork; env SS_EXPORTS=ss_exports.txt). Dry run: 53 repoints; 19 slots respaced at the same count; 11 slots +1 or +2 station (ft0 ft5 ft6 ft7 ft9 ft11 ft13 ft14 ft16 ft28 +1, ft10 +2); hops <= 385 um; tails <= 43 um, except ft57 (522 bits) 107 um. +1 lanes: L596 L1961 L1963 L1975 L1979 L1981 L1993 L1995 L2009 L2015, L1977 +2.
- Not done: post-fix m is a proxy (fstart launch at port), LATCHECK / join alignment not run, PRE and bind not run, ft57 likely needs its own siting.
- Waiter: epyc10 kv-sender-skew/wait_a5s.sh for A5s plan.json; then ot-tree-fork + row + PRE + LATCHECK + scoped bind (no PRE override).
## CORRECTION 00:3x PST (read first)
- WITHDRAWN: "io_ft_v1 ft3_o = kit SDC tap window, structural -7.8" and "m on hgi_v7 / phy_v1 includes window pessimism". FABLE 00:19: the TT probe mixed corners on hroot / io_cor / io_cor_v1 / io_ft / io_ft_v1 (ft3 -107.8 -> +80.6 TT); hgi_v7 / phy_v1 / io_ft_v1 ft0 is a real cross-tap window.
- io_ft_v1 rows in the census and what-if are invalid (two-corner kit). Re-measure with sender_margin_probe.sh. The census NO-DEFECT text is superseded.
- A5s runs on epyc11 (rt 7e0794724813); waiter epyc11 kv-sender-skew/wait_a5s.sh (the epyc10 one was stopped).

## STATUS 2026-11-24 04:03 PST
- Row v2 ROWS_KV-SENDER-SKEW-PV12-v2.py 32157b360983 (epyc11 /srv/opentallas-scratch2/claude/kv-sender-skew/) targets A5t5 (COORD), not A5t4. ROW-REBASED posted b9a250f44e1a.
- A5t3 evidence in kv-sender-skew/a5t3/: row_plan 0cfe7c6c6897, pv_col take a494038c27dc (pvcol_take.py, take.log), law2 identical, PRE no new pair (ENTRYFOOT pv_v12 58->5), scoped strict bind 0 errors / 0 R8 stale, seamhold_rings.tsv (53 rings).
- Open: LATCHECK on the A5t5 full bind (L1961/L2009/L2015 first); 5 pv_v12 exports outside census still stale (probe two-sided); SEAMHOLD -335.1 re-derive; after A5t5 binds: pv_v12 kit rebuild + TT/FF d_min/d_max via sender_margin_probe.sh.
