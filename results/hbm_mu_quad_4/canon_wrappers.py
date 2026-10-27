#!/usr/bin/env python3
"""HBM-MU-QUAD-4: canonical strap wrappers for the index-normalised pgslice families + per-member LEC scripts.

Usage: canon_wrappers.py REPORT.json WRAPPER_DIR OUT_DIR
For every type_reduce group whose members are pure-wiring split wrappers: write OUT_DIR/<canonical>.sv = the first
member with module renamed, ports index-normalised (_(bank|lane)_<n>_ -> _\\1_x_), and each differing constant tie
replaced by an input strap_<port> (tied at the parent, OWNER 10-25 ID-straps rule B).  For every member write
lec_<member>.ys: gold = member wrapper, gate = canonical with the member's constants on its straps (shim), canonical
top blackboxed (identical cell on both sides), equiv_make/equiv_simple/equiv_induct/equiv_status -assert."""
import json, re, sys
from pathlib import Path

IDXRE = re.compile(r"_(bank|lane)_([0-9]+)_")


def nz(text, ref=None):
    rm = {i: r for r, i in enumerate(sorted({int(m.group(2)) for m in IDXRE.finditer(ref or text)}))}
    return IDXRE.sub(lambda m: f"_{m.group(1)}_k{rm[int(m.group(2))]}_", text)


def width(lit):
    if lit.startswith("{"):
        return len([x for x in lit[1:-1].split(",") if x.strip()])
    return int(lit.split("'")[0])


def main():
    rep, wd, out = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]), Path(sys.argv[3])
    rtl = sys.argv[4]
    out.mkdir(parents=True, exist_ok=True)
    man = {}
    for g in rep["groups"]:
        mem = [m for m in g["members"] if (wd / f"{m}.sv").exists()]
        if not mem or len(g["members"]) < 2:
            continue
        cn = g["canonical"]
        src = (wd / f"{mem[0]}.sv").read_text()
        body = nz(src)
        body = re.sub(rf"\bmodule {re.escape(mem[0])}\b", f"module {cn}", body)
        straps = g["straps"]
        decl = []
        for k in straps:
            m = re.search(rf"\.{k}\((\{{[^}}]*\}}|\d+'[bhd][0-9a-fA-F_]+)\)", body)
            w = width(m.group(1))
            body = body[:m.start()] + f".{k}({k})" + body[m.end():]
            decl.append(f"    input wire [{w - 1}:0] {k},")
        body = re.sub(rf"(module {re.escape(cn)} \(\n)", lambda mm: mm.group(1) + "\n".join(decl) + ("\n" if decl else ""), body, count=1)
        body = body.replace("// GENERATED", f"// HBM-MU-QUAD-4 canonical strap view of {len(mem)} members ({', '.join(mem)}); GENERATED", 1)
        (out / f"{cn}.sv").write_text(body)
        canon_top = re.search(r"canonical top (\w+)", src).group(1)
        for m in mem:
            ms = (wd / f"{m}.sv").read_text()
            cons = {k: re.search(rf"\.{k}\((\{{[^}}]*\}}|\d+'[bhd][0-9a-fA-F_]+)\)", ms).group(1) for k in straps}
            # shim: member port names -> canonical (index-normalised) names + strap constants
            ports = re.findall(r"^\s*(input|output) wire (\[[^\]]+\] )?(\w+)", ms, re.M)
            pl = ",\n".join(f"    {d} wire {w or ''}{n}" for d, w, n in ports)
            conn = ",\n".join([f"        .{nz(n, ms)}({n})" for _, _, n in ports] +
                              [f"        .{k}({v})" for k, v in cons.items()])
            shim = f"module {m} (\n{pl}\n);\n    {cn} u_canon (\n{conn}\n    );\nendmodule\n"
            (out / f"shim_{m}.sv").write_text(shim)
            (out / f"lec_{m}.ys").write_text(
                f"read_verilog -sv -lib {rtl}/{canon_top}.sv\n"
                f"read_verilog -sv {wd}/{m}.sv\nhierarchy -top {m}\nrename {m} gold\n"
                f"read_verilog -sv {out}/{cn}.sv {out}/shim_{m}.sv\nhierarchy -top {m}\nrename {m} gate\n"
                "flatten gold gate\nopt_clean\nequiv_make gold gate equiv\nhierarchy -top equiv\n"
                "equiv_simple -undef\nequiv_induct -undef\nequiv_status -assert\n")
            man.setdefault(cn, []).append(dict(member=m, straps=cons))
        man[cn + "#top"] = canon_top
    (out / "canon_manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps({k: len(v) for k, v in man.items() if not k.endswith("#top")}))


if __name__ == "__main__":
    main()
