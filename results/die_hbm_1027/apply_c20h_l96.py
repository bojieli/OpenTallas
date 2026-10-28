#!/usr/bin/env python3
"""DIE-HBM-4 C20h (C20g + latency table) = C20f + 1 ft station on root slots L96x1 / L96mx1 (C20f G0 hops: L96 hop1 / L96m hop9 = 458 um > 405).
The C20f W-face ripple moved the NW_hub E-face L96/L96m windows up to y ~3672/3681 (root-local); the first (last) root
station stayed at y 3222.72 / 3231.36.  Insert one station between them, 8.64/17.28 um in from the W edge (clear of the
L106_o / L62_o bus stations at x <= 4.32), on the 8.64 lattice; bit sites = the neighbour station's sites shifted on the
2.16 / 0.27 grid.  usage: apply_c20g_l96.py SRC_DIR DST_DIR"""
import json, hashlib, shutil, sys
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
P = json.load(open(src / "die_plan.json"))
t = P["partition_types"]["root"]
slots = {s["name"]: s for s in t["ft_slots"]}
rep = []
for name, ref, at, new in (("L96x1", 1, 1, (17.28, 3438.72)), ("L96mx1", 8, 9, (25.92, 3456.0))):
    s = slots[name]
    old = [list(r) for r in s["regs_um"]]
    rx, ry = s["regs_um"][ref]
    dx, dy = round(new[0] - rx, 4), round(new[1] - ry, 4)
    assert abs(dx / 2.16 - round(dx / 2.16)) < 1e-6 and abs(dy / 0.27 - round(dy / 0.27)) < 1e-6, (dx, dy)
    sites = [[round(x + dx, 4), round(y + dy, 4)] for x, y in s["bit_sites_um"][ref - 1]]   # regs[0] = face register, no bit sites
    assert len(s["bit_sites_um"]) == len(s["regs_um"]) - 1
    s["bit_sites_um"].insert(at - 1, sites)
    s["regs_um"].insert(at, list(new))
    s["stations"] = int(s["stations"]) + 1
    lid = name[:-2]                                            # L96x1 -> L96, L96mx1 -> L96m
    lat = P["latency"]["lanes"][lid]
    lat_old = dict(lat)
    lat["stations"] += 1; lat["natural"] += 1; lat["cycles"] += 1      # +1 cycle (12.15c: static schedule absorbs it)
    rep.append(dict(lane=lid, latency_before=lat_old, latency_after=dict(lat), slot=name, inserted_at=at, reg=list(new), from_ref=ref, shift=[dx, dy], stations=s["stations"],
                    regs_before=old, regs_after=s["regs_um"]))
if dst.exists():
    raise SystemExit(f"{dst} exists")
shutil.copytree(src, dst, ignore=shutil.ignore_patterns("gates", "gates_*", "*.otrun.log", "g0c_par.sh", "gates20f.sh"))
P["note"] = (P.get("note", "") + " | C20g (DIE-HBM-4): +1 root ft station on L96x1/L96mx1 (G0 hops 458 > 405), LAT_L96/LAT_L96M 11 -> 12")
txt = json.dumps(P, indent=1)
(dst / "die_plan.json").write_text(txt)
sha = hashlib.sha256(txt.encode()).hexdigest()
(dst / "die_plan.sha256").write_text(sha + "  die_plan.json\n")
(dst / "c20h_event_report.json").write_text(json.dumps(dict(event="C20h L96 station + latency", base=str(src), sha=sha, edits=rep), indent=1))
print(sha[:12], json.dumps([(r["slot"], r["reg"], r["stations"]) for r in rep]))
