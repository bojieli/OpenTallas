# Bounded S81 continuation — Codex, 2026-10-06

No new route submitted. Preserve the active Claude replacements at `3f0455126`.
No closure, adoption, main integration, timing relaxation in a production job, or physical export claimed here.

The isolated branch `codex/s81-tile-continuation-20261006` began at local
`claude/s81-placeholders-20261006` = `41c34fce0`. During work, that branch advanced
through `1ee4b8967` to `3f0455126`; its changes and running jobs were left alone.
Parent exclusively integrates main. No subagents; no closure-loop or HBM-generator edits.

## Failure triage

All three original routes have DRC 0. Original and ECO records are in `failed_jobs/`.

| Tile / source | Original SS / FF ps | ECO SS / FF ps | Limiting class |
|---|---:|---:|---|
| ctrl_pc / 093da5918 | 64.93 / -6.95 | 19.59 / 12.80 | FF output hold; ECO SS k_rdy -> k_wdata |
| svcio_od / 093da5918 | 40.25 / 4.15 | -17.65 / 17.93 | FF output hold; ECO SS sel_c -> o_d, input-to-register margin 3.73 |
| colt_lane / 7345266ce-e | 47.67 / -9.99 | -4.42 / 11.00 | FF ow -> t_w (398 endpoints in ledger); ECO SS w[509] -> rem[8] |

No RTL stages were added for controller or collector hold. No SRAM clock-to-Q,
II-2/multicycle behavior, clock period, setup/hold uncertainty, or original
failure evidence was changed.

## New flow audit: 1ee4b8967

The old effective output FF requirement was `round(BCmax) + 50 ps`.
The new effective requirement is `round(BCmin) + 65 ps`: virtual clock latency L,
output min delay `L - round(BCmin) - 40`, plus the retained 25 ps hold uncertainty.
This is algebraically equivalent to the budget generator's zero-wire convention:
virtual receiver clock at BCmin, output min delay -15 ps, and 50 ps IO uncertainty.
It is a real change of the boundary assumption, not an improvement to routed hardware.

Read-only STA on each unchanged pre-ECO routed ODB/SPEF/SDC confirms this equivalence:

| Tile | Old output FF ps | New formula ps | Explicit zero-wire model ps | Max per-pin difference ps |
|---|---:|---:|---:|---:|
| ctrl_pc | -6.949746 | 15.050266 | 15.050266 | 0 |
| svcio_od | 4.152095 | 25.152103 | 25.152088 | 0.000016 |
| colt_lane | -9.988288 | 47.011726 | 47.011726 | 0 |

The unchanged pre-ECO internal-register FF minima are 30.33 / 27.78 / 22.66 ps,
respectively. The above table reports output-only STA, not new route verdicts.
No files in the original job directories were written. Docker mounts of `/work`
and `/src` were read-only. Audit scripts, logs, source hashes and DB/SPEF/SDC hashes
are retained under `audit/`. An initial container executable lookup failure is
also recorded; it was a test-driver error, not a design failure.

Boundary qualification gaps remain:

- Controller sheet: target-grade insertion; all listed widths are zero; `rq` is
  labelled output and `r_data` input despite RTL declaring the opposite; the PHY
  ports have null clock_domain and 833.333 ps despite the tile's distinct 900 ps
  hbm_clk. The new hook does handle hbm_clk separately, but the sheet is not a
  complete executable pin/domain contract.
- There is no `dsfd_svcio_od` tile sheet in the inspected budget inventory. The
  older `dsfd_svc_io` slab sheet gives `od` a forwarded-clock boundary and 611.2 um
  distance. Its output_min_delay_ff_ps is -19.2: with the generator's sign convention,
  its output hold requirement is BCmin + 30.8, less strict than zero-wire +65.
- The collector sheet's t_w distance is 371.3 um and output_min_delay_ff_ps is -26.6,
  yielding BCmin + 23.4; again zero-wire +65 is stricter, conditional on the same
  reference-clock convention. That does not establish the real receiver insertion.
- Both new jobs disable budget enforcement and do not pin the budget generator/sheets
  in their source commit. Their source commit does not contain those files.
- Report_clock_latency's all-leaf minimum is not automatically the calibrated
  boundary-leaf minimum. The die must bind the chosen receiver clock reference,
  region skew/forwarded clock, wire and actual per-domain FF arrival.
- ctrl_pc's conditional +15.05 has only 0.05 ps over the acceptance line. Preserve
  the real replacement route and judge its measured result; do not round this audit
  into a robust closure or relax the +15 line.

Thus the formula is validated against the stated zero-wire FF model, but these
jobs are NOT yet validated replacements for die-context adoption. Keep them running.
Repair/validate the boundary sheet and actual receiver binding before adoption.

## Existing replacements

At the 22:33 status snapshot both are RUNNING/calibrate on EPYC3:

- `s81ph-dsfd_ctrl_pc-3f0455126`
- `s81ph-dsfd_svcio_od-3f0455126`

Their exact benches passed; controller MUT_PACK failed as required. The OD
summary confirms three exact seeds PASS and both NOATOM and SKID FAIL, although
its job JSON only enforces NOATOM as a separate negative stage. Job snapshots and
bench outputs are retained. No newer collector successor was in that snapshot;
the collector result is triaged here, not independently re-routed.

## Parked structural fallback

Built before discovering the concurrent flow successor, never submitted:

- `7ad89fba6`: unified-model sizing plus OD-only opt-in input pin capture/three-entry
  credit-counted queue and masked-source register before the merge OR.
- `487315fbb`: directed latency, uninterrupted drain and malformed-header-fault bench.

`MARGIN=0` / `OD_MARGIN=0` remain the defaults. Legacy shared skid/merge RTL and
existing benches are byte-identical. Only the OD tile/composition gains an opt-in
parameter. Changed/new paths are the `svc/*od_margin*` files,
`svc/tb_s81ph_svc_od_latency.sv`, `svc/ot_s81ph_svc_io_tiles.sv`, and the appended
`dsrom_s81_svcio_od_margin_price` function in `tools/uarch_model.py`.

Validation: three randomized transaction seeds PASS (300 frames/source each),
three default-off regression seeds PASS, NOATOM and lost-slot mutants FAIL.
The minimum two-tile comparison measures input acceptance to first output:
legacy 4 cycles, successor 6, exactly +2; 300 uninterrupted words prove II=1,
and the malformed header raises sticky fault in both. See `bench_results.json`.

Price: +2 cycles = 1.6667 ns per exposed frame at 1.2 GHz, unchanged II=1;
6400 added-register/control-bit reservation and 2635.13 um2 gross cell-growth
budget (9.41% of the existing 216 x 129.6 um slot). The explicit 244-exposed-frame
scenario costs 406.67 ns, NOT a proven caller count or headline delta. Native
exposed frame count, whole-token AR/MTP composition, SS/FF route, routing-layer
check and die-context STA remain adoption blockers. Leave the fallback off and
avoid duplicating the active flow successor.
