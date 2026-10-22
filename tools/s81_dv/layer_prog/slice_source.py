"""Resolve the selected slice's actual source components for native lowering.

This follows existing wrapper instances. It does not change any master or
qualify a physical binding. Materialized kit inventories remain authoritative
for a run; source-only programmes retain their explicit adoption hold.
"""
import hashlib
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path('rtl/dsrom_sys/s81_dv/slice')


def resolve(die, slice_inst, source_root=None):
    explicit = source_root is not None or bool(os.environ.get('OT_S81_SELECTED_SOURCE_ROOT'))
    source_root = Path(source_root or os.environ.get('OT_S81_SELECTED_SOURCE_ROOT') or ROOT)
    sources = {}
    chain = []

    def body(master):
        paths = list((source_root / BASE).rglob(master + '.sv'))
        if not paths:
            # Selected wrappers such as xr1/xrt1 can be real module definitions
            # in their family's source file. Resolve the definition, never a
            # similarly named candidate or a presumed compatible alias.
            definition = re.compile(r'\bmodule\s+' + re.escape(master) + r'\b')
            paths = [p for p in (source_root / 'rtl/dsrom_sys/s81_dv').rglob('*.sv')
                     if definition.search(re.sub(r'/\*.*?\*/|//[^\n]*', '', p.read_text(), flags=re.S))]
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
    hb = re.search(r'\.HB\(\s*(\d+)\s*\)', die.inst[slice_inst].get('params', ''))
    hb = int(hb.group(1)) if hb else None
    seen = set()
    while True:
        if master in seen:
            raise ValueError('recursive slice wrapper ' + master)
        seen.add(master)
        text = body(master)
        default_hb = re.search(r'parameter\s+integer\s+HB\s*=\s*(\d+)', text)
        if hb is None and default_hb:
            hb = int(default_hb.group(1))
        chain.append(master)
        xg = child(text, 'u_xg')
        if xg:
            break
        # instance names: u_<x> or the bare wrapper core `u` (ot_s81sl_slice_lepw: `ot_s81sl_slice_lep #(...) u (...)`)
        nested = re.findall(r'(?m)^\s*(ot_s81sl_slice[A-Za-z0-9_]*)\s*(?:#\s*\([^;]*?\)\s*)?(u(?:_[A-Za-z0-9_]+)?)\s*\(', text, re.S)
        # generate branches may instantiate the same child master more than once (lep: u_sl in both HOST_EN arms)
        masters = sorted({m for m, _ in nested})
        if len(masters) != 1:
            raise ValueError('selected slice wrapper child is ambiguous: ' + master)
        master = masters[0]
    cap = child(text, 'u_cap')
    if cap is None:
        raise ValueError('selected source CAP instance is unresolved')
    xr = child(text, 'u_xr')
    xr_options = set(re.findall(r'\b(ot_s81sl_xr[0-9t]*)\s+u_xr\s*\(', text))
    if len(xr_options) > 1:
        if xr_options not in ({'ot_s81sl_xr1', 'ot_s81sl_xr3'}, {'ot_s81sl_xrt1', 'ot_s81sl_xrt3'}) or hb is None:
            raise ValueError('selected XR generate branch requires explicit HB binding')
        xr = next(x for x in xr_options if x.endswith('3' if hb != 0 else '1'))
    if xr is None:
        raise ValueError('selected source XR instance is unresolved')
    before = set(sources)
    body(xr)
    xr_paths = set(sources) - before
    if len(xr_paths) != 1:
        raise ValueError('selected XR source file is unresolved')
    xr_path = xr_paths.pop()
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
                xr=xr, xr_source_path=xr_path,
                selected_hb=hb,
                streamer_added_capture_edges=added, source_sha256=sources,
                source_root=str(source_root), explicit_source_root=explicit, physical_binding_qualified=False,
                qualification='SOURCE RESOLUTION ONLY; exact kit/netlist inventory and runtime clocks remain required')
