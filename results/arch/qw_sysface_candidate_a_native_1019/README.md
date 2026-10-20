# SYSFACE Candidate A native source comparison

**Native mapping and all-output source equivalence PASS; safe fanout/electrical closure FAIL; standalone timing HOLD.** This is an isolated full-component comparative source diagnostic, not a SYSFACE gate. Original and Candidate A are the exact 76277b2cb32db263d527bb1e7c66ae91754f2ef1 modules: 677 non-clock/reset input bits, 145 state bits, 161 output aliases, zero added edges. The parent a0ab17388 failure remains unchanged. No publication duplication, producer integration, physical closure or production activation is included.

## Terminal admitted result

Qwen lead reviewed the full prelaunch inventory and admitted canonical mapping, native/source proof and uncapped census only, at1 thread/4 GB/2 GB with automatic ot-run placement. All jobs are terminal on ep7 under /srv/opentallas-scratch/claude/sysface-candidate-a-native-1019. Client admission/exit logs and measured process receipts are preserved. The exact ten HBM canonical TT/FF library hashes match all ten contemporaneously observed inputs; additional library files in the platform inventory are not mapper inputs. Actual Yosys is0.67 git2d1509d1b under the pinned16470 image.

| Actual isolated result | Original | Candidate A |
|---|---:|---:|
| Native cells / cell types |1217 /35|1085 /39|
| Native Liberty cell area um² |147.155940|131.307480|
| Actual DFFASRHQN cells |145|145|
| Mapping elapsed / peak RSS KiB |2.81 s /150804|2.18 s /150976|
| Arbitrary-state source/native SAT |32964 variables /84211 clauses PASS|30672 variables /78393 clauses PASS|
| SAT peak RSS KiB |65640|62576|
| Transparent BUF/INV instances |196|256|
| Unsafe logic-root loads after transparent traversal |132,132,132,143|132,132,132,131,144|
| Raw clock / reset / SETN literal loads |145 /145 /145|145 /145 /145|
| Native declared PG MTerms / source graph bindings |2434 /0|2170 /0|
| Known TT internal pin-capacitance violations |4|4|
| Maximum native graph cell levels to FF D |7|8|
| Native graph cell levels to fault D |7|7|

Every source/native SAT miter leaves all677 inputs and145 present-state bits arbitrary and compares every161 post-transition output bits. native_proof.py reads the actual native mapped JSON and actual Liberty functions, rejects unsupported cells/state merges/reset/set/clock bindings, cuts the145 actual state cells into corresponding arbitrary present-state values, and derives next state from the real Liberty definition. DFFASRHQN is **ff(IQN,IQNN), next_state !D, clear !SETN, preset !RESETN, QN function IQN, simultaneous clear/preset L/L**. Every SETN is proven literal1 and RESETN is exactly rst_n. Actual output inversion/buffering is traced per state bit. No async2sync or generic positive-Q replacement occurs. The exhaustive SAT proof is binary functional next-state/reset-value equivalence; it does not establish analog reset recovery or native four-state timing behavior. The separate109457 source four-state checks remain scoped to76277.

The candidate removes132 native cells in this isolated mapping but adds a fifth unsafe logic root. Known internal TT capacitances alone exceed real output max-cap limits: original62.133/61.758/63.526 fF against23.04 fF, and59.795 fF against46.08 fF; candidate61.778/61.738/61.469 fF against23.04 fF, and59.874 fF against46.08 fF. These are native Liberty pin-cap sums without external loads or wires, so each is already a definite internal electrical failure. Native capacitive unit is1 ff and timing unit1 ps. The complete census retains every root/endpoint, transparent inversion path, source support set, native cell/master, reset/set/clock role, declared PG MTerm, direct cap bound and FF endpoint graph depth. PG ITerm binding is NULL: a source graph is not a physical PG proof.

Graph level counts are finite connectivity measurements, not timing: there is no TT/FF slack, delay reduction or full-parent timing transfer. Existing full-parent28 levels/833.5 ps and TT−57.924 ps remain separate. Candidate A is not SAFE and cannot proceed to a gate or activation on this result. No speculative benefit is reported.

## Remaining exact boundary work

All677 input bits and161 output aliases resolve to actual old-parent native connections. Those connections include original internal feedback, optimized shared nodes and external consumers. A native internal predicate can be shared outside the original source component after whole-parent optimization. Source ownership and actual per-bit cap/drive/arrival separation must close before standalone STA; assigning all observed sinks as external would double-count component feedback. The frozen signoff SDC's propagated-parent reference cannot be transplanted onto this unplaced component. Both original and candidate must receive the same explicit extracted boundaries. Until then TT/FF setup, hold, slew, actual ps depth, FF cap checks and physical reset/PG remain HOLD. No unit-cap fallback or artificial waveform is supplied.

## Preserved prelaunch inventory and intended timing method

The following records the reviewed plan. Mapping/proof/census portions have completed as reported above; timing remains held.

## Source and canonical dependency identities

The original receiver source SHA256 is 94f59024db39f4250ad15e07ae4ec85f099c8e13a9cb1d556d7d6cd5ab063b9f, extracted from frozen ff05d759bd0370d41fa671b755233e91670f7fe0. Both standalone module files and the arbitrary-state source proof remain at results/arch/qw_sysface_candidate_a_source_1019. This identity is separate from later main context sources.

Canonical mapping scripts are copied verbatim from da40a2a46 tools/hbm_int8_safe_source/{map.sh,map_baseline.sh,merge_libs.py,ot_keep_regs.tcl}. Only module/source/output paths will change. Native libraries are the real RVT TT AO/OA/SIMPLE 211120, INVBUF 220122 and SEQ 220123 families; matching FF versions supply FF STA. No FAKE DFF or synthetic Liberty is allowed. HBM lead supplied its original matching ten-library receipt; input/hbm_lib_SHA256SUMS preserves it. The imported terminal native_tt/native_ff libraries are single-cell parent ETMs and will NOT be used as standard-cell mapping libraries.

Read-only ep7 inventory on 2026-10-19 records actual installed image Id and RepoDigest 16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29, Yosys binary SHA256 5cd52bc790d39b1e59a88112e9132ef8de338c2a26e4b0df8222d937e65bab92, and OpenROAD SHA256 21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846. Raw full library hashes are in input/tool_library_inventory.txt. These are current observations, not reconstructed historical job receipts. The actual run must capture its own image, binary versions/hashes and exact merged library hashes again.

## Exact proposed mapping invocation

For each of original and candidate, in separate immutable output directories, with the same five native families and keep hook:

```
read_liberty -lib mapped/all.lib
read_verilog -sv -DSYNTHESIS component.sv
hierarchy -check -top COMPONENT
tcl canonical/ot_keep_regs.tcl
synth -top COMPONENT -flatten -noabc
dfflibmap -liberty mapped/seq.lib
abc -liberty mapped/comb.lib
clean
stat -liberty mapped/all.lib
write_verilog -noattr mapped/netlist.v
write_json mapped/netlist.json
```

OT_KEEP_PIN_REGS=1 and DESIGN_NAME=COMPONENT apply equally to both. No async2sync, retiming, extra FFs, tie substitutions, dropped outputs or additional state assumptions are permitted. Any unmapped cell or lost state/output correspondence is a refusal. The exact native graph is the audit input; area/depth are not inferred from source operators.

## Actual parent load and timing plan

Finite inventory.py resolves every one of the 677 input bits and 161 output aliases to actual original parent native connectivity. The 161 outputs refer to 145 distinct generic bits because host_epoch aliases host_tag[58:43]. The preserved 54,890-instance post-CTS native netlist, generated original wrapper, original Yosys graph, endpoint/root tables and Liberty files are source pinned to a0ab. The wrapper's actual face aliases are resolved explicitly; absent core/nNN names do not mean zero load.

boundary_inventory.json preserves every immediate connected native instance/master/pin. These connections include component feedback and parent consumers. External output capacitance and input drive remain NULL until those sets are separated using original source ownership and actual TT/FF native pin capacitances. Transparent BUF/INV paths must be traced with polarity, including clone ownership. An ambiguous shared clone remains HOLD; it is never assigned a guessed unit load. Fault FF's five old loads are distinct from the downstream 39-load OR publication. No old full-parent setup/depth number transfers to the standalone component.

Both components will use identical explicit per-bit external caps/input driver/slew, the frozen 833.333 ps clock and 60 ps setup /25 ps hold uncertainty, and the actual parent signoff.sdc identity. Parent reference arrivals, IO budgets and reset role must be extracted numerically and reported. The current signoff file is preserved verbatim as input. Its propagated-CTS reference helper cannot be blindly sourced onto an unplaced standalone graph. Any missing boundary arrival, pin-cap corner or source ownership prevents a timing claim. Diagnostic cell-only STA will label ideal clock and absent wire parasitics explicitly; TT/FF setup, hold, slew, cap, fanout and logic depth must cover all endpoints plus the exact reserved-input/fault cone. No physical or routed claim follows.

## Native graph to source proof and census

For both mapped graphs, build an arbitrary present-state next-state miter against its exact source. Actual Liberty Boolean functions, sequential ff definitions, clear/preset polarity and ties supply semantics; do not use invented cell stubs. Match every 145 state bit and all161 post-transition outputs. DFFASRHQN QN inversion, RESETN/SETN priority and any output inverter are explicit in the correspondence. Preserve asynchronous assertion: no async2sync conversion. Binary arbitrary-state SAT and actual sequential reset/clock tests are separate evidence, as in 76277. Unknown primitive semantics or unmatched state fails closed before timing conclusions.

The uncapped census lists every native cell/master, driver and sink, transparent BUF/INV polarity paths, actual clock/reset/set/tie/PG roles and full endpoint counts. Liberty PG MTerms and actual graph bindings are counted separately; no VDD/VSS membership assumption. Source-only graph PG absence is an explicit HOLD, not a physical connection result. The old39-load publication remains present unless actual new mapping proves otherwise; this diagnostic does not add a second OR.

## Resource admission and next action

At 15:02 PT ot-run reported 564–1249 GB admissible on ep4–8 and 99/100 GB on smaller nodes. Source input is about33 KB, parent context about8 MB compressed plus the original graph; exact file bytes/hashes are in the generated inventory. Native TT/FF library inventory totals20,904,971 on-disk bytes. Prior same-component generic formal used39,932 KiB RSS/0.19 s, but no native mapper peak measurement exists.

Proposed reservation is 1 thread, 4 GB RAM, 2 GB disk for sequential original/candidate mapping, graph census and native equivalence, with incremental immutable logs and measured RSS/disk. This is a capacity reservation, not a per-process cap or timeout. Use unpinned `ot-run --threads 1 --mem 4 --disk 2 --dir REMOTE_DIR -- bash run.sh`; this installed client defaults to automatic placement and has no --remote option. No arbitrary wall-time limit. Reuse completed outputs; do not restart a progressing job.

ROOT/Qwen inventory review authorized mapping plus graph proof/census only, now completed. Standalone STA remains held until actual external load/arrival extraction closes. No additional build, parent gate or physical qualification is authorized by this packet.
