"""TOK-SCHED 10-25: native glue for the word-level combinational primitives of the current S81 dissolved parents.
Each helper is emitted by Yosys write_verilog from one primitive cell and compared with Icarus against the documented
Yosys semantics (written as plain SV) on random vectors; a wrong-parameter mutant must be caught."""
import random
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_elab as E
from bind_native_glue import NativeGlue

pytestmark = pytest.mark.skipif(not shutil.which("iverilog") or
    not (shutil.which("docker") or E.os.environ.get("OT_BIND_YOSYS")),
    reason="native Yosys and Icarus required")

def b(v, w):
    return format(v, f"0{w}b")

# type, params, port widths/dirs, reference SV for y given the inputs, input constraint
CASES = [
    ("$demux", dict(WIDTH=b(4, 32), S_WIDTH=b(2, 32)), dict(A=(4, "input"), S=(2, "input"), Y=(16, "output")),
     "{12'd0, a[3:0]} << (s[1:0] * 4)"),
    ("$bwmux", dict(WIDTH=b(8, 32)), dict(A=(8, "input"), B=(8, "input"), S=(8, "input"), Y=(8, "output")),
     "(a[7:0] & ~s[7:0]) | (bb[7:0] & s[7:0])"),
    ("$bmux", dict(WIDTH=b(4, 32), S_WIDTH=b(2, 32)), dict(A=(16, "input"), S=(2, "input"), Y=(4, "output")),
     "a[s[1:0]*4 +: 4]"),
    ("$pmux", dict(WIDTH=b(4, 32), S_WIDTH=b(3, 32)), dict(A=(4, "input"), B=(12, "input"), S=(3, "input"), Y=(4, "output")),
     "s[0] ? bb[3:0] : s[1] ? bb[7:4] : s[2] ? bb[11:8] : a[3:0]"),
    ("$shift", dict(A_SIGNED=b(0, 32), B_SIGNED=b(1, 32), A_WIDTH=b(8, 32), B_WIDTH=b(4, 32), Y_WIDTH=b(8, 32)),
     dict(A=(8, "input"), B=(4, "input"), Y=(8, "output")),
     "$signed(bb[3:0]) < 0 ? a[7:0] << (-$signed(bb[3:0])) : a[7:0] >> bb[3:0]"),
    ("$div", dict(A_SIGNED=b(0, 32), B_SIGNED=b(0, 32), A_WIDTH=b(8, 32), B_WIDTH=b(8, 32), Y_WIDTH=b(8, 32)),
     dict(A=(8, "input"), B=(8, "input"), Y=(8, "output")), "a[7:0] / bb[7:0]"),
    ("$mod", dict(A_SIGNED=b(0, 32), B_SIGNED=b(0, 32), A_WIDTH=b(8, 32), B_WIDTH=b(8, 32), Y_WIDTH=b(8, 32)),
     dict(A=(8, "input"), B=(8, "input"), Y=(8, "output")), "a[7:0] % bb[7:0]"),
]
NAMES = {"A": "a", "B": "bb", "S": "s", "Y": "y"}


def _cell(t, params, ports):
    bit = iter(range(2, 10_000))
    return NS(ytype=t, yparams=dict(params), dirs={p: d for p, (w, d) in ports.items()},
              ports={p: [next(bit) for _ in range(w)] for p, (w, d) in ports.items()})


@pytest.mark.parametrize("mutant", [False, True])
def test_native_combinational_primitives(tmp_path, mutant):
    native = NativeGlue(tmp_path / "helpers", sorted({c[0] for c in CASES}))
    rng = random.Random(7)
    body, checks = [], []
    for i, (t, params, ports, ref) in enumerate(CASES):
        params = dict(params)
        if mutant and t == "$bmux":
            params["WIDTH"] = b(4, 32)
            ports = dict(ports)
        c = _cell(t, params, ports)
        conns = {p: (f"y{i}" if p == "Y" else NAMES[p] + f"[{w - 1}:0]") for p, (w, d) in ports.items()}
        if mutant and t == "$bmux":
            conns["S"] = "{s[0], s[1]}"          # select bits swapped: must be caught
        body.append(f"  wire [{ports['Y'][0] - 1}:0] y{i};")
        body.append(native.emit(c, conns, f"u{i}"))
        checks.append((i, ports["Y"][0], ref, t))
    lines = ["module tb;", "  reg [15:0] a, bb, s; integer k, bad; initial bad = 0;"] + body
    lines.append("  initial begin")
    lines.append("    for (k = 0; k < 400; k = k + 1) begin")
    lines.append("      a = $random; bb = $random; s = $random;")
    lines.append("      if (bb[7:0] == 0) bb[0] = 1'b1;")                  # $div/$mod: no divide-by-zero vector
    lines.append("      if (k % 2) s[2:0] = 3'b1 << (k % 3); else s[2:0] = (k % 4 == 0) ? 3'b0 : s[2:0] & 3'b001;")
    lines.append("      #1;")
    for i, w, ref, t in checks:
        lines.append(f"      if (y{i} !== {w}'({ref})) begin bad = bad + 1; $display(\"MISMATCH {t} %h\", y{i}); end")
    lines.append("    end")
    lines.append("    if (bad == 0) $display(\"PASS\"); else $display(\"FAIL %0d\", bad);")
    lines.append("    $finish;")
    lines.append("  end")
    lines.append("endmodule")
    (tmp_path / "tb.sv").write_text("\n".join(lines) + "\n")
    exe = tmp_path / "tb.vvp"
    subprocess.run(["iverilog", "-g2012", "-o", str(exe), str(tmp_path / "tb.sv")] + [str(f) for f in native.files],
                   check=True)
    out = subprocess.run(["vvp", str(exe)], capture_output=True, text=True, check=True).stdout
    if mutant:
        assert "FAIL" in out and "MISMATCH $bmux" in out
    else:
        assert "PASS" in out, out


def test_native_memory_shared_write_clock(tmp_path):
    """two write ports on ONE clock (WR_CLK [c, c]): the helper keeps one clock net (Yosys mem.cc would assert on
    distinct clocks with a write priority) and matches the RTL; both write processes use that one clock."""
    import json
    src = """module gold(input clk, input we0, we1, input [1:0] a0, a1, ra, input [7:0] d0, d1, output [7:0] q);
reg [7:0] mem [0:3]; integer i; initial for (i = 0; i < 4; i = i + 1) mem[i] = 8'h30 + i;
always @(posedge clk) if (we0) mem[a0] <= d0;
always @(posedge clk) if (we1) mem[a1] <= d1;
assign q = mem[ra];
endmodule
"""
    (tmp_path / "gold.sv").write_text(src)
    (tmp_path / "x.ys").write_text(f"read_verilog -sv {tmp_path / 'gold.sv'}\nproc\nmemory_collect\n"
                                   f"write_json {tmp_path / 'gold.json'}\n")
    E.run_yosys(tmp_path / "x.ys", tmp_path / "x.log", [tmp_path], mem_gb=2)
    cells = json.loads((tmp_path / "gold.json").read_text())["modules"]["gold"]["cells"]
    mem = next(c for c in cells.values() if c["type"] == "$mem_v2")
    assert int(mem["parameters"]["WR_PORTS"], 2) == 2
    wc = mem["connections"]["WR_CLK"]
    assert len(wc) == 2 and wc[0] == wc[1]
    m = NS(ytype="$mem_v2", yparams=mem["parameters"], dirs=mem["port_directions"], ports=mem["connections"])
    nets = json.loads((tmp_path / "gold.json").read_text())["modules"]["gold"]["netnames"]
    name = {}
    for n, v in nets.items():
        for k, bit in enumerate(v["bits"]):
            name.setdefault(bit, f"{n}[{k}]" if len(v["bits"]) > 1 else n)

    def expr(bits):
        return "{" + ", ".join(("1'b" + b) if isinstance(b, str) else name[b] for b in reversed(bits)) + "}"
    conns = {p: expr(bits) for p, bits in mem["connections"].items()}
    native = NativeGlue(tmp_path / "h", ["$mem_v2"])
    inst = native.emit(m, conns, "u_mem")
    # (Icarus cannot parse the per-bit memory-word writes Yosys prints, so check the structure here; the
    # combinational primitives above are simulated.)  Yosys itself built the helper (it asserted before the fix).
    sv = native.files[0].read_text()
    import re
    clocks = set(re.findall(r"always @\(posedge (\S+?)\)", sv))
    assert clocks == {"WR_CLK[0]"}, clocks
    assert inst.count(".WR_CLK(") == 1
