# KV-DCAL2 10-19: token-run CONTEXT slot after RESULT(n) at the KV HOST (KV-EMB2 d9631325d ask)

Compiler: tools/qwen_split/d2d_link_calendar.py --ctx-host-req H [--emb-fill-edges F]
(production script env D2D_CTX_HOST_REQ / D2D_EMB_FILL). Default off: the MU production image is byte-identical
to rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu.svh (K22, TXDP_K 0x03030416) - checked.

Rule: CONTEXT (S->C port 1 kind 12 beat 0) at max(PREC_K0, RESULT(n)@KV HOST + H); the MU beat-1 slot one edge
before it; the C->S kind-14 WITNESS moves with it (ctx + txl + phy + 12). One static slot serves prompt and generated tokens.

Price (MU production seam 2,2,2,3,2,2/11,11,9,9,9,9,9, kv codec 2, host stages 0, pinreg):
| H (HOST RESULT->context edges) | CONTEXT slot | moved | fill budget to header slot 191 | token period | busy seg1 | entries |
|---|---|---|---|---|---|---|
| 0 | 21 | +18 | 170 | 249,600 (unchanged) | 2710 (unchanged) | unchanged |
| 4 | 25 | +22 | 166 | unchanged | unchanged | unchanged |
| 8 | 29 | +26 | 162 | unchanged | unchanged | unchanged |
RESULT(n) at KV HOST = 21 (send 2 + 1 + txl 8 + phy 7 + 2 + 1 + host 0). TXDP unchanged.
Token cost 0 edges unless F = fork ages + 2 + join4_cal last + 1 exceeds the budget (then the embed window grows by
the shortfall; the compiler fails closed with that number).

OPEN (owners): H must be MEASURED by the KV HOST lane (KV-HOST2); F from the kvjc3 join calendar + the die fork ages
(KV-EMB2 / KV-GEN9). Adoption = a NEW dcal image (seg1 K TX / C RX dt words and the target-11 K words change), so it
rides the next dcal image successor (bc4 generator gen_dcal_bc4.py refuses any image but K22 -> regenerate + re-harden
with the image; compute-side qfd_sys_face consumes the same C RX words).
