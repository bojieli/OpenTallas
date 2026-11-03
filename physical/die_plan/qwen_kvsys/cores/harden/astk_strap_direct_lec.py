#!/usr/bin/env python3
"""DIE-KV-63 11-03: per-strap-value LEC of the ASTK strap-direct transform (astk_native_faces.strap_direct).
gold = original module, gate = strap-direct module; strap input replaced by the constant on BOTH sides (the parent tie),
submodules black boxes (read -lib), keep attrs unset, opt -full folds constant-D registers, then equiv_make /
equiv_simple / equiv_induct / equiv_status -assert.  Mutant: gate tied to a flipped strap must NOT be equivalent.
usage: strap_direct_lec.py ORIG_RTL_DIR NEW_RTL_DIR OUT_DIR"""
import json, re, subprocess, sys
from pathlib import Path
orig, new, out = map(Path, sys.argv[1:4])
out.mkdir(parents=True, exist_ok=True)

def mod_text(p, mod):
    t = p.read_text()
    m = re.search(rf"(\(\*[^*]*\*\)\s*)?\bmodule {mod}\s*[#(]", t)
    return t[m.start():t.index("endmodule", m.start()) + len("endmodule")]

def tie(text, mod, newname, port, width, val):
    decl = re.search(rf"^\s*input\s+wire\s+\[{width-1}:0\]\s+{port},\s*\n", text, re.M)
    assert decl, (mod, port)
    text = text[:decl.start()] + text[decl.end():]
    text = re.sub(rf"\bmodule {mod}\b", f"module {newname}", text, count=1)
    i = text.index(");\n", text.index(f"module {newname}")) + 3
    return text[:i] + f"    wire [{width-1}:0] {port} = {width}'b{val:0{width}b};\n" + text[i:]

libs = sorted(str(p) for p in orig.glob("*.sv"))
cases = []
for L in (1, 2, 3):
    for V in range(4):
        cases.append(("qkd_astk_zn", "qkd_astk_leaves.sv", "zc", 4, (L << 2) | V, (L << 2) | (V ^ 1) if V == 0 else None))
for V in range(4):
    cases.append(("qkd_astk_ctl_s_g0", "qkd_astk_ctl_s_g0.sv", "st", 2, V, (V ^ 1) if V == 0 else None))
res = []
for mod, f, port, w, val, mut in cases:
    for kind, gv in (("eq", val), ("mutant", mut)):
        if gv is None:
            continue
        tag = f"{mod}_{port}{val:0{w}b}_{kind}"
        d = out / tag
        d.mkdir(exist_ok=True)
        g = tie(mod_text(orig / f, mod), mod, "gold", port, w, val)
        # the gold strap-capture register after the strap settled (reset is held >= 64 edges after power-up, the
        # strap is a parent tie): init = its constant D, so opt folds it like the gate's direct read
        cap = {"zc": ("reg [3:0]   zc_q;", f"reg [3:0]   zc_q = 4'b{val:04b};"),
               "st": ("reg [1:0]   st_q;", f"reg [1:0]   st_q = 2'b{val:02b};")}[port]
        assert g.count(cap[0]) == 1, (mod, cap[0])
        (d / "gold.sv").write_text(g.replace(cap[0], cap[1]) + "\n")
        (d / "gate.sv").write_text(tie(mod_text(new / f, mod), mod, "gate", port, w, gv) + "\n")
        (d / "top.sv").write_text("module lec_top;\n    gold g();\n    gate h();\nendmodule\n")
        ys = (f"read_verilog -sv {' '.join(libs)}\nread_verilog -sv {d}/gold.sv {d}/gate.sv {d}/top.sv\n"
              "hierarchy -top lec_top\nproc\nmemory\nsetattr -unset keep\nsetattr -unset keep_hierarchy\nsetattr -mod -unset keep_hierarchy\nflatten gold gate\ndelete lec_top\n"
              "async2sync\nopt -full\nopt_clean -purge\n"
              "equiv_make gold gate eq\nhierarchy -top eq\nequiv_simple -seq 2\nequiv_induct -seq 2\nequiv_status -assert\n")
        (d / "lec.ys").write_text(ys)
        r = subprocess.run(["yosys", "-q", "-l", str(d / "lec.log"), str(d / "lec.ys")], capture_output=True, text=True)
        st = re.findall(r"Found (\d+) \$equiv cells.*|Of those cells (\d+) are proven and (\d+) are unproven", (d / "lec.log").read_text())
        ok = r.returncode == 0
        res.append(dict(case=tag, rc=r.returncode, verdict=("EQUIVALENT" if ok else "NOT_EQUIVALENT"),
                        expect=("EQUIVALENT" if kind == "eq" else "NOT_EQUIVALENT"),
                        tail=(d / "lec.log").read_text().strip().splitlines()[-3:]))
        print(tag, res[-1]["verdict"], "expect", res[-1]["expect"], flush=True)
v = "PASS" if all(x["verdict"] == x["expect"] for x in res) else "FAIL"
(out / "strap_direct_lec.json").write_text(json.dumps(dict(schema="opentallas.astk_strap_direct_lec.v1", verdict=v,
    orig=str(orig), new=str(new), cases=res), indent=1) + "\n")
print("STRAP_DIRECT_LEC", v)
sys.exit(0 if v == "PASS" else 1)
