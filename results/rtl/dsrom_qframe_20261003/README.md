# DS ROM q-frame signoff verdicts (collected 2026-10-04)
- A_r3_mig (521.64x178.47 um, util 0.60): DRC/DRV clean; FAIL SS setup -201.1 ps, FF hold -204.8 ps (verdict_A_r3_mig.json).
- B_r3_mig (521.64x223.02 um, util 0.48): DRC clean, 1 slew + 1 cap DRV; FAIL SS setup -213 ps, FF hold -205 ps (verdict_B_r3_mig.json).
- D_r2 (envelope 510.84x151.2 um, die 77,239 um2, util 0.726): routes DRC/antenna clean (0 final violations), 1 slew + 1 cap + 1 fanout DRV; FAIL SS setup -199.8 ps (TNS -448.5 ns), FF hold -210.0 ps (verdict_D_r2.json).
- C_r2_mig (p12q9 frame, util 0.86): still routing on ot-epyc1tb at collection, no verdict.
Policy: SS setup >= 0 at 60 ps, FF hold >= 0 at 25 ps; none passes timing. Timing fix owned by claude/dsrom-qelem-pipeline-20261003.
