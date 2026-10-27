#!/usr/bin/env python3
"""KV-CORES-R3 (2026-10-27): head_eighth type-reduction plan deltas on the CLOCK-KV-R21 plan (hm_r21.json).

  A  fMX -> orientation: every hard core whose pins_file is <view>_fMX.json AND whose module has NO in-core die
     island (R15/R21 census with_islands 0) is re-placed with the canonical view <view>.json at the flipped instance
     orientation (MX <-> R0, same origin: outline 216 x 216, MX about the core centre line).  check: the fMX view is
     the MX image of the canonical view except the reset pins core_pins_orient kept (named in the report), so every
     data and clock pin lands on the same die xy; only the kept reset pins change face.
  B  (what-if, --e2-on-e6) e2 slots on the e6 canonical pin slots: an e2-named view with every pin at the e6 slot of
     the positionally equal port (g_t_4/5,g_front_1 <-> g_t_12/13,g_front_3); module/bind unchanged (geometry gate only).

    head_type_delta.py PD_DIR --plan hm_r21.json --out OUT_PD [--modules kv3_head_eighth_e5,kv3_head_eighth_e6] [--e2-on-e6 R0|MX]
Writes OUT_PD (copy of PD_DIR with the delta applied) + OUT_PD/head_type_delta.json (per changed instance, pin checks)."""
import argparse, copy, hashlib, json, shutil
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_views as PV  # noqa: E402  KV-CORES-R6: real view copies + views.sha256, no write through shared symlinks

FLIP = {"MX": "R0", "R0": "MX"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def mx_check(canon, fmx, h):
    a = {p["name"]: p for p in canon["pins"]}
    b = {p["name"]: p for p in fmx["pins"]}
    assert set(a) == set(b), "pin sets differ"
    kept, bad = [], []
    for n, p in a.items():
        q = b[n]
        if p["layer"] != q["layer"] or abs(p["x"] - q["x"]) > 1e-3:
            bad.append(n)
        elif abs((h - p["y"]) - q["y"]) <= 1e-3:
            continue
        elif abs(p["y"] - q["y"]) <= 1e-3:
            kept.append(n)
        else:
            bad.append(n)
    return kept, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pd")
    ap.add_argument("--plan", default="hm_r21.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--modules", default="kv3_head_eighth_e5,kv3_head_eighth_e6")
    ap.add_argument("--e2-on-e6", choices=["R0", "MX"])
    a = ap.parse_args()
    pd, out = Path(a.pd), Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    PV.snapshot(pd, out, ignore=shutil.ignore_patterns("*.png"))
    P = json.loads((pd / a.plan).read_text())
    mods = set(a.modules.split(",")) if a.modules else set()
    nparts = Counter(p["type"] for p in P["partitions"])
    rep = dict(schema="opentallas.kv_cores_r3.head_type_delta.v1", plan=str(pd / a.plan), plan_sha256=sha(pd / a.plan),
               modules=sorted(mods), checks={}, changed=[], e2_on_e6=a.e2_on_e6)
    for tn, t in P["partition_types"].items():
        for hc in t.get("hard_cores", []):
            pf = hc["pins_file"]
            if hc["module"] in mods and pf.endswith("_fMX.json"):
                canon = pf.replace("_fMX.json", ".json")
                if pf not in rep["checks"]:
                    kept, bad = mx_check(json.loads((pd / canon).read_text()), json.loads((pd / pf).read_text()), hc["outline_um"][1])
                    if bad:
                        raise SystemExit(f"{pf}: {len(bad)} pins are neither MX image nor kept: {bad[:5]}")
                    rep["checks"][pf] = dict(canonical=canon, mx_image_pins=None, kept_reset_pins=kept)
                o = hc.get("orient", "R0")
                if o not in FLIP:
                    raise SystemExit(f"{tn}/{hc['inst']}: orient {o}")
                rep["changed"].append(dict(type=tn, inst=hc["inst"], module=hc["module"], n=nparts[tn],
                                           orient=[o, FLIP[o]], pins_file=[pf, canon]))
                hc["orient"], hc["pins_file"] = FLIP[o], canon
                hc["note"] = hc.get("note", "") + f" | KV-CORES-R3 type delta A: {pf.split('/')[-1]} -> canonical view at orient {FLIP[o]} (same data/clock pin die xy)"
            if a.e2_on_e6 and hc["module"] == "kv3_head_eighth_e2":
                hc["pins_file"] = "cores/kv3_head_eighth_e2_pins_on_e6.json"
                rep["changed"].append(dict(type=tn, inst=hc["inst"], module=hc["module"], n=nparts[tn],
                                           orient=[hc.get("orient", "R0"), a.e2_on_e6], pins_file=[pf, hc["pins_file"]]))
                hc["orient"] = a.e2_on_e6
    for k, v in rep["checks"].items():
        v["mx_image_pins"] = len(json.loads((pd / k).read_text())["pins"]) - len(v["kept_reset_pins"])
    if a.e2_on_e6:
        e6 = json.loads((pd / "cores/kv3_head_eighth_e6_pins.json").read_text())
        e2 = json.loads((pd / "cores/kv3_head_eighth_e2_pins.json").read_text())
        ren = lambda n: n.replace("g_t_12_", "g_t_4_").replace("g_t_13_", "g_t_5_").replace("g_front_3_", "g_front_1_")
        pos = {ren(p["name"]): p for p in e6["pins"]}
        J = copy.deepcopy(e2)
        assert set(pos) == {p["name"] for p in J["pins"]}
        for p in J["pins"]:
            q = pos[p["name"]]
            p["layer"], p["x"], p["y"] = q["layer"], q["x"], q["y"]
        J["faces"] = e6["faces"]
        J["source"] += " | KV-CORES-R3 what-if: every pin on the e6 canonical slot of its positional port"
        PV.safe_write(out, "cores/kv3_head_eighth_e2_pins_on_e6.json", json.dumps(J, indent=1) + "\n")
    PV.safe_write(out, a.plan, json.dumps(P) + "\n")
    rep["out_plan_sha256"] = sha(out / a.plan)
    rep["instances_changed"] = sum(c["n"] for c in rep["changed"])
    PV.safe_write(out, "head_type_delta.json", json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k != "changed"}, indent=1))
    print("changed rows", len(rep["changed"]), "instances", rep["instances_changed"])


if __name__ == "__main__":
    main()
