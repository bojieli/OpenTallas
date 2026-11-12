#!/usr/bin/env python3
"""ISS2E issuer pad mask (-DOT_COLL_ISS8E_PAD_MASK) as ONE per-parent bit -> edge-parity map, for every programme the parent runs.

ISS2E (ot_hgi_coll_issuer_m256v8e) issues one row every 2nd edge; every field of a row leaves the issuer on the same pipe.  A
field whose v8 edge offset (from the programme's reference field, parity 0) is odd therefore needs its bits delayed one edge
(mask bit = 1).  The mask is one build define, so the ARGMAX and ROW_GATHER programmes of a parent must agree bit by bit; a
bit that one programme needs padded and another unpadded is a CONFLICT (union() raises).  Layout bit positions are
static_uop_layout_v4.json."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
LAYOUT = json.loads((ROOT / 'rtl/hbm_accel/generic/collective/p2p/static_uop_layout_v4.json').read_text())['fields']


def field_bits(name, lo=0, n=None):
    f = LAYOUT[name]
    n = f['width'] - lo if n is None else n
    return range(f['lsb'] + lo, f['lsb'] + lo + n)


def mark(m, parity, name, lo=0, n=None, nib=None):
    """bits of field `name` (bits lo..lo+n-1, or nibbles nib=(first, count)) get edge parity `parity`"""
    if nib:
        lo, n = 4 * nib[0], 4 * nib[1]
    for b in field_bits(name, lo, n):
        if m.setdefault(b, parity) != parity:
            raise ValueError(f'bit {b} ({name}) parity conflict inside one programme')


def arg_bit_parity(fp, npt=3):
    """fp = argmax_rows.field_parity(): ARGMAX programme bit parities"""
    m = {}
    for n in ('vm_rq', 'vm_pair_select', 'vm_meta'):
        mark(m, fp['vm_rq'], n)
    mark(m, fp['capture_slot'], 'capture_slot', 2 + npt, 4)
    mark(m, fp['sink_vm'], 'sink_slot', npt + 8, 4)
    mark(m, fp['sink_vm'], 'sink_select', nib=(npt + 8, 4))
    mark(m, fp['in_slot'], 'ar_high', 20, 4)
    for name, bit in (('start', 17), ('flush', 18), ('publish', 19)):
        mark(m, fp[name], 'ar_high', bit, 1)
    mark(m, fp['start'], 'tkm_cfg_g')                 # start-edge data: sampled with start, so padded with it
    mark(m, fp['start'], 'tkm_cfg_gbase')
    mark(m, fp['capture_arg'], 'capture_arg')
    mark(m, fp['sink_delivery'], 'sink_slot', npt, 1)
    mark(m, fp['sink_delivery'], 'sink_select', nib=(npt, 1))
    mark(m, fp['del_obase'], 'del_obase')
    return m


def gather_bit_parity(stages, npt=3):
    """stages = row_gather_rows.stages() edge numbers (cadence-1 instruction cycles); reference = the VM request (parity 0)"""
    ref = stages['REQV']
    par = {k: (v - ref) % 2 for k, v in stages.items()}
    m = {}
    for n in ('inj_rd', 'inj_idx', 'inj_meta', 'inj_addr'):
        mark(m, par['REQ'], n)
    for n in ('vm_rq', 'vm_pair_select', 'vm_meta'):
        mark(m, par['REQV'], n)
    mark(m, par['CAP'], 'capture_slot', 0, 2)
    mark(m, par['CAP'], 'capture_slot', 2 + npt, 1)
    mark(m, par['SINK'], 'sink_slot', 0, npt)
    mark(m, par['SINK'], 'sink_select', nib=(0, npt))
    for key, sname, vname in (('wr', 'WRSEQ', 'WR'), ('rd', 'RDSEQ', 'RD'), ('rx', 'RXSEQ', 'RXE')):
        mark(m, par[sname], f'lk_{key}_slot')
        mark(m, par[sname], f'lk_{key}_seq_high')
        mark(m, par[vname], 'lk_rx_expect' if key == 'rx' else f'lk_{key}_v')
    mark(m, par['RXCAP'], 'capture_slot', 2, npt)
    mark(m, par['DSINK'], 'sink_slot', npt, npt)
    mark(m, par['DSINK'], 'sink_select', nib=(npt, npt))
    mark(m, par['DADDR'], 'del_obase', 0, 40 * npt)
    return m, par


def arg_hold_bits(npt=3):
    """LEVEL bits of an ARGMAX row that padded action bits are qualified by on their padded (gap) edge (HBM-TAPS ctl_v5:316-318
    protocol fault when ar mode 47 is 0 at an arg start/flush/publish/in_slot edge; the publisher rank ar[30:23] is sampled with
    start).  The issuer repeats these on the gap edge after the row edge (-DOT_COLL_ISS8E_HOLD_MASK); they must not overlap the pad mask."""
    return sorted([*field_bits('ar_high', 16, 1), *field_bits('ar_low', 23, 8)])


def hold_literal(bits):
    v = 0
    for b in bits:
        v |= 1 << b
    return f"1536'h{v:0384x}"


def union(*maps):
    out = {}
    for name, m in maps:
        for b, p in m.items():
            if out.setdefault(b, (p, name))[0] != p:
                raise ValueError(f'ISS2E pad mask conflict at uop bit {b}: {out[b][1]} needs parity {out[b][0]}, {name} needs {p}')
    return {b: p for b, (p, _) in out.items()}


def literal(m):
    v = 0
    for b, p in m.items():
        if p:
            v |= 1 << b
    return f"1536'h{v:0384x}"
