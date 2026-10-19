#!/usr/bin/env python3
"""QXF-SEAMK 2026-10-18 (TOKEN-XDIE-QWEN F5 / F6): static RECORD BUNDLES of a die -- the die buses that carry one record
and so must reach their consumer on ONE age.

Owner rule (static fixed-cycle schedule, no credits / backpressure): a record (valid + slot + kind + beat + payload, or a
writer word valid + tag + data + identity + generation) is consumed in the cycle its valid arrives.  When the die gives
its members different relay stage counts the consumer captures a torn record (kvs14c: att_rx_v 9 vs rx_payload 11 ->
rx_record fault at the first CMD, results/rtl/xdie_qwen_1018/run_r3/netlist_k/run.log).  So:
  * the die generator gives every member of a bundle the bundle's stage count (tools/qwen_kv_die/kv_bundle_eq.py pads
    the shorter members at their sink end), and
  * tools/die_relay_check.py FAILS a die run whose table has a torn bundle (whatever the schedule says).

    BUNDLES[design] = {name: [(src_inst, src_port, dst_inst), ...]}   (die-table selectors, RTL port names as the
    netlist exporters write them: every bus from src_inst.src_port to any port of dst_inst is a member)
    report(doc) -> {name: dict(members=[{bus, stages, age, width}], ages=[...], torn=bool, missing=[selector])}
    torn(doc)   -> [(name, report row)] for the bundles whose members differ (missing members count as torn)

The K.rx_record / K.tx_slot / K.tx_record / C.* selectors are tools/qwen_layerbench/layer_compile.py BUNDLES (the
calendar compiler's; test_kv_bundle_eq checks they stay identical); K.emb_record and K.kvn_writer are the KV die's two
other d2d record bundles (qkd_kv_static_writer samples word_valid / tag / data / identity / generation in one cycle,
rtl/qwen_sys/static_kv_20261014/qkd_kv_static_writer.sv:69,113; kvs14c gives them 2 / 2 / 4 / 4 / 3 stages).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_relay_stages as DRS   # noqa: E402

BUNDLES = {
    'qwen_compute': {
        'C.tx_slot': [('d2d_rom', p, 'native59') for p in ('native_tx_slot', 'native_tx_slot_kind', 'native_tx_slot_beat')],
        'C.rx_record': [('d2d_rom', p, 'native59') for p in ('native_rx_v', 'native_rx_slot', 'native_rx_slot_kind',
                                                            'native_rx_slot_beat', 'rx_payload')],
        'C.x3_slot': [('d2d_rom', 'kv_x3_slot', 'native59')],
        'C.tx_record': [('native59', p, 'd2d_rom') for p in ('native_tx_v', 'native_tx_payload')],
        'C.x3_record': [('native59', p, 'd2d_rom') for p in ('x3', 'x3_identity', 'x3_generation')],
    },
    'qwen_kv': {
        'K.rx_record': [('d2d_kv', p, 'kvs_attn') for p in ('att_rx_v', 'att_rx_kind', 'att_rx_beat', 'rx_payload')],
        'K.tx_slot': [('d2d_kv', p, 'kvs_attn') for p in ('att_tx_slot', 'att_tx_kind', 'att_tx_beat')],
        'K.tx_record': [('kvs_attn', p, 'd2d_kv') for p in ('attn__tx_valid', 'attn__tx_payload')],
        'K.emb_record': [('kvs_emb', p, 'd2d_kv') for p in ('rowtx__emb_tx_v', 'rowtx__emb_tx_payload')],
        'K.kvn_writer': [('d2d_kv', p, 'kvs_ctl') for p in ('kvn_word_valid', 'kvn_word_tag', 'kvn_word_data',
                                                            'kvn_word_identity', 'kvn_word_generation')],
    },
}


def age(b):
    """a bus's arrival age in edges: a landed compute lane carries age_edges (land plan), else its relay stage count"""
    return b.get('age_edges', b['stages'])


def report(doc, bundles=None):
    T = DRS.Table(doc)
    out = {}
    for name, sel in (bundles if bundles is not None else BUNDLES.get(doc['design'], {})).items():
        mem, missing = [], []
        for si, sp, di in sel:
            bs = T.match(src_inst=si, src_port=sp, dst_inst=di)
            if not bs:
                missing.append(f'{si}.{sp} -> {di}.*')
            for b in bs:
                mem.append(dict(bus=b['id'], stages=b['stages'], age=age(b), width=b['width']))
        ages = sorted({m['age'] for m in mem if m['age'] is not None})
        out[name] = dict(members=mem, ages=ages, missing=missing,
                         torn=bool(missing) or len(ages) > 1 or any(m['age'] is None for m in mem))
    return out


def torn(doc, bundles=None):
    return [(n, r) for n, r in report(doc, bundles).items() if r['torn']]


def describe(name, r):
    if r['missing']:
        return f"{name}: members missing from the die table {r['missing'][:3]}"
    return f"{name} torn: " + ', '.join(f"{m['bus'].split(' -> ')[0]} {m['age']}" for m in r['members'])


if __name__ == '__main__':
    d = DRS.load(sys.argv[1])
    for n, r in report(d).items():
        print(('TORN ' if r['torn'] else 'ok   ') + (describe(n, r) if r['torn'] else f"{n} age {r['ages']}"))
