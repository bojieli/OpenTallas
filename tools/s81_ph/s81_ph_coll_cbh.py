#!/usr/bin/env python3
"""el1011-ds-coll 2026-10-11 (owner TEXTBOOK AUDIT): pin plans of the HARDENED sub-elements of the collective core's
bottom tile (rtl/dsrom_sys/s81_ph/coll/dsfd_coll_cbh.sv), contract `contract_cbh`.  The cb outline (680.4 x 340.2) is
tiled W -> E by
    dsfd_coll_cbr  113.4  lane 0 relay pair  (lane group on its W face at the lane-core y, seam on its N face)
    dsfd_coll_cbf   64.8  f_vm pass-through  (f_vm on S, fvm_u on N, slice-0 header copy hq on E)
    dsfd_coll_cbq0  77.76 output-queue slice 0 (t_vm[419:0] + ts on S, bw_v / bw_d[419:1] / bw_cr / bw_flt on N)
    dsfd_coll_cbq   77.76 x 4 slices 1..4  (t_vm[420k +: 420] + ts on S, bw_v / bw_d slice on N, fault chain W/E)
    dsfd_coll_cbr  113.4  lane 4 relay pair  (the W master mirrored MY: its lane group lands on the E face)
Every tile has its own ck / rs (local clock tree), on its S face beside the VM pins (cbr: S face middle).
    s81_ph_coll_cbh.py      writes physical/s81_ph_views/ports/contract_cbh/<master>/{ports.json, io_place.tcl, ports.svh}"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_ph'))
import s81_ph_coll_tiles as T  # noqa: E402

T.CONTRACT = 'contract_cbh'


# 1-bit ports of these masters are scalars in the RTL (netlist pin `x`, not `x[0]`): emit them without the index
_emit = T.Plan.emit


def _emit_scalar(self, note):
    one = {p for p, (d, b) in self.dirs.items() if b == 1}
    self.pins = [((nm.split('[')[0],) if nm.split('[')[0] in one else (nm,)) + tuple(rest) for nm, *rest in self.pins]
    _emit(self, note)


T.Plan.emit = _emit_scalar
H = 340.2
WR, WF, WQ = 113.4, 64.8, 77.76
P = T.P


def ck(pl, face, at):
    pl.bus('ck', 1, 'input', face, 'M5' if face in 'NS' else 'M4', at)
    pl.bus('rs', 1, 'input', face, 'M5' if face in 'NS' else 'M4', at + 4.8)


def main():
    # lane relay pair: x_* = the lane tile's core face, n_* = the ce seam
    pr = T.Plan('dsfd_coll_cbr', WR, H)
    y = T.Y_CORE
    for p, b, d in [('x_lo_v', 1, 'output'), ('x_lo_r', 1, 'input'), ('x_lo_d', 553, 'output'), ('x_li_v', 1, 'input'),
                    ('x_li_r', 1, 'output'), ('x_li_d', 553, 'input'), ('x_flt', 3, 'input')]:
        y = pr.bus(p, b, d, 'W', 'M4', y)
    x = 2.4
    for p, b, d in [('n_lo_v', 1, 'input'), ('n_lo_r', 1, 'output'), ('n_lo_d', 553, 'input'), ('n_li_v', 1, 'output'),
                    ('n_li_r', 1, 'input'), ('n_li_d', 553, 'output'), ('n_flt', 3, 'output')]:
        x = pr.bus(p, b, d, 'N', 'M5', x)
    assert x < WR - 0.3, x
    ck(pr, 'S', WR / 2)
    pr.emit('cbh lane relay pair (2 x ot_s81ph_cr_relay RSL 8 PCR 1): W face lane group, N face ce seam')

    pf = T.Plan('dsfd_coll_cbf', WF, H)
    x = pf.bus('f_vm', 592, 'input', 'S', 'M5', 2.4)
    assert x < WF - 0.3, x
    x = pf.bus('fvm_u', 592, 'output', 'N', 'M5', 2.4)
    pf.bus('hq', 14, 'input', 'E', 'M4', H / 2)
    ck(pf, 'W', H / 2)
    pf.emit('cbh f_vm pass-through (2 registers; cbj: job endpoint between them)')

    # cbj: the same tile with the controller endpoint; c_* on the S face after f_vm (single-track pitch)
    pj = T.Plan('dsfd_coll_cbfj', WF, H)
    x = pj.bus('f_vm', 592, 'input', 'S', 'M5', 2.4)
    x = pj.bus('c_cmd', 85, 'input', 'S', 'M5', x, step=1)
    x = pj.bus('c_done', 9, 'output', 'S', 'M5', x, step=1)
    x = pj.bus('c_st', 2, 'output', 'S', 'M5', x, step=1)
    assert x < WF - 0.3, x
    pj.bus('fvm_u', 592, 'output', 'N', 'M5', 2.4)
    pj.bus('hq', 14, 'input', 'E', 'M4', H / 2)
    ck(pj, 'W', H / 2)
    pj.emit('cbh f_vm pass-through with the ot_s81_coll_job controller endpoint (dsfd_coll_cbj rebuild)')

    for m, v0 in (('dsfd_coll_cbq0', 1), ('dsfd_coll_cbq', 0)):
        pq = T.Plan(m, WQ, H)
        x = pq.bus('t_vm', 420, 'output', 'S', 'M5', 2.4)
        x = pq.bus('ts', 1, 'input', 'S', 'M5', x + 1.0)
        ck(pq, 'S', x + 2.0)
        x = pq.bus('bw_v', 1, 'input', 'N', 'M5', 2.4)
        x = pq.bus('bw_d', 419 if v0 else 420, 'input', 'N', 'M5', x)
        if v0:
            x = pq.bus('bw_cr', 1, 'output', 'N', 'M5', x)
            x = pq.bus('bw_flt', 1, 'output', 'N', 'M5', x)
            pq.bus('hq', 14, 'output', 'W', 'M4', H / 2)
        else:
            pq.bus('flt_o', 1, 'output', 'W', 'M4', H / 2)
        assert x < WQ - 0.3, (m, x)
        pq.bus('flt_i', 1, 'input', 'E', 'M4', H / 2)
        pq.emit('cbh output-queue slice (registered-head 16-deep FIFO, t_vm pin relay)' + (' 0 (valid, bw_cr, bw_flt, hq)' if v0 else ''))
    print('contract_cbh: dsfd_coll_cbr, dsfd_coll_cbf, dsfd_coll_cbq0, dsfd_coll_cbq')


if __name__ == '__main__':
    main()
