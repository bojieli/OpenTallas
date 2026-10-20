# HBM r10 collection and opt-in functional-port transport repair

Base a6572c814, implementation 656474555. Own sparse WT; original Claude source/outputs untouched.
The r10 A/B chains both terminated at S5 with class-source drift, 79 excessive route hops and four/three mixed transport problems. Neither reached S7 (no owed S7 PNG exists) or GRT.

`--port-age-land` takes transitive closure of rows sharing a producer-port -> consumer-port path: all bits use landed transport if any row does. After actual fork cascades, sink-root registered pads align the functional word's ages. Existing defaults are unchanged. Every added pad is represented by a real relay instance, clock/reset and splice-chain entry; compiler/landing reports record its cycle cost.

Fleet evidence:
- 34020-1792525708: actual r10A 2312-bus layer generated, four mixed problems -> zero.
- 34981-1792525770: independent bit/consumer oracle checks 8530 groups: original seven unequal, new zero; physically deleting an inserted stage is caught. Missing E stays None. 60 generated exact-tail classes and immediate `--check` pass using a new unique RTL path; old generated class source untouched.
- 36707-1792525865: complete default layer (63040 instances) and report compare exactly as JSON against preserved r10A.
- 36438-1792525851: real Verilator 5.050 minimal production-dimension changed/promoted plus fork paths (two buses, three landings): positive 385 checks, zero mismatches/faults. lane_stage/bitswap/branch_drop/land_k causal negatives all fail. This tests the transport/pad mechanism under ideal clocks; it does not qualify the die's unknown phase offsets.
- 36259-1792525834 was a subset-selection setup failure (empty changed-fork set); preserved separately. First nohup client never started; recorded replacement handles ran.

Remote full layer/report and source snapshot: ot-epyc6 `/srv/opentallas-scratch/claude/codex-hbm-die11-1020`.
The source snapshot inherits the frozen r10 source tree and replaces only the committed relay generator; the new class source is generated into its own filename. Raw logs and selected RTL evidence are here. Full original failure logs remain in r10 A/B.

## Blocking qualification

1013 landing links still have E=None (1009 before four newly landed rows); reported latency remains None. E=1 is used only for diagnostic ideal-clock age alignment, never a physical qualification claim. The full die still has 79 >405um obstacle-route hops. No gate, route, binding adoption or main merge is authorized by this packet. Full schedule composition, strict binding, physical reach, actual phase-derived E/K and downstream GRT/STA remain owed. Source repair is default off.

Source/model follow-up: several SFU rows combine N/S/E/W output ports into one centroid **inside the macro**, causing first snap hop520um. Split those physical port groups before routing; preserve exact bit maps and re-run port-age alignment. Do not extend the reach threshold.
