HF-5a 2026-10-18: fc_t native verdict = BIND the exact-pin closed record, no new route.
The HF-5 audit (results/arch/hf5_1018/native) used record 833f5b2c9 = job smh_fct_ref_p45-r1-a9afd2404-lf, the route that
ignored the exact io_tcl (region-grouped pins: DEF r0a at the E face y 0.7-51, u_a0 flops at the W edge x 2-23 -> 216 um
of wire, launch 313 ps).  The same kit re-routed on main with the exact pins (job smh_fct_ref_p45-r1-9214bae8b, CLOSED
TT +301.33 / FF +23.90 DRC 0, record branch codex/closure-record-smh_fct_ref_p45-r1-9214bae8b @ 73093766f) audits
BINDABLE: launch 205.3 (r0a[229]) <= 220, capture 156.5 <= 190, boundary spread TT 44.6 / FF 41.8.  0 cycles.
Re-run: python3 results/arch/hf5_1018/native/run_audit.py <repo> <dir with views.tsv and v/73093766f/<view>>.
