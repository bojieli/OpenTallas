# qfd_sys_face_mu_dhobs d2 (QW-MU 10-20; fallback _b = same RTL/pins, PD 0.35). CRITICAL prefix (qfd_sys_face): COORD review, no submit.
Die-level tt_ctlm.dh_user observer (inst mu_dhobs) = qfd_sys_face_mu_dhuser NU 4 OPSEG 0 with the compiled lists.
d2 vs d1 (COORD 16:30 10-19): DHREG 1 -- dh_user is a 2-b output flop (+1 edge, unpriced: release ctlm OPSEG 1 ignores dh_user, USER_SEQ 0).
Bench (Verilator 5.050, fleet oth-ubuntu-2362006-1792564029): tb_dhobs 1800 h_starts PASS, bad stage PASS, MUT 2 FAIL.
SAFE-DESIGN checklist: 1 every output a flop, no in->out path (fixed); reset 2-stage landing. 2 reach n/a (43.2 um). 3 ~11-60 flops, reset < 32.
4 one compare level. 5 no storage. 6 outline 43.2 = die slot (dv_case DHOBS_WH) = minimum lattice tile for 193 face pins; util ~1% is
pin-bound (waived under the freeze); pins = GEN frame (out/pins/qfd_sys_face_mu_dhobs.json). 7 single root. 8 static; +1 edge on dh_user only.
Why not "the k3 leaf in GEN": k3 = qfd_sys_face_mu_dhuser OPSEG 1 PINREG 1 is already INSIDE qfd_tt_ctlm_dv (u_leaf / u_gi.g_op.u_leaf)
and its dh_user is `assign 2'd0`; dhobs is the real die driver of tt_ctlm.dh_user (port_bind PASS, input_tied none).
