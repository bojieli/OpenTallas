TOK-KV-RT20 2026-10-28 07:51 PDT. KV token test, RT20 bind (DIE-KV-8 bind_s2, intel1:/srv/opentallas-scratch2/claude/die-kv-8-1028/bind_s2,
recipe_kv8: no PV calendar restore, no vport_request_extra) vs pair image codex c2d5fd4d76 (bind4).
Tools: main regen_constants.py + c2d5fd4d76 recipe kv_boot_v36.py prep (asbuilt_rtl6 of that image), python:3.11 docker on intel1.
Control: the same prep on bind4 reproduces the c2d5fd4d76 prep_native2 output byte-for-byte (JSON equal).
RESULT: FAIL before simulation - no valid boot image can be compiled for RT20.
 1 VPORT_RT 66..74 on all 16 vports > RTL bound 63 (u_vport_E/W) / 31 (vport_* top) -> kv_bootage boot_error; cfg_age word rejected (age_bad).
 2 DQ<=15 rule re-derived on bind_s2 (DQ_p = max_q(W_q+RT_q) - (W_p+RT_p)): unpadded DQ 0..108 (12/16 > 15);
   W request lane pads needed 0..93 stages/port, 9720 FF (bind4: 0..15, 0 pads). PV RL 131->190, FIA 132->191.
 3 PV calendar: pv_trunk law TRUNK_D/FLAG_D 63/77 (S), 65/75 (N), column deltas NOT uniform -> TRUNK_D/FLAG_D alone cannot
   keep the invariant; bound RTL keeps 54/58 -> MISMATCH. PV entry pads/restore are needed.
 4 Pair image: RT20 KV seams 88,88,86,86,86,83,83 (image 56,56,54,54,54,56,56); TXDP law 0x030304ad [173,4,3,3] vs bound 0x03030472.
tok/s: not measured (no image). Previous KV number 4051.0 tok/s (QCE 296341 cyc @833 ps; 4050.5 with +36). Estimate UNCHECKED:
 each attn_kv cycle/layer costs 36 cyc/token (accepted_cost DAG); +59/layer (PV RL) -> 4022.2 tok/s (-0.71%).
