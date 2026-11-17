# S4q9l2 self-review (QC-PLAN-R, Opus; Fable at its weekly limit until 11-22, per COORD 19:3x)

Plan 19be3f0a3bb42d8e = L 50d472e1a81f + clock tol need+10 + 24 tail1 param_wrap rows + source text. Bind S4Q9L2BQ (epyc2 fable-fix-qc-knee-hc/bind).

Verdict: ADOPT-OK, to be adopted after the Kf atomic apply.

(a) Clock tol +10. Measured delta per port vs L:
- +10.0 on 2,603 ports. These are the multi-instance edge ports; L had 2,591 ports with tol > 10.
- +0.1 on 9,929 single-instance ports (floor 10 -> 10.1), so the floor ports are not widened.
- The remaining ports gain between +0.2 and +9.9.

Max tol goes from 129.1 to 139.1. The offsets are unchanged: 0 mismatches against a re-derive from the S4q9c routed proof. tap_offset_gate is PASS 0/84,512. By construction every instance sits at least 10 ps inside its band. The cost is a kit early/late source latency at most 10 ps wider per port, against a die TT intra setup of +362 ps. No measured finding.

(b) tail1 rows.
- Bind errors are 0 and HARD_CORE_PARAM shows 0 mismatches over 20 param_wrap types. The bound RTL params equal the signed masters on all 24 instances; the 24 HARD_CORE_PARAM rows seen in the earlier D/E binds are gone.
- Plan pins_file y958 vs the 4 signed views (pins.json): both have 560 pins, with the same faces and layers. 138 S-face pins differ by 0.006 um in y (0.048 vs 0.042, a pin-centre snap). 8 scalar ports differ only in name form (bt_re vs bt_re[0]).
- Not a finding.

(c) Structural diff L -> L2: only these changed:
- clock.tap_offset (15,391 ports + source text);
- the top-level note;
- hard_cores[11..14] of the 6 st_a_v1 types (module, physical_master, param_wrap, note).

Gates: errors 0, r8rc 0, LATCHECK 1921/1921, hcparam 0. G0 shows only the 2 inherited face errors (sl_W5_fw.W, coll_f4.E); these are fixed in S4q9l2d a915f1136c27, which has G0 0.
