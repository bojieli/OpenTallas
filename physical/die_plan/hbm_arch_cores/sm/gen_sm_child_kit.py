#!/usr/bin/env python3
"""PATH-HBM-SM 10-25: per-child-type ORFS kits for the hnx-sm4p cluster halves hnx_rp3lp3h_n / hnx_rp3lp3h_s.

    python3 gen_sm_child_kit.py --child bdc|tct|tcl|xs3n|beat_e|land|row_w|row_e --out KITROOT [--views-out V.json]
                                [any gen_core_kit_hbm.py option, e.g. --clock-taps density]

Why: a flat half is 765k (n) / 754k (s) std cells, over the 400k-cells-per-OpenROAD-run cap, so the half is hardened
as the hnx-sm4p CLUSTER (spec physical/hbm_next/sm4/hnx_rp3lp3h_<h>_spec.json @ SRC): n = 18 hard children, s = 16,
from 8 child types shared by n and s.  The children closed only under the old SS policy; this re-kits each type on the
current HBM core-kit flow (gen_core_kit_hbm.py: RCX RC basis, per-corner vclk TT/FF, density clock taps, sdc_lint,
LEC + SELRANGE + face_guard + port_bind gates).

Substitutions over gen_core_kit_hbm.py (same pattern as gen_sm_kit.py):
  * every RTL file is read with `git show SRC:<path>` (the exact hnx-sm4p RTL the halves lockstep bench proves);
  * file list = the child's own ref_tile spec sources @SRC (the half list carries unrelated files that do not elaborate
    stand-alone, e.g. hnx_rp4lp4_leaf.sv `OT_RP4_AR -> LEC lint failed); defines = the HALF spec's (the child module is
    elaborated with the cluster's define set); top = the child module;
  * pins = the child's as-built abstract pins (LEF of the closed ref_tile view; xs3n: its exact pin plan tcl, it never
    closed), same face / order / layer class, snapped onto the HBM plan lattice (M4/M5 0.024+0.048k, M6/M7
    0.032+0.064k; M3 face pins move to M5) so the cluster parent routes them on the plan tracks;
  * outline = the as-built LEF SIZE (the cluster child_lattice positions were laid out with it); xs3n = spec outline;
  * xs3n SRAMs: fixed placement from its spec (12 x ot_sram_1r1w_128x256_m1_r2c2 on the 43.2 lattice);
  * face shell OFF: a +1/+1 shell on a cluster child would add cycles inside the half (the half schedule is the flat
    lp record); face_guard still reports every unregistered child pin (structural item, see the lane file).
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import gen_core_kit_hbm as G  # noqa: E402

SRC = "4d6f5439dcee43b97baffaa731aae826fdcb6a66"   # origin/claude/hnx-sm4p-1020 (HNX-SM4P half kits + bench)
PLAN = "/srv/opentallas-scratch/claude/elem-hbm/inputs/physical/die_plan/hbm_arch/B2r2/die_plan.json"
RT = "physical/ref_tile"
CHILDREN = {
    "xs3n": dict(top="hnx_xs3", spec=f"{RT}/hnx_rp3lp3_xs3n/spec.json", pins_tcl="physical/hbm_next/sm4/hnx_rp3lp3_xs3n_pins.tcl",
                 view="physical/ref_tile/hnx_rp3lp3_xs3n/views/hnx_xs3"),
    "bdc": dict(top="ot_hbm_accel_smh_bdc", spec=f"{RT}/smh_bdc_ref_p50/spec.json", view=f"{RT}/smh_bdc_ref_p50/views/ot_hbm_accel_smh_bdc"),
    "tct": dict(top="ot_hbm_accel_smh_tct", spec=f"{RT}/smh_tct_ref_p45/spec.json", view=f"{RT}/smh_tct_ref_p45/views/ot_hbm_accel_smh_tct"),
    "tcl": dict(top="ot_hbm_accel_smh_tcl", spec=f"{RT}/smh_tcl_ref_p45/spec.json", view=f"{RT}/smh_tcl_ref_p45/views/ot_hbm_accel_smh_tcl"),
    "beat_e": dict(top="ot_smh_tr_group_beat_e", spec=f"{RT}/smh_tr_group_beat_e_ref/spec.json", view=f"{RT}/smh_tr_group_beat_e_ref/views/ot_smh_tr_group_beat_e"),
    "land": dict(top="ot_smh_tr_group_land", spec=f"{RT}/smh_tr_group_land_ref/spec.json", view=f"{RT}/smh_tr_group_land_ref/views/ot_smh_tr_group_land"),
    "row_w": dict(top="ot_smh_tr_group_row_w", spec=f"{RT}/smh_tr_group_row_w_ref/spec.json", view=f"{RT}/smh_tr_group_row_w_ref/views/ot_smh_tr_group_row_w"),
    "row_e": dict(top="ot_smh_tr_group_row_e", spec=f"{RT}/smh_tr_group_row_e_ref/spec.json", view=f"{RT}/smh_tr_group_row_e_ref/views/ot_smh_tr_group_row_e"),
}
LAT = {"M4": (0.024, 0.048, "y"), "M5": (0.024, 0.048, "x"), "M6": (0.032, 0.064, "y"), "M7": (0.032, 0.064, "x")}
EDGE_KEEP_UM = 1.0          # no pin closer than this to a corner


def git_show(path):
    r = subprocess.run(["git", "-C", str(G.REPO), "show", f"{SRC}:{path}"], capture_output=True)
    if r.returncode:
        raise SystemExit(f"{path} missing at {SRC}")
    return r.stdout


def fetch(f, commit, dst, at_commit=False):
    data = git_show(f)
    if dst.exists() and dst.read_bytes() != data:
        raise SystemExit(f"rtl name clash {dst.name}")
    dst.write_bytes(data)


def lef_pins(text):
    size = re.search(r"SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)", text)
    w, h = float(size.group(1)), float(size.group(2))
    pins = []
    for m in re.finditer(r"(?m)^\s*PIN\s+(\S+)\s*$", text):
        name = m.group(1)
        e = re.compile(r"(?m)^\s*END\s+" + re.escape(name) + r"\s*$").search(text, m.end())
        body = text[m.end():e.start()]
        if name in ("VDD", "VSS"):
            continue
        lm = re.search(r"LAYER\s+(\w+)\s*;\s*RECT\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)", body)
        x0, y0, x1, y1 = map(float, lm.groups()[1:])
        pins.append(dict(name=name.replace("\\[", "[").replace("\\]", "]"), layer=lm.group(1),
                         x=(x0 + x1) / 2, y=(y0 + y1) / 2))
    return w, h, pins


def tcl_pins(text):
    pins = []
    for m in re.finditer(r"place_pin -pin_name \{([^}]+)\} -layer (\w+) -location \{([-0-9.]+) ([-0-9.]+)\}", text):
        pins.append(dict(name=m.group(1), layer=m.group(2), x=float(m.group(3)), y=float(m.group(4))))
    return pins


def snap(pins, w, h):
    """keep face / order; M3 -> M5 (N/S) or M4 (E/W); along-face coordinate onto the plan lattice, unique track."""
    out, moved = [], 0.0
    groups = {}
    for p in pins:
        f = G.face_of(p["x"], p["y"], w, h)
        L = p["layer"]
        if L not in LAT:
            L = "M5" if f in "NS" else "M4"
        if (f in "NS") != (LAT[L][2] == "x"):
            raise SystemExit(f"pin {p['name']} layer {L} does not run across face {f}")
        groups.setdefault((f, L), []).append(dict(p, layer=L, face=f))
    for (f, L), ps in groups.items():
        off, pitch, ax = LAT[L]
        span = w if ax == "x" else h
        kmin = int((EDGE_KEEP_UM - off) / pitch) + 1
        kmax = int((span - EDGE_KEEP_UM - off) / pitch)
        ps.sort(key=lambda q: q[ax])
        if len(ps) > kmax - kmin + 1:
            raise SystemExit(f"face {f} {L}: {len(ps)} pins > {kmax - kmin + 1} lattice tracks")
        prev = kmin - 1
        for i, q in enumerate(ps):
            k = max(prev + 1, round((q[ax] - off) / pitch), kmin)
            k = min(k, kmax - (len(ps) - 1 - i))       # leave room for the rest
            prev = k
            v = round(off + k * pitch, 4)
            moved = max(moved, abs(v - q[ax]))
            x = v if ax == "x" else (0.0 if f == "W" else w)
            y = v if ax == "y" else (0.0 if f == "S" else h)
            out.append(dict(name=q["name"], layer=L, x=x, y=y))
    return out, moved


def main():
    argv = sys.argv[1:]

    def take(flag, default=None):
        nonlocal argv
        if flag not in argv:
            return default
        i = argv.index(flag)
        v = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
        return v
    child = take("--child")
    views_out = take("--views-out")
    # --src <commit>: RTL/spec commit (default SRC); --extra-define A,B: added to the half defines (e.g. OT_SMH_FACE_CLONE,
    # the opt-in one-register-per-face-pin copies on claude/path-hbm-sm-rtl-1025)
    global SRC
    s = take("--src")
    if s:
        SRC = subprocess.run(["git", "-C", str(G.REPO), "rev-parse", f"{s}^{{commit}}"], capture_output=True, text=True,
                             check=True).stdout.strip()
    extra = [d for d in (take("--extra-define") or "").split(",") if d]
    c = CHILDREN[child]
    half = json.loads(git_show("physical/hbm_next/sm4/hnx_rp3lp3h_n_spec.json"))
    half_s = json.loads(git_show("physical/hbm_next/sm4/hnx_rp3lp3h_s_spec.json"))
    if half["sources"] != half_s["sources"] or half["defines"] != half_s["defines"]:
        raise SystemExit("n / s halves elaborate children differently: one child kit cannot serve both")
    cspec = json.loads(git_show(c["spec"]))
    assert cspec["top"] == c["top"], (cspec["top"], c["top"])
    insts = [f"{h_}:{ch['inst']}" for h_, hs in (("n", half), ("s", half_s)) for ch in hs["children"] if ch["view"] == c["view"]]
    if not insts:
        raise SystemExit(f"{child}: view {c['view']} not used by the halves")
    if "pins_tcl" in c:
        w, h = float(cspec["outline"]["w"]), float(cspec["outline"]["h"])
        raw = tcl_pins(git_show(c["pins_tcl"]).decode())
        pin_src = f"{c['pins_tcl']}@{SRC}"
    else:
        lef = f"{c['view']}/{c['top']}.lef"
        w, h, raw = lef_pins(git_show(lef).decode())
        pin_src = f"{lef}@{SRC}"
    pins, moved = snap(raw, w, h)
    kitroot = Path(take("--out", None) or ".")
    argv += ["--out", str(kitroot)]
    pdir = kitroot / "_views"
    pdir.mkdir(parents=True, exist_ok=True)
    pf = pdir / f"{c['top']}.pins.json"
    pf.write_text(json.dumps(pins) + "\n")
    psha = hashlib.sha256(pf.read_bytes()).hexdigest()
    view = f"{c['top']}@{psha[:12]}"
    vf = Path(views_out) if views_out else pdir / f"views_{c['top']}.json"
    V = dict(schema="opentallas.hbm_arch.core_views.v1", plan=PLAN, note="PATH-HBM-SM hnx-sm4p cluster children",
             view_list=[dict(view=view, module=c["top"], outline_um=[w, h], pins_file=str(pf.resolve()), pins_sha256=psha,
                             pins=len(pins), family="SM-CHILD", instances=insts, placed=len(insts), recipe_keys=[c["top"]],
                             pin_source=pin_src, snap_max_move_um=round(moved, 4))])
    vf.write_text(json.dumps(V, indent=1) + "\n")
    rec = dict(files=cspec["sources"], top=c["top"], params={}, defines=half["defines"] + [d for d in extra if d not in half["defines"]], source_commit=SRC, read_at_commit=True,
               util=float(cspec.get("route", {}).get("pd", 0.5)), src_spec=f"{c['spec']}@{SRC}",
               cluster=f"physical/hbm_next/sm4/hnx_rp3lp3h_{{n,s}}_spec.json@{SRC}")
    if cspec.get("macros"):
        names = sorted({Path(m["view"]).name for m in cspec["macros"]})
        rec["macros"] = names
        mp = []
        for m in cspec["macros"]:
            g = re.match(r"^\*g_ln\?(\d+)\?\.g_xm\?(\d+)\?\.u_x\*$", m["inst"])
            if not g:
                raise SystemExit(f"unexpected macro inst glob {m['inst']}")
            mp.append(dict(inst=f"u_leaf.g_ln[{g.group(1)}].g_xm[{g.group(2)}].u_x", xy_um=m["at"],
                           orient=m.get("orient", "R0"), macro=Path(m["view"]).name))
        rec["macro_placement"] = mp
        rec["macro_place_halo_um"] = float(cspec.get("route", {}).get("macro_halo_um", 4.32))
    G.fetch = fetch
    G.load_recipes = lambda: {c["top"]: rec}
    sys.argv = [sys.argv[0], "--views", str(vf), "--view", view, "--recipe-key", c["top"], "--face-shell", "off",
                "--core-insertion", "none"] + argv
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        G.main()
    out = json.loads(buf.getvalue().strip().splitlines()[-1])
    kd = Path(out["kit"])
    fz = json.loads((kd / "freeze.json").read_text())
    fz.update(src_commit=SRC, src_spec=rec["src_spec"], cluster=rec["cluster"], cluster_instances=insts, pin_source=pin_src,
              snap_max_move_um=round(moved, 4), flow="hnx-sm4p cluster child (PATH-HBM-SM 10-25), face shell off")
    fz["kit_hash"] = G.kit_hash(kd)
    (kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
    out.update(kit_hash=fz["kit_hash"], child=child, instances=len(insts), snap_max_move_um=round(moved, 4), outline=[w, h])
    print(json.dumps(out))


if __name__ == "__main__":
    main()
