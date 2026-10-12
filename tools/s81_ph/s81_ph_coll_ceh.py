#!/usr/bin/env python3
"""el1011-ds-coll 2026-10-11: pin plans of the HARDENED sub-elements of the collective core's middle tile
(rtl/dsrom_sys/s81_ph/coll/dsfd_coll_ceh.sv), contract `contract_ceh` (physical spec: el1011-ds-coll.log, ce rebuild).
    dsfd_coll_ces0 / dsfd_coll_cesn  226.8 x 340.2  engine lane-slice (2 local-FIFO macros 256x256): bw on S (to cb),
                                     q + broadcasts on N (from ceq), remote landings on W (FIFO tiles), tx / credits /
                                     pass-through landings on E (lane tiles)
    dsfd_coll_cef                    405.6 x 280    remote FIFO tile (6 macros 256x256, 2 x 3): rx on W, slice links N
    dsfd_coll_cele 113.4 x 170.1 / dsfd_coll_celp 64.8 x 170.1  lane link: lane face W, core side E
    dsfd_coll_ceq                    300 x 680.4    VM queues (18 macros 128x256, 2 x 9): fvm_u S, streams E, rest W
    s81_ph_coll_ceh.py   -> physical/s81_ph_views/ports/contract_ceh/<master>/{ports.json, io_place.tcl, ports.svh}"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_ph'))
import s81_ph_coll_tiles as T  # noqa: E402

T.CONTRACT = 'contract_ceh'


# 1-bit ports of these masters are scalars in the RTL (netlist pin `x`, not `x[0]`): emit them without the index
_emit = T.Plan.emit


def _emit_scalar(self, note):
    one = {p for p, (d, b) in self.dirs.items() if b == 1}
    self.pins = [((nm.split('[')[0],) if nm.split('[')[0] in one else (nm,)) + tuple(rest) for nm, *rest in self.pins]
    _emit(self, note)


T.Plan.emit = _emit_scalar


LO = {'pe_i': 1, 'tx_v': 1, 'tx_rdy': 1, 'cr_i': 2, 'cr_o': 2}     # [hi:lo] ports of dsfd_coll_ces with lo != 0


def lay(pl, face, buses, start=2.4, step=2):
    layer = 'M5' if face in 'NS' else 'M4'
    x = start
    for p, b, d in buses:
        lo = LO.get(p, 0) if pl.m.startswith('dsfd_coll_ces') else 0
        x = pl.bus(p, b, d, face, layer, x, step=step, lo=lo, n=b)
    lim = pl.w if face in 'NS' else pl.h
    assert x < lim - 0.3, (pl.m, face, x, lim)
    return x


def ck(pl, face, at):
    lay(pl, face, [('ck', 1, 'input'), ('rs', 1, 'input')], start=at, step=50)


def main():
    for m, s0 in (('dsfd_coll_ces0', 1), ('dsfd_coll_cesn', 0)):
        pl = T.Plan(m, 226.8, 340.2)
        lay(pl, 'S', [('bw_v', 1, 'output'), ('bw_d', 563 if s0 else 512, 'output'), ('bw_cr', 1, 'input')])
        x = lay(pl, 'N', [('q_v', 1, 'input'), ('q_d', 162, 'input'), ('q_cr', 1, 'output'), ('e_en', 1, 'input'),
                          ('rank_i', 2, 'input'), ('qp', 6, 'input'), ('fv_i', 8, 'input'), ('lf', 2, 'output'),
                          ('pe_o', 1, 'output')] + ([('pe_i', 3, 'input')] if s0 else []))
        ck(pl, 'N', x + 4.8)
        lay(pl, 'W', [('xl_v', 8, 'input'), ('xl_d', 8 * 163, 'input'), ('xl_cr', 8, 'output')], start=4.8)
        lay(pl, 'E', [('tx_v', 3, 'output'), ('tx_d', 163, 'output'), ('tx_rdy', 3, 'input'), ('cr_i', 6, 'input'),
                      ('cr_o', 6, 'output'), ('pt_v', 5, 'input'), ('pt_d', 5 * (169 if s0 else 129), 'input'),
                      ('pt_cr', 5, 'output')], start=4.8, step=3)
        pl.emit('ceh engine lane-slice' + (' 0 (b_word header)' if s0 else ''))

    pf = T.Plan('dsfd_coll_cef', 405.6, 280.0)
    lay(pf, 'W', [('rx_v', 1, 'input'), ('rx_d', 547, 'input')], start=4.8)
    lay(pf, 'N', [('x_v', 2, 'output'), ('x_d', 8 * 163, 'output'), ('x_cr', 2, 'input')])
    x = lay(pf, 'S', [('e_en', 1, 'input'), ('flt', 1, 'output')], start=200.0)
    ck(pf, 'S', x + 4.8)
    pf.emit('ceh remote-source receive FIFO tile (2 parities x 3 macros)')

    for m, ep in (('dsfd_coll_cele', 1), ('dsfd_coll_celp', 0)):
        pl = T.Plan(m, 113.4 if ep else 64.8, 170.1)   # el1011 21:40: util 27% / 16% at 340.2 tall (textbook util_channel) -> 54% each
        lay(pl, 'W', [('f_lo_v', 1, 'output'), ('f_lo_r', 1, 'input'), ('f_lo_d', 553, 'output'), ('f_li_v', 1, 'input'),
                      ('f_li_r', 1, 'output'), ('f_li_d', 553, 'input'), ('x_flt', 3, 'input')], start=4.8)
        if ep:
            lay(pl, 'E', [('tx_v', 1, 'input'), ('tx_d', 4 * 163, 'input'), ('tx_rdy', 1, 'output'), ('cr_o', 2, 'input'),
                          ('cr_i', 2, 'output'), ('rx_v', 1, 'output'), ('rx_d', 547, 'output')], start=4.8)
            x = lay(pl, 'N', [('e_en', 1, 'input'), ('lf', 4, 'output')])
        else:
            lay(pl, 'E', [('q_v', 1, 'input'), ('q_d', 553, 'input'), ('q_cr', 1, 'output'), ('p_v', 1, 'output'),
                          ('p_d', 169 + 3 * 129, 'output'), ('p_cr', 1, 'input')], start=4.8)
            x = lay(pl, 'N', [('lf', 4, 'output')])
        ck(pl, 'N', x + 4.8)
        pl.emit('ceh lane link (' + ('engine port' if ep else 'pass-through') + ')')

    pq = T.Plan('dsfd_coll_ceq', 300.0, 680.4)
    lay(pq, 'S', [('fvm_u', 592, 'input')])
    lay(pq, 'E', [('q_v', 1, 'output'), ('q_d', 4 * 162, 'output'), ('q_cr', 1, 'input'), ('p_v', 5, 'output'),
                  ('p_d', 5 * 553, 'output'), ('p_cr', 5, 'input')], start=4.8, step=4)
    lay(pq, 'W', [('e_en', 1, 'output'), ('rank', 2, 'output'), ('qp', 6, 'output'), ('fv', 8, 'output'),
                  ('lane_f', 32, 'input'), ('slice_f', 8, 'input'), ('fifo_f', 3, 'input'), ('bw_flt', 1, 'input')], start=4.8)
    ck(pq, 'N', 150.0)
    pq.emit('ceh VM queue tile (6 queues in SRAM, broadcasts, fault collector)')
    # el1011-ds-coll 21:45: per-queue tiles (ceq split). 140.4 x 204.12: 3 macros 128x256 in one column, 20.25 um
    # channels; f_vm chain S (in) -> N (out) at identical x so abutted tiles connect straight; queue stream E.
    for m, q0 in (('dsfd_coll_ceq0', 1), ('dsfd_coll_ceqp', 0)):
        pt = T.Plan(m, 140.4, 204.12)
        lay(pt, 'S', [('fvm_u' if q0 else 'f_i', 592, 'input')] + ([] if q0 else [('qf_o', 1, 'output')]), step=4)
        lay(pt, 'N', [('f_o', 592, 'output'), ('qf_i', 1, 'input')], step=4)
        if q0:
            lay(pt, 'E', [('q_v', 1, 'output'), ('q_d', 4 * 162, 'output'), ('q_cr', 1, 'input')], start=4.8, step=4)
            x = lay(pt, 'W', [('e_en', 1, 'output'), ('rank', 2, 'output'), ('qp', 1, 'output'), ('fv', 8, 'output'),
                              ('lane_f', 32, 'input'), ('slice_f', 8, 'input'), ('fifo_f', 3, 'input'),
                              ('bw_flt', 1, 'input')], start=4.8)
        else:
            lay(pt, 'E', [('p_v', 1, 'output'), ('p_d', 553, 'output'), ('p_cr', 1, 'input')], start=4.8, step=4)
            x = lay(pt, 'W', [('lid', 3, 'input'), ('qp', 1, 'output')], start=4.8)
        ck(pt, 'W', x + 4.8)
        pt.emit('ceh VM queue tile (' + ('queue 0 + rank/enable + fault collector' if q0 else 'one pass-through queue') + ')')
    print('contract_ceh: dsfd_coll_ces0, dsfd_coll_cesn, dsfd_coll_cef, dsfd_coll_cele, dsfd_coll_celp, dsfd_coll_ceq, dsfd_coll_ceq0, dsfd_coll_ceqp')


if __name__ == '__main__':
    main()
