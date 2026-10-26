# Native W128 HC physical integration candidate

Source branch `codex/hbm-hc-native-1026` recovers six W/NQ providers, then regenerates the physical cuts from current main arithmetic defaults. It does not substitute the old DRST-fixed exported masters. No extra face-shell cycles are inserted.

Apply `physical/die_plan/hbm_arch/native_hc128_delta.py` to the latest composed plan, then `tools/hbm_b2/hc128_apply_templates.py --plan WIDTH_PLAN --templates physical/die_plan/hbm_arch_cores/native128 --out OUTPUT`. Copy existing sidecars first; only changed pin files are emitted. Merge `core_conns_delta.json` over the latest connectivity sidecar's ten HC type entries. Original non-HC geometry and sidecars must remain intact. Rebuild stations/FT and clock taps against the new obstacles; old measured clock taps for replaced cores are invalidated. The optional halo/parent/cut plan fields require the geometry lane's schema addition.

All native profiles pass a same-cycle composition comparison at every unchanged arithmetic/SRAM/client boundary input and all original parent outputs, using checked unchanged parent-state points. The intentional SRAM-WE fault is caught in every bank; the qhub adder-input fault is caught on 32 bits. Actual elaboration parameters and receipts are in `results/hbm_hc_native_1026/native_profiles.json`.

- Plain: W128, CPI1/CPO1, 18,114 proven.
- First: W128, DRLY2/CPO1, 22,180 proven.
- Feed: W128, 18,606 proven.
- Terminal: W128, CPI1/CPO1, 18,084 proven.
- Qhub: W128, DRLY2/CHX11/RD_CAPTURE51/GATHER_PHASE51/DONE_LAT47, 16,289 proven.

Physical interface: common pair 1,590 pins, first pair 1,078, subtree 1,091. The live `square` port is scalar; the previous 16-bit template had phantom pins. Pins use M4 W/E and M5 N/S, phase .024/pitch .048. Clock/reset occupy the N-face midpoint with a reserved 12um data gap. Eight 250.56x267.84 pairs fit each existing bank outline at x25.92, y17.28+k*371.52, leaving 86.4um clear inter-row corridors after halos and at least 95.04um on the right of the narrowest bank. Four 220.32um subtrees fit a 2x2 cluster inside each former qhub HC rectangle. The three upper adders and original parent control/client remain partition logic.

Allocation model: replacement hard-core rectangles add 2,108,888.5248um2 across the actual 16 banks and two hubs, with zero partition/die outline growth. This is a rectangle allocation delta, not measured standard-cell area or PPA. Each pair contains two 1024x256 weight SRAMs, one128x256 x SRAM and768 original capture bits; SRAM macro area perpair is28,528.56288um2. Banks total128pairs (112common +16first), hubs total8subtrees. Each qhub retains all127 adders (124 in cuts,3 in parentlogic). Actual M5 mapping/CTS/setup/hold/clock/model gates remain pending.

Connectivity derives from the actual cut adapter signal graph and native B2 named bindings. Clock/reset do not create data dependencies. All112/120 nonclock bank portgroups are present; each hub has18. Only subtree1/3 `valid_out` is intentionally unused at the original parent. Multi-lane root bundles conservatively retain all reported endpoint bus targets; this is not a per-bit external lane assignment.

Artifacts on epyc1: `/srv/opentallas-scratch2/claude/codex-hbm-hc-native-1026/` contains `masters_native/` (current source module closure SV+JSON+receipts), `adapters_native/` (exact native-profile parent remainder + common-master blackboxes), `native_core_conns_final/`, `templates_native/`, and the five native proof directories. Do not use earlier `masters_current/` or `adapters_current/`, which preserved standalone default parent controls. Generated master SVs are reproducible artifacts rather than committed blobs.

Known remaining risk: current main `ot_hdc_v41x_hcp.sv` omits multiplier `.DRST(ADRST)`. Prior Claude work fixed it, but that fix is absent from main. These new cuts preserve current behavior; old DRST-fixed reset/clock/PPA measurements are not acceptance evidence for them. Resolve the reset profile before measured replacement views are adopted. Geometry image review found zero HC-vs-hardcore halo overlaps; station, FT and full pin/clock geometry still belong to the composed-plan gate. No routed or timing pass is claimed.

Failure diagnosis retained remotely: old cut expected unqualified leaf type names (Slang uses hierarchical suffixes); unsplit capture vectors and parent memory blocked submod; qhub reset appeared as `u_rst.rst_n[8]`; qcen keep_hierarchy blocked proof flatten; proof of original control state needed explicit lockstep points. Each was corrected; raw failed logs remain. The old raw cut contracts embed historical source labels; current source/profile identity is recorded by the new exporter receipts and native profile manifest.
