# G-XS4-SELECTOR: one ot_s81sl_xs4 source (RTLGAP-G9, 2026-10-22)

Three definitions were live: 974ec6f3 (4620453ba, original xgt_xo), b4d95e79 (2d1106663/5feb5dc07 census fix,
= main and the cap18 strict PB `chosen`), 50485a59 (f5f35855d = 8a495768f rtl_extra override used by GEN / dv_rvcase).
Lineage 974ec -> b4d95e -> 7299701d (ca3dcfdfb: c41af8f64 bdec parity + 9e1590308 kept hb_q copy) -> 50485a (f5f35855d:
hb_q1 enables on spare same-release leaves, kept wps split).  All successors are value-preserving, 0 cycles, same
ot_s81sl_xs4 top ports (xs4_ctl gains an internal hbk_o used only inside the file).  b4d95e FAILS the native census
(r3 33/3); 50485a PASSES it (MAIN+FB gate-flow native max 32 / 0 violations, receipt 7800bff3c).

DECISION: the die binds 50485a59 only.  This commit puts it on main, so the strict port bind (src) and the GEN
override (rtl_extra 8a) select byte-identical files and the selector divergence disappears for every die after the
merge (cap18 PB 528fc3c9f still records src b4d95e as `chosen` with 8a as `differ`/`iface_differ` -> re-bind).
Bench (this file, Verilator 5.050, tools/s81_slice/xs4_equiv.sh at f5f35855d): 21/21 cases PASS (7 legal production
L0/L2 programmes, 2 late-offset faults, 10 fault injections, 2 in-flight resets) = cycle-equivalent to main
ot_s81sl_xs; mutant OT_S81SL_XS4_MUT_WCOPY: both listed cases FAIL as required (caught).
