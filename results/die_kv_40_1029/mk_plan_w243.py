# DIE-KV-40: event28w = event28b + q1/q2 widen-EAST 233.28 -> 243.648 (DIE-KV-39 ruling 20:21, COORD 10-29 conditions).
# Only change: hard_cores ectl_q1/ectl_q2 outline_um[0] 233.28 -> 243.648 in every hg type (origins fixed) and
# pins_file -> new pin tables with the E-face pins x + 10.368 (W/S/N + interior ck/rst/ft_ck pins unchanged).
# Fails closed on any other difference.  usage: mk_plan_w243.py SRC_PLAN OUT_DIR
import json, sys, copy, hashlib
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
OLD_W, NEW_W, DX = 233.28, 243.648, 10.368
assert abs(OLD_W + DX - NEW_W) < 1e-9 and abs(NEW_W / 0.432 - round(NEW_W / 0.432)) < 1e-9
raw = json.load(open(src)); old = copy.deepcopy(raw)
newpins = {}
rep = dict(types=[], pins={})
for mod in ("qkd_ectlk_q1", "qkd_ectlk_q2"):
    pf = None
    for tn, t in raw["partition_types"].items():
        for h in t.get("hard_cores", []) or []:
            if h["module"] != mod: continue
            assert h["outline_um"] == [OLD_W, 172.8] and h["orient"] == "R0", (tn, h)
            pf = pf or h["pins_file"]; assert h["pins_file"] == pf
    d = json.load(open(pf)); n = dict(E=0, W=0, S=0, N=0, interior=0)
    ex = OLD_W - 0.096
    for p in d["pins"]:
        if abs(p["x"] - ex) < 1e-6:
            p["x"] = round(p["x"] + DX, 3); n["E"] += 1
        elif abs(p["x"] - 0.096) < 1e-6: n["W"] += 1
        elif abs(p["y"] - 0.096) < 1e-6: n["S"] += 1
        elif abs(p["y"] - (172.8 - 0.096)) < 1e-6: n["N"] += 1
        else:
            assert 1 < p["x"] < OLD_W - 1 and 1 < p["y"] < 171, p; n["interior"] += 1
    assert n["E"] == d["faces"]["E"]["pins"], (n, d["faces"])
    d["frame"] = d["frame"].replace("233.28 x 172.8", "243.648 x 172.8")
    d["source"] += " | DIE-KV-40 W243: widen EAST 233.28 -> 243.648 (origin fixed), E face pins x +10.368, W/S/N/interior pins unchanged, 0 cycles"
    q = mod.split("_")[-1]
    np_ = out / f"qkd_ectlk_{q}_pins_243.json"; json.dump(d, open(np_, "w"), indent=1)
    newpins[mod] = str(np_.resolve()); rep["pins"][mod] = dict(src=pf, out=newpins[mod], counts=n,
        sha256=hashlib.sha256(np_.read_bytes()).hexdigest())
for tn, t in raw["partition_types"].items():
    for h in t.get("hard_cores", []) or []:
        if h["module"] in newpins:
            h["outline_um"] = [NEW_W, 172.8]; h["pins_file"] = newpins[h["module"]]
            h["note"] += " | DIE-KV-40 W243: widen EAST to 243.648 (origin fixed; KV-KITS-V q2 centre-max GRT ov 0 at 50 it)"
            x1 = h["origin_um"][0] + NEW_W
            # growth strip stays inside the type outline and clear of every other hard core
            assert x1 <= t["outline_um"][0]
            for g in t["hard_cores"]:
                if g is h: continue
                gx0, gy0 = g["origin_um"]; gw, gh = g["outline_um"]
                ov = min(x1, gx0 + gw) > max(h["origin_um"][0], gx0) and min(h["origin_um"][1] + 172.8, gy0 + gh) > max(h["origin_um"][1], gy0)
                assert not ov, (tn, h["inst"], g["inst"])
            rep["types"].append([tn, h["inst"], h["origin_um"], [NEW_W, 172.8]])
raw["note"] = raw.get("note", "") + " | DIE-KV-40 event28w: q1/q2 ECTL hard cores widened EAST 233.28 -> 243.648 (origins fixed, E-face pins +10.368, clock taps unchanged; COORD 10-29 + DIE-KV-39 20:21 ruling)"
# fail closed: nothing else changed
def strip(p):
    p = copy.deepcopy(p); p.pop("note", None)
    for t in p["partition_types"].values():
        for h in t.get("hard_cores", []) or []:
            if h["module"] in newpins:
                for k in ("outline_um", "pins_file", "note"): h.pop(k)
    return p
assert strip(raw) == strip(old)
pp = out / "plan.json"; json.dump(raw, open(pp, "w"), indent=1)
rep["plan_sha256"] = hashlib.sha256(pp.read_bytes()).hexdigest(); rep["src_sha256"] = hashlib.sha256(src.read_bytes()).hexdigest()
json.dump(rep, open(out / "plan_delta.json", "w"), indent=1)
print(json.dumps(dict(types=len(rep["types"]), pins={k: v["counts"] for k, v in rep["pins"].items()}, plan_sha256=rep["plan_sha256"])))
