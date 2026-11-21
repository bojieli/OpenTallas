# KV-PLAN-R2 handoff (KV plan owner; successor of KV-PLAN-R1). CURRENT as of 2026-11-20 20:5x PST

Posts: lanes/posts/KV-PLAN-R2.md. Lane dirs: epyc7/epyc8 /srv/opentallas-scratch2/claude/kv-plan-r2, intel2 ~/tmp/kvplanr2.
Older context: lanes/handoff/KV-PLAN-R1.md, lanes/FABLE-PD-KV-1500.md, lanes/FABLE-PD-KV-1840.md.
hg/hgi family is owned end to end by FABLE-FIX-KV-HGI (COORD 19:3x); I only carry what D26 already has.

## 1. D26 (live gate) -- R3e, plan a9f605cb1acf
- Content: D25f2 + core_input_lockup 40 ports/19 hg-hgi types + score pack_fault pipe + krsp RT26 (32 lanes 5->6) + N3 hgi_v1 section N
  at 300 um + n3_cycles.py (12 tN lanes 8->10, eN stays 6: no eN station row) + pv station 300 + CLKSITE-SPLIT p3 rows.
  Compose = epyc7 kv-plan-r2/compose_r3d.sh (kv-plan-r1/compose_r3.sh + n3_cycles.py). Script epyc7
  .../kv-d23-compose8/d26_raw/d26_contracts/run_gate_r3e.sh {compose|g0|bind}. Candidate tree = d26_contracts/source_gate_r3b
  (tools = rt/bbcc7f022a8e die_plan copied in + typed_d26_contracts.patch; pinned by path, immune to rt/current).
- History: R3b died on runtime pin cmp; R3c bind refused L415 (tN cycles); R3d (tN+eN) cancelled before refusal (eN wrong).
- G0: GREEN (unit oth-ubuntu-2752101-1795230047; RC_PRECHECK 0 with --skip TOOLSTALE via kv-d23-compose8/gate_g0_d26.sh, RC_PRE 0, RC_G0 0,
  0 errors). Out epyc7 d26_contracts/normal_g0_r3e/gate.out.
- BIND + LATCHECK: RUNNING, unit oth-ubuntu-2751986-1795230046 on epyc7 (loved-redfish), client log intel2 ~/tmp/kvplanr2/d26_r3e_bind.log,
  gate out epyc7 d26_contracts/normal_gates_r3e/gate.out. RC_ELAB 0; bind.py pid 3350760 at 95% CPU 1h12 at 20:50 (past the R3c refusal
  point). gate_bind_d25.sh then runs LATCHECK, BOUND-PARAM (RC_BPC), R8 recheck. Green = RC_BIND 0, BIND_ERRORS 0, RC_LATCHECK 0.
  Static replay kv-plan-r2/replay_native.py: R3e shows only the 44 superset rows the clean D25f2 bind also shows.
- After green, also check: param_regen.json ectl RESPONSE_LAT 26 (QK 37) on hg frames; the 40 core_input_lockup ports bound.

## 2. D26 apply (run as soon as bind+LATCHECK green; the 20:00 cut has passed, no wait)
- `bash ~/tmp/kvplanr2/apply_d26.sh` on intel2 (out ~/tmp/kvplanr2/apply_d26.out). It: checks normal_gates_r3e green; mv candidate on
  epyc7 to kw45/src_kv_pin_eb1e73448bd0_hg14_a9f605cb_tbbcc7f0_d26 (+ kv-d23-compose8/d26/tree.txt); G0 on the final path (ot-run epyc7,
  gate_g0_d26.sh -> kv-d23-compose8/d26g0gate); seal_rep_d24.sh d26 from epyc7 (seal_d24.py SEAL_G0, verify, replicate to
  epyc8,9,10,intel1,epyc2 link-from D25e3); guard_d23.py; mk_candidate_g0.py from ~/tmp/kvd23c/cand_d25e3.json -> cand_d26.json; die_gen_env
  += OT_PLACE_MAX_TRANSITION=320 and POPS OT_PLACE_MAX_FANOUT, OT_CBC_REACH_UM (live has 405), OT_RESET_HOP_CAP_UM (BUILD-SETTINGS-AUDIT-1900);
  tools_sha = bbcc7f022a8e; publish_apply.py apply --expect-source kw45/..._hg12_983443ee_ta2fb7e6_d25e3 --expect-event KV-D25e3 --lane
  KV-PLAN-R2 (post-apply bind runs itself). Review the script once before running (written, never run).
- After RC_APPLY 0: (a) verify kit_wave dies.qwen_kvsys.die_gen_env has no OT_CBC_REACH_UM / OT_PLACE_MAX_FANOUT (kit_wave_edit if they
  survived the merge); (b) kit_wave_edit delete hold_items kv3_hg, hg_v1, hg_v1p2..v1p6, hg_v3; (c) drop auto_visual_review_skip
  ["kv3_hgi*"]; (d) ot-delete epyc8 d26_contracts/source_gate_r3 (refused earlier while the d26_contracts dir was a live --dir) and epyc7
  d26_contracts/r3c_spent_die_plan_*; (e) post APPLIED; first D26 gens = the one-type proof on the new tools (COORD FLEET-WATCH-1630).

## 3. D27 (11-21 cut) -- private, epyc8 kv-plan-r2/d27
- Sub-agent work so far: compose_d27.sh + rows/ (L356 per-bit exact bank 9 st on o_dcal_dob[2], 78->87; o_serdes_E_tx_up 5->7 st;
  KV-SYSC-1119 rx_payload/srx/svc/kvn_word_identity +3, svc_d1/emb_tx +1, link_cfg data/addr/rx_we/tx_we 4 st each (L1431-1434 +4);
  351 forward legs re-spaced to 300 (fwd_reach 0/358); efault_stage on hub_Wo in private asbuilt). First compose plan 3d152d53d5b5 G0 PASS but
  based on R3c (no n3_cycles) -> its bind (oth-ubuntu-2031059-1795226238) cannot pass. A second sub-agent is re-basing on R3e (compose running).
- D27 MUST include (COORD): re-pin tools to current main (pinned rt/<sha> path, >= c0feb4c70e; add rt_pin.py --export when a2a4cb2d35 lands);
  pv re-site rows lanes/handoff/OPUS-FIX-KV-PV-R4-resite-rows.json (16 pv types, 499 hops >300 -> 300, +17..+49 cycles/type) + rest of
  OPUS-FIX-KV-PV-R4-d27-rows.json; hg/hgi census300 rows (owned by FABLE-FIX-KV-HGI: take their rows, do not author); RESET-R3 u_bin reset rows
  (RESET-RELAY-GEN-R2 / RESET-R3: every u_bin_<bus> on its nearest tap; no other extra relays); LOCKUP-STATION-1130 stage-chain lockups;
  efault_stage all 29 types + fault-output hop site (~1,300 um hub_Wo; tool main 4459f7ee18); pc_v1 i_ectl_Q_N_kf third bank (24 lanes 2->3);
  PDN-0006 kv_pcsplit_views_1119 re-export in merged-obstruction form (not M6/M7 pins); hub_C 6 kvd23_hubc_views re-freeze from source
  (CLAND-MACRO-1 form); kv3_io_cor_v1 DRT-0255 (u_bound.u_ft_ft11_o_3/net77912 pocket at ~(504,520) um, 257 viol at opt iter 4, 5:23 h;
  + u_cland_ft13_i -> u_ft_ft13_o_0 69 b at 458 um): re-site ft11_o/ft13_o stations at 300 and open the pocket; pv_v6n CLAND band (PV owner).
- Before every D27 bind: replay_native.py (no new vs 44) + tools/precheck/plan_geom_census.py (R3c: 1,032 hops >300 on 47 types; drive to 0).
- After G0+bind: one private CTS proof per family class (pv, pc, hub, sys, hroot/phy; hg/hgi = FABLE-FIX-KV-HGI). NO D27 volume before a
  CTS read per class.

## 4. Pushed / other
- main 65f3f85d7c fwd_reach declared-hop check (5 tests); 4459f7ee18 staged efault bind form (10 tests + RTL bench).
- kv3_hub_Ei a4 (D25e3): place done GPL on intel1 at 15:0x; read its route result.
- kv3_io_cor_v1 a9 auto-relaunched 19:55 on unchanged D25e3 inputs (expect repeat DRT-0255; 3 h unsignable rule applies).
- Failed KV rows triage (post 17:5x): hg GEN_LINT x11 + reset identity x4 + hub_Wi -> D26; hub_C, pc PDN x2, pc_v1 x3, pv_v6n -> D27.
- PV: FABLE-FIX-KV-PV-R2 v8m/v8c/v8p results not yet brought in.

## Stop list
No route/repair of hub_Wo / sys_c; no route release of the 20 held D25e3 rows; no route of D25e3 hgi kits; no kR late-repair retry; no apply
on f81cafc24d3a (R3d); no extra reset relays beyond the u_bin fix; no D27 volume before per-class CTS proof.
