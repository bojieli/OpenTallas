"""TOK-QW-5: qc_rom_load.py turns tile ROM_TILE defparams into per-leaf hierarchical $readmemh lines."""
import subprocess, sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent / 'current_path' / 'qc_rom_load.py'


def run(tmp, bind, prog=None, tiles=2):
    b = tmp / 'bind.vh'; b.write_text(bind)
    args = [sys.executable, str(TOOL), '--rom-bind', str(b), '--expect-tiles', str(tiles), '--out', str(tmp / 'o.vh')]
    if prog is not None:
        (tmp / 'p.txt').write_text(prog); args += ['--prog', str(tmp / 'p.txt')]
    return subprocess.run(args, capture_output=True, text=True)


def test_tiles_opseg_prog(tmp_path):
    r = run(tmp_path, 'defparam tb.u.c0.u_u_t_0_0.ROM_TILE = 384;\ndefparam tb.u.c0.u_u_t_0_1.ROM_TILE = 386;\n'
            'defparam tb.u.tt.u_core.\\u_gi.g_op.u_rom .INSTANCE = "qfd_tt_ctlm_opseg";\n',
            '# c\ntb.u.tt.u_core.\\u_gi.u_cal.m0 calendar_m0\ntb.u.sl.u_ld.m0 table_s0_m0\n')
    assert r.returncode == 0, r.stderr
    o = (tmp_path / 'o.vh').read_text()
    assert o.count('$readmemh') == 2 * 10 + 1 + 2
    assert ('"/qtile_t386_b4_c1.viamap.hex"}, tb.u.c0.u_u_t_0_1.u_g.u_tile.u_tile.u_logic.g_rom_pipe.g_rph.g_rb[4]'
            '.g_single.g_col[1].u_leaf.u_rom.arr);') in o
    assert 'tb.u.tt.u_core.\\u_gi.g_op.u_rom .arr);' in o          # escaped identifier ends at white space
    assert 'tb.u.tt.u_core.\\u_gi.u_cal.m0 .arr);' in o
    assert '+OT_TB_ROM_DIR' in o and 'OT_ROM_DIR=")) $fatal' in o


def test_refuses_bad_input(tmp_path):
    assert run(tmp_path, 'defparam tb.a.ROM_TILE = 1;\ndefparam tb.b.ROM_TILE = 1;\n').returncode != 0   # duplicate tile
    assert run(tmp_path, 'defparam tb.a.ROM_TILE = 1;\n').returncode != 0                                 # tile count
    assert run(tmp_path, 'defparam tb.a.ROM_TILE = 1;\ndefparam tb.b.FOO = 2;\n', tiles=1).returncode != 0  # unknown defparam
