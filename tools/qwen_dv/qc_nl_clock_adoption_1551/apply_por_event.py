"""DIE-QC-91 11-07 (COORD 17:07 (5)): QC NL clock-pin plan event, qc52 -> qc52n.

Applies the access_v4 JSON patch (two cbx_q10 types / 48 instances: NL IDLE_UCK=1, clock_entry_access, pin table with the
signed ck M5 (228.972,578.880), tap u_t30.ck -> (928.8,656.652) with the signed means TT 774.38 / FF 610.59) to the plan
of record.  The pin table is laid plan-relative (cores/a0_nl_pins_ck1107.json, byte-identical to access_v4/a0_nl_pins.json)
like every other QC pin table.  Only the 'test' ops' old values and the ck row may differ; everything else is checked
byte-identical after the round trip.  Usage: apply_por_event.py <repo root>"""
import copy, hashlib, json, sys
from pathlib import Path

R = Path(sys.argv[1])
POR = R / "physical/die_plan/qwen_compute/plan_of_record"
ADO = R / "results/physical/qc_nl_clock_adoption_1551/access_v4"
NEW_PINS = "cores/a0_nl_pins_ck1107.json"
sha = lambda b: hashlib.sha256(b).hexdigest()

src = (POR / "plan_qc52.json").read_bytes()
P = json.loads(src)
assert json.dumps(P, separators=(",", ":")).encode() + b"\n" == src, "qc52 does not round-trip"
N = copy.deepcopy(P)
ops = json.loads((ADO / "proposed_event.patch.json").read_text())


def walk(doc, path):
    ks = [k.replace("~1", "/").replace("~0", "~") for k in path.lstrip("/").split("/")]
    for k in ks[:-1]:
        doc = doc[int(k)] if isinstance(doc, list) else doc[k]
    return doc, (int(ks[-1]) if isinstance(doc, list) else ks[-1])


for op in ops:
    d, k = walk(N, op["path"])
    v = op.get("value")
    if op["path"].endswith("/pins_file") and op["op"] == "replace":
        v = NEW_PINS
    if op["op"] == "test":
        assert d[k] == v, (op["path"], d[k], v)
    elif op["op"] == "add":
        assert k not in d, op["path"]
        d[k] = v
    elif op["op"] == "replace":
        assert k in d, op["path"]
        d[k] = v
    else:
        raise ValueError(op)

old_pins = (POR / "cores/a0_nl_pins.json").read_bytes()
new_pins = (ADO / "a0_nl_pins.json").read_bytes()
a, b = json.loads(old_pins), json.loads(new_pins)
diff = [(x, y) for x, y in zip(a["pins"], b["pins"]) if x != y]
assert len(a["pins"]) == len(b["pins"]) == 1042 and {k: v for k, v in a.items() if k != "pins"} == {k: v for k, v in b.items() if k != "pins"}
assert diff == [({"name": "ck", "layer": "M4", "x": 457.824, "y": 668.076}, {"name": "ck", "layer": "M5", "x": 228.972, "y": 578.88})], diff

# nothing outside the two cbx_q10 types changed
for tk in P["partition_types"]:
    if tk not in ("cbx_q10__cl94a12200", "cbx_q10__cl89936551"):
        assert P["partition_types"][tk] == N["partition_types"][tk], tk
assert {k: v for k, v in P.items() if k != "partition_types"} == {k: v for k, v in N.items() if k != "partition_types"}
n_inst = sum(1 for p in N["partitions"] if p.get("type") in ("cbx_q10__cl94a12200", "cbx_q10__cl89936551"))

out = json.dumps(N, separators=(",", ":")).encode() + b"\n"
(POR / "plan_qc52n.json").write_bytes(out)
(POR / NEW_PINS).write_bytes(new_pins)
rec = dict(schema="opentallas.qc_por_event.v1", event="QC NL clock pin adoption (COORD 11-07 17:07 (5))",
           base_plan="plan_qc52.json", base_plan_sha256=sha(src), plan_output="plan_qc52n.json", plan_output_sha256=sha(out),
           types=["cbx_q10__cl94a12200", "cbx_q10__cl89936551"], instances=n_inst, module="qfd_tile_nl_a0c",
           pins_file_old="cores/a0_nl_pins.json", pins_file_old_sha256=sha(old_pins),
           pins_file_new=NEW_PINS, pins_file_new_sha256=sha(new_pins),
           pin_change=dict(pin="ck", old=["M4", 457.824, 668.076], new=["M5", 228.972, 578.88]), other_pins_unchanged=1041,
           tap=dict(name="u_t30.ck", old_xy=[699.936, 745.848], new_xy=[928.8, 656.652],
                    insertion_ps=[692.6, 774.38], insertion_ff_ps=[601.9, 610.59]),
           params=dict(IDLE_UCK=1), data_cycles=0, pin_cycles=0,
           eq_gate=dict(verdict="EQUIVALENT", scope="routed 6_final.v of the signed NL (ecow3 i1) vs kit RTL + IDLE_UCK=1, 64-edge reset",
                        record="epyc2:/srv/opentallas-scratch3/claude/dq90_nl/resign_idleuck/PROVENANCE.json", accepted="COORD 11-07 15:23"),
           patch_source="results/physical/qc_nl_clock_adoption_1551/access_v4/proposed_event.patch.json (pins_file re-pointed plan-relative)",
           preservation="every other partition type and every top-level key byte-identical (checked)")
(POR / "qc52n_nl_ck_event.json").write_text(json.dumps(rec, indent=1) + "\n")
print(json.dumps(rec, indent=1))
