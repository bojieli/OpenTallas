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

## 02:3x state (LEP-PUSHDUP-1 in build)
- Row script: epyc7 /srv/opentallas-scratch2/claude/fable-unc-head/tmp/pushdup_rtl.py FILE (idempotent; rtl/dsrom_sys/s81_head/ot_s81hd_lep0N_split_tx_io_stages.sv ade1bb2fe54f -> 6a04159bb196; file is tree-only, not on main). Local copies: scratchpad/unch/{pushdup_rtl.py,pushdup_equiv.sh,eq_docker.sh,chain_unch_gate.sh}.
- Equiv (hub ot_s81hd_lep0N_noidx_hubc, E wrapper params, kit RTL of ep1 vs patched): intel2 ~/fable-unc-head/eq1.otrun.log, unit oth-ubuntu-4047734-1795429277 epyc7, out epyc7 D/eq/out (D=/srv/opentallas-scratch2/claude/fable-unc-head). PASS line = LEP_PUSHDUP_EQUIV PASS.
- Fork: intel2 ~/fable-unc-head/forkY7.sh -> epyc7 D/trees/s81_head_r18y_pushdup (from R9 r18w_ecol), log fork7_r18y.log (slow: disk load; R9's r18x fork also slow).
- After fork: `ot-run --priority plan --hosts epyc7 --no-spill --mem 24 --threads 4 --disk 5 --dir D -- bash D/tmp/chain_unch_gate.sh r18y1 > ~/fable-unc-head/chain_r18y1.otrun.log` (applies the patch, PRE vs base_r18t_ecol, bind, cohort, LATCHECK).
- Then probe: intel2 ~/fable-unc-head/launch_probe.sh yp1 s81_head_r18y_pushdup hd_lep0N epyc7 probe (unit unch-lep0n-yp1, goal grt, probe-through). A/B vs R9 ep1 (same plan, no patch): expect wn[1] -> rg3 txi gone.
- Class items: CLASS-FIX-RHI writes the HEAD die rows for RESET-ASYNC + IO-BOUNDARY (its TAKING post 02:16; my AGREE 9dd7f242). GRT-0273 handed to FLOW-OPS-R2 (d10c8eb7).
- Posts: CLAIM 34587e25, REPORT-1 821a9c26, ROW-DRAFT 9b91990b, AGREE 9dd7f242, HANDOVER d10c8eb7.
- rc138: e1 geometry shows die-clock reserved rects [805.2,651.2,813.7,654.2], [810.6,609.1,813.7,632.6], [825.8,634.5,828.3,656.9] beside rx_mem g_rx[3] bank[2] (x747-799): a 11-27 um slot. ECOL moved the macros; decide on ep1 census.

## 03:0x state
- EQUIV PASS: 168,059 compare points, 0 unproven (post 14130750).
- R9 changed course 02:55: ep1 FAILED at GPL (ECOL row bug, fixed), r18x fork abandoned, the event (r18x1 FAIL republish tie, r18x2 queued) is composed IN PLACE in R9 trees/s81_head_r18w_ecol.
- My fork r18y_pushdup finished (2419 s) but copied that tree WHILE R9 edited it (plan 3682da8c mid-state, no plan_r18w3.json): NOT gate-able. Do not gate or probe from it as is. Delete via ot-delete once not needed, or re-sync after R9's gate.
- Asked R9 (SendMessage a318dc59168bed8ac + post a2f0b1a9) to run pushdup_rtl.py on its tree before the r18x2 gate / ep2 probe, so ONE E probe covers ECOL + PUSHDUP. Waiting for its answer. Fallback: re-fork after R9's r18x2 gate PASS, chain_unch_gate.sh, own probe.
- Review note sent to R9: E per-port windows median 77 / max 131 -> W estimate still ~90 ps; W probe must report hold endpoints vs 17,932.

## 03:2x R9 TAKES PUSHDUP (reply to my SendMessage): after r18x2 it runs pushdup_rtl.py on trees/s81_head_r18w_ecol, re-gates as r18x3, probes ep2 from r18x3. R9 asked: NO separate fork/probe from me.
- ROWS-READY post eb245f19 (R9 + FIX-LEDGER). My fork r18y unused; ot-delete --dry SKIPs it as protected -> left for cleanup (47.5 GB, epyc7).
- Waiting (background waiter on intel2 ~/fable-fix-head-lep0n-1122/chain7_r9_r18x3*.otrun.log CHAIN_DONE).
## NEXT
1. On r18x3 gate: check PUSHDUP_ applied sha 6a04159bb196 in the tree, bind/cohort/LATCHECK PASS, WTAPOFF rows file (L/plan/rows_r18x*-WTAPOFF.json: window min/med/max), post review.
2. On ep2 (R9 unit r9-lep0n-ep2): CTS post-hook: wn[1] -> rg3 txi slack vs -179.76; GRT census: rc136/137/138/139 clusters vs 45,948 (PROBE-PASS rule fe8a2a5). Row for any surviving cluster, else COVERED. If ep2 cannot finish by 11:00: REASONED (equiv PASS + measured geometry) to FABLE-RC-KVHEAD.
3. REPORT-2 to COORD (<200 words) when every item is GATED or REASONED.
