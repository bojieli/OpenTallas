#!/usr/bin/env python3
"""Wrapper around tools/risk_clock_loops_screen.py for the DS (V4.1 ROM) control screens.

It changes nothing in the tool's method; it only makes three blocks screenable:
  * resolve(): also reads the file of every --blackbox module (so ``blackbox`` finds it), puts SystemVerilog
    packages (*_pkg.sv) first, and substitutes a synthesis view from ../jobs/patched/<path> where one exists
    (spine / ROM adapter: the simulation-only $value$plusargs/$readmemh ROM loader replaced by a write port, so
    the ROM arrays stay variable instead of being constant-folded or rejected by Yosys);
  * before OpenROAD: strips the ``#(...)`` parameter list from instances of black-boxed modules in mapped.v
    (OpenSTA's Verilog reader rejects parameterised instances of undefined modules);
  * --blackbox modules (and DS_STUB=m1,m2: modules of untaken generate branches) are read as (* blackbox *)
    header stubs (../jobs/stubs/<m>.sv), so their bodies are never parsed (package imports Yosys rejects);
  * DS_CHPARAM=1: parameters set with ``chparam -set`` before ``hierarchy`` (Yosys 0.68 asserts on
    ``hierarchy -chparam`` for ot_hdc_v41x_idx_ring_port);
  * DS_DIE_UM=<d>: a fixed d x d um die instead of the utilisation floorplan (blocks whose IO pin count
    exceeds the utilisation die's perimeter).
"""
import os
import re
import subprocess
import sys
from pathlib import Path

SRC = Path.home() / "rcl-20261003/src"
sys.path.insert(0, str(SRC / "tools"))
import risk_clock_loops_screen as T  # noqa: E402

PATCH = Path("../jobs/patched")
_orig_resolve = T.resolve


def _patched(f: str) -> str:
    return str(PATCH / f) if (T.ROOT / PATCH / f).is_file() else f


STUBS = Path("../jobs/stubs")


def _strip_comments(t: str) -> str:
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    return re.sub(r"//[^\n]*", "", t)


def _stub(mod: str, files: list[str]) -> str | None:
    """A (* blackbox *) copy of ``mod``'s header (parameters + ports), so its body is never parsed."""
    for f in files:
        t = _strip_comments((T.ROOT / f).read_text(errors="replace"))
        m = re.search(rf"^\s*module\s+{mod}\b", t, re.M)
        if not m:
            continue
        i = m.end()
        depth, j, seen_port = 0, i, False
        while True:          # through the parameter list and the port list, to the ';'
            c = t[j]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            elif c == ";" and depth == 0:
                break
            j += 1
        out = T.ROOT / STUBS / f"{mod}.sv"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("(* blackbox *)\n" + t[m.start():j + 1].strip() + "\nendmodule\n")
        return str(STUBS / f"{mod}.sv")
    return None


def resolve(top, extra, listfile, incs, blackboxes):
    stub_only = [x for x in os.environ.get("DS_STUB", "").split(",") if x]
    bb = list(blackboxes) + stub_only
    need = _orig_resolve(top, extra, listfile, incs, bb)
    files = [l.strip() for l in (T.ROOT / listfile).read_text().splitlines() if l.strip() and not l.startswith("#")]
    # a file named after a black-boxed module is replaced by that module's header stub
    need = [f for f in need if Path(f).stem not in bb]
    for b in bb:
        if any(re.search(rf"^\s*module\s+{b}\b", (T.ROOT / f).read_text(errors="replace"), re.M) for f in need):
            continue
        st = _stub(b, list(dict.fromkeys(extra + files)))
        if st:
            need.append(st)
    pk = [f for f in need if f.endswith("_pkg.sv")]
    for f in files:   # packages imported by any needed file
        if f.endswith("_pkg.sv") and f not in pk:
            name = Path(f).stem
            if any(re.search(rf"\b{name}::", (T.ROOT / g).read_text(errors="replace")) for g in need):
                pk.append(f)
    need = pk + [f for f in need if f not in pk]
    return [_patched(f) for f in need]


T.resolve = resolve
_orig_tcl = T.tcl


def tcl(*a, **k):
    s = _orig_tcl(*a, **k)
    d = os.environ.get("DS_DIE_UM")
    if d:
        d = float(d)
        s = re.sub(r"initialize_floorplan -utilization \S+ -aspect_ratio 1 -core_space 2",
                   f'initialize_floorplan -die_area "0 0 {d} {d}" -core_area "2 2 {d - 2} {d - 2}"', s)
    return s


T.tcl = tcl
_orig_run = subprocess.run


def run(cmd, *a, **k):
    if cmd and str(cmd[0]).endswith("yosys") and os.environ.get("DS_CHPARAM"):
        ys = Path(cmd[-1])
        lines = []
        for l in ys.read_text().splitlines():
            m = re.match(r"hierarchy -check -top (\S+)((?: -chparam \S+ \S+)+)$", l)
            if m:
                kv = re.findall(r"-chparam (\S+) (\S+)", m.group(2))
                lines.append("chparam" + "".join(f" -set {k_} {v_}" for k_, v_ in kv) + f" {m.group(1)}")
                lines.append(f"hierarchy -check -top {m.group(1)}")
                l = f"rename -top {m.group(1)}"      # the derived $paramod top back to its name
            lines.append(l)
        ys.write_text("\n".join(lines) + "\n")
    if cmd and cmd[0] == "docker":
        w = Path([x for x in cmd if x.endswith(":/w:ro")][0].split(":")[0])
        mv = w / "mapped.v"
        text = mv.read_text()
        defined = set(re.findall(r"^module\s+(\S+)", text, re.M))
        out, i, n = [], 0, len(text)
        pat = re.compile(r"^(\s*)(\\?[\w$]+)\s*#\(", re.M)
        while True:
            m = pat.search(text, i)
            if not m:
                out.append(text[i:])
                break
            if m.group(2) in defined or m.group(2) in ("module",):
                out.append(text[i:m.end()])
                i = m.end()
                continue
            depth, j = 1, m.end()
            while depth:
                c = text[j]
                depth += (c == "(") - (c == ")")
                j += 1
            out.append(text[i:m.start()] + m.group(1) + m.group(2) + " ")
            i = j
        new = "".join(out)
        if new != text:
            mv.write_text(new)
    return _orig_run(cmd, *a, **k)


subprocess.run = run
# the tool's sources given with --source also get the patched view
argv = sys.argv[1:]
for idx, x in enumerate(argv[:-1]):
    if x == "--source":
        argv[idx + 1] = _patched(argv[idx + 1])
sys.argv = [sys.argv[0]] + argv
raise SystemExit(T.main())
