# FABLE-FIX-KV-HG handoff (third instance, started 2026-11-18 07:35 PST; KV-HG-OPUS owns D23/D24)

Work dir epyc9 /srv/opentallas-scratch2/claude/fable-fix-kv-hg3 (sc/ = STA dumps, rm/ = relay proof kits, wt/ = lane clone). Hub logs intel2 ~/tmp/ffkhg3.

## RESULT 11-18 09:35 PST: proof p2 (hgi_v1__cl141fc26e, HG6 kit + relay chain keys), post-CTS TT, same STA script as the base
- failing setup ends 1,450 -> 290; tns -123,329 -> -24,581; hst_t2->head (673 ends) and lpad->hst_g (477 ends) = 0 left.
- wns -309 -> -402: the reset rs_ri -> core rst_n class moved (27 ends); kp core->core 192+ ends at -251. These two classes are all that is left.
- Flow note: GOAL=cts on a copied kit re-ran floorplan after CTS (stage ODBs pruned, make chain); I stopped my container after
  4_cts.odb (17:20Z) and dumped a snapshot: epyc9 fable-fix-kv-hg3/sc/p2/out/ends.tsv. No routed result; nothing to export.
- Next owner step (KV-D23-COMPOSE / KV-HG-OPUS): section A keys in D23c for 17 hg/hgi types; D24 = kp core stations realized + reset rows.

## STATE 11-18 08:40 PST
- 0710 headline 6 is wrong: KV kits reach CTS. Route-goal jobs run in sealed dirs <host>:/srv/opentallas-scratch2/claude/ot-jobs/kv3_*-route-*/work.
  23 HG6 kits past CTS, in GRT. Post-CTS TT setup: io_cor +156, hroot +3; hgi -268..-792; hg -502..-864; pc -468..-1486.
- Cause: unregistered 1.0-3.2 mm wires in every failing class (rows file: lanes/handoff/FABLE-FIX-KV-HG-rows-d24.json).
- Fix on main a572716aa09: relay chain siting keys (budgets.relay_mid_re[_types], relay_mid_tail[_types], relay_mid_soft_frac[_types],
  GEN env OT_RELAY_MID_RE / _TAIL / _SOFT_FRAC; gen_phys.RELAY_MID_RE_KV). Absent = byte-identical.
- Proof kit p2 (hgi_v1__cl141fc26e, HG6 kit + the keys): epyc9 rm/p2, place -> CTS via ot-run, log intel2 ~/tmp/ffkhg3/p2_cts.log;
  chain_p2.sh then writes sc/p2/out/ends.tsv (compare with sc/hgi_v1/out/ends.tsv: 1,450 ends, wns -309, tns -123,329).
  Class tools: scratch copies in sc/ (run.sh TAG, tail.tcl), classifier cls.py / fine.py in the session scratchpad (not kept).

## Open
1. Read p2: OT_RELAY_MID lines in 3_3_place_gp.log (both chains placed, tail at centroid), then ends.tsv classes hst_t2->head, lpad->hst_g.
2. If p2 holds: KV-HG-OPUS puts section A keys on the 17 hg/hgi types (item_env = no plan event), relaunch only after the HG6 route jobs gave their GRT numbers.
3. Section B rows are plan rows with cycles (D24): eN stations, kp core stations realized, ring->bin, writer-start reach, idpc.
4. io_cor / hroot: wave route jobs; on sign-off export full DB to rtx-pro /home/ubuntu/signed-export-1114 and metadata to AGIdock /archive/opentallas-signed-1114.

---
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
