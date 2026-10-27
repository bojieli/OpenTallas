#!/usr/bin/env python3
"""PIN-ON-TRACK lint at submit (fe-push-hphys-1010, 2026-10-10).

Every IO pin (place_pin in an io_place / IO_CONSTRAINTS tcl) and every pin of a placed hard macro (place_macro in a
MACRO_PLACEMENT_TCL, its LEF from --macro-view / LANEDIR / verdict.macros) must sit on its layer's routing track in the
layer's preferred direction (asap7 make_tracks), for the block origin and the macro's location and orientation.

Measured class: hfd_su_tile_xl 2f07deaae / bb7e34c70 / fe sw147 (M5 x0 0.528, M7 0.64, M4 y 2.0: a quarter pitch off ->
DRT-0422 / DRT-0421 on every bc_in / acc pin, DRT-0255 maze failures at the S edge) and hfd_sfu_tile 18d5bc494 (M3 0.516 /
M5 0.528 / M7 0.64 faced pins).  u_lane at y 1.080 put the lane's M4 / M6 W-face pins (on grid in the lane frame) 0.024 /
0.056 off the tile tracks.  A mirrored (MX) macro of height H is on grid only when its y offset + H keeps the pins on
the lattice (H = 0.024 mod 0.048 for M4 pins at the lane-frame phase 0.012): the transform below applies the
orientation, so that rule falls out of the same check.

Static: only files that exist at the source commit and are named (after simple shell-variable expansion) in the
calibrate / route commands or the scripts they call (one level).  Generators that write their pin tcl at run time are
not visible here (verdict SKIP for that job).

Verdicts: off-track IO pins REFUSE.  Off-track macro pins WARN only (8 CLOSED routes had every SRAM M4 pin off-track;
detailed route reaches macro M4 stubs off grid), and only when some offset puts more of the macro's pins on track than the
placed one does (a LEF off the lattice in its own frame is not the placement's fault).
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# asap7 platform make_tracks.tcl (x_offset, x_pitch, y_offset, y_pitch) in um; preferred direction per layer
TRACKS = {
    "M1": (0.009, 0.036, 0.009, 0.036, "V"),
    "M2": (0.009, 0.036, None, None, "H"),     # M2 y tracks are an irregular 0.270-periodic set (see M2_Y)
    "M3": (0.009, 0.036, 0.009, 0.036, "V"),
    "M4": (0.009, 0.036, 0.012, 0.048, "H"),
    "M5": (0.012, 0.048, 0.012, 0.048, "V"),
    "M6": (0.012, 0.048, 0.016, 0.064, "H"),
    "M7": (0.016, 0.064, 0.016, 0.064, "V"),
    "M8": (0.116, 0.080, 0.116, 0.080, "H"),
    "M9": (0.116, 0.080, 0.116, 0.080, "V"),
}
M2_Y = (0.045, 0.081, 0.117, 0.153, 0.189, 0.225, 0.270)   # offsets, pitch 0.270
TOL = 0.0005


def _nm(v):
    return int(round(v * 1000))


def on_track(layer: str, x: float, y: float) -> bool:
    """the pin centre's preferred-direction coordinate lies on a track of its layer"""
    t = TRACKS.get(layer)
    if t is None:
        return True
    xo, xp, yo, yp, d = t
    if d == "V":
        return (_nm(x) - _nm(xo)) % _nm(xp) == 0
    if layer == "M2":
        r = _nm(y) % 270
        return any(r == _nm(o) % 270 for o in M2_Y)
    return (_nm(y) - _nm(yo)) % _nm(yp) == 0


# ---- tcl parsing --------------------------------------------------------------------------------------------------
PIN_RE = re.compile(r"place_pin\s+-pin_name\s+\{?([^}\s]+)\}?\s+-layer\s+(\S+)\s+-location\s+\{\s*([-\d.]+)\s+([-\d.]+)\s*\}")
MAC_RE = re.compile(r"place_macro\s+-macro_name\s+\{?([^}\s]+)\}?\s+-location\s+\{\s*([-\d.]+)\s+([-\d.]+)\s*\}"
                    r"(?:\s+-orientation\s+(\S+))?")


def io_pins(tcl: str):
    return [(m.group(1), m.group(2), float(m.group(3)), float(m.group(4))) for m in PIN_RE.finditer(tcl)]


def macros(tcl: str):
    return [(m.group(1), float(m.group(2)), float(m.group(3)), (m.group(4) or "R0").upper()) for m in MAC_RE.finditer(tcl)]


def lef_pins(lef: str):
    """(macro name, W, H, [(pin, layer, cx, cy)]) of the first MACRO; signal pins, first rect of each"""
    m = re.search(r"(?m)^\s*MACRO\s+(\S+)", lef)
    sz = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", lef)
    if not m or not sz:
        return None
    out = []
    for blk in re.split(r"\n\s*PIN\s+", lef)[1:]:
        name = blk.split(None, 1)[0]
        end = re.search(r"\n\s*END\s+" + re.escape(name) + r"\s", blk)
        body = blk[:end.start()] if end else blk
        pm = (name,)
        if re.search(r"USE\s+(POWER|GROUND)", body):
            continue
        r = re.search(r"LAYER\s+(\S+)\s*;\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", body)
        if not r:
            continue
        x0, y0, x1, y1 = map(float, r.groups()[1:])
        out.append((pm[0], r.group(1), (x0 + x1) / 2, (y0 + y1) / 2))
    return m.group(1), float(sz.group(1)), float(sz.group(2)), out


def place(orient: str, w: float, h: float, x: float, y: float):
    o = orient.upper()
    if o in ("R0", "N"):
        return x, y
    if o in ("MX", "FS"):
        return x, h - y
    if o in ("MY", "FN"):
        return w - x, y
    if o in ("R180", "S"):
        return w - x, h - y
    raise ValueError(f"orientation {orient}")


def macro_offtrack(lp, ox, oy, orient):
    _, w, h, pins = lp
    bad = []
    for n, ly, cx, cy in pins:
        px, py = place(orient, w, h, cx, cy)
        if not on_track(ly, ox + px, oy + py):
            bad.append((n, ly, round(ox + px, 4), round(oy + py, 4)))
    return bad


def best_offtrack(lp, ox, oy, orient):
    """fewest off-track pins over any offset (each preferred direction independently, 1 nm steps over the lattice LCM)"""
    from collections import Counter
    _, w, h, pins = lp
    cnt = {"V": Counter(), "H": Counter()}
    for n, ly, cx, cy in pins:
        t = TRACKS.get(ly)
        if t is None:
            continue
        px, py = place(orient, w, h, cx, cy)
        if t[4] == "V":
            cnt["V"][(ly, _nm(ox + px))] += 1
        else:
            cnt["H"][(ly, _nm(oy + py))] += 1
    best = 0
    L = 4320                                  # nm: a common period of every track lattice (36, 48, 64, 80, 270)
    for d, c in cnt.items():
        arr = [0] * L
        for (ly, v), k in c.items():
            xo, xp, yo, yp, _ = TRACKS[ly]
            if d == "V":
                starts, p = [_nm(xo)], _nm(xp)
            elif ly == "M2":
                starts, p = [_nm(o) for o in M2_Y], 270
            else:
                starts, p = [_nm(yo)], _nm(yp)
            for st in starts:
                for sh in range((st - v) % p, L, p):
                    arr[sh] += k
        best += sum(c.values()) - (max(arr) if c else 0)
    return best


# ---- locating the files a job reads ------------------------------------------------------------------------------
ASSIGN_RE = re.compile(r"(?:^|[\s;&(])(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=((?:\"[^\"]*\"|'[^']*'|[^\s;&|)])+)")
SCRIPT_RE = re.compile(r"[\w./${}:-]+\.sh\b")
PATH_RE = re.compile(r"[\w./${}:+=-]+\.(?:tcl|lef)\b")


def expand(s: str, env: dict, depth=0) -> str:
    def rep(m):
        name, dflt = m.group(1) or m.group(3), m.group(2)
        if name in env:
            return env[name]
        return dflt if dflt is not None else m.group(0)
    for _ in range(6):
        n = re.sub(r"\$\{([A-Za-z_]\w*)(?::-([^}]*))?\}|\$([A-Za-z_]\w*)", rep, s)
        if n == s:
            break
        s = n
    return s


def assigns(text: str, env: dict, override=False):
    for m in ASSIGN_RE.finditer(text):
        k, v = m.group(1), m.group(2).strip("\"'")
        if k in ("PATH",):
            continue
        if override or k not in env:
            env[k] = expand(v, env)


def _norm(p: str):
    p = re.sub(r"^(/src/|\{SRC\}/|\{SRCDIR\}/)", "", p)
    p = p.lstrip("./") if p.startswith("./") else p
    return None if ("$" in p or "{" in p or p.startswith("/")) else p


def job_files(spec: dict, git) -> dict:
    """{"io": [paths], "macro_tcl": [paths], "lefs": [paths]} named by the calibrate / route commands"""
    commit = str((spec.get("source") or {}).get("commit", ""))
    st = spec.get("stages") or {}
    cmds = [st[k]["cmd"] for k in ("route", "calibrate") if isinstance(st.get(k), dict) and st[k].get("cmd")]
    found = {"io": set(), "macro_tcl": set(), "lefs": set(), "lefdirs": set()}
    for cmd in cmds:
        env = {}
        assigns(cmd, env, override=True)
        texts = [cmd]
        for sc in SCRIPT_RE.findall(cmd):
            p = _norm(expand(sc, env))
            body = git.show(commit, p) if p else None
            if body:
                senv = dict(env)
                assigns(body, senv)          # the command's own env wins over the script's defaults
                for k, v in env.items():
                    senv[k] = v
                texts.append((body, senv))
        for t in texts:
            body, e = (t, env) if isinstance(t, str) else t
            body = re.sub(r"(?m)#.*$", "", body)
            for line in body.splitlines():
                le = expand(line, e)
                for tok in PATH_RE.findall(le):
                    tok = tok.split("=", 1)[-1]
                    p = _norm(tok)
                    if not p:
                        continue
                    txt = git.show(commit, p)
                    if not txt:
                        continue
                    if p.endswith(".lef"):
                        found["lefs"].add(p)
                    elif "place_pin" in txt:
                        found["io"].add(p)
                    elif "place_macro" in txt:
                        found["macro_tcl"].add(p)
                for mv in re.findall(r"--macro-view\s+\S+?=(\S+)|LANEDIR=(\S+)", le):
                    d = _norm(mv[0] or mv[1])
                    if d:
                        found["lefdirs"].add(d.rstrip("/"))
    for d in (spec.get("verdict") or {}).get("macros", []) or []:
        found["lefdirs"].add(str(d).rstrip("/"))
    for d in sorted(found["lefdirs"]):
        name = d.rsplit("/", 1)[-1]
        for cand in (f"{d}/{name}.lef",):
            if git.show(commit, cand):
                found["lefs"].add(cand)
    return {k: sorted(v) for k, v in found.items()}


def check(spec: dict, git, max_list=8) -> dict:
    """{"verdict": PASS|REFUSE|SKIP, "message", "io_off", "macro_off"}"""
    if spec.get("pin_track_lint", True) is False:
        return {"verdict": "SKIP", "message": "pin_track_lint opted out"}
    commit = str((spec.get("source") or {}).get("commit", ""))
    f = job_files(spec, git)
    if not f["io"] and not f["macro_tcl"]:
        return {"verdict": "SKIP", "message": "no static place_pin / place_macro tcl named by the job"}
    msgs, io_off, mac_off = [], [], []
    n_io = 0
    for p in f["io"]:
        pins = io_pins(git.show(commit, p) or "")
        n_io += len(pins)
        for n, ly, x, y in pins:
            if not on_track(ly, x, y):
                io_off.append((p, n, ly, x, y))
    if io_off:
        ex = ", ".join(f"{n} {ly} ({x}, {y})" for _, n, ly, x, y in io_off[:max_list])
        msgs.append(f"{len(io_off)} of {n_io} IO pins off their layer's track ({', '.join(sorted({p for p, *_ in io_off}))}): {ex}")
    lefs = {}
    for lp in f["lefs"]:
        parsed = lef_pins(git.show(commit, lp) or "")
        if parsed:
            lefs[lp] = parsed
    for p in f["macro_tcl"]:
        for inst, x, y, orient in macros(git.show(commit, p) or ""):
            if len(lefs) != 1:
                cand = [k for k, v in lefs.items() if v[0] in inst]
                if len(cand) != 1:
                    continue
                key = cand[0]
            else:
                key = next(iter(lefs))
            lp = lefs[key]
            bad = macro_offtrack(lp, x, y, orient)
            if not bad:
                continue
            best = best_offtrack(lp, x, y, orient)
            if best >= len(bad):
                continue          # off-lattice in its own frame: no placement fixes it
            mac_off.append((inst, len(bad), len(lp[3]), best))
            ex = ", ".join(f"{n} {ly} ({px}, {py})" for n, ly, px, py in bad[:max_list])
            msgs.append(f"macro {inst} ({lp[0]}) at ({x}, {y}) {orient}: {len(bad)} of {len(lp[3])} pins off-track "
                        f"(an on-lattice offset leaves {best}): {ex}")
    if mac_off and not io_off:
        # 8 CLOSED routes (hbm_cmdproc_{n,s}, hcjoin, hcmean) had every SRAM M4 pin off-track: detailed route reaches
        # off-grid macro pins on their M4 stubs, so a macro alone WARNs; off-track IO pins (DRT-0422 at a packed edge,
        # su tile_xl / sfu_tile DRT-0255 / DRT-0073) REFUSE.
        return {"verdict": "WARN", "io_off": 0, "macro_off": mac_off,
                "message": "PIN_TRACK WARN: " + " || ".join(msgs)}
    if msgs:
        return {"verdict": "REFUSE", "io_off": len(io_off), "macro_off": mac_off,
                "message": "PIN_TRACK: " + " || ".join(msgs) + " -- put every pin on its track (asap7: M3 x 0.009+0.036k, "
                           "M4 y 0.012+0.048k, M5 x 0.012+0.048k, M6 y 0.016+0.064k, M7 x 0.016+0.064k) and each "
                           "macro at an offset that keeps its pins on the lattice"}
    return {"verdict": "PASS", "message": f"pin-on-track: {n_io} IO pins + {len(f['macro_tcl'])} macro tcl on track",
            "io_off": 0, "macro_off": []}


def main(argv=None):
    import argparse
    import json
    sys.path.insert(0, str(HERE))
    import submit_lint
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("specs", nargs="+", help="job spec json (or a loop state json with a 'spec' key)")
    ap.add_argument("--repo", default=str(HERE.parent.parent))
    a = ap.parse_args(argv)
    g = submit_lint.Git(a.repo)
    for s in a.specs:
        d = json.loads(Path(s).read_text())
        spec = d.get("spec", d)
        r = check(spec, g)
        print(f"{spec.get('name')}: {r['verdict']} {r['message'][:600]}")


if __name__ == "__main__":
    main()
