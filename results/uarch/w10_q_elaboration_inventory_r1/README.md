# Current Q source elaboration inventory — no physical admission

Source b046de7f0, exact ORFS image af971398d91e5d154ec40d3df26554efd8790107268a4c7f1e6bb8f222979d34. Model-only read/hierarchy/proc/opt/memory_collect; no ABC, techmap, placement or route. NB2/MTP1/EARLY1/FAST1/PP1/FRONT_PAR0/WAKE_REG1; inner BF16=0, XF4, LAT8. MTP1 is the boolean configuration mechanism, not a six-position runtime trace. This inventory supplies no new exactness or latency qualification.

The successful r2 coarse netlist is retained at the absolute path and SHA in inventory.json. It contains four 4096x274 ROMs and eight ICGs. Register storage is 25342 bits; 33 retained memories add 5480 bits, charged as DFF storage without free SRAM credit. Read muxes total 5962 and write muxes 9832 under the explicit full-selection construction. Write clocks are verified single-net per memory, including multiwrite-port memories. Logic driving those muxes, reset/enable lowering and all other combinational primitives still require a complete construction budget.

Clock inventory preserves nine distinct net groups including four macro-only groups. The conditional 14-stage fanout-32 construction charges 1114 buffers, input capacitance 1248.794 fF and guard-2 output-wire capacitance 162004.564000 fF. These are conditional inventory coefficients, not extracted route or power bounds. Every group uses activity upper envelope 1; root-stop credit is zero. Actual sink capacitances, root-versus-leaf phase, load/slew, voltage, internal energy, spatial corridors, PG and IR remain unqualified. No TT baseline subtraction or historical q-area transfer is made.

The initial elaboration failed because hierarchy visited the default PP0 8192-row macro before parameter derivation. Its terminal evidence is preserved separately. r2 supplies both actual/default macro declarations and prunes the unused default branch; this is an elaboration-input correction, not an RTL change or hardware failure.

Replay:

```sh
python3 tools/w10_q_elaboration_inventory.py --netlist /home/ubuntu/w10-w18-recovery/baseline_wake/q_elaboration_model_r2/q_coarse.json --source /home/ubuntu/w10-w18-recovery/baseline_wake/q_elaboration_model_r2/source.json --script /home/ubuntu/w10-w18-recovery/baseline_wake/q_elaboration_model_r2/model.ys --log /home/ubuntu/w10-w18-recovery/baseline_wake/q_elaboration_model_r2/elaboration.log --output /home/ubuntu/w10-w18-recovery/baseline_wake/q_elaboration_model_r2/replay.json
cmp /home/ubuntu/w10-w18-recovery/baseline_wake/q_elaboration_model_r2/replay.json results/uarch/w10_q_elaboration_inventory_r1/inventory.json
PYTHONPATH=. python3 tests/test_w10_q_elaboration_inventory.py
```

Ram owns integer residency, descriptor and complete design-point composition. The root physical owner retains sole all-port escape/spatial clock/PG review. This source inventory supplies those owners with actual current Q storage and clocks; it does not qualify a footprint. Physical admission remains false.

## Finite construction hypothesis

`construction.json` prices a deliberately conservative NAND2/ASR-DFF Boolean implementation of every retained primitive, register, memory read/write mux and decoder, reset/enable selector, eight ICGs and conditional clock reserve. Unsupported primitives raise an error. Palette areas come from the recovered actual-worker LEF, joined by SHA. It allocates 107510.52888 um2 standard cells and 246546.516960 um2 for cell placement at unchanged 50% density plus four ROMs. This is an analytical allocation, not actual mapped area, a legal geometry, or a lower bound; its size cannot refute an optimized implementation.

At Ram's 3749 resident q pairs, this construction allocates 924.302892083040 mm2 per stage/rank before the separately priced 17.9871561456 mm2 q configuration, BF reserve, hub, legal corridors, taps/hold repair and PG. Those terms cannot be hidden in a slot or credited from historical q dimensions. The conservative construction does not establish a feasible complete-owner design point. A tighter current-source construction or actual mapping requires a separate budget qualification; no physical build is admitted by this record.

Reproduce construction with:

```sh
PYTHONPATH=. python3 tools/w10_q_constructive_area_bound.py --netlist /home/ubuntu/w10-w18-recovery/baseline_wake/q_elaboration_model_r2/q_coarse.json --lef /home/ubuntu/w10-w18-recovery/baseline_wake/local_fit_r1/actual_worker_R.lef --output /home/ubuntu/w10-w18-recovery/baseline_wake/q_elaboration_model_r2/construction_replay.json
cmp /home/ubuntu/w10-w18-recovery/baseline_wake/q_elaboration_model_r2/construction_replay.json results/uarch/w10_q_elaboration_inventory_r1/construction.json
PYTHONPATH=. python3 tests/test_w10_q_constructive_area_bound.py
```

Power has no finite qualified complete-element bound here: operating-voltage envelope, actual storage/macro clock capacitances, slew/load domain and cell internal-energy maxima remain separate required inputs. Setting activity to one removes free gating credit but does not supply those inputs. The conditional wire component must reconcile with existing modeled clock power before any delta is claimed. No synthesized root-stop provider or physical stop credit exists.
