#!/usr/bin/env python3
"""Recover exact relay replica pads from a generated bound netlist without rerunning physical preparation.

Only pinned bit-independent standard/forwarded relay payloads are admitted. A b bit is spare only when its SAME a bit is tied zero and
the generated output goes to that replica's private __spare wire. No other unread output or open port is waived.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import die_port_bind as P

ROOT = Path(__file__).resolve().parents[2]
RTL = 'rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv'
RTL_SHA = '62c15fc98ea519674d8f1e606b936b89e6e5718867c571d0939dd9ca985f4d7e'
STANDARDS = {f'qkd_rlys_{w}': w for w in (1, 36, 296, 528)}
FORWARDED = {f'qkd_{family}_{w}': w for family in ('rlysh0','rlysh','landsh0','landsh') for w in (1,36,296,528)}
FWD_SOURCES = {
    'rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv': 'a40160aeeb388dd333b6495f9ce01175bd2117d4086822db1ccd9f46d68af849',
    'rtl/qwen_split/qfd_fwd_lane.sv': '16d2375b15110a3613eaf684c727e50933a1b877b48347364a383ad3c3ef7622',
}


def derive(die_v, root=ROOT, existing=None):
    src = Path(root)/RTL
    if hashlib.sha256(src.read_bytes()).hexdigest() != RTL_SHA:
        raise ValueError('relay source changed; re-prove the bitwise a -> one flop -> b contract')
    nets, _, _, insts = P.parse_die(str(die_v))
    if any(m in FORWARDED for m, *_ in insts):
        # These sources preserve each payload bit independently through station/ring; control/fault outputs excluded.
        for path, digest in FWD_SOURCES.items():
            if hashlib.sha256((Path(root)/path).read_bytes()).hexdigest() != digest:
                raise ValueError('forwarded relay source changed; re-prove payload lane independence: '+path)
    families = dict(STANDARDS, **FORWARDED)
    # Pin-repair may insert a full-width transparent lane between the original zero-pad input and its private sink.
    # Follow only individual bit identities of these pinned families; no RTL expression/logic or name-based waiver.
    drivers = {}
    driver_ports = {}
    relay_inputs = {}
    for m, inst, params, cm in insts:
        if m not in families:
            continue
        aa, bb = P.expr_bits(cm.get('a',''), nets), P.expr_bits(cm.get('b',''), nets)
        if params or aa is None or bb is None or len(aa) != families[m] or len(bb) != families[m]:
            raise ValueError(f'{inst}: unqualified transparent relay width/parameters')
        relay_inputs[(m, inst)] = aa
        for pos, (a, b) in enumerate(zip(aa,bb)):
            if b in drivers:
                raise ValueError(f'{inst}: multiply driven relay payload {b}')
            drivers[b] = a
            driver_ports[b] = (m, inst, families[m]-1-pos)
    zero_cache = {}
    def zero_source(bit):
        path, active = [], set()
        while bit in drivers and bit not in zero_cache:
            if bit in active:
                raise ValueError('cycle in relay-only constant provenance')
            active.add(bit)
            path.append(bit)
            bit = drivers[bit]
        value = zero_cache.get(bit, bit == ('CONST',0))
        for b in path:
            zero_cache[b] = value
        return value
    doc = json.loads(json.dumps(existing or dict(pads={}, instances={})))
    old_pads = P.load_pads(doc)
    # A reach-repair stage can move a declared pad's zero literal upstream while
    # the original replica now receives a full-width bus. Recover permission by
    # following the actual bit graph from THAT declared instance/input bit. Never
    # infer padding from a zero alone or a different replica's logical width.
    relocated = set()
    for key, spec in old_pads.items():
        if len(key) != 3 or key[1] != 'a':
            continue
        m, _, inst = key
        aa = relay_inputs.get((m, inst))
        if aa is None:
            continue
        width = families[m]
        for index in P.pad_bits(spec, width):
            bit, origin, active = aa[width-1-index], None, set()
            while bit in drivers:
                if bit in active:
                    raise ValueError('cycle in declared input pad provenance')
                active.add(bit)
                origin = driver_ports[bit]
                bit = drivers[bit]
            if bit == ('CONST', 0) and origin is not None:
                relocated.add(origin)
    masters = doc.setdefault('pads', {})
    for m in families:
        masters.pop(m, None)  # replace old master-wide input minima with exact instance declarations
    entries = doc.setdefault('instances', {})
    count, bits = 0, 0
    for m, inst, params, cm in insts:
        if m not in families:
            continue
        if params or not {'a','b'} <= set(cm):
            raise ValueError(f'{inst}: unexpected relay parameters/ports')
        if re.search(r"(?<![A-Za-z0-9_])'[01xXzZ]|\d+'[sS]?[bBhHdDoO][0-9a-fA-F_]*[xXzZ?]", cm['a']):
            raise ValueError(f'{inst}: ambiguous/unknown relay input literal; only explicit sized zero pads admitted')
        width = families[m]
        aa, bb = P.expr_bits(cm['a'], nets), P.expr_bits(cm['b'], nets)
        if aa is None or bb is None or len(aa) != width or len(bb) != width:
            raise ValueError(f'{inst}: relay width does not match its source')
        spare = []
        for msb, (a, b) in enumerate(zip(aa, bb)):
            if b[0] == f'n_{inst}__spare' and zero_source(a):
                spare.append(width-1-msb)
            elif b[0] == f'n_{inst}__spare':
                raise ValueError(f'{inst}: private spare output has a dynamic/nonzero input')
        # Narrow pre-existing input permissions to actual zero literals on this specific replica. Never infer that
        # a live input is padding merely because another replica of the same standard used fewer bits.
        key = (m,'a',inst) if (m,'a',inst) in old_pads else (m,'a')
        old_input = P.pad_bits(old_pads[key],width) if key in old_pads else set()
        input_spare = [width-1-msb for msb,a in enumerate(aa)
                       if a == ('CONST',0) and (width-1-msb in old_input or width-1-msb in spare
                                                  or (m, inst, width-1-msb) in relocated)]
        entries.pop(inst, None)
        ports = {}
        for port, selected in (('a',input_spare),('b',spare)):
            if not selected:
                continue
            ranges = []
            for i in sorted(selected):
                if ranges and i == ranges[-1][1]+1:
                    ranges[-1][1] = i
                else:
                    ranges.append([i,i])
            ports[port] = ranges
        if ports:
            entries[inst] = dict(master=m, reason='Pinned bit-independent relay/landing payload; output bits trace through '
                                 'exact same-lane relay edges to zero and drive private spare wires; input permissions '
                                 'are actual zero literals from existing declared pads, scoped to this instance',ports=ports)
        if spare:
            count += 1
            bits += len(spare)
    doc['source_contract'] = dict(die_sha256=hashlib.sha256(Path(die_v).read_bytes()).hexdigest(),
                                 rtl=RTL, rtl_sha256=RTL_SHA, relay_replicas=count, paired_spare_bits=bits,
                                 relocated_declared_input_bits=len(relocated))
    if any(m in FORWARDED for m, *_ in insts):
        doc['source_contract']['forwarded_source_sha256'] = FWD_SOURCES
    return doc


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('die_v', type=Path)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--existing', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    d = derive(a.die_v, a.root, json.loads(a.existing.read_text()) if a.existing else None)
    a.out.write_text(json.dumps(d, indent=1)+'\n')
    print(json.dumps(d['source_contract']))


if __name__ == '__main__':
    main()
