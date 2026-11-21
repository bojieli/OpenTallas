"""complete_top on the ANSI and the non-ANSI (gen.py rtl since 11-1x) die top forms."""
import re
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1] / 'die_plan')]
import head_start_sources as H

PLAN = dict(partitions=[dict(name='a0', type='ta')],
            partition_types=dict(ta=dict(module='ot_ta', reset_start_raw_exports=[dict(port='rst_start_raw_0')])))
STAGES = dict(reset_ports={'wrst_a0__rst_start_raw_0': dict(part='a0', port='rst_start_raw_0')},
              die_outputs=[dict(net='pst_a0')], stages=[dict(clock_port='t_st_b0__clk')])
INST = '    ot_ta a0 (\n        .clk(clk),\n        .cland_tstart_in(pst_a0)\n    );\n'
ANSI = 'module s81_head_top (\n    input  wire rst_n,\n    input  wire pst_a0,\n    input  wire clk\n);\n' + INST + 'endmodule\n'
NANSI = ('module s81_head_top (rst_n, pst_a0, clk);\n    input  wire rst_n;\n    input  wire pst_a0;\n    input  wire clk;\n'
         + INST + 'endmodule : s81_head_top\n')


def _check(t):
    assert '.rst_start_raw_0(wr_a0__rst_start_raw_0)' in t
    assert 'ot_die_start_stages u_die_start_stages' in t and '.pst_a0(pst_a0)' in t and '.t_st_b0__clk(t_st_b0__clk)' in t
    assert not re.search(r'input\s+wire\s+pst_a0', t)
    assert re.search(r'input\s+wire\s+t_st_b0__clk', t)
    assert re.search(r'\bwire wr_a0__rst_start_raw_0;', t)


def test_ansi():
    t, unused = H.complete_top(ANSI, PLAN, STAGES)
    _check(t); assert unused == []


def test_non_ansi():
    t, unused = H.complete_top(NANSI, PLAN, STAGES)
    _check(t); assert unused == []
    hdr = re.search(r'module s81_head_top \(([^;]*)\);', t)[1].split(', ')
    assert hdr == ['rst_n', 'clk', 't_st_b0__clk']
    assert '    wire pst_a0;' in t
