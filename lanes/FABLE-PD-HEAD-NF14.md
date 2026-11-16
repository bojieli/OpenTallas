# FABLE-PD-HEAD-NF14: r199 review of HEAD plan event NF14 (A) / NF14r (B) / NF15pg

2026-11-16 13:30 PST. Technical PD only. MEASURED = I read the file or ran the tool. REPORTED = lane post.
Reviewed: (A) NF14 sha 40e5a7f6fa53, (B) NF14r sha f5fb75d218ef, both epyc7
`/srv/opentallas-scratch2/claude/fable-die-head/prep21z20NF14{,r}/prep`, sidecar aef151594c56. NF15pg = NF14r +
pg_pin_rule on 2 types (REPORTED), so everything said about (B) holds for NF15pg. The two wrappers that change
(ot_s81hd_lep0N.sv, ot_s81hd_ctl.sv) are byte-equal in (A) and (B).

## Verdict: ADOPT-WITH-SPLIT. Take (B) / NF15pg, not (A). Hold hd_lep0N until one row delta.

| goes in now (B / NF15pg) | next delta (NF15a), before hd_lep0N launches | later, per type |
|---|---|---|
| sideband rows hd_lep0N + hd_ctl; reserved sites on hd_host_e, hd_host_w, hd_serdes; la300 + stamped die tree | hd_lep0N: one status stage for lepk_o0 + move reset copy k49; hd_lep0N and hd_mesh reserved rects unmerged (fine sites) | hd_tile reserved sites after an off-count proof build; the other 12 signed types when they rebuild for another reason |

No BLOCK: no measured failure on a released type. The two hd_lep0N findings are on an open, unsigned type; a typed
hold on hd_lep0N until NF15a is enough. hd_mesh may launch on NF15pg (its strips are short), and takes fine rects
with NF15a if it has not placed by then.

## 1 Relay rows: reach is closed except one branch (MEASURED)

`head_sideband_audit.py` on the NF14r published wrappers, limit 405 um. Composer's "worst hop 369.9 / 356.0" is the
row tool's own path list; the audit of the built wrapper shows what is left.

| type | hops over 405 um, NF13b | NF14r | what is left |
|---|---|---|---|
| hd_lep0N status | 40 (worst 2,780) | 1 | `u_cland_agg_6` (1324.7, 10) -> `u_cland_up_lepk_o0` (1890, 137): **694.6 um in one cycle** |
| hd_lep0N reset of collect/start | 23 (2,464) | 1 | local copy `k49` (1442.9, 132.8) -> `u_cland_up_lepk_o0`: **453.6 um** |
| hd_lep0N start | 22 (1,515) | 0 | |
| hd_lep0N raw relay | in class D | 4 | 417.1, 434.3 x2 (estimated position), 494.4 |
| hd_ctl status / start / reset | 9 / 3 / 3 (931) | 1 / 0 / 0 | ring lepk_i0 -> `u_cland_agg_1` 437.1 um, estimated position |

Cause of the 694.6: `landing_status_input_stages` has rows for agg, coll_o0..3, ctrl_o0, fault_o0, lw_o and none for
lepk_o0. It is 1.72 x the reach, the same class as the -4,225 ps path. Fix (NF15a): one status stage for lepk_o0 near
(1620, 10) (two hops of about 300 / 400 um), and k49 placed within 405 um of the E-face pin (e.g. x 1755). Status
only, +1 status cycle, 0 data cycles. hd_ctl 437.1 is 32 um over on an estimated position: advisory, read it from the
placed DB.

LATCHECK 329/329, delta {}, bind PASS, cohort 26/26 on both shas (read from bindrun/nf14q, nf14r).

## 2 Reserved clock sites: not needed for die clock closure now; (A) is not worth 13 re-signs

- Die numbers do not move with the type rows. Stamped tree on NF13b without any type row (fdh_st) and on the full
  NF14 plan (fdh_nf14): kit PASS, GRT TT/FF exit 0, seam TT setup +654.88 / hold -80.60 / skew 91.21, identical to
  the digit. fdh_st count-aligned 427/427 (REPORTED by composer; the NF14 count-aligned result I did not read).
  The rows change type kits only.
- Coverage of the 45,076 die clock cells under partitions: (A) 45,061; (B) 3,274 (7.3 %); hd_tile alone 38,392
  (85.2 %); the other 12 signed types about 3,395 (7.5 %).
- **(B)'s hidden metal on hd_tile is real.** Signed hd_tile (b54b, 717.12, intel1
  `closed/s81_head/hd_tile__2dd0d8c9fd/base/6_final.def`) against the 197 rects (A) would reserve (3,237 um2):
  2,135 logic cells and 680 tap cells have their origin inside a rect, 146 of 197 rects hold a cell, 16,406 routed
  signal segments cross the rects (M2 4,779, M3 8,156, M4 1,173, M5 1,005, M6 727, M7 566), 184 of 197 rects are
  crossed, 12 are free. Times 264 instances. The die route units pass DRC only because the kit cuts the abstract
  there (16 windows per type, `abstract_cutout.json`). So the die DRC 0 on tile units is a statement about the cut
  abstract, not about the merged layout. It is not one of the four blocking gates today, and no die STA / GRT number
  depends on it.
- **(A) puts hd_tile at risk for that.** The fresh hd_tile build on NF13a without any reserved row failed today
  12:19 PST: GRT-0116, overflow 3, 4,493 gcells over 90 %, local density 0.757 (epyc10 kw43 `head_rp21z20NF13a/items/
  hd_tile`, 1 h 35 min to the failure). The signed record needed attempt 3 plus an ECO. (A) would add 197 M1-M7
  obstructions, displace 2,815 cells and reroute 16.4 k segments on that type, and stale the only signed hd_tile.
  Small types re-sign in about 50 min (hd_spn_eshim_tx 08:48 -> 09:38); hd_tile does not.
- So: opt-in is the right form. hd_tile takes the rows through a parallel off-count proof build (rows as fine
  sites, see 3) that must reach sign-off before the rows enter the plan; the signed b54b record stays counted
  until then. The 12 small signed types take theirs at their next rebuild; together they are 7.5 % of the cells.
- Each tree change moves the sites. Keep the stamped tree (`stamped_fdh_st.json`, la300) frozen as the HEAD die
  clock from this event on, or every clock edit re-keys the reserved types.

## 3 Congestion / pin access (MEASURED on the NF14r plan)

- No reserved rect overlaps a hard core or leaves the outline on the 5 types. hd_host_e (48 rects, 2.16 x 1.08),
  hd_host_w (100, up to 2.7 x 2.16), hd_serdes (100, up to 3.78 x 2.7): site-sized, no risk.
- **hd_lep0N: the merge to 289 rects makes M1-M7 walls.** 6,094 um2 reserved for 1,465 um2 of sites (76 % waste).
  - [1753.92, 210.06, 1756.62, 502.74] = 2.7 x 292.7 um, 8.64 um east of `g_pp[3].u_pair`: 648 core pins (M4 325,
    M6 323) face it. An 8.64 um channel holds about 315 M5 + M7 tracks before PG.
  - [913.68, 728.46, 916.38, 826.74] = 2.7 x 98.3 um, 8.2 um east of the rx_mem banks: 891 M4 pins face it.
  - [857.52, 598.32, 1010.88, 599.94] = 153.4 x 1.6 um across the centre street (110 of its 121 um).
  - 35 of 610 sideband stage / anchor / reset points sit on a reserved rect (e.g. agg_2 at (1049.05, 520.0),
    writer start stage (982.12, 600.0)); the placement blockage moves them, small against the 35 um hop margin.
  Fix (NF15a): emit hd_lep0N rows unmerged (628 rects of 2.16 x 1.08). The rect cap is not a gate (r197).
- hd_mesh: 225 rects, longest 47.0 x 2.7 and 2.3 x 34.0; 50 to 106 SRAM M4 pins face three of them. Routable round
  the ends; take the unmerged 633 rects in NF15a anyway.
- In (A) only: hd_spn 3,426 um2 for 1,043, hd_st_turn 3,963 for 1,145, hd_spn_wshim_rx 2,057 for 611 carry the same
  merge waste. Use fine sites when those types take rows.

## 4 Four table -1 lanes: acceptable (MEASURED)

coll_EN1_d / WS1_d / ES1_d: table 20, wrapper transport 19, delta -1. coll_HOST0_u: table 14, transport 13, delta
-1. `fixed_cycles: 1` sits in the core, so delivered = table. `fixed_in_core` = 12 (9 rows at -1, 3 at -2), 317 at
0. This is the form I asked for in FABLE-PD-HEAD-NF13b F1 (tables raised to 20 / 14).

## Not done

No build. hd_tile cell count uses cell origins (lower bound). The 694.6 um hop is geometry, not a timed path.
Count-aligned on the NF14 plan not read. hd_ctl kept its die_islands_um (not in the reserved set); not reviewed.
