# CAPC2 bench receipt (LEAD2-S81/CAPC2 10-19, Verilator 5.050 on ot-epyc6, src = claude/s81-capc2-cal-1019)
| bench | DUT | result |
|---|---|---|
| gold_base | cap_p1 PINPIPE1 EDLY24 WL3DLY16, golden vectors + s_16_24 launch advance | PASS rows 1280/1280 at W+2, arrivals 7446/7446, fault 0 |
| gold_m23 | EDLY 23 (mutant) | FAIL (missing / wrong writes) = expected |
| gold_m15 | WL3DLY 15 (mutant) | FAIL (wrong writes) = expected |
| cal_base | DUT vs closed 3-child RTL + TB delays (real vectors, unadvanced) | PASS 166/166 equal writes, equal fault/fcause |
| cal_m23 / cal_m15 | mutants | FAIL = expected |
| p1_exact_edly0 | cap_p1 PINPIPE1 EDLY0 (the closed 267b RTL) after the edits | PASS 1280/1280, 7446/7446 |
Schedule: +24 edges on E-column words, +16 on W lane-3 words (compiler s_16_24) on top of PINPIPE +1/+1, reset +2.
