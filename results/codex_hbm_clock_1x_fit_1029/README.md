# HBM native 1x clock-stage calibration

Shared `ot_clk refit --placed-stages` now fits the street_body configuration's actual 1x routed stack. Earlier entry `inv2_ndr_hbm_trial2b_early` belongs to a different NDR stack; it remains available for historical replay. This is a calibrated model for a new build, with full-die GRT and real-view STA still required.

Inputs are retained unchanged from intel2 `codex-hbm-clock-0300/channel_pg_grt/{nodes_TT.txt,nodes_FF.txt,arr_TT.txt,arr_FF.txt}` and sibling `channel_pg_sm3_v2/{tree_frozen.json,ctree.v}`. The routed coupon has 386 native clock cells, 34 taps, and 67 logical nodes; its 66 logical legs contain 2-18 retained physical stages each. The shared fitter follows `parent_of` and `sites`, rather than inventing ideal stage counts. Native stage lengths span 2.16-298.08um.

Run `python3 normalize.py` here to normalize the raw readout and fit the 34 actual tap wires. Raw N rows contain max-rise, max-fall, min-rise, min-fall; normalized early is min-rise (token 4). The previous generic parser would take max-fall (token 3). All logical-node outputs are true source-rise polarity. Tap lengths span 8.846-334.498um; TT/FF RMS1.805/1.757ps.

From the repository root, reproduce the stage fit with:

```
python3 tools/clk/ot_clk.py refit tools/clk/configs/hbm_street_body.yaml \
  --tree results/codex_hbm_clock_1x_fit_1029/raw/tree_frozen.json \
  --arr-prefix results/codex_hbm_clock_1x_fit_1029/actual --corners TT,FF \
  --id inv2_1x_hbm_native_sm3_early \
  --tap-from results/codex_hbm_clock_1x_fit_1029/tap_actual.json --placed-stages \
  --route 'HBM NW_sm3 native 386-cell body/PG clock-only GRT, M8/M9 1x' \
  -o /tmp/hbm_stage_cal_actual_1x.json
```

Early-rise stage RMS11.53/10.21ps TT/FF, maximum residual26.61/22.89ps; detailed percentiles and interpolation range in fit_scope.json. The FF negative linear term is regression covariance with the positive quadratic term; it is not a physical negative-delay claim. `refit.log` compares with the tool's uncalibrated BUFx24 fallback because the old NDR entry correctly fails stack matching. No clock uncertainty or die gate changes.

`ot_clk check` passes the actual1x entry and rejects config_wrong_ndr.yaml (wrong calibrated stack). The generic fitter's four focused positive/disconnected/missing-site controls passed in the source implementation. No physical job or die sign-off was launched by this fit.
