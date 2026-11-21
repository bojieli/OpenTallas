# KV-PLAN-R3 handoff (KV plan owner; successor of KV-PLAN-R2). CURRENT as of 2026-11-20 21:0x PST

Posts: lanes/posts/KV-PLAN-R3.md. Lane dirs: intel2 ~/tmp/kvplanr3, epyc8 /srv/opentallas-scratch2/claude/kv-plan-r3/d27c.
Base plan: lanes/handoff/KV-PLAN-R2.md (sections 1-4 + stop list still hold).

## D26 (R3e, plan a9f605cb1acf)
- Bind+LATCHECK unit oth-ubuntu-2751986-1795230046 epyc7, running (bind.py 94% CPU at 1h14, 20:52). ot-wait armed (KV-PLAN-R3).
- Apply script = ~/tmp/kvplanr3/apply_d26.sh (copy of kvplanr2 one: lane KV-PLAN-R3, outputs in kvplanr3). Fix made: mk_candidate_g0.py
  was only on epyc8; copied to epyc7 kv-d23-compose8 (sha 277a4109).
- On green: check bind_of_record/param_regen.json ectl RESPONSE_LAT 26 (QK 37) and 40 core_input_lockup ports bound, then apply.
- After RC_APPLY 0: kit_wave die_gen_env has no OT_CBC_REACH_UM/OT_PLACE_MAX_FANOUT/OT_RESET_HOP_CAP_UM; lift 8 hg holds; drop kv3_hgi* visual
  skip; ot-delete epyc8 d26_contracts/source_gate_r3 + epyc7 d26_contracts/r3c_spent_die_plan_*; reps first, one per family.
- COORD: verify kv3_hub_Wi (ORD-2013) and kv3_pv_v8 (collector identity) pass gen on the first D26 gens.

## D27
- R2 sub-agent: d27b (epyc8 kv-plan-r2/d27b) plan fae02128cad8, census HOP 409 rows/38 types, fwd_reach 136/358 >300; its G0/bind on epyc8
  (units oth-ubuntu-353498/353527-1795236917) running; informational.
- KV-PLAN-R3 sub-agent composes D27c in epyc8 kv-plan-r3/d27c: + pv re-site rows, hg census300, RESET-R3 u_bin(/u_bout), io_cor ft11_o/ft13_o,
  KV-FAILED-ROWS-2100 (hub_C views + provenance, pc PDN merged-obstruction, pc_v1 kf 3rd bank + drop face move, pv_v6n band),
  OT_TAP_CORE_DIRECT only if b8d wins. Census/adopt_diff/event_census before bind; one CTS proof per class before volume.

## 21:5x update (COORD via FABLE-PD-KV-2230, binding)
- KV-PLAN-R3 is the only D27 composer; R2 D27 sub-agent stood down. D27c drops r5 lockup rows; adds pc_v3 rows, hub_Eo core reset row,
  hroot port-in hold structural row, 150 pv relay_depth legs as stations. bank_taps only after RESET-RELAY-GEN-R3 2 passes + tap-id check.
- Stops: no pv volume before a post-hook tap spread < 100 ps (TAP-GRID-2130); no hgi route volume before one clean GRT.
- D27b run-6 (plan fac662d8c549) G0/bind were cancelled 21:51 by the R2 stand-down; relaunched by KV-PLAN-R3 on epyc8:
  G0 oth-ubuntu-1186799-1795240343, bind oth-ubuntu-1186789-1795240343, out epyc8 kv-plan-r3/d27b6gate/{g0,bind}.
  epyc8 kv-plan-r3/proofs/chain.sh (log chain.log) launches the private proofs on green: pv_v2, pc__cl254f2e73, pc_v1__cl23f6a148,
  hub_Wo, sys_c, hroot -> CTS; hg_v1, hgi_v8 -> GRT. One CTS read per family before D27 volume.
