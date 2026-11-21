# S81-J6-ASSEMBLY handoff (started 2026-11-20 17:50 PST)

Takes over J6 build/prove/apply from S81-DIE-R4 (cut 11-21 13:00). S81-DIE-R4 keeps J5 ops (post-apply bind, leaf reps, svc_rs MPL watch, holds).
Inputs read: lanes/handoff/S81-DIE-R4.md, FABLE-CLOSURE-STRATEGY 17:30 + 15:15, FABLE-PD-S81-1100.
Hub dir: intel2 /srv/opentallas-scratch2/claude/s81-j6-hub (logs, scripts).

## J6 item status (priority order)
1 source+tools adoption (main source, hwin 8e20268b5d83 + reach row, RIP1 + lepe rows 1-4; tools re-pin 8e9cdd615c/ecd0239bd5/f02ccd50eb/25fc65d0cb1): OPEN
2 monitor-pin rows (S81-MONITOR-PIN-1745, 29 types) + item 9 relays (fallback 405 die-top hop): OPEN
3 donors f0_q, rom, r1_frame, t31, vp_sr SRAMREG (+real ho sites, VP cycle in compiler table, 79 types): OPEN
4 col masters routed w/ launch-leaf latch: OPEN
5 leaf reset legs (reset_leg_plan.py on J6 bind): OPEN
6 per-lane spread rows + slice C finish leg (S81-SLICEC-R3): OPEN
7 bk_sel rows (OPUS-FIX-S81-BKSEL-R3): OPEN
8 svc manifest delta (FABLE-FIX-S81-SVC-R3): OPEN
9 leaf class rows (S81-LEAF-CLASS-1730) if green else J7: OPEN
10 lockup rows only after LOCKUP-STATION-1130 proof2 re-solved taps: OPEN
Gates: regression census vs J5 (monitor pin dist, hops, reset legs); private strict bind 0, LATCHECK, G0 no new over J5; apply.

## 11-20 18:30 state
- Work root epyc10 /srv/opentallas-scratch2/claude/s81-j6/ : clone/ (lane clone, main abfa72731be0 = rt current), mk_tree.sh (rsync link-dest of
  J5 tree kw45/s81_j5_existing_clock_r4_1120/tree, tools from rt/<sha>, TOOLS_RT_SHA file), adopt_rtl.sh, gate.sh (rt_pin; strict --all-gaps,
  LATCHECK + latcmp vs J5 gate_r5_repair, G0 + g0cmp vs J5, PRE), gates/<name>/, logs/gate*.log.
- treeA = J5 plan/rtl + rt abfa727 tools (tools control) -> gate A_tools_control RUNNING (epyc10 ot-run 108 GB).
- treeB = treeA + rtl adoption (adopt/classify.tsv: 76 MAIN_OLDER files -> main, 115 main-only added, 24 J5_PRIVATE overlays kept;
  vp CFX is opt-in/off, so the J5 vp overlay stays) -> gate B_rtl_adopt QUEUED.
- Donor deltas (plan_delta.py format) epyc10 s81-die-r4-donors/<d>/j6_delta_<d>.json: rom 60 types, vp_sr 79 (+manifest define/reproof), r1_frame 1
  (needs schema 8e9cdd615c: in rt), t31 1. f0_q: J5 dir plan_j5_f0_q_date_private.json / gate_f0_q.
- epyc8 j6_lockup: hop.tcl client cancelled (input ODB deleted), 2 echo-LEC waiters killed (PIDs 95864/96446); r1 midpoint masters not routed (stop list).

## 11-20 19:55 state
- Gates A (tools control) and B (rtl adoption): strict bind 0, LATCHECK 0, LAT diff vs J5 0; G0/PRE pending in logs/gateA|B.log.
- mk_cand.sh TREE LIST (epyc10 s81-j6/): mk_tree + adopt2 (ADOPT-DIFF LAG carry, BOTH via decisions.tsv) + ROM sidecars + FILE lines + merge_deltas.py
  (refuses same-path/ancestor conflicts) + manifest ops (list union when two deltas set one key, e.g. /defines). SKIP_TREE=1 resumes, RT=<sha> overrides.
  census_c.sh TREE = plan_geom_census + event_adopt_diff + event_census vs J5.
- candC1 (rt 1ddefd55818e; cand/c1.list: rom r1_frame t31 f0_q lepe slicec serdes-noregion, 195 ops; plan 2dcd5fad): census HOP 9761/384, RESET_LEG 522/82,
  CORE_WIRE 1254/63; ADOPT-DIFF LAG 0, ledger missing bksel-l4-define only; EVENT-CENSUS REGRESS 0. gate C1 RUNNING (logs/gateC1.log).
- candC2 (rt 42eeacf87f79; cand/c2.list = C1 + vp_sr (rows/vp_sr, real sites) + svc H8 (rows/svc, needs ELAB) + item9 (rows/item9 /clock /reset);
  460 ops, dry merge clean): c2chain.sh = compose -> census -> ot-run [elab.sh + gate.sh C2]. logs/mk_candC2.log, census_candC2.log, gateC2.log.
- Pending rows: CBC300 (rows/cbc300, fork running), iq_C + eng registered reads (rows/iqc_eng, fork running), monitor-home rows (S81-MONITOR-PIN-1745),
  bk_sel (OPUS-FIX-S81-BKSEL-R4), core-pin relays own-tap form only (CORE-PIN-RELAY-1930), reset legs (reset_leg_plan on the J6 bind, alternate edge from
  RESET-RELAY-GEN-R2), lockup (S81-DIE-R5). Dropped: seqhost u_win region (no member count), slicec finish (bind risk; next compose).
- Apply: reuse intel2 s81-die-r4-hub j5_chain2.sh / j5_apply3.sh; set kit_wave tools_sha to the J6 rt sha via kit_wave_edit after one bound-type proof gen.

## 11-21 00:1x PST STATE (S81-J6-ASSEMBLY stands down; the successor takes the gate reads and the apply)
Work root: epyc10 /srv/opentallas-scratch2/claude/s81-j6/. The C1d gate result is the current GREEN fallback evidence.
Scripts:
- chain.sh NAME LIST RT ELAB: compose -> census -> ot-run --priority plan [elab] + gate.
- mk_cand.sh: mk_tree, adopt2, ROM sidecars, FILE lines, HOOK lines, merge_deltas, manifest ops with list union.
- gate.sh: strict --all-gaps bind, LATCHECK + latcmp, G0 + g0cmp vs J5, PRE.
- census_c.sh: geom, adopt-diff, event census.
- lanefix.py: lane fixed_cycles = source stations + max receiver stations.
- mhdelta.py / mhver.py: monitor-home delta builder and verifier.
- rtpin/: hardlink copies of rt 93b5c482240d and 2ddb19c08ba6. Both are reaped from rt/; gate.sh and mk_tree fall back to rtpin.
- ADOPT_MAIN=a4fc295c2a05: export it for every compose. A plain fetch moves refs/remotes/origin/main.
- Logs: logs/{mk_,census_,gate_}candNAME.log and gates/candNAME/.

### Candidates
- C1d GREEN (fallback base). rt 93b5c48, plan 87b70a00, manifest 72bb2fb3. Contents: rtl adoption, rom, r1_frame, t31, f0_q, lepe (RIP1 + rows 1/3), slicec_v2, serdes-noregion, lanefix (76 lanes). Gates: bind 0, LATCHECK 873/873 (78 lanes with intended +cycles), G0 87/87 inherited, 0 new, PRE PASS. Leaves monitor pins at J5 values (62 types over 300 um).
- C1n = C1d + monitor-home (FALLBACK to apply). List cand/c1m.list, rt 93b5c48. Delta rows/monhome_c1d: 70 seats plus the gunit pin slide, with its sidecar. MONITOR-PIN 0 types over 300 um, max 280.1. Census HOP 9,761, REGRESS 0. Gate unit oth-ubuntu-152516-1795245393, chain PID 120582. Inputs sha 44be6051 / 72bb2fb3.
- C3c = C2d + lepe/f0_q fixes + ROM pval + monitor-home + leaf relay_sites keys + reprove39. List cand/c3a.list, rt 2ddb19c08ba6, elab + gate. Inputs sha 7ea453a3 / b08acfc8. Gate unit oth-ubuntu-207147-1795245549, chain PID 177099. Census HOP 7,294, RESET_LEG 519, MONITOR-PIN 0 over 300, REGRESS 0.
  - C2d = C1d + vp_sr SRAMREG real sites + svc H8 (defines union 39) + item 9 die reset/monitor relays.
  - lepe/f0_q (rows/lepe_f0q/j6_delta_lepe_f0q_v2.json): replaces the f0_q and lepe deltas. All 7 regression rows and the land reset legs are at 300 um or less, with the D4 land reset and u_rstr sited. The f0_q type also carries the ROM pval rows.
  - ROM pval (rows/rom_pval): one rising stage per qbank input, 5.3 um off the ROM edge. That is 1,728 pairs on 216 col_h* types, +1 internal-pipe cycle. r1_frame is replaced by r1_frame_rompval.
  - leaf keys: rows/leafkeys, 47 types, 1,175 keys.
  - reprove39: the svc proof under the 39-define union.
- C3d = C3c + FSTART (rows/fstart, 182 types, 735 legs -> 0, 0 cycles; svc 16 types not covered) + CFX (rows/cfx: 75 leaf types, HOOK apply_overlay.sh, reprove40, manifest defines 40). List cand/c3.list, chain PID 407736, composing at handoff. This is the PREFERRED APPLY if green.
- Kept OUT of J6:
  - CBC300 station pass (rows/cbc300 README; J7 after a kit proof);
  - core-pin relay rows (wait for the CORE-PIN-RELAY-R2 A/B);
  - leaf class rows and reset_legs_PROVISIONAL;
  - root_entry_negedge (held per FABLE-CLOSURE-2130; rrgen-r3 delta);
  - eng relay_sites (the -766 ps side; J7: u_e hx_res D 1->2 and the u_e MX->R0 rotation);
  - iq_C WCOPY (its proof is not passing in the J6 tree);
  - bk_sel L4 (only if S81-BKSEL-R5 reports by 09:00);
  - lockup rows (proof4);
  - tap-grid;
  - seqhost u_win region (no member count);
  - the 8 J5 col lane-FIFO relay_depth rows (464-480 um, J7);
  - svc FSTART legs (J7 or a retry);
  - ROM pval falling-edge form (needs a relay_depth edge option, J7).

### Successor steps
1. Read the gate results.
   - Expected failure classes: the stale dead-input defines check (the proof define list must equal the manifest list, order included). If the 40-define order differs, regenerate reprove40 under the composed manifest; recipe rows/reprove39/run.sh, ot-run --priority plan. Also the native_istations fixed_cycles rule (use lanefix.py), and reset_tree refusals.
   - Compare G0 to J5 with g0cmp: 0 new is required.
2. Apply choice: C3d if green, else C3c if green, else C1n. Do not apply plain C1d.
   - Apply chain: adapt intel2 /srv/opentallas-scratch2/claude/s81-die-r4-hub j5_chain2.sh (seal bind, compose on gen hosts, replicate, publish_onbase, out_install, mk_event_commit_r4.sh) and j5_apply3.sh (kit_wave_edit holds + publish_apply apply --candidate).
   - Set kit_wave dies.s81.tools_sha to a real rt sha through kit_wave_edit, replacing the literal j5tree. Do one bound-type proof gen on the scheduler rt first: check config.mk VERILOG_DEFINES has OT_S81SL_LEP_RIP1 on lepe_mu_LP t2, CFX on leaf, SRAMREG on vp_sr types. Check the kit place log prints "plan keys unmatched: 0".
   - Token compile: main >= f453583d58 (CFX), with 222ac8a1b0 (SRAMREG) selected defines.
3. First launches after apply: col_h9_r2, col_h9_r1, leaf t39, serdes t4, slice_station t36, lepe_mu_LP t2. Then c1x_C t4, iq_C t1, kv512_C t1, svc_hi rs t4, pvso_entry t2, kv_leaf t5. Read each at OT_CTS_POST_TIMING (post-hook) with OT_RELAY_SITES.
4. Tools findings posted: main 42eeacf refused 30 leaf types (fixed by 9cf14ee057, in 2ddb19); rt snapshots are reaped within hours, so pin them via rtpin.
