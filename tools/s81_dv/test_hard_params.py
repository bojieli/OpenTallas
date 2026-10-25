"""PATH-S81/F2 10-25: stripped hard-child overrides are recorded (hard_params sidecar) and baked into the bind stubs."""
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT / 'tools/die_plan')]
import hard_params as HP  # noqa: E402
import bind_elab as E  # noqa: E402

ELEM = '''module elem #(
    parameter integer NB = 1,   // lanes
    parameter integer MTP = 0,
    parameter INSTANCE = ""
) (input wire clk, output wire [32*NB-1:0] pval, output wire [NB-1:0] pv);
  assign pval = 0; assign pv = 0;
endmodule
'''
FRAME = '''module frame (input wire clk, output wire [63:0] a, output wire [63:0] b);
    elem #(.NB(2), .MTP(1), .INSTANCE("u_e0")) u_e0 (.clk(clk), .pval(a), .pv());
    elem #(.NB(2), .MTP(1), .INSTANCE("u_e1")) u_e1 (.clk(clk), .pval(b), .pv());
    soft #(.W(3)) u_s (.clk(clk));
endmodule
'''


def _stub_widths(stub, mod):
    """pval width of the stub under its own parameter defaults (enough for the NB-scaled ports here)"""
    body = stub[stub.index(f'module {mod}'):]
    nb = int(re.search(r'\bNB\s*=\s*(\d+)', body).group(1))
    return 32 * nb


def test_strip_records_hardened_set():
    t2, n, params, sites = HP.strip_hard(FRAME, {'elem'}, 'frame')
    assert n == 3 and sites == {'elem': 2}                       # n = every #() site seen (kit header count)
    assert params == {'elem': {'MTP': '1', 'NB': '2'}}           # INSTANCE is a label, never baked
    assert 'elem u_e0 (' in t2 and 'elem #(' not in t2
    assert 'soft #(.W(3)) u_s' in t2                               # soft children keep their overrides


def test_strip_fails_closed_on_two_configs():
    bad = FRAME.replace('elem #(.NB(2), .MTP(1), .INSTANCE("u_e1"))', 'elem #(.NB(1), .MTP(1), .INSTANCE("u_e1"))')
    with pytest.raises(SystemExit, match='two configurations'):
        HP.strip_hard(bad, {'elem'}, 'frame')


def test_strip_fails_closed_on_non_constant():
    bad = FRAME.replace('.NB(2), .MTP(1), .INSTANCE("u_e0")', '.NB(NBP), .MTP(1), .INSTANCE("u_e0")')
    with pytest.raises(SystemExit, match='not a constant'):
        HP.strip_hard(bad, {'elem'}, 'frame')


def test_strip_fails_closed_on_positional():
    bad = FRAME.replace('.NB(2), .MTP(1), .INSTANCE("u_e0")', '2, 1, "u_e0"')
    with pytest.raises(SystemExit, match='positional'):
        HP.strip_hard(bad, {'elem'}, 'frame')


def test_bind_stub_baked_vs_mutant(tmp_path):
    """the as-built bind black box takes the hardened interface (64-bit pval, NB=2); the MUTANT = the pre-fix flow
    (overrides stripped, nothing recorded) gives the RTL-default 32-bit stub that tied lane 1 of every qbank"""
    src = tmp_path / 'elem.sv'
    src.write_text(ELEM)
    _, _, params, sites = HP.strip_hard(FRAME, {'elem'}, 'frame')
    sc = tmp_path / 'frame_kit.hard_params.json'
    HP.write_sidecar(sc, params, sites, 'frame.sv', FRAME)
    hp = E.load_hard_params([str(sc)])
    good = Path(E.lib_stubs([str(src)], tmp_path / 'good.sv', hp)).read_text()
    mutant = Path(E.lib_stubs([str(src)], tmp_path / 'mutant.sv')).read_text()
    assert _stub_widths(good, 'elem') == 64
    assert _stub_widths(mutant, 'elem') == 32
    assert re.search(r'parameter integer MTP = 1', good) and 'INSTANCE = ""' in good


def test_bind_fails_closed_on_undeclared_param(tmp_path):
    src = tmp_path / 'elem.sv'
    src.write_text(ELEM)
    with pytest.raises(E.ElabError, match='declared 0 times'):
        E.lib_stubs([str(src)], tmp_path / 'o.sv', {'elem': {'NBX': '2'}})


def test_bind_fails_closed_on_missing_leaf(tmp_path):
    src = tmp_path / 'elem.sv'
    src.write_text(ELEM)
    with pytest.raises(E.ElabError, match='no leaf'):
        E.lib_stubs([str(src)], tmp_path / 'o.sv', {'other': {'NB': '2'}})
    # a hard master with nothing stripped needs no stub
    E.lib_stubs([str(src)], tmp_path / 'o.sv', {'other': {}})


def test_conflicting_sidecars_fail(tmp_path):
    a, b = tmp_path / 'a.json', tmp_path / 'b.json'
    HP.write_sidecar(a, {'elem': {'NB': '2'}}, {'elem': 1}, 'a.sv', '')
    HP.write_sidecar(b, {'elem': {'NB': '1'}}, {'elem': 1}, 'b.sv', '')
    with pytest.raises(E.ElabError, match='different hardened sets'):
        E.load_hard_params([str(a), str(b)])


LPDIR = ROOT / 'rtl/dsrom_sys/s81_dv/frame_lp'


@pytest.mark.parametrize('master', ['col_h9', 'col_h10'])
def test_committed_vg_sidecar_matches_source(master):
    """the committed sidecar is what strip_hard derives from the vg LP RTL today, the q element is the NB=2 view, and
    the committed kit carries no #() on any recorded hard master"""
    sc = LPDIR / 'kit' / f'{master}_l4_lp_kit_vg.hard_params.json'
    src = LPDIR / 'vg' / f'{master}_l4_lp.sv'
    if not (sc.exists() and src.exists()):
        pytest.skip('frame_lp not in this checkout')
    rec = json.loads(sc.read_text())
    t = src.read_text()
    _, n, params, sites = HP.strip_hard(t, set(rec['masters']), str(src))
    assert params == rec['masters'] and sites == rec['sites']
    assert rec['masters']['ot_v41_rom_elem_q_qxpq_w10']['NB'] == '2'
    kit = (LPDIR / 'kit' / f'{master}_l4_lp_kit_vg.sv').read_text()
    for m in rec['masters']:
        assert not re.search(rf'^\s*{m}\s*#\(', kit, re.M), m
