# Reset-only native partition MODEL — not a clock/reset qualification

Final concrete bounded option: **155 local groups over the 331 reset entries in the 26 failing reset-only regions**. This counts 1,993 existing native FFs and 177 conditional instances of the exact existing `qfd_rst_rep` landing master (531 additional FFs). Every group has at most 31 combined existing/landing FFs. Reference-root to actual native capture pin L1 distance is at most 298.5375 um. Native phase, legal root/landing placement, PG completeness and stopped-clock assertion remain HOLD. No RTL, GEN, compiler, synthesis, simulation, route, gate or acceptance was performed.

## What is pinned and measured

- Original terminal packet `f52b60afc`: rA/rB both FAIL 38/655; 26 reset-only + 12 CB16/reset groups. Original 76 failed-region rows and 84-file hash manifest are preserved unchanged here; full raw arrivals/topology/PNGs remain in `results/rtl/qw_regional_terminal_1019`. `eb0ee1e0b`'s 446 links / 186347 bits remain separate debt.
- Exact read-only parent: ep6 `/srv/opentallas-scratch/claude/qw-dieclk-1019/d/floorplan_ck.odb`, SHA256 `109181601648ebc9532fd6fa39f2f713ebbc78610b8f9d23278d7512b1f88b95`. Scan includes all signal endpoints of every net touching the 331 selected instances: 343 nets, 372 directed connections. There is no max-fanout truncation in this extraction.
- Exact final native reset ODBs from existing PG packet `0ea3ca6ba`: `qfd_rst_rep` SHA256 `2fb3c45a01ac2c1e8220ad9854db08f09fee4d174f783bdfc7188d885f9744b8`; p8 SHA256 `0be37cfaad75b23d2a2d6d82f039fe3cc27d4a048dd0a58229fc00b1cba1765c`. `leaf_sources.json` retains original host/path/hash records. No full PG scan was repeated.
- The 206 regular / 125 p8 instances contain respectively 3 / 11 actual `DFFHQNx1_ASAP7_75t_R` cells. All selected parent transforms are R0; native FF D/CLK/QN pin coordinates are transformed by the actual parent origin. `entries.json.gz` retains every capture pin, native clock/data buffer path and complete original regional/spine clock-cell path, including actual source `clk_rx/pll_d2d[0]` ancestry. This is not an instance-centroid model.
- Read-only scans: unpinned `ot-run` unit `oth-ubuntu-1583669-1792442770`, 16 GB / 1 thread, and leaf-only area unit `oth-ubuntu-1600006-1792442864`, 2 GB / 1 thread; both completed exit 0. Placement chose ep6 for existing ODB locality. No ongoing owned process.

## Concrete assignments and crossing cost

`groups.csv` and `groups.json` give every exact member, old source pin, reference root pin/XY and destination group. The deterministic greedy partition bounds the full capture-point L1 diameter at 320 um and then splits to a fixed point including each newly required native landing's THREE FF clock loads. It is a bounded construction, not an optimal partition or timing result. Reference root pins are actual existing clock entry locations; they are **not** proof of a legal new clock-buffer site. Added capture/landing placement, row/rail/via contacts, route detours and clock electrical loads require a native physical model.

| Final native option | Incremental/model quantity |
|---|---:|
| Local groups / additional groups over old 26 | 155 / 129 |
| Existing capture FFs / combined local FF budget maximum | 1993 / 31 |
| Newly crossed physical reset nets | 167 |
| New directed source-pin → capture-pin connections | 177 |
| Distinct (net, destination-group) landing requirements | 177 |
| Exact native landing instances / additional FFs | 177 / 531 |
| Additional bare FF area, native DFF geometry | 154.8396 um² |
| Additional existing native frames, before spacing/PG/clock | 14864.6016 um² |
| Additional landing clock input ports | 177 |
| Maximum subroots per old source | 14 |
| Conditional selected-subgraph added release edges maximum | 32 |

Every new crossing is reset level data; the scan found no newly crossed payload or non-reset control in this bounded scope. Full directed ownership and original physical source/output/capture coordinates are in `edges.json.gz`, without duplicate `(net, source instance/pin, capture instance/pin)` keys. Multiple sinks on one physical net explain the difference between 167 nets and 177 directed connections. Existing incident inter-region crossings number 91; together with the 177 newly introduced connections, 268 incident connections cross proposed/local or outside roots. These are not the separate 446 payload-link inventory.

The newly crossed original pin-to-pin L1 distances sum to 21061.4745 um, maximum 233.1785 um. Those are lower bounds on **existing connection** geometry, not incremental routed wire length or proof that new landing faces fit. New per-net routed wire/landing pin coordinates remain NULL. Existing source buffers to proposed root references have independent L1 sum 279434.922 um and maximum 3160.23 um: at least 762 segments of reach <=405 um before obstruction detours. Sharing can change the aggregate; it is not 762 independent new cells. Those source paths still need priced forwarded relay topology, phase and electrical analysis. The maximum 14 local subroots does not prove whole-tree transparent fanout/electrical safety.

For example r235's existing 17 entries span 1118.88 um and had full TT entry spread 467 ps despite smaller linked-pair maxima. The final assignment splits those actual pins/captures into eight named groups (`r235_p0_s0` through the exact CSV names). Maximum combined FF budgets are 31,3,23,14,28,6,9,6. No rB ideal entry is substituted for real clock distribution.

## Reset semantics and first-use limitations

The exact preserved `ot_qwen_rst_rep.sv` at `cddafbdcc` has synchronous data capture only: d → input s → registered q0/q1, or d → nine s registers → q0/q1 for p8. The extra output is a genuine registered physical role even when one output is unused at the proposed landing. Thus a concrete reuse costs THREE FFs and a full 12.96×6.48 um frame, not an abstract two-FF floor. The source explicitly requires running clocks to flush arbitrary state. Both reset masters have six native unbound PG terminals in the existing audit; reusing 177 original masters would replicate 1062 such unbound terminals until a separately qualified repair. No net-only PG pass overrides this.

The concrete conditional option adds an existing two-stage native landing before each newly crossed receiver: old receiver latency 2/10 becomes 4/12 receiving edges from its new incoming level. This is an analytical pricing option, not an approved source change. `longest_conditional_release_path.json.gz` retains the exact selected-subgraph path from `rstt_rst_field_2383/q0` to `rstt_rst_field_8780`, all 22 original connections, source roots and 16 newly crossed connections. At fixed compatible native phases those 16 new two-stage landings add 32 receiving edges **within this selected subgraph**. Root-to-entry history outside it, changed forwarded phase, independent clock stops, asynchronous assertion and parent first-use windows are not bound; 32 is neither a production minimum nor a global release/token delta.

In particular stopped clocks prevent these plain FFs from propagating assertion at all. A separate actual asynchronous assertion path or a qualified running-clock/pulse contract is required; its hardware/area/latency is NULL. No such producer contract is invented. Pulse width must cover the composed reset graph, phase, clock stops, both output branches, p8 delays and added landing stages before any first operation. The earlier CTLM producer pulse19/pulse20 counterexample is separate evidence: this reset-field subset has no proof of the same producer, clock, lifecycle or earliest-use epoch. It cannot turn either pulse into a release guarantee. Absolute assertion/release epochs, earliest valid operation and SU/MU added latency remain NULL.

Eight primary SU roots remain the required hierarchy intent. The original failed trial's 26 `pll_r*` names and global `pll_d2d` forwarded spine are retained as evidence only. There is no actual source mapping from the eight intended SU roots to these 155 local groups in this packet. `accepted_eight_su_parent_root` is NULL for each group; do not collapse them to a global balanced tree or alias roots. New root buffering, every forwarded phase, root/control fanout fixed point, source/capture apertures, registered input ownership and stopped-clock reset protocol must be bound before a full GEN.

## Preserved incomplete bounds and next decision

The initial 121-group / 156-connection / 312 abstract FF proposal omitted the extra landing clock loads and is incomplete. Including a hypothetical two-FF landing produced 151 groups / 178 connections / 356 FF, retained as `abstract_2ff_incomplete_summary.json`; it still did not price the actual three-FF native master. The authoritative concrete option above counts that master and closes its local load partition in three iterations. These different greedy partitions are not numerical improvement claims.

ROOT review next: accept/reject this partition as a bounded starting graph; select the real eight-root distribution and an actual assertion/release mechanism; then supply legal native PG-connected root/landing locations and all-corner phase plus first-use contracts. Total incremental area and token latency stay NULL until these missing terms are priced. The 12 CB16-containing failure groups, child insertion/PG limitations and the separate 446-link debt are not repaired by this packet. No new full GEN/rerun/gate is requested automatically.

Safe checklist: pin registration/reset HOLD; reach bounded only on actual existing capture geometry, new routing HOLD; local FF count bounded, whole transparent fanout/electrical HOLD; depth HOLD; existing tiny reset state <=2kb, no arbitrary four-slot ring substitution; floorplan/PG HOLD; native clock spread remains original FAIL; schedule/epochs HOLD. Original failure evidence remains immutable.

Reproduce with `QW_PRIOR_EVIDENCE=<f52b raw/d> python3 model.py`. It is bounded JSON/geometry postprocessing, not a simulator. Inputs with `.json.gz` are accepted after compression. `scan.py` and `cell_metrics.py` document the read-only native exports and require OpenROAD on the fleet. Artifact hashes cover committed evidence; original ODBs remain on their hosts.
