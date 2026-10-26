#!/usr/bin/env python3
"""rom_infer_gate.py -- fail any synthesis that turns ROM content into standard-cell logic.

OWNER 2026-10-25 ~20:40: every ROM is a GENERATED memory macro (tools/mem_compiler/rom_gen.py: one LEF / Liberty /
behavioural view per shape, content = a per-instance via map).  ROM content is data and is never synthesised into
tile logic.  Yosys turns content into logic in two ways, both visible in the coarse netlist as a ``$mem`` /
``$mem_v2`` cell with no write port:

* ``proc_rom`` converts a ``case`` table of constants into a read-only memory;
* an ``initial`` / ``$readmemh`` array that is only read (``memory_collect`` folds the init into the cell).

``memory_map`` (ORFS synth.tcl, any size up to SYNTH_MEMORY_MAX_BITS) then flattens that ROM into a mux tree of
tie cells -- content baked into the netlist, so every content needs its own design and sign-off.

Inputs (either):
  --mem-json F [F ...]   ORFS ``$RESULTS_DIR/mem.json`` (written by synth.tcl after coarse synthesis, before
                         memory_map) of any run -- the post-hoc gate for kits and routes;
  --rtl F [F ...] --top T  elaborate with Yosys (``synth -run :fine``, the same stage ORFS dumps) and check; pass the
                         generated macros' ``*_bb.v`` so they stay black boxes, as ORFS does with ADDITIONAL_LEFS.

Verdict per design: FAIL if any read-only memory holds >= --min-bits bits (default 1024: a content table); smaller
read-only memories (a 16-entry FP4 decode, a one-hot table) are logic functions and are listed as INFO.  Initialised
RAMs (write port + INIT) are listed as WARN (silicon has no init).  Exit 1 on any FAIL.

DECLARED LOGIC (OWNER D-ROM-2 = (a), 2026-10-25 20:26): fixed math function tables (exp range tables, Sinkhorn seeds,
the KP4 GF(1024) inverse, ...) are identical in every instance and stay synthesised logic.  They are listed in
--allowlist (default tools/mem_compiler/rom_declared_logic.json): one entry per table = RTL module + table name +
SHA-256 of the Yosys INIT bit string + shape + reason.  A read-only memory >= --min-bits passes as DECLARED only when
its shape AND its content hash equal an entry's (and, when the cell carries a src attribute, its source file is the
entry's); the content hash is the identity, so the same table in any host module passes and any other content -- a
weight table, a calibration image, an edited math table -- still FAILs.

    python3 tools/mem_compiler/rom_infer_gate.py --mem-json run/results/asap7/X/base/mem.json
    python3 tools/mem_compiler/rom_infer_gate.py --rtl a.sv b.sv physical/asap7_memory_macros_v2/M/M_bb.v --top X \\
        --yosys "docker run --rm -v $PWD:$PWD -w $PWD openroad/orfs:asap7lock yosys"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

MIN_BITS = 1024
ALLOWLIST = Path(__file__).resolve().with_name("rom_declared_logic.json")


def _int(v) -> int:
    if isinstance(v, int):
        return v
    s = str(v)
    if s and set(s) <= {"0", "1"}:
        return int(s, 2)
    try:
        return int(s)
    except ValueError:
        return 0


def _has_init(v) -> bool:
    s = str(v or "")
    return bool(s) and set(s) - {"x", "z"} != set()


def memories(design: dict) -> list[dict]:
    """Yosys JSON -> [{module, cell, type, words, width, bits, rd_ports, wr_ports, init}] for every memory cell."""
    out = []
    for mname, m in (design.get("modules") or {}).items():
        for cname, c in (m.get("cells") or {}).items():
            t = c.get("type", "")
            if t not in ("$mem", "$mem_v2"):
                continue
            p = c.get("parameters") or {}
            words, width = _int(p.get("SIZE", 0)), _int(p.get("WIDTH", 0))
            out.append(dict(module=mname, cell=cname, type=t, words=words, width=width, bits=words * width,
                            rd_ports=_int(p.get("RD_PORTS", 0)), wr_ports=_int(p.get("WR_PORTS", 0)),
                            init=_has_init(p.get("INIT")), memid=str(p.get("MEMID", "")),
                            sha256=hashlib.sha256(str(p.get("INIT", "")).encode()).hexdigest()))
    # a cell's attribute src tells where the table came from
    for mname, m in (design.get("modules") or {}).items():
        for cname, c in (m.get("cells") or {}).items():
            for r in out:
                if r["module"] == mname and r["cell"] == cname:
                    r["src"] = (c.get("attributes") or {}).get("src", "")
    return out


def load_allowlist(path: Path | str | None = ALLOWLIST) -> list[dict]:
    """The declared-logic tables; every entry must carry module, table, sha256, words, width and a reason."""
    if path is None:
        return []
    entries = json.loads(Path(path).read_text())["tables"]
    for e in entries:
        miss = [k for k in ("id", "module", "table", "sha256", "words", "width", "reason") if not e.get(k)]
        if miss:
            raise SystemExit(f"{path}: entry {e.get('id', '?')} lacks {miss}")
        if len(e["sha256"]) != 64:
            raise SystemExit(f"{path}: entry {e['id']} sha256 must be the full 64-hex digest")
    return entries


def _src_file(src: str) -> str:
    return src.split("|")[0].split(":")[0].rsplit("/", 1)[-1] if src else ""


def declared(r: dict, allowlist: list[dict]) -> dict | None:
    for e in allowlist:
        if (e["words"], e["width"], e["sha256"]) != (r["words"], r["width"], r["sha256"]):
            continue
        f = _src_file(r.get("src", ""))
        if f and e.get("src") and f != e["src"]:
            continue
        return e
    return None


def classify(mems: list[dict], min_bits: int = MIN_BITS, allowlist: list[dict] | None = None) -> list[dict]:
    rows = []
    for r in mems:
        if r["wr_ports"] == 0:
            r["kind"] = "ROM"
            r["verdict"] = "FAIL" if r["bits"] >= min_bits else "INFO"
            e = declared(r, allowlist or []) if r["verdict"] == "FAIL" else None
            if e:
                r["verdict"], r["declared"] = "DECL", e["id"]
        elif r["init"]:
            r["kind"], r["verdict"] = "RAM+INIT", "WARN"
        else:
            r["kind"], r["verdict"] = "RAM", "OK"
        rows.append(r)
    return rows


def check_design(design: dict, min_bits: int = MIN_BITS, allowlist: list[dict] | None = None) -> dict:
    """allowlist None = no declared tables (the raw check); main() loads ALLOWLIST by default."""
    rows = classify(memories(design), min_bits, allowlist)
    fails = [r for r in rows if r["verdict"] == "FAIL"]
    decl = sorted({r["declared"] for r in rows if r["verdict"] == "DECL"})
    return dict(verdict="FAIL" if fails else "PASS", min_bits=min_bits, memories=rows,
                rom_bits_failed=sum(r["bits"] for r in fails), n_fail=len(fails), declared=decl)


YOSYS_SCRIPT = """{reads}
hierarchy -check -top {top}
synth -run :fine -top {top}
memory_collect
json -o {out}
"""


def elaborate(rtl: list[str], top: str, yosys: str, defines: list[str]) -> dict:
    with tempfile.TemporaryDirectory(prefix="romgate_") as td:
        out = Path(td) / "mem.json"
        dflags = " ".join(f"-D{d}" for d in defines)
        reads = "\n".join(f"read_verilog -sv {dflags} {shlex.quote(str(Path(f).resolve()))}" for f in rtl)
        ys = Path(td) / "gate.ys"
        ys.write_text(YOSYS_SCRIPT.format(reads=reads, top=top, out=out))
        cmd = shlex.split(yosys) + ["-q", "-s", str(ys)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            raise SystemExit(f"yosys failed ({p.returncode}): {(p.stdout + p.stderr)[-2000:]}")
        return json.loads(out.read_text())


def report_lines(name: str, res: dict) -> list[str]:
    lines = [f"{res['verdict']} {name}: {res['n_fail']} ROM(s) >= {res['min_bits']} bits synthesised as logic "
             f"({res['rom_bits_failed']} bits)"
             + (f"; declared logic: {', '.join(res['declared'])}" if res.get("declared") else "")]
    for r in res["memories"]:
        if r["verdict"] != "OK":
            tag = f" [{r['declared']}]" if r.get("declared") else f" sha256 {r['sha256'][:16]}" * (r["verdict"] == "FAIL")
            lines.append(f"  {r['verdict']:4} {r['kind']:8} {r['module']}.{r['memid'] or r['cell']} "
                         f"{r['words']}x{r['width']} = {r['bits']} b{tag}  {r.get('src', '')[:120]}")
    return lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mem-json", nargs="*", default=[])
    ap.add_argument("--rtl", nargs="*", default=[])
    ap.add_argument("--top")
    ap.add_argument("--define", action="append", default=[])
    ap.add_argument("--yosys", default="yosys", help="yosys command (>= 0.10: proc_rom / memory_v2)")
    ap.add_argument("--min-bits", type=int, default=MIN_BITS)
    ap.add_argument("--allowlist", default=str(ALLOWLIST), help="declared-logic tables (OWNER D-ROM-2 (a))")
    ap.add_argument("--no-allowlist", action="store_true", help="raw check: every ROM >= --min-bits FAILs")
    ap.add_argument("--json", type=Path, help="write the per-design verdicts here")
    a = ap.parse_args(argv)
    allow = [] if a.no_allowlist else load_allowlist(a.allowlist)
    results = {}
    for f in a.mem_json:
        try:
            results[f] = check_design(json.loads(Path(f).read_text()), a.min_bits, allow)
        except (OSError, ValueError) as e:
            results[f] = dict(verdict="ERROR", error=str(e), memories=[], n_fail=0, rom_bits_failed=0,
                              min_bits=a.min_bits)
    if a.rtl:
        if not a.top:
            ap.error("--rtl needs --top")
        results[a.top] = check_design(elaborate(a.rtl, a.top, a.yosys, a.define), a.min_bits, allow)
    if not results:
        ap.error("give --mem-json or --rtl/--top")
    for name, res in results.items():
        if res["verdict"] == "ERROR":
            print(f"ERROR {name}: {res['error']}")
        else:
            print("\n".join(report_lines(name, res)))
    if a.json:
        a.json.write_text(json.dumps(results, indent=1, sort_keys=True) + "\n")
    bad = [n for n, r in results.items() if r["verdict"] in ("FAIL", "ERROR")]
    print(f"rom_infer_gate: {len(results) - len(bad)}/{len(results)} PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
