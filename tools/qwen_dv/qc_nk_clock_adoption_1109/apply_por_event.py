"""DIE-QC-97 11-09 (COORD-approved form): QC NK clock-pin plan event on the final QC second-switch plan.

base  plan_qc53v4nS_mem9_vml.json sha256 282ca18e... (intel1/epyc6 /srv/opentallas-scratch2/claude/qc-transport-fix-4/plan;
      not on main, its cores/ is byte-identical to plan_of_record/cores)
out   plan_of_record/plan_qc53v4nS_mem9_vml_nkck.json + cores/a0_nk_pins_ck1109.json + qc53v4nS_nk_ck_event.json
Applies results/physical/qc_nk_clock_adoption_1109/access_v1/proposed_event.patch.json (62 NK cores in 16 types:
pins_file -> ck M5 (228.972,578.880) table, clock_entry_access, tap <inst>.ck -> entry M7 track, signed NK pin-flop
means).  Every 'test' op must hold; every other partition type and top-level key is asserted byte-identical, and in
the 16 types only the patched paths may differ.  Usage: apply_por_event.py <repo root> <base plan>"""
import copy, hashlib, json, sys
from pathlib import Path

R = Path(sys.argv[1]); BASE = Path(sys.argv[2])
POR = R / "physical/die_plan/qwen_compute/plan_of_record"
ADO = R / "results/physical/qc_nk_clock_adoption_1109/access_v1"
NEW_PINS = "cores/a0_nk_pins_ck1109.json"
OUT = "plan_qc53v4nS_mem9_vml_nkck.json"
BASE_SHA = "282ca18ef6cc7923775d54c0a039613637e4d39bb9ae1d4e360d46243a8f1f77"
sha = lambda b: hashlib.sha256(b).hexdigest()

src = BASE.read_bytes()
assert sha(src) == BASE_SHA, sha(src)
P = json.loads(src)
assert json.dumps(P, indent=1).encode() + b"\n" == src, "base does not round-trip (indent=1)"
N = copy.deepcopy(P)
ops = json.loads((ADO / "proposed_event.patch.json").read_text())


def walk(doc, path):
    ks = [k.replace("~1", "/").replace("~0", "~") for k in path.lstrip("/").split("/")]
    for k in ks[:-1]:
        doc = doc[int(k)] if isinstance(doc, list) else doc[k]
    return doc, (int(ks[-1]) if isinstance(doc, list) else ks[-1])


touched = set()
for op in ops:
    d, k = walk(N, op["path"])
    if op["op"] == "test":
        assert d[k] == op["value"], (op["path"], d[k], op["value"])
    elif op["op"] == "add":
        assert k not in d, op["path"]
        d[k] = op["value"]; touched.add(op["path"])
    elif op["op"] == "replace":
        assert k in d, op["path"]
        d[k] = op["value"]; touched.add(op["path"])
    else:
        raise ValueError(op)


def diffs(a, b, p=""):
    if type(a) != type(b):
        return [p]
    if isinstance(a, dict):
        out = []
        for k in set(a) | set(b):
            out += [f"{p}/{k}"] if (k not in a or k not in b) else diffs(a[k], b[k], f"{p}/{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [p]
        return [q for i, (x, y) in enumerate(zip(a, b)) for q in diffs(x, y, f"{p}/{i}")]
    return [] if a == b else [p]


types = sorted({op["path"].split("/")[2] for op in ops})
assert len(types) == 16, types
for tk in P["partition_types"]:
    if tk not in types:
        assert P["partition_types"][tk] == N["partition_types"][tk], tk
assert {k: v for k, v in P.items() if k != "partition_types"} == {k: v for k, v in N.items() if k != "partition_types"}
assert list(P) == list(N) and list(P["partition_types"]) == list(N["partition_types"])
changed = set()
for tk in types:
    for q in diffs(P["partition_types"][tk], N["partition_types"][tk], f"/partition_types/{tk}"):
        changed.add(q if q in touched else next((t for t in touched if q.startswith(t + "/")), q))
assert changed <= touched, sorted(changed - touched)[:5]
# insertion values that equal the old ones would not show as changed; every touched path is a patch target
n_cores = sum(1 for t in N["partition_types"].values() for c in t.get("hard_cores", []) if c.get("module") == "qfd_tile_nk_a0c")
assert n_cores == 62 and all(c["pins_file"] == NEW_PINS and c.get("clock_entry_access")
                             for t in N["partition_types"].values() for c in t.get("hard_cores", [])
                             if c.get("module") == "qfd_tile_nk_a0c")
n_inst = sum(1 for p in N["partitions"] if p.get("type") in types) if isinstance(N["partitions"], list) else \
    sum(1 for p in N["partitions"].values() if p.get("type") in types)

old_pins = (POR / "cores/a0_nk_pins.json").read_bytes()
new_pins = (ADO / "a0_nk_pins.json").read_bytes()
a, b = json.loads(old_pins), json.loads(new_pins)
diff = [(x, y) for x, y in zip(a["pins"], b["pins"]) if x != y]
assert len(a["pins"]) == len(b["pins"]) == 2584 and {k: v for k, v in a.items() if k != "pins"} == {k: v for k, v in b.items() if k != "pins"}
assert diff == [({"name": "ck", "layer": "M4", "x": 457.824, "y": 668.076}, {"name": "ck", "layer": "M5", "x": 228.972, "y": 578.88})], diff
assert old_pins.split(b'"name": "ck"')[1].split(b"}", 1)[1] == new_pins.split(b'"name": "ck"')[1].split(b"}", 1)[1]

out = json.dumps(N, indent=1).encode() + b"\n"   # same serialization as the base
(POR / OUT).write_bytes(out)
(POR / NEW_PINS).write_bytes(new_pins)
ado = json.loads((ADO / "adoption.json").read_text())
taps = [dict(type=r["type"], tap=r["tap"], orient=r["orient"], old_xy=r["old_xy"], new_xy=r["new_xy"]) for r in ado["instances"]]
rec = dict(schema="opentallas.qc_por_event.v1", event="QC NK clock pin adoption (DIE-QC-97 11-09, COORD-approved form)",
           base_plan="plan_qc53v4nS_mem9_vml.json (final QC second-switch plan; intel1/epyc6 "
                     "/srv/opentallas-scratch2/claude/qc-transport-fix-4/plan, not on main)",
           base_plan_sha256=sha(src), plan_output=OUT, plan_output_sha256=sha(out),
           types=types, cores=n_cores, partition_instances=n_inst, module="qfd_tile_nk_a0c",
           pins_file_old="cores/a0_nk_pins.json", pins_file_old_sha256=sha(old_pins),
           pins_file_new=NEW_PINS, pins_file_new_sha256=sha(new_pins),
           pin_change=dict(pin="ck", old=["M4", 457.824, 668.076], new=["M5", 228.972, 578.88]), other_pins_unchanged=2583,
           access_lef="results/physical/qc_nk_clock_adoption_1109/access_v1/qfd_tile_nk_a0c.access.lef",
           access_lef_sha256=ado["access_lef_sha256"], original_lef_sha256=ado["original_lef_sha256"],
           obs_windows_child_um=ado["native_obs_windows_child_um"], entry_stack_child=ado["entry_stack_child"],
           tap_rule="xy = type-frame M7 utility-pin centre of the entry stack: x on the parent M7 track (child 229.024), "
                    "y = real pin centre (origin + track_offset + 578.880)",
           insertion=dict(old_ps=[665.8, 576.5], new_ps=[ado["insertion"]["tt"], ado["insertion"]["ff"]],
                          source=ado["insertion"]["source"]),
           taps=taps, data_cycles=0, pin_cycles=0, signed_view_changed=False,
           patch_source="results/physical/qc_nk_clock_adoption_1109/access_v1/proposed_event.patch.json",
           preservation="every other partition type and every top-level key byte-identical; in the 16 types only the "
                        "patched paths differ (checked)")
(POR / "qc53v4nS_nk_ck_event.json").write_text(json.dumps(rec, indent=1) + "\n")
print(json.dumps({k: v for k, v in rec.items() if k != "taps"}, indent=1))
