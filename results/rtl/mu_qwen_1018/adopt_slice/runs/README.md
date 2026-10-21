# MU-ADOPT-SLICE witnesses (R4 per-user chunked LM-head argmax in qfd_dv_slice2 / _w / _e)

Source: claude/mu-adopt-slice-1019 @a540f1f9f (each `.out` header names host, time and commit). Fleet ot-epyc4 / ot-epyc5 via
ot-run, Verilator 5.050 (verilator_version_*.txt), one Verilator build per ot-run job (cases sharing a build ran sequentially
in one job). Script: `../run_group.sh` (groups ONE / FONE / DHUSER; the F0/F1/F2/NEG/FACES case set). Memory: dv_bench2
2-slice builds ~16 GB, tb_qfd_dv2_faces ~20 GB, bench h (12-slice chain) > 50 GB.

## Root cause of the bench m failure (fixed in a540f1f9f)
Every user's token came out as the same row (e.g. 383 = the largest head of the round). The per-user slice argmax
(qfd_dv_amax_mu) was right; the ROOT merge (qfd_dv_scalar2 am_best / amc) restarts only on a ROOT cfg, and bench m issues one
ROOT cfg for the whole run (as a 4-user calendar must: a ROOT cfg per user token would also clear the PSUM slots of other
users' reductions in flight). So after the first token the root kept the largest candidate ever seen. RTL fix:
qfd_dv_scalar2 MU_NU > 1 clears am_best on the token edge and broadcasts the latched tok_idx (MU_NU 1 statement for statement
unchanged; slice2 passes MU_NU). Mutant AM_MUT 6 (= scalar2 MU_MUT 1) removes the restart and reproduces the failure.
Not an F-TOK-1 / stn_pend effect: at gaps >= 16 no fault fires. Gaps 12 / 14 DO fire the stn_pend fault (the next STN issues
while the previous op's results are still pending) -> correct per F-TOK-1, moved from positive to NEG (NEG_m_gap12_stnpend).

## Results
Positive (PASS): F{0,1,2}_nu{1,4}_ag (benches a-g, i, j on master / W face / E face at MU_NU 1 and 4); F{0,1,2}_nu4_m_s21/s22
(4 users, chunked heads interleaved op by op, 8/8); F0_nu4_m_gap16/20/24/30 (8/8); F{0,1,2}_nu4_o (stn overlap faults, legal
does not); FACES_mut0_nu1/nu4 (W1 W0 E0 E1 chain); dhuser_pass_s7/s11, dhuser_slip_pass; F0_nu{1,4}_h (see below).
Negative (FAIL as wanted): NEG_m_nu1_w (MU_NU 1: heads collide), NEG_m_am1..4 (qfd_dv_amax_mu mutants), NEG_m_am2_e (E face),
NEG_m_am6_rootnoclr (root merge not restarted), NEG_m_gap12_stnpend (stn_pend fault), NEG_o_am5 / NEG_o_nu1_w (overlap not
faulted), NEG_i_mut11_nu4, NEG_j_mut12_nu4, FACES_mut11_nu4 / FACES_mut12_nu4, dhuser_mut1 / mut3 / mut2_slip.
