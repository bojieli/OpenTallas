Actual B-selector vehicle correction, preparation only

The current physical R1/R2 kits modify `ot_s81ph_native_sel_su` in native_sel_lib, while their production top selects SEARCH_PIPE1 and elaborates `ot_s81ph_sel_su_pipe`. The two production pipeline source files have identical SHA256da2becfa97afb74a5d2c4767958d174a11865b2ba00ff1b25531e1329056ab29. Their full-kit equivalence receipt does not establish an active selector optimization. The reported positive CTS setup estimate was an FF scene, not TT closure.

These opt-in full-file copies and exact-anchor patches target only the active B-stage `aboveb` mux. R1 selects constant slices with a highest-one mask and a balanced OR tree. R2 registers that mask from `geb_nx` on the same edge as `geb`; it adds no external cycle. A-stage arithmetic, clocks, pins and defaults remain unchanged. No production source or existing kit is edited.

The smallest bench elaborates only the actual search pipeline plus its real prefix-adder helper. It compares every output of old/R1/R2 each edge after flushing the no-reset pipeline. Both actual configurations use Q4/CB11/XR6, with coarse QW11 and fine QW21. Inputs change every edge. The mutant changes only the R2 registered selector to stale `geb`, exposing a one-edge mismatch. It uses interface stimulus, with no forced internal state.

Run the prepared portable bench through `ot-run --crit --mem 1 --threads 1 --dir PKG --stage PKG -- bash PKG/run.sh PKG/out`. Read receipt.json and each run log. This component receipt is not whole-selector qualification or physical adoption.

Minimal fresh generation, NOT LAUNCHED:

```
python3 physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py \
  --module dsdv_bksel_c_pipe_r2 \
  --recipes tools/s81_ph/bksel_pipe_select_1131/recipes.json \
  --out OWN_KITS --trial
```

Use the corresponding r1 recipe for the constant-select variant. Fresh synthesis and official exact-parameter LEC are required; no old physical checkpoint or receipt qualifies changed RTL. Render the unchanged388.8x172.8/5513-pin source contract first; stop at actual placement and LOOK before CTS. R1 adds no state; R2 declares17 selector bits per SU, of which unused gh[0] is expected to optimize away, giving an estimate of32 additional live FF across coarse/fine units. This estimate awaits synthesis. New selector clock sinks must be included by the fresh clock planner. No constraints, floorplan slot or cycle price is relaxed. No new P&R has run.

The old production R2's actual TT GRT path also measured A-stage `acc_a` as critical (initial−251.754ps atacc_a[17], then−194.968 after10resize iterations; B res_above remained−163.856 after20). A+B companion variants and exact-anchor recipes now apply the same constant-selector/registered-NEXT substitution to A as well. A bucket15 selects ZERO; B bucket15 selects acc_b4. Neither adds a cycle. The new recipe keys are dsdv_bksel_c_pipe_ab_r1/r2. Their conservative added-state budget is64FF across both SUs; expected live count is about60 after unused/duplicate bits are optimized. This remains an estimate until fresh synthesis.

The minimum A+B cut bench extracts the actual compare/capture, select and result-register blocks directly from the source copies, retaining real sum/compare edge coupling. After four no-reset pipeline warmup edges, it exhausts all65,536 compare masks in an affine order with changing21-bit lane data, both actual quota widths and A/B fallback semantics. Quota/date and selected data are checked, with stale gea/geb selector-register mutants. Cut PASS is not full-SU/whole-kit equivalence. The unchanged full-SU bench attempt reached its1GB memory cap during Icarus elaboration and produced no functional verdict; its resource failure is retained under results/rtl/bksel_pipe_select_1131/full_su_1gb. No running full-SU job was restarted. Normal fresh whole-kit native LEC remains mandatory.
