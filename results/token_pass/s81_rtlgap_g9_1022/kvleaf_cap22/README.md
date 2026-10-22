# G-KV-LEAF on the CURRENT die (cap22 MAIN) -- STW-S81c-RTLGAP3 10-22

Cut cut_3N_kv of bind die.v 1e188248 (cap22 MAIN; u_s_3N = ot_s81sl_slice_sukv_raw512, sid 7), DIE kit-wrapper sim
sources (die_sim_wrappers 7de9a2080), --landing-reset none, frame x-lane flight model (dv_slice_cut @4762b156b on this
branch = ck_r<k> clock ports + TOKc 47a6ef9b5). Programme: tools/s81_dv/tokfunc/kvleaf_prog.py --in-ports 1760..1763
--out-ports 1752..1755 (GK gain load + KV norm/RoPE/QDQ op 15 + 13 RDOUT), checked by kvleaf_check.py vs SU-golden expected.mem.

- base: KVLEAF_CHECK PASS, 13 beats, 392 words, 0 bad; fault_cycles 0 over 4300 cycles (the G9 block_fault[5] is gone
  with the frame-lane flight model: it was a bench gap, zero flight into K5 frame rings).
- mutant row 700 word0 bit30: FAIL, 25 bad words (caught).
Run host ot-epyc9, /srv/opentallas-scratch/claude/stw-s81c-g9c22/{out_cut_3N_kv_fx,kvleaf}.
