Generic ot_clk local-entry migration, source aca469fad.

Moves the existing native clock-load isolation placement algorithm from the
HEAD-only helper on 735403ad0 into tools/clk/local_entry.py, callable through
ot_clk.py local-entry with the same --physical/--stages/--plan/--ctree/--lef/--out
arguments. Optional --cell defaults to the same BUFx8 master. Output fields and
placement order preserved. New master support is restricted to single-row bodies.
There is no change to the frozen HEAD clock, schedule or reset/START semantics.

Actual HEAD-START-2 fixture replay PASS, ot-run intel2 self/localhost unit
oth-ubuntu-2345345-1793288304. Full 1,356 buffer physical_lc.json BYTE-IDENTICAL
(hash in compare.json); 0 flops / 0 cycles added. No P&R or STA launched.
Source input = head-start-2/in/final5/driven/physical.json, after the data-path
buffers are inserted. Initial comparison mistakenly used the earlier physical.json
(14,680 rather than18,370 cells), so buffer locations differed; corrected input
reproduces the retained output exactly. Failed artifact physical_lc_new.json is
retained beside the passing physical_lc_source2.json in intel2 run dir
/srv/opentallas-scratch2/claude/codex-local-entry-0841.

Focused test PASS: selected buffer master, immutable source, existing-driver
rejection, unsupported multirow rejection. Generic algorithm retains existing
START stage schemas; no die-specific code imports.
