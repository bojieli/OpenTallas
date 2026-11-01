# Current native Tnode: VIEW request for bounded PLACE

LOOK: personally viewed `results/hbm_tnode_native_1131/native_input_geometry.png`. This is the actual generated macro/pin input geometry before placement; it contains no invented placed cells, PG or wires. Recommend bounded floorplan/PLACE characterization only, subject to ROOT approval. CTS/GRT/DRT/STA require the actual placed-image review afterward.

The native component is `ot_hnx_fused_tnode` with DELIVERED_RESET1/LA6/UW271/DW173, 724 inputs and617outputs. Exact current C11E selected21-file closure is captured in intel1 `wt/codex-hbm-tnode-native-src-r2-1131@eb2bc8b561c`; only the already-approved223c8158c YC1 correction is added in other modules. The Tnode module body is byte-identical to current selected source. GEN/LINT/PREFLIGHT, face guard, port bind and selrange pass. Fresh synthesis and full independent-frontend LEC prove4730/4730 with KEEP358/358 and requested4/USED4 reset edges. Historical64 is not adopted. There is no external input/output register shell.

The source-native register-stage model is down2, scalar-up4 and chunk-up LA+3=9. The earlier child additionally uses the static pad delay selected by pad_k/pad_b. A stage-count N means output after capturing-edge e+N−1, with reset regions active. The delivered reset adapter has three synchronous stages per region. These are existing source stages, with no new cycle allocation.

All30 actual Tnodes have live `io_native_required_*_pad_k/pad_b` producer obligations:60portgroups, not literal0. They remain free and uncaseanalysed in this component. Mission pad producers, alignment and whole-graph cohort dates remain SOURCE_HOLD. This request characterizes the full component interface and does not qualify that unresolved mission.

Current G `e0638225f8b38653671aa3a59d11023c566182278d7256359f8f5b221b34c492` has the same172.8×172.8 outline and exact50055cbac918 pin-file SHA as the generated kit. All30 current G hooks resolve the actual planned native clk to M5 center(86.376,86.4), rectangle(86.352,86.16)–(86.4,86.64). No island-center alias or old physical view is supplied.

The two literal planned macros are `u_pad.u_d`,94.824×41.064 at(38.976,15.132), and `u_pad.u_c`,31.992×17.304 at(38.976,67.068), bothR0. Both fit with the actual2um halos; vertical macro gap10.872um and halo gap6.872um. Clock rectangle clears both halos by minimum L1 distance13.384um. The outline bounds every point-pair L1 distance by345.6um. The source GEN PG recipe retains M1/M2 followpins, M5 stripes width.12/pitch4.32/offset2.064 and macro M4–M5 connection; actual PG continuity is not measured yet.

Reported SYNTH design area is approximately6022um²,20.2% of the fixed current outline; hard-macro area is4447.442304um². Underfill remains a measured concern for the placement screen, without an outline change or a geometry-gate waiver. Native pin-capture reach, local density, overlaps, routing access and clock insertion remain unmeasured until the appropriate physical stages. Current period833ps, TT250ps/FF202.5ps insertion bounds±40ps, setup uncertainty0 and hold25 are unchanged.

Requested producer: HBM clock, own coupon `intel1:codex-hbm-clock-tnode-native-1101/current`,8GB4T, floorplan+PLACE only. Preserve source4730 proof, reset4 and every free pad port. No ties, case analysis, falsepaths, added stages or source edits. Stop for actual placed-image/geometry review before further physical stages. ROOT verdict remains pending.

## Independent review of actual ordinary PLACE

Reviewed native_actual_placed.png produced by the separate clock owner from intel1 codex-hbm-clock-tnode-native-1101/current/run/results/asap7/hbc_ot_hnx_fused_tnode/base/3_place.odb. Exact source eb2, component EQ4730/KEEP358/reset4, native1341pins and all pad inputs remain free. Actual image reports2984FF/5778std/3602buf/3138taps/2macros.

W/E/S boundary flop groups sit close to their native data faces. Both macro halos visibly exclude standard cells, the intermacro channel remains open, and the real central M5 clock location has clear access. No macro wall or closed data/clock corridor is visible. The upper interior remains largely empty; low fill is explicit, with no gate exception inferred. This picture omits PG and routes, so it cannot establish PG continuity, pin access, signal congestion, clock reach or timing closure.

Verdict: actual placement is suitable for a bounded next measurement subject to parent/root authorization and the ordinary numerical gates. This review grants no CTS/GRT/STA launch by the reviewer and no global or mission qualification. All60 live pad producer bindings remain SOURCE_HOLD.
