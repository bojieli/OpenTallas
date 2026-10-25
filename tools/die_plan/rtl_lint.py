#!/usr/bin/env python3
"""rtl_lint: pre-synthesis RTL lint gate of every kit flow (FLOW-FIX 2026-10-25, canary finding F1).

Why: an identifier used in a port connection before its declaration (ot_s81eng_aq_n32: g_ec .ep_next(ep_next) above
'wire [10:0] ep_next') is an implicit 1-bit net.  yosys-slang leaves it undriven, so 8 exponent registers were tied to
0 in every eng_rr_e netlist, and the kit passed sdc_lint, SELRANGE, face_guard and port_bind.  Industry practice
(`default_nettype none` + lint UndrivenNet / ImplicitNet rules, run before synthesis): any implicit net, missing
module / port, undriven or multiply driven net fails the kit before synthesis.

Passes (yosys of the ORFS image, kit RTL exactly as config.mk lists it; macro liberty cells read as black boxes):
  1. read_slang -Wimplicit-net --compat=vcs (the synthesis frontend's semantics) ; hierarchy -check ; proc ; check
  2. read_verilog -sv -noautowire (implicit nets are errors)                   ; hierarchy -check ; proc ; check
FAIL on: any implicit net (either pass), any ERROR / missing module or port, any 'used but has no driver' net, any
multiple conflicting drivers, in the pass of the kit's own synthesis frontend (SYNTH_HDL_FRONTEND, default
read_verilog).  The other frontend's pass only contributes implicit nets (it may not parse every construct the kit's
frontend accepts); its other diagnostics are recorded as 'other_frontend'.

  rtl_lint.py KIT [--out KIT/rtl_lint.json]               inside the ORFS image (run_kit*.sh preflight)
  rtl_lint.py KIT --image openroad/orfs:asap7lock [--mem 8]  from a host (re-runs itself in docker)
Exit 0 PASS, 1 FAIL, 2 NOT RUN (tool error: the run_kit preflight treats it as a FAIL too).
"""
import argparse
import gzip
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

SCHEMA = "opentallas.rtl_lint.v1"
ORFS = "/OpenROAD-flow-scripts"
IMPLICIT_SLANG = re.compile(r"^(\S+?):(\d+):\d+: warning: implicit net '([^']+)' created")
IMPLICIT_RV = re.compile(r"(?:ERROR|Warning): Identifier `\\?([^']+)' is implicitly declared")
UNDRIVEN = re.compile(r"[Ww]arning: [Ww]ire (\S+) (?:\[\d+\] )?is used but has no driver")
MULTI = re.compile(r"[Ww]arning: multiple conflicting drivers for [^\n]*")
# 'Drivers conflicting with a constant' = yosys proc artifact of integer loop variables in clocked always blocks
# (a $dff with constant D and Q, e.g. ot_s81eng_aq_n32 'for (i ...)'): recorded, not a FAIL.
CONST_CONFLICT = re.compile(r"[Ww]arning: Drivers conflicting with a constant[^\n]*")
ERROR = re.compile(r"^ERROR: .*$", re.M)
SLANG_ERR = re.compile(r"^\S+:\d+:\d+: error: .*$", re.M)


class LintError(Exception):
    pass


def parse_config(kit):
    """config.mk -> {VAR: value} (the make subset the kit generators write)."""
    env = {}
    for line in (Path(kit) / "config.mk").read_text().splitlines():
        line = line.split("#", 1)[0].rstrip()
        m = re.match(r"^\s*(?:override\s+)?(?:export\s+)?([A-Z0-9_]+)\s*[:?+]?=\s*(.*)$", line)
        if m:
            env[m[1]] = m[2].strip()
    if "DESIGN_NAME" not in env or "VERILOG_FILES" not in env:
        raise LintError(f"{kit}/config.mk: no DESIGN_NAME / VERILOG_FILES")
    return env


def kpath(kit, p):
    return str(Path(kit) / p[len("/work/"):]) if p.startswith("/work/") else p


def macro_libs(env, kit):
    out = []
    for k in ("ADDITIONAL_LIBS", "TC_LIB_FILES"):
        for p in env.get(k, "").split():
            if p.endswith((".lib", ".lib.gz")) and "$(" not in p:
                q = kpath(kit, p)
                if q not in out:
                    out.append(q)
    # one timing view per macro is enough for a black-box interface (TT first)
    seen, keep = set(), []
    for q in sorted(out, key=lambda p: (not re.search(r"_tt[._]", Path(p).name, re.I), p)):
        stem = re.sub(r"_(tt|ff|ss|tc|bc|wc)?(_[0-9p]+v)?(_[0-9]+c)?\.lib(\.gz)?$", "", Path(q).name, flags=re.I)
        if stem not in seen:
            seen.add(stem)
            keep.append(q)
    return keep


def lib_cells(path):
    op = gzip.open if str(path).endswith(".gz") else open
    with op(path, "rt", errors="replace") as f:
        return re.findall(r"^\s*cell\s*\(\s*\"?([A-Za-z_][\w$]*)\"?\s*\)", f.read(), flags=re.M)


def src_modules(path):
    try:
        t = Path(path).read_text(errors="replace")
    except OSError:
        return []
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    t = re.sub(r"//[^\n]*", " ", t)
    return re.findall(r"^\s*(?:\(\*.*?\*\)\s*)?(?:module|macromodule)\s+(?:automatic\s+|static\s+)?([A-Za-z_][\w$]*)",
                      t, flags=re.M)


def frontend_of(env):
    return "slang" if env.get("SYNTH_HDL_FRONTEND", "").strip() == "slang" else "verilog"


def scripts(env, kit):
    """{frontend: yosys script} for the two passes."""
    top = env["DESIGN_NAME"]
    files = [kpath(kit, f) for f in env["VERILOG_FILES"].split()]
    miss = [f for f in files if not Path(f).is_file()]
    if miss:
        raise LintError(f"VERILOG_FILES missing: {miss[:5]}")
    incs = [kpath(kit, d) for d in env.get("VERILOG_INCLUDE_DIRS", "").split()]
    defs = env.get("VERILOG_DEFINES", "").split()
    if "-DSYNTHESIS" not in defs:
        defs.append("-DSYNTHESIS")
    srcmods = set()
    for f in files:
        srcmods |= set(src_modules(f))
    libs = [l for l in macro_libs(env, kit) if Path(l).is_file() and not set(lib_cells(l)) <= srcmods]
    head = [f"read_liberty -lib -ignore_miss_func {l}" for l in libs]
    params = env.get("VERILOG_TOP_PARAMS", "").split()
    params = list(zip(params[0::2], params[1::2]))
    tail = [f"hierarchy -check -top {top}", "proc", "check"]
    a = ["--keep-hierarchy", "--compat=vcs", "--ignore-assertions", "-Wimplicit-net", "--top", top]
    a += [f"-I{i}" for i in incs] + defs + files
    for k, v in params:
        a += ["-G", f"{k}={v}"]
    for m in env.get("SYNTH_BLACKBOXES", "").split():
        a += ["--blackboxed-module", m]
    for l in libs:
        for c in lib_cells(l):
            a += ["--blackboxed-module", c]
    slang = head + ["read_slang " + " ".join(shlex.quote(x) for x in a)] + tail
    rv = head + ["verilog_defaults -push", "verilog_defaults -add " + " ".join(defs)]
    rv += ["read_verilog -defer -sv -noautowire " + " ".join(f"-I{i}" for i in incs) + " " + f for f in files]
    rv += ["verilog_defaults -pop"] + [f"chparam -set {k} {v} {top}" for k, v in params] + tail
    return {"slang": "\n".join(slang) + "\n", "verilog": "\n".join(rv) + "\n"}


def parse(log, rc):
    """diagnostics of one pass (yosys log text, exit code)."""
    implicit = []
    for l in log.splitlines():
        m = IMPLICIT_SLANG.match(l.strip())
        if m:
            implicit.append(dict(file=re.sub(r"^(\.\./)*/?work/", "", m[1]), line=int(m[2]), net=m[3]))
        for n in IMPLICIT_RV.findall(l):
            implicit.append(dict(file=None, line=None, net=n))
    uniq = []
    for h in implicit:
        if h not in uniq:
            uniq.append(h)
    errors = ERROR.findall(log) + SLANG_ERR.findall(log)
    if rc and not errors:
        errors = [f"yosys exit {rc}"]
    return dict(rc=rc, implicit=uniq, undriven=sorted(set(UNDRIVEN.findall(log))), multi_driven=MULTI.findall(log),
                const_conflict=len(CONST_CONFLICT.findall(log)), errors=errors)


def verdict(env, passes):
    """FAIL reasons: implicit nets from any pass; errors / undriven / multi-driven of the kit-frontend pass."""
    fe = frontend_of(env)
    why = []
    for name, p in passes.items():
        for h in p["implicit"]:
            why.append(f"implicit net '{h['net']}'" + (f" at {h['file']}:{h['line']}" if h["file"] else "") +
                       f" ({name})")
    own = passes.get(fe)
    if own is None:
        why.append(f"{fe} pass NOT RUN")
    else:
        why += [f"{fe}: {e}" for e in own["errors"][:20]]
        why += [f"undriven net {n} ({fe})" for n in own["undriven"][:50]]
        why += [f"{fe}: {m}" for m in own["multi_driven"][:20]]
    return ("PASS" if not why else "FAIL"), why


def run_pass(script, path):
    Path(path).write_text(script)
    y = ORFS + "/tools/install/yosys/bin/yosys"
    y = y if os.access(y, os.X_OK) else (shutil.which("yosys") or "yosys")
    r = subprocess.run([y, "-q", "-l", str(path) + ".log", "-s", str(path)], capture_output=True, text=True)
    log = Path(str(path) + ".log").read_text(errors="replace") if Path(str(path) + ".log").is_file() else ""
    return parse(log + "\n" + r.stderr, r.returncode)


def lint(kit, out=None):
    kit = Path(kit)
    out = Path(out) if out else kit / "rtl_lint.json"
    wd = out.parent / "rtl_lint"
    wd.mkdir(parents=True, exist_ok=True)
    rec = dict(schema=SCHEMA, kit=str(kit), gate="FAIL_PREFLOOR lint",
               tool="yosys read_slang -Wimplicit-net | read_verilog -sv -noautowire; hierarchy -check; proc; check")
    try:
        env = parse_config(kit)
        rec.update(top=env["DESIGN_NAME"], frontend=frontend_of(env))
        passes = {fe: run_pass(s, wd / f"lint_{fe}.ys") for fe, s in scripts(env, kit).items()}
        rec["verdict"], rec["why"] = verdict(env, passes)
        rec["passes"] = passes
        rec["other_frontend"] = {fe: dict(errors=p["errors"][:5], undriven=p["undriven"][:10])
                                 for fe, p in passes.items() if fe != rec["frontend"]}
    except (LintError, OSError) as e:
        rec.update(verdict="NOT RUN", why=[str(e)])
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(f"RTL_LINT {rec['verdict']} top={rec.get('top')} frontend={rec.get('frontend')} "
          + "; ".join(rec["why"][:8]))
    return {"PASS": 0, "FAIL": 1}.get(rec["verdict"], 2)


def via_docker(kit, out, image, mem):
    kit = str(Path(kit).resolve())
    out = str(Path(out).resolve()) if out else kit + "/rtl_lint.json"
    if not out.startswith(kit + "/"):
        raise SystemExit("--out must be inside the kit for --image runs")
    me = str(Path(__file__).resolve())
    inner = (f"source {ORFS}/env.sh >/dev/null 2>&1; python3 -I /rtl_lint.py /work --out /work/{out[len(kit) + 1:]}; "
             "rc=$?; chown -R $HUID:$HGID /work/rtl_lint* 2>/dev/null; exit $rc")
    return subprocess.run(["docker", "run", "--rm", f"--memory={mem}g", f"--memory-swap={mem}g", "-v", f"{kit}:/work",
                           "-v", f"{me}:/rtl_lint.py:ro", "-e", f"HUID={os.getuid()}", "-e", f"HGID={os.getgid()}",
                           image, "bash", "-lc", inner]).returncode


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("kit")
    ap.add_argument("--out")
    ap.add_argument("--image", help="run inside this ORFS image via docker (host use)")
    ap.add_argument("--mem", type=int, default=8)
    a = ap.parse_args(argv)
    if a.image:
        return via_docker(a.kit, a.out, a.image, a.mem)
    return lint(a.kit, a.out)


if __name__ == "__main__":
    sys.exit(main())
