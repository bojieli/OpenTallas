#!/usr/bin/env python3
"""bind_rowcheck: the plan-row precheck classes of plan_gate_pre (BIND-SPEED-1118).  Minutes before a 45-80 min bind.

Late bind failures of 11-17/18 that a bind found only after its full run, and the class that now catches each in seconds:

  FIXEDCYC   (QC N4C: fixed_cycles double-counted)   every lane has a latency row, row.fixed == lane.fixed_cycles, and the row is
             self-consistent: natural == boundary + stations + fixed + clock_landing and cycles == natural + pad.  A lane whose
             fixed_cycles was bumped without the table (or the table bumped twice) fails here; G0 `latency` finds it 20 min later.
  ROWSINK    (S81 D8e / QC R8_STALE "no such sink")  every R8 table member (asbuilt.land_r8 + land_r8_extra) whose pad is not 0
             names a sink leaf (and port) that exists in the elaborated die (OUT/asbuilt.json).  Names compare exactly, then in
             instance-name form (u_r0.u_x == u_r0_u_x, bind's sv_id), then by canonical yosys `$op$#` name.  Needs the elab output.
  MODULES    (rows naming missing modules)  every module named by asbuilt.substitute_inst / substitute / sub_core_leaf exists as RTL (module_index) or in the elaborated netlist.
  TOOLSTALE  (S81 D8e: tools older than rt/current without b8f543dd448)  a tools/die_plan file of the bind tree that differs from the
             live reference tree's (OT_RT_CURRENT, --ref-tools, or <scratch>/claude/rt/current) and is OLDER than it.

Every function returns finding lines `FAIL <CLASS> ...` / `WARN <CLASS> ...` like plan_gate_pre.  No network, no writes.
"""
import json
import os
import re
from pathlib import Path

MAX_LINES = 12


def _sv_id(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def _canon(x):
    return re.sub(r"\$(\w+)\$[\w.]+:\d+\$\d+", r"$\1$#", x)


def _cap(lines, total, what):
    out = lines[:MAX_LINES]
    if total > len(out):
        out.append(f"{out[0].split()[0]} {out[0].split()[1]} ... {total - len(out)} more {what}")
    return out


# ---------------------------------------------------------------- FIXEDCYC
def check_fixedcyc(plan):
    lanes = plan.get("lanes") or []
    if not lanes:
        return []
    lat = (plan.get("latency") or {}).get("lanes")
    if lat is None:
        return ["FAIL FIXEDCYC no latency table (gen.py latency PLAN --inplace)"]
    bad = []
    for ln in lanes:
        lid = ln.get("id")
        row = lat.get(lid)
        if row is None:
            bad.append(f"FAIL FIXEDCYC lane {lid}: missing from the latency table")
            continue
        fx = int(ln.get("fixed_cycles", 0) or 0)
        if int(row.get("fixed", 0) or 0) != fx:
            bad.append(f"FAIL FIXEDCYC lane {lid}: fixed_cycles {fx} != latency row fixed {row.get('fixed')} (STALE_TABLE / counted twice)")
            continue
        if all(k in row for k in ("natural", "boundary", "stations", "fixed")):
            nat = int(row["boundary"]) + int(row["stations"]) + int(row["fixed"]) + int(row.get("clock_landing", 0) or 0)
            if int(row["natural"]) != nat:
                bad.append(f"FAIL FIXEDCYC lane {lid}: row natural {row['natural']} != boundary {row['boundary']} + stations "
                           f"{row['stations']} + fixed {row['fixed']} + clock_landing {row.get('clock_landing', 0)} = {nat}")
                continue
            if "pad" in row and int(row["cycles"]) != int(row["natural"]) + int(row["pad"]):
                bad.append(f"FAIL FIXEDCYC lane {lid}: row cycles {row['cycles']} != natural {row['natural']} + pad {row['pad']}")
    return _cap(bad, len(bad), "lanes") if bad else []


# ---------------------------------------------------------------- tools
def find_ref_tools(explicit=None):
    """explicit path, or "auto" = $OT_RT_CURRENT / <scratch>/claude/rt/current; None or "" = no reference (TOOLSTALE not run)"""
    if not explicit:
        return None
    cands = [None if explicit == "auto" else explicit, os.environ.get("OT_RT_CURRENT")] + [f"/srv/opentallas-scratch{n}/claude/rt/current" for n in ("2", "", "3")]
    for c in cands:
        if c and (Path(c) / "tools" / "die_plan").is_dir():
            return Path(c)
    return None


def check_toolstale(tree, ref=None, level="FAIL"):
    ref = find_ref_tools(ref)
    if ref is None:
        return []
    mine, theirs = Path(tree) / "tools" / "die_plan", ref / "tools" / "die_plan"
    try:
        if mine.resolve() == theirs.resolve():
            return []
    except OSError:
        return []
    stale, missing = [], []
    for f in sorted(theirs.glob("*.py")):
        if f.name.startswith("test_"):
            continue
        g = mine / f.name
        if not g.exists():
            missing.append(f.name)
        elif g.stat().st_size != f.stat().st_size or g.read_bytes() != f.read_bytes():
            if f.stat().st_mtime > g.stat().st_mtime + 1:
                stale.append(f.name)
    out = []
    if stale:
        out.append(f"{level} TOOLSTALE {len(stale)} tools/die_plan file(s) of {tree} are older than {ref}: {', '.join(stale[:8])}"
                   + (" ..." if len(stale) > 8 else "") + " (take tools from the live tree, or --skip TOOLSTALE)")
    if missing:
        out.append(f"WARN TOOLSTALE {len(missing)} tools/die_plan file(s) of {ref} absent in the tree: {', '.join(missing[:6])}")
    return out


# ---------------------------------------------------------------- elab walk
def _base(plan_path, ab, ab_path):
    b = ab.get("base")
    if ab_path and b and not Path(b).is_absolute():
        return str((Path(ab_path).parent / b).resolve())
    if b:
        return str((Path(plan_path).parent / b).resolve()) if not Path(b).is_absolute() else b
    return None


def leaf_paths(yjs, top, parent_variants=()):
    """{instance path: (master module, set(port names))} of every leaf / unknown / glue cell of the elaborated die, walked exactly
    like bind_elab.flatten (dissolved = a non-blackbox module cell), without nets (seconds, not minutes)."""
    mods = yjs["modules"]
    byname = {}
    for k, m in mods.items():
        byname.setdefault(m.get("attributes", {}).get("hdlname", k), k)
    pv = [(re.compile(r["inst"]), r["module"]) for r in parent_variants]
    out = {}
    stack = [(top, "")]
    while stack:
        mname, path = stack.pop()
        for c_name, c in mods[mname].get("cells", {}).items():
            c_name = re.sub(r"\$(/[^$:]*/)([^/$:]+:)", r"$\2", c_name)
            cpath = f"{path}.{c_name}" if path else c_name
            ct = c["type"]
            if ct in mods and "blackbox" not in mods[ct].get("attributes", {}):
                vm = next((mm for rx, mm in pv if rx.fullmatch(cpath)), None)
                if vm is not None and byname.get(vm):
                    ct = byname[vm]
                stack.append((ct, cpath))
                continue
            master = mods[ct].get("attributes", {}).get("hdlname", ct) if ct in mods else ct
            out[cpath] = (master, set(c.get("connections", {})))
    return out


def _tables(ab, base):
    files = [ab.get("land_r8")] + list(ab.get("land_r8_extra") or [])
    for f in files:
        if not f:
            continue
        p = Path(f) if Path(f).is_absolute() else Path(base) / f
        try:
            yield p, json.loads(p.read_text())
        except (OSError, ValueError):
            yield p, None


def check_rowsink(plan_path, plan, ab, ab_path, elab_dir, yjs=None):
    ep = Path(elab_dir) / "asbuilt.json"
    if yjs is None and not ep.is_file():
        return []
    if ab.get("land_align") != "r8" or not ab.get("land_r8"):
        return []
    if ab.get("compose"):
        return ["WARN ROWSINK skipped: asbuilt.compose renames table members (bind _compose_rename)"]
    base = _base(plan_path, ab, ab_path) or "."
    yjs = yjs or json.loads(ep.read_text())
    cells = leaf_paths(yjs, ab["top"], ab.get("substitute_parent", []))
    byid, bycanon = None, None
    out, n_bad, n_rows, n_skip = [], 0, 0, 0
    for p, js in _tables(ab, base):
        if js is None:
            out.append(f"FAIL ROWSINK R8 table {p} missing or unreadable")
            continue
        for m in js.get("members", []):
            if m["id"].startswith("INNER:"):
                continue
            n_rows += 1
            if not m.get("pad"):
                continue                           # a sink the RTL removed needs no pad (bind: gone_pad0)
            s = m["sink"]
            if "$" in s:
                n_skip += 1                        # numbered yosys cells: bind renumbers them (R8Renumber); not decidable here
                continue
            hit = cells.get(s)
            if hit is None:
                if byid is None:
                    byid = {}
                    for k, v in cells.items():
                        byid.setdefault(_sv_id(k), k)
                k2 = byid.get(_sv_id(s))
                hit = cells.get(k2) if k2 else None
            if hit is None:
                n_bad += 1
                out.append(f"FAIL ROWSINK {m['id']}: sink {s} is no leaf of the elaborated die (normalized u_r0_u_x form tried) [{p.name}]")
            elif m["sink_port"] not in hit[1]:
                n_bad += 1
                out.append(f"FAIL ROWSINK {m['id']}: sink {s} has no port {m['sink_port']} (master {hit[0]}) [{p.name}]")
    out = _cap(out, n_bad + sum(1 for x in out if "missing or unreadable" in x), "rows") if out else []
    if n_skip:
        out.append(f"WARN ROWSINK {n_skip} numbered `$` sink rows not decidable here (bind renumbers them)")
    return out


def check_modules(plan_path, plan, ab, ab_path, elab_dir, yjs=None):
    names = {}
    # plan hard-core modules are NOT checked: landing rings (qc_cland_*), station tails and kit wrappers are generated at bind time
    for r in ab.get("substitute_inst") or []:
        if isinstance(r, dict) and r.get("module"):
            names.setdefault(r["module"], f"asbuilt.substitute_inst {r.get('inst')}")
    for k in ("substitute", "sub_core_leaf"):
        v = ab.get(k)
        if isinstance(v, dict):
            for a, b in v.items():
                for x in (b if isinstance(b, list) else [b]):
                    if isinstance(x, str) and re.fullmatch(r"[A-Za-z_]\w*", x):
                        names.setdefault(x, f"asbuilt.{k} {a}")
    if not names:
        return []
    base = _base(plan_path, ab, ab_path)
    have = set()
    ep = Path(elab_dir) / "asbuilt.json" if elab_dir else None
    if yjs is None and ep is not None and ep.is_file():
        yjs = json.loads(ep.read_text())
    if yjs is not None:
        for k, m in yjs["modules"].items():
            have.add(k)
            have.add(m.get("attributes", {}).get("hdlname", k))
    if base:
        try:
            import bind_elab as E
            have |= set(E.module_index(ab.get("rtl_roots", ["rtl"]), ab.get("files", []) + ab.get("prefer", []), base))
        except Exception as exc:                  # noqa: BLE001  (an unreadable root is plan_gate_pre INPUT's finding)
            if yjs is None:
                return [f"WARN MODULES not checked: {exc}"]
    if not have:
        return []
    miss = sorted(n for n in names if n not in have and not any(h.endswith(n) for h in have if "$paramod" in h))
    return _cap([f"FAIL MODULES module {n} ({names[n]}) is in neither the RTL index nor the elaborated netlist" for n in miss],
                len(miss), "modules") if miss else []


def check_all(tree, plan_path, plan_raw, asbuilt=None, elab_dir=None, ref_tools=None, skip=(), toolstale_level="FAIL"):
    skip = {s.upper() for s in skip}
    out = []
    if "FIXEDCYC" not in skip:
        out += check_fixedcyc(plan_raw)
    if "TOOLSTALE" not in skip:
        out += check_toolstale(tree, ref_tools, toolstale_level)
    ab_path = asbuilt
    ab = json.loads(Path(asbuilt).read_text()) if asbuilt else plan_raw.get("asbuilt")
    if ab and elab_dir and (Path(elab_dir) / "asbuilt.json").is_file():
        yjs = None
        if "ROWSINK" not in skip or "MODULES" not in skip:
            yjs = json.loads((Path(elab_dir) / "asbuilt.json").read_text())
        if "ROWSINK" not in skip:
            out += check_rowsink(plan_path, plan_raw, ab, ab_path, elab_dir, yjs)
        if "MODULES" not in skip:
            out += check_modules(plan_path, plan_raw, ab, ab_path, elab_dir, yjs)
    elif ab and "MODULES" not in skip:
        out += check_modules(plan_path, plan_raw, ab, ab_path, None)
    return out
