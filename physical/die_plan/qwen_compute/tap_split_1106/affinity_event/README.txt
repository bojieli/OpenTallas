QC-TAPSPLIT / HOLDCLS conservative affinity component, 2026-11-06

Source a3ab6b89bd, default OFF. Shared support only, no POR activation.
Plan opt-in clock.tap_chain_affinity={radius_um:200,max_group:128}.
The generator refuses radius above the declared grid radius and groups above
min(1200, declared tap capacity). It stages the helper with clock_taps.tcl.

Only actual positive-edge generated delay-register clock pins on the original
direct free-running input net are captured before ordinary nearest/cap split.
Individual matrix bits or scalar delay prefixes form ordered groups, including
actual terminal q registers. Terminal ordering observes all stages, even excluded
gated stages, and cannot skip across them. Hard-macro pins and gated/muxed/inverted
clock descendants are excluded. Changed captured instance/master/source identity
fails explicitly. All members must fit one tap within radius and capacity;
long groups split into bounded adjacent segments. No wildcard whole-bus grouping.
No data/reset/instance/placement changes, new cells, RTL stages or SDC waiver.

Actual retained CBN attempt6 3_place component canary:
E5 /srv/opentallas-scratch2/claude/codex-qc-tapsplit-1106/canary_cbn_97
Source source a3ab6b89bd; normal ot-run 8GB/2T, unit
oth-ubuntu-3851586-1793977217, actual exit0. Measured event238496's
97 legal prototype taps were injected in memory only; no parent/native claim.
52,809 actual soft sinks; original assignment max1049/reach197.148um.
36,004 eligible clock pins/8,228 individual-bit groups; 5,302 segments joined,
15,544 moved clock pins, 2,930 already same tap. Final max grid load1200 and
max joined member Manhattan reach199.990um. Explicit actual per-register groups
are retained in ot_tap_chain_groups.tsv under that immutable output.

Full A/B snapshot comparison: 348,544 instance/master/pose records and
1,288,379 other pin/net records unchanged; 15,544 changes only eligible CLK pins.
No hard, gated, reset, data, master, placement, or cell-count changes. The retained
old28tap control canary had0 legal moves atcap1200, max4814: density A is a real
prerequisite, not optional. 12 focused Tcl/plan tests PASS including capacity,
radius, gated source, master/identity changes, scalar/matrix terminal joins and
terminal gated-gap refusal.

Actual affinity_geometry.png reviewed PASS-COND: original macro channels retained,
97 legal candidate tap positions; joined members stay within unchanged200um bound.
Lines are assignment edges, not routed wires. No CTS, PG, hold or sign-off credit.

Activation must compose coherent current approved source/plan/native/reset/START/
clock-provider event. New hardened-ring CBN geometry needs its own current soft
sink inventory and macro obstacles: do not overlay this old soft-ring profile.
Remaining cross-tap boundaries and any source-window skew still need actual CTS
and ordinary hold repair. All hard timing/PG/LEC gates remain unchanged.

Actual adjacent-edge residual census on these same A/B snapshots:
27,776 adjacent delay-register pairs; cross-tap pairs13,496 ->3,375.
10,443 old boundaries disappear; bounded segmentation introduces322 new
boundaries. This intentionally does not assert complete-chain affinity or
hold closure: remaining and moved boundaries need actual CTS/hold screening.
Explicit examples and reproducible snapshot analysis in edge_diagnosis.json
and edges.py. This shared source remains default off.
