#!/usr/bin/env python3
"""TYPE-REDUCE-3/HBM 10-25: Verilator lockstep bench, strap master vs the old constant variant it replaces.

    python3 results/type_reduce3_1025/hbm/gen_bench.py MASTER OLD_KIT 'strap=VAL,..' OUTDIR [--cycles N]

One bench per (master, strap value): REF = the old variant's plan module (its kit wrapper <old>__fcore: old pin names,
ID constant inside), DUT = the strap master wrapper (repo rtl, template pin names) with strap_* = the same constant,
MUT = the strap master with strap bit 0 flipped (wrong ID).  Same random stimulus on every input pin bit each cycle
(template name = core_templates.renamer(old name)), all clock pins on one clock, resets released after 8 cycles.
PASS = DUT outputs == REF outputs on every cycle AND MUT differs from REF on >= 1 output bit (mutant caught).
Face shells are not part of the bench (+1/+1 cycle registers, same on both sides; the kit LEC covers them)."""
import json, re, sys
from pathlib import Path
R = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(R / "physical/die_plan/hbm_arch"))
import core_templates as CT
CLK_RE = r"^(clk|clk_[a-z0-9_]+|[a-z0-9_]*_clk|ck|ck_[a-z0-9_]+|[a-z0-9_]*clk_[a-z0-9_]*)$"
RST_RE = r"^(rst_n|rst|arst_n|reset_n|rst_[a-z0-9_]+|[a-z0-9_]*_rst_n|[a-z0-9_]*rst_n|[a-z0-9_]*rst_[a-z0-9_]*n)$"
master, okit, straps, out = sys.argv[1:5]
cycles = int(sys.argv[sys.argv.index("--cycles") + 1]) if "--cycles" in sys.argv else 3000
straps = dict(x.split("=", 1) for x in straps.split(","))
views = {v["module"]: v for v in json.load(open(R / "physical/die_plan/hbm_arch_cores/views_b2n_strap.json"))["view_list"]}
sm = views[master]["strap_master"]
canon = json.load(open(R / "physical/die_plan/hbm/cores/harden/canonical_ports_split.json"))["types"][sm["canonical_type"]]
okit = Path(okit); of = json.load(open(okit / "freeze.json")); omod = of["design"]
tid = next(t for t in canon["type_ids"] if re.sub(r"__[\d.]+x[\d.]+$", "", t) == omod)
rn, rb = CT.renamer(canon["type_ids"][tid]["cut_pins"], canon["ports"])
cfg = (okit / "config.mk").read_text()
files = [okit / "rtl" / Path(f).name for f in re.search(r"(?m)^export VERILOG_FILES = (.*)$", cfg).group(1).split()]
files = [f for f in files if not f.name.endswith("__fshell.sv") and f.name != "ot_hbm_face_reg.sv"]
files.append(R / sm["wrapper"])          # copied into the bench dir below (fleet jobs see only the bench dir)
wrapf = next(f for f in files if re.search(r"(?m)^\s*module\s+" + re.escape(omod) + r"__fcore\b", f.read_text()))
PORT_RE = re.compile(r"(input|output)\s+wire\s+(?:\[(\d+):(\d+)\]\s+)?([A-Za-z_]\w*)")
t = wrapf.read_text(); m = re.search(r"(?s)module\s+" + re.escape(omod) + r"__fcore\s*\((.*?)\);", t)
ports = [(p[3], p[0], int(p[1]) - int(p[2]) + 1 if p[1] else 1) for p in PORT_RE.findall(m.group(1))]
st = R / sm["wrapper"]; mt = re.search(r"(?s)module\s+" + re.escape(master) + r"\s*\((.*?)\);", st.read_text())
nports = {p[3]: (p[0], int(p[1]) - int(p[2]) + 1 if p[1] else 1) for p in PORT_RE.findall(mt.group(1))}
o2n = {o: rb(o) for o, _d, _w in ports}
miss = sorted(set(nports) - set(o2n.values()) - set(straps))
bad = [o for o, d, w in ports if nports.get(o2n[o]) != (d, w)]
if miss or bad:
    raise SystemExit(f"port correspondence FAIL: master-only {miss[:6]}, mismatched {bad[:6]}")
L = ["`timescale 1ns/1ps", "module tb;", "  reg clk = 0; reg rst_n = 0; integer cyc = 0; integer ndiff = 0; integer nmut = 0;",
     "  always #1 clk = ~clk;"]
c_ref, c_dut, c_mut, cmp_ = [], [], [], []
for o, d, w in ports:
    n = o2n[o]
    if d == "input":
        if re.match(CLK_RE, o) or re.match(CLK_RE, n):
            sig = f"{{{w}{{clk}}}}" if w > 1 else "clk"
        elif re.match(RST_RE, o) or re.match(RST_RE, n):
            sig = f"{{{w}{{rst_n}}}}" if w > 1 else "rst_n"
        else:
            L.append(f"  reg [{w - 1}:0] i_{o};"); sig = f"i_{o}"
        c_ref.append(f".{o}({sig})"); c_dut.append(f".{n}({sig})"); c_mut.append(f".{n}({sig})")
    else:
        for s in ("r", "d", "m"):
            L.append(f"  wire [{w - 1}:0] {s}_{o};")
        c_ref.append(f".{o}(r_{o})"); c_dut.append(f".{n}(d_{o})"); c_mut.append(f".{n}(m_{o})")
        cmp_.append(o)
for s, val in straps.items():
    w, bits = re.fullmatch(r"(\d+)'b([01]+)", val).groups()
    mb = bits[:-1] + ("1" if bits[-1] == "0" else "0") if s == sorted(straps)[0] else bits
    c_dut.append(f".{s}({w}'b{bits})"); c_mut.append(f".{s}({w}'b{mb})")
L.append(f"  {omod}__fcore u_ref ({', '.join(c_ref)});")
L.append(f"  {master} u_dut ({', '.join(c_dut)});")
L.append(f"  {master} u_mut ({', '.join(c_mut)});")
L.append("  always @(negedge clk) begin")
for o, d, w in ports:
    if d == "input" and f"reg [{w - 1}:0] i_{o};" in L:
        L.append(f"    i_{o} <= {{{', '.join(['$urandom'] * ((w + 31) // 32))}}};")
L.append("  end")
L.append("  always @(posedge clk) begin")
L.append("    cyc <= cyc + 1; if (cyc == 8) rst_n <= 1;")
for o in cmp_:
    L.append(f"    if (d_{o} !== r_{o}) begin ndiff = ndiff + 1; if (ndiff < 5) $display(\"DIFF cyc %0d {o}\", cyc); end")
    L.append(f"    if (m_{o} !== r_{o}) nmut = nmut + 1;")
L.append(f"    if (cyc == {cycles}) begin $display(\"RESULT master={master} old={omod} straps={json.dumps(straps).replace(chr(34), '')} cycles=%0d dut_vs_ref_diffs=%0d mutant_diffs=%0d %s\", cyc, ndiff, nmut, (ndiff == 0 && nmut > 0) ? \"PASS\" : \"FAIL\"); $finish; end")
L.append("  end")
L.append("endmodule")
out = Path(out); out.mkdir(parents=True, exist_ok=True)
(out / "tb.sv").write_text("\n".join(L) + "\n")
import shutil
(out / "rtl").mkdir(exist_ok=True)
for f in files:
    shutil.copyfile(f, out / "rtl" / f.name)
(out / "files.f").write_text("\n".join(f"rtl/{f.name}" for f in files) + "\n")
print(json.dumps(dict(out=str(out), old=omod, outputs=len(cmp_), inputs=sum(1 for p in ports if p[1] == "input"), files=len(files))))
