"""BIND-SUBTYPE 11-11: asbuilt.subtype_bind (bind_subtype.py) replaces a native leaf by an exact RTL composition."""
import pytest

import bind_subtype as BS
from bind_elab import Cell, Flat


class _R:
    def __init__(self, parts):
        self.parts = dict(parts)

    def _lookup(self, path):
        p, tail = path, ""
        while True:
            if p in self.parts:
                v = self.parts[p]
                return (v[0], v[1] + tail) if isinstance(v, list) else (v, None)
            if "." not in p:
                return None, None
            p, last = p.rsplit(".", 1)
            tail = "." + last + tail

    def part_of(self, path):
        return self._lookup(path)[0]

    def local_of(self, path):
        return self._lookup(path)[1]


class _B:
    def __init__(self, cells, base, parts):
        self.F = Flat()
        self.F.new(100)
        self.F.cells = cells
        self.R = _R(parts)
        self.base = str(base)
        self.extra_lib = []


GLUE = """
module GLUE (input wire map_clk, input wire sfu_clk, input wire [1:0] a, output wire [1:0] sfu_y);
    GLUE__fcore u_fcore (.map_clk(map_clk), .sfu_clk(sfu_clk), .a(a), .sfu_y(sfu_y));
endmodule
module GLUE__fcore (input wire map_clk, input wire sfu_clk, input wire [1:0] a, output wire [1:0] sfu_y);
    wire [1:0] t;
    SUBA u_fr (.clk(map_clk), .a(a), .x(t));
    SUBB u_bk (.clk(sfu_clk), .x(t), .y(sfu_y));
endmodule
"""
SUBS = """
module SUBA (input wire clk, input wire [1:0] a, output wire [1:0] x);
endmodule
module SUBB (input wire clk, input wire [1:0] x, output wire [1:0] y);
endmodule
"""


def _native(path="q.cut_lane0", module="NAT"):
    return Cell(path, module, {}, {"map_clk": [1], "a": [2, 3], "lane_y": [4, 5]},
                {"map_clk": "input", "a": "input", "lane_y": "output"}, "leaf", ytype=module)


def _files(tmp_path):
    (tmp_path / "glue.sv").write_text(GLUE)
    (tmp_path / "subs.sv").write_text(SUBS)
    return ["glue.sv", "subs.sv"]


def _rule(tmp_path, **kw):
    r = dict(leaf=r"q\.cut_lane\d+", native="NAT", top="GLUE", files=_files(tmp_path), stops=["GLUE"],
             rename={"sfu_y": "lane_y"}, share={"sfu_clk": "map_clk"})
    r.update(kw)
    return r


def test_substitute_keeps_path_and_nets(tmp_path):
    other = Cell("q.other", "X", {}, {"o": [4]}, {"o": "input"}, "leaf")
    b = _B([_native(), other], tmp_path, {"q": ["p0", "u_q"]})
    rec = BS.apply(b, [_rule(tmp_path)])
    c = b.F.cells[0]
    assert (c.path, c.module) == ("q.cut_lane0", "GLUE")
    assert c.ports == {"map_clk": [1], "sfu_clk": [1], "a": [2, 3], "sfu_y": [4, 5]}
    assert b.F.cells[1] is other
    assert rec[0]["port_map"]["sfu_y"] == "lane_y" and rec[0]["share"] == {"sfu_clk": "map_clk"}
    assert any(f.endswith("glue.sv") for f in b.extra_lib)


def test_split_into_stops_with_fresh_internal_nets(tmp_path):
    b = _B([_native()], tmp_path, {"q": ["p0", "u_q"]})
    rule = _rule(tmp_path, stops=["SUBA", "SUBB"], local={"u_fcore.u_bk": "u_q_bk"})
    rec = BS.apply(b, [rule])
    by = {c.path: c for c in b.F.cells}
    fr, bk = by["q.cut_lane0.u_fcore.u_fr"], by["q.cut_lane0.u_fcore.u_bk"]
    assert (fr.module, bk.module) == ("SUBA", "SUBB")
    assert fr.ports["clk"] == [1] and bk.ports["clk"] == [1]          # sfu_clk shares the native map_clk net
    assert fr.ports["a"] == [2, 3] and bk.ports["y"] == [4, 5]
    assert fr.ports["x"] == bk.ports["x"] and all(n >= 100 for n in fr.ports["x"])
    assert b.R.local_of(bk.path) == "u_q_bk" and b.R.local_of(fr.path) == "u_q.cut_lane0.u_fcore.u_fr"
    assert rec[0]["internal_nets"] == 2


def test_native_module_mismatch(tmp_path):
    b = _B([_native(module="OTHER")], tmp_path, {"q": "p0"})
    with pytest.raises(BS.SubtypeError, match="native module"):
        BS.apply(b, [_rule(tmp_path)])


def test_uncovered_native_port(tmp_path):
    c = _native()
    c.ports["extra"], c.dirs["extra"] = [9], "input"
    b = _B([c], tmp_path, {"q": "p0"})
    with pytest.raises(BS.SubtypeError, match="port cover"):
        BS.apply(b, [_rule(tmp_path)])


def test_width_mismatch(tmp_path):
    c = _native()
    c.ports["a"] = [2]
    b = _B([c], tmp_path, {"q": "p0"})
    with pytest.raises(BS.SubtypeError, match="native a"):
        BS.apply(b, [_rule(tmp_path)])


def test_undriven_native_output(tmp_path):
    (tmp_path / "g2.sv").write_text("module G2 (input wire map_clk, input wire sfu_clk, input wire [1:0] a, "
                                    "output wire [1:0] sfu_y);\n SUBA u_fr (.clk(map_clk), .a(a), .x());\nendmodule\n")
    (tmp_path / "subs.sv").write_text(SUBS)
    b = _B([_native()], tmp_path, {"q": "p0"})
    with pytest.raises(BS.SubtypeError, match="drivers"):
        BS.apply(b, [_rule(tmp_path, top="G2", files=["g2.sv", "subs.sv"], stops=["SUBA"])])


def test_short_between_native_nets(tmp_path):
    (tmp_path / "g3.sv").write_text("module G3 (input wire map_clk, input wire sfu_clk, input wire [1:0] a, "
                                    "output wire [1:0] sfu_y);\n assign sfu_y = a;\nendmodule\n")
    b = _B([_native()], tmp_path, {"q": "p0"})
    with pytest.raises(BS.SubtypeError, match="native nets differ"):
        (tmp_path / "subs.sv").write_text(SUBS)
        BS.apply(b, [_rule(tmp_path, top="G3", files=["g3.sv", "subs.sv"], stops=["SUBA"])])


def test_rule_matching_nothing_fails(tmp_path):
    b = _B([_native(path="q.elsewhere")], tmp_path, {"q": "p0"})
    with pytest.raises(BS.SubtypeError, match="matched no leaf"):
        BS.apply(b, [_rule(tmp_path)])


def test_constant_on_stop_terminal(tmp_path):
    (tmp_path / "g4.sv").write_text("module G4 (input wire map_clk, input wire sfu_clk, input wire [1:0] a, "
                                    "output wire [1:0] sfu_y);\n SUBB u_bk (.clk(sfu_clk), .x({1'b0, a[0]}), "
                                    ".y(sfu_y));\n SUBA u_fr (.clk(map_clk), .a(a), .x());\nendmodule\n")
    (tmp_path / "subs.sv").write_text(SUBS)
    b = _B([_native()], tmp_path, {"q": "p0"})
    BS.apply(b, [_rule(tmp_path, top="G4", files=["g4.sv", "subs.sv"], stops=["SUBA", "SUBB"])])
    bk = {c.path: c for c in b.F.cells}["q.cut_lane0.u_bk"]
    assert bk.ports["x"] == [2, "0"]
