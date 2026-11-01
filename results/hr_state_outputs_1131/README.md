Opt-in state-output recut preparation. No production recipe is enabled.

Use the actual flattened Yosys JSON and explicit output bits. The tool rejects
primary input, opaque, memory, mixed clock/reset and initialized-state cones.
Combinational x/z constants are preserved; state resets and the final folded
reset must be known. It does not interpret x/z as zero.

```sh
python3 physical/die_plan/qwen_kvsys/cores/harden/hr_state_outputs.py stage pre.json cone.json manifest.json --top MODULE --output fault[0]
yosys -p 'read_json cone.json; opt_expr; opt_clean; write_json folded.json'
python3 physical/die_plan/qwen_kvsys/cores/harden/hr_state_outputs.py finish folded.json candidate.json manifest.json
python3 physical/die_plan/qwen_kvsys/cores/harden/hr_state_outputs.py finish folded.json mutant.json manifest.json --mutant
```

Retain normal native and emitted equivalence, negative control, mapped/ODB face
and physical gates for each candidate. The native peer76 cut uses its existing
arbitrary-D proof vehicle from16d3289c4; this qualifies the recut of those actual
cones and is not a whole-peer protocol proof. RX full proof remains running.

The tiny.sh and peer76.sh files preserve the actual run commands. They ran under
intel1 codex-kv-residuals-1101/hr_state_recut1131, with the tool in that directory
and the parent's native peer input files in peer76/. Proof logs are retained.
