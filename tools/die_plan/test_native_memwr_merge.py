"""Per-bit write statements of a native $mem_v2 merge into chunk-wide statements without changing behaviour."""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_memwr_merge import merge_memwr, CHUNK


def per_bit(n, mem="\\\\native_memory", addr="WR_ADDR", off=0, en="WR_EN", d="WR_DATA", const=None, ind="    "):
    out = []
    for i in range(n):
        rhs = const if const else f"{d}[{i}]"
        out.append(f"{ind}if ({en}[{off + i}])\n{ind}  {mem} [{addr}][{i}:{i}] <= {rhs};\n")
    return "".join(out)


def count(text):
    return len(re.findall(r"<= ", text))


def test_run_of_one_port_becomes_chunks():
    t = "always @(posedge WR_CLK) begin\n" + per_bit(2120) + "end\n"
    o, st = merge_memwr(t)
    assert st == [("\\\\native_memory", 2120, 9)]          # ceil(2120 / 256)
    assert count(o) == 9 and "if (" not in o
    assert "[0 +: 256] <= (" in o and "[2048 +: 72] <= (" in o


def test_small_memory_is_byte_identical():
    t = "always @(posedge c) begin\n" + per_bit(63) + "end\n"
    assert merge_memwr(t) == (t, [])


def test_ports_with_other_address_or_constant_data_do_not_mix():
    t = ("always @(posedge c) begin\n" + per_bit(100, addr="WR_ADDR[2:0]") + per_bit(100, addr="WR_ADDR[5:3]", off=100)
         + per_bit(100, addr="WR_ADDR[5:3]", off=200, const="1'h0") + "end\n")
    o, st = merge_memwr(t)
    assert st == [("\\\\native_memory", 300, 3)]
    assert o.index("WR_ADDR[2:0]") < o.index("WR_ADDR[5:3]")      # statement order between ports kept
    assert "{100{1'h0}}" in o


def test_gap_in_enable_index_breaks_the_run():
    t = per_bit(40) + per_bit(40, off=41)
    t = "always @(posedge c) begin\n" + t + per_bit(0) + "end\n"
    # 80 statements, enable index jumps 39 -> 41: two runs
    t2, st = merge_memwr(t)
    assert st[0][2] == 2


def test_reordered_overlap_is_never_merged():
    # same bit written twice in a row: second statement restarts at bit 0, so it cannot join the first run
    t = "always @(posedge c) begin\n" + per_bit(64) + per_bit(64, d="WR_DATA2") + "end\n"
    o, st = merge_memwr(t)
    assert st == [("\\\\native_memory", 128, 2)]
    assert o.index("WR_DATA[") < o.index("WR_DATA2[")


def test_emit_merges_and_is_equivalent_to_the_per_bit_form(tmp_path, monkeypatch):
    """End to end through NativeGlue.emit: 96-bit word, per-bit enables; merged form has <= 1 write statement per 256 bits
    and a yosys equivalence proof against the per-bit form (separate helper directories, same $mem_v2)."""
    import shutil
    from types import SimpleNamespace as NS
    import bind_elab as E
    from bind_native_glue import NativeGlue
    if not (shutil.which("docker") or E.os.environ.get("OT_BIND_YOSYS")):
        import pytest
        pytest.skip("native Yosys required")
    W, ABITS = 96, 2
    bits = lambda v, n: format(v, "0%db" % n)
    params = {"ABITS": bits(ABITS, 32), "INIT": "x" * (W * 4), "MEMID": "\\\\m", "OFFSET": bits(0, 32),
              "RD_ARST_VALUE": "x" * W, "RD_CE_OVER_SRST": "0", "RD_CLK_ENABLE": "0", "RD_CLK_POLARITY": "0",
              "RD_COLLISION_X_MASK": "0", "RD_INIT_VALUE": "x" * W, "RD_PORTS": bits(1, 32), "RD_SRST_VALUE": "x" * W,
              "RD_TRANSPARENCY_MASK": "0", "RD_WIDE_CONTINUATION": "0", "SIZE": bits(4, 32), "WIDTH": bits(W, 32),
              "WR_CLK_ENABLE": "1", "WR_CLK_POLARITY": "1", "WR_PORTS": bits(1, 32), "WR_PRIORITY_MASK": "0",
              "WR_WIDE_CONTINUATION": "0"}
    n = iter(range(2, 10000))
    take = lambda k: [next(n) for _ in range(k)]
    ports = {"RD_ADDR": take(ABITS), "RD_ARST": ["0"], "RD_CLK": ["x"], "RD_DATA": take(W), "RD_EN": ["1"],
             "RD_SRST": ["0"], "WR_ADDR": take(ABITS), "WR_CLK": take(1), "WR_DATA": take(W), "WR_EN": take(W)}
    dirs = {p: ("output" if p == "RD_DATA" else "input") for p in ports}
    cell = NS(ytype="$mem_v2", yparams=params, dirs=dirs, ports=ports)
    conns = {"RD_ADDR": "ra", "RD_ARST": "1'b0", "RD_CLK": "1'b0", "RD_DATA": "q", "RD_EN": "1'b1", "RD_SRST": "1'b0",
             "WR_ADDR": "a", "WR_CLK": "clk", "WR_DATA": "d", "WR_EN": "en"}
    sv = {}
    for flag in ("0", "1"):
        monkeypatch.setenv("OT_NATIVE_MEMWR_MERGE", flag)
        ng = NativeGlue(tmp_path / ("h" + flag), ["$mem_v2"])
        ng.emit(cell, conns, "m0")
        sv[flag] = ng.files[0]
    gold_text, gate_text = sv["0"].read_text(), sv["1"].read_text()
    assert gold_text.count("<= ") == W and gate_text.count("<= ") == 1      # 96 bits < one 256-bit chunk
    top = sv["0"].stem
    (tmp_path / "lec.ys").write_text(
        f"read_verilog -sv {sv['0']}\nrename {top} gold\nread_verilog -sv {sv['1']}\nrename {top} gate\n"
        "proc\nmemory_collect\nmemory_map\nopt_clean\nequiv_make gold gate eq\nhierarchy -top eq\n"
        "equiv_simple -seq 2\nequiv_induct -seq 2\nequiv_status -assert\n")
    E.run_yosys(tmp_path / "lec.ys", tmp_path / "lec.log", [tmp_path], mem_gb=4)


def test_overlapping_ports_at_different_addresses_carry_earlier_writes():
    """LEC finding on land (11-16): port B's chunk (en bit 0) must not undo port A's write to the same word.  The merged text starts B's
    read-modify-write from the word as port A leaves it (address compare) instead of from the old word."""
    a = per_bit(64, addr="{ 24'h000000, WR_ADDR[7:0] }")
    b = per_bit(64, addr="{ 22'h000000, WR_ADDR[41:32] }", off=64, d="WR_DATA", )
    o, st = merge_memwr("always @(posedge c) begin\n" + a + b + "end\n")
    assert st == [("\\\\native_memory", 128, 2)]
    second = [l for l in o.splitlines() if "WR_ADDR[41:32]" in l][0]
    assert "(" in second and "== " in second and "WR_ADDR[7:0]" in second          # earlier port A folded in under an address compare
    first = [l for l in o.splitlines() if "WR_ADDR[7:0]" in l][0]
    assert "==" not in first                                                       # the first chunk has no earlier statement to fold in


def test_same_address_overlap_folds_without_compare():
    a = per_bit(64)
    b = per_bit(64, off=64)
    o, st = merge_memwr("always @(posedge c) begin\n" + a + b + "end\n")
    second = [l for l in o.splitlines() if "WR_EN[64" in l][0]
    assert "==" not in second and "WR_EN[0 +: 64]" in second
