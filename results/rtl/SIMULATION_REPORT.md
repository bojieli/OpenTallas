# Public two-simulator RTL campaign

**Overall status:** PASS

Icarus Verilog and a separately compiled Verilator C++ executable both pass. The C++ scoreboard independently implements signed dot-product saturation, FIFO ordering, and multi-sink credit conservation; it does not call an RTL helper algorithm.

| Test | Simulator | Result |
|---|---|---|
| `iverilog_tile` | Icarus/vvp | PASS |
| `iverilog_reference_units` | Icarus/vvp | PASS |
| `iverilog_cdc_reset` | Icarus/vvp | PASS |
| `iverilog_stage_integration` | Icarus/vvp | PASS |
| `verilator_randomized_units` | Verilator/C++ | PASS |

## Independent executable

- Seed: `0x4f54564c`
- Cycles: 20,502
- Scoreboard checks: 131,724
- Exercised saturation, poison, invalid bubbles, full/stalled and full/recycle FIFO states, credit exhaustion, and atomic release/reserve recycle.

## Verilator DUT coverage

| Metric | Hit/total | Percent | Unit-scope target |
|---|---:|---:|---:|
| Line | 25/25 | 100.000% | 95% |
| Branch | 32/34 | 94.118% | 90% |
| Toggle | 305/332 | 91.867% | 85% |

These percentages close only the named three-block executable scope, not the stage or project-wide coverage gate. Wrapper points are excluded; legal-traffic error outputs remain in the DUT toggle denominator.

## Evidence boundary

This is public-tool RTL simulation evidence. It does not qualify target numerical formats, model quality, ROM/HBM/PHY macros, package behavior, or PDK timing/power.
