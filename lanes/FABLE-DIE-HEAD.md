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
