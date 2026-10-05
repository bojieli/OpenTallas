# V4.1x pooled-index physical gate

Basis: adopted RTL commit `3799243c1eca4b01afcea4a71e5c6e9d7d0cf941`.
View: predictive ASAP7, RVT TT, ORFS image
`sha256:af971398d91e5d154ec40d3df26554efd8790107268a4c7f1e6bb8f222979d34`.
These are characterization periods in one local clock domain, not a die clock
claim. All non-clock input ports are false-path sources; output delay is zero.
For completed routes, the generated SDC and config files, source hashes,
mapped netlist and its hash, and extracted timing report are archived beside
the JSON record. The large final DEF/GDS/SPEF files are SHA-256 recorded by
the runner but not retained; rerun the command to regenerate them.

## Scope and commands

The producer is `ot_hdc_v41x_idx_pool_kwr`: 128 BF16 captured elements,
four 32-element FP4/scale encoders, sector-address arithmetic, and the
four-stack HBM write interface. The core's pooled MP=2 connection supplies
`NL=16`; the module default `NL=8` is a reduced producer slice. The consumer
is `ot_hdc_v41x_idx_pool_finish` at the adopted `G=4,M=2,IH=32`: pooled score
collection, metadata FIFO, head sum, and BF16 output. No SRAM, HBM controller,
HBM PHY, full key read bank, or query operand loader is inside these two route
boundaries.

Run from the repository root:

```sh
bash tools/run_hdc_v41x_idx_pool_kwr_physical.sh pnr results/physical_abi3/asap7/hdc/v41x/ot_hdc_v41x_idx_pool_kwr/physical_nl16_12ns_slew.json 12 kwr16_12ns_slew --param NL=16 --max-transition-ns 0.32 --slew-margin-percent 30 --max-fanout 32
bash tools/run_hdc_v41x_idx_pool_finish_physical.sh pnr results/physical_abi3/asap7/hdc/v41x/ot_hdc_v41x_idx_pool_finish/physical_2ns_slew.json 2 finish2ns_slew --max-transition-ns 0.32 --slew-margin-percent 20 --max-fanout 32
```

Both scripts use 35% floorplan core utilization and the pinned toolchain in
`tools/run_abi3_physical.py`. The input false paths remove neighboring
producer/consumer launch timing; outputs have zero delay and a modeled load.
The worst reported consumer setup and hold paths are internal
register-to-register paths. The records contain the exact false-path port
lists and output load.

## Completed probes

| Gate | Period | Status | Cell area µm² | Setup / hold WNS ns | Slew / cap violations | DRC / antenna | Routed wire µm / vias | Global-route congestion |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Producer, adopted `NL=16`, explicit slew | 12 ns | **NOT_MET** | 11,194.3 | +0.910 / +0.053 | 2,328 / 1 | 0 / 0 | 1,342,859 / 1,739,438 | 46.58%, zero overflow |
| Producer, `NL=8` default | 12 ns | NOT_MET | 6,977.87 | +0.798 / +0.045 | 2,347 / 1 | 0 / 0 | 609,571 / 891,204 | 32.50%, zero overflow |
| Producer, `NL=8`, explicit slew | 12 ns | NOT_MET | 7,119.84 | +0.913 / +0.051 | 291 / 0 | 0 / 0 | 609,665 / 887,288 | see routed record |
| Consumer, `G=4,M=2,IH=32` | 2 ns | NOT_MET | 16,068.6 | +0.666 / +0.026 | 5 / 0 | 0 / 0 | 454,447 / 1,071,524 | 11.18%, zero overflow |
| Consumer, explicit slew | 2 ns | **PASS** | 16,094.4 | +0.768 / +0.028 | 0 / 0 | 0 / 0 | 453,799 / 1,073,287 | 11.17%, zero overflow |

The adopted 16-lane producer completed full routing and extraction. Its
global route consumed 46.58% of routing resources with zero overflow and
estimated 1,518,181 µm wirelength; the final routed wirelength is in the
table. Positive setup/hold slack and clean geometric DRC do **not** close
this tile because its final netlist violates the explicit 0.32 ns slew
constraint 2,328 times and has one max-capacitance violation. Its global-route
log, extracted timing report, SDC/config, mapped netlist, and JSON verdict are
retained. This is a physical electrical blocker at the chosen local period,
not a validated producer clock.

The original producer 2 ns timing probe was stopped during detailed-route
repair after global routing showed −7.048 ns setup WNS. Its runner record has
status `error` because the run was deliberately stopped; the retained
`partial_2ns/5_1_grt.json` and log are **not** final route or DRC evidence.

The combined `ot_hdc_v41x_idx_pool_batch` synthesis was stopped after 37
minutes in Yosys SAT-based resource sharing at about 6.25 GiB RSS with no
mapped netlist. Its partial runner JSON records the interrupted command and
the eleven exact RTL source hashes; it gives no mapped area or timing claim.

## Hash and memory ledger

`ot_hdc_v41x_idx_pool_kwr.sv` SHA-256:
`76a7658ee2e9a7ab063ec799412b94b200b60a7a4c8803c70fafd9875be9f21a`.
The six consumer RTL source hashes are embedded in each consumer JSON record.
For the completed first routes, the producer SDC/config hashes are
`1bddba0ee3324bb708ab5d7e457c1a7c427863d358d90012c069d56cd0851b23` /
`e0fcd79b56dbf85bf2722f250d196a582ab9012b37f67ef346b7090215b66016`,
and the consumer SDC/config hashes are
`7e2f5848e0604313ebef5c8269d17a1373972b59180f2eef83167454a4e46939` /
`de3764b3ce4f23e023bee133d77394623b84d06d1422146ce8a88e285134cb7d`.
The constrained runs have separate hashes in their JSON records.
For the adopted `NL=16` producer route, SDC/config/mapped-netlist SHA-256
values are
`8495e0593db759d61edf4416779bc5f621e7eee27c95af414efb6c1b0f92f382` /
`97c0b3bae65d64696d7ccc3f86b7a2bb94328d4e3fd301867e96a13aba24698c` /
`a8a48b95edf4e848761cbe79c76fe9f0549fa4394228093b43eafce0083f0eca`.
For the passing consumer route, SDC/config/mapped-netlist SHA-256 values are
`6e08933d1be1c627e08ee725446a4e5af4ed24f8b12b683bd0cafcf0ffbfe0d6` /
`8492a0f7813355ea625e40d31ff953c14042f47c1d86b95c0495cb2b371c78da` /
`465a4ff1f6f3faf6db4a8f08a179ae61e8e383948827311417aadcd8c18e8090`.

Both completed boundaries have `macro_count=0`: their internal banks map to
standard cells. The repository's `physical/asap7_memory_macros` views are
generated analytical macro collateral and are not instantiated by these RTL
boundaries. No foundry-qualified SRAM view matching the 64×544 pooled key
bank or full HBM subsystem is fitted here. This gate does not validate memory
array density, read latency, multiport delivery, cross-tile clocks, package
collectives, full-die area, or a target-process operating frequency.
