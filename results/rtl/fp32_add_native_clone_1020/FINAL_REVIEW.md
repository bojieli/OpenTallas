# LAT7/DRST0 native fanout candidate: final coordinator review packet

Status: component candidate, original shared RTL unchanged; caller binding and physical qualification remain HOLD until ROOT reviews this immutable packet.

The exact configuration is `ot_hdc_fp32_add_lat LAT=7, DRST=0, CUTS=-1` (all4 optional cuts active). New graph module is `ot_hdc_fp32_add_lat7_fan32_native`. Its API is clk/rst_n/valid_in/a[31:0]/b[31:0] -> y[31:0]/err[1:0]/valid_out. No edge, rounding, reset-landing, or interface change.

## Direct proof and source identities

`formal_verified_import/{prove.ys,proof.log}` is the direct ORIGINAL RTL-vs-native SAT20 proof, terminal SUCCESS. `miter.sv` asserts actual valid equality and payload/error equality whenever EITHER actual output is valid. The only reset assumption is initial legal reset at step1; subsequent reset/valid/data are unrestricted. No set-init option, no warm mask, no ongoing reset masking. Top inputs are defined, clk1 at each step; only initial reset step is skipped. Lowering is read_verilog -sv; hierarchy; proc; flatten; opt_clean; async2sync; dffunmap; opt_clean; sat. SAT completed1437.28s, peak4893.61MB.

`final_packet/input_identity.sha256` pins actual remote original RTL, probe/miter, canonical keep, cloner, tool, model, native graph, mapped graph, retained graph and proof script/log. `final_packet/source_snapshot.tar.gz` and compressed cells.v/mapped.v/mapped.json make those inputs independently replayable. `receipts/image.id` equals final packaging image_current.id; all jobs used the same local openroad/orfs:latest image and proof log records Yosys0.68+post. Per-container IDs were not separately retained after Docker --rm; the image equality assertion is in final_packet packaging log.

## Initial state, first valid, and in-flight reset

`capture_depth.py` reproduces native source byteforbyte from original mapped.json and checks every primitive input/clock/reset family and output family. Both combinational and capture graph are acyclic. `receipts/capture_depth_bound_valid.json` gives maximum7 captures for y,err,valid; independently initialized clones converge by capture7. Generic cloner ledger first-edge wording is superseded by the full DAG bound.

The certificate extracts the ACTUAL production-valid chain: valid_in -> u_ca.rv -> s1_v -> u_cb.rv -> u_cd.rv -> s2_v -> u_cc.rv -> valid_out. Every stage is ASRHQN with exact clk, actual rst_n, SETN1, inverted QN observed as valid0 on reset. All7 stages clear at ANY asserted reset; first valid needs7 subsequent captures. This is source topology, not an external warm-up assumption.

`valid_firstuse/{prove.ys,proof.log}` separately proves actual gold/native valid equality and no early actual valid before7 captures after arbitrary reset. The observer count never drives either design. `first_use/*` gives five independent random-initial-state Verilator5.050 seeds, each49990 comparisons with no20-cycle warm mask and repeated off-edge in-flight resets. Acyclic7-capture data/control window plus direct arbitrary-input SAT20 covers every later sliding window; no independent power-up output-valid guarantee is claimed without the initial legal reset.

## Exact sequential models

`seq_coupon/canonical_model_identity.json` pins exact canonical PDKSEQ, full imported cells.v, and extracted ASR/HQN bodies. Canonical PDK UDP ASR544/HQN128 and BOTH exact imported-model coupons PASS. Our Yosys0.68 import equations are correct; GROUP's separate0.67 import failed. No blanket library/model qualification is claimed. Final canonical compatible model3905 is not substituted into this proof because its own unchanged import already passed the same PDK coupons.

## Physical preflight measurements

`receipts/native32.json` is retained canonical keep+synth+ABC strict all-driver check: ZERO non-tie loads>32 including input/reset, source cloner limit24. Native primitive count includes real fanout consumers, no buffer hiding. Baseline597FF/377.57826um2 -> retained629FF/384.2559um2, delta32FF/+6.67764um2(+1.77%); depth estimate288.4ps/9levels. This is native pre-layout estimate, not routed timing. Full5TT Liberty hashes are in receipts/libraries.sha256. Helpers/read_liberty port directions and exact primitive ledger are retained.

## Default compatibility and caller strategy

Keep released `ot_hdc_fp32_add_lat.sv` byte-identical. Proposed isolated wrapper `ot_hdc_fp32_add_lat_fan32` defaults SAFE_DIST0 and directly instantiates original LAT/CUTS/DRST implementation. SAFE_DIST1 selects the new technology-specific graph ONLY for LAT7/DRST0/default(all4)cuts. Current released wrapper rejects every other SAFE_DIST1 parameter configuration explicitly at elaboration; SAFE_DIST0 alone keeps every legacy profile. See WRAPPER_INTEGRATION.md and actual wrapper_integration_receipts for the post-review implementation. Caller opt-in parameter defaults0; no existing PVM/COLL source pin or default behavior changes. The MAIN-based implementation replaces rejected stage-part prototypes with the exact reviewed graph in a separate new wrapper; historical failed packets remain on the engineering branch.

PVM caller is LAT7/DRST0/defaultCUTS at u_core.g_safe.g_madd[0..15].u_m. HBM owner binds only after ROOT approval, then performs actual full caller all-root native32 census and source/Lib identity audit before any gate. COLL controls are separately qualified but still230 arithmetic violations; its fixed native graph may prevent constant-operand pruning, so full caller area/FF/storage census is mandatory (standalone+1.77% is NOT a whole-COLL claim). No new schedule edges.

Separate auto-name RTL->mapped `mapping_equiv` diagnostic terminated with1912 unproven equiv points, not an output counterexample; original failed diagnostic retained. The direct originalRTL-vs-native SAT20 proof is PASS and does not use these unproved seam assumptions. Prior initial SAT interrupted during model investigation is unqualified and not this proof.
