# HEAD-EAST-REPLAN (Opus 5.5) handoff - East hd_lep0N re-plan, taken from HEAD-R18 11-24 01:2x PST
Scope: FABLE-RC-ALL East causes E1-E5 (hub db04d916). HEAD-R18 keeps tie audit + E-W seam. HEAD-WEST owns hd_lep0N_w.
Lane dir: epyc11 /srv/opentallas-scratch2/claude/head-east-replan (clone/ = lane clone, rd/ = read-only analysis of the rscap 4_cts.odb copy, tmp/, inputs/, trees/).

## Findings (rscap 4_cts.odb, post-hook, epyc11 rd/out)
- E1/E2 = unbuffered nets made by tap_reset_split (copies placed after the placement repair_design). E1 u_srl_302 -> u_rrl_303 copies 655 um, slew 2906, -468.7; E2 u_rstr root -> 115 RESETN loads, slew 2800, -785.8. repair_design -max_wire_length 300 on the DB: 0 reset endpoints < -42 (1891 buffers). Remaining 78 data endpoints -157 (rx[2] addr_nz -> rx[3], mtx.wn[5] -> rg3 tx), pre-repair.
- Tool LEP-RSPLIT-REPAIR-1 pushed: main 9dbd20ffb17b (clock.tap_reset_split_repair -> OT_TAP_RESET_SPLIT_REPAIR; repair_design after the split). rt 9dbd20ffb17b carries it and 4676043.
- Seats: 10 stale keys (g_leaf 32/33/53/56-60/62, u_rstr g_local[1]) not in the netlist -> dropped (row S).
- E3 FF (pre-repair): pair-in hold rg0 +63.9 / rg3 +13.1, pair-out rg0 -1.05 / rg3 +41. Lead row L (+~54 ps on the core pins) predicts rg3 pair-in ~-41 (k_lo_d) -> hold repair or rg3 pair-in bank follow, measure in the probe.
- E4a K-shelf: rx SRAM 32x128 pins are on W/E edges (M4, ~195 each) and banks sat 2.4-3.6 um apart, so facing pins shared one gap: V congestion. 0 through-nets in the window. Row K (LEP-KSHELF-1): rx bank gaps 17.3-21.6 um, rx[2]b2 -> row y712, 20 banks moved, 0 collisions with taps / die_clock_tree sites / seats / sinks. Render: scratchpad east_kshelf_before_after.png (to be posted with the probe).
- E4b (x980-1000 y360-400) is in epin_r4 only (rscap 4 markers): not carried (rscap base).

## Rows (plan prep_east_r1 = rscap a0b11fee2817 + S/L/R/K), chain tmp/chain_east_r1.sh -> bind_east_r1/
## Next: chain PASS -> private-spec kit (template intel2 ~/fable-fix-head-lep0n-1122/r18g_exact_continue/east-rscap/run.sh) --host epyc11 --rt >= 9dbd20ffb17b --goal grt; renders before counting.
