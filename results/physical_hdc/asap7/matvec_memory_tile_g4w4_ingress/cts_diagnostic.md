# G4/W4 related ingress clock: source-pinned CTS checkpoint

The full physical experiment started from clean commit
`03a5570d676d80dcc5e1b46b4277a000f76192b3`. Its independent flat
bank-model Verilator gate passed 16 exact 16-lane output slots across two
addresses, plus ingress commits. The test drove `ingress_clk` and `clk` with
the same waveform. A later compatibility commit made the split clock opt-in;
it did **not** change this run's source pin.

The retained [`cts.json`](cts.json) is a completed **post-CTS**, placement-
estimated checkpoint, **not** a detailed-route verdict. It uses ASAP7 RVT
TT, 0.7 V, 0 °C, a 1.5 ns period on both related clocks, 320 ps maximum
transition, 60% slew-repair margin, and 15% target core utilization. The
assumed source-synchronous ingress contract places `kv_load`, `x_load`, both
load addresses, and both load data buses at **0.75 ns minimum / 1.15 ns
maximum** after the ingress clock edge. All other inputs retain the 0.3 ns
default input delay relative to the core clock. No physical HBM interface
measurement establishes this contract.

| Placement-estimated CTS metric | Split ingress clock | Matched G4/W4 single clock |
| --- | ---: | ---: |
| Core register clock sinks | 22,194 | 22,856 |
| Ingress register clock sinks | 662 | 0 |
| Macro clock sinks | 9 | 9 |
| Core register tree depth | 19–22 | 22–24 |
| Ingress tree depth | 15–17 | — |
| Setup WNS | −203.112 ps | −405.282 ps |
| Setup violating endpoints | 631 | 1,057 |
| Hold WNS | −590.117 ps | −643.935 ps |
| Hold violating endpoints | 728 | 790 |
| Inserted hold buffers | 10,765 | 17,478 |
| Maximum transition violations | 8 | 19 |
| Standard-cell area | 22,538 µm² | 23,039.2 µm² |
| Macro area | 113,104 µm² | 113,104 µm² |
| Placement violations | 0 | 0 |
| Limiting core-clock Fmax | 587.16 MHz | 524.857 MHz |
| Engineering verdict | **NOT_MET** | **NOT_MET** |

Both buffer counts are **incomplete repair attempts**, so their difference
is not evidence of hold-buffer savings at closure. During repair, the worst
hold endpoint moved to `u_me.xcs_r[0]/D`, a core control input outside the
split load-port contract. The endpoint was observed in the live CTS log;
the driver cleaned that temporary log after producing `cts.json`. The
final record contains the path slack and violation counts but not endpoint
names. The final setup endpoint during CTS was `o_data[206]`.

**Fmax reporting caveat:** the source-pinned driver copied ORFS's aggregate
`cts__timing__fmax` of 1,856.69 MHz, which is the faster ingress clock. The
raw metrics in `cts.json` give 587.16 MHz for `core_clk` and 1,856.69 MHz
for `ingress_clk`; **587.16 MHz is the limiting tile clock** at this
checkpoint. Driver commit `ed699134` fixes future multi-clock records to
use the minimum per-clock Fmax and retain the ORFS aggregate separately.

The tile has one analytical ROM macro, four analytical KV SRAM macros, and
four analytical vector SRAM proxies. Their LEF/Liberty views are estimated;
their GDS views do not establish macro-internal layout. ROM depth is 8,192,
KV/vector depth is 1,024, and only 32 bits of each vector SRAM's 256-bit
word are used. The checkpoint says nothing about full Qwen-core closure or
manufacturable macro timing. A separately pinned full OpenROAD route is
still running on this source.
