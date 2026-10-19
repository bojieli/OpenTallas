# Dual-clock SRAM access: conditional analytical model, no replacement views

All ten existing `1r1w2c` directory variants in the ASAP7 v1/v2 memory families have minimum local W/E contact pitch **0.096um (10.4167 contacts/um)**. None supplies a presently legal <=6/um local distribution. Larger outlines do not cure the crowded interval. `inventory.json` pins every existing file, outline, contact count and source-presence result. V1 has six variants; v2 has four. V2 `64x546` lacks behavioral V, so its BB cannot establish storage semantics. No GDS/OAS/CDL/SP is present in these directory inventories. This does not prohibit an analytical model conditional on modeled macro internals.

This packet models distinct `ot_sram_1r1w2c_32x64_m1_p192_access_MODEL`. It emits **no LEF, V, Liberty, GDS or hardware**. Exact original LEF/V/BB/TT/FF/SS/JSON hashes are in the inventory and input. Source semantics remain those audited in `a6343c77a`: write data, address, CE and per-bit mask sample at rising `wclk`; enabled read samples at rising `rclk`, registered readout holds while disabled. Same-address simultaneous cross-clock read/write is forbidden, with no OLD ordering promise. The macro has no reset. Eight external valid bits per lane and actual first-use/collision/calendar ownership remain separate requirements.

The constructive geometry adapts the source-backed S81 access planner from `19ccd29b9` to these **206 actual dual-clock abstract anchors**, rather than borrowing its different single-clock macro. `reference_planner.py` and `reference_input.json` are pinned historical planner/calibration inputs. Their historical nominal-core-CQ minimum fields are **unqualified**, discarded by this model, and must never be used for STA. `model.json` publishes passive access costs only. This packet creates no minimum-CQ assertion at any corner and no aggregate timing qualification.

| Constructed access geometry | Model result |
|---|---:|
| Native paths, connectivity checked | 206 / 206 |
| Explicit VIA45 instances / contained enclosures | 408 / 408 |
| M4 signal width / external contact pitch | 24nm / 192nm |
| Minimum M4 / M5 / cut cross-net axis gaps | 50 / 72 / 72nm |
| Old PG rectangles preserved | 44 |
| Original outline | 31.992 × 17.304um |
| New outline / each side channel | 52.440 × 21.144um / 10.224um |
| Scalar modeled geometry errors | 0 |

Each old anchor translates with the original core by +10.224um in x. Each net has a separate monotone M5 column on the real 48nm routing grid, two M4 leads and explicit native VIA45 cuts/enclosures; the two zero-jog first contacts instead have one continuous M4 lead and no coincident vias. Paths preserve original net identity. They do not jump electrically to new pins. Source and terminal rectangles, metal, vias, RC, and per-path capacitance are all in `model.json`. Original M1–M4 OBS and interior M4 PG rails translate intact. Proposed channel M5 OBS reserves internal leads from parent use; core M5 remains accessible for parent PG. Final terminal-approach protection and parent PG topology still need the complete source-backed OBS/role checker (`ec861194a`), native rule-deck qualification and actual grid access. The scalar checks here cover the cited widths, PRL/scalar spacing, PG clearance, minimum metal area, enclosure containment, connectivity and outline. They do not certify full LEF58 EOL/density/orientation/parent escape.

RC uses the source-pinned ORFS ASAP7 parameters carried by the reference model: M4 R/C=0.0180365 kohm/um and 0.178475fF/um; M5=0.0189935 and 0.164264; VIA45 R=0.0118kohm, native cut/enclosure and34nm cut spacing. Technology/rule/calibration hashes and the native image identity are retained in `input.json`. Lead delay uses `Rtotal*(Ctotal+Cload)+max(Rinv4,Rout)*Ctotal`, an upper envelope only for this explicit passive RC/driver model. There is no separately characterized via-cut fringe capacitance in the inherited platform model. Macro internals, external transition/load-domain dependencies and coupling/extraction remain conditional; no silicon-bound claim follows.

| Per macro, conditional costs | FF | TT | SS sensitivity |
|---|---:|---:|---:|
| Maximum clock lead delay, ps | 3.774 | 4.073 | 4.871 |
| Maximum input lead delay, ps | 3.830 | 4.765 | 6.489 |
| Maximum output lead at46.08fF, ps | 18.536 | 19.361 | 20.855 |
| `wclk` / `rclk` total input cap, fF | 12.202 /12.234 | 11.175 /11.206 | 10.513 /10.544 |
| Simultaneous R+W plus access energy, fJ | 531.989 | 440.472 | 357.586 |

Energy charges every nonclock lead one complete0→1→0 cycle at corner voltage and both clock-access leads once; original core read+write energy is added once. This is a deliberately full-activity access model, not measured workload energy. Full boundary clock-driver energy includes original clock input capacitance separately, avoiding double counting original clock loads as new access. No extra pipeline edge is proposed. Timing could still require source/calendar changes once actual propagation/hold roles are bound.

The selected hybrid remains **six independent small direct-FF rings and three wide SRAM lanes**, respectively9+9+8=26 banks,52 independent macro clock contacts. No tiny lane is folded into a large array. `contacts.csv` retains all5356 candidate signal/clock contacts with actual-instance/escape/PG ownership empty; `hybrid.json` includes26 explicit43.2um-lattice origins, unbound to production names.

| Hybrid price | Result |
|---|---:|
| Old26 macro area | 14,393.329um² |
| Proposed26 macro area | 28,828.575um² (+100.29%) |
| Reserved3-column ×9-row lattice envelope | 259.2 ×388.8um;100,776.96um² |
| Candidate signal access vias | 10,608 |
| Candidate contacts | 5,356 signal/clock +52 PG |
| Declared soft FF inventory from hybrid | 4,672, not measured synthesis |
| All52 clock input capacitance TT | 581.910fF, original485.982fF |
| All26-bank R+W energy TT, full activity | 11.452pJ |
| All52 boundary clock-driver cycle energy TT | 0.285pJ |

Origins advance86.4um in x and43.2um in y: wider macro fits two x-lattice pitches; height leaves22.056um between rows. The reserved envelope aspect is1.5, with one unused slot. These are **macro placement reservations**, not measured routed escapes or a parent outline. The full-width soft-cell band, measured cell area/utilization, clock/reset/tie copies, real PG/vias, safe fanout,405um reach and parent side channels remain unpriced/unqualified. Source K/phase/reset epoch/lifetime/first use and R-versus-R+1 contract remain NULL under the separate source-ledger owner. No token latency/rate or SU/MU correctness claim is made.

Next ROOT choices: accept this access-area/clock/energy price as the geometry candidate or require a different architectural storage model; then assign complete native terminal/PG/OBS model review and source-clock/calendar binding before any generation. This packet requests no user permission and starts no RTL, macro generation, prototype, physical gate or heavy job.

Reproduce the bounded inventory/geometry arithmetic with `python3 results/arch/qwen_dualclk_geometry_1019/model.py`. An initial inventory run incorrectly assumed every BB family also had behavioral V and raised FileNotFoundError on v2 `64x546`; `initial_failure.txt` retains that failure. The corrected inventory records the missing V explicitly. All numerical outputs in this packet come from the corrected run.
