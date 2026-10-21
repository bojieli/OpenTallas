"""Resolve the selected slice's actual source components for native lowering.

This follows existing wrapper instances. It does not change any master or
qualify a physical binding. Materialized kit inventories remain authoritative
for a run; source-only programmes retain their explicit adoption hold.
"""
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path('rtl/dsrom_sys/s81_dv/slice')


def resolve(die, slice_inst, source_root=ROOT):
    source_root = Path(source_root)
    sources = {}
    chain = []

    def body(master):
        paths = list((source_root / BASE).rglob(master + '.sv'))
        if len(paths) != 1:
            raise ValueError('selected slice master needs one explicit source definition: ' + master)
        path = paths[0]
        raw = path.read_text()
        sources[str(path.relative_to(source_root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        clean = re.sub(r'/\*.*?\*/|//[^\n]*', '', raw, flags=re.S)
        match = re.search(r'\bmodule\s+' + re.escape(master) + r'\b(.*?)\bendmodule\b', clean, re.S)
        if not match:
            raise ValueError('selected source does not define master ' + master)
        return match[1]

    def child(text, name):
        match = re.search(r'(?m)^\s*(ot_[A-Za-z0-9_]+)\s*(?:#\s*\([^;]*?\)\s*)?' + re.escape(name) + r'\s*\(', text, re.S)
        return match[1] if match else None

    master = die.inst[slice_inst]['master']
    seen = set()
    while True:
        if master in seen:
            raise ValueError('recursive slice wrapper ' + master)
        seen.add(master)
        text = body(master)
        chain.append(master)
        xg = child(text, 'u_xg')
        if xg:
            break
        nested = re.findall(r'(?m)^\s*(ot_s81sl_slice[A-Za-z0-9_]*)\s*(?:#\s*\([^;]*?\)\s*)?(u_[A-Za-z0-9_]+)\s*\(', text, re.S)
        if len(nested) != 1:
            raise ValueError('selected slice wrapper child is ambiguous: ' + master)
        master = nested[0][0]
    cap = child(text, 'u_cap')
    if cap is None:
        raise ValueError('selected source CAP instance is unresolved')
    xg_text = body(xg)
    streamer = child(xg_text, 'u_s')
    ring = child(xg_text, 'u_r')
    if streamer not in ('ot_s81sl_xs', 'ot_s81sl_xs4') or ring is None:
        raise ValueError('selected source streamer/ring pair is unresolved: ' + xg)
    body(streamer)
    body(ring)
    body(cap)
    added = 0
    if streamer == 'ot_s81sl_xs4':
        known = '974ec6f3e0ca8deb84d6690c03f10035213b6a3bc94ff178edeb9549f29b9ca9'
        if sources[str(BASE / (streamer + '.sv'))] != known:
            raise ValueError('changed XS4 source has no matching capture-stage receipt')
        added = 1
    return dict(schema='opentallas.s81.selected_slice_source.v1', slice=slice_inst,
                die_master=die.inst[slice_inst]['master'], wrapper_chain=chain,
                xg=xg, ring=ring, streamer=streamer, capture=cap,
                streamer_added_capture_edges=added, source_sha256=sources,
                source_root=str(source_root), physical_binding_qualified=False,
                qualification='SOURCE RESOLUTION ONLY; exact kit/netlist inventory and runtime clocks remain required')
