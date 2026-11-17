from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_preflight as kp


def kit(tmp_path, q='rst_rl_7', tree=True):
    (tmp_path/'config.mk').write_text('export DESIGN_NAME = top\nexport VERILOG_FILES = /work/top.sv\n')
    (tmp_path/'top.sv').write_text(f'module top; ot_dp_rrelay u_rrl_7 (.clk(clk), .d(d), .q({q})); endmodule\n')
    if tree:
        (tmp_path/'reset_tree.tcl').write_text('rtr_place rst_rl_7 {*u_rrl_7[./]*} 10 20 rrl:wire1\n')
    return tmp_path


def test_coherent(tmp_path):
    assert kp.reset_tree_coherence(kit(tmp_path)) == []


def test_renumbered_tree_mutant(tmp_path):
    errors = kp.reset_tree_coherence(kit(tmp_path, q='rst_n_t0'))
    assert len(errors) == 1 and 'rst_n_t0' in errors[0]


def test_missing_relay(tmp_path):
    k = kit(tmp_path)
    (k/'top.sv').write_text('module top; endmodule\n')
    assert 'MISSING/AMBIGUOUS' in kp.reset_tree_coherence(k)[0]


def test_other_module_same_name_ignored(tmp_path):
    k = kit(tmp_path)
    with (k/'top.sv').open('a') as f:
        f.write('module child; ot_dp_rrelay u_rrl_7 (.q(other)); endmodule\n')
    assert kp.reset_tree_coherence(k) == []


def test_no_tree_unchanged(tmp_path):
    assert kp.reset_tree_coherence(kit(tmp_path, tree=False)) == []


def test_start_relay(tmp_path):
    k = kit(tmp_path)
    (k/'top.sv').write_text('module top; ot_dp_rrelay u_srl_2 (.clk(clk), .d(d), .q(rn_rst_rl_2)); endmodule\n')
    (k/'reset_tree.tcl').write_text('rtr_place rn_rst_rl_2 {*u_srl_2[./]*} 10 20 rrl:wire1\n')
    assert kp.reset_tree_coherence(k) == []
