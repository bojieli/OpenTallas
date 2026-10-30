#!/usr/bin/env python3
"""S81 kit-wave kit-RTL helpers (S81-KITS-F 10-30, COORD 02:5x ruling (3): S81 kit recipe as a script).

image  BIND_OUT PLAN TYPE   -> JSON on stdout: the bound instance whose parameter set the kit takes.
    A plan type whose bound instances carry different parameter values is kit-able as ONE hardened block only when
    every differing parameter is an image selector consumed solely by black-box hard cores of that type
    (plan partition_types[TYPE].hard_cores[] module with a LEF), passed straight through as `.X(P)`.  S81 col_*
    types: P_u_cN_M_INSTANCE -> ot_rom_4096x72_m8 .INSTANCE (one LEF/lib master, per-instance ROM image) and
    P_u_eN_INSTANCE -> ot_v41_rom_elem_q_qxpq_w10_gb .INSTANCE.  The kit netlist is then identical for every value
    set; the instance is chosen deterministically (first by name) and named in the output, never implicitly.
    Any other use of a differing parameter (logic, localparam, generate, a soft child) fails closed.

overlay BIND_OUT SRC OV     -> OV = BIND_OUT entries (symlinks) + bind.f and bind_report.json extra_lib with dead
    absolute worktree paths (/srv/opentallas-scratch*/claude/wt/<wt>/<rel>) rewritten to SRC/<rel>, so kit-rtl's
    preferred sources (bindf_prefer, extra_lib) are the files the bind listed: without it bind.f entries are
    silently dropped and a dead extra_lib entry stops kit-rtl.  A rewritten path
    missing in SRC fails closed.  Paths that exist are kept byte-for-byte.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

INST_RE = r"^\s*{m}\s*(#\(.*?\))?\s*(\w+)\s*\("          # = bind.py cmd_kit_rtl pinst regex
ARG_RE = re.compile(r'\s*\.(\w+)\s*\(\s*("(?:[^"\\]|\\.)*"|[^()",]*)\s*\)\s*(,|$)')
HDR_RE = re.compile(r"^\s*(\w+)\s*#\((.*)\)\s*(\w+)\s*\(")
DEAD_WT = re.compile(r"^/srv/opentallas-scratch\d*/claude/wt/[^/]+/(.+)$")


class KitError(Exception):
    pass


def parse_params(pset):
    """'#(.A("x"), .B(3))' -> {A: '"x"', B: '3'}; anything the simple grammar cannot consume fails closed"""
    if not pset:
        return {}
    s = pset.strip()
    if not (s.startswith("#(") and s.endswith(")")):
        raise KitError(f"unparsed parameter list {s[:80]}")
    body, out, i = s[2:-1], {}, 0
    while i < len(body):
        m = ARG_RE.match(body, i)
        if not m:
            raise KitError(f"unparsed parameter list at {body[i:i + 60]!r}")
        if m.group(1) in out:
            raise KitError(f"duplicate parameter {m.group(1)}")
        out[m.group(1)] = m.group(2)
        i = m.end()
    return out


def image_choice(out, plan, tn):
    out = Path(out)
    raw = json.loads(Path(plan).read_text())
    if tn not in raw["partition_types"]:
        raise KitError(f"{tn}: not a plan type")
    t = raw["partition_types"][tn]
    rep = json.loads((out / "bind_report.json").read_text())
    if tn not in rep["types"]:
        raise KitError(f"{tn}: not in the strict bind")
    bmod = rep["types"][tn]["module"]
    tops = sorted((out / "rtl").glob("*_bound_top.sv"))
    if len(tops) != 1:
        raise KitError(f"expected one bound top in {out}/rtl, found {len(tops)}")
    top = tops[0].read_text()
    pinst = {m.group(2): (m.group(1) or "").strip()
             for m in re.finditer(INST_RE.format(m=re.escape(bmod)), top, re.M)}
    if not pinst:
        raise KitError(f"{tn}: no instance of {bmod} in {tops[0].name}")
    sets = {k: parse_params(v) for k, v in pinst.items()}
    names = set().union(*sets.values())
    differing = sorted(p for p in names if len({s.get(p) for s in sets.values()}) > 1)
    res = dict(type=tn, bound_module=bmod, instances=len(pinst), value_sets=len(set(pinst.values())),
               image_params=differing, instance=None, consumers={})
    if not differing:
        return res
    hard = {h["module"] for h in t.get("hard_cores", []) if h.get("lef")}
    btxt = (out / "rtl" / f"{bmod}.sv").read_text()
    for p in differing:
        uses, decl = [], 0
        for ln in btxt.splitlines():
            if not re.search(rf"\b{re.escape(p)}\b", ln):
                continue
            if re.match(rf"^\s*parameter\s+(\w+\s+)?{re.escape(p)}\s*=", ln):
                decl += 1
                continue
            h = HDR_RE.match(ln)
            if not h:
                raise KitError(f"{tn}: {p} used outside a child parameter port: {ln.strip()[:120]}")
            args = parse_params("#(" + h.group(2) + ")")
            hit = [k for k, v in args.items() if re.search(rf"\b{re.escape(p)}\b", v)]
            if any(args[k].strip() != p for k in hit):
                raise KitError(f"{tn}: {p} enters an expression on {h.group(3)}: {ln.strip()[:120]}")
            if h.group(1) not in hard:
                raise KitError(f"{tn}: {p} reaches {h.group(1)} {h.group(3)}, not a black-box hard core of the type")
            uses += [f"{h.group(1)}:{h.group(3)}.{k}" for k in hit]
        if decl != 1 or not uses:
            raise KitError(f"{tn}: {p} declared {decl}x / consumed {len(uses)}x in {bmod}")
        res["consumers"][p] = uses
    res["instance"] = sorted(pinst)[0]
    res["note"] = ("differing parameters are image selectors of black-box hard cores only; the kit netlist is the "
                   "same for every instance; kit built with the parameter set of the named instance")
    return res


def overlay(out, src, ov):
    out, src, ov = Path(out).resolve(), Path(src).resolve(), Path(ov)
    ov.mkdir(parents=True, exist_ok=True)
    for n in ("bind.f", "bind_report.json", "bind_f_overlay.json"):   # never write through a link into BIND_OUT
        if (ov / n).is_symlink():
            (ov / n).unlink()
    rew = []

    def fix(ln):
        p = Path(ln)
        if not (p.is_absolute() and not p.exists()):
            return ln
        m = DEAD_WT.match(ln)
        if not m or not (src / m.group(1)).is_file():
            raise KitError(f"overlay: bound source {ln} is gone and has no file in {src}")
        now = str(src / m.group(1))
        rew.append(dict(was=ln, now=now, sha256=hashlib.sha256(Path(now).read_bytes()).hexdigest()))
        return now
    for e in sorted(out.iterdir()):
        if e.name in ("bind.f", "bind_report.json"):
            continue
        d = ov / e.name
        if d.is_symlink() or d.exists():
            if d.is_symlink() and d.resolve() == e.resolve():
                continue
            raise KitError(f"overlay: {d} exists and is not a link to {e}")
        d.symlink_to(e)
    bf = out / "bind.f"
    lines = [fix(ln) for ln in (bf.read_text().split() if bf.is_file() else [])]
    (ov / "bind.f").write_text("\n".join(lines) + ("\n" if lines else ""))
    rep = json.loads((out / "bind_report.json").read_text())
    rep["extra_lib"] = [fix(x) for x in rep.get("extra_lib", [])]   # kit-rtl validates these as preferred sources
    (ov / "bind_report.json").write_text(json.dumps(rep))
    man = dict(bind_out=str(out), src=str(src), entries=len(lines), rewritten=rew)
    (ov / "bind_f_overlay.json").write_text(json.dumps(man, indent=1))
    return dict(bind_out=str(out), overlay=str(ov), entries=len(lines), rewritten=len(rew))


def main(argv):
    try:
        if len(argv) == 4 and argv[0] == "image":
            print(json.dumps(image_choice(*argv[1:])))
        elif len(argv) == 4 and argv[0] == "overlay":
            print(json.dumps(overlay(*argv[1:])))
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except KitError as e:
        print(f"S81_KIT_RTL: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
