# Preserve original clock RC and native GRT DATA RC

Use native `estimate_parasitics -global_routing`, then load the original, prequalified CLOCK-ONLY SPEF with the exact existing dataset name:

```tcl
source clk_freeze.tcl
ot_clk_restore_parasitics [dict create tc original_clock_only.spef bc original_clock_only.spef]
```

Q1/Q2 use `tc` and uppercase `BC`; HB100 uses `tc`/`bc`. Names are case-sensitive. The helper checks all files and existing datasets before annotation changes. It is opt-in and does not route, estimate, change units, edit clocks, or change timing constraints. The original clock graph/wires/cell masters must remain unchanged; retain the existing clock freeze/geometry checks. It accepts prequalified clock-only SPEFs, not a full old design SPEF.

The installed OpenROAD binary is `26Q3-1510-g6cb3f2b704`, whose OpenSTA submodule is `509913b1398b36eda23caa1f1f380167465dceee`:

- [Native GRT estimator](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6cb3f2b704/src/est/src/EstimateParasitics.cpp#L615) creates separate existing parasitic datasets named after each scene, bound to both min/max.
- [Installed `Sta::readSpef`](https://github.com/The-OpenROAD-Project/OpenSTA/blob/509913b1398b36eda23caa1f1f380167465dceee/search/Sta.cc#L4226) creates/replaces a dataset when the legacy `-corner` form omits `-name`; explicit `-name` finds the existing dataset instead. Repeated legacy reads therefore discard native DATA RC. The hidden `-increment` flag is parsed but unused.
- [Dataset existence guard](https://github.com/The-OpenROAD-Project/OpenSTA/blob/509913b1398b36eda23caa1f1f380167465dceee/search/Sta.cc#L4280) errors if a requested annotation name is absent; the helper performs it before any reload.

Actual HB100 control, owned/executed by KV/HR, is terminal PASS in intel2 `/srv/opentallas-scratch2/claude/codex-kv-hr-1030/phypad_hb100/hb100/grt_named_restore_check.log` using the original unmodified clock SPEF:

```
HB100_NAMED_CLOCK_READ_DATA_CAP_MAXDELTA_SI 0 changed_values 0 probes 23321 both_corners_min_max
HB100_NAMED_CLOCK_NATIVE_ARRIVAL_CHANGED 0 pins 4776 both_corners
PHY_HB100_PROTO TT worst_slack_ps 147.168396 groups 3
PHY_HB100_PROTO FF worst_slack_ps -35.549076 groups 3
```

Every DATA net's total/wire capacitance in both corners and min/max remains equal; every clock-pin arrival report in both corners restores exactly. The per-net DATA and clock reports are retained alongside that log (`*named_control.tsv`). The now-valid FF hold failure remains a real physical failure; no DRT/signoff adoption follows from this RC-method pass. Q1B2's repaired ODB/guide are saved and its owner is applying the same method with the correct uppercase BC dataset.

Rejected methods are preserved in HR's lane: plain `read_spef -corner` changed native DATA annotations, including all800 values in the coupling-grounded control. Ground projection also had an endpoint-ownership bug and was not adopted. The failure is a dataset replacement issue, not evidence that partial same-dataset clock loading must clear DATA. Native DATA SPEF export/merge and terminal-cap reconstruction are unnecessary for this method; those unqualified paths are not used for STA.
