# HBM connectivity and geometry search, 2026-10-15

The exact ATT-hi placement candidate reduces summed actual data-pin Manhattan distance by **8.31%**, from 3,488,973.666 to 3,199,090.842 bit-µm. Ten of 54 children move; parent outline, children, orientation, external data-pin children and signal topology remain unchanged. The independent existing ATT auditor passes all **18,946** signal pin pairs, with **383.04 µm** maximum, zero overlap/outside/off-grid and an actual pin-shift mutant detected. The optimization objective covers 18,944 data pairs; the independent auditor additionally checks two internal clock signal pairs.

This is a component geometry candidate. Clock delivery, external die seams, routing congestion, actual timing and current static native source composition remain unqualified. It does not establish a full-die improvement or token performance improvement.

`attention_hi_plan.json` is compatible with `tools/hbm_attention_reach_repair.py` in the attention owner's worktree. It pins the exact starting direct manifest bytes and exact component source. `attention_hi_search.json` has the full before/after objective and top 20 connectivity groups, moves and limitations. `attention_hi_reproof.json` is the independent auditor receipt. `orientation_admission.json` confirms all 54 referenced LEF hashes match and none declares SYMMETRY; unsupported macro flips were not attempted. New per-child clock pin locations travel with the moved children and require die delivery updates.

The global source/geometry audit exposes the larger unresolved issue. Actual contract has 68 instances and 644 known edges, but only 47 instance names occur in the old geometry. Of these, only five master names match; the other 42 are historical VM/COLL/service slots for changed masters. Twenty-one source instances have no slot, and 140 known edges lack even historical endpoint boxes. All global pin-coordinate coverage is missing. `coverage.json` ranks the largest **historical rectangle-distance lower bounds** as diagnostic priorities; these are not actual pin wirelengths or native candidates.

Replacing all 32 old SM frames at their historical origins with the actual unqualified complete35 frame, **6609.6 × 1712.08 µm**, exposes **34 rectangle overlaps**. It retains all non-SM blocks and does not conceal the old 9.412 mm² assumption. This replacement is intentionally a packing-debt diagnostic, not a proposal for adoption.

Reproduction inputs are owned and preserved by the active streams:

- Source contract: `/home/ubuntu/wt/hbm-die-feas-1014/results/arch/hbm_die_v15/source_contract/contract.json`.
- Historical geometry: `/home/ubuntu/wt/hbm-die-feas-1014/results/arch/hbm_die_v14/sm32_repack_probe_1014.json`.
- Actual SM frame: `/home/ubuntu/wt/sm-dense-pack-1015/results/hbm_sm_dense_pack/complete35.json`.
- ATT direct manifest: `/tmp/attention_hi_repaired.direct.json`, also frozen remotely at `/srv/opentallas-scratch/codex/hbm-geometry-1015/attention_hi_repaired.direct.json` on the fleet.
- Independent ATT auditor: `/home/ubuntu/wt/hbm-static-attn-quant-1014/tools/hbm_attention_reach_repair.py`.

```sh
python3 tools/hbm_geometry_coverage.py --contract CONTRACT --legacy LEGACY --sm SM --out coverage.json
PYTHONPATH=tools python3 -m unittest tools/test_hbm_geometry_pin_search.py
# Run substantive pin search and reproof through ot-run with memory admission.
python3 tools/hbm_geometry_pin_search.py MANIFEST --out attention_hi_search.json
python3 tools/hbm_attention_reach_repair.py MANIFEST attention_hi_plan.json --out attention_hi_reproof.json
```

Actual admitted search: `ot-agidock128`, `oth-ubuntu-3706613-1792050630`, exit 0. Independent reproof: same host, `oth-ubuntu-3707902-1792050687`, exit 0. Both used 2 GB / 1 thread and preserve their frozen artifacts remotely. Five focused tests pass: external anchoring/global incident-wire objective, obstacle/clearance rejection, missing actual pin rejection, preserving the actual SM frame rather than shrinking it to a child bounding box, and anchoring an explicitly bound external pin even when its net also has internal fanout.

Next: the ATT owner decides whether to adopt the exact coordinate overrides in its current source-bound placement generator. The die lead supplies actual parent and SM client geometry so this stream can optimize global connectivity without reviving legacy master assumptions. No existing route was rerun or modified.

Follow-up search explicitly anchors all non-clock `boundary_binding` entries, including external pins on nets with internal fanout. Admitted AGI unit `oth-ubuntu-3708653-1792050865` exits 0 and reproduces the identical candidate. `attention_hi_before_after.svg` draws both exact geometries at the same scale; displayed lines are representative pin pairs, not routed wires.
