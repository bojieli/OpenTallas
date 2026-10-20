# S81 shallow-payload repair + opt-in M8 RC (66736dcff) — paired ROOT suites
Base = main fe39a70ac, candidate = 66736dcff (Codex ROOT-CODEX-1245, fleet ep5 unit 2520299).
closure_loop 19F/1151P both, ref_tile 184F/691P both (identical failure IDs, NEW 0); die_repeaters 25 PASS base / 26 PASS cand.
Local test_fclk_pairing.py 16 PASS. M8 RC is opt-in; default M7/M4 repeater RC unchanged. fclk_audit.tcl is not a daemon HELPER (no runtime sync).
Merged by ROOT10 10-20.
