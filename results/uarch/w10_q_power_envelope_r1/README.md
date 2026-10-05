# Finite conservative current-Q power allocation — thermal refusal

This companion prices the actual current-Q elaboration and finite Boolean construction from 301a8203a/6da3c7a60. The immutable exact ORFS image is sha256:af971398d91e5d154ec40d3df26554efd8790107268a4c7f1e6bb8f222979d34. Source extraction uses the real RVT SIMPLE/INVBUF/SEQ libraries, not the FAKE clock-flop libraries. Three characterized points are SS 0.63 V, TT 0.70 V and FF 0.77 V. library_sources.json binds compressed/uncompressed full sources and selected cell sections; power.json binds the actual sections and all three actual 4096x274 macro Liberty files.

Every cell's rise/fall energy is summed from the independent maximum absolute table entry across all states, related pins and rails, including mutually exclusive conditions. The per-cell envelope takes the maximum across corners. This overcounts energy rather than assuming mutually exclusive states are free. In these sources, mA*V*ps is fJ; standard leakage is pW and macro leakage is nW. Macro address/data buses are expanded to all 12/274 bits; bus capacitance is not treated as one pin.

Capacitive switching uses C*V^2*f, at 0.77 V and 1.2 GHz, with one rise/fall pair per cycle (activity 1). Every modeled cell input and every output's maximum load is charged independently; these overlap and are deliberately not subtracted. The maximum-output load envelope covers its downstream pin/wire load. The candidate clock's guard-2 500 um/buffer wire component and separate 200 um ICG wire are charged additionally. This is a conservative allocation for the declared construction, not an incremental subtraction from the historical TT clock model.

Numerical allocation per Q pair:

- Clock endpoints: 15568.791584 fF; buffer inputs: 1488.54908 fF; guarded clock/ICG wires: 162062.734400 fF.
- Clock capacitance switching: 0.12744035100653472 W.
- All storage/buffer/ICG/macro internal arcs: 1.7351848531025184 W. This includes data/reset/enable arcs and is deliberately broader than clock-pin-only power.
- Their combined clock-related allocation: 1.86262520410905312 W.
- Full construction switching: 39.01647190769745648 W; internal: 7.9594365048401184 W; leakage: 0.008407424728304 W.
- Full construction total: **46.98431583726587888 W**. Supply-average equivalent is 61.01859199644919335064935065 A at the allocated 0.77 V; it is not a peak-current or IR qualification.

At 1024 Q pairs this is **48111.93941736025997312 W**, exceeding U.COOLING_LIMIT_W = 474.56 W from tools/uarch_model.py. All enumerated 512/768/1024/1536/2048/3749-pair allocations fail that thermal budget before hub/descriptor, PG loss, repair cells and upstream package clock are added. Therefore this construction allocation cannot admit those points. An upper allocation exceeding the ceiling does not prove an optimized implementation's minimum power exceeds it; a tighter source-bound budget is necessary before a new point can be admitted.

Conditions remain explicit: use a characterized rail point, stay within the power table's slew/load domain, respect output maximum load and the declared wire guard, and bound each pin to at most one rise/fall pair per cycle. Glitches or reset transitions beyond that envelope require additional pricing. No continuous-voltage interpolation or internal-energy V^2 scaling is claimed. The model point does not establish SS/FF timing, extracted RC, physical phase, routed PG or IR. Physical admission is always false; root-stop credit is zero.

Replay, using the retained local selected source sections:

```sh
PYTHONPATH=. python3 tools/w10_q_power_envelope.py --construction results/uarch/w10_q_elaboration_inventory_r1/construction.json --inventory results/uarch/w10_q_elaboration_inventory_r1/inventory.json --libdir /home/ubuntu/w10-w18-recovery/baseline_wake/q_power_envelope_r1 --macrodir /home/ubuntu/w10-w18-recovery/baseline_wake/physical_src_r2/physical/asap7_memory_macros/ot_rom_4096x274_m8 --output /home/ubuntu/w10-w18-recovery/baseline_wake/q_power_envelope_r1/replay.json
cmp /home/ubuntu/w10-w18-recovery/baseline_wake/q_power_envelope_r1/replay.json results/uarch/w10_q_power_envelope_r1/power.json
PYTHONPATH=. python3 tests/test_w10_q_power_envelope.py
```

Ram is the whole-DSROM geometry/runtime/inventory authority under DSROM.whole-geometry-owner-parent-20261001.json. These numeric fields are supplied to his current U.PRODUCT_GEOM composition/search. They replace no historical measured power receipt and provide no free root-stop credit. No RTL, mapping or P&R job was launched.
