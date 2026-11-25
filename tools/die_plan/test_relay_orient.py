"""relay_orient: hop -> orientation, chain last-stage sink, tcl rewrite (bbox-normalized ot_seat_o)."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import relay_orient as R


def test_orient_for_hop_default_faces():
    assert R.orient_for_hop(100, -100) == 'R0'      # east + south = native R0 flow
    assert R.orient_for_hop(-100, -100) == 'MY'     # west
    assert R.orient_for_hop(100, 100) == 'MX'       # north
    assert R.orient_for_hop(-100, 100) == 'R180'    # west + north
    assert R.orient_for_hop(-3, 3) == 'R0'          # inside tol: keep
    assert R.orient_for_hop(0, 400) == 'MX'


def test_orient_for_hop_other_faces():
    assert R.orient_for_hop(100, 100, out_faces=('W', 'N')) == 'MY'
    assert R.orient_for_hop(-100, 100, out_faces=('W', 'N')) == 'R0'


def test_chain_uses_sink_then_previous_hop():
    pts = [(0, 0), (-300, 0), (-300, 300)]
    assert R.chain_orients(pts, sink=(0, 300)) == ['MY', 'MX', 'R0']
    assert R.chain_orients(pts, sink=None) == ['MY', 'MX', 'MX']


def _seats():
    return {
        'hard_seats': [{'elaborated_path': 'u_bank.g_kve[3].genblk2.g_npc.u_kve', 'origin_um': [0, 1000],
                        'outline_um': [100, 100]}],
        'relay_seats': [
            {'master': 'kvi', 'engine': 3, 'stage': 1, 'origin_um': [500, 600], 'outline_um': [34.56, 34.56],
             'elaborated_path': 'u_bank.g_kve[3].g_input_relay[1].u_relay'},
            {'master': 'kvi', 'engine': 3, 'stage': 0, 'origin_um': [900, 600], 'outline_um': [34.56, 34.56],
             'elaborated_path': 'u_bank.g_kve[3].g_input_relay[0].u_relay'}],
        'exit_relay_seats': [
            {'master': 'kvx', 'chain': 'q', 'block': 0, 'stage': 0, 'origin_um': [100, 100],
             'outline_um': [51.84, 51.84], 'elaborated_path': 'u_bank.g_kvq[0].g_exit_relay[0].u_relay'},
            {'master': 'kvx', 'chain': 'q', 'block': 0, 'stage': 1, 'origin_um': [500, 0],
             'outline_um': [51.84, 51.84], 'elaborated_path': 'u_bank.g_kvq[0].g_exit_relay[1].u_relay'}]}


def test_orient_seats_and_tcl_positions_override():
    s = _seats()
    o = R.orient_seats(s)
    assert o['u_bank.g_kve[3].g_input_relay[0].u_relay'] == 'MY'      # stage0 -> stage1 goes west
    assert o['u_bank.g_kve[3].g_input_relay[1].u_relay'] == 'R180'    # stage1 -> engine goes west + north
    assert o['u_bank.g_kvq[0].g_exit_relay[0].u_relay'] == 'R0'       # east + south
    assert o['u_bank.g_kvq[0].g_exit_relay[1].u_relay'] == 'R0'       # last: keeps previous hop
    tcl = 'ot_seat {u_bank.g_kve\\[3\\].g_input_relay\\[0\\].u_relay} 100 600\n'
    o2 = R.orient_seats(s, R.tcl_positions(tcl))                        # tcl moves stage 0 west of stage 1
    assert o2['u_bank.g_kve[3].g_input_relay[0].u_relay'] == 'R0'


def test_rewrite_tcl_adds_proc_once_and_keeps_r0_lines():
    tcl = ('set blk [ord::get_db_block]\nproc ot_seat {name x y} { global blk }\n'
           'ot_seat {u_bank.g_kve\\[3\\].g_input_relay\\[0\\].u_relay} 900 600\n'
           'ot_seat {u_bank.g_kvq\\[0\\].g_exit_relay\\[0\\].u_relay} 100 100\n')
    out = R.rewrite_tcl(tcl, R.orient_seats(_seats(), R.tcl_positions(tcl)))
    assert 'ot_seat_o {u_bank.g_kve\\[3\\].g_input_relay\\[0\\].u_relay} 900 600 MY' in out
    assert 'ot_seat {u_bank.g_kvq\\[0\\].g_exit_relay\\[0\\].u_relay} 100 100' in out
    assert out.count('proc ot_seat_o') == 1 and out.index('proc ot_seat_o') < out.index('proc ot_seat {')
    assert R.rewrite_tcl(out, {}).count('proc ot_seat_o') == 1


def test_cli_roundtrip(tmp_path):
    p = tmp_path / 's.json'; p.write_text(json.dumps(_seats()))
    q = tmp_path / 'o.json'
    assert R.main(['--seats', str(p), '--out', str(q)]) == 0
    d = json.loads(q.read_text())
    assert {s['elaborated_path']: s['orient'] for s in d['relay_seats']}['u_bank.g_kve[3].g_input_relay[0].u_relay'] == 'MY'
