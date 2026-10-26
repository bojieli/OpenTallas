from pathlib import Path
import lec


def test_only_source_declared_genvars_are_removed(tmp_path):
    p = tmp_path / 'macros.sv'
    p.write_text('module hard #(parameter W=8)(input ck); genvar gf, gz; localparam N=4; endmodule\nmodule other; genvar nope; endmodule')
    env = dict(VERILOG_FILES=str(p), SYNTH_BLACKBOXES='hard')
    assert lec.blackbox_local_constant_cleanup(env, tmp_path) == ['setparam -unset N t:hard', 'setparam -unset gf t:hard', 'setparam -unset gz t:hard']


def test_ambiguous_source_declarations_do_not_strip(tmp_path):
    a, b = tmp_path / 'a.sv', tmp_path / 'b.sv'
    a.write_text('module hard; genvar gf; endmodule')
    b.write_text('module hard; parameter gf=4; endmodule')
    assert lec.blackbox_local_constant_cleanup(dict(VERILOG_FILES=f'{a} {b}', SYNTH_BLACKBOXES='hard'), tmp_path) == []


def test_comments_and_other_modules_do_not_declare_genvars(tmp_path):
    p = tmp_path / 'a.sv'
    p.write_text('module hard; /* genvar gf; */ // genvar gz;\n parameter W=8; initial $display("localparam W=99; genvar W;"); endmodule\nmodule other; genvar gf; endmodule' )
    assert lec.blackbox_local_constant_cleanup(dict(VERILOG_FILES=str(p), SYNTH_BLACKBOXES='hard'), tmp_path) == []
