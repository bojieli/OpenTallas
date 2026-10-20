# HBM exact-tail source repair — 2026-10-19

GEN2e2 S5 actually failed strict bind: 541,758 unread bits. Three new relay padding classes total 471,438 bits. The source generator fills spare fixed-width positions with repeated real data that reaches no consumer. This packet removes those positions as actual narrow core hardware; no new observation sink or unread waiver.

`exact_tail_layer.py` transforms the immutable relay layer; `full_die_v16.py` accepts explicit per-tile real widths, default unchanged. All driver/load identities, stations, clock/reset/epoch edges, fault exports and accepted payload widths remain. No added successful data edge or schedule credit. New masters need own native synthesis and closure; no old hard view reuse.

Full shape: 2,144 buses, 39,269 narrowed instances, 981 distinct source master variants; 6,437,831 unused data positions across stages removed. These are data positions, NOT FF/area savings: landing rings and width-dependent reset groups have separate costs. Throughput, real boundary bits, station count and latency unchanged. Floorplan/area/routing/current/TT/FF closure remains unqualified; old placement is diagnostic only. Existing full 624x4 landing rings exceed the approximately 2kb indexed-storage threshold and still need SRAM qualification.

The all-bus source map compares 9,917,643 real edge bits, checks no alias/duplicate edge, and proves unchanged clock/reset/epoch connections. Final comparator also compares legacy default emitted edges with original full_die_v16.py byte-for-byte. Map SHA256 5dd5b6bc6bd64c9af838cbdf228f69d95ac824da167ec3b889e1e6d379c4d314. PASS is source-map evidence, not native timing or whole-token PASS.

Source review found the width-sensitive reset threshold: ot_hbm_rly automatically inserts a three-edge reset relay only above W256. Old624 tails now explicitly preserve RS_RELAY=1 even below that threshold. The initial data-only generated source is retained on fleet as initial_data_only_tail_masters.sv and is NOT eligible for use. Fixed generator/source is this packet.

Native minimal mechanism: Icarus four-state and pinned Verilator5.050 PASS107checks on actual cores W1/255/256/257/623, 3-way fork branch packing, landing data/fault, assertion with stopped clock and re-release. Genuine removed-reset-relay mutant FAIL at3.201ns on W1/255/256. Model/map proof plus native mechanism do not establish arbitrary unreset startup equivalence or physical qualification.

Actual source splice + strict whole-die bind remains LIVE at hand-back: ep6 unit oth-ubuntu-1970966-1792457006, PID1993991, session71378; log /home/ubuntu/artifacts/takeover3-hbm-die-reset-1019/tail_strict.otrun. Source overlay starts from immutable6f783d0a1, preserves failed original binding, and changes only exact-tail source/splice. Collect actual class delta before integration; no strict PASS claim yet.

Frozen inputs: old_layer.json.gz SHA d8f6de49bd9b847e574ef2399315dd99479bc0f7c7fa2cea7049eeaf3abcac02; fixed layer SHA10254ad52aec69c100b1ff89a982d2cefc0ca7c32aa97e0d553f4b8f203d3834. Fleet root /srv/opentallas-scratch/codex/takeover3-hbm-die-reset-1019, owned remote source there. Original model, map and native receipts retained.

GEN2e3 separate six-synth recovery is LIVE: localPID744806, source5b5d01284 frozen in /home/ubuntu/wt/codex-takeover3-gen2e3-synth-1019;5/6 real synthesis+ETM results PASS, selector Yosys progressing. Exact pinned checkout repairs environmental rejection, not RTL. S3 case_a runner prepared at /home/ubuntu/artifacts/takeover3-hbm-die-reset-1019/gen2e3_case_a.sh but NOT launched. Resume only after six strict fetch receipts; send actual PNG/checklist/source residuals to ROOT. No autoGO granted.

cplanK hard-footprint reset forest remains LIVE3918051, HBM release106 PASS and serial NW progressing. Preserve carr/carrhh/cplan/post x/y. If hard-footprint plan actually fails, execute in-lane carrier fallback. No e4 integration, new physical submit or adoption occurred. e4 requires l21 exact unread manifest replay, FAN32 collar params+actual slot, and pslice11clock/11reset interfaces; all remain pending.
