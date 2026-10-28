"""DIE-HEAD-7 10-28: KIT_PREFLIGHT module_closure -- an instantiated module with no staged definition, no *_bb
blackbox and no macro liberty fails before allocation (HEAD r2 hd_tile: ot_meso_ring u_ring passed preflight and
failed RTL_LINT in the container)."""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import kit_preflight as K  # noqa: E402

ROOT = HERE.parent.parent
TOP = """module top(input wire clk, input wire [3:0] d, output wire [3:0] q);
    ot_dp_clk_landing #(.W(4)) u_cland (.clk(clk), .fclk(clk), .rst_n(1'b1), .d(d), .q(q));
endmodule
"""


def kit(tmp_path, files, top='top', defines='-DSYNTHESIS', libs=()):
    k = tmp_path / 'kit'
    (k / 'rtl').mkdir(parents=True)
    for name, text in files.items():
        (k / 'rtl' / name).write_text(text)
    for name, text in libs:
        (k / 'macros').mkdir(exist_ok=True)
        (k / 'macros' / name).write_text(text)
    (k / 'config.mk').write_text(f'export DESIGN_NAME = {top}\nexport VERILOG_FILES = '
                                 + ' '.join(f'/work/rtl/{n}' for n in files) + f'\nexport VERILOG_DEFINES = {defines}\n')
    return k


def test_real_landing_without_ring_library_fails_with_it_passes(tmp_path):
    land = (ROOT / 'rtl/common/ot_dp_clk_landing.sv').read_text()
    bad = kit(tmp_path / 'a', {'top.sv': TOP, 'ot_dp_clk_landing.sv': land})
    err = K.unresolved_modules(bad)
    assert any('module ot_meso_ring instantiated in ot_dp_clk_landing.sv' in e for e in err), err
    assert K.check(bad)['checks']['module_closure']['verdict'] == 'FAIL'
    good = kit(tmp_path / 'b', {'top.sv': TOP, 'ot_dp_clk_landing.sv': land,
                                'ot_meso_fifo.sv': (ROOT / 'rtl/common/ot_meso_fifo.sv').read_text()})
    assert K.unresolved_modules(good) == []


def test_gen_phys_landing_rtl_closes_the_ring_library():
    got = [p.name for p in gen_phys.landing_rtl(ROOT, TOP)]
    assert got == ['ot_dp_clk_landing.sv', 'ot_meso_fifo.sv']
    for p in gen_phys.landing_rtl(ROOT, TOP):
        assert p.is_file()


def test_blackbox_liberty_platform_guarded_dead_and_unreachable_pass(tmp_path):
    src = """module top(input wire clk, output wire y);
    m_bb u_bb (.a(clk), .y(y));
    m_lib u_lib (.a(clk));
    INVx1_ASAP7_75t_R u_inv (.A(clk), .Y());
    generate if (0) begin : g_bad
        never_defined_guard u_refuse ();
    end endgenerate
`ifdef NOT_SET
    never_defined_ifdef u_x ();
`else
    sub u_sub (.clk(clk));
`endif
endmodule
module sub(input wire clk);
    function automatic logic f(input logic a); f = a; endfunction
endmodule
module unused_mod(input wire a);
    never_defined_unreachable u_z (.a(a));
endmodule
"""
    k = kit(tmp_path, {'top.sv': src, 'm_bb.v': 'module m_bb(input a, output y);\nendmodule\n'},
            libs=[('m_lib_tt.lib', 'library(x) { cell (m_lib) { pin (a) { direction : input; } } }\n')])
    assert K.unresolved_modules(k) == []
    # mutant: the same names unguarded / live fail
    k2 = kit(tmp_path / 'm', {'top.sv': src.replace('`ifdef NOT_SET', '`ifdef SYNTHESIS')
                                             .replace('m_lib u_lib', 'm_gone u_lib'),
                               'm_bb.v': 'module m_bb(input a, output y);\nendmodule\n'})
    err = K.unresolved_modules(k2)
    assert any('never_defined_ifdef' in e for e in err) and any('m_gone' in e for e in err), err
    assert not any('never_defined_guard' in e or 'never_defined_unreachable' in e for e in err), err


def test_missing_top_fails(tmp_path):
    assert any('DESIGN_NAME' in e for e in K.unresolved_modules(kit(tmp_path, {'top.sv': TOP}, top='nope')))


def test_missing_include_fails_staged_include_passes(tmp_path):
    src = 'module top(input wire a, output wire y);\n`include "inc_tbl.svh"\n    assign y = a;\nendmodule\n'
    k = kit(tmp_path, {'top.sv': src})
    assert any('inc_tbl.svh' in e for e in K.unresolved_modules(k))
    (k / 'rtl' / 'inc_tbl.svh').write_text('// table\n')
    assert K.unresolved_modules(k) == []
    # a dead `ifdef include is not read by the flow
    k2 = kit(tmp_path / 'd', {'top.sv': src.replace('`include', '`ifdef NOPE\n`include').replace('.svh"', '.svh"\n`endif')})
    assert K.unresolved_modules(k2) == []


def test_gen_phys_stages_includes_transitively(tmp_path):
    s = tmp_path / 'src'
    s.mkdir()
    (s / 'a.sv').write_text('`include "b.svh"\nmodule a; endmodule\n')
    (s / 'b.svh').write_text('`include "c.svh"\n')
    (s / 'c.svh').write_text('// c\n')
    d = tmp_path / 'rtl'
    d.mkdir()
    gen_phys.stage_includes([str(s / 'a.sv')], d)
    assert sorted(p.name for p in d.iterdir()) == ['b.svh', 'c.svh']


def test_event_control_star_is_not_an_attribute(tmp_path):
    """QC-A0-KITS-3 10-28: `always @(*)` before a `(* keep *)` attribute made the attribute strip eat the text between
    them, so ot_qwen_w12_tadd (defined in between) read as undefined (node kit FAIL, false)."""
    src = """module top(input wire clk, input wire a, output reg y, output wire z);
    always @(*) begin
        y = a;
    end
    sub u_s (.a(a), .z(z));
endmodule
module sub(input wire a, output wire z);
    assign z = a;
endmodule
module other(input wire clk);
    (* keep *) reg r;
    always @( * ) r = clk;
endmodule
"""
    k = kit(tmp_path, {'top.sv': src})
    assert K.unresolved_modules(k) == []
    assert 'module sub' in K._strip_src(src) and 'keep' not in K._strip_src(src)
