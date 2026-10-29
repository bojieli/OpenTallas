"""TOK-KV-1 10-28: gen_kvpc_rst_diag.py derives the kvpc reset-spine force list from the bound top (no hand-kept copy)."""
import subprocess, sys
from pathlib import Path

H = Path(__file__).resolve().parent
TOP = """module qwen_kvsys_bound_top;
    wire [0:0] x_hub_Wi_rs_host_die_rst_n_81_pc_EN_0;  // reset spine
    wire [0:0] x_hub_Wi_rs_host_die_rst_n_97_pc_WS_3;  // reset spine
    wire [0:0] x_hub_Wi_rs_host_hbm_rst_n_4_pc_EN_0;  // reset spine
    wire [1:0] x_hub_Wi_o_host_hbm_rst_n_hub_C;
endmodule
"""


def run(tmp, text):
    top = tmp / 'top.sv'; top.write_text(text); out = tmp / 'd.svh'
    r = subprocess.run([sys.executable, '-I', str(H / 'gen_kvpc_rst_diag.py'), str(top), str(out)], capture_output=True, text=True)
    return r, out


def test_spines_follow_same_slot_hbm_spine_else_lane(tmp_path):
    r, out = run(tmp_path, TOP)
    assert r.returncode == 0, r.stderr
    t = out.read_text()
    assert 'force dut.x_hub_Wi_rs_host_die_rst_n_81_pc_EN_0 = dut.x_hub_Wi_rs_host_hbm_rst_n_4_pc_EN_0;' in t
    assert 'force dut.x_hub_Wi_rs_host_die_rst_n_97_pc_WS_3 = dut.x_hub_Wi_o_host_hbm_rst_n_hub_C[0];' in t
    assert t.count('force ') == 2


def test_no_spine_fails(tmp_path):
    r, _ = run(tmp_path, 'module qwen_kvsys_bound_top; endmodule\n')
    assert r.returncode != 0


if __name__ == '__main__':
    import tempfile
    for t in (test_spines_follow_same_slot_hbm_spine_else_lane, test_no_spine_fails):
        with tempfile.TemporaryDirectory() as d:
            t(Path(d))
        print('PASS', t.__name__)
