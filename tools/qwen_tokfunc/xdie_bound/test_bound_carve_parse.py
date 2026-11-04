#!/usr/bin/env python3
"""parse_top reads the current bound top: several nets on one wire line and output top ports (SS25-TOK 11-03)."""
import importlib.util, pathlib, tempfile
H = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('bound_carve', H / 'bound_carve.py')
BC = importlib.util.module_from_spec(spec); spec.loader.exec_module(BC)
TOP = """module t (a, b);
    input wire a;
    output wire [3:0] b;
    wire x, y;
    wire [1:0] p, q;
    wire one; // lane L1
endmodule
"""


def test_parse():
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / 't.sv'; f.write_text(TOP)
        w, t, _ = BC.parse_top(f)
    assert t == {'a': 1, 'b': 4}
    assert w['x']['decl'].strip() == 'wire x;' and w['y']['width'] == 1
    assert w['q']['width'] == 2 and w['q']['decl'].strip() == 'wire [1:0] q;'
    assert w['one']['lane'] == 'L1' and w['one']['decl'] == '    wire one; // lane L1'
