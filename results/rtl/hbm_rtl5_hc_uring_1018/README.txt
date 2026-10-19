HBM-RTL5 10-18: d4g HC U-ring b7->b0 die relay (coordinator 0fi), ring lockstep vs the single-block golden.
Fleet dir ot-epyc4:/srv/opentallas-scratch/claude/hbmrtl5-hc (src = hbmb-rtl2b bundle + this branch's qeng/tb + ot_hbm_rly.sv;
cases from tools/rtl_hbm_hc_eng_static_gate.py --split --rs 104: probe, p1/p2 at --raw0 167, p1 at --raw0 165 (= old s_p1, identical)).
Builds (bench.sh TAG MUT DEFS CASE:OUT):
  u0  DRLY 2 XRLY 1 QDRLY 2 MUT 0: probe (expect first PROBE raw t = TL + 167 = 2197), p1/p2 raw0 167 PASS, p1 raw0 165 FAIL
      (mutant: compiler keeps the old RAW0)
  u1  DRLY 2 XRLY 1 QDRLY 1 MUT 0: p1 raw0 167 FAIL (mutant: root not told about the relay)
  u2  DRLY 2 XRLY 1 QDRLY 2 MUT 1: p1 raw0 167 FAIL (bank-3 rotation mutant, U form)
  d0  defaults (XRLY 0) MUT 0: p1 raw0 165 PASS (default ring form unchanged by the XRLY edit)
Verdicts: out/verdict_<tag>.txt, logs out/<case>/run.log.
