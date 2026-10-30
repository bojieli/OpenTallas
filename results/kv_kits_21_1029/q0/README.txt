KV-KITS-21 q0 ECTL LEC (KV-014) root cause + RTL fix (2026-10-29)

Failing proof: Codex kit codex-kv-1028/ectl/fp/kits/qkd_ectlk_q0__216x172.8 (intel1 scratch), lec.py df83, KEEP FAIL
cp 18976 / proved 18704 / differs 272, + 128 kept lmax_i bits "not flops of their own name".

Root cause [CHECKED: lec.json failing list + flop census of the kit's 1_2_yosys.v]:
all q0 leaves are HEADS=1 / STATIC_QK=1 (qkd_ectl_native_direct_tp8.sv, qkd_ectl_c_st.sv). Three RTL registers carry an
ELABORATED CONSTANT through UNRESET state; yosys folds them to the constant (legal for an X power-up), but the gold side
keeps them as free X state that the sequential LEC cannot give a base case within the reset window:
 (1) ot_qkd_ectl_part u_tag: ot_hdc_delay W12 D=SCD-1 (unreset data line) carries {c_g, c_pidx}; c_g == 0 for HEADS 1.
     Gate: sc_addr[11] constant -> lmax/lmax_i[255:128] removed in all 3 leaves. Gold: sc_addr[11] X for SCD edges ->
     128 lmax + 128 lmax_i (u_c) + 6 lmax_any/lmax_any_i differ (= 262).
 (2) ot_qkd_ectl_part rq_g / rq_v: unreset load-enable regs loaded only with 0 (rg_g == 0 for HEADS 1; rq_v <= 0 in a
     QK-only engine). Load-enable = D reads Q, so no reset-window base case at all -> 2 g_rq[].u_d.q stages differ (4 with
     their alias captures in the Codex coupon).
 (3) qkd_static_k_issuer ident[0:RESPONSE_LAT=80]: 36-bit unreset line of {req_epoch, req_layer, req_t}; req_t[13] is
     {1'b0,...}. Gate: ident[*][13] (81 flops) + req_t_i[13] removed (census: ident bits 0..35 except 13, 81 each).
     Gold: 82-edge X chain > any reset window (16-edge KV contract included) -> fault, fault_i differ.
Not the cause: the ECTLK face-port transform (private port flops) -- its twin flops are matched by name; q3 (no exposed
leaf ports, transform inert) is EQ 9742/9742 with the same leaves.

Fix (main RTL, all values identical on every edge, no cycle/port change; ectlk_face_ports.py transform output
re-generated from the fixed sources = the kit files, CHECKED cmp):
 (1) u_tag W = HEADS==2 ? 12 : 11, tag_sc[11] = 1'b0 for HEADS 1 (HEADS 2 path unchanged: same W12 line).
 (2) rqd_s uses rq_g_o = HEADS==2 ? rq_g : 0 and rq_v_o = (STATIC_QK || KVD_QK_ONLY) ? 0 : rq_v.
 (3) ident holds the 35 live bits; compare re-inserts the constant 0 at bit 13.
Proof runs (lec.py against the EXISTING Codex netlist synthesised from the OLD RTL, so EQ also shows old netlist ==
new RTL): intel1:/srv/opentallas-scratch2/claude/kv-kits-21-1029/q0lec/{A (default 4-edge window), B (+ KV reset
contract 16 edges)}/qkd_ectlk_q0__216x172.8/lec_run.log + lec/lec.json.
Random-stimulus iverilog lockstep old vs new kit RTL: traces identical 3000 cyc, but mutant controls NOT caught
(stimulus does not exercise the engine) -> the sim is NOT evidence; the LEC is.
