HBM idx quarter r0c0_k0h1: four LEC differences were wrong scalar-to-flat-array Q aliases.

Original immutable kit lec/lec.json remains NOT EQUIVALENT33867/33871.
New source687ef703ff uses exact function pairing for scalar-to-indexed aliases; all33871 compare/induction obligations pass on the same gold/gate AIGs and maps. Original10065 hypotheses are re-proved, not trusted; three new cross-side cf relations are also proved. Original KEEP1215/1215 is unchanged; this target receipt does not claim a fresh frontend/physical run or recover the original unknown source commit.

Reproduce: copy original gold.aig,gate.aig,gold.map,gate.map,hyp.json to YOUR empty output dir, check target.json SHA256 entries, and invoke python3 results/lec_idx_alias_1026/replay.py YOUR_DIR through ot-run24GB2t with yosys-abc on PATH. It writes new idx_alias_target.aig/solver log/target.json, never edits the original kit.

Tiny4-register positive and wrong-data mutant plus43focused Python tests pass (one optional skipped). No RTL,data-cycle or pin changes.
