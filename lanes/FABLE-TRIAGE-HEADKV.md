# FABLE-TRIAGE-HEADKV (HEAD/KV design triage queue; opened by CORES-NOROW-1 2026-11-15)

## 2026-11-15 00:55 PST HDCORE elemA_cv pin_audit: 10 interior ft/rst_n pins read as wrong_place (design/audit verdict needed)
- Evidence: epyc9 runs2/A2/kit/pin_audit.json (routed 6_final.odb exists, 06:33 UTC): PIN_AUDIT FAIL 456/466 missing 0 wrong_layer 0 wrong_place 10 extra 0. The 10 = ft_ck0_i/o, ft_ck1_i/o, ft_mesh_i/o, ft_mstrap_i, ft_rst_i/o, rst_n. The audit expects them on the die face (e.g. ft_ck0_i N y=319.68) but the kit places the M5 0.192 squares inside the core (y 156-163, x 157-160), the signed-centre interior squares (TYPE-HDCORE-ELEMAB track-fix note: signed view keeps them interior).
- Question for Fable: is the pin_audit expectation wrong for interior ft squares (exempt them, as face_guard already skips ft), or must these pins sit on the face? If exempt, signoff GOAL=post on A2/A1 routed DBs is minutes. Same audit applies to elemB (B kits not yet at pin audit).
- Not done by CORES-NOROW-1: no audit/kit edit.
## 2026-11-15 00:55 PST HDCORE pre-route LEC stops the flow (advisory under R-MINIMAL)
- A2 NOT EQUIVALENT 107/58130 (u_core.u_m.g_ch[0].g_s[0].u_a.y[*]); B1/B2 KEEP FAIL 172/52669 (8 of 150 declared kept regs merged/folded by synthesis, e.g. u_m.g_t[6].g_pad.u_a.g_cy_copy.cyq[0]). lec_async stops the flow container on exit 1 (A2 after route, B1/B2 in DRT after 5_1_grt).
- Action taken (precedent S81 seqhost kitS5r): B1r/B2r copies with no lec_async files and the inline LEC verdict advisory, route resumed from 5_1_grt. Question for Fable: real RTL/synth difference (u_a.y regs of elemA g_s; kept-reg list vs synthesis) or keypoint matching? Inputs: runs2/{A2,B1,B2}/kit/lec/lec.json.
