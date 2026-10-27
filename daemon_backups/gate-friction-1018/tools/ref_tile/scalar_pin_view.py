#!/usr/bin/env python3
"""Derived view: rename recipe-3 x[0] pins back to the scalar RTL port x (ROOT 2026-10-16, coordinator option (b)).

physical/common_flow/ot_pin_regs.tcl before e3919f90e declared every wrapper port [a:b], so a scalar RTL port x became
a one-bit bus and the routed tile exported pin x[0].  A die netlist built from the RTL binds .x(...), so these views
mis-bind.  This writes a DERIVED copy of a CLOSED view with only those pins renamed -- no geometry, no timing change:

  LEF      PIN x[0] / END x[0]  ->  PIN x / END x
  Liberty  type ("x") group removed; bus ("x") { bus_type : x; <bus attrs> pin ("x[0]") { ... } }  ->  pin ("x") { ... }
           (the bus-level attributes are dropped: the pin group repeats direction/capacitance), every "x[0]" -> "x"
  JSON     "x[0]" tokens -> "x" (child_lint text, pin lists); internal hierarchical names are untouched
  other    copied byte-identical (export_*.tcl/log are the parent's export record; provenance/ unchanged)

Only bases whose RTL declaration is SCALAR are renamed (a genuine [0:0] or [W-1:0] bus stays x[0]).  The copy gets
view_lineage.json (kind scalar_pin_rename): parent view + files sha256, original CLOSED job, the renamed ports with their
RTL declaration (file:line), and the gates:
  native   tools/hier_contract/native_pin_audit.audit_one on parent and derived: every number identical
  arcs     per-pin liberty metrics of the derived view == the parent's under the rename map (pinreg_audit.pin_metrics)
  pins     LEF pin set == TT/FF/SS liberty pin set; renamed pins absent as x[0]
  bind     the RTL module's port list (scalar x) == the derived LEF pins with their widths
The die binders accept it through tools/view_lineage.py verify (lineage SCALAR_PIN_RENAME).

  scalar_pin_view.py scan [--root REPO]                       # list views with single-[0] pins and the RTL verdict
  scalar_pin_view.py derive VIEW_DIR [--out DIR]              # default DIR = <kit>/views_scalar/<cell>
  scalar_pin_view.py check DERIVED_VIEW...                    # + OpenROAD parse and die_port_bind gates (docker)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/hier_contract"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def lef_pins(lef: Path) -> list[str]:
    return re.findall(r"^\s*PIN\s+(\S+)", lef.read_text(errors="replace"), flags=re.M)


def single_zero_bases(pins) -> list[str]:
    bits = {}
    for p in pins:
        m = re.fullmatch(r"(.+)\[(\d+)\]", p)
        if m:
            bits.setdefault(m.group(1), set()).add(int(m.group(2)))
    return sorted(b for b, s in bits.items() if s == {0} and b not in pins)


# ---------------------------------------------------------------- RTL port declarations
def _strip_comments(t: str) -> str:
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    return re.sub(r"//[^\n]*", "", t)


def _split_top(s: str) -> list[str]:
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return out


DECL = re.compile(r"^\s*(input|output|inout)\b(.*)$", re.S)


def rtl_ports(srcs: list[Path], module: str) -> dict | None:
    """{port: dict(dir, ranged, decl, file)} of module's ports (ANSI or non-ANSI); None when the module is not found"""
    for f in srcs:
        if not f.is_file():
            continue
        raw = f.read_text(errors="replace")
        t = _strip_comments(raw)
        m = re.search(rf"\bmodule\s+{re.escape(module)}\b", t)
        if not m:
            continue
        i = m.end()
        j = i
        while j < len(t) and t[j].isspace():
            j += 1
        if t.startswith("#", j):            # parameter list
            k = t.index("(", j)
            depth = 0
            for q in range(k, len(t)):
                depth += t[q] == "("
                depth -= t[q] == ")"
                if depth == 0:
                    j = q + 1
                    break
        k = t.find("(", j)
        body_start = None
        if k < 0:
            continue
        depth = 0
        for q in range(k, len(t)):
            depth += t[q] == "("
            depth -= t[q] == ")"
            if depth == 0:
                hdr, body_start = t[k + 1:q], q
                break
        if body_start is None:
            continue
        end = t.find("endmodule", body_start)
        body = t[body_start:end]
        ports, carry = {}, None
        items = [x.strip() for x in _split_top(hdr) if x.strip()]
        ansi = any(DECL.match(x) for x in items)
        def parse_decl(d, rest):
            names_part = re.sub(r"\[[^\]]*\]", " [] ", rest)       # ranges first: they may hold '=' ('!=', '==')
            names_part = names_part.split("=")[0]                     # then drop a default value
            rng = "[]" in names_part
            words = names_part.replace("[]", " ").split()
            name = [w for w in words if w not in ("wire", "logic", "reg", "var", "signed", "unsigned", "tri", "bit")]
            return d, bool(rng), (name[-1] if name else None)
        if ansi:
            for x in items:
                dm = DECL.match(x)
                if dm:
                    d, ranged, n = parse_decl(dm.group(1), dm.group(2))
                    carry = (d, ranged)
                elif carry:
                    n = re.sub(r"\[[^\]]*\]", " ", x).split()[-1]
                    d, ranged = carry
                else:
                    continue
                if n:
                    ports[n] = dict(dir=d, ranged=ranged, decl=" ".join(x.split())[:120], file=str(f.relative_to(ROOT)) if f.is_relative_to(ROOT) else str(f))
        else:
            for st in body.split(";"):
                dm = DECL.match(st.strip())
                if not dm:
                    continue
                rest = dm.group(2)
                rng = re.findall(r"^\s*(?:(?:wire|logic|reg|signed|unsigned)\s+)*(\[[^\]]*\])", rest)
                names = [re.sub(r"\[[^\]]*\]", "", n).split()[-1] for n in _split_top(re.sub(r"^\s*(?:(?:wire|logic|reg|signed|unsigned)\s+)*(\[[^\]]*\]\s*)?", "", rest)) if n.strip()]
                for n in names:
                    ports[n] = dict(dir=dm.group(1), ranged=bool(rng), decl=" ".join(st.split())[:120], file=str(f.relative_to(ROOT)) if f.is_relative_to(ROOT) else str(f))
        return ports
    return None


def kit_srcs(kit: Path) -> tuple[list[Path], str | None]:
    env = (kit / "kit.env").read_text() if (kit / "kit.env").is_file() else ""
    srcs = re.search(r"^SRCS=(.*)$", env, flags=re.M)
    top = re.search(r"^TOP=(\S+)", env, flags=re.M)
    files = [ROOT / x for s in shlex.split(srcs.group(1)) for x in s.split()] if srcs else []
    return files, top.group(1) if top else None


def rtl_verdict(view: Path, cell: str, bases: list[str]) -> dict:
    kit = view.parent.parent
    srcs, top = kit_srcs(kit)
    ports = rtl_ports(srcs, cell) or (rtl_ports(srcs, top) if top else None)
    out = {}
    for b in bases:
        if ports is None:
            out[b] = dict(verdict="unknown", why=f"module {cell} not found in {kit.name}/kit.env SRCS")
        elif b not in ports:
            out[b] = dict(verdict="unknown", why=f"port {b} not declared in module {cell}")
        else:
            out[b] = dict(verdict="bus" if ports[b]["ranged"] else "scalar", **ports[b])
    return out


# ---------------------------------------------------------------- the rename
def tok_re(b: str):
    return re.compile(r'(?:(?<=\s)|(?<=")|(?<=\()|(?<=,)|^)' + re.escape(b) + r"\[0\](?![\w\[])", re.M)


def rename_lef(t: str, bases) -> str:
    for b in bases:
        t, n = re.subn(rf"^(\s*)(PIN|END)\s+{re.escape(b)}\[0\]\s*$", lambda m: f"{m.group(1)}{m.group(2)} {b}", t, flags=re.M)
        assert n == 2, f"LEF {b}[0]: {n} PIN/END lines"
    return t


def _group_end(t: str, start: int) -> int:
    """index just past the } closing the group whose { is the first after start"""
    k = t.index("{", start)
    depth = 0
    for q in range(k, len(t)):
        if t[q] == "{":
            depth += 1
        elif t[q] == "}":
            depth -= 1
            if depth == 0:
                return q + 1
    raise ValueError("unbalanced liberty group")


def rename_lib(t: str, bases) -> str:
    for b in bases:
        qb = re.escape(b)
        m = re.search(rf'^[ \t]*type\s*\(\s*"?{qb}"?\s*\)\s*\{{', t, flags=re.M)
        if m:
            e = _group_end(t, m.start())
            if t[e:e + 1] == "\n":
                e += 1
            t = t[:m.start()] + t[e:]
        m = re.search(rf'^([ \t]*)bus\s*\(\s*"?{qb}"?\s*\)\s*\{{', t, flags=re.M)
        assert m, f"lib: bus ({b}) missing"
        e = _group_end(t, m.start())
        grp = t[m.start():e]
        pm = re.search(rf'^[ \t]*pin\s*\(\s*"{qb}\[0\]"\s*\)\s*\{{', grp, flags=re.M)
        assert pm, f"lib: pin ({b}[0]) missing in bus ({b})"
        pe = _group_end(grp, pm.start())
        pin = grp[pm.start():pe]
        assert not re.search(r"^[ \t]*pin\s*\(", grp[pe:], flags=re.M), f"lib: bus ({b}) holds more than one pin"
        pin = re.sub(rf'pin\s*\(\s*"{qb}\[0\]"\s*\)', f'pin("{b}")', pin, count=1)
        t = t[:m.start()] + m.group(1) + pin.lstrip() + t[e:]
        t = re.sub(rf"(?<![\w\[/.]){qb}\[0\](?![\w\[])", b, t)
        assert not re.search(rf"(?<![\w\[/.]){qb}\[0\]", t), f"lib: {b}[0] still referenced"
    return t


def rename_json_text(t: str, bases) -> str:
    for b in bases:
        t = tok_re(b).sub(b, t)
    return t


def lib_pins(lib: Path) -> set:
    t = lib.read_text(errors="replace")
    return set(re.findall(r'^\s*pin\s*\(\s*"?([^")\s]+)"?\s*\)', t, flags=re.M)) - {"VDD", "VSS"}


def derive(view: Path, out: Path | None = None) -> dict:
    import view_lineage as VL
    view = view.resolve()
    cell = view.name
    pins = lef_pins(view / f"{cell}.lef")
    bases = single_zero_bases(pins)
    rv = rtl_verdict(view, cell, bases)
    ren = [b for b in bases if rv[b]["verdict"] == "scalar"]
    if not ren:
        return dict(cell=cell, view=str(view.relative_to(ROOT)), renamed=[], rtl=rv, verdict="NOTHING_TO_RENAME")
    out = (out or view.parent.parent / "views_scalar" / cell).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    files = {}
    for f in sorted(view.rglob("*")):
        if not f.is_file() or f.name == VL.RECEIPT:
            continue
        rel = f.relative_to(view)
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if rel.parts[0] == "provenance" or f.suffix in (".tcl", ".log", ".gz"):
            shutil.copy2(f, dst)
            how = "copied"
        elif f.suffix == ".lef":
            dst.write_text(rename_lef(f.read_text(errors="replace"), ren))
            how = "renamed"
        elif f.suffix == ".lib":
            dst.write_text(rename_lib(f.read_text(errors="replace"), ren))
            how = "renamed"
        elif f.suffix == ".json":
            dst.write_text(rename_json_text(f.read_text(errors="replace"), ren))
            json.loads(dst.read_text())
            how = "renamed" if dst.read_bytes() != f.read_bytes() else "copied"
        else:
            shutil.copy2(f, dst)
            how = "copied"
        files[str(rel)] = dict(how=how, from_sha256=sha(f), sha256=sha(dst))
    # ---- gates
    why = []
    import pinreg_audit as PA
    import native_pin_audit as NPA
    nat_p = NPA.audit_one((str(view), cell, "."))
    nat_d = NPA.audit_one((str(out), cell, "."))
    rn = lambda x: (x[:-3] if isinstance(x, str) and x.endswith("[0]") and x[:-3] in ren else x)
    norm = lambda r: {k: (rename_json_text(v, ren) if isinstance(v, str) else v) for k, v in r.items() if k not in ("view",)}
    if norm(nat_p) != {k: v for k, v in nat_d.items() if k != "view"}:
        a_, b_ = norm(nat_p), {k: v for k, v in nat_d.items() if k != "view"}
        why.append("native audit differs: " + str({k: (a_.get(k), b_.get(k)) for k in set(a_) | set(b_) if a_.get(k) != b_.get(k)}))
    arcs = {}
    for c in ("tt", "ff", "ss"):
        lp, ld = view / f"{cell}_{c}.lib", out / f"{cell}_{c}.lib"
        if not lp.is_file():
            continue
        mp = PA.pin_metrics(PA.parse_lib(lp), {})
        md = PA.pin_metrics(PA.parse_lib(ld), {})
        mp = {rn(n): {k: ([rn(x) for x in v] if isinstance(v, list) else v) for k, v in m.items()} for n, m in mp.items()}
        arcs[c] = "identical" if mp == md else "DIFFER"
        if mp != md:
            why.append(f"{c} liberty pin metrics differ under the rename")
        lpins = lib_pins(ld)
        lef_d = set(lef_pins(out / f"{cell}.lef")) - {"VDD", "VSS"}
        if lpins != lef_d:
            why.append(f"{c} liberty pins != LEF pins ({sorted(lpins ^ lef_d)[:6]})")
    left = [b for b in ren if f"{b}[0]" in set(lef_pins(out / f"{cell}.lef"))]
    if left:
        why.append(f"LEF still has {left}")
    # bind: RTL port list vs derived LEF pins
    srcs, top = kit_srcs(view.parent.parent)
    ports = rtl_ports(srcs, cell) or (rtl_ports(srcs, top) if top else {}) or {}
    dpins = set(lef_pins(out / f"{cell}.lef")) - {"VDD", "VSS"}
    dbases = {re.sub(r"\[\d+\]$", "", p) for p in dpins}
    scalar_ok = all(b in dpins and not ports[b]["ranged"] for b in ren if b in ports)
    missing = sorted(set(ports) - dbases)
    extra = sorted(dbases - set(ports))
    bind = dict(rtl_ports=len(ports), lef_bases=len(dbases), missing_in_lef=missing[:10], not_in_rtl=extra[:10], scalars_bind=scalar_ok)
    if not scalar_ok or missing or extra:
        why.append(f"bind: {bind}")
    # lineage
    ab = json.loads((view / "abstract.json").read_text()) if (view / "abstract.json").is_file() else {}
    m = re.search(r"/closure-loop/([^/]+)/", ab.get("orfs_dir", ""))
    job = m.group(1) if m else (ab.get("verdict") or {}).get("job") if isinstance(ab.get("verdict"), dict) else None
    ok_c, txt_c, info = VL.closed_job(job or "")
    if not ok_c:
        why.append(txt_c)
    rec = dict(schema=VL.SCHEMA, kind="scalar_pin_rename", master=cell, view=str(out.relative_to(ROOT)),
               parent_view=str(view.relative_to(ROOT)), parent_files=VL.view_files(view, cell), original_job=job, closed=info,
               renamed=[dict(pin=f"{b}[0]", to=b, rtl=rv[b]) for b in ren],
               kept_bus=[dict(pin=f"{b}[0]", rtl=rv[b]) for b in bases if b not in ren],
               gates=dict(native_parent=nat_p, native_derived=nat_d, liberty_pin_metrics=arcs, bind=bind),
               file_map=files, tool="tools/ref_tile/scalar_pin_view.py", tool_sha256=sha(Path(__file__)),
               rule="pin names only (recipe-3 ot_pin_regs [0:0] defect, fixed e3919f90e); geometry and arcs unchanged",
               files=VL.view_files(out, cell), verdict="PASS" if not why else "FAIL", why=why)
    (out / VL.RECEIPT).write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def lef_dirs(lef: Path) -> dict:
    """{pin: direction} from LEF PIN blocks"""
    out, cur = {}, None
    for ln in lef.read_text(errors="replace").splitlines():
        m = re.match(r"^\s*PIN\s+(\S+)", ln)
        if m:
            cur = m.group(1)
            continue
        m = re.match(r"^\s*DIRECTION\s+(\w+)", ln)
        if m and cur:
            out[cur] = m.group(1).lower()
        if re.match(r"^\s*END\s+", ln) and cur and ln.split()[-1] == cur:
            cur = None
    return out


def die_bind_check(view: Path, tmp: Path) -> dict:
    """die_port_bind of a one-instance die (every derived LEF pin a die port of its LEF width) against the kit's RTL"""
    import subprocess
    cell = view.name
    kit = view.parent.parent
    srcs, _ = kit_srcs(kit)
    dirs = lef_dirs(view / f"{cell}.lef")
    width = {}
    for p_, d_ in dirs.items():
        if p_ in ("VDD", "VSS") or d_ not in ("input", "output", "inout"):
            continue
        m = re.fullmatch(r"(.+)\[(\d+)\]", p_)
        base, bit = (m.group(1), int(m.group(2))) if m else (p_, None)
        w = width.setdefault(base, [d_, -1, bit is None])
        if bit is not None:
            w[1] = max(w[1], bit)
    decl = [f"  {d_} {'' if scalar else f'[{hi}:0] '}{base};" for base, (d_, hi, scalar) in sorted(width.items())]
    die = tmp / "die.v"
    env = (kit / "kit.env").read_text() if (kit / "kit.env").is_file() else ""
    pm = re.search(r"^PARAMS=\((.*)\)", env, flags=re.M)
    params = re.findall(r"--param\s+(\w+)=(\S+)", pm.group(1)) if pm else []
    ptxt = (" #(" + ", ".join(f".{k}({v})" for k, v in params) + ")") if params else ""
    die.write_text("module scalar_bind_check(" + ", ".join(sorted(width)) + ");\n" + "\n".join(decl) + "\n  " + cell + ptxt + " u (" +
                   ", ".join(f".{b}({b})" for b in sorted(width)) + ");\nendmodule\n")
    out = tmp / "bind.json"
    cmd = [sys.executable, str(ROOT / "tools/die_port_bind.py"), str(die), "--top", "scalar_bind_check", "--rtl-root", str(tmp / "none"),
           "--out", str(out)] + [x for f in srcs for x in ("--rtl-file", str(f))]
    (tmp / "none").mkdir(exist_ok=True)
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    rec = json.loads(out.read_text()) if out.is_file() else {}
    counts = rec.get("counts") or {k: v for k, v in rec.items() if isinstance(v, int)}
    return dict(rc=r.returncode, counts=counts, tail=(r.stdout + r.stderr)[-600:])


def scalar_pin_lint(lef: Path, kit: Path, cell: str) -> list[str]:
    """export lint (ref_tile.py export): every RTL-scalar port whose exported LEF pin is x[0] (the pre-e3919f90e
    recipe-3 wrapper defect); [] when the module cannot be parsed (the bind gates still apply downstream)"""
    srcs, top = kit_srcs(kit)
    ports = rtl_ports(srcs, cell) or (rtl_ports(srcs, top) if top else None) or {}
    pins = set(lef_pins(lef))
    return sorted(f"{n}[0]" for n, d in ports.items() if not d["ranged"] and n not in pins and f"{n}[0]" in pins)


def name_bind(view: Path) -> dict:
    """physical pin-NAME bind: a die DEF/netlist names a scalar RTL port x and a bus port x[i]; the LEF must agree"""
    cell = view.name
    srcs, top = kit_srcs(view.parent.parent)
    ports = rtl_ports(srcs, cell) or (rtl_ports(srcs, top) if top else {}) or {}
    pins = set(lef_pins(view / f"{cell}.lef"))
    bad = []
    for n, d in sorted(ports.items()):
        if d["ranged"]:
            if n in pins or not any(p.startswith(n + "[") for p in pins):
                bad.append(f"{n}: RTL bus, LEF has {'scalar ' + n if n in pins else 'no ' + n + '[i]'}")
        elif n not in pins:
            bad.append(f"{n}: RTL scalar, LEF has {n + '[0]' if n + '[0]' in pins else 'no pin'}")
    return dict(rtl_ports=len(ports), mismatches=len(bad), first=bad[:8], ok=not bad)


def sta_parse_check(views: list[Path], tmp: Path) -> dict:
    """OpenROAD (orfs asap7lock) reads each derived LEF + TT/FF/SS liberty; liberty and LEF pin sets are compared there"""
    import subprocess
    tcl = ["set P /OpenROAD-flow-scripts/flow/platforms/asap7", "read_lef $P/lef/asap7_tech_1x_201209.lef"]
    for v in views:
        rel = v.relative_to(ROOT)
        tcl.append(f"read_lef /src/{rel}/{v.name}.lef")
        for c in ("tt", "ff", "ss"):
            if (v / f"{v.name}_{c}.lib").is_file():
                tcl.append(f"if {{[catch {{read_liberty /src/{rel}/{v.name}_{c}.lib}} e]}} {{puts \"SPV_FAIL {v.name} {c} $e\"}} else {{puts \"SPV_OK {v.name} {c} [llength [get_lib_pins -quiet */{v.name}/*]]\"}}")
    (tmp / "parse.tcl").write_text("\n".join(tcl) + "\n")
    r = subprocess.run(["docker", "run", "--rm", "-v", f"{ROOT}:/src:ro", "-v", f"{tmp}:/t", "openroad/orfs:asap7lock", "bash", "-lc",
                        "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /t/parse.tcl"],
                       capture_output=True, text=True, timeout=1800)
    res = {}
    for ln in r.stdout.splitlines():
        m = re.match(r"SPV_(OK|FAIL) (\S+) (\w+) ?(.*)", ln)
        if m:
            res.setdefault(m.group(2), {})[m.group(3)] = m.group(1) + (" " + m.group(4) if m.group(4) else "")
    return res


def check(views: list[Path]) -> int:
    import tempfile
    import view_lineage as VL
    views = [v.resolve() for v in views]
    tmp = Path(tempfile.mkdtemp(prefix="spv_"))
    parse = sta_parse_check(views, tmp)
    bad = 0
    for v in views:
        rp = v / VL.RECEIPT
        rec = json.loads(rp.read_text())
        t = tmp / v.name
        t.mkdir(exist_ok=True)
        bind = die_bind_check(v, t)
        p_ = parse.get(v.name, {})
        ok_parse = bool(p_) and all(x.startswith("OK") for x in p_.values())
        ok_bind = bind["rc"] == 0
        rec["gates"]["export_parse"] = dict(tool="openroad (orfs asap7lock) read_lef + read_liberty", corners=p_, ok=ok_parse)
        rec["gates"]["die_port_bind"] = dict(tool="tools/die_port_bind.py one-instance die vs kit SRCS", **bind, ok=ok_bind)
        nb_d, nb_p = name_bind(v), name_bind(ROOT / rec["parent_view"])
        rec["gates"]["pin_name_bind"] = dict(rule="RTL scalar x -> LEF pin x; RTL bus x -> LEF pins x[i]", derived=nb_d, parent=nb_p)
        ok_bind = ok_bind and nb_d["ok"]
        why = [w for w in rec.get("why", []) if not w.startswith(("export parse", "die_port_bind"))]
        if not ok_parse:
            why.append(f"export parse: {p_}")
        if not ok_bind:
            why.append(f"die_port_bind rc {bind['rc']}: {bind['counts']}; pin-name bind {nb_d['first']}")
        rec["why"], rec["verdict"] = why, "PASS" if not why else "FAIL"
        rp.write_text(json.dumps(rec, indent=1) + "\n")
        print(f"{rec['verdict']} {rec['view']} parse {p_} bind rc {bind['rc']} name-bind derived {nb_d['mismatches']} parent {nb_p['mismatches']}")
        bad += rec["verdict"] != "PASS"
    return 1 if bad else 0


def find_views(root: Path):
    for lef in sorted(root.glob("physical/ref_tile/*/views/*/*.lef")):
        d = lef.parent
        if lef.stem == d.name and (d / f"{d.name}_tt.lib").is_file():
            yield d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("--json")
    ck = sub.add_parser("check")
    ck.add_argument("views", nargs="+")
    dv = sub.add_parser("derive")
    dv.add_argument("view")
    dv.add_argument("--out")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        return check([Path(v) for v in a.views])
    if a.cmd == "scan":
        rows = []
        for d in find_views(ROOT):
            b = single_zero_bases(lef_pins(d / f"{d.name}.lef"))
            if b:
                rv = rtl_verdict(d, d.name, b)
                rows.append(dict(view=str(d.relative_to(ROOT)), cell=d.name, scalar=[x for x in b if rv[x]["verdict"] == "scalar"],
                                 bus=[x for x in b if rv[x]["verdict"] == "bus"], unknown={x: rv[x]["why"] for x in b if rv[x]["verdict"] == "unknown"}))
        for r in rows:
            print(f"{r['view']}: scalar {r['scalar']} bus {r['bus']} unknown {list(r['unknown'])}")
        if a.json:
            Path(a.json).write_text(json.dumps(rows, indent=1) + "\n")
        return 0
    r = derive(Path(a.view), Path(a.out) if a.out else None)
    print(json.dumps({k: r.get(k) for k in ("master", "view", "verdict", "why")} | {"renamed": [x["to"] for x in r.get("renamed", [])] if r.get("renamed") and isinstance(r["renamed"][0], dict) else r.get("renamed")}))
    return 0 if r.get("verdict") in ("PASS", "NOTHING_TO_RENAME") else 1


if __name__ == "__main__":
    sys.exit(main())
