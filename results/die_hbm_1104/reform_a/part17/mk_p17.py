#!/usr/bin/env python3
"""HBM-REFORM-A d44v part 17: lanes canon (14 rows) -> 4 x lane1 at its existing table; lanes_plain (8 rows) -> 4 x lane1p, stacked.
    mk_p17.py PLAN_DIR PART_DIR REPO [--wrapper-out PATH]
PLAN_DIR: unpacked d44v (plain die_plan.json, clock_entries.json, core_conns.json).  Runs results/die_hbm_1103/reform/mk_split.py unchanged, then:
  * canon rows point at the existing lane1 oneclk table (live forms keep their key): mk_split's own lane1 table is put back byte for byte;
  * lane1p gets its one-clock table through results/die_hbm_1104/reform/mk_oneclk.py, as lane1 had in part 9;
  * no parent_id_straps on the sub rows, as the lanes8_11 lane1 rows: lane0_lane_id is an 11-bit plan pin the parent ties ({lane_lane_id, k});
  * core_clock_regions.json entries of the 2 removed modules go, totals follow.
Plain tile order: least total pin displacement over the 24 orders."""
import collections, hashlib, itertools, json, re, shutil, subprocess, sys
from pathlib import Path
pd, part, repo = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
wout = Path(sys.argv[sys.argv.index("--wrapper-out") + 1]) if "--wrapper-out" in sys.argv else part / "ot_hbm_su_pg_lane1p_core.oneclk.sv"
L1, LP = "ot_hbm_su_pg_lane1_core", "ot_hbm_su_pg_lane1p_core"
CANON, PLAIN = "ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77", "ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526"
PRE = "u_fcore.u_core."; PW, PH = 440.64, 112.32; SY = 112.32
spec = json.loads((part / "split_p17.json").read_text())
D = json.loads((pd / "die_plan.json").read_text())
ids = {h["inst"] for t in D["partition_types"].values() for h in t.get("hard_cores") or [] if h["module"] in (CANON, PLAIN)}
row = next(h for t in D["partition_types"].values() for h in t.get("hard_cores") or [] if h["module"] == PLAIN)
OP = {p["name"]: p for p in json.loads((pd / row["pins_file"]).read_text())}
C = json.loads((part / "lanes_plain.conn.json").read_text())
slots = [(0.0, round(k * SY, 3)) for k in range(4)]
def box(px, py, o):
    return max(o[0] - px, 0, px - o[0] - PW) + max(o[1] - py, 0, py - o[1] - PH)
insts = [s["inst"] for s in C["subs"]]; bits = {s["inst"]: s["bits"] for s in C["subs"]}
cost = {i: [sum(box(OP[t]["x"], OP[t]["y"], o) for b in bits[i].values() for t in b["top"] if t in OP) for o in slots] for i in insts}
perm = min(itertools.permutations(range(4)), key=lambda p: sum(cost[i][k] for i, k in zip(insts, p)))
for sp in spec:
    if sp["core"] == PLAIN:
        sp["layout"] = {i: dict(xy=list(slots[k]), wh=[PW, PH]) for i, k in zip(insts, perm)}
print("plain order", dict(zip(insts, perm)), "displacement", round(sum(cost[i][k] for i, k in zip(insts, perm))), "um")
(pd / "split_p17_resolved.json").write_text(json.dumps(spec, indent=1) + "\n")
# the lane1 table mk_split rewrites and the table the plan rows use
L1T = "cores/ot_hbm_su_pg_lane1_core__190.08x311.04__d44v_split.json"
L1O = L1T[:-5] + "__oneclk.json"
keep = (pd / L1T).read_bytes(); keep_o = (pd / L1O).read_bytes()
subprocess.run([sys.executable, str(repo / "results/die_hbm_1103/reform/mk_split.py"), str(pd), str(pd / "split_p17_resolved.json"), str(part)], check=True, stdout=open(pd / "split_p17.log", "w"))
print((pd / "split_p17.log").read_text()[-900:])
(pd / L1T).write_bytes(keep); assert (pd / L1O).read_bytes() == keep_o
D = json.loads((pd / "die_plan.json").read_text()); n = collections.Counter()
for tn, t in D["partition_types"].items():
    for h in t.get("hard_cores") or []:
        if h["module"] == L1 and h.get("pins_file") == L1T:
            h["pins_file"] = L1O; n["canon rows"] += 1
        if h["module"] in (L1, LP) and h.get("physical_inst", "").split(".")[0] in ids:
            h.pop("parent_id_straps", None); n["straps dropped"] += 1   # as the lanes8_11 lane1 rows: lane0_lane_id is a plan pin the parent ties
(pd / "die_plan.json").unlink(); (pd / "die_plan.json").write_text(json.dumps(D, indent=1) + "\n")
# lane1p W/E faces: M4 only, tile 112.32 tall, so the 840-bit load bus would put E at every track. Move ld_c bits with index >= 255 to W (a registered parent wire, 440 um), then both faces go on even M4 tracks in order.
LPT = pd / f"cores/{LP}__440.64x112.32__d44v_split.json"; T = json.loads(LPT.read_text()); PITCH, OFF, MG = 0.048, 0.024, 1.0
E_, W_ = round(PW - 0.096, 3), 0.096; nmv = 0
for p_ in T:
    m_ = re.fullmatch(r"lane0_ld_c\[(\d+)\]", p_["name"])
    if m_ and int(m_.group(1)) >= 255 and p_["x"] == E_:
        p_["x"] = W_; p_["y"] = round(MG + (int(m_.group(1)) - 255) / 585 * (PH - 2 * MG), 3); nmv += 1
tracks = [round(OFF + k * PITCH, 3) for k in range(int(PH / PITCH)) if MG <= OFF + k * PITCH <= PH - MG]
for f_, xf in (("W", W_), ("E", E_)):
    ps = sorted((p for p in T if p["layer"] == "M4" and p["x"] == xf), key=lambda p: (p["y"], p["name"]))
    st = len(tracks) / max(len(ps), 1)
    assert st >= 2, (f_, len(ps), len(tracks))
    for i, p_ in enumerate(ps):
        p_["y"] = tracks[int((i + 0.5) * st)]
    print("lane1p face", f_, "pins", len(ps), "tracks", len(tracks), "step", round(st * PITCH, 3), "um", "moved", nmv)
LPT.unlink(); LPT.write_text(json.dumps(T) + "\n")
# lane1p one-clock table + wrapper
txt = (repo / "rtl/hbm_accel/cores_split/reform_1104a/lanes4" / f"{LP}.sv").read_text()
hdr = re.search(r"module\s+" + LP + r"\s*#\s*\(.*?\)\s*\((.*?)\n\);", txt, re.S).group(1)
pl = ["# dir width name"]
for k, w, nm in re.findall(r"(input|output)\s+wire\s+(?:\[(\d+):0\]\s*)?(\w+)", hdr):
    pl.append(f"{k} [{int(w or 0)}:0] {nm}")
(part / "lane1p.portlist").write_text("\n".join(pl) + "\n")
r = subprocess.run([sys.executable, str(repo / "results/die_hbm_1104/reform/mk_oneclk.py"), str(pd), LP, str(wout), "--rename-top", LP + "__mc", "--portlist", str(part / "lane1p.portlist")], check=True, capture_output=True, text=True)
print(r.stdout.strip()[:400])
# clock-region sidecar
f = pd / "core_clock_regions.json"; G = json.loads(f.read_text()); gone = []
if isinstance(G.get("modules"), dict):
    for m in (CANON, PLAIN):
        if m in G["modules"]:
            e = G["modules"].pop(m); gone.append(m)
            G["totals"]["modules"] -= 1; G["totals"]["entries"] -= e["entries"]; G["totals"]["slots"] -= e["instances"]
    G["no_sink_data"] = sorted(set(G["no_sink_data"]) | {LP})
    (f).unlink(); f.write_text(json.dumps(G, indent=1) + "\n")
print("rows", dict(n), "regions removed", gone, "totals", G.get("totals"))
