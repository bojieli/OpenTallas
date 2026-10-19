# MU-DQ-BOOTCTX (2026-10-19): runtime filler initial context over the existing KV->compute D2D stream

Coordinator 0kg (1): each filler user's initial context (token / position of a new request) comes from the KV/system
die host plane over the EXISTING KV->compute D2D command/token stream; a ctlm boot-context loader on the compute die
consumes it. The DW5/DW6 image record (0ka) stays the boot default only.

## Path (no new D2D lane, slot or die port)
KV host plane -> qkd_host_native_context_tx (KV die, kind 12, compiled send slot) -> qkd d2d -> qfd_d2d_static ->
qfd_sys_face record port `prog_context_slot` (kind 12 HOST context, one per latency-user token run) ->
qfd_host_native_context_rx #(FILL 1) -> qfd_sys_face_fill_ctx (FILL_CTX 1) -> seq_dh DW lane -> qfd_tt_ctlm_dv dh pin ->
qfd_dv_cmd_cal_mu (CTX_DW: sealed-image DW5 = runtime word, ctx_rt) -> ctlm OPSEG loader (arm, apply on result seq).

## Record (kind 12 DATA[188:142], FILL 1 on both ends; FILL 0 = DATA[511:142] zero as before)
FC = {pos18 [188:171], tok18 [170:153], seq8 [152:145], user2 [144:143], v [142]}; all zero when v = 0; one filler per record.
Face -> ctlm word (dw_addr 5): {16'h4346 'CF', 2'b00, seq8, user2, tok18, pos18}, edge slot + 1, replaces the DW field.

## Semantics / static schedule
seq = index (mod 256) of the user's filler result, counted from its last boot-context load, that the context replaces:
on that result's edge tok_b/pos_b take {tok, pos} instead of {argmax, pos + 1}. Armed on slot + 4 edges (fill reg, dh
pin, ctx_rt, arm). Sticky op_fault and nothing armed on: tag / reserved bits, user 0 or >= NU, tok >= 151,936,
pos >= 8,192, a second record before the first applied, LATE or EARLY (seq != results so far, or the named result
lands on the arming edge). No credit / ready / wait anywhere.

## Cost
qfd_sys_face FILL_CTX 1: +116 flops (47 + 1 + 68 + fault), 0 edges on existing paths. ctlm OPSEG (flat and landed
u_gi): (NU-1) x 45 + pending flops (NU 4: ~180 incl. user 0 slots), 0 edges on existing paths.
qfd_dv_cmd_cal_mu: +1 flop (ctx_rt), dwr[5] reused.

## Benches (fleet ot-epyc8, Verilator 5.050)
Source 74316378a (flat ctlm / face / cal = 9bae4cdf4; 9bae4cdf4 adds the landed u_gi port + eq stimulus). Logs in witness/.
- run_mu_opseg.sh pass: MU_OPSEG_PASS mut 0, cases red ctx_part d2d_ctx neg_drift neg_coll neg_ctx neg_late full.
  d2d_ctx: users 1/2/3 records (seq 1/2/1) through the REAL qfd_host_native_context_rx FILL 1 + qfd_sys_face_fill_ctx,
  armed slot + 4, applied on the named result (C5 bank, C7 EMB = record token, C8 arms), user 0 identity (C2) kept.
  neg_late: record after its result -> op_fault on slot + 4, nothing armed.
- run_mu_opseg.sh mut: 21..29 FAIL as before; 32 (record armed into the wrong user) FAIL on d2d_ctx (C1/C5/C8);
  33 (seq / late check dropped) FAIL on neg_late (fault not raised). Fail regexes: `MU_OPSEG_FAIL mut 32: d2d_ctx C`,
  `MU_OPSEG_FAIL mut 33: neg_late: required fault not raised`.
- run_sys_face_bench.sh (FILL_CTX 0 face, iverilog): SYS_FACE_PASS MUT 0, MUT 1..5 FAIL (unchanged).
- Verilator 5.050 lint of qfd_sys_face FILL_CTX 0 and 1: 0 errors.
- Not covered: a full qfd_sys_face FILL_CTX 1 sim (the composition bench replicates its 1-line DW-field replace mux).

## Kits / views to regenerate (RTL changed)
- qfd_sys_face: only at FILL_CTX 1 (default 0 = bit-identical, closed view stays valid for FILL_CTX 0). Die GEN opt-in
  OT_QWEN_FILL_CTX=1 (tools/qwen_split/die_params.py) once a FILL_CTX 1 face view is closed.
- qfd_tt_ctlm_dv (+ lpf / lpf_lp landed form, u_gi; CRITICAL tile): OPSEG logic changed (loader + cal ctx_rt). MU kit
  (MU-DQ-CTLMKIT / CTLMCLK) must regen from this RTL; OPSEG 0 unchanged.
- KV die: qkd_host_native_context_tx FILL 1 emitter owed by MU-KV (NOTICE in lanes/MU-KV.md).
