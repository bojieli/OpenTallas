"""DIE-HBM-2 C20d = C20c (a2212c07d93f) + the C19/C20a G0 fixes, as one plan delta (COORD 21:10 (2)(4), 21:28).
usage: apply_c20d.py REPO C20C_DIR C20D_DIR
(1) NE_b101 N / NE_hub S: L74m_0 window moved to the W end of the shared face and L12m_1 shifted W so the two windows
    no longer share tracks (C20a G0: abutment x4 + faces x2 from the L12 re-route).
(2) per-bit ft station sites over macros (q_su31 L34x1/L35x1/L48x10/L53x2/L117x7, root L9mx1/L63mx1/L96mx1):
    tools/die_plan/ft_nudge.py (only the bit cells that hit a core move to the nearest free legal row site; station
    counts, windows, pins and cores unchanged).
(3) root tkm clock leg repeaters (u_tkmclk_L4/L150 columns c1..c3) sat inside the tkm tiles: they were sited on a
    328.32-um column pitch, the tiles are on 336.96.  Every c1..c3 repeater moves to the inter-tile gap column
    (tile E edge + 4.32, the c0 rule); count/symmetry unchanged; segments re-checked <= 405 um and off every core.
(4) plan pin tables emit pin CENTRES: pins 0.019 um inside the outline (plan form) -> 0.096 um (io.tcl centre form)
    in every pins file referenced by a hard core (COORD 21:10 (2): fix the writer, not the check).
"""
import json, sys, shutil, hashlib, os, re, subprocess
from pathlib import Path
REPO, SRC, OUT = map(Path, sys.argv[1:4])
OUT.mkdir(parents=True, exist_ok=True)
for f in SRC.iterdir():
    if f.is_file() and f.suffix in (".json", ".sha256") and not (OUT / f.name).exists():
        shutil.copy2(f, OUT / f.name)
if (OUT / "cores").exists(): shutil.rmtree(OUT / "cores")
shutil.copytree(os.path.realpath(SRC / "cores"), OUT / "cores")
raw = json.load(open(SRC / "die_plan.json")); T = raw["partition_types"]
rep = dict(source=str(SRC / "die_plan.json"), source_sha=hashlib.sha256((SRC / "die_plan.json").read_bytes()).hexdigest()[:12])
def r4(v): return round(v, 4)

# (1) window de-overlap on the NE_b101 N / NE_hub S face
P = {p["id"]: p for p in raw["ports"]}
parts = {p["name"]: p for p in raw["partitions"]}
x0 = parts["NE_b101"]["origin_um"][0]
w74 = P["L74m_0"]["window_um"]; w12 = P["L12m_1"]["window_um"]
lo74 = r4(round((x0 + 9.36) / 0.048) * 0.048); P["L74m_0"]["window_um"] = [lo74, r4(lo74 + (w74[1] - w74[0]))]
lo12 = r4(round((P["L74m_0"]["window_um"][1] + 8.64) / 0.048) * 0.048); P["L12m_1"]["window_um"] = [lo12, r4(lo12 + (w12[1] - w12[0]))]
rep["windows"] = dict(L74m_0=[w74, P["L74m_0"]["window_um"]], L12m_1=[w12, P["L12m_1"]["window_um"]],
                      face_end=r4(x0 + T[parts["NE_b101"]["type"]]["outline_um"][0]))

# (3) tkm leg repeaters to the inter-tile gap columns
rt = T["root"]; ck = rt["clock"]; taps = {t["name"]: t for t in ck["taps"]}
tiles = [c for c in rt["hard_cores"] if "u_tkm_SW_tile" in c["inst"]]
cols = sorted({(c["origin_um"][0], r4(c["origin_um"][0] + c["outline_um"][0])) for c in tiles})
boxes = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1], c["inst"]) for c in rt["hard_cores"]]
moved, bad = [], []
for b in ck["branch_buffers"]:
    m = re.match(r"u_tkmclk_L(4|150)_c(\d)$", b["name"])
    if not m or not b.get("leg_repeaters"): continue
    ci = int(m.group(2))
    if ci == 0: continue
    gx = r4(cols[ci][1] + 4.32)
    for r in b["leg_repeaters"]:
        old = list(r["xy"]); dx = r4(gx - r["xy"][0])
        r["xy"] = [gx, r["xy"][1]]; r["cell_ll_um"] = [r4(r["cell_ll_um"][0] + dx), r["cell_ll_um"][1]]
        cw, ch = r.get("cell_wh_um", (1.404, 0.27)); ll = r["cell_ll_um"]
        hit = [n for a, c, e, f, n in boxes if ll[0] < e and ll[0] + cw > a and ll[1] < f and ll[1] + ch > c]
        tp = taps[r["tap"]]["xy"]
        s1 = abs(b["xy"][0] - gx) + abs(b["xy"][1] - r["xy"][1]); s2 = abs(gx - tp[0]) + abs(r["xy"][1] - tp[1])
        moved.append(dict(name=r["name"], frm=old, to=r["xy"], seg_um=[r4(s1), r4(s2)], hits=hit))
        if hit or s1 > 405 or s2 > 405: bad.append(r["name"])
rep["tkm_repeaters"] = dict(moved=len(moved), bad=bad, detail=moved)

# (4) pin centres
fixed, files = 0, 0
seen = {}
for tn, t in T.items():
    for h in t.get("hard_cores") or []:
        pf = h.get("pins_file")
        if pf and pf not in seen: seen[pf] = h["outline_um"]
for pf, (W, H) in seen.items():
    fp = OUT / pf
    if not fp.is_file(): continue
    d = json.loads(fp.read_text()); pins = d["pins"] if isinstance(d, dict) else d; n = 0
    for p in pins:
        for k, lim in (("x", W), ("y", H)):
            v = p[k]
            if abs(v - 0.019) < 1e-6: p[k] = 0.096; n += 1
            elif abs((lim - v) - 0.019) < 1e-6: p[k] = r4(lim - 0.096); n += 1
    if n:
        fp.write_text(json.dumps(d, indent=1)); fixed += n; files += 1
rep["pin_centres"] = dict(files=files, pins=fixed)
raw["die"]["label"] = "C20d = C20c + DIE-HBM-2 G0 fixes (L74m/L12m windows, ft bit sites, tkm leg repeaters, pin centres) | " + raw["die"].get("label", "")
tmp = OUT / "die_plan.pre_nudge.json"; tmp.write_text(json.dumps(raw))

# (2) ft_nudge (bit sites over macros)
r = subprocess.run([sys.executable, str(REPO / "tools/die_plan/ft_nudge.py"), str(tmp), str(OUT / "die_plan.json"),
                    str(OUT / "ft_nudge_ledger.json")], capture_output=True, text=True, cwd=str(OUT))
rep["ft_nudge"] = dict(rc=r.returncode, out=r.stdout[-800:], err=r.stderr[-1500:])
if r.returncode != 0:
    shutil.copy2(tmp, OUT / "die_plan.json")
d = json.load(open(OUT / "die_plan.json")); (OUT / "die_plan.json").write_text(json.dumps(d, indent=1)); tmp.unlink()
(OUT / "die_plan.sha256").write_text(hashlib.sha256((OUT / "die_plan.json").read_bytes()).hexdigest() + "\n")
(OUT / "c20d_event_report.json").write_text(json.dumps(rep, indent=1, default=str))
print(json.dumps({k: (v if k != "tkm_repeaters" else dict(moved=v["moved"], bad=v["bad"])) for k, v in rep.items()}, indent=1, default=str)[:3000])
