SEG_CAL port validation on fleet Verilator 5.050, source ff9abcf4f (manifest committed).
Both HARD_HR=0/1: default image PASS 123/123; LM-head image PASS 131/131.
Both: MUT36 FAIL128/131 (missing head issue/ROM), MUT37 FAIL130/131 (XPF fault), BMUT3 FAIL129/131 (G row one edge late).
Original OT_SEG_MUT harness error retained in codex_r1; absolute filename exceeded SV 128-byte buffer. Bench now sends relative EV/LOG filenames and resolves work directory. codex_r3 reuses the exact original binaries; OT_SEG_MUT behavioral FAIL126/131 both HARD_HR modes, head fault at24695. Original binary build logs retained.
SEG_CAL default0 and hard-leaf SEGCAL default0 remain opt-in. No compiled image edits, adoption, physical closure or MU programme replay claimed. Source port adds zero issue cycles. Hardening and mapped native census still owed; legacy h16c reset/control fanout must pass the new <=32 rule before any layout gate.
