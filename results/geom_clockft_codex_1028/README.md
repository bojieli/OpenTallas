# Explicit clock infrastructure feedthrough classification

KV pv_pair AUTO-GEOM rejected ft_ck_i_0/1 and ft_ck_o_0/1 as four
unregistered data pins. These are declared die-owned clock arcs in the
kit's ft_interface.json, implemented as clock-buffer infrastructure.
geom_rules now accepts an explicit --ft-interface argument. It recognises
only kind=clock source INPUT / sink OUTPUT pairs whose actual checkpoint
connectivity is entirely buffers/inverters, reaches the declared sink,
and has no data/logic/other-output fanout. Names alone, undeclared arcs,
reset/data kinds, missing endpoints and arbitrary logic are insufficient.
Unused clock-buffer loads are permitted. geom_check.sh passes the kit
sidecar when present; kits without it retain the previous metrics.
Data pin registration, register reach and every other geometry rule stay
unchanged. No thresholds or routing gates change.

Validation: 39 focused tests PASS (32 existing auto_geom + 7 controls).
On the retained real pv_pair geom.tsv, all four declared pins are
recognised, unregistered count 4 -> 0, and p90/max register distance stay
8.3/12.37 um. Reusing the original metrics for other unchanged rules gives
PASS. The original FAIL artifact is untouched; no route/STA rerun.
Data: intel2:/srv/opentallas-scratch2/claude/codex-geom-clockft-1028.
Original: intel2:/srv/opentallas-scratch2/claude/codex-kv-kits-1028/geom/kv3_pv_pair__380.16x190.08.

The two ft_ck_i_1 buffers are intentional PARALLEL mesh drivers:
island_ft.tcl ot_ft_short joins both Y terminals onto the output net.
The dump format retains one net driver, so the Python graph sees one
buffer as an unused load. Recognising that buffer-only load is necessary;
it does not indicate an unused physical driver or a missing cascade.
