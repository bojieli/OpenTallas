"""KEEP-MODULE AUDIT (ROOT-KEEP 2026-10-18): a kit's synthesis keep entries must match something after synthesis.

Lesson (HBM lgtap, claude/nf3-lgtap-1018 6a79110b8): ORFS SYNTH_KEEP_MODULES runs `select "NAME" "NAME\\$*"` +
`setattr -mod -set keep_hierarchy 1`.  With the default verilog frontend a parameterised instance `NAME #(.W(256))`
elaborates as `$paramod\\NAME\\W=256` (or `$paramod$<sha1>\\NAME` for long parameter lists), which neither pattern
matches: yosys only warns 'Selection "NAME" did not match any module', the copy is flattened and opt_merge folds the
replicated register back into its original.  The gate saw it only indirectly (CTS probe launch 329.7 ps).

Two checks, both scoped to kits that carry keep entries (kit.env --orfs-var SYNTH_KEEP_MODULES=..., spec
route.synth_keep_modules):
  * static (local, before any fleet run): an entry that the RTL instantiates with a #(...) parameter override can never be
    kept under the verilog frontend -> FAIL (unparameterise the module, or put (* keep_hierarchy *) on its definition --
    a module attribute is copied to every $paramod derivative);
  * post-synthesis (remote gate): every entry must name a module that survives as hierarchy in 1_2_yosys.v, or an
    instantiated cell type (a macro), under its exact name, a slang `NAME$<n>` name or a `$paramod...\\NAME...` name.
    An entry that matches nothing -> FAIL.

CLI (run by the remote gate script): python3 keep_module_audit.py netlist 1_2_yosys.v TOP  ->  GATE_KEEP_NETLIST <json>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ID = r"(?:\\\S+|[A-Za-z_][\w$]*)"
_MODULE_RE = re.compile(r"^\s*module\s+(" + _ID + r")", re.M)
_INST_RE = re.compile(r"^\s*(" + _ID + r")\s+(" + _ID + r")\s*\(", re.M)
_KEYWORDS = {"module", "input", "output", "inout", "wire", "reg", "assign", "endmodule", "always", "initial", "parameter",
             "localparam", "supply0", "supply1", "tri", "function", "task", "generate", "genvar", "integer", "logic"}
_SLANG_SUFFIX = re.compile(r"\$\d+$")


def _plain(name: str) -> str:
    return name[1:] if name.startswith("\\") else name


def keep_entries(kit_env: str | None, spec: dict | None) -> list[str]:
    """The kit's synthesis keep list: kit.env SYNTH_KEEP_MODULES (what ORFS actually receives) plus spec
    route.synth_keep_modules (what ref_tile.py gen emits into it)."""
    out = []
    if kit_env:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from kit_orfs_vars import parse
        try:
            out += parse(kit_env).get("SYNTH_KEEP_MODULES", "").split()
        except ValueError:
            pass                # kit_shell / pin_regs checks report an unparsable EXTRA
    out += list(((spec or {}).get("route") or {}).get("synth_keep_modules") or [])
    return list(dict.fromkeys(e for e in out if e))


def entry_matches(entry: str, name: str) -> bool:
    """True when post-synthesis module / cell type `name` is the kept module `entry` (exact, slang NAME$<n>, or a yosys
    $paramod derivative: $paramod\\NAME\\P=V... / $paramod$<hash>\\NAME)."""
    name = _plain(name)
    if name == entry or name.startswith(entry + "$"):
        return True
    if not name.startswith("$paramod"):
        return False
    parts = name.split("\\")
    return len(parts) >= 2 and parts[1] == entry


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def attribute_kept(entries, texts) -> set:
    """Entries whose module definition carries (* keep_hierarchy *): the attribute is copied to every $paramod
    derivative, so the hierarchy survives whatever SYNTH_KEEP_MODULES matches (qfd ot_qfd_xs_local_bank)."""
    kept = set()
    for text in texts:
        for e in entries:
            if re.search(r"\(\*[^*]*\bkeep_hierarchy\b[^*]*\*\)\s*module\s+" + re.escape(e) + r"\b", text):
                kept.add(e)
    return kept


def parameterised_instances(entries, sources, root: Path) -> dict:
    """{entry: [file:instance ...]} for entries the RTL instantiates with a #( parameter override and whose module
    definition does not carry (* keep_hierarchy *) itself."""
    hits: dict = {}
    texts = []
    for src in sources or []:
        p = Path(src)
        p = p if p.is_absolute() else root / p
        try:
            text = strip_comments(p.read_text(errors="replace"))
        except OSError:
            continue
        texts.append(text)
        for e in entries:
            for m in re.finditer(r"(?<![\w$])" + re.escape(e) + r"\s*#\s*\(", text):
                inst = re.match(r"[^;]*?\)\s*(\w+)\s*\(", text[m.end() - 1:m.end() + 4000], re.S)
                hits.setdefault(e, []).append(f"{Path(src).name}:{inst.group(1) if inst else '?'}")
    for e in attribute_kept(list(hits), texts):
        hits.pop(e, None)
    return hits


def netlist_summary(text: str, top: str | None = None) -> dict:
    """Module definitions and cell-type instance counts of a yosys netlist; `flat` multiplies through the hierarchy."""
    text = strip_comments(text)
    bodies = {}
    starts = [(m.start(), _plain(m.group(1))) for m in _MODULE_RE.finditer(text)]
    for i, (pos, name) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        bodies[name] = text[pos:end]
    direct: dict = {}
    for mod, body in bodies.items():
        counts: dict = {}
        for m in _INST_RE.finditer(body):
            typ = _plain(m.group(1))
            if typ in _KEYWORDS or typ == mod:
                continue
            counts[typ] = counts.get(typ, 0) + 1
        direct[mod] = counts
    flat: dict = {}
    top = top if top in bodies else None
    if top:
        def walk(mod, mult, depth=0):
            if depth > 64:
                return
            for typ, n in direct.get(mod, {}).items():
                flat[typ] = flat.get(typ, 0) + mult * n
                if typ in bodies:
                    walk(typ, mult * n, depth + 1)
        walk(top, 1)
    else:
        for counts in direct.values():
            for typ, n in counts.items():
                flat[typ] = flat.get(typ, 0) + n
    return {"modules": sorted(bodies), "cells": flat}


def judge(entries, summary: dict | None, warnings=()) -> list:
    """[(severity, message)] for the post-synthesis keep check."""
    if not entries:
        return []
    if summary is None:
        return [("WARN", f"{len(entries)} keep entr{'y' if len(entries) == 1 else 'ies'} but the remote log carries no "
                 "GATE_KEEP_NETLIST record (a gate older than the ROOT-KEEP check): the copies are unverified")]
    names = set(summary.get("modules") or []) | set(summary.get("cells") or {})
    out, dead = [], []
    for e in entries:
        hit = sorted(n for n in names if entry_matches(e, n))
        if not hit:
            dead.append(e)
            continue
        n = sum((summary.get("cells") or {}).get(h, 0) for h in hit)
        out.append(("INFO", f"keep {e}: {', '.join(hit[:3])}{' ...' if len(hit) > 3 else ''} survives synthesis "
                    f"({n} instance{'s' if n != 1 else ''})"))
    if dead:
        warn = [w for w in warnings if any(f'"{e}"' in w for e in dead)]
        out.append(("FAIL", f"{len(dead)} synthesis keep entr{'y' if len(dead) == 1 else 'ies'} matched no module or "
                    f"instance after synthesis: {', '.join(dead[:8])}" + (f" (+{len(dead) - 8})" if len(dead) > 8 else "")
                    + " -- the kept copies were flattened and opt_merge may have folded them back"
                    + (f"; yosys: {warn[0][:200]}" if warn else "")))
    return out


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] != "netlist":
        print(__doc__)
        return 2
    try:
        text = Path(argv[1]).read_text(errors="replace")
    except OSError as ex:
        print(f"GATE_KEEP_NETLIST_ERROR {ex}")
        return 1
    print("GATE_KEEP_NETLIST " + json.dumps(netlist_summary(text, argv[2] if len(argv) > 2 else None),
                                            separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
