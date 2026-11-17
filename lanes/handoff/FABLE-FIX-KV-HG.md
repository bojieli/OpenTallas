# FABLE-FIX-KV-HG handoff (KV HG plan event owner; second instance started 2026-11-17 09:25 PST)

(11-16 instance notes: v25hv views work, epyc10 /srv/opentallas-scratch2/claude/fable-fix-kv-hg; superseded by D16.)

Work dir: epyc10 /srv/opentallas-scratch2/claude/fable-fix-kv-hg2 (read-only use of kv-r3/). Hub logs intel2 ~/tmp/ffkhg2.
Split (KV-R3 HANDBACK 09:24): I own R8 table, composer, bind, gates, tree, publish, apply. KV-R3: type builds, fleet, e7483c8821.

## Measured (11-17)
- r8.py check --replica type --bus leaf on the D16 bind (applied tree): 64 unequal / 2 inversions / 6 types. Same as D18. It is the
  KV baseline (strap pads / position bank / exempt carry it), NOT an HG6 effect and not the KV R8 gate. r8check_d16.log.
- KV R8 gate of record = table equals its derivation: land_r8_derive.py derive --like <D16 r8_ev.json> + kv-102/adopt_kvgeom7u/kv_r8_pin.py
  (control der_ctl_d16.json; 91 pvw members keep the shipped pad). On D16 it reproduces r8_ev.json 5911/5911.
- Same recipe on the v3 (D18) bind: 572 members change, x__tep pads 0 -> 17 per instance, 8 new tok/tep inversions, pad flops
  92,231 -> 143,556. v3 is dead. FABLE-CLOSURE-STRATEGY step "pad the shorter bus" = KV-R3 v5 (one k per R8 bundle), correct form.
- D18 31st error: PARAM_REGEN ECTL RT [26, 29] (kv_regen.py RT = 8 + krq + krs; +3 on i_ectl_Q_N_rq in pc_v1 frames only). v5 excludes rq.

## Running / next
1. bind1 of v5 plan c4a90079c005 (symlink mirror on D16): epyc10 fable-fix-kv-hg2/bind1_v5.sh -> bind1_v5/diag.out
   (unit oth-ubuntu-3923780-1794936523). Writes r8pin_v5.json (recipe) and r8renum_v5.json (KV-R3 renum), compares, r8 check.
   Expect: only R8_STALE errors, PIN_vs_RENUM 0, r8 check 64/2/6.
2. build_d19.py (cp -a D16 + plan + r8_ev.json, manifest) -> kw45/src_kv_pin_eb1e73448bd0_hg6_c4a90079_d19; protect it.
3. gate_d19.sh <tree> via ot-run --priority plan --hosts epyc10: PRE, G0, strict bind 0, R8_RECHECK changed 0, R8_VS_D16 0, LATCHECK.
4. Publish: intel2 /srv/opentallas-scratch2/claude/tools-converge/kv-r3/run_d18_publish.py pattern (PC dry GEN kv3_pc_v1__cl23f6a148
   nocommit first, then kv3_hg_v1 commit), apply (KW00 apply_reviewed_tree_marker, see KV-R3.md 07:3x), pilot kv3_hg_v1 to sign-off,
   export AGIdock /archive/opentallas-signed-1114 + rtx-pro /home/ubuntu/signed-export-1114 with INDEX rows.
5. HG7 (next event, on HG6 base): rq ring->bin > 405 um -> +k on all frames, RESPONSE_LAT 29 / QK 40, rebuild 4 ECTL quarters
   (outline unchanged). hub_C split (KV-HUBC-SPLIT) does not ride with HG6.
