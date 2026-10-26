TOKg 10-23: HBM token rec2 root cause after the ring-calendar correction.
Source d34578d6f (r18h5 SOURCE die.v, slice binary sha 273a0824...), fixtures ~/scratch/tok-func-hbm/rsrc/L00.
1. Codex rec2 pair (ep9): corrected_rec2 FAIL 97/287, hcollgl_SW fault @317 (all 120 ring-output checks PASS, hcollb fault cleared);
   negative_omit_bccw FAIL 127/287 + hcollb fault + 20 B-CCW ring-output fails => ingress 6/18/4/20, launch 48 causally confirmed.
2. Residual = die assembly: ot_hgi_coll_gq_land samples pa (ring A ag), pb (ring B ag) at the same fixed stage after ld_ev; RTL
   contract wires all direct. r18h5 die.v relay edges pa/pb/ld_ev: SW 3/0/0, NW 1/1/0, NE 3/0/0, SE 5/1/0 (skew_all.json, trace_pa.py).
3. Causal bench (tb_coll_replay.sv, new PA_DLY param, default 0 = unchanged; Verilator 5.050 ep9, run_pad.sh):
   PA_DLY=0 12/12 DS L0 COLL records PASS; PA_DLY=1 and =3 12/12 FAIL (bench_results.txt). One extra edge on the A publish lane breaks the gather.
Fix owner: HBM die generator (l6_collq/L12 relay insertion): {pa,pb,ld_*} into each hcollgl must be one equal-depth landed group
(co-locate hcollgl at the ring ag faces, or pad + a landing-delay parameter). Not a compiler calendar issue.
