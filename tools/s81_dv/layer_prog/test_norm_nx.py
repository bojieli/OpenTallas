#!/usr/bin/env python3
"""TOK-DS-GAPS 10-24: tests of layer_prog/norm_nx.py and the dv_cut_replay hooks it uses (pure python, no simulator).

1. flit_ports / nxb follow ot_s81sl_rstop (map_e / map_w snake ends, tier port roles, header fields); the fc31 L0
   cut_0S zero-data trace headers are 0x77 (vo, hops 7) and 0x87 (ro_e, hops 8).
2. dv_cut_replay.event_words honours `width` (a one-lane flit on a 4-lane port: bundle age = lane 0's).
3. dv_cut_replay.ctl_beat drives a payload186 CTL event as the seq_host line beat with the line hops / src rewrite.
   python3 tools/s81_dv/layer_prog/test_norm_nx.py   (exit 0 = PASS)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import norm_nx as N  # noqa: E402
import dv_cut_replay as R  # noqa: E402


def t_ports():
    assert N.flit_ports(0) == {'vo': 7, 'ro_e': 8}          # 0S: W side on V (map_w), E line carries eo
    assert N.flit_ports(1) == {'vo': 8, 'ro_e': 7}          # 0N: E side (snake fwd = physical W) on V
    assert N.flit_ports(14) == {'vo': 8, 'ro_w': 7}         # 7S
    assert N.flit_ports(15) == {'vo': 7, 'ro_w': 8}         # 7N
    assert N.flit_ports(6) == {'ro_e': 8, 'ro_w': 7} and N.flit_ports(7) == {'ro_e': 7, 'ro_w': 8}
    assert N.nxb(0, 7, 0) == 0x77 and N.nxb(0, 8, 0) == 0x87   # trace headers (fc31 run_data L0 cut_0S)
    v = N.nxb(5, 8, 0xABC)
    assert v & 1 and (v >> 1) & 7 == 3 and (v >> 4) & 0x1F == 8 and (v >> 9) & 0xF == 5 and (v >> 13) & 0xFF == 25
    assert v >> 21 == 0xABC and v.bit_length() <= N.LANE
    print('PASS flit ports / header')


class Die:
    """two-instance stub: u_a.ro (8 b = 4 lanes of 2 b, ages 3 5 4 6) -> u_b"""
    def __init__(self):
        self.links = {f'l{i}': dict(age=a, src=[('u_a', 'ro')], dst=[('u_b', 'ri')], out_net=f'w_l{i}_lnd')
                      for i, a in enumerate((3, 5, 4, 6))}
        self.by_out = {f'w_l{i}_{k}': f'l{i}' for i in range(4) for k in ('src', 'lnd')}

    def port_bits(self, inst, port):
        return [(f'w_l{b // 2}_src', b % 2) for b in range(8)]

    def sid(self, inst):
        return {'u_s_4S': 8}[inst]


def t_width():
    d = Die()
    e = dict(kind='NX', tag='t', inst='u_a', port='ro', ports=['ro'], dir='out', words=[[10, '3', '3']])
    full = R.event_words(e, d)
    one = R.event_words(dict(e, width=2), d)
    assert full[0]['cycle_land'] == 16 and len(full[0]['bits']) == 8      # slowest lane (6)
    assert one[0]['cycle_land'] == 13 and set(one[0]['bits']) == {('w_l0_lnd', 0), ('w_l0_lnd', 1)}
    print('PASS event width')


def t_payload186():
    d = Die()
    p = 0x1234 | 5 << 16
    ev = dict(kind='CTL', payload=f'entry {p:047x}', payload186=f'{p:047x}', port='ri_e', inst='u_s_0S')
    beat, ti, hops, src = R.ctl_beat({}, ev, d, 'u_s_0S')
    assert ti is None and hops == 1 and src == 8 and beat >> 21 == p and beat & 1 and (beat >> 4) & 0x1F == 1
    print('PASS payload186 CTL beat')


if __name__ == '__main__':
    R.lane_of_net = lambda die, net: net[2:-4] if net.startswith('w_') and net[2:-4] in die.links else None
    t_ports()
    t_width()
    t_payload186()
    print('test_norm_nx: ALL PASS')
