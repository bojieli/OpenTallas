# qwen-fulldie STATUS (handover to Codex, 2026-10-03)

The branch is claude/qwen-rom-fulldie-20261003. The tool is tools/qwen_rom_fulldie.py. Records are in results/rtl/qwen_rom_fulldie_20261003/, with a README.md and a REPLAY.md. The remote root is /srv/opentallas-scratch/claude/qwen-fulldie/cases on ot-epyc1tb. The runner is cases/run_case.sh, which writes `<log>.exit`.

## Corridor-gate constraints adopted (claude/qwen-corridor-gate @ 89e70dd78)

- The tile tap row is centred on its station.
- The station frame is 52.704 x 69.12 um, which meets the >= 17.28 um slab.
- The bundled GRT gives M2-M5 an adjustment of 1.0, so no long haul runs there.
- Link stages are pitched at <= 430.56 um. Hub<->stack goes from 46 to 52 stages: +432 cycles/token (+0.36 us), which must be reported to the model.

## Results so far

- **Floorplan.** 792.36 mm2 against 815 mm2, a 22.6 mm2 margin.
- **(a) Legality and pin access.** Legal: 0 overlaps. Track assert PASS: 7.17 M pins, 0 off-track. pin_access: macroNoAp = 0 (a2_real, constrained geometry). pdngen macro grids FAIL (PDN-0217): the abstracts have no power pins.
- **(c) IR drop (PSM).**
  - At the r2 PG, rail-to-rail is 74-118 mV against the 35 mV budget: FAIL.
  - Bump-aligned straps plus all-power bumps over the core give 21-25 mV: PASS.
  - The shoreline window comes to 35.3 mV, unless strip coverage is doubled (2x gives 33 mV).
- **(b) GRT, k=32, 5 iterations, constrained.** Central tree top: overflow 5,367. Banded: 2,491. Overflow sits in the spine vertical link channel M9 and the hub/tree top at the mid-line.
- **(d) Clock.** Insertion is 29 / 15.5 / 3.8 ns depending on the wire model. A single synchronous die tree is infeasible, so FIFOs or a mesh are needed at the top-level splits.

## Running (detached; leave them)

- b2_k16_i5 and b2_k16_banded_i5: k16, 5 iterations.
- b2_k16_banded: k16, 50 iterations.
- superseded/: the r1 runs with M5 open. They are kept as evidence and summarised in feasibility_r1_m5open.json.

## Next steps

1. When the k16 runs exit, rsync logs and gcell_usage.txt, then run `python3 tools/qwen_rom_fulldie.py record --work <pull dir>`. Locate hotspots by region and update README §2(b).
2. If the spine link channel M9 still overflows at k16, try VCH 174 -> ~260 um or move the port slabs off the channel. Rerun as b3_*.
3. Give the element abstracts VDD/VSS M7/M8 pins so that the full-die pdn.tcl (macro grids) can run. Then re-derive pdn.tcl with the bump-aligned pitches.
4. Price the banded tree top (16 block words per band slab; result write serialised) in the uarch model before adopting it.
