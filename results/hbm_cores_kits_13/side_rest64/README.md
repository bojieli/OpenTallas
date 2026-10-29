# HBM side_rest64 completed retained-graph proof

The old LEC stopped at 26 differing compare points in the reciprocal-square-root multiplier pipeline. The gate folds facts intrinsic to squaring identical operands; the correspondence search did not discover those facts. No RTL, cycles, reset contract or timing constraints changed.

The inherited HBM-CORES-KITS-13 target5 proof completed: 8,146 joint hypotheses and all 25,511 compare points PROVED. The 32 new candidate facts are 28 constants (square sign, shift parity, rounded mantissa parity) and four gold-to-gold equalities. Every constant has a free-state, fresh-input initial base (at most four edges); all four equalities have a separate free-state initial base proven at five edges. `eqbase_run2.log` also records passes at six and eight edges. This proof uses the existing 64-edge reset contract; it adds no reset or assumption. Failed predecessor evidence remains on the fleet.

`inputs.tar.gz` contains the exact retained gold/gate AIGs, maps, gold frontend metadata and predecessor correspondence. `lec_engine.py` is the exact proof engine used. `kept4.json` contains untrusted discovered candidates; the replay re-proves them jointly. `rest_target5.log` and `eqbase_run2.log` are the completed inherited logs; `inputs.sha256` records their source paths and hashes. The replay scripts use repository-relative engine/candidate paths and fail closed on an unproved joint obligation, compare point or initial base.

Run `replay.sh NEW_OUTPUT_DIRECTORY` with the project Yosys/ABC toolchain through ot-run. It unpacks into the chosen new directory, checks the entire retained-graph proof and the equality initial bases. Do not overwrite failed output directories.

Scope: equivalence of the pinned side_rest gold and gate graph only. This does not qualify the obsolete fullcanon GPL-0307 physical shape, authorize its route, or claim SIGNED. The die owner must compose the current source/interface/geometry before a physical rebuild.
