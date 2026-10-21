Qwen GEN safety exporter, 2026-10-20

Source: tools/qwen_split/gen_safety_facts.py, installed at the end of
qwen_rom_fulldie_b3r2.selected(), after final placement, reset tree and clock
refiling. case_real and case_grt automatically emit work/gen_safety_facts.json.
OT_GEN_SAFETY_FACTS_OUT=/absolute/path.json additionally emits the final selected
model without requiring case generation. This exporter does not move instances,
add relays, modify clocks, or change the RTL.

Run the shared checker with:
  python3 tools/die_safety/gen_check.py --facts CASE/gen_safety_facts.json --out report.json

The final source uses oriented, matching generated bit pins and exports the worst
corresponding net bit for each segment. Any unresolved bit geometry remains
explicit in centroid_only_segments. It stitches actual relay/reset port chains so
W2 sees continuous unavailable-site spans across relay stations. Channels exclude
hard-block bodies and declared relay keepouts; no synthetic grid of sites is
created. Actual two-stage qfd_rst_rep reset synchronizers and source-synchronous
forwarded clock ancestry have separate metadata; they are not invented rings.
Per-port clock identities come from existing cluster/native related-pin contracts;
unresolved multiple roots are compared conservatively.

Committed evidence is diagnostic, not a die qualification. Three fresh production
GEN copies ran on the fleet, preserving the original live g5r2b snapshot. Their
placement and bus/instance identities match original out/rom_tp8b.json exactly.
The copies exercised earlier exporter revisions, before final bit extraction and
crossing classification, and therefore do not qualify the final exporter.
manifest.json pins source files, inputs, netlists and facts by SHA256.

baseline_centroid_chain_report.json analyzes actual production pin-group centroid
segments, stitched through actual relay/reset ports: 16,864 chains, maximum hop
377.6 um, W1=0 and W2=0. Its C1/C2 classification is the INITIAL incomplete
classification and is retained as a failure. Channels in that historical analysis
exclude hard blocks but do not include final-model reserved keepouts; all-bit
reach and final full channel coverage are not claimed by that report.

negative_witnesses.json is a fault-injection check on one actual rooted, landed
production crossing and one actual production chain, not a whole-die PASS. The
unaltered subset passes. Removing its landing, removing a regional root, or
mutating one hop to 406 um causes the corresponding C1/C2/W1 failure.

Both production reset logs use the same latest 8cd522a2f auditor. The original
netlist and a fresh GEN with the 8cd generator/reset-sync patch both FAIL on the
two actual foreign reset -> forwarded hop-0 enable joins. This is evidence that
the proposed structural patch did not yet repair that production configuration;
the parent Qwen lead owns the generator-hook repair and next GEN.

unit_tests.log: 16 small Python tests pass, including actual helper orientation
and sliced bit identity, undriven clocks, absent rings, foreign reset joins,
continuous unsited chains, hard-macro/keepout exclusion and automatic case output.

Follow-up: corrected2230/ records the corrected reset-input GEN (audit PASS for
the two original foreign-clock hops), its remaining regional/data failures, and
complete actual corresponding-bit/reset-site geometry analysis. That directory
is the current diagnosis; the earlier failures above remain historical evidence.
