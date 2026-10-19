Generated lp.py lockstep bench (random inputs, flat vs landed), Verilator 5.050, fleet ot-agidock128 unit oth-ubuntu-1589811-1792434822,
source a7d977887 (landed RTL byte-identical to safe1/5825f8e82).
- AUDIT PASS; AUDIT-UNLAND FAIL (expected).
- MUT1 FAIL 10,604 / MUT2 FAIL 8,362 mismatches (mutants detected).
- MUT0 FAIL 12 of 50,371: ONLY port dc, cycles 37-48 (reset release at 16; bench warm window 36). The core-sourced low dc bits read 0
  in the landed parent for 12 cycles longer than flat (landing warm-up after the regional reset tree); identical afterwards.
  MUT4 shows the same 12 (it was already "waived, not observable"). This is a post-reset status transient, not a data mismatch,
  but the bench is literally RED: fix = lp.py warm window derived from reset depth + landing K for every port (or zero-reset dc).
  Production-shape LANDED_LOCKSTEP (ctx_safe1 land0, 845k edges) PASS remains the functional witness.
