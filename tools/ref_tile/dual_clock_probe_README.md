# Related dual-clock accounting probes

`probe_dual_clock_etm.py` builds a zero-wire parent using two actual VMX ETMs. Core clocks have period P and serial clocks 4P/3, with a common waveform origin. The parent connects actual core-launch `t_cd` to serial-capture `f_kd` and serial-launch `t_ks` to core-capture `f_cs`. All four actual clock pins must satisfy arrival + their own per-corner routed boundary mean = phi. The ETM arcs are copied unchanged. Both directions require actual setup and hold paths; a missing path fails.

The numerical oracle compares propagated baseline and compensated paths, reserving setup 60+90 ps, or 60+150 when either TT insertion exceeds300 ps, and hold100 ps. It independently checks every virtual and entry clock period. The 770 ps route-period probe retains the same4/3 relationship. Negative slacks are reported and retained; passing this accounting probe does not qualify a physical tile.

The default CLOSED VMX fixture has1167 normal input hold exceptions in its original `6_final.sdc`; its original ETMs consequently contain no hold checks. Full probing rejects those views. `--setup-only-diagnostic` permits explicitly partial accounting evidence. `tighten_diagnostic_input_hold.py` removes only those normal-data hold exceptions in a copied SDC and records every removed port and the exact original statement. Clock/reset exceptions remain explicit. Exporting this tighter copied SDC from the original ODB+SPEF+libraries produces actual diagnostic hold arcs without adding or changing arc math. It does not establish CLOSED status under the stricter constraints.

Prepare with:

```sh
python3 tools/ref_tile/probe_dual_clock_etm.py \
  --fixture /path/to/actual/vmx/fixture \
  --tool-root /path/to/clock/api/worktree \
  --out /tmp/dual-etm-probe \
  --diagnostic-record /path/to/diagnostic_exception_provenance.json
```

The fixture needs `dsfd_wfc_vmx_{tt,ff,ss}.lib`, `dsfd_wfc_vmx.lef`, and actual `insertion_core_clk.json` / `insertion_ser_clk.json`. The builder stages an exact per-pin `clock_measurements` record and hashes its source files and the tested clock API. Omit `--diagnostic-record` for an original qualified export. Add `--period 770` for route-clock scaling. After copying the generated directory to a fleet host, run its `run.sh` inside `openroad/orfs:asap7lock` through `ot-run`; `/probe` must mount that directory.

`--unmapped-input-mutant` must fail actual IO-domain coverage. `--zero-source-mutant` must fail per-pin numerical compensation. These mutants use the same actual ETMs.

`probe_related_phase_windows.py` is a separate synthetic diagnostic, never a production qualification fixture. Scalar launch100/setup50/hold20 models verify related-edge windows in actual OpenSTA:

| Launch | Capture | Minimum setup edge gap | Previous hold edge gap |
| --- | --- | ---: | ---: |
| Core rising | Serial rising | P/3 | 0 |
| Core rising | Serial falling | P/3 | 0 |
| Serial rising | Core rising | P/3 | 0 |
| Serial rising | Core falling | P/6 | P/6 |

Its equal-period mutant (`--serial-period 833.333`) must fail the independent expected-window oracle. The numerical results and their scope are recorded in `dual_clock_probe_evidence_1013.json`.
