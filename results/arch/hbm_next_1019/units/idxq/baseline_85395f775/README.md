# IDXQ baseline immutable evidence

Source bundle 85395f775, baseline CW0/RS0 with the done-edge expectation corrected. Verilator 5.050, ot-epyc4; finished 2026-10-19 07:49:58 PT, SUMMARY unexpected=0, ot-run command exit 0. N1/N2/N4/N6 bit-exact with zero oracle mismatches. Done shifts +8 edges (2+CHAIN), row II stays232. Chain13 and mutants m2/m3/m4/m6/m7/m8 fail as intended; all run logs, source SHA256 manifest, tool version and verdict are retained here.

This establishes the baseline done-timing correction only. It does not qualify CW2/RS1 source bundle859b27b6b, whose lockstep build remains running; the IDXQ programme merge and qctl submission still wait for that source-specific PASS.
