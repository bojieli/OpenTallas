#!/usr/bin/env python3
"""kv-die 2026-10-09: the r22k ROM die record -- build the recipe once (tools/die_top_lint.py QWEN_R22K) and write
die size / reticle margin, the area by master family, the UCIe placement, the relay stages of every crossing bus (the
re-price reads them), the die relay margin lint (fp_margin_lint.die_margin) and the r21c -> r22k area delta.

    python3 tools/qwen_kv_die/rom_record.py --out results/arch/qwen_kv_die_20261009/rom_r22k.json
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_top_lint as L               # noqa: E402
import fp_margin_lint as FPL           # noqa: E402
import qwen_rom_fulldie_b3r2 as B      # noqa: E402

CROSS = ('x3', 'attn_ret', 'emb', 'emb_a', 'emb_cr', 'seq_d2d', 'd2d_seq', 'd2d_fdi', 'pll_fwd', 'rst_fwd')
RETICLE = 858.0
# r22ko4: the option-4 words and the moved control / tree / sequencer words (their relay stages go to the record)
O4_PREFIX = ('o4_', 'tt_', 'pword_', 'seq_', 'd2d_', 'vm_seq', 'coll_')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--recipe', default='r22k', choices=L.R22K_FAMILY)
    ap.add_argument('--insts', type=Path, default=None, help='block rectangles file (default rom_r22k_insts.json beside --out)')
    a = ap.parse_args()
    r = dict(L.QWEN_RECIPES[a.recipe])
    cdc = r.pop('cdc')
    v, m = B.selected(True, cdc=B._cdc_arg(cdc), **r)
    ins = m['insts']
    W, H = m['die']['w'], m['die']['h']
    stages = Counter()
    for bid, cl, bits, eps in m['buses']:
        base = re.sub(r'__r\d+$', '', bid)
        if base in CROSS or (a.recipe != 'r22k' and base.startswith(O4_PREFIX)):
            stages[base] += 1
    fam = Counter()
    for i in ins:
        k = 'relay' if (i.kind or '').startswith('relay') or i.name.startswith('rly_') else i.kind or i.master
        fam[k] += i.w * i.h / 1e6
    by = {i.name: i for i in ins}
    rec = dict(
        schema='opentallas.qwen-kv-die.rom-r22k.v1', recipe=('r22k = r21c + tools/qwen_kv_die/rom_r22k.py surgery' if a.recipe == 'r22k'
                                                              else f'{a.recipe} (tools/die_top_lint.py QWEN_RECIPES)'),
        generator_sha256=hashlib.sha256((ROOT / 'tools/qwen_rom_fulldie_b3r2.py').read_bytes()).hexdigest(),
        surgery_sha256=hashlib.sha256((ROOT / 'tools/qwen_kv_die/rom_r22k.py').read_bytes()).hexdigest(),
        die_um=[round(W, 3), round(H, 3)], die_mm2=round(W * H / 1e6, 3), reticle_mm2=RETICLE,
        margin_mm2=round(RETICLE - W * H / 1e6, 3), r21c_die_mm2=846.792,
        instances=len(ins), buses=len(m['buses']), instance_mm2=round(sum(i.w * i.h for i in ins) / 1e6, 3),
        area_by_kind_mm2={k: round(x, 3) for k, x in sorted(fam.items(), key=lambda t: -t[1])},
        ucie=dict(by['ucie_kv'].d(), mm2=round(by['ucie_kv'].w * by['ucie_kv'].h / 1e6, 4), edge='S',
                  edge_um=round(by['ucie_kv'].w, 3)),
        d2d_rom=by['d2d_rom'].d(), clk_rx=by['clk_rx'].d(),
        crossing_bus_stages={k: max(0, stages[k] - 1) for k in list(CROSS) + sorted(k for k in stages if k not in CROSS)},
        stage_note='relay stages = registered hops between the endpoint pins (segments - 1); every endpoint port is '
                   'registered as well (the stage the r21 token-cost counts as one per die hop)',
        r22k=m.get('r22k'),
        margin_lint=FPL.die_margin(ins, [b for b in m['buses'] if b[1] not in ('clock_trunk', 'reset')],
                                   {i.kind for i in ins if i.name.startswith('rly_')}, reach_um=504.0),
        margin_note='data buses only: clock / reset trunks are CTS / reset trees (their relay-row sinks are clock pins)',
        relay_kinds=sorted({i.kind for i in ins if i.name.startswith('rly_')}))
    st_ = rec['crossing_bus_stages']
    if 'coll_seq' in st_:
        # qwen-1010/A: the all-reduce words leave seq_su (tp_seq_vrl, which reads the VM over seq_vrd / vm_seq_q) on
        # seq_coll through io_xfifo (CDC) to io_collective and return on coll_seq; a credit-based link (no same-cycle
        # ready across stations) needs credits >= the round trip
        pins, cdc = 2 * 4, 2 * 4      # registered endpoint ports (seq_su, xfifo x2, collective) each way; 4 sync edges a CDC
        rt = st_['seq_coll'] + st_.get('seq_coll_x', 0) + st_['coll_seq'] + st_.get('coll_seq_x', 0) + pins + cdc
        rec['collective_credit'] = dict(
            round_trip_edges=rt, credits=rt, receiver_buffer_words=rt, receiver_buffer_bits=rt * 512,
            one_way_edges=dict(fwd=st_['seq_coll'] + st_.get('seq_coll_x', 0) + 4 + 4,
                               ret=st_['coll_seq'] + st_.get('coll_seq_x', 0) + 4 + 4),
            note='the die streams all-reduce words seq_su (tp_seq_vrl reads / writes the VM over seq_vrd / vm_seq_q / '
                 'seq_vwr) -> io_xfifo -> io_collective on seq_coll (548 b) and back on coll_seq (518 b); no VM <-> '
                 'collective words.  Credits = round trip (relays both ways + 8 port stations + 2 CDCs of 4 edges) keep one '
                 'word a cycle; the collective input buffer holds that many words.  The token vehicle carries the same '
                 'one-way edges as relay stations on the sequencer <-> collective words (option4_die --crly).')
    elif all(k in st_ for k in ('coll_tx', 'coll_tx_x', 'coll_rx', 'coll_rx_x')):
        # qwen-1010/a: the collective words leave the VM (ct) through io_xfifo (CDC) to io_collective and return the same
        # way (cr); a credit-based link (no same-cycle ready across stations) needs credits >= the round trip
        pins, cdc = 2 * 4, 2 * 4      # registered endpoint ports (VM, xfifo x2, collective) each way; 4 sync edges a CDC
        rt = st_['coll_tx'] + st_['coll_tx_x'] + st_['coll_rx'] + st_['coll_rx_x'] + pins + cdc
        rec['collective_credit'] = dict(
            round_trip_edges=rt, credits=rt, receiver_buffer_words=rt, receiver_buffer_bits=rt * 512,
            note='the die streams all-reduce words VM -> io_xfifo -> io_collective (coll_tx 512 b) and back (coll_rx); the '
                 'sequencer sends only the 66-b descriptor (seq_coll).  Credits = round trip (relays both ways + 8 port '
                 'stations + 2 CDCs of 4 edges) keep one word a cycle; the collective input buffer must hold that many words. '
                 'The token vehicle streams the words through the sequencer (tp_seq_vrl CRED), the die through the VM port.')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=str) + '\n')
    # block rectangles (relays omitted) for the two-die explorer view
    (a.insts or (a.out.parent / 'rom_r22k_insts.json')).write_text(json.dumps(
        dict(die=[round(W, 3), round(H, 3)], insts=[[i.name, i.master, i.kind, round(i.x, 2), round(i.y, 2), round(i.w, 2),
                                                     round(i.h, 2)] for i in ins if not i.name.startswith('rly_')]),
        separators=(',', ':')) + '\n')
    print(json.dumps({k: rec[k] for k in ('die_um', 'die_mm2', 'margin_mm2', 'crossing_bus_stages')}))
    print(json.dumps({k: rec['margin_lint'][k] for k in rec['margin_lint'] if 'examples' not in k}))


if __name__ == '__main__':
    main()
