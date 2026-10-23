#!/usr/bin/env python3
"""outline_audit.py -- every ref_tile leaf kit (and cluster, its hard children counted as macros) on main and the active branches against its content (TILE-FLOW 10-23).

For each kit (physical/ref_tile/<kit>/spec.json read straight from git objects, no checkout needed):
  current     outline of the kit (floorplan.json die, else spec outline)
  computed    tile_plan.content_outline: std / 0.65 + macro footprints + pin-register band, aspect from the per-face pin
              demand at <= 3 pins/um (pin bits from the top's ANSI header with the spec parameters)
  ratio       current / computed area; FLAG when > 1.3 and the spec has no "outline_reason"
  fill        std area / (outline - macro area) of the CURRENT outline
  bound       what sets the computed outline: area | pins (interface-limited) | macros
  regs        pin-register status: spec mode (rtl = pin_regs off with a reason, wrapper = flow-inserted ot_pin_regs,
              none) + measured unregistered pins from the coordinator's tile review (stats.json pins_unregistered) and
              from pin_reg_rtl_check.py results when given (--rtl-check DIR)
  macro_away  macros whose every signal-pin face points away from the tile centre (floorplan.json orientations + LEF)

std area source, first found: spec std_area_um2, gate_result.json "synthesized std area", floorplan.json std_area_um2,
tile-review stats.json std_area_um2 (placed; buffers included -> marked 'placed').  Kits without any std area get no
computed outline (column '-').

  outline_audit.py [--refs origin/main,...] [--active-days 2] [--review DIR] [--out TSV] [--md MD] [--kits k1,k2]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import tile_plan as TP  # noqa: E402
import check_macro_track_alignment as cmta  # noqa: E402

REPO = HERE.parent.parent
KIT_RE = re.compile(r"^physical/ref_tile/([a-z0-9_]+)/spec\.json$")
SYNTH_RE = re.compile(r"synthesized std area ([0-9.]+) um2")


class Git:
    """blob reader over one `git cat-file --batch` process"""

    def __init__(self, repo: Path):
        self.repo = repo
        self.p = subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch"], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE)
        self.cache = {}

    def read(self, ref: str, path: str) -> str | None:
        key = (ref, path)
        if key in self.cache:
            return self.cache[key]
        self.p.stdin.write(f"{ref}:{path}\n".encode())
        self.p.stdin.flush()
        hdr = self.p.stdout.readline().decode()
        if hdr.endswith("missing\n") or not hdr.strip():
            self.cache[key] = None
            return None
        n = int(hdr.split()[2])
        data = self.p.stdout.read(n)
        self.p.stdout.read(1)
        txt = data.decode(errors="replace")
        if n < (1 << 20):            # cache specs / LEFs / reports, not multi-MB netlists
            self.cache[key] = txt
        return txt

    def run(self, *args) -> str:
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True).stdout


def kit_paths(g: Git, ref: str, base: str | None) -> list:
    if base:
        out = g.run("diff", "--name-only", f"{base}...{ref}", "--", "physical/ref_tile/")
    else:
        out = g.run("ls-tree", "-r", "--name-only", ref, "physical/ref_tile/")
    return sorted({m.group(1) for line in out.splitlines() if (m := KIT_RE.match(line))})


def active_refs(g: Git, days: float) -> list:
    out = g.run("for-each-ref", "--sort=-committerdate", "--format=%(refname:short) %(committerdate:unix)",
                "refs/remotes/origin/")
    import time
    now = time.time()
    refs = []
    for line in out.splitlines():
        r, ts = line.rsplit(" ", 1)
        if r in ("origin/main", "origin/HEAD", "origin") or now - int(ts) > days * 86400:
            continue
        refs.append(r)
    return refs


_LEF = {}


def lef_macro(g: Git, ref: str, view: str) -> dict | None:
    name = view.rstrip("/").split("/")[-1]
    if view in _LEF:
        return _LEF[view]
    txt = g.read(ref, f"{view}/{name}.lef") or g.read("origin/main", f"{view}/{name}.lef")
    tm = None
    if txt:
        try:
            ms = cmta.parse_lef(txt)
            tm = next((m for m in ms if m["name"] == name), ms[0] if ms else None)
        except Exception:  # noqa: BLE001
            tm = None
    _LEF[view] = tm
    return tm


def review_index(rdir: Path | None) -> dict:
    """{kit: stats} from the coordinator's tile review dumps (<rdir>/*/stats.json)"""
    out = {}
    if not rdir or not rdir.is_dir():
        return out
    for f in rdir.glob("*/stats.json"):
        try:
            d = json.loads(f.read_text())
        except Exception:  # noqa: BLE001
            continue
        s = d.get("source") or ""
        m = (re.search(r"/ref_gate/([a-z0-9_]+?)-\d{8}-\d{6}/", s)
             or re.search(r"/closure-loop/([a-z0-9_]+?)-", s))
        if m:
            out.setdefault(m.group(1), d)
        el = d.get("element", "")
        if "__" in el:
            out.setdefault(el.split("__", 1)[1], d)
    return out


def pin_away(blocks: list, W: float, H: float, g: Git, ref: str) -> int:
    n = 0
    for b in blocks:
        if b.get("kind") != "macro":
            continue
        tm = lef_macro(g, ref, b["view"])
        if not tm:
            continue
        faces = [f for f, c in TP.macro_pin_faces(tm).items() if c >= 0.1 * max(1, max(TP.macro_pin_faces(tm).values()))]
        o = b.get("orient", "R0")
        if o not in TP._ORIENT_FACE:
            continue
        cx, cy = W / 2, H / 2
        mx, my = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
        vx, vy = cx - mx, cy - my
        norm = {"E": (1, 0), "W": (-1, 0), "N": (0, 1), "S": (0, -1)}
        dots = [norm[TP.face_after(o, f)][0] * vx + norm[TP.face_after(o, f)][1] * vy for f in faces]
        if dots and max(dots) < -1e-6:
            n += 1
    return n


def audit_kit(g: Git, ref: str, kit: str, review: dict, rtlchk: dict) -> dict | None:
    base = f"physical/ref_tile/{kit}"
    try:
        s = json.loads(g.read(ref, f"{base}/spec.json") or "null")
    except json.JSONDecodeError:
        return None
    if not isinstance(s, dict) or s.get("kind", "tile") not in ("tile", "cluster"):
        return None
    fp = None
    try:
        fp = json.loads(g.read(ref, f"{base}/floorplan.json") or "null")
    except json.JSONDecodeError:
        pass
    gr = None
    try:
        gr = json.loads(g.read(ref, f"{base}/gate_result.json") or "null")
    except json.JSONDecodeError:
        pass
    if fp and fp.get("die"):
        W, H = float(fp["die"][2]) - float(fp["die"][0]), float(fp["die"][3]) - float(fp["die"][1])
    elif s.get("outline"):
        W, H = float(s["outline"]["w"]), float(s["outline"]["h"])
    else:
        W = H = None
    std, src = s.get("std_area_um2"), "spec"
    if not std and gr:
        for it in gr.get("items", []):
            m = SYNTH_RE.search(it.get("message", ""))
            if m:
                std, src = float(m.group(1)), "gate"
                break
    if not std and fp and fp.get("std_area_um2"):
        std, src = fp["std_area_um2"], "floorplan"
    rv = review.get(kit)
    if not std and rv and rv.get("std_area_um2"):
        std, src = rv["std_area_um2"], "placed"
    texts = {}
    for f in s.get("sources", []):
        if str(f).endswith((".sv", ".v")) and not str(f).endswith("_bb.v"):
            t = g.read(ref, f)
            if t and re.search(r"\bmodule\s+(?:automatic\s+)?" + re.escape(s.get("top", "")) + r"\b", t):
                texts[f] = t
                break
    widths = TP.port_widths(texts, s.get("top", ""), s.get("params")) if texts else None
    demand, exact = TP.face_demand(s, widths)
    blocks = (fp or {}).get("blocks") or []
    macros, fixed = [], []
    for b in blocks:
        if b.get("kind") not in ("macro", "child"):
            continue
        tm = lef_macro(g, ref, b["view"])
        if tm:
            macros.append({"w": b["w"], "h": b["h"], "tm": tm})
        else:       # no LEF at this ref: still a hard block (its footprint), never std area
            fixed.append({"w": b["w"], "h": b["h"]})
    if not blocks:
        for m in s.get("macros", []):
            tm = lef_macro(g, ref, m["view"])
            if tm:
                for _ in range(int(m.get("count", 1))):
                    macros.append({"w": tm["W"] / 1000, "h": tm["H"] / 1000, "tm": tm})
    halo = float((s.get("route") or {}).get("macro_halo_um", 5.4))
    comp = None
    if std:
        try:
            cap = str(s.get("layer_cap") or "M5")
            comp = TP.content_outline(float(std), macros, demand, halo=halo, fixed=fixed,
                                      pin_layers=TP.face_pin_layers(cap if cap in ("M5", "M6") else "M5"))
        except Exception as e:  # noqa: BLE001
            comp = {"error": str(e)[:80]}
    mac_area = sum(m["w"] * m["h"] for m in macros + fixed)
    fill = (float(std) / max(1e-9, W * H - mac_area)) if (std and W) else None
    pr = s.get("pin_regs")
    mode = ("wrapper" if isinstance(pr, dict) and pr.get("enable") else
            "rtl" if isinstance(pr, dict) and pr.get("enable") is False else "none")
    if not exact and rv and rv.get("pins_per_face"):
        demand = {f: int(rv["pins_per_face"].get(f, 0)) for f in TP.FACES}   # measured on the reviewed layout
        exact = "measured"
    row = {"ref": ref, "kit": kit, "kind": s.get("kind", "tile"), "top": s.get("top"), "cur_w": W, "cur_h": H,
           "std_um2": round(float(std), 1) if std else None, "std_src": src if std else None,
           "fill": round(fill, 3) if fill is not None else None, "pins": sum(demand.values()),
           "pins_exact": exact, "macros": len(macros), "reg_mode": mode,
           "outline_reason": bool(str(s.get("outline_reason") or "").strip())}
    if comp and "error" not in comp:
        ratio = (W * H) / (comp["w"] * comp["h"]) if W else None
        row.update(comp_w=comp["w"], comp_h=comp["h"], bound=comp["bound"],
                   ratio=round(ratio, 2) if ratio else None,
                   flag=bool(ratio and ratio > TP.OUTLINE_RATIO_MAX and not row["outline_reason"]))
    else:
        row.update(comp_w=None, comp_h=None, bound=None, ratio=None, flag=False)
    row["macro_away"] = pin_away(blocks, W or 0, H or 0, g, ref) if (blocks and W) else 0
    if rv:
        row.update(meas_unreg=rv.get("pins_unregistered"), meas_p90=rv.get("pin_to_reg_p90_um"),
                   meas_fill=rv.get("std_fill_of_free_pct"), meas_away=len(rv.get("macros_pins_facing_away") or []))
    rc = rtlchk.get(kit)
    if rc:
        row["rtl_missing"] = rc.get("missing_bits")
    return row


def pct(v) -> str:
    return "" if v is None else f"{v:.0%}"


COLS = ["ref", "kit", "kind", "top", "cur_w", "cur_h", "comp_w", "comp_h", "ratio", "flag", "bound", "fill", "std_um2", "std_src",
        "pins", "pins_exact", "macros", "macro_away", "reg_mode", "rtl_missing", "meas_unreg", "meas_p90", "meas_fill",
        "meas_away", "outline_reason"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", default=str(REPO))
    ap.add_argument("--refs", default="origin/main", help="comma list; main is scanned fully, others by diff to main")
    ap.add_argument("--active-days", type=float, default=0.0, help="add every origin branch committed in the last N days")
    ap.add_argument("--review", default="/home/ubuntu/scratch/tile-review-1023")
    ap.add_argument("--rtl-check", default="", help="dir of pin_reg_rtl_check.py <kit>.json results")
    ap.add_argument("--kits", default="", help="only these kits (comma list)")
    ap.add_argument("--out", default="", help="TSV of every row")
    ap.add_argument("--md", default="", help="markdown summary")
    a = ap.parse_args(argv)
    g = Git(Path(a.repo))
    refs = [r for r in a.refs.split(",") if r]
    if a.active_days:
        refs += [r for r in active_refs(g, a.active_days) if r not in refs]
    review = review_index(Path(a.review) if a.review else None)
    rtlchk = {}
    if a.rtl_check:
        for f in Path(a.rtl_check).glob("*.json"):
            try:
                d = json.loads(f.read_text())
                rtlchk[d["kit"]] = d
            except Exception:  # noqa: BLE001
                pass
    only = {k for k in a.kits.split(",") if k}
    rows, seen = [], set()
    for ref in refs:
        kits = kit_paths(g, ref, None if ref == refs[0] else refs[0])
        for k in kits:
            if (only and k not in only) or k in seen:
                continue
            seen.add(k)
            try:
                r = audit_kit(g, ref, k, review, rtlchk)
            except Exception as e:  # noqa: BLE001
                r = {"ref": ref, "kit": k, "top": f"ERROR {str(e)[:60]}"}
            if r:
                rows.append(r)
            if len(seen) % 100 == 0:
                print(f"... {len(seen)} kits ({ref})", file=sys.stderr, flush=True)
    if a.out:
        with open(a.out, "w") as f:
            f.write("\t".join(COLS) + "\n")
            for r in rows:
                f.write("\t".join("" if r.get(c) is None else str(r.get(c)) for c in COLS) + "\n")
    comp = [r for r in rows if r.get("ratio")]
    flagged = sorted((r for r in comp if r.get("flag")), key=lambda r: -r["ratio"])
    summ = (f"{len(rows)} leaf kits on {len(refs)} refs; {len(comp)} with a computed outline; {len(flagged)} FLAGGED "
            f"(> {TP.OUTLINE_RATIO_MAX}x, no outline_reason); bound: "
            + ", ".join(f"{b} {sum(1 for r in comp if r['bound'] == b)}" for b in ("area", "pins", "macros"))
            + f"; macro_away>0: {sum(1 for r in rows if r.get('macro_away'))}; reg_mode: "
            + ", ".join(f"{m} {sum(1 for r in rows if r.get('reg_mode') == m)}" for m in ("rtl", "wrapper", "none")))
    print(summ)
    if a.md:
        lines = [f"- {summ}", "", "| kit | ref | current | computed | ratio | bound | fill | pins | macros away | regs | unreg (meas) | p90 um |",
                 "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        show = flagged[:60]
        for r in show:
            lines.append(f"| {r['kit']} | {r['ref'].replace('origin/', '')[:28]} | {r['cur_w']:g}x{r['cur_h']:g} | "
                         f"{r['comp_w']:g}x{r['comp_h']:g} | {r['ratio']} | {r['bound']} | "
                         f"{pct(r['fill'])} | {r['pins']} | "
                         f"{r.get('macro_away', 0)} | {r['reg_mode']}{'' if r.get('rtl_missing') is None else ' rtl-miss ' + str(r['rtl_missing'])} | "
                         f"{r.get('meas_unreg', '')} | {r.get('meas_p90', '')} |")
        Path(a.md).write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
