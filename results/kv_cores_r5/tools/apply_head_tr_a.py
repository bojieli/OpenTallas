#!/usr/bin/env python3
"""KV-CORES-R5: apply D-KV-HEAD-TR (A) (COORD 04:26 ADOPTED on independent NUMBER-CHECK) to a KV plan.
Every hard core on cores/kv3_head_eighth_e{5,6}_pins_fMX.json (orient MX) -> canonical view at R0, same origin.
Checks (fail-closed) on the pin views next to the plan:
  * every data pin of the fMX view is the MX image (x, H-y) of the canonical pin (rst_n pins excepted: they change face);
  * clock pins: the canonical view's clock pins must lie in the 12.8a centre entry island (orient-invariant about y=H/2);
    either the fMX clock pin is the MX image, or it is the pre-slice face pin superseded by that centre entry.
    usage: apply_head_tr_a.py PLAN.json OUT.json [--entry-island x0,y0,x1,y1]"""
import argparse, copy, hashlib, json
from pathlib import Path
ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("out")
ap.add_argument("--entry-island", default="103.68,103.68,112.32,112.32")
a = ap.parse_args()
isl = [float(v) for v in a.entry_island.split(",")]
pd = Path(a.plan).parent
d = json.load(open(a.plan)); rep = dict(plan=a.plan, plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),
                                        rows=[], views={})
H = 216.0
for v in ("kv3_head_eighth_e5", "kv3_head_eighth_e6"):
    c = {p["name"]: p for p in json.load(open(pd / f"cores/{v}_pins.json"))["pins"]}
    f = {p["name"]: p for p in json.load(open(pd / f"cores/{v}_pins_fMX.json"))["pins"]}
    assert set(c) == set(f), v
    img = lambda n: abs(f[n]["x"] - c[n]["x"]) < 1e-6 and abs(f[n]["y"] - (H - c[n]["y"])) < 1e-6 and f[n]["layer"] == c[n]["layer"]
    bad = [n for n in c if not img(n)]
    rst = [n for n in bad if "rst_n" in n]
    clk = [n for n in bad if n.split("[")[0].endswith("clk")]
    other = [n for n in bad if n not in rst and n not in clk]
    assert not other, (v, other[:5])
    inis = lambda p: isl[0] <= p["x"] <= isl[2] and isl[1] <= p["y"] <= isl[3]
    cclk = [n for n in c if n.split("[")[0].endswith("clk")]
    if clk:
        assert all(inis(c[n]) for n in cclk), (v, "canonical clock pins not all in the centre entry island")
    rep["views"][v] = dict(pins=len(c), mx_image=len(c) - len(bad), rst_n_face_change=rst,
                           clk_to_centre_entry=clk, canonical_clk_in_entry_island=all(inis(c[n]) for n in cclk))
n = 0
for tn, t in d["partition_types"].items():
    for i, hc in enumerate(t.get("hard_cores", [])):
        pf = hc.get("pins_file", "")
        if pf in ("cores/kv3_head_eighth_e5_pins_fMX.json", "cores/kv3_head_eighth_e6_pins_fMX.json"):
            assert hc["orient"] == "MX", (tn, i)
            hc["pins_file"] = pf.replace("_fMX", ""); hc["orient"] = "R0"
            hc["note"] = (hc.get("note", "") + " | D-KV-HEAD-TR(A) KV-CORES-R5 10-27: fMX view -> canonical at R0").strip(" |")
            rep["rows"].append(dict(type=tn, idx=i, inst=hc.get("inst"), module=hc.get("module")))
            n += 1
parts = {}
for p in d["partitions"]:
    parts[p["type"]] = parts.get(p["type"], 0) + 1
rep["rows_changed"] = n
rep["instances"] = sum(parts.get(r["type"], 0) for r in rep["rows"])
Path(a.out).write_text(json.dumps(d))
rep["out_sha256"] = hashlib.sha256(Path(a.out).read_bytes()).hexdigest()
Path(a.out).with_suffix(".head_tr_a.json").write_text(json.dumps(rep, indent=1) + "\n")
print(json.dumps({k: rep[k] for k in ("rows_changed", "instances", "out_sha256")}), json.dumps(rep["views"])[:900])
