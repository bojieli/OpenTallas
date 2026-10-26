#!/usr/bin/env python3
"""Actual VN_b partial (p_v/p_d) to XR p_v/p_d return transport, plus XR rb_v/rb_d to VN_b.

Per RTL (slice/ot_s81sl_slice.sv, ot_s81sl_vn.sv): each leaf's ot_s81sl_vn_sp drives the leaf p_v/p_d from
u_b (ot_s81sl_vn_b); the slice glue carries leaf k's partial through u_up to XR p_v[k] / p_d[32k+:32], and XR
rb_v/rb_d (one copy) fans out through u_dn to every leaf's VN (u_a and u_b).

Fail closed: each XR return bit is identified by the ACTUAL bound driver of the XR input pin (after exact
source $buf A[i]->Y[i] stitching), the driver must be an output pin of one actual ot_s81sl_vn_b leaf interface,
the bit order must be exact, valid/payload ages coherent, and the VN_b leaf must be the same leaf instance whose
VP the actual XR sw_v[k] command bit reaches (bound_entry_transport). No path-index normalisation, no DL/L4
default; ages are actual bound stage counts only. Local VN/XR latency is NOT included.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

from layer_prog.bound_entry_transport import BufferSinks, collect as collect_entry

VNB = 'ot_s81sl_vn_b'
XRS = ('ot_s81sl_xrt1', 'ot_s81sl_xrt3')
RB_PORTS = (('rb_v', 1), ('rb_d', 32))


def vnb_interfaces(interfaces, prefix):
    out = []
    for name, meta in interfaces.items():
        if name.startswith(prefix) and meta.get('module') == VNB:
            if meta.get('kind') != 'leaf':
                raise ValueError(f'{name}: VN_b interface is not an atomic leaf')
            ports = meta.get('ports', {})
            want = dict(p_v=('output', 1), p_d=('output', 32), rb_v=('input', 1), rb_d=('input', 32))
            for p, (d, w) in want.items():
                if p not in ports or ports[p].get('dir') != d or ports[p].get('width') != w:
                    raise ValueError(f'{name}.{p}: VN_b interface differs from RTL ({d} {w})')
            out.append(name)
    return sorted(out)


def wanted_pins(die):
    """Selected inventory input pins + source $buf inputs + exact VN_b rb_v/rb_d input pins."""
    wanted = {p for ps in die.inventory['input_pins'].values() for p in ps}
    interfaces = die.inventory['leaf_interfaces']
    for name, meta in interfaces.items():
        width = BufferSinks.width(meta)
        if width is not None:
            wanted.update(f'{name}.A[{i}]' for i in range(width))
        elif meta.get('module') == VNB:
            for p, w in RB_PORTS:
                wanted.update(f'{name}.{p}[{i}]' for i in range(w))
    return wanted


def import_buffers(die, full):
    """Add exact source $buf glue interfaces from the full inventory of the SAME source graph, limited to the
    slice-parent, leaf and VN scopes this return crosses. Nothing else is imported; other glue stays opaque."""
    for k in ('schema', 'source_top', 'source_top_sha256', 'source_asbuilt_sha256'):
        if full.get(k) != die.inventory.get(k):
            raise ValueError(f'buffer inventory {k} differs from the selected inventory')
    li = die.inventory['leaf_interfaces']
    scopes = {n.rsplit('.', 1)[0] for n, u in die.units.items() if u['master'] in XRS}
    for name, meta in li.items():
        if meta.get('module') == VNB:
            leaf = leaf_of(name, '.u_vn.u_b')
            scopes.update((leaf, leaf + '.u_vn'))
    added = 0
    for name, meta in full['leaf_interfaces'].items():
        if name.rsplit('.', 1)[0] in scopes and BufferSinks.width(meta) is not None:
            if name in li and li[name] != meta:
                raise ValueError(f'{name}: buffer interface differs between inventories')
            if name not in li:
                li[name] = meta; added += 1
    return dict(scopes=len(scopes), added_buffers=added)


def enable(die):
    from layer_prog.bound_die import object_items
    wanted = wanted_pins(die)
    raw = {k: v for k, v in object_items(die.bound / 'bind_sinks.json') if k in wanted}
    die.sinks = BufferSinks(raw, die.inventory['leaf_interfaces'])


def check_variant(die, pin):
    variants = die.inventory.get('source_variants', {})
    if not variants.get('leaf_rules_applied', False):
        for rule in variants.get('leaf_rules', []):
            if re.fullmatch(rule['inst'], pin.rsplit('.', 1)[0]):
                raise ValueError(f'{pin}: source variant ABI needs explicit projection')


def desc_of(die, pin):
    d = die.sinks.get(pin)
    if not isinstance(d, list) or len(d) != 4 or d[0] != 'pin':
        raise ValueError(f'{pin}: no exact bound pin driver ({d!r})')
    if type(d[2]) is not int or d[2] < 0:
        raise ValueError(f'{pin}: no exact bound stage count')
    return d


def xr_input_pin(die, xr, port, bit):
    """XR input pin name, verified against the inventory's own net->input-pin record."""
    net = die.units[xr]['ports'][port]['bits'][bit]
    if isinstance(net, str):
        raise ValueError(f'{xr}.{port}[{bit}] is a constant {net!r}, not a returned bit')
    pin = f'{xr}.{port}[{bit}]'
    if pin not in die.inventory['input_pins'].get(str(net), []):
        raise ValueError(f'{pin}: not the actual inventory input pin of net {net}')
    return pin


def leaf_of(inst, suffix):
    if not inst.endswith(suffix):
        raise ValueError(f'{inst}: not a {suffix} instance')
    return inst[:-len(suffix)]


def collect_return(die, entry_rows):
    interfaces = die.inventory['leaf_interfaces']
    entry = {(r['slice'], r['leaf']): r for r in entry_rows if r.get('status') == 'PASS'}
    rows = []
    for sl in sorted(die.slices()):
        xrs = [n for n, u in die.units.items() if n.startswith(sl + '.') and u['master'] in XRS]
        try:
            vnbs = vnb_interfaces(interfaces, sl + '.')
        except ValueError as exc:
            rows.append(dict(status='BLOCKED', slice=sl, reason=str(exc)))
            continue
        if len(xrs) != 1 or len(vnbs) != 5:
            rows.append(dict(status='BLOCKED', slice=sl, reason='need one retained XR and five actual VN_b leaf interfaces',
                             xr_units=xrs, vnb=vnbs))
            continue
        xr = xrs[0]
        used = {}
        for k in range(5):
            row = dict(slice=sl, leaf=k, xr=xr)
            try:
                pv_pin = xr_input_pin(die, xr, 'p_v', k)
                check_variant(die, pv_pin)
                d = desc_of(die, pv_pin)
                m = re.fullmatch(r'(.+)\.p_v\[0\]', d[1])
                if not m or m[1] not in vnbs:
                    raise ValueError(f'{pv_pin} is driven by {d[1]}, not an actual VN_b p_v output of this slice')
                vnb = m[1]
                if vnb in used:
                    raise ValueError(f'{vnb} drives XR p_v[{used[vnb]}] and p_v[{k}]: return leaf not unique')
                used[vnb] = k
                check_variant(die, d[1])
                pd_ages, pd_proof = set(), 0
                for j in range(32):
                    pin = xr_input_pin(die, xr, 'p_d', 32 * k + j)
                    check_variant(die, pin)
                    e = desc_of(die, pin)
                    if e[1] != f'{vnb}.p_d[{j}]':
                        raise ValueError(f'{pin} is driven by {e[1]}, expected {vnb}.p_d[{j}]')
                    pd_ages.add(e[2]); pd_proof += 1
                if pd_ages != {d[2]}:
                    raise ValueError(f'incoherent p_v/p_d bound ages: p_v {d[2]}, p_d {sorted(pd_ages)}')
                leaf_inst = leaf_of(vnb, '.u_vn.u_b')
                ent = entry.get((sl, k))
                if ent is None:
                    raise ValueError('no PASS entry transport for this XR leaf ordinal; command/return leaf not proven')
                if leaf_of(ent['vp'], '.u_vp') != leaf_inst:
                    raise ValueError(f'XR sw_v[{k}] reaches {ent["vp"]} but p_v[{k}] returns from {vnb}')
                rb, rb_ages = {}, set()
                for p, w in RB_PORTS:
                    ages = set()
                    for i in range(w):
                        pin = f'{vnb}.{p}[{i}]'
                        e = desc_of(die, pin)
                        if e[1] != f'{xr}.{p}[{i}]':
                            raise ValueError(f'{pin} is driven by {e[1]}, expected {xr}.{p}[{i}]')
                        ages.add(e[2])
                    if len(ages) != 1:
                        raise ValueError(f'{vnb}.{p}: mixed bound ages {sorted(ages)}')
                    rb[p] = ages.pop(); rb_ages.add(rb[p])
                if len(rb_ages) != 1:
                    raise ValueError(f'incoherent rb_v/rb_d bound ages {rb}')
                row.update(status='PASS', vn_b=vnb, vp=ent['vp'], leaf_instance=leaf_inst,
                           partial_return_edges=d[2], p_d_bits_checked=pd_proof,
                           rb_broadcast_edges=rb_ages.pop(), command_transport_edges=ent['command_transport_edges'],
                           p_v_driver=d[1], p_v_through_buffer=pv_pin in die.sinks.proofs,
                           local_vn_partial_edges=None, local_xr_capture_edges=None)
            except (KeyError, ValueError) as exc:
                row.update(status='BLOCKED', reason=str(exc))
            rows.append(row)
    ok = len(rows) == 80 and all(r['status'] == 'PASS' for r in rows)
    return dict(schema='opentallas.s81.bound_return_transport.v1',
                verdict='PASS_BOUND_RETURN' if ok else 'BLOCKED',
                die_sha256=die.die_sha, source_asbuilt_sha256=die.inventory['source_asbuilt_sha256'],
                leaves=rows, legacy_geometry_used=False, legacy_dl_depth_used=False,
                scope='VN_b p_v/p_d output pin event to actual XR p_v/p_d input pin event, and XR rb_v/rb_d output to '
                      'VN_b rb_v/rb_d input; VN local partial latency, XR capture/reduction, XG/XFIN/NX remain separate',
                readiness_qualified=False, native_job_sealed=False, full_token=False, added_rtl_cycles=0)


def main():
    from layer_prog.bound_die import BoundDie
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('bound', 'inventory', 'out'):
        ap.add_argument('--' + name, type=Path, required=True)
    ap.add_argument('--buffer-inventory', type=Path,
                    help='full inventory of the same source graph; only in-scope $buf glue interfaces are imported')
    a = ap.parse_args()
    if a.out.exists():
        raise ValueError('preserve prior verdict; use a fresh output')
    die = BoundDie(a.bound, a.inventory)
    imported = import_buffers(die, json.loads(a.buffer_inventory.read_text())) if a.buffer_inventory else None
    enable(die)
    ent = collect_entry(die)
    rec = collect_return(die, ent['leaves'])
    rec['entry_verdict'] = ent['verdict']
    rec['buffer_import'] = imported
    rec['transparent_buffer_proofs'] = die.sinks.proofs
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(verdict=rec['verdict'], entry=ent['verdict'], leaves=len(rec['leaves']),
                          blocked=sum(r['status'] != 'PASS' for r in rec['leaves']))))
    return 0 if rec['verdict'] == 'PASS_BOUND_RETURN' else 2


if __name__ == '__main__':
    raise SystemExit(main())
