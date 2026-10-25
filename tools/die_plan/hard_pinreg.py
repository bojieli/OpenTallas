#!/usr/bin/env python3
"""hard_pinreg: the REGISTERED-PIN hard-partition rule (COORD 2026-10-25 11:31, PATH-QC-PHYB; standard hard-PHY practice).

A plan type marked `hard` whose single hard core declares `"registered_pins": true` (contents[] or hard_cores[] entry,
with its liberty view(s) in `lib`) is the bare macro: the macro's own registered boundary pins (e.g. a UCIe / SerDes
PHY's FDI) ARE the partition's boundary registers.  The binder (tools/die_plan/bind.py) then emits NO ot_dp_st
station on that partition's side of any crossing; the neighbour keeps its station.  The claim must be visible in the
macro's timing model, so this checker fails closed unless, in EVERY lib given:

  * every non-clock input pin / bus has a setup_* AND a hold_* arc related to a clock pin of the cell;
  * every output pin / bus has a clock-to-output arc (rising_edge / falling_edge) related to a clock pin;
  * (bind) every as-built port of the leaf that crosses the boundary exists in the lib with the as-built width;
    declared bump_ports (the hard IP's line side, absent from the as-built die) are not FDI pins and are skipped.

    python3 tools/die_plan/hard_pinreg.py LIB [LIB ...]          # print the per-pin verdict of a liberty view

Used by check.py (G0: plan-level, lib only) and bind.py (bind: lib + as-built leaf ports).
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CLOCK_TO_Q = ("rising_edge", "falling_edge")


def _block(txt, i):
    """the text of the {...} block whose '{' is at or after i (balanced)"""
    j = txt.index("{", i)
    d = 0
    for k in range(j, len(txt)):
        c = txt[k]
        if c == "{":
            d += 1
        elif c == "}":
            d -= 1
            if d == 0:
                return txt[j + 1:k], k + 1
    raise ValueError("unbalanced liberty braces")


def parse_lib(path):
    """{cell: {pin: dict(dir, clock, width, arcs=[(related_pin, timing_type)])}} for pin () / bus () groups of each
    cell (bus width from its bus_type)."""
    txt = Path(path).read_text(errors="replace")
    txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
    widths = {m.group(1): int(re.search(r"bit_width\s*:\s*(\d+)", b).group(1))
              for m in re.finditer(r"\btype\s*\(\s*(\w+)\s*\)", txt)
              for b in [_block(txt, m.end())[0]] if re.search(r"bit_width\s*:\s*(\d+)", b)}
    cells = {}
    for m in re.finditer(r"\bcell\s*\(\s*\"?([\w$]+)\"?\s*\)", txt):
        body, _ = _block(txt, m.end())
        pins = {}
        k = 0
        while True:
            pm = re.compile(r"\b(pin|bus)\s*\(\s*\"?([\w$\[\]]+)\"?\s*\)\s*\{").search(body, k)
            if not pm:
                break
            pb, k = _block(body, pm.start())
            dm = re.search(r"direction\s*:\s*(\w+)", pb)
            w = 1
            if pm.group(1) == "bus":
                bt = re.search(r"bus_type\s*:\s*\"?(\w+)\"?", pb)
                w = widths.get(bt.group(1)) if bt else None
            rel = re.findall(r"related_pin\s*:\s*\"?([\w$]+)\"?", pb)
            tt = re.findall(r"timing_type\s*:\s*\"?(\w+)\"?", pb)
            pins[pm.group(2)] = dict(dir=dm.group(1) if dm else None, clock=bool(re.search(r"\bclock\s*:\s*true", pb)),
                                     width=w, arcs=list(zip(rel, tt)))
        cells[m.group(1)] = pins
    return cells


def resolve(p, bases=()):
    """a repo-relative / plan-relative view path -> existing Path, or None"""
    q = Path(p)
    if q.is_absolute():
        return q if q.is_file() else None
    for b in list(bases) + [REPO]:
        if b is not None and (Path(b) / q).is_file():
            return Path(b) / q
    return None


def libs_of(entry):
    v = entry.get("lib")
    if not v:
        return []
    return [v] if isinstance(v, str) else list(v)


def lib_views(entry, bases=()):
    """[(declared name, Path | None)]: the declared lib(s) plus, for a <cell>_<corner>.lib, every sibling corner view
    present (<cell>_tt/ff/ss.lib): the registered-pin claim must hold at every sign-off corner (TT setup, FF hold)."""
    out = []
    for lb in libs_of(entry):
        f = resolve(lb, bases)
        out.append((lb, f))
        m = re.match(r"(.*)_(tt|ff|ss)\.lib$", lb)
        if f is not None and m:
            for c in ("tt", "ff", "ss"):
                sib = f.with_name(re.sub(r"_(tt|ff|ss)\.lib$", f"_{c}.lib", f.name))
                name = f"{m.group(1)}_{c}.lib"
                if sib.is_file() and sib != f and name not in {n for n, _ in out}:
                    out.append((name, sib))
    return out


def check_lib(path, cell, ports=None, skip=()):
    """errors of one liberty view against the registered-pin claim.  ports: {name: (dir, width)} of the as-built
    leaf (bind) -- each non-clock one must be a lib pin of that direction and width; None = lib-only (G0)."""
    errs = []
    cells = parse_lib(path)
    if cell not in cells:
        return [f"{path}: no cell {cell} (cells {sorted(cells)[:5]})"], {}
    pins = cells[cell]
    clocks = {n for n, d in pins.items() if d["clock"]}
    if not clocks:
        errs.append(f"{path}: cell {cell} has no clock pin (clock : true)")
    n_in = n_out = 0
    for n, d in sorted(pins.items()):
        if d["clock"] or n in skip:
            continue
        arcs = [(r, t) for r, t in d["arcs"] if r in clocks]
        if d["dir"] == "input":
            n_in += 1
            if not any(t.startswith("setup_") for _r, t in arcs) or not any(t.startswith("hold_") for _r, t in arcs):
                errs.append(f"{path}: {cell}.{n} input without setup AND hold to a clock pin (arcs {d['arcs']})")
        elif d["dir"] == "output":
            n_out += 1
            if not any(t in CLOCK_TO_Q for _r, t in arcs):
                errs.append(f"{path}: {cell}.{n} output without a clock-to-q arc (arcs {d['arcs']})")
        else:
            errs.append(f"{path}: {cell}.{n} direction {d['dir']!r}: a registered-pin macro has only in/out pins")
    if ports is not None:
        for n, (dr, w) in sorted(ports.items()):
            if n in skip or n in clocks:
                continue
            d = pins.get(n)
            if d is None:
                errs.append(f"{path}: as-built pin {cell}.{n} ({dr}, {w} b) is not in the lib")
            elif d["dir"] != dr or (d["width"] is not None and d["width"] != w):
                errs.append(f"{path}: as-built pin {cell}.{n} {dr} {w} b != lib {d['dir']} {d['width']} b")
    return errs, dict(inputs=n_in, outputs=n_out, clocks=sorted(clocks))


def registered_types(raw):
    """{type: entry} of the plan's registered-pin hard types, plus the declaration errors (fail closed)."""
    res, errs = {}, []
    for tn, t in sorted(raw.get("partition_types", {}).items()):
        ents = [e for e in t.get("contents", []) + t.get("hard_cores", []) if e.get("registered_pins")]
        if not ents:
            continue
        if not t.get("hard"):
            errs.append(f"type {tn}: registered_pins on {ents[0]['inst']} but the type is not hard")
            continue
        if len(ents) != 1:
            errs.append(f"type {tn}: {len(ents)} entries declare registered_pins (the rule needs a single hard core)")
            continue
        e = ents[0]
        others = [c["inst"] for c in t.get("contents", []) + t.get("hard_cores", []) if c is not e and
                  c["inst"] != e["inst"]]
        if others:
            errs.append(f"type {tn}: registered_pins core {e['inst']} is not the only content ({others[:4]}): the "
                        "partition must be the bare macro (no std-cell room for anything else)")
            continue
        if not libs_of(e):
            errs.append(f"type {tn}: registered_pins core {e['inst']} has no lib (its FDI flops must be in the timing "
                        "model)")
            continue
        if t.get("ft_slots"):
            errs.append(f"type {tn}: registered_pins type with ft slots {[s['name'] for s in t['ft_slots']][:4]} "
                        "(a bare macro has no flops for feedthrough stations)")
            continue
        res[tn] = e
    return res, errs


def check_plan(raw, bases=()):
    """G0: declaration + lib check of every registered-pin hard type -> (errors, {type: summary})"""
    types, errs = registered_types(raw)
    summ = {}
    for tn, e in types.items():
        mod = e.get("module") or raw["partition_types"][tn].get("module")
        skip = {b["pin"] for b in e.get("bump_ports", [])}
        st = []
        for lb, f in lib_views(e, bases):
            if f is None:
                errs.append(f"type {tn}: registered_pins lib {lb} not found")
                continue
            ee, s = check_lib(f, mod, None, skip)
            errs += [f"type {tn}: {x}" for x in ee]
            st.append(dict(lib=lb, **s))
        summ[tn] = dict(core=e["inst"], module=mod, libs=st)
    return errs, summ


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    bad = 0
    for f in a:
        for cell in parse_lib(f):
            e, s = check_lib(f, cell)
            print(json.dumps(dict(lib=f, cell=cell, verdict="PASS" if not e else "FAIL", **s)))
            for x in e:
                print("  ", x)
            bad += bool(e)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
