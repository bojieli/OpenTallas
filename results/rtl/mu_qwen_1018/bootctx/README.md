# MU-DQ-BOOTCTX (2026-10-19): compute-side consumer of the fillers' runtime initial context

Coordinator 0kg (1), rescoped by COORD after MU-KV-CTX (claude/mu-kv-ctx-1019 7eea9df20): the record format and KV side
are MU-KV-CTX's (2nd kind-12 HOST context slot on d2d port 1, TAG user = epoch[1:0]; leaf rtl/qwen_split/mu/qfd_mu_ctx_rx.sv;
spec lanes/MU-QW-DIE.md). Branch claude/mu-dq-bootctx2-1019 (from claude/mu-die-qw2-1019 86a80287a + MU-DQ-DHUSER
28450899c). The earlier own-record design on claude/mu-dq-bootctx-1019 (kind-12 DATA field) is DROPPED (superseded).

## RTL
- qfd_tt_ctlm_dv: param CTX_SRC (0 = unchanged, ctx_x ignored), new input ctx_x[128:0] = {load, CTX} (boot-record layout).
  Pin register ctx_q (+1 edge), then the SAME check / load path as the DW5/DW6 boot record (which stays the boot default).
  Rule: a runtime load must not share its edge with a leaf start or a filler result of a filler in its mask, nor with a
  boot-record load -> sticky op_fault, nothing loaded. MUT 33 (bench): rule not checked. Cost ~130 flops, 0 edges on
  existing paths.
- qfd_mu_ctx_rx_die (in qfd_mu_ctx_rx.sv): whole-port die form (prog_context_slot, prog_rx_v, rx_payload[547:0]); the die
  bus model has no part-select endpoints, so 453 rx_payload inputs are unused pins (follow-up: GEN part-select endpoints).
- Filler native59 contexts (COORD add-on, from MU-DQ-D2DUSER; ctlm FCTX, NCTX_BASE 0x10): the hard head raises
  layer_context_v only for prog_base 0, the fillers' attention ops are LOCAL SEG at base 0x10. The ctlm now raises
  layer_context_v for a filler head start at base 0x10 on the head's edge (start + 2) with native_tok / native_pos from its
  own 2-edge copy of the start (user on [17:16], D2DUSER carrier), held like the head's latch. Bench finding: taking the
  head's latch instead gave user 0's tok/pos whenever the busy head did not accept the filler start. MUT 35: not raised.
- qfd_sys_face / qfd_sys_face_record_port / qfd_host_native_context_rx: param MU_HEAD (0 = unchanged): the HOST-context
  check on the head's layer context applies to user 0 only (head_position[17:16] == 0); filler contexts are native59 NU 4's.
  The closed face faulted on every filler context before. Re-close owner MU-DQ-SYSFACE (die_params sets MU_HEAD 1).
## GEN (tools/qwen_split)
dv_case._ctxrx_inst / _ctxrx_buses: instance mu_ctxrx above sys_face's N face (OT_SPLIT_DV_CTXRX_XY override, fail closed on
overlap), one more endpoint on the face's prog_context_slot / prog_rx_v / rx_payload nets, sys_face's clock / reset, and
dvw_mu_ctxrx_ctx_x (129 b) -> tt_ctlm.ctx_x; no tie anywhere (missing net / port = GEN error). die_params: tt_ctlm CTX_SRC 1,
leaf NU (audit: same NU, CTX_SRC 1). test_ctxrx.py. A real GEN + strict bind run is owed by MU-DIE-QW (next dv2f18 GEN).
## native59 / face host_tag audit (COORD item c): HARMLESS by schedule
The MU slot puts the filler TAG on the face's host_tag / host_epoch / host_generation and token register for the edges
between the two context receives (token-run RX 18 -> 19, + the face / native59 pin registers). Consumers and when they sample:
- native59 qfd_native59_command_context: only on context_v (tt layer_context_v with stage 1..36) and request_slot
  (native_cmd[0]), both inside decode layers, i.e. after the L0 h_start (T cycle C0 + 272 in the bench calendar) -- never
  in the token-run context window; by then the 2nd (user-0) receive has restored user 0's TAG.
- face: tok/pos (ev_res at the LM head; EMB fill at E cycle 5 = BEFORE the window, using the argmax token; EMBW expected
  token / epoch from E cycle 191; core epoch at core_start), result_tag (RESULT capture at the LM head), status_epoch16
  (STATUS slots in layers; the token-run kind-15 RESULT is at run cycle 2, before the window). None samples in the window.
So no fix; a compiler rule keeps it so: no face/native59 host_* consumer event within [MU slot RX, user-0 slot RX + 2].
## Kits / views
- qfd_tt_ctlm_dv (+ landed lpf / lpf_lp, CRITICAL): new port ctx_x + CTX_SRC loader + FCTX filler contexts -> MU-DQ-CTLMCLK
  must port them into the landed form (ctx_x into u_gi core region with its pin register; fcx / ov copy beside the head
  outputs in the hr region; lp regen) and regate. OPSEG 0 / CTX_SRC 0 / FCTX 0 unchanged.
- qfd_sys_face: MU_HEAD 1 view (MU-DQ-SYSFACE re-close).
- mu_ctxrx leaf (qfd_mu_ctx_rx_die): new die-top leaf, needs a kit / closed view (43.2 x 97.2 um outline in the GEN).
- qfd_d2d_static: unchanged.
## Benches (fleet ot-epyc8, Verilator 5.050; source c27f337fd) -- logs in witness/
- run_mu_opseg.sh pass: MU_OPSEG_PASS (red, ctx_part, d2d_ctx, neg_drift, neg_coll, neg_ctx, neg_xcoll, full; incl.
  MU-DQ-D2DUSER's C8). d2d_ctx: MU-slot kind-12 records for users 1/2/3 through the REAL face receiver (accepts them) +
  qfd_mu_ctx_rx_die -> ctx_x, loaded on slot + 2 while each filler is idle (C9), bank / EMB / SEG follow (C5, C7).
  neg_xcoll: a load on the bank-write edge of the same filler's result -> op_fault, nothing loaded.
  C10 filler native contexts: red 108 (u1/u2/u3 = 60/30/18), full 1,089 (544/291/254), each on start + 2 with the
  filler's tok and {user, pos}; user-0 contexts identical to the NU 1 reference. (Vehicle limit: the bench head has no ME
  returns, so after its first start it never goes idle -- 1 user-0 context per run; acceptance is not modelled.)
- run_mu_opseg.sh mut: 21..29, 32 FAIL as before; 33 (load rule unchecked) FAIL neg_xcoll; 34 (leaf MUT 1, wrong user)
  FAIL d2d_ctx C9/C5; 35 (filler context not raised) FAIL red C10. Regexes: `MU_OPSEG_FAIL mut 33: neg_xcoll`,
  `MU_OPSEG_FAIL mut 34: d2d_ctx C9`, `MU_OPSEG_FAIL mut 35: red C10`.
- run_mu_ctlm.sh mu prog lp eq seq: PASS (OPSEG 0 / CTX_SRC 0 / FCTX 0 unchanged; landed lpf eq PASS -- lpf does not have
  ctx_x / FCTX yet, see Kits).
- run_sys_face_bench.sh (MU_HEAD 0): SYS_FACE_PASS, MUT 1..5 FAIL; qfd_sys_face lint MU_HEAD 0 / 1 clean;
  test_ctxrx.py + test_dhobs.py ok.
