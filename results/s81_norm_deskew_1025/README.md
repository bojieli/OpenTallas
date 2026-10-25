# S81 norm partial deskew

Adopted the paused S81 implementation without changing its RTL. The xrt1/xrt3 masters apply fixed partial delays [4,3,2,1,0] to the five consecutive per-leaf partial arrivals. The collector still requires all five valids together and faults on any incomplete set. Data has no reset; only valid state resets. `PDSK=0` preserves the previous aligned interface.

Latency charged to TOK-DS: +4 edges from the first per-leaf NORMR to the aligned collection; no extra edge after the last of five leaf commands. The compiler treats this as one logical slice norm lowered to five consecutive leaf commands because each leaf has its own XQ/XB address. Other operations retain their timing.

Collected existing final-source results from epyc3:/srv/opentallas-scratch2/claude/tok-ds/dsk/m2, preserved verbatim in summary.txt: four 6,016-cycle functional runs PASS for HB=0/1 and FACE_LAND=0/1; wrong-depth mutants caught for both HB modes (7,369/7,362 mismatches); all 16/17 malformed-traffic cases caught; four 20,000-cycle locksteps PASS (zero-delay compatibility and landing composition). Legacy baselines PASS. Old aligned-input bench against new default fails as expected (8,415/8,366 mismatches): the schedule must use the staggered contract.

Post-synthesis LEC remains RUNNING on epyc3 under dsk/kits/{ot_s81sl_xrt1,ot_s81sl_xrt3}/lec2. No physical timing closure claimed. Source recovered read-only from epyc3:/srv/opentallas-scratch2/claude/wt/s81-norm-deskew-1025; original worktree and jobs unchanged.
