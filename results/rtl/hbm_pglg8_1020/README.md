HBM-PGLG8 10-20: lockstep tb_hbm_su_pgslice_rg with HREG=1 (rgf_lph: 4 hardened region tiles ot_hbm_su_pgrg_region) vs the
flat strapped pgslice_lg master, Verilator 5.050 on ot-epyc9 (tools/hbm_static/su_pgslice_rg_vl_run.sh OUT MUT EDGES 1).
m0 PASS checks=29952 (HREG=0 baseline identical PASS 29952). Mutants all FAIL: m1 fill early, m2 drain group flip,
m4 RF select early (region glue), m11 strap g ignored (class check), m20 relay short, m21/m23 face relay, m101/m103 lp landing.
b2 (10-21, src 37653f5fc, PAIR tiles ot_hbm_su_pgrg_pair, HREG=1, Verilator 5.050 ot-epyc9): m0 PASS checks=29952 (identical
to r1 / HREG=0); m1/2/4/20/21/23/101/103 LOCKSTEP MISMATCH FAIL, m11 CLASS CHECK FAIL. Logs b2/m*/bench.log.
