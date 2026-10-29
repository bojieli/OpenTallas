"""DIE-HBM-10 C25a = C24 + clock-class pins of the 8 multi-clock cores on M5 at 0.048 x 0.48 (COORD 19:30 ruling on the
HBM-CORES-KITS-1 ASK (b): KIT_PREFLIGHT clock_pin_geometry (tools/die_plan/kit_contract.py, GEOM-21) needs every
clock port on M5, >= 0.048 x 0.48, centre on the M5 track).
usage: apply_c25a.py C24_DIR OUT_DIR
Clock class = gen_core_kit_hbm.CLK_RE on the pin base name (the ports the kit SDC create_clock's, which is what
clock_pin_geometry judges).  Per clock pin:
  * N/S-face pins stay on their face; E/W-face pins move to the nearer N/S face (M5 is vertical: an M5 pin leaves the
    core only through N/S) at the same corner (x 1.008 from the W / E edge, then the nearest free track).
  * layer M5, centre on the plan M5 track (0.024 + k 0.048), plan face y (S 0.096 / N H - 0.096) as every plan pin.
  * explicit size in the record: w 0.048 (across the face) x h 0.48 (into the core); keys w/h are plan pin keys the
    shared canonical pin hash already reads (die_sta_related.PIN_KEYS).  gen_core_kit_hbm.io_tcl honours them
    (opt-in: no C24 pin carries w/h, so every other kit is byte-identical).
  * spacing: centre >= 0.096 um (2 M5 tracks) from every other M5 pin on that face, so the 0.048 shape keeps >= 0.048
    to a 0.024 neighbour and to another clock pin.  Nearest such track to the wanted x.
Not changed: every other pin, every outline, every check, every section 12 rule; C24 plan content otherwise."""
import json, sys, shutil, os, hashlib, re
from pathlib import Path
SRC, OUT = map(Path, sys.argv[1:3])
CLK_RE = r"^(clk|clk_[a-z0-9_]+|[a-z0-9_]*_clk|ck|ck_[a-z0-9_]+|[a-z0-9_]*clk_[a-z0-9_]*)$"   # gen_core_kit_hbm.CLK_RE
TRK0, TRK, EDGE_Y, CW, CH, MIN_D, CORNER = 0.024, 0.048, 0.096, 0.048, 0.48, 0.096, 1.008
KEYS = ["calendar_f20", "wr_q_t_lanes4", "xload_cl2_ctlx", "selector_static_sel", "topk_link", "wb_kport_q",
        "vp4_banks_cp", "sm_group_rel_id"]


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def r4(v): return round(v, 4)
def face_of(x, y, w, h): return min([(x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")])[1]   # gen_core_kit_hbm.face_of
def base(n): return re.sub(r"\[\d+\]$", "", n)


P = json.load(open(SRC / "die_plan.json")); T = P["partition_types"]
OUT.mkdir(parents=True, exist_ok=True)
if not (OUT / "cores").exists():
    shutil.copytree(os.path.realpath(SRC / "cores"), OUT / "cores")
files = {}
for tn, t in T.items():
    for c in t.get("hard_cores", []):
        m, pf = c.get("module", ""), c.get("pins_file", "")
        k = next((k for k in KEYS if k in m), None)
        if k:
            files.setdefault(pf, dict(key=k, module=m, outlines=set(), insts=0))
            files[pf]["outlines"].add(tuple(round(v, 3) for v in c["outline_um"]))
            files[pf]["insts"] += 1
assert sorted({v["key"] for v in files.values()}) == sorted(KEYS), files
rep = dict(event="C25a (DIE-HBM-10)", source=str(SRC / "die_plan.json"), source_sha=sha(SRC / "die_plan.json")[:12],
           rule="clock-class pins M5 0.048 x 0.48 on the M5 track (COORD 19:30 / KITS-1 ASK b; GEOM-21)", cores={})
for pf, info in sorted(files.items()):
    assert len(info["outlines"]) == 1, (pf, info["outlines"])
    W, H = next(iter(info["outlines"]))
    pins = json.load(open(OUT / pf))
    ck = [p for p in pins if re.match(CLK_RE, base(p["name"]))]
    moves = []
    placed = {"S": [], "N": []}
    for p in ck:                                           # deterministic: plan order
        f0 = face_of(p["x"], p["y"], W, H)
        f = f0 if f0 in "NS" else ("N" if p["y"] > H / 2 else "S")
        want = p["x"] if f0 in "NS" else (CORNER if f0 == "W" else W - CORNER)
        fy = EDGE_Y if f == "S" else r4(H - EDGE_Y)
        others = [q["x"] for q in pins if q is not p and q["layer"] == "M5" and not re.match(CLK_RE, base(q["name"]))
                  and face_of(q["x"], q["y"], W, H) == f]
        occ = others + placed[f]
        k0 = round((want - TRK0) / TRK)
        best = None
        for d in range(0, 20000):
            for k in ((k0 + d, k0 - d) if d else (k0,)):
                x = r4(TRK0 + k * TRK)
                if not (CORNER - 1e-6 <= x <= W - CORNER + 1e-6):
                    continue
                if all(abs(x - o) >= MIN_D - 1e-6 for o in occ):
                    best = x
                    break
            if best is not None:
                break
        assert best is not None, (pf, p["name"])
        old = dict(p)
        p.update(layer="M5", x=best, y=fy, w=CW, h=CH)
        placed[f].append(best)
        moves.append(dict(pin=p["name"], old=dict(layer=old["layer"], x=old["x"], y=old["y"], face=f0, size="plan default"),
                          new=dict(layer="M5", x=best, y=fy, face=f, w=CW, h=CH),
                          shift_um=r4(abs(best - old["x"]) + abs(fy - old["y"]))))
    # post-conditions: on lattice, spacing, unique, face consistent
    for p in ck:
        assert abs((p["x"] - TRK0) / TRK - round((p["x"] - TRK0) / TRK)) < 1e-6
        f = face_of(p["x"], p["y"], W, H); assert f in "NS"
        for q in pins:
            if q is not p and q["layer"] == "M5" and face_of(q["x"], q["y"], W, H) == f:
                assert abs(q["x"] - p["x"]) >= MIN_D - 1e-6, (p, q)
    assert len({p["name"] for p in pins}) == len(pins)
    json.dump(pins, open(OUT / pf, "w"), indent=0)
    rep["cores"][info["module"]] = dict(pins_file=pf, outline_um=[W, H], instances=info["insts"], clock_pins=len(ck),
                                        layer_changed=sum(1 for m in moves if m["old"]["layer"] != "M5"),
                                        face_changed=sum(1 for m in moves if m["old"]["face"] != m["new"]["face"]),
                                        max_shift_um=max(m["shift_um"] for m in moves), moves=moves)
n_note = 0
mods = {v["module"] for v in files.values()}
for t in T.values():
    for c in t.get("hard_cores", []):
        if c.get("module") in mods:
            c["note"] = (c.get("note") or "") + " | C25a: clock-class pins M5 0.048x0.48 on track (pin w/h; KITS-1 ASK b)"
            n_note += 1
P["note"] = (P.get("note") or "") + (" | C25a (DIE-HBM-10 10-28): clock-class pins of 8 multi-clock cores on M5 "
                                     "0.048x0.48 (COORD 19:30, KIT_PREFLIGHT clock_pin_geometry)")
rep["notes_updated"] = n_note
txt = json.dumps(P, indent=1); (OUT / "die_plan.json").write_text(txt)
(OUT / "die_plan.sha256").write_text(hashlib.sha256(txt.encode()).hexdigest() + "  die_plan.json\n")
rep["plan_sha"] = hashlib.sha256(txt.encode()).hexdigest()[:8]
for f in os.listdir(SRC):
    if f.endswith(".json") and not (OUT / f).exists():
        shutil.copy2(SRC / f, OUT / f)
json.dump(rep, open(OUT / "c25a_event_report.json", "w"), indent=1)
print(json.dumps(dict(plan_sha=rep["plan_sha"], notes=n_note,
                      cores={m: {k: v for k, v in d.items() if k != "moves"} for m, d in rep["cores"].items()}), indent=1))
for m, d in rep["cores"].items():
    for mv in d["moves"]:
        print(m, mv["pin"], mv["old"], "->", mv["new"]["face"], mv["new"]["x"], mv["new"]["y"])
