# KV-KVSCTL-4 (10-27): kvs_ctl recut proof collect + [4,2] H-tree prep

## Recut proof (kvsctl3-fp, intel2, 03:12-04:11 PDT) -- FAIL
- fp_eq_rc.txt: post rc=0 / mut rc=1 / emitted_v rc=1.
- emitted_v: 92037 $equiv, 92000 proven, 37 unproven (fp_eq_v_unproven.txt) -- the SAME 37 as fp3/fp4 (u_lprg
  wa_d[32k], w_data[0], w_zero, w_one, b_data[0,32,..,160..167]). The KVSCTL-3 async resets did not change them, so the
  "no-reset reg" root cause is refuted.
- What the 37 have in common: all are functions of data_q[0] (= dqf[0]); w_data[1..31] (same regs, same reset, same
  mux) prove. post (recut json vs RTL) proves with 0 unproven, so the recut transform is proven; the 37 appear only on
  the write_verilog -> read_verilog round trip (emitted .v). Structural read of the emitted .v (dqf flop _5485_,
  dm2 = data_q - 2, u_wd0/u_wd1 ot_s32_sel leaves, w_* async reset on rnv[0]) shows no functional difference
  (UNCHECKED by proof). Working hypothesis: induction strength on the round-tripped names, not a real mismatch.
- Diagnostic proofs (docker, intel2, started 04:17 PDT, ~60 min): seq4.ys (equiv_simple/induct -seq 4) and undef.ys
  (-undef -seq 2) on the same gold/gate. Collect /srv/opentallas-scratch2/claude/kvsctl4/diag/{seq4,undef}.{rc,log}
  (grep "unproven"); FP = /srv/opentallas-scratch2/claude/kvsctl3/fp/.
- gen_core_kit_kv.py --hr-face-ports refuses the kit until eq_rc = post 0 / mut 1 / emitted_v 0 -> kit, face_guard,
  build, render, GEOM REQ NOT DONE.

## [4,2] H-tree prep (12.8b, 12.2a1, 12.8 d1)
- tools/die_plan/core_infra_htree.py --hb-axes x,y,x --islands <8 slice islands>: balanced BINARY H-tree from the centre
  entry over the 2^n fixed master-plan islands (every internal node 2 children; hub = midpoint of its children; buffer per
  branch, one point-to-point wire per net; per-level equal length). Tests tools/die_plan/test_core_infra_htree_hb.py 2/2.
- On the slice islands of results/kv_core_slice_1/slices/qkd_kvs_ctl.json the legs are equal per level by construction
  (level spread 0.0/0.0/0.0 um, hub snap 0): 94.5 / 93.4 / 44.8 um (the slice islands are 4.32 um off mirror in y;
  the midpoint hubs absorb it, no plan delta needed).
- Synthetic-sink pre-prediction (12000 uniform DFFs, no macros; htree_syn/sweep.tsv; PLAN MODEL NLDM+Elmore, UNCHECKED):
  every [4,2] form predicts TT 304-315 / FF 257-266 (window 50-81 ps), [4,4] 310-322 -> OUT of the 250+-20 band
  (model offset vs built trees -12.8 TT, still ~290). Slice prediction 245.8 assumed trunk 0.20 ps/um; the
  buffer-per-branch tree has 7 stages (~43 ps/stage in this model). The real-sink plan runs on the pass-1 placement
  (dump_geo_core.tcl) before the tree is built; if it stays >270, 12.3/12.3a apply (structural fix first: fewer/stronger
  stages by plan-computed sizing, 12.8 d1; core insertion annotated for die CTS, v5.0).
