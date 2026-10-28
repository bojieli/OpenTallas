"""HBM-STREETS-2 C18 street event on C17g: (a) dense-array column streets (spread x to >= 17.28 um gaps: q_su00/01/11
lane_exp + lanes_plain, root tkm), (b) q_su31 row gap 43.2, (c) SM die-edge streets (NW/NE_sm0/2 17.28 um off the
die edge), NW_sm3 69.12 um W, (d) native LEF/Liberty (repo-relative) on every hard core whose closed view exists.
Moved cores carry their type clock taps (same delta).  Not done here: spb0 PHY re-site, su31 FT-cross street, hub
vms_glue re-outline (see lanes/PATH-HBM.md HBM-STREETS-2)."""
import json, sys, hashlib
from pathlib import Path
REPO = Path(sys.argv[1]); src = Path(sys.argv[2]); out = Path(sys.argv[3])
sys.path.insert(0, str(REPO / "tools/die_plan")); sys.path.insert(0, str(Path(__file__).resolve().parent))
import cores as C
from spread import spread_type
raw = json.load(open(src))
SPREAD = [("q_su00", 17.28, (0,)), ("q_su01", 17.28, (0,)), ("q_su11", 17.28, (0,)), ("root", 17.28, (0,)), ("q_su31", 43.2, (1,))]
SHIFT = {"NW_sm0": [17.28, 0], "NW_sm2": [17.28, 0], "NE_sm0": [-17.28, 0], "NE_sm2": [-17.28, 0], "NW_sm3": [-69.12, 0]}
rep = dict(source=str(src), source_sha=hashlib.sha256(src.read_bytes()).hexdigest()[:12], moved={}, shifted=SHIFT, taps_moved=0)
for tn, T, axes in SPREAD:
    t = raw["partition_types"][tn]
    before = {c["inst"]: list(c["origin_um"]) for c in t["hard_cores"]}
    m, over = spread_type(t, T=T, axes=axes)
    assert not over, (tn, over)
    rep["moved"][tn] = m
    for tp in (t.get("clock", {}) or {}).get("taps", []) or []:
        inst = str(tp.get("name", "")).split(".")[0]
        if inst in m and tp.get("xy"):
            tp["xy"] = [round(tp["xy"][0] + m[inst][0], 4), round(tp["xy"][1] + m[inst][1], 4)]
            rep["taps_moved"] += 1
for p in raw["partitions"]:
    if p["name"] in SHIFT:
        d = SHIFT[p["name"]]
        p["origin_um"] = [round(p["origin_um"][0] + d[0], 4), round(p["origin_um"][1] + d[1], 4)]
filled, miss = [], set()
for tn, t in raw["partition_types"].items():
    for c in t.get("hard_cores", []) or []:
        if c.get("lef") and c.get("lib"):
            continue
        lef, tt, ff = C.find_views(REPO / "physical/ref_tile", c.get("module", c["inst"]))
        if lef and tt:
            c["lef"] = str(Path(lef).relative_to(REPO.resolve())); c["lib"] = str(Path(tt).relative_to(REPO.resolve()))
            if ff:
                c["lib_ff"] = str(Path(ff).relative_to(REPO.resolve()))
            filled.append((tn, c["inst"]))
        else:
            miss.add(c.get("module", c["inst"]))
rep["views_filled"] = len(filled); rep["views_missing_modules"] = sorted(miss)
raw["die"]["streets"] = dict(mode="demand", enforce=True, note="HBM-STREETS-2 C18: per-street demand (clock+hold base 17.28 um + FT bits x 0.048/(2 x 0.6)), 12.10c ERROR on hbm")
raw["die"]["label"] = "C18 = C17g + HBM-STREETS-2 street event (partial: see die.streets) | " + raw["die"].get("label", "")
out.mkdir(parents=True, exist_ok=True)
(out / "die_plan.json").write_text(json.dumps(raw, indent=1))
(out / "street_event_report.json").write_text(json.dumps(rep, indent=1))
print("views filled", len(filled), "missing modules", len(miss), "taps moved", rep["taps_moved"], "moved", {k: len(v) for k, v in rep["moved"].items()})
