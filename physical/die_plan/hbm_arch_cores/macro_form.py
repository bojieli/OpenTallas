#!/usr/bin/env python3
"""DIE-HBM-64/REFORM macro form: new macro placement for a kit (same RTL, same pins); snaps with the generator rule.
  macro_form.py KIT placements.json    placements: [[inst,x,y,orient],...]; master read from the old macro_placement.tcl
  macro_form.py KIT --resnap [--restart]  keep the placement in the kit, snap it again; --restart also clears run
                                       stage files from 2_2 on and FAIL_* markers so the kit resumes from 2_1_floorplan.
DIE-HBM-66 class fix (12 nm y): the snap got the PATH of make_tracks.tcl instead of its text, matched no make_tracks line and
fell back to the platform offsets (M4/M5 12 nm) where the kit has 24 nm, so forms sat 12 nm off the kit grid and
macro_grid_snap.json said moves []."""
import glob, json, os, re, shutil, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "die_plan"))
import gen_core_kit_hbm as G  # noqa: E402

ROW = r"\{(\S+)\}\s+(\S+)\s+([-\d.]+)\s+([-\d.]+)\s+(\w+)"
TAIL = '} {\n  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact\n}\n'


def read_rows(k):
    return re.findall(ROW, (k / "macro_placement.tcl").read_text())


def save_pre(k):
    pre = k / ".form64_pre"
    pre.mkdir(exist_ok=True)
    for n in ("macro_placement.tcl", "macro_grid_snap.json"):
        if (k / n).exists() and not (pre / n).exists():
            shutil.copy2(k / n, pre / n)


def snap(k, P):
    tracks = (k / "make_tracks.tcl").read_text()
    if not re.search(r"(?m)^\s*make_tracks\s+M[4-7]\s", tracks):
        raise SystemExit(f"macro_form: {k}/make_tracks.tcl declares no M4-M7 tracks; snap would use platform offsets")
    W, H = map(float, re.search(r"DIE_AREA = 0 0 (\S+) (\S+)", (k / "config.mk").read_text()).groups())
    return G.snap_macro_placement(P, tracks, lambda m: (k / "macros" / f"{m}.lef").read_text(), (W, H))


def restart(k):
    n = 0
    for r in ("results", "logs", "reports", "objects"):
        for g in glob.glob(str(k / "run" / r / "asap7/*/base/*")):
            b = os.path.basename(g)
            if re.match(r"(2_2|2_3|2_4|2_floorplan|3_|4_|5_|6_)", b) and b != "2_1_floorplan.odb" and not os.path.isdir(g):
                os.remove(g)
                n += 1
    for x in ("FAIL_POSTCTS", "FAIL_PREFLOOR"):
        (k / x).unlink(missing_ok=True)
    return n


def main(argv):
    k = Path(argv[1])
    rows = read_rows(k)
    masters = {r[0]: r[1] for r in rows}
    if argv[2] == "--resnap":
        P = [dict(inst=r[0], macro=r[1], xy_um=[float(r[2]), float(r[3])], orient=r[4]) for r in rows]
    else:
        pl = json.load(open(argv[2]))
        assert set(masters) == set(p[0] for p in pl), (sorted(masters), sorted(p[0] for p in pl))
        P = [dict(inst=i, macro=masters[i], xy_um=[x, y], orient=o) for i, x, y, o in pl]
    out, moves = snap(k, P)
    save_pre(k)
    L = ["foreach {inst master x y orient} {"] + ["  {%s} %s %s %s %s" % (
        p["inst"], p["macro"], format(p["xy_um"][0], ".12g"), format(p["xy_um"][1], ".12g"), p["orient"]) for p in out]
    (k / "macro_placement.tcl").write_text("\n".join(L) + "\n" + TAIL)
    (k / "macro_grid_snap.json").write_text(json.dumps(dict(
        source="gen_core_kit_hbm.snap_macro_placement via macro_form.py", moves=moves), indent=1) + "\n")
    if argv[2] != "--resnap":
        (k / "FORM_MACRO64.json").write_text(json.dumps(dict(
            form="macro_channels", by="DIE-HBM-64/REFORM", date=time.ctime(),
            placements=[[p["inst"], p["xy_um"][0], p["xy_um"][1], p["orient"]] for p in out],
            note="same RTL, same pins; placement only"), indent=1) + "\n")
    print(k.name, "moves", len(moves), [(m["dx_nm"], m["dy_nm"]) for m in moves][:4])
    if "--restart" in argv:
        print("removed", restart(k))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
