# S81-DIE-R3 handoff (Opus, succeeded S81-DIE-R2 / Codex 05:03 packet)
E = /srv/opentallas-scratch2/claude/s81-b3-clk/rows/f2s5_S81-DIE-R on epyc10; K = /srv/opentallas-scratch2/claude/kw45.

## State 2026-11-17 16:2x PST
- D5e-r3b APPLIED: s81 event 3fa87b84b18, src K/src_s81_pin_3c913dbdfb23_f2s4_cohort_d5e, manifest 20ee0959...5965,
  plan 9f664e6f, asbuilt 3b58769a; on epyc10/epyc8/intel1 (pack E/d5e/r3b/pack, 1300 adds, 2243 deletes, delta 2bb63afe).
  Strict bind 0 (395 types, 873 crossings), LAT 873/873, G0 6 inherited ERR (baseline lanes/handoff/S81-D5E-R3B-G0-BASELINE-1117.json),
  PRE PASS, publish gate PASS, guard ok (relaunched on checker 001728c6 after rt/current moved to 690699611b9c).
  Pilot gunit__t1 release gen_pilot:s81:20ee09596c16, receipt lanes/handoff/s81_atomic_apply_1794932780359983736.json.
- bksel stays hq3 (D5c ledger 2467d3db). Honest eco3 registry entry (OLL2/RFH2/HLAT1, records 3a374028+ac34039b) is scoped by
  lib_contains cores/views/bksel_eco3_1117/ (registry 48f0b05d) = real mismatch vs die RTL (only OLL); goes to D6 with RTL merge.
- C4r3 (on K/src_s81_pin_3c913dbdfb23_c4b_1117, D5c-based copy, NOT published): plan E/c4r3/plan_C4R3_HI3v2_col150_fwppk_bkselhq3_r3.json
  0126890b (Codex formB_hi3 201eef7c, 24 eco3 bksel rows reversed). Strict bind 0, LAT 873/873, PRE PASS, G0 5 ERR = strict subset
  of D5e baseline (t6 ft2 macro overlap cleared). e943f1f62f4 ordered rows + 056783ac187 face_flops present. c4b gen_phys 0b9902a6
  already contains D5e EGN c5e20297 (3-way merge identical, E/c4r3/genphys_merge). c4b lacks only D5e record files
  g0_report_d5e_r3.json, params_recheck1117.json (copy in).
- Kits (VPW_BANK=1): E/c4r3/kits/{t34,t62}/gen/<type>, GEN + gen_lint PASS. t62 = form-B pilot -> S81-TYPES-R3. t34 HELD (seam, FABLE-PD-S81-0720).
- Seam census E/c4r3/strip_seam_census.json: exposed t71 1.33, t13 1.29, t34 1.12; marginal t10/t74 0.69, t75 0.66, t39 0.61; t62 0.25.

## Next
1. C4 publish: pack D5c manifest d23e4b91 -> c4b (as E/tools/make_d5e_r3_pack.py, skip symlinks), delta-apply onto D5c into a new
   cohort_d5f path, publish, replicate (E/tools/replicate_d5e_r3b.sh pattern), candidate json, G0 baseline record, tree_check.launch
   with CURRENT rt checker, publish_gate, apply --pilot-item t62 form-B item.
2. D6 (ONE next tree): VE_m/VE_s east t34 +34.56 / t71 ~+43.2 / t13 ~+51.84 um (fit check); blocking per-channel track check 0.70
   in plan gate (branch + ot-gate-remote + READY); bksel eco3 RTL merge (S81-CORES-R3, +1 cycle priced, eco3 rows + ledger bd1dc957);
   gunit bf record; rck centre-root trunk (pma_rck x+13.4 -> serdes pin x1448/y1063.8 M7, M8/M9) only if H12 routed AM < -42 and H14 beats H12/H13.
3. col/dsdv plain-posedge: 66 col + 43 other types wait on tap-skew reads.
4. E10 scratch2 95% (438 GB free) - watch.
