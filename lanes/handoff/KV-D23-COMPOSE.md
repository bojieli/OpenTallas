# KV-D23-COMPOSE handoff (helper of KV-HG-OPUS; started 2026-11-18 06:0x PST)

Work dir epyc7 /srv/opentallas-scratch2/claude/kv-d23-compose (lane clone wt/ = sparse main worktree). Hub logs intel2 ~/tmp/kvd23c.

## Candidates (all built from the live D22 tree, manifest d988db9486e2, plan 23c87c42a4e9; tools/common_flow + rtl/lib/ot_dp_efault.sv from main eefb7e36eb6)
- D23  kw45/src_kv_pin_eb1e73448bd0_hg8_add04d1e_teefb7e3_d23  plan add04d1e8a2d asbuilt da56e1cd818c; gate d23gate/
  = tail split types kv3_pv.* (only under-matching ^-string in plan+asbuilt) + KV-D23-PC composer re-run on D22 (pc/ : 68/72/72 taps,
    fclk edge splits, reset/collector re-solve, sidecar 9704beb258d4) + efault EQ_PIPE_V 10 rows (plan_cell_conns_v36) + hub_Wo 11 cores.
- D23b kw45/src_kv_pin_eb1e73448bd0_hg8_2cc1cff4_teefb7e3_d23b plan 2cc1cff49074; gate d23bgate/ = D23 + 59 PV raw-stage band rows
  (band/band_rows.py, flags 3/3 KV-HG6 literal-local-reset CLAND failures; D22 left v4 TNQN_b stage 2 at y 1516.32).
- D23c = D23b + KV-D23-REACH rows (rows_proof.json: reset_replicate rsync on 36 types, reset sink_stages, tail split pipes:true);
  needs the reach code on main (my squash of claude/kv-core-reach-1118, conflicts with BIN-COPY resolved by hand; ot-push-main).
## Scripts
build_d23.py MAIN TAG (in/plan_TAG.json, in/asbuilt_extra_TAG.json), gate_d23.sh TREE OUT, seal_d23.py TAG, seal_rep_d23.sh TAG,
mk_candidate.py (from the KV-D22 candidate); intel2 ~/tmp/kvd23c/{guard_d23.py, launch_gate_when_staged.sh}.
Apply: python3 -I rt/current/tools/autopilot/publish_apply.py apply --candidate C --expect-source LIVE --expect-event EV --lane KV-D23-COMPOSE
## D24 (next): hub_C split (KV-D23-HUBC), die clock node re-site, pvfin stations, hub_Wi host rows (KV-HUBWI-HOST-rows-d23.json,
writer main 04df4c77f065), pc core RTL for qkd_kvs_pcc/pcf(+_h_head_p) (portbind/LEC gap; bind + kits not affected), light ring key.
## Status 15:15Z
D23 + D23b strict binds running on epyc7 (ot-run plan bind). ot-push-main of reach squash (wt branch kvd23-reach 440bf7477b6) running tests (push3.log).
D23c staged inputs: in/plan_d23c.json (band + reach + ring2 lite/narrow keys on hub C/Wi/Wo/Ei/Eo), in/asbuilt_extra_d23c.json.
Apply order (KV-HG-OPUS): D23 when green -> D23b -> D23c. Rider rows (kv-pv-rider) not yet in any candidate.
## Status 16:45Z (after D23/D23b FAIL)
BASE FOR MIRRORS (live, applied): /srv/opentallas-scratch2/claude/kw45/src_kv_pin_eb1e73448bd0_hg7_23c87c42_t5144e08_d22
  manifest d988db9486e2, plan 23c87c42a4e9, asbuilt efad37e95d45, r8 57bb66595819 (event KV-D22). Updated here when D23e/f/g applies.
D23/D23b FAIL: 1 EMIT kv3_hub_Wo raw Q rst_rl_214 (hub_Wo cores change the solved reset tree; lane KV-HUBWO-RESET).
In flight (epyc7, no hub_Wo, NO_WO=1 build_d23.py): D23e (D23 minus hub_Wo, tools eefb7e3), D23f (band + rider), D23g (band + rider + reach + ring2 keys, main e8731b01bcf).
D24 prep on main: 05f7de74d0c (hard RSTREP rings keep reach reader START), db1854527ce (clksite_resite.py; hub_C S 68.31 um).
hub_C pre-proof gate: epyc7 kv-d23-compose/hubc/gate_c (rows4 = KV-D23-HUBC rows3 + resite, D22 mirror, tools main e8731b01bcf).
## Status 18:00Z
Gates (epyc7, all PRE PASS, strict binds running, ot-run --crit since 17:07Z): d23egate, d23fgate, d23ggate, d23hgate (D23h = D23g + FABLE-FIX-KV-HG
relay_mid keys on 17 hg/hgi types, main 0c3fb152c30, tree kw45/src_kv_pin_eb1e73448bd0_hg8_aa3f08ac_t0c3fb15_d23h plan aa3f08ac4159), hubc/gate_c.
Apply rule: most complete green of g > f > e first (expect-source D22, expect-event KV-D22), then D23h on top (expect-source = applied tree).
pvfin (RULING KV-HG-OPUS 18:0x): NO pvfin station rows from this lane. ahub fr_rz -> pvfin rz is 0 kept stages, per-bit 1,084 / 1,176 um
(lo / hi, needs k=2 at 405 um), but pvfin faults on an rz off its calendar slot (qkd_pv_fin_s8 l.144) and pvfin sits in the u_kvs_attn
static loop (pvfst D45 -> pvfin -> fin D46, RETIRE_STATIC). Lane KV-PVFIN-CAL moves the attn_root calendar R slot +2 + 2 rz stations and
writes ~/coord/lanes/handoff/KV-PVFIN-CAL-d24.json; it drops into D24 last. Fallback re-floor next to ahub: 0 free sites <= 500 um today
(blocked by taps / internal station regs / collector relays; epyc7 kv-d23-compose/hubc/pvsite*.py).
pc RTL (D24): sources already in every tree (results/kv_host_regen_1/rtl_rf3/<m>/<m>.sv, on main); the gap is only asbuilt portbind_files.
Proof: epyc8 /srv/opentallas-scratch2/claude/kv-d23-compose8/pcpb (strict portbind on D22 + 4 pc tops in portbind_files; ot-run from intel2).
D24 recipe (base = applied D23 tree): hub_C rows (re-run kv-d23-hubc/d23_hubc_rows.py on the applied plan + tools/die_plan/clksite_resite.py)
+ hub_C clock.landing_ring_lite/narrow (KV-RING2-LIGHT-keys-d24.json; hard rings are wide, LITE only <= 4 bits, NARROW keeps hard params)
+ hub_Wi host rows (KV-HUBWI-HOST-rows-d23.json apply_recipe, writer main 04df4c77f065, views epyc9 kv-d23-hubwi/views_src)
+ 4 pc portbind_files + hub_Wo (KV-HUBWO-RESET-d23.json when green) + pvfin (KV-PVFIN-CAL-d24.json) last.
HUBC leftovers now mine: 6 exported ring/dly masters, kv_dly_w512_d46_b4fbd in GRT (KV-D23-HUBC dead).
## Status 19:05Z -- KV-D23 APPLIED (D23f)
LIVE BASE (for mirrors / D24): /srv/opentallas-scratch2/claude/kw45/src_kv_pin_eb1e73448bd0_hg8_e21a54ae_teefb7e3_d23f
  manifest ec75f13b9d2b, plan e21a54aebe16, asbuilt da56e1cd818c, event KV-D23, hosts epyc7/epyc9/epyc10 (epyc8 disk floor, not replicated).
  receipt lanes/handoff/qwen_kvsys_atomic_apply_1795034096412178751.json.
Next on top (expect-source = D23f tree, expect-event KV-D23): D23h2 (= D23g2 + FABLE-FIX-KV-HG relay_mid keys on 17 hg/hgi types;
  tree kw45/src_kv_pin_eb1e73448bd0_hg8_aa3f08ac_t0c3fb15_d23h2, gate epyc7 d23h2gate) or D23g2 if h2 fails.
  D23g/D23h: NOT to apply (ring RTL without LITE; D23g bind BIND_PARAM_UNKNOWN). build_d23.py EXTRA_PATHS adds the ring RTL.
D24: epyc8 kv-d23-compose8/build_d24.py BASE EVENT MAIN TAG (inputs d24in/); needs the HCPARAM entry (main 61164324139e) in tools.
pc portbind proof: epyc9 kv-d23-compose8/pcpb (epyc8 below disk floor). d46 dly rebuild: epyc10 kv-d23-compose/dly_h1.
BOUND-PARAM-1 (main 60fe7ab5499): run tools/die_plan/bound_param_check.py --tree T --rtl-dir T/.../bind_of_record/rtl after each gate.
After the first D23 hub/pv kits: post native hub_Wo cell count (hub_Wo split held, so from D24) and NEED-STATION counts on pv v2/v6 kits.

## Status 21:50Z -- KV-D23H APPLIED (D23h2 on D23f)
LIVE BASE: /srv/opentallas-scratch2/claude/kw45/src_kv_pin_eb1e73448bd0_hg8_aa3f08ac_t0c3fb15_d23h2  manifest dd671e408127, plan aa3f08ac4159,
  tools 0c3fb152c30a, event KV-D23H, hosts epyc7/8/9/10 (tree_check full_ok), receipt lanes/handoff/qwen_kvsys_atomic_apply_1795037429350356690.json.
  Content: D23f + reach rows (reset_replicate rsync copy_depth 3 = FABLE fix #3) + ring-lite keys + FABLE fix #1 relay_mid keys (17 hg/hgi).
  D23f (KV-D23) re-replicated to epyc8, tree_check full_ok 4 hosts. Candidate maker for stacked events: epyc7 W/mk_candidate_stack.py.
  Seal lesson: seal_rep_d23.sh continues after RC_VERIFY 1 (it replicated anyway); h2 bind_sinks.json had nlink 2 from outside -> cp -p + mv.
D24 (building epyc8 kv-d23-compose8/build_d24a.log, TAG d24a, base D23h2, main 795a5223111):
  1 hub_C split  2 hub_Wi host  3 pc portbind_files (+ portbind_prefer mu_qwen_20261018 collected_mu: pc proof AMBIGUOUS fix, rerun epyc9 pcpb)
  4 PVFIN-CAL: asbuilt.land_intra_stations 6 nets ahub.fr_* -> pvfin_{lo,hi} k=2 (bind_intra_stations.py; plan core rows get NO RTL on KV),
    sites d24in/pvfin/pvfin_intra_sites_d24.json (2 stages re-sited off pvfin_hi / pll, hops <= 398.7), FR_LEAD derived by
    r8/kv_pv_col_regen_d24.py (declare qkd_kvs_attn_fl FR_LEAD 0). RTL qkd_kvs_attn_fl_r17 + qkd_kvs_attn_r17 from main.
  D_RL caveat: real boot image boot_v36/boot_ages_asbuilt.json D_RL 93 / D_QK 57 / F_DLY 55 / FIA 113 (lane scanned 235/3/95/255): KV-PVFIN-CAL re-scan asked.
  Next: gate D24 (bind_fast precheck -> strict bind -> LATCHECK -> G0 + bound_param_check + bind_intra_stations.json / param_regen FR_LEAD 2 read-back).
Not in D24: FABLE fix #2 (28x2 parent kt + 2 e0-local + astk calendar +2): NEEDS-LANE KV-KT-E0 (head RTL ot_qkh_head_native_r4 kst D=2 x16
  lanes, astk cal +2 + sim, e0 re-harden 216x216, bind_intra_stations bit-slice net form); hub_Wo split (KV-HUBWO-RESET).
d46 dly (epyc10 dly_h1): still NOT SIGNED, FF hold -5.75 ps even with margins 30/25.
