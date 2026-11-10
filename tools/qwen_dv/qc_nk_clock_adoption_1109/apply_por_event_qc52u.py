"""DIE-QC-97 11-09 (COUNT-ARCHIVE-2 18:13 (2)): the NK clock-pin plan event on the QC plan of record, qc52t -> qc52u.

The signed NK (re-sign f73e270e6f50, flow-20261109-fc-qc) has ck on M5 at (228.972, 578.880); plan_qc52t still has the
M4 east-edge pin, so DESIGN-MATCH fails on 1/2584 pins.  This applies the SAME access_v1 patch as plan_qc53v4nS_mem9_vml_nkck
(d5743d9ea53: 62 NK cores in 16 types, pins_file -> cores/a0_nk_pins_ck1109.json, clock_entry_access, tap <inst>.ck ->
entry M7 track, signed NK pin-flop means TT 733.25 / FF 586.0) to plan_qc52t.  Every 'test' op must hold on qc52t; every
other partition type and top-level key is asserted byte-identical, and in the 16 types only the patched paths may differ.
Usage: apply_por_event_qc52u.py <repo root>"""
import copy, hashlib, json, sys
from pathlib import Path

R = Path(sys.argv[1])
POR = R / "physical/die_plan/qwen_compute/plan_of_record"
ADO = R / "results/physical/qc_nk_clock_adoption_1109/access_v1"
NEW_PINS = "cores/a0_nk_pins_ck1109.json"
BASE, OUT, REC = "plan_qc52t.json", "plan_qc52u.json", "qc52u_nk_ck_event.json"
sha = lambda b: hashlib.sha256(b).hexdigest()

src = (POR / BASE).read_bytes()
P = json.loads(src)
assert json.dumps(P, separators=(",", ":")).encode() + b"\n" == src, "qc52t does not round-trip (compact)"
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
nk_types = sorted({tn for tn, t in P["partition_types"].items() for c in t.get("hard_cores", []) or []
                   if c.get("module") == "qfd_tile_nk_a0c"})
assert types == nk_types and len(types) == 16, (types, nk_types)
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
nk = [c for t in N["partition_types"].values() for c in t.get("hard_cores", []) or [] if c.get("module") == "qfd_tile_nk_a0c"]
assert len(nk) == 62 and all(c["pins_file"] == NEW_PINS and c.get("clock_entry_access") for c in nk)
parts = N["partitions"]
n_inst = sum(1 for p in (parts if isinstance(parts, list) else parts.values()) if p.get("type") in types)

old_pins = (POR / "cores/a0_nk_pins.json").read_bytes()
new_pins = (POR / NEW_PINS).read_bytes()          # already on main (d5743d9ea53)
assert new_pins == (ADO / "a0_nk_pins.json").read_bytes(), "cores/a0_nk_pins_ck1109.json != access_v1 table"
a, b = json.loads(old_pins), json.loads(new_pins)
diff = [(x, y) for x, y in zip(a["pins"], b["pins"]) if x != y]
assert len(a["pins"]) == len(b["pins"]) == 2584
assert diff == [({"name": "ck", "layer": "M4", "x": 457.824, "y": 668.076}, {"name": "ck", "layer": "M5", "x": 228.972, "y": 578.88})], diff

out = json.dumps(N, separators=(",", ":")).encode() + b"\n"     # same serialization as qc52t
(POR / OUT).write_bytes(out)
ado = json.loads((ADO / "adoption.json").read_text())
rec = dict(schema="opentallas.qc_por_event.v1",
           event="QC NK clock pin adoption on the plan of record (DIE-QC-97 11-09, COUNT-ARCHIVE-2 18:13 (2))",
           base_plan=BASE, base_plan_sha256=sha(src), plan_output=OUT, plan_output_sha256=sha(out),
           types=types, cores=len(nk), partition_instances=n_inst, module="qfd_tile_nk_a0c",
           pins_file_old="cores/a0_nk_pins.json", pins_file_old_sha256=sha(old_pins),
           pins_file_new=NEW_PINS, pins_file_new_sha256=sha(new_pins),
           pin_change=dict(pin="ck", old=["M4", 457.824, 668.076], new=["M5", 228.972, 578.88]), other_pins_unchanged=2583,
           signed_record=dict(name="kq_qfd_tile_nk_a0c_vR7", resign="intel1:/srv/opentallas-scratch2/claude/dq97/nk_eco2_resign_fc",
                              flow_tag="flow-20261109-fc-qc", routed_db_sha256="bfa23d1f3970648140f3965ea90a5e66bf21a652a1baa7d6842e063ca845d145",
                              ck_def="M5 ( -24 -240 ) ( 24 240 ) FIXED ( 228972 578880 ) N, UNITS 1000"),
           access_lef="results/physical/qc_nk_clock_adoption_1109/access_v1/qfd_tile_nk_a0c.access.lef",
           access_lef_sha256=ado["access_lef_sha256"], entry_stack_child=ado["entry_stack_child"],
           insertion=dict(old_ps=[665.8, 576.5], new_ps=[ado["insertion"]["tt"], ado["insertion"]["ff"]],
                          source=ado["insertion"]["source"]),
           data_cycles=0, pin_cycles=0, signed_view_changed=False,
           same_patch_as="plan_qc53v4nS_mem9_vml_nkck.json (d5743d9ea53, qc53v4nS_nk_ck_event.json)",
           patch_source="results/physical/qc_nk_clock_adoption_1109/access_v1/proposed_event.patch.json (all 310 test ops hold on qc52t)",
           preservation="every other partition type and every top-level key byte-identical; in the 16 types only the "
                        "patched paths differ (checked)")
(POR / REC).write_text(json.dumps(rec, indent=1) + "\n")
print(json.dumps({k: v for k, v in rec.items() if k not in ("entry_stack_child",)}, indent=1))
