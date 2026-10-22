# QW-TOK3 10-19: MU D2D image recompile + MU benches on it

- `d2d_cal_image_mu.svh` recompiled (D2D_MU=1 production compile, dv2f18dh2 MU seam 2,2,2,3,2,2/11,11,9,9,9,9,9):
  TXDP C [8,3,1,10] K [21,4,3,3] (was stale [8,3,1,9]/[23]). MU0 recompile byte-identical to committed d2d_cal_image.svh.
- `sysface_mu1.out`: run_sys_face_bench.sh D2D_MU=1 on it: MUT0 PASS (4 head ctx, boot 54, 1512 events exact), MUT1..7 FAIL.
- `kvctx_benches.out` + `kvctx_*.out`: run_mu_kvctx.sh pass mut (CAL mode, both dies' real D2D sequencers + MU image),
  Verilator 5.050 ot-epyc7: mu_image == compiler, positive MU_KVCTX_PASS, k1/k2/k3/r1/c1 MU_KVCTX_FAIL -> BENCHES PASS.
- `kvctx_pass_r1_c8none_benchgap.out`: first run, positive failed only C8 'user carrier = None' because tb_mu_kvctx did not
  log CTXU (bench gap; probe added in this branch). Preserved.
Component/link scope only: no KV release GEN, no full layer, no independent-request numerics.
