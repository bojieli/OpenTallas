#!/usr/bin/env python3
"""BOUND-PARAM-1 (KV-D23-COMPOSE 11-18): every parameter a bound partition passes to a module must be declared by that
module's definition IN THE TREE.

KV D23g/D23h: the plans carried clock.landing_ring_lite, so the bind (tools from main) emitted `ot_dp_clk_landing_ca
#(... .LITE(1))` on the hub types, while the trees kept the D22 rtl/common/ot_dp_clk_landing_ca.sv (no LITE parameter).
The strict bind, G0 and LATCHECK all passed; only kit elaboration would fail.  This check reads every `module #(.P(v)) inst (`
instantiation of the bound parts and every module definition under the tree's RTL roots:

  ERROR    no definition of the module in the tree declares parameter P (a plan key emits RTL the tree does not have)
  WARN     some, not all, definitions declare P (which one the kit takes depends on prefer / file order)
  info     modules with no definition in the tree (hard macros / views) are counted, not checked

usage: bound_param_check.py --tree TREE --rtl-dir BIND_OUT/rtl [--roots rtl physical results] [--json OUT]   exit 1 on ERROR
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

INST_RE = re.compile(r"(?<![\w$.])([A-Za-z_]\w*)\s*#\s*\(([^;]*?)\)\s*(\\\S+|[A-Za-z_][\w$]*(?:\s*\[[^\]]*\])?)\s*\(", re.S)
MODHDR_RE = re.compile(r"\b(?:macro)?module\s+$")
PNAME_RE = re.compile(r"\.\s*([A-Za-z_]\w*)\s*\(")
MOD_RE = re.compile(r"^\s*(?:macro)?module\s+([A-Za-z_]\w*)", re.M)
KEYWORDS = {"module", "if", "for", "case", "assign", "always", "initial", "function", "task", "begin", "end"}
SRC_EXT = (".sv", ".v", ".svh", ".vh")


def strip_comments(txt):
    txt = re.sub(r"/\*.*?\*/", " ", txt, flags=re.S)
    return re.sub(r"//[^\n]*", "", txt)


def instantiations(rtl_dir):
    """-> {module: {param: [(file, inst)]}} from every *.sv / *.v file of the bound RTL directory."""
    out = defaultdict(lambda: defaultdict(list))
    for f in sorted(Path(rtl_dir).glob("*")):
        if f.suffix not in SRC_EXT or not f.is_file():
            continue
        txt = strip_comments(f.read_text(errors="replace"))
        for m in INST_RE.finditer(txt):
            mod, plist, inst = m.group(1), m.group(2), m.group(3)
            if mod in KEYWORDS or MODHDR_RE.search(txt[max(0, m.start() - 16):m.start()]):
                continue                     # a module's own parameter header, not an instantiation
            for p in PNAME_RE.findall(plist):
                if len(out[mod][p]) < 3:
                    out[mod][p].append((f.name, inst.strip()))
                else:
                    out[mod][p]
    return out


def declares(body, p):
    return re.search(r"\bparameter\b[^;]*?\b" + re.escape(p) + r"\s*=", body) is not None


def definitions(tree, roots, wanted):
    """-> {module: [(rel path, module text)]} for the wanted modules, under TREE/<root> for each root."""
    defs = defaultdict(list)
    for r in roots:
        base = Path(tree) / r
        if not base.is_dir():
            continue
        for dp, dn, fn in os.walk(base, followlinks=False):
            for n in fn:
                if not n.endswith(SRC_EXT):
                    continue
                f = Path(dp) / n
                try:
                    raw = f.read_text(errors="replace")
                except OSError:
                    continue
                if "module" not in raw:
                    continue
                txt = strip_comments(raw)
                for m in MOD_RE.finditer(txt):
                    if m.group(1) not in wanted:
                        continue
                    end = txt.find("endmodule", m.end())
                    defs[m.group(1)].append((os.path.relpath(f, tree), txt[m.start(): end if end >= 0 else len(txt)]))
    return defs


def check(tree, rtl_dir, roots=("rtl", "physical", "results")):
    inst = instantiations(rtl_dir)
    defs = definitions(tree, roots, set(inst))
    errors, warns, undefined, checked = [], [], [], 0
    rd = os.path.realpath(str(rtl_dir))
    own = lambda rel: os.path.realpath(os.path.join(str(tree), rel)).startswith(rd + os.sep)
    for mod in sorted(inst):
        if mod not in defs:
            undefined.append(mod)
            continue
        for p, where in sorted(inst[mod].items()):
            checked += 1
            have = [path for path, body in defs[mod] if declares(body, p)]
            lack = [path for path, body in defs[mod] if not declares(body, p)]
            ex = ", ".join(f"{a}:{b}" for a, b in where[:2])
            if not have:
                errors.append(f"BOUND-PARAM {mod}.{p}: passed by {ex}; no definition in the tree declares it "
                              f"({', '.join(lack[:3])})")
            elif lack and not any(own(path) for path in have):   # the bind output's own definition is authoritative
                warns.append(f"BOUND-PARAM-PARTIAL {mod}.{p}: declared in {', '.join(have[:2])}, not in {', '.join(lack[:3])}")
    return dict(schema="opentallas.bound_param_check.v1", tree=str(tree), rtl_dir=str(rtl_dir),
                verdict="FAIL" if errors else "PASS", modules=len(inst), params_checked=checked,
                undefined_modules=len(undefined), undefined_sample=undefined[:20], errors=errors, warnings=warns)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tree", required=True)
    ap.add_argument("--rtl-dir", required=True)
    ap.add_argument("--roots", nargs="+", default=["rtl", "physical", "results"])
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    r = check(a.tree, a.rtl_dir, a.roots)
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=1) + "\n")
    for e in r["errors"][:40]:
        print(e)
    for w in r["warnings"][:10]:
        print(w)
    print(f"BOUND-PARAM-CHECK {r['verdict']} modules={r['modules']} params={r['params_checked']} errors={len(r['errors'])} "
          f"warnings={len(r['warnings'])} undefined_modules={r['undefined_modules']}")
    return 1 if r["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
