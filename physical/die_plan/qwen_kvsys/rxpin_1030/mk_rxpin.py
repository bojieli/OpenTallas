#!/usr/bin/env python3
"""DIE-KV-49 one-block RX pin fix (COORD 10-30 20:48 ruling, RX ASK (a)).

Adds the two held qkd_hr_core_rx pin deltas to the KV plan of record (event28w_c):
  1. ownership_valid[0] <-> rx_d[263] swap on the W face (M4; exact coordinate swap);
  2. die_id[0] / die_id[2] move to the E-face centre next to die_id[1] (M4, y 128.76 / 130.488).
These are the positions the signed RX view (core_rx e2, intel1 die-kv-47-hr/rx/kit pins.json) was built with.
Writes pins/qkd_hr_core_rx_pins_r26q5d.json and repoints the one plan_c hard_cores entry; every other byte of
plan_c (other types, outline, origin, clocks, reset) is unchanged (asserted fail-closed).
Usage (repo root): python3 physical/die_plan/qwen_kvsys/rxpin_1030/mk_rxpin.py
"""
import json, os, copy

POR = "physical/die_plan/qwen_kvsys/plan_of_record"
OLD, NEW = "pins/qkd_hr_core_rx_pins_r26q5.json", "pins/qkd_hr_core_rx_pins_r26q5d.json"
# kit x on the edge (0 / 259.2) maps to the plan's track-centre x (0.096 / 259.104)
MOVES = {"die_id[0]": ("M4", 259.104, 128.76), "die_id[2]": ("M4", 259.104, 130.488)}
SWAP = ("ownership_valid[0]", "rx_d[263]")


def main():
    pins = json.load(open(os.path.join(POR, OLD)))
    P = {p["name"]: p for p in pins["pins"]}
    a, b = P[SWAP[0]], P[SWAP[1]]
    assert a["layer"] == b["layer"] == "M4" and a["x"] == b["x"] == 0.096
    (a["y"], b["y"]) = (b["y"], a["y"])
    for n, (l, x, y) in MOVES.items():
        p = P[n]
        assert p["layer"] == l and p["x"] == x
        assert not any(q["layer"] == l and abs(q["x"] - x) < 0.01 and abs(q["y"] - y) < 0.2 for q in pins["pins"]), n
        p["y"] = y
    pins["source"] += (" | DIE-KV-49 10-30 one-block RX pin fix (COORD 20:48): ownership_valid[0]<->rx_d[263] W swap;"
                       " die_id[0]/[2] to E centre (= signed core_rx e2 view)")
    json.dump(pins, open(os.path.join(POR, NEW), "w"), indent=1)
    old = json.load(open(os.path.join(POR, OLD)))
    diff = [p["name"] for p, q in zip(old["pins"], pins["pins"]) if p != q]
    assert sorted(diff) == sorted(list(MOVES) + list(SWAP)), diff

    path = os.path.join(POR, "plan_c.json")
    raw = open(path).read()
    plan = json.loads(raw)
    ref = copy.deepcopy(plan)
    hits = 0
    for t in plan["partition_types"].values():
        for h in t.get("hard_cores", []) or []:
            if h.get("module") == "qkd_hr_core_rx" and h.get("pins_file") == OLD:
                h["pins_file"] = NEW
                hits += 1
    assert hits == 1, hits
    # fail-closed: only that one string differs
    assert raw.count(json.dumps(OLD)) == 1
    out = raw.replace(json.dumps(OLD), json.dumps(NEW))
    assert json.loads(out) == plan and plan != ref
    open(path, "w").write(out)
    print("RX pin delta applied:", sorted(diff), "plan_c pins_file ->", NEW)


if __name__ == "__main__":
    main()
