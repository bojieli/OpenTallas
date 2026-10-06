# DS ROM S81 die r8: the wired netlist (CLAUDE S81-DIE, 2026-10-06)

Tool: `tools/dsrom_s81_fulldie.py --gen r8` (`plan | check | real | grt | ir | record`, `--die layer|head`,
`--elem-h`, `--pairs`, `--field-margin`). Without `--gen r8` the tool still builds the r7 die of `21fcf6469`,
and its records reproduce unchanged (only the tool sha differs).

The die-top lint at `7ccef3810` (`results/rtl/die_top_lint_20261006/findings.json`) showed what the `21fcf6469` pass
covered: physical feasibility of a netlist with connectivity holes. The x chain was undriven at 2,161 of 2,417
pairs. The cfg ROMs and the return nodes had no clock. There were no forwarded stages and no meso FIFOs. r8 builds
the same die from the same blocks, with every die-level connection bound to a real port.

## Records

| file | content |
|---|---|
| `floorplan.{json,def,svg}`, `head_die/` | floorplan, instance census, forwarded-chain census, field round-trip stages, slot/capacity report |
| `dsfd_glue.sv` | generated glue RTL: stations, column FIFO, slot stations, node wrappers, hub CDC blocks |
| `feasibility.json` | every OpenROAD case below (layer `r8*`, head `h_r8*`) |
| `lint/` | die-top lint (python graph + physical) and the Verilator `--lint-only` summaries of both r8 tops |
| `cfg7_seq_bench/` | exact gate of `rtl/v41die/ot_s81_cfg7_seq.sv` (gold + 2 negative controls) |

The case dirs are kept on ot-epyc2 at `/srv/opentallas-scratch2/scratch/claude/s81-die/cases` (final) and
`cases_v1..v9` (earlier GRT rounds).

## Findings fixed (lint IDs)

FINDINGS_TABLE

## Physical results (final r8 geometry) against `21fcf6469` (r7)

PHYS_TABLE

## GRT rounds (k16, 5 iterations, layer die)

GRT_ROUNDS

## Slot height and elements per die (owner decision 2026-10-06)

The element frame height sets the slot: slot = cfg band 77.76 + element frame + 4.32 um. The QELEM frames have
FH + 6.48 = frame. The slots per column are the slots that fit the field height, with a field-to-band gap of at
least 216 um on each side (`--field-margin`). The pairs per die come from the generator's exact frame packing:
the BF share is kept, a q slot holds two pairs, and a BF slot holds one.

SLOT_TABLE

## Open items and owners

OPEN_ITEMS
