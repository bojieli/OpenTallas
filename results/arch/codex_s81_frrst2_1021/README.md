# FRRST2 forwarded reset soft-clock repair

Candidate helper source on main base14cfd03e7. No deployed helper, physical gate, closure or submission.

All four original h9/h10 rf3r/rf3rl gates failed OT_MULTI_ROOT unowned u_xrl0.reset_pipe[0]$_DFF_PN0_. Original logs remain /home/ubuntu/scratch/frrst/gate_col_h{9,10}_rf3r{,l}.{log,json}; original source snapshots0033c8a5e/387cf605c remain authoritative.

The original frame source branch claude/s81-frame-rf3r-1020 contains the real per-xk async-assert, 2-edge synchronous-deassert ot_reset_sync. This candidate changes no RTL, no latency and no geometry. ROOT must integrate that source separately if absent from main. Apply forwarded_soft_clock_spec.json to a fresh successor of each rf3rl frame spec. Names are exact actual mapped instances from the failed flow, never wildcard ownership. Wrong/missing clock ancestry or extra soft consumers fails closed.

The helper creates actual per-bit clocks with the owning domain period. They remain separate from regional CTS; it propagates them, retains normal setup/hold/recovery/removal and uncertainty, checks complete exact mapped soft sink membership and structural ancestry, and includes soft arrivals in the forwarded-clock spread. No false path/multicycle, Liberty edits, ties, reset removal or move to ck_r0.

Qualification limit: three pure spec/default-byte/refusal tests pass. An initial tiny actual OpenROAD fixture accidentally auto-ran locally through the existing test availability probe; it failed early because CTS metadata was not initialized. The candidate now emits forwarded metadata with clocks, and tests require an explicit fleet-only environment flag. The actual fixture has NOT been rerun after this repair: owner instructed no more checks or validations, push closures first. Therefore this packet is SOURCE CANDIDATE / ROOT REVIEW REQUIRED, not a passing gate claim. No fleet fixture job was launched. Harmless source-only staging directories exist on EPYC5/7/9.

Actual selected rf3rl h9 has115 hard children, outline1436.832x3369.6; h10 has123,1436.832x3672. These contain production l4 LP child counts. Five h9 plus two h10 sum24192um; +760streets+250top =25202 before any extra band. No compact reset-landed closed frame is available in this packet.
