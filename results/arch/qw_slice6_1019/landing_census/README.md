Qwen parent landing census, source19819c3ad, 2026-10-20

This packet measures the actual parent's GENERIC ot_pl_land_w/r mechanism,
not a whole parent and not an assumed physical-chunk implementation. The
standalone coupon has W1095 and independent ck_w/ck_r ports, D4K2 or D8K4.
The physical_chunk24 source is a comparison only; the parent does not use it.
No production sources changed, no layout gates, no behavior-proof claims.

ASAP7 RVT TT NLDM mapped primitive pin loads (both clocks excluded, all other
input/reset/data/enable drivers included; recursive hierarchy ports unified):

variant    max loads  >32 drivers  primary mechanism
 generic4    2190        9         shared write rq+wc decoded slot controls
 generic8    2192       17         shared write rq+wc decoded slot controls
 physical4    105       48         writer rq controls all four slots
 physical8    209       48         writer rq controls all eight slots

Transparent BUF/INV root counts give the same maxima. All four FAIL32.
No unmapped Yosys logic cells remain (scope metadata excluded). Physical
violations are46 writer-local rq registers plus2 reset input ports (46loads).
Physical read_oh max26 and write_oh max27 are within32: the rq/reset/enable
fanout is the missed mechanism, so a generic->physical_chunk24 substitution
alone does not establish safe admission. Generic reader rc/warm cones reach
1099/1098 loads (D4/D8); valid/pick gating reaches1095. Source register-cone
locations are recorded in every violating driver row, even where ABC removed
public rq/warm/wc names. Clock roots remain distinct through synthesis.

Storage inventory (generated parent file SHA pinned in inventory.json):
183 reader crossings /28312bits share154 unique writer rings /20151bits.
D4 data-bank total80604bits,14 logical stores>2048bits (53036bits).
D8 data-bank total161208bits,16 logical stores>2048bits (113792bits).
Representative generic bank is1095*D =4380bits/8760bits, runtime-indexed by
slot control, requiring SRAM under the binding checklist. Epoch diagnostics
are not counted as data storage; synthesis drops unused epoch outputs.
Physical comparison owns46 independent24bit-or-smaller data chunks, each
96/192bits, but still fails actual control/reset loads as measured above.
Shared writers are counted once, not once per destination reader.

Reproduction: fleet only, openroad/orfs:asap7lock image digest and exact
liberty hashes committed. map.sh prepares a combined five-family liberty,
uses Yosys synth -flatten -noabc, dfflibmap, then ABC liberty mapping.
This is a standalone technology mapping baseline, not an ORFS place/route
or full-parent admission. Original *_census.json results are preserved;
*_roots.json adds transparent-buffer and source-cone classification.
Full mapped JSONs remain in ot-epyc9:/srv/opentallas-scratch/claude/
codex-qw-landing-census-1020/mapped3, SHA256 receipt committed.

ASR scope: read_liberty is used for mapping and port-direction counting ONLY.
No Yosys-generated DFFASRHQN behavior model was simulated or used for formal
equivalence. Counts do not depend on SETN/RESETN/QN behavior. Existing proofs
that imported the defective ASR behavior model remain HOLD/provisional under
the root directive. Pure RTL ring tests from the preceding task are unaffected.
No numerical/RTL/clock equivalence or safe adoption follows from this packet.

Concrete correction belongs to canonical shared landing owner
/root/hbm_takeover/pgvm_pickup (contacted with all four results): joint writer/
reader SRAM backend for logical stores above2kb; keep source/destination phase
and fixed age/reset contract in one model; distribute kept reset/enable copies
by actual mapped slot-control load (not only CHUNK_BITS); audit both raw reset
ports and local rq flops. Preserve separate clock domains and price any added
landing cycles before the generator opts in. No duplicate shared backend here.
