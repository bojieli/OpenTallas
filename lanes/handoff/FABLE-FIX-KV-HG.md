# FABLE-FIX-KV-HG handoff (KV HG plan event owner; second instance started 2026-11-17 09:25 PST)

Work dir: epyc10 /srv/opentallas-scratch2/claude/fable-fix-kv-hg2. Hub logs intel2 ~/tmp/ffkhg2. Runners intel2 /srv/opentallas-scratch2/claude/tools-converge/ffkhg2.

## STATE 11-17 19:3x PST: D21b APPLIED = KV-HG6
- Live: kw45/src_kv_pin_eb1e73448bd0_hg6_2433b9c2_t24c7347c_d21b, manifest 79bf6f8a4d40, plan 2433b9c21c26, r8_ev.json ad024d0bb7d3,
  tools = main 24c7347cc887, on epyc10/7/8/9 + intel1 (src_manifest replicate --link-from D16, hosts --expect rc 0, guard full_ok 5 hosts).
  bind_out fable-fix-kv-hg2/d21bgate/bind (same path, all 5 hosts). Receipt lanes/handoff/qwen_kvsys_atomic_apply_1794972605558774278.json.
  Pilot kv3_hg_v1, release gen_pilot:qwen_kvsys:79bf6f8a4d40 (system releases the other items after the wave GEN of the pilot passes).
- Content: D16 + HG6 v5 (KV-R3 composer: PC bays carve, ring->bin FIRM stations on 3 kv3_pc_v1 types, ONE k per R8 bundle, rq unstationed,
  +1296 lane-cycles) + v6 row (kv3_hroot raw branch fs_o_kvs_hroot_Q_o_emb stage [1886.8,530.114] -> [1894.252,530.654], off the reserved
  clock rect) + r8_ev re-derived (land_r8_derive --like D16 + kv_r8_pin, control der_ctl_d16.json; 516 members bound/landed, pads kept).
- Gate of record epyc10 fable-fix-kv-hg2/d21bgate/gate.out: PRE 0; G0 0 err / 2403 warn; strict bind 0, 160/56/2545/429,530;
  R8_RECHECK 0; r8.py check 64/2/6 = D16 baseline (0 differing lines; NOT a KV gate); strap audit PASS 580; LATCHECK 2404/2404.
- Publish record ed4ad20f8c0 (dry GEN kv3_hg_v1 DRY-PASS).

## Lessons (cost several hours)
- r8.py check --replica type --bus leaf fails 64/2/6 on every KV tree; KV R8 gate = table equals pinned derivation.
- A tools rebase must drop skip-pattern files (*.orig) from the manifest or tree_check fails DRIFT (missing).
- bind.f embeds the absolute tree path: gate on the FINAL tree path; a rename needs a re-gate (70 min).
- apply tool (11-17) replicates from the hub and fails "not a manifest tree": replicate from the build host, list all gen hosts in the
  candidate, run tree_check for exactly those hosts (ffkhg2/guard5.py), then apply.
- ot-delete refuses unpublished candidates newer than the live tree; D19 (49 GB, epyc10) is still there, unprotected.

## Open, in order
1. Pilot kv3_hg_v1 wave GEN -> place/CTS/route -> sign-off -> export AGIdock /archive/opentallas-signed-1114 + rtx-pro
   /home/ubuntu/signed-export-1114 with INDEX rows. Read the first PC GEN (kit_istations on the 20 station rows: never exercised; the
   D19 PC dry GEN failed at kit_rtl on missing kvpc child source = WAIT-DEP/provisional class) and CTS per-tap insertion before any tap split.
2. WAVE-FLOW-R2 KV tools-only refresh (r620, r641) on the D21b base; bind command in my BIND-CMD post.
3. D22 (compose on 2433b9c21c26):
   a. hub_C 17 rows: lanes/handoff/KV-HUBC-SPLIT-hubC-rows-d21.json (place-check vs ft stations/taps/resets; +1 IN_STAGE cycle).
   b. hub_Wi host: 21 hard_cores rows have physical_inst u_bound.u_host.host__qkd_hr_* but the bound part instantiates the unclustered
      qkd_host_root_admission_obsx_bo1_c45 and the rows have no lef/lib. Need clustered host RTL (cores/harden/kv_core_rtl.py --hr-wrappers,
      tools/qwen_kv_die/host_cluster/gen_cluster.py, partition_r2.json) as the bound u_host + views of the 14 signed qkd_hr masters
      (rtx-pro signed-export-1114/{qwen_kvsys,Qwen_ROM}/qkd_hr_*). No-view rows: hub_Wi 21, hub_Eo 2, hub_Wo 2, 6 pc types x 8.
   c. PV/PC pad-chain tail per consumer core (bind key asbuilt.land_pad_tail_split, proposed to TAIL-REPL) + plan stages where
      pad < ceil(branch/380). Helper FABLE-FIX-KV-HG-CHAIN: list + bind proof + pv_v12 placement proof; dirs epyc10
      fable-fix-kv-hg2/{chainproof,tailsplit}. R-REACH-5 / r_dly_spread proven to make wns worse: never enable for KV.
   d. kv3_pv_v2 / v2n OT_CLAND writer-face:ft26_o window [541.504,1512.0,550.144,1520.64] on the N face strip (type height 1520.64).
   e. kv3_pv_v6n raw:o:4 window 1.17 um2 free (advisory).
4. HG7: i_ectl_Q_N_rq ring->bin > 405 um: all-frame RESPONSE_LAT 29 / QK 40 + 4 ECTL quarter rebuilds.
