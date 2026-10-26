"""Synthetic unit tests of bound_l14_stim (classification mechanics only; not token evidence)."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bound_l14_stim as S  # noqa: E402

TOP = """module s81_bound_top;
    wire [4:0] x_pa_o0_pb;  // lane la
    wire [4:0] x_pb_ft0_o_pc;  // lane la
    wire [2:0] x_pc_o1_pd;  // lane lb
    wire [2:0] x_pd_ft1_o_pc;  // lane lb
    wire [1:0] x_pe_o0_pc;  // lane lc
    s81p_a__t1 pa (
    s81p_ft__t1 pb (
    s81p_c__t1 #(.S_x(1'b1)) pc (
    s81p_ft__t1 pd (
    s81p_a__t1 pe (
endmodule
"""
MOD_A = """module s81p_a__t1 (
    output wire [4:0] o0,   // 4 data + epoch [4]: lane la
);
    ot_dp_st #(.W(4)) u_bout_o0 (.clk(clk));
endmodule
"""
MOD_FT = """module s81p_ft__t1 (
    output wire [4:0] ft0_o,   // ft ft0: 3 station(s)
    output wire [2:0] ft1_o,   // ft ft1: 2 station(s)
);
endmodule
"""
MOD_C = """module s81p_c__t1 (
);
    ot_dp_st #(.W(2)) u_bout_o1 (.clk(clk));
    ot_rom_4096x72_m8 #(.INSTANCE(""), .VIAMAP("")) u_u_c0_0 (
endmodule
"""


def bit(path, port, n):
    return [['leaf', path, port, i] for i in range(n)]


def make(tmp, events, tied=0, lowering=None):
    b = tmp / 'bound'
    (b / 'rtl').mkdir(parents=True)
    (b / 'rtl/s81_bound_top.sv').write_text(TOP)
    (b / 'rtl/s81p_a__t1.sv').write_text(MOD_A)
    (b / 'rtl/s81p_ft__t1.sv').write_text(MOD_FT)
    (b / 'rtl/s81p_c__t1.sv').write_text(MOD_C)
    (b / 'bind_report.json').write_text(json.dumps(dict(n_errors=0, errors=[], type_splits={}, proof=dict(tied=tied))))
    buses = [dict(lane='la', src='pa', dst='pc', width=4, source_bits=bit('u_a', 'o', 4), bound_stages=6),
             dict(lane='lb', src='pc', dst='pc', width=2, source_bits=bit('u_c', 'q', 2), bound_stages=4),
             dict(lane='lc', src='pe', dst='pc', width=1, source_bits=bit('u_e', 'z', 1), bound_stages=2)]
    (b / 'bind_latency.json').write_text(json.dumps(dict(buses=buses)))
    (b / 'bind_names.json').write_text(json.dumps({'pc.u_core': 'u_seqhost', 'pc.u_u_c0_0': 'u_f_0L01.u_c0_0'}))
    top_sha = hashlib.sha256(TOP.encode()).hexdigest()
    carve = dict(schema='opentallas.tok_qw.bound_carve.v1', top_sha256=top_sha, seeds={'pc': 's81p_c__t1'},
                 inputs={'clk_core': dict(width=1, lane=None, readers=['pc.clk']),
                         'x_pb_ft0_o_pc': dict(width=5, lane='la', readers=['pc.a_i']),
                         'x_pd_ft1_o_pc': dict(width=3, lane='lb', readers=['pc.b_i']),
                         'x_pe_o0_pc': dict(width=2, lane='lc', readers=['pc.c_i'])},
                 outputs={'x_pc_o1_pd': dict(width=3, lane='lb', drivers=['pc.o1'])}, internal={})
    (tmp / 'carve.json').write_text(json.dumps(carve))
    p = tmp / 'prog'
    (p / 'prog').mkdir(parents=True)
    (p / 'prog/host_boot.memh').write_text('1\n')
    (p / 'schedule.json').write_text(json.dumps(dict(layer='L14', price=dict(span=100.0, crit=90.0),
                                                     ops=[dict(start=0, end=100, critical=True)], events=events, links={})))
    (p / 'lowering.json').write_text(json.dumps(dict(ops=lowering or [])))
    (p / 'manifest.json').write_text('{}')
    return b, tmp / 'carve.json', p


def ev(inst, port, words, **kw):
    return dict(dict(cycle=words[0][0], inst=inst, port=port, dir='out', kind='T', tag='t', words=words), **kw)


def test_derivable_word_epoch_and_port_edge(tmp_path):
    b, c, p = make(tmp_path, [ev('u_a', 'o', [[10, '5', 'f']]), ev('u_c', 'q', [[20, '2', '3']])])
    s = S.build(b, c, p)
    r = s['inputs']['x_pb_ft0_o_pc']
    assert r['class'] == 'DERIVABLE'
    assert r['stations_to_port'] == 1 + 3          # source out flop + 3 ft stations
    assert r['words'] == [dict(edge=10, port_edge=14, word_hex='15')]   # data 0x5 + epoch bit 4
    assert s['inputs']['clk_core']['class'] == 'CLOCK'
    assert s['inputs']['x_pd_ft1_o_pc']['class'] == 'LOOPBACK_FT'
    assert s['inputs']['x_pe_o0_pc']['class'] == 'MISSING'
    assert 'u_e' in s['inputs']['x_pe_o0_pc']['reason']
    o = s['outputs']['x_pc_o1_pd']
    assert o['class'] == 'DERIVABLE' and o['expected'][0]['port_edge'] == 21 and o['expected'][0]['word_hex'] == '6'


def test_mask_and_plan_only_are_not_values(tmp_path):
    b, c, p = make(tmp_path, [ev('u_a', 'o', [[10, '5', '7']])])
    assert S.build(b, c, p)['inputs']['x_pb_ft0_o_pc']['class'] == 'MISSING'
    b, c, p = make(tmp_path / 'q', [ev('u_a', 'o', [[10, '5', 'f']], plan_only=True)])
    r = S.build(b, c, p)['inputs']['x_pb_ft0_o_pc']
    assert r['class'] == 'MISSING' and 'plan-only' in r['reason']


def test_multi_pin_event_split(tmp_path):
    # event over ports [v(1 bit, not on this lane), o(4)] : o = bits 1..4
    widths_event = ev('u_a', 'o', [[3, str(hex((0xA << 1) | 1))[2:], '1f']], ports=['v', 'o'])
    b, c, p = make(tmp_path, [widths_event])
    lat = json.loads((b / 'bind_latency.json').read_text())
    lat['buses'].append(dict(lane='lv', src='pa', dst='pz', width=1, source_bits=bit('u_a', 'v', 1), bound_stages=1))
    (b / 'bind_latency.json').write_text(json.dumps(lat))
    r = S.build(b, c, p)['inputs']['x_pb_ft0_o_pc']
    assert r['class'] == 'DERIVABLE' and r['words'][0]['word_hex'] == '1a'


def test_idle_only_when_fully_lowered(tmp_path):
    low = [dict(status='LOWERED', insts=['u_e (m)'])]
    b, c, p = make(tmp_path, [], lowering=low)
    assert S.build(b, c, p)['inputs']['x_pe_o0_pc']['class'] == 'IDLE_BY_SCHEDULE'
    b, c, p = make(tmp_path / 'g', [], lowering=[dict(status='GAP', insts=['u_e (m)'])])
    assert S.build(b, c, p)['inputs']['x_pe_o0_pc']['class'] == 'MISSING'


def test_strict_bind_and_top_identity_required(tmp_path):
    b, c, p = make(tmp_path, [], tied=3)
    with pytest.raises(ValueError):
        S.build(b, c, p)
    b, c, p = make(tmp_path / 'x', [])
    carve = json.loads(c.read_text())
    carve['top_sha256'] = '0' * 64
    c.write_text(json.dumps(carve))
    with pytest.raises(ValueError):
        S.build(b, c, p)


def test_load_map_and_rom_instance(tmp_path):
    b, c, p = make(tmp_path, [])
    s = S.build(b, c, p)
    hb = [r for r in s['prog_load_map'] if r['file'] == 'prog/host_boot.memh'][0]
    assert hb['status'] == 'MAPPED_IN_CARVE'
    assert hb['consumers'][0]['partitions'][0] == dict(partition='pc', module='s81p_c__t1', in_carve=True)
    assert s['rom_images']['n'] == 1 and s['rom_images']['empty_instance'] == 1
    assert s['rom_images']['status'].startswith('BLOCKED')
    assert s['rom_images']['macros'][0]['original'] == 'u_f_0L01.u_c0_0'


def test_ev_files(tmp_path):
    b, c, p = make(tmp_path, [ev('u_a', 'o', [[10, '5', 'f']])])
    s = S.build(b, c, p, t0=100)
    S.write_ev(s, tmp_path / 'ev', 100)
    assert (tmp_path / 'ev/stim/x_pb_ft0_o_pc.ev').read_text() == '115 15\n'
    assert not (tmp_path / 'ev/stim/x_pe_o0_pc.ev').exists()
