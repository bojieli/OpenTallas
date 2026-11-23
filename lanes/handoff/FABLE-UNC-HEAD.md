# FABLE-UNC-HEAD (Fable, started 11-23 01:48 PST; resumed once after an API 529) uncovered hd_lep0N items for HEAD r18 (cut 12:00, GATED by 11:00)
Brief: scratchpad fable_uncovered_brief.txt + rules.txt. Local scratch: scratchpad/unch/. Host scratch: intel1 /srv/opentallas-scratch2/claude/fable-unc-head/tmp.
Owner/plan lane OPUS-FIX-HEAD-LEP0N-R9 (event candidate r18x1 = epyc7 L/trees/s81_head_r18x_event, L=/srv/opentallas-scratch2/claude/fable-fix-head-lep0n-1122). Reviewer FABLE-RC-KVHEAD. Ledger lane FIX-LEDGER. Class lane CLASS-FIX-RHI (reset/hold/IO). GRT-0273 -> FLOW-OPS.
Host clocks differ (epyc9 shows +1 h); use intel2 `date` (PST).

## Items, cause, row (01:5x-02:1x)
- rc140 E setup wn[1] -> rg3 txi -180. MEASURED (e1 4_cts geom + 1_synth_odb.v fanout trace): each ot_s81sl_lep_tx_push gate (g_push_groups.g_group[c].u_push, keep) is ONE gate shared by 4 consumers: rg0 txi v_o (E), u_bout_o_h2r1_p + o_h2r2_p (W cut face x 4-10) and rg3 txi v_o. Placement puts all 22 gates at the W edge (x 20-90, y 710-830); the hub wopen (401,580) goes 520 um W to the gate and 400 um back E to rg3 txi (466,636). A TXI stage cannot fix it (the detour is before stage 0). ROW = LEP-PUSHDUP-1: per-lane copies of the push gate in the HEAD lep core (generator tools/s81_head/head_lep_nr_sources.py), 0 cycles, combinational duplicate.
- rc130 / census P1 P2 (setup CLOCK-SKEW) / P15 / P16-P19 (RESET-ASYNC hold): one cause = flat 200 ps tap window on W (constraint.sdc: set_clock_latency -source -early -200 on all clk_t ports; launch 247 vs capture 456 on a reset leaf and the flop one INV away). Row = R9 LEP-WTAPOFF-1 (+ LEP-PAIRTAP-1 lead 210); I review it in r18x1 and read the probe.
- census P20-P23 IO-BOUNDARY hold (fclk_in_coll_iN port -> ring, fclk insertion 136-204 vs input min 80): class owner CLASS-FIX-RHI; asked who builds.
- census C1/C3 (x262-403 y644-645, CLOCK-TAP, M3): reserved sites = HEAD-DCLK-SPLIT-1; verify on r18x probe. C2 x691-724 y1376 (128): check on probe.
- rc138 E stripe x810 y650-660, rc136/137/139: read from R9 probe ep1 (r18w3, unit r9-lep0n-ep1, epyc7), census with hotspot_census.
- GRT-0273 x25 in 4_2_tapbal_grt -> FLOW-OPS.
## Posts
- CLAIM 34587e25 (01:5x).
## NEXT
1. LEP-PUSHDUP-1: lane clone, generator patch, regen, sim/equiv, apply on r18x tree, gate, E probe.
2. ep1 census read. 3. r18x1 review of WTAPOFF/PAIRTAP. 4. reports (1) and (2) to COORD.
