# FABLE-DIE-HEAD: NF15f whole-die review, tree2 proof, M8 lock, hd_mesh (2026-11-17 23:15 PST)

MEASURED = my run or my read of the file. REPORTED = lane post. Plan = live tree `..._t86a9d26_d1_t58211f4_t30393b4`
`prep/NF15f/prep/source_plan.json` sha de6c7105. Clock = HEAD-PLAN-R4 `clock_rs8/tree2/kit` (copy, read-only).
Lane dir: epyc10 `/srv/opentallas-scratch2/claude/fable-die-head` (proof `base/head/nf15f_t2`). Older review (11-16) is below.

## 1 Verdict

| item | number (MEASURED) | verdict |
|---|---|---|
| die route, HEAD form (combo: signals M4-M7, clock M8/M9) | TT and FF: overflow 0 / 0 / 0, usage 0.37 %, 90 s | good |
| the "tree2 die GRT" that has run since 20:05 (`run_grt.sh`) | iteration 19/50 after 2 h 45; my 1-iteration copy: congestion 785,400, 19,477 of 20,000 listed gcells have capacity 0 | wrong runner, stop it (row R1) |
| tree2 routed clock proof | 13,122 taps, 0 missing; TT intra setup +572.0, seam +656.0; seam kit contract +9.08 (W 90, need 80.92) | same as NF15c |
| kit windows vs tree2, whole set | 14 types have ports over their plan window; hd_tile 43/43 ports (excess up to 90 ps), hd_spn 40/42 (73), hd_lep0N 163/195 (73), hd_spn_end 64/68 (53) | stale table, advisory; fix for open types (R2) |
| hold on real views | 0 of 585,476 pairs measured (no signed view loaded in my run) | not done (section 7) |
| M8 grant lock, tree2 route vs frozen guide a8dcf2f5 | 4,321 die tracks on granted type tracks in 14 types; hd_tile 1,069 | BAD (section 4, R3) |
| hd_lep0N bands, plan_grown2 (sha 34044fc3) | 11 rects + 5 reader boxes: 0 overlap with cores, SRAMs, other bands, outline; 1 reserved clock site inside rid_low | ADOPT (R5) |
| third open type | hd_mesh (hd_tile is signed: `hd_tile__nf15c_tp2_land1_1117`) | I own hd_mesh (section 6) |

## 2 Die route

- `run_grt.sh` is the die_trial signal-only script: M4-M7 at 25 %, M8/M9 at 0 %, laid over 19 real signed views whose own
  routing already fills M4-M7. The ft pins then sit in gcells of capacity 0. HEAD was never judged on it: NF13b, NF14 and
  NF15c were all judged on the combo GRT (`proto_die.sh`, M7 at 100 %, M8/M9 at 60 %, clock routed in the same run).
- Per type of the 20,000 listed gcells: hd_turn_b 22,858, hd_tile 20,393, hd_spn_wshim_tx 17,249, hd_turn_a 15,838,
  hd_lep0N 305. It is die-wide and not an NF15f effect.
- Combo on tree2 (`run_t2.sh`, unit oth-ubuntu-1931525-1794984025): 0 overflow on M4-M9, M8 usage 0.68 %, M9 0.39 %.
  The corridor x 880-1160 / 1230-1472 is inside hd_lep0N and is not a die-route item.

## 3 Clock windows on tree2 (routed, `kitwin.json`, need = late(q) - early(p) - CPPR, whole set)

| type | ports | need max / p50 | plan per_type, per_port range | ports over | worst excess |
|---|---|---|---|---|---|
| hd_tile | 43 | 113 / 88 | 130, 22-38 | 43 | 90 |
| hd_spn | 42 | 88 / 48 | 70, 12-19 | 40 | 73 |
| hd_lep0N | 195 | 163 / 111 | 200, 10-108 | 163 | 73 |
| hd_spn_end | 68 | 66 / 48 | 44, 10-23 | 64 | 53 |
| hd_ctl_n | 14 | 58 / 45 | 40, 15-27 | 8 | 35 |
| hd_serdes | 22 | 84 / 54 | 50 | 15 | 34 |
| hd_ctl | 65 | 77 / 32 | 44, 10-44 | 16 | 33 |
| hd_mesh | 83 | 84 / 51 | 83, 37-83 | 20 | 31 |

Six more types are over by 1-23 ps; seven are inside. The placement-RC "63 ps span" of lep0N is not the window need: the
routed need includes the late/early range and is 163 ps whole-set.

hd_mesh, related pairs only (566 data-carrying tap pairs of 6,806, `kit_tap_related_pairs.tcl` on the wave 4_cts.odb):
mean window need 36.6 ps against a plan mean of 61.6; 9 ports need MORE than the plan gives (clk_t63 84 vs 56,
clk_t54 71 vs 50, clk_t47 65 vs 43). So the table is too wide on 70 ports and too narrow on 9.

## 4 M8 grant lock (tool of record `m8_grant.lock_check`, union over instances)

Types route on the M8 tracks the frozen die guide a8dcf2f5 left free. tree2 is a fresh GEN and its M8 clock legs cross the
types in other gcell rows. Die tracks of the tree2 route that land on granted type tracks:

| type | state | granted type tracks | tree2 die tracks on them |
|---|---|---|---|
| hd_lep0N | open | 8,486 | 1,296 |
| hd_tile | signed, 264 inst | 7,209 | 1,069 |
| hd_mesh | open, in route | 6,755 | 512 |
| hd_st_turn | signed | 6,915 | 361 |
| hd_serdes | open | 1,525 | 336 |
| hd_turn_b / hd_turn_a | signed | 5,995 / 8,789 | 175 / 150 |
| hd_st_str | signed | 2,758 | 167 |
| hd_spn, eshim_tx, eshim_rx, wshim_rx, mesh_e, wshim_tx | signed | | 65, 65, 55, 45, 16, 9 |
| 12 other types | | | 0 |

Signed hd_tile really uses M8: 173 segments on 107 tracks, 13.2 mm (`6_final.def`). 62 of those tracks (7.0 mm of wire)
are tracks tree2 claims in at least one of the 264 instances. The die GRT cannot see this: the hd_tile view LEF has no
M8 OBS. The plan still names guide a8dcf2f5, so every kit built today (hd_mesh, hd_lep0N, hd_serdes) gets the old grant.
Decision: the die keeps the contract. The die clock route must stay on the die's own tracks; types do not re-sign.
Proof run t2g (combo GRT with the granted type tracks as 165,298 M8 obstructions over all 358 instances): INCONCLUSIVE.
The guide is byte-identical to t2 (sha 8d0b6462), so the obstructions did not move one clock leg: a 10.8-um gcell holds
135 M8 tracks and GRT cannot enforce a track contract. The lock FAIL stands unresolved. Next test: per instance, tree2
M8 clock boxes against the signed M8 shapes (hd_tile first, 62 tracks), or a die clock detailed route on the real views.

## 5 hd_lep0N bands (r681)

plan_grown2 changes only `native_stage_groups` rect_um (14 entries, 11 rects) and adds `box_um` on 5 reader-start stages.
No rect touches a lep_pair core, an SRAM, another band or the outline. Nearest core edges: wdq_bank3 0.86 um above the
lep_pair top (y 509.76), mlwd_h1 1.01, pout_s0 1.03, rid_low 1.06. wdq_bank3 holds 14 full rows (3.78 um of its 4.0),
so its real fill is about 0.61 on the 395 um2 need, not 0.58. NOT CHECKED: the core placement halo in the kit; if it is
1 um or more, wdq_bank3 loses 1 row (fill 0.66) and still passes. rid_low now covers 1 reserved clock site (blocked, fine).

## 6 hd_mesh (I own it to sign-off)

- Not waiting on hd_lep0N or lep_pair. Wave route unit `hd_mesh-route-renewed-glider-4069487-1794979630` (epyc9), started
  21:27 PST on tree 2e1bef7c, now in pre-GRT hold repair.
- At CTS: TT -49.56 after repair (gate -42, placement RC); FF hold -125.74 on 17,123 ends: cross_tap 11,732, port_in 4,209,
  same_tap 1,026 (-72.6), port_out 157. Tap insertion 399..462 ps. Structural limit -183 = 83 window + 90 contract + guard.
- Same class as hd_lep0N: the cross-tap ends are priced with the stale one-sided windows. This attempt also carries the
  old M8 grant (512 tracks, section 4). It runs on as the timing read; the build that can sign is the one after rows R2/R3.

## 7 Rows

- R1 FABLE-FIX-HEAD-LEP0N: stop unit oth-ubuntu-2990167-1794974744 (epyc9, tree2 `run_grt.sh`). Use the finished proof
  epyc10 `fable-die-head/base/head/nf15f_t2/proof` (tap_arrivals_TT/FF.json, plan de6c7105, inv). Command, as `run_rel.sh`:
  `die_sta_related.py PROOF --plan PLAN --out OUT --corner TT --corner FF --core-insertion declared --cppr-lca --clock-cell inv
  --kit-window-related related_hd_lep0N.json --kit-window-out kitwin_rel.json --kit-offset-out kitoff.json` (75 s).
- R2 HEAD-PLAN-R4, next pack: `clock.tap_window.per_port_ps.hd_mesh` = `lanes/handoff/FABLE-DIE-HEAD-per_port_hd_mesh_related.json`
  (83 ports, need + 10, floor 10, cap 83; mean 46.4, was 61.6; includes clk_t79..t82, which the plan table lacks).
  hd_lep0N takes its table from FABLE-FIX-HEAD-LEP0N the same way. Do not copy my whole-set table into the plan.
- R3 HEAD-PLAN-R4: no change to `type_m8_grant.guide` yet. It waits for t2g. If t2g passes the lock for the signed types,
  the pack takes the t2g guide for the open types only; I post the file and the sha.
- R4 HEAD-PLAN-R4: plan_grown2 ADOPT as is.
- R5 mine: real-view die STA on the tree2 proof (23 signed views) so FF hold is measured; t2g; hd_mesh second build after the pack.

## 8 Not done

No real-view hold. No related-pair table for hd_lep0N (its related set is with FABLE-FIX-HEAD-LEP0N). The lock is a
union-over-instances count; I did not test hd_tile shape by shape per instance. PHY region: hd_serdes whole-set need 84 ps
against its 50 ps window and 336 lock tracks are the only die-level PHY findings; no PHY rail or bump check was run.
No repo code changed, so no branch or gate.

---

# FABLE-DIE-HEAD: s81_head whole-die PD verdict and plan event NF14 (2026-11-16 08:45 PST)

MEASURED = my run or my read of the file. REPORTED = lane post. Lane dir: epyc7 (and a copy on epyc9, disk full there)
`/srv/opentallas-scratch2/claude/fable-die-head`; tools = v2 tree `src_head_pin_eb1e73448bd0_d1/tools`; plan = NF13b
(HEAD-100 `dr/plan13`, sha b1bfab61a590, asset paths rewritten to the lane). Render: localhost scratchpad `fdh/die_nf13s.png`.

## 1 Verdict

The floorplan, the die route and the forwarded-clock architecture are sound. Three die-level structures are bad:
the lep0N region tree, the unstamped clock sites, and one-cycle landing sideband reach in hd_lep0N and hd_ctl.
None needs a core reshape or an outline change.

| item | number (MEASURED, nf13s = HEAD-100 chain on NF13b) | verdict |
|---|---|---|
| floorplan | 358 partitions, 26 types, fill 0.901; 468 of 468 ports abut (gap 0); 95 channels | good |
| die GRT, TT/FF, 50 it | overflow 0 on M4-M9, usage 0.38 %, 52.5 m wire, 92,923 nets | good |
| die route units | 143 of 144 MY units DRC 0 (REPORTED HEAD-100 table) | good |
| clock insertion | taps 830..7,001 ps TT, 173 stages max, feed hk6 | accepted (count-aligned) |
| count-aligned crossings | not run by HEAD-100 on NF13b; my run: 427/427, depth 4 on 427 | pass, section 3 |
| lep0N region tree | FF tap spread 271.6 ps (next worst type hd_tile 98.8); 53,553 contract violations | BAD, fix A |
| clock cells vs type islands | 44,493 cells under partitions, 1,611 on a declared island, 42,882 not (hd_tile 37,705) | BAD, fix B |
| seam, declared-budget form | TT hold -80.6 / 5,564 pairs, FF -83.3; contract form +9.08 margin, 0 negative | advisory, unmeasured on real views |
| real-view hold | 0 of 585,476 pairs measured (26 types "missing view" in die STA although 18 closed views are in the kit) | open, fix D |
| sideband reach | hd_lep0N status hop up to 2,780 um, start 1,515; hd_ctl status 931, start 840 | BAD, fix C |

## 2 Sideband audit (lever C), all 26 types

Tool `sb_audit.py` (lane dir): every ready/fault collect, FSTART/reader/writer start relay and raw reset copy in the
published NF13b wrappers, pin-to-pin Manhattan from plan pins, stage rows, anchors and relay comments. 6,400 hops.
Over the 405 um plan reach: 122 hops (table `lanes/handoff/FABLE-DIE-HEAD-sideband-405.tsv`).

| type | class | hops over 405 | worst um | worst hop |
|---|---|---|---|---|
| hd_lep0N | status | 40 | 2,780 | ring coll_i2 -> u_cland_up_lw_o |
| hd_lep0N | raw reset of collect/fstart | 23 | 2,464 | u_cland_rst_lepk_i0 -> u_cland_up_coll_o1 |
| hd_lep0N | start | 22 | 1,515 | origin -> u_cland_fstart_coll_o1 |
| hd_ctl | status | 9 | 931 | ring b7_rx_i -> u_cland_up_lepk_o0 |
| hd_ctl | start | 3 | 840 | origin -> u_cland_fstart_b7_tx_o |
| hd_ctl | raw reset | 3 | 842 | u_rrl_5 -> u_cland_fstart_lepk_o0 |
| 10 other types | raw relay to relay | 22 | 623 (hd_st_turn, estimated position) | 428..623, 8 of them on estimated positions |

hd_lep0N has no `landing_reader_start / writer_start / status_input_stages / status_anchors / local_resets` row at all;
hd_ctl has only `landing_reader_start`. The other 22 types with rows are within 405 um on status and start. The
-4,225 ps path of HEAD-TYPES-O (coll_i0 fault -> coll_o1) is one of the 40. hd_serdes, hd_turn_b, eshim_rx: clean.

## 3 Proof runs (ot-run, epyc9 then epyc7, v2 _d1 tools)

| run | clock | GRT TT | FF intra spread / contract need | seam FF | count-aligned TT lo / FF lo |
|---|---|---|---|---|---|
| nf13s (HEAD-100) | hk6 | 0 overflow | 271.6 / 271.6, 53,553 viol | 80.9 | not run |
| fdh_base | hk6 + `actual_max_region {lep0N: 300}` | 0 overflow | 128.6 / 98.1, 44,179 viol | 80.9 | 204.9 / 132.3, 427/427 PASS, plan margin 106.8 |
| fdh_st | fdh_base + stamped tree, 14 multi-instance types | 0 overflow | 128.6 / 100.3, 52,790 viol | 80.9 | 190.7 / 127.3, 427/427 PASS, plan margin 106.4 |

Both: bind OK (18 freg ports), start-skew fail 0, start hops over 405 um 0, depth 4 on 427. The stamp costs 14 ps of
TT margin and adds 8,611 advisory contract violations; it does not change seam or landed numbers. The landed T/2 row
in sta.log (-855 ps) is the wrong check for count-aligned rings (FABLE-PD-HEAD-CLK) and is not a result.

## 4 Plan event NF14 = NF13b + rows A-C (one event, re-gate on the v2 tree)

- A. ot_clk config: `region.actual_max_region: {lep0N: 300}`. Config only. PROVEN (fdh_base).
- B. Die clock = stamped tree (`ot_clk extra_argv --tree-json`, built by `clksite_stamp_native.py` in the order of
  `run_st.sh`). PROVEN through kit, GRT, STA, count-aligned (fdh_st). `clock.die_islands_um` for the 14 multi-instance
  types then comes from this tree. NOT DONE: one site set per type is not measured on this tree (CLKSITE reported 39
  sets for hd_tile); the island rows wait for that count.
- C. Sideband rows, existing plan keys only, 0 data cycles (files `lanes/handoff/FABLE-DIE-HEAD-sbrows-<type>.json`):
  - hd_lep0N: hub at (1140, 600) in the centre street; `landing_status_input_stages` per ring, `landing_status_anchors`,
    sidecar `local_status_depth` coll_o0 4, coll_o1 6, coll_o2 5, coll_o3 4, ctrl_o0 4, fault_o0 5, lw_o 5;
    `landing_reader_start` depth 4, `landing_writer_start` depth 4. Worst hop 349 um along streets round the four
    lep_pair cores. About 384 flops. Status seen up to 11 cycles later, boot +8 cycles.
  - hd_ctl: hub (20, 300); `local_status_depth` a_tx_o 4, b7_tx_o 4, h_tx_o 3, lepk_o0 2, x_o 3; reader depth 2 (as
    today), writer depth 2. Worst hop 363 um, about 114 flops, boot +4.
  - NOT DONE: gen, bind, LATCHECK on these rows; `landing_local_resets` for the new stages (HEAD-100's
    `head_cland_stage_delta.py` computes them and checks depth; add both types to its TYPES list).
- D. Next, not in NF14: load the 18 closed views in die STA so hold is measured; raw relay hops 428..623 um in 10
  types (reset_tree rows) after their positions are read from a placed DB.

Type lanes: hd_lep0N and hd_ctl rebuild on NF14 (both are open and unsigned today). No signed type changes in A or C.
B re-keys the islands of the multi-instance types when its rows land; hd_tile is owed a rebuild at 717.12 anyway.

## 5 HEAD totals 5/5 + 26 -> 4/4 + 25

No core or type was dropped. The counter fell back to the pinned plan l48uo (25 types with the unsplit hd_host, 4 core
designs, no he_epc). Cause: kit_wave.json `plan_sha256` is 810a66fa536a, but the in-tree copy the wave now points at
(`_d1/physical/die_plan/s81_head/prep/NF13a/source_plan.json`) hashes ddebc47fddd3: 14 asset paths were rewritten into
the tree, nothing else differs. `stage_host_plan` rejects the sha, so PLAN DRIFT counts l48uo. The in-tree plan has 26
types and 5 core designs. Fix (KIT-OPS-5 / TOOLS-CONVERGE): set `plan_sha256` to the in-tree file's hash.

## 6 Not done

No lane clone or branch: no repo code changed (sb_audit.py / sb_rows.py are lane scripts, not gated). NF14 is not
composed or bound. Droop / OCV on the die clock not run (nominal policy).
