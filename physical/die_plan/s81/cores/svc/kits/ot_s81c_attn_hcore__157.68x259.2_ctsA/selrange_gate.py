#!/usr/bin/env python3
"""selrange_gate (RTL-SELRANGE, COORD 10-24): fail a kit whose synthesised RTL has an out-of-range part-select / index.

Why: the ORFS Yosys slang frontend silently DROPS logic fed by an out-of-bounds select that only goes out of range
after loop unrolling (proven: csa31 in ot_s81eng_rr_n32.sv read a[31:24] of a 31-bit operand at k=3; slang tied
csa31[30:24] to 0 in every eng netlist while every Verilator bench passed).  Neither Verilator (-Wall: no SELRANGE
inside unrolled function/always loops) nor slang (0 warnings) reports that class; a constant out-of-range select at
module scope is a slang ERROR but only a warning for the built-in read_verilog frontend.  Yosys read_verilog
unrolls loops and evaluates functions per instance and DOES report every out-of-range select:
    <file>:<line>: Warning: Range [31:24] select out of bounds on signal `\\a': Setting 1 MSB bits to undef.
So the gate reads the kit's VERILOG_FILES with `read_verilog -sv -defer` (each module elaborated only with the
parameters it is actually instantiated with under DESIGN_NAME), runs `hierarchy -top DESIGN_NAME` and fails on any
such warning.  A select that is genuinely benign is waived only on its source line with a reason:
    ... a[i]  // selrange-ok: <why this never reaches synthesised logic>

Usage:
    selrange_gate.py KITDIR [--out KITDIR/selrange.json]          (reads KITDIR/config.mk; /work/... -> KITDIR/...)
    selrange_gate.py --top T [-D X] [-I DIR] [--filelist F] [files...]
    env OT_YOSYS / --yosys: the yosys binary (default: yosys on PATH)
Exit: 0 PASS, 1 FAIL (unwaived out-of-range select), 2 ERROR (yosys could not read / elaborate the sources, or the
checker crashed).  run_kit.sh stops on every nonzero exit, including NOT RUN (read_verilog rejects some constructs
slang accepts: a package import inside a module body, a defparam into a generate block, ...).
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

WARN = re.compile(r"^(?P<file>[^\s:][^:]*):(?P<line>\d+)(?:\.\d+-\d+\.\d+)?: Warning: "
                  r"(?P<msg>Range (?:select )?(?:\[[^\]]*\] )?(?:select )?out of bounds on signal `(?P<sig>[^']*)'.*)$")
WAIVE = re.compile(r"selrange-ok:\s*\S")
MODULE = re.compile(r"^\s*(?:macromodule|module)\s+(?:automatic\s+|static\s+)?([A-Za-z_][A-Za-z0-9_$]*)", re.M)
LIBCELL = re.compile(r"\bcell\s*\(\s*\"?([A-Za-z_][A-Za-z0-9_$]*)")
# hard macros: synthesis takes their liberty view (ORFS blackboxes ADDITIONAL_LIBS cells), so their behavioural
# models are skipped here (elaborating a 1024x256 behavioural SRAM costs minutes and is never synthesised)
MACRO_RE = r"^(?:ot_(?:sram|rom|regfile|rf)_(?:[a-z0-9]+_)?\d+x\d+|.*_ASAP7_75t_[RLS]L?$)"   # + std-cell models


def parse_config_mk(text):
    """export KEY = VALUE / KEY=VALUE / KEY ?= VALUE lines -> dict (last wins; backslash continuations joined)."""
    env = {}
    text = re.sub(r"\\\n", " ", text)
    for ln in text.splitlines():
        ln = ln.split("#", 1)[0].strip()
        m = re.match(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*[:?]?=\s*(.*)$", ln)
        if m:
            env[m.group(1)] = m.group(2).strip()
    return env


def _map(p, kit):
    """kit paths are written for the container (/work = KITDIR); outside the container map them back."""
    if kit is not None and p.startswith("/work/") and not Path(p).exists():
        return str(Path(kit) / p[len("/work/"):])
    return p


def kit_inputs(kit):
    kit = Path(kit).resolve()
    env = parse_config_mk((kit / "config.mk").read_text())
    files = [_map(f, kit) for f in shlex.split(env.get("VERILOG_FILES", ""))]
    incs = [_map(d, kit) for d in shlex.split(env.get("VERILOG_INCLUDE_DIRS", ""))]
    defs = [d[2:] for d in shlex.split(env.get("VERILOG_DEFINES", "")) if d.startswith("-D")]
    bb = set(shlex.split(env.get("SYNTH_BLACKBOXES", "")))
    for lib in shlex.split(env.get("ADDITIONAL_LIBS", "")):
        try:
            bb.update(LIBCELL.findall(Path(_map(lib, kit)).read_text(errors="replace")))
        except OSError:
            pass
    return dict(top=env.get("DESIGN_NAME"), files=files, incs=incs, defines=defs, blackboxes=sorted(bb),
                frontend=env.get("SYNTH_HDL_FRONTEND", "") or "read_verilog")


def _is_blackbox_file(f, blackboxes, macro_re=MACRO_RE):
    """a file whose every module is a hard macro / named blackbox -> read interface-only (-lib)."""
    try:
        mods = MODULE.findall(Path(f).read_text(errors="replace"))
    except OSError:
        return False
    return bool(mods) and all(m in blackboxes or re.match(macro_re, m) for m in mods)


INSIDE = re.compile(r"(\b[A-Za-z_][A-Za-z0-9_$.]*(?:\[[^\]\[]*\])?)\s+inside\s*\{([^{}]*)\}")


def _inside_rewrite(text):
    """read_verilog has no `inside`: `x inside {a, b}` -> `(x == a || x == b)` on the same line (ranges unsupported)."""
    def rep(m):
        items = [i.strip() for i in m.group(2).split(",")]
        if any(i.startswith("[") for i in items):
            return m.group(0)
        return "(" + " || ".join(f"{m.group(1)} == {i}" for i in items) + ")"
    return INSIDE.sub(rep, text)


def _prepare(files, td):
    """copies of files that use `inside`, rewritten for read_verilog (same name, same line numbers) under td."""
    out = []
    for i, f in enumerate(files):
        try:
            t = Path(f).read_text(errors="replace")
        except OSError:
            out.append(f)
            continue
        if INSIDE.search(t):
            d = Path(td) / f"ins{i}"
            d.mkdir()
            (d / Path(f).name).write_text(_inside_rewrite(t))
            out.append(str(d / Path(f).name))
        else:
            out.append(f)
    return out


def ys_script(top, files, incs, defines, blackboxes=(), overwrite=False):
    flags = " ".join(["-DSYNTHESIS"] + [f"-D{d}" for d in defines if d.split("=", 1)[0] != "SYNTHESIS"]
                     + [f"-I{d}" for d in incs])
    bb = set(blackboxes)
    # macro model files are not read at all (even `read_verilog -lib` simplifies the body: minutes for a behavioural
    # SRAM); `hierarchy` without -check keeps their instances as unknown cells, which is all this check needs
    ow = "-overwrite " if overwrite else ""
    L = [f"read_verilog -sv -defer {ow}{flags} {shlex.quote(f)}" for f in files if not _is_blackbox_file(f, bb)]
    L.append(f"hierarchy -top {top}")
    return "\n".join(L) + "\n"


def scan_log(log, files):
    """-> (hits, errors).  hits deduplicated by (file, line, message); waivers read from the source line."""
    by_name = {}
    for f in files:
        by_name.setdefault(Path(f).name, f)
    hits, seen, errors = [], {}, []
    for ln in log.splitlines():
        m = WARN.match(ln.strip())
        if m:
            f, line = m.group("file"), int(m.group("line"))
            key = (f, line, m.group("msg"))
            if key in seen:
                seen[key]["count"] += 1
                continue
            src = f if Path(f).exists() else by_name.get(Path(f).name, f)
            text = ""
            try:
                text = Path(src).read_text(errors="replace").splitlines()[line - 1]
            except (OSError, IndexError):
                pass
            h = dict(file=src, line=line, signal=m.group("sig").lstrip("\\"), msg=m.group("msg"), count=1,
                     source=text.strip()[:240], waived=bool(WAIVE.search(text)))
            seen[key] = h
            hits.append(h)
        elif ln.startswith("ERROR") or ": ERROR" in ln:
            errors.append(ln.strip())
    return hits, errors


def run(top, files, incs=(), defines=(), yosys=None, frontend=None, blackboxes=(), overwrite=False):
    yosys = yosys or os.environ.get("OT_YOSYS") or "yosys"
    uniq, seen = [], set()
    for f in files:                      # the same file named twice (two paths to one file) is read once
        k = os.path.realpath(f)
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    files = uniq
    # kits copy every source into one rtl/ dir; `include of a sibling .svh resolves there (as the ORFS run sees it)
    incs = list(incs) + [d for d in dict.fromkeys(os.path.dirname(os.path.abspath(f)) for f in files) if d not in incs]
    missing = [f for f in files if not Path(f).exists()]
    if missing:
        return dict(verdict="ERROR", top=top, errors=[f"missing source {m}" for m in missing[:10]], hits=[])
    with tempfile.TemporaryDirectory() as td:
        ys = Path(td) / "selrange.ys"
        ys.write_text(ys_script(top, _prepare(files, td), incs, defines, blackboxes, overwrite))
        p = subprocess.run([yosys, "-q", "-l", str(Path(td) / "y.log"), "-s", str(ys)], capture_output=True,
                           text=True)
        log = (Path(td) / "y.log").read_text(errors="replace") if (Path(td) / "y.log").exists() else ""
        log += "\n" + p.stdout + "\n" + p.stderr
    hits, errors = scan_log(log, files)
    if p.returncode != 0 and not errors:
        errors = [f"yosys exit {p.returncode}: " + (p.stderr.strip() or p.stdout.strip())[-400:]]
    bad = [h for h in hits if not h["waived"]]
    verdict = "ERROR" if p.returncode != 0 else ("FAIL" if bad else "PASS")
    return dict(schema="opentallas.selrange_gate.v1", verdict=verdict, top=top, frontend=frontend,
                files=len(files), unwaived=len(bad), waived=len(hits) - len(bad), hits=hits, errors=errors[:20])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("kit", nargs="?", help="kit dir with config.mk (VERILOG_FILES / DESIGN_NAME / ...)")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--top")
    ap.add_argument("--filelist", action="append", default=[])
    ap.add_argument("-D", dest="defines", action="append", default=[])
    ap.add_argument("-I", dest="incs", action="append", default=[])
    ap.add_argument("--yosys")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.kit and Path(a.kit).is_dir() and (Path(a.kit) / "config.mk").exists():
        k = kit_inputs(a.kit)
        out = a.out or str(Path(a.kit) / "selrange.json")
    else:
        files = ([a.kit] if a.kit else []) + a.files
        for fl in a.filelist:
            for t in Path(fl).read_text().split():
                if t.startswith("+incdir+"):
                    a.incs += [x for x in t[len("+incdir+"):].split("+") if x]
                elif t.startswith("+define+"):
                    a.defines += [x for x in t[len("+define+"):].split("+") if x]
                elif not t.startswith(("+", "-", "//")):
                    files.append(t)
        if not a.top:
            ap.error("--top is required without a kit dir")
        k = dict(top=a.top, files=files, incs=a.incs, defines=a.defines, frontend=None)
        out = a.out
    r = run(k["top"], k["files"], k["incs"], k["defines"], a.yosys, k.get("frontend"), k.get("blackboxes", ()))
    if out:
        Path(out).write_text(json.dumps(r, indent=1) + "\n")
    print(f"SELRANGE {r['verdict']} top={r['top']} files={len(k['files'])} unwaived={r.get('unwaived', 0)} "
          f"waived={r.get('waived', 0)}")
    for h in r["hits"]:
        if not h["waived"]:
            print(f"  {h['file']}:{h['line']}: {h['msg']}  [{h['source'][:120]}]")
    for e in r["errors"][:5]:
        print(f"  ERROR {e}")
    return {"PASS": 0, "FAIL": 1}.get(r["verdict"], 2)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:      # a crash of the checker is NOT RUN (2), never a FAIL verdict (1)
        print(f"SELRANGE ERROR checker crashed: {e!r}")
        sys.exit(2)
