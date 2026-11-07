# HBM-GAPS-8 11-06 SVGR_TOP RE-FORM P1 proofs

- Flag-off (P1=0 default) = unchanged: yosys equiv_make/equiv_simple/equiv_induct (fv/eqoff.sh, fv/runfv4.sh):
  issuer 3467/3467, cache136 PASS, ot_svgr_top_cachecut (kit params) 54727/54727 equiv cells proven.
- issuer MPIPE registered match: match_q == (ids_ok_q && ids_layer_q==layer_q) by sat -tempinduct
  (fv/match.ys ID_COHORT=1, fv/match0.ys ID_COHORT=0): SUCCESS; mutant fv/match_mut.ys: FAIL (caught).
- P1=1 behaviour: SMB_UNIT lock-step bench (bench/mkbench_hg8.sh + one_hg8.sh, src_rf1 base of hbm-gaps-5-lec):
  k0, k0il, k1 (P1), k1il (P1+OPEN_IL) PASS ops=20 gos=29/29 go_slots_exact=True fault=None, cycles 12764 identical
  (no go-slot / pin-cycle change). Mutants: m_odly, m_wa, m_mid FAIL; m_match passes the smoke bench and is
  caught by the induction proof above. Results: bench/out/rc.txt.
