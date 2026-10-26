#!/usr/bin/env python3
"""Actual leaf VQ xf -> XG partial forwarding, XG ring/V boundary (NX carrier) and XG <-> XFIN NX endpoints.

Per RTL (slice/ot_s81sl_slice.sv, ot_s81sl_xg*.sv, ot_s81sl_rstopt*.sv):
  XG   leaf k's ot_s81sl_vq drives xf_v/xf_s/xf[276] -> slice u_up relay -> XG xf_v[k]/xf_s[k]/xf[276k+:276]
       (XR is not on this path; the XG ring stop consumes the beats).
  NX   XFIN eo_*/wo_* -> XG nx_eo/nx_wo -> ring stop -> ro_e/ro_w (K_NX ring words) or vo (V-mapped NX) -> the
       neighbour XG ri_w/ri_e/vi -> that XG's nx_wi/nx_ei -> its XFIN wi_*/ei_*.  The slice-to-slice hop is the
       XG ro_e->ri_w / ro_w->ri_e / vo->vi boundary; which neighbour is identified from actual bound drivers only.
  XFIN XG nx_wi/nx_ei {v[172], h[171:168], b[167:160], d[159:0]} -> XFIN wi_*/ei_*; XFIN eo_*/wo_* -> XG nx_eo/nx_wo;
       XFIN rb_v/rb_d -> XR x_rbv/x_rbd.

Fail closed, same style as bound_return_transport: every bit is identified by the ACTUAL bound driver of the
receiving pin (after exact source $buf A[i]->Y[i] stitching), bit order exact, one bound age per valid+payload
word.  No path-index normalisation, no DL/L4/slowest default; local XG/XFIN latency is NOT included.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

from layer_prog.bound_entry_transport import BufferSinks, collect as collect_entry
from layer_prog.bound_return_transport import (VNB, XRS, check_variant, collect_return, desc_of, import_buffers,
                                               leaf_of, wanted_pins as return_wanted_pins)

XGS = ('ot_s81sl_xg', 'ot_s81sl_xgt', 'ot_s81sl_xg_xo', 'ot_s81sl_xgt_xo')
VQ = 'ot_s81sl_vq'
XFIN = 'ot_s81dv_xfin'
VQ_PORTS = dict(xf_v=('output', 1), xf_s=('output', 1), xf=('output', 276))
NXF = (('v', 1, 172), ('h', 4, 168), ('b', 8, 160), ('d', 160, 0))     # field, width, lsb in the 173-b nx word
XFIN_PORTS = {f'{s}_{f}': (d, w) for s, d in (('wi', 'input'), ('ei', 'input'), ('eo', 'output'), ('wo', 'output'))
              for f, w, _ in NXF}
XFIN_PORTS.update(rb_v=('output', 1), rb_d=('output', 32))
RING = (('ri_w', 'ro_e', 1104), ('ri_e', 'ro_w', 1104), ('vi', 'vo', 276))   # input <- neighbour output


def interfaces_of(interfaces, prefix, module, want):
    out = []
    for name, meta in interfaces.items():
        if name.startswith(prefix) and meta.get('module') == module:
            if meta.get('kind') != 'leaf':
                raise ValueError(f'{name}: {module} interface is not an atomic leaf')
            ports = meta.get('ports', {})
            for p, (d, w) in want.items():
                if p not in ports or ports[p].get('dir') != d or ports[p].get('width') != w:
                    raise ValueError(f'{name}.{p}: {module} interface differs from RTL ({d} {w})')
            out.append(name)
    return sorted(out)


def unit_in_pin(die, unit, port, bit):
    """Unit input pin, verified against the inventory net->input-pin record; None for a literal constant."""
    p = die.units[unit]['ports'][port]
    if p['dir'] != 'input':
        raise ValueError(f'{unit}.{port} is not an input')
    net = p['bits'][bit]
    if isinstance(net, str):
        return None
    pin = f'{unit}.{port}[{bit}]'
    if pin not in die.inventory['input_pins'].get(str(net), []):
        raise ValueError(f'{pin}: not the actual inventory input pin of net {net}')
    return pin


def wanted_pins(die):
    wanted = return_wanted_pins(die)
    for name, meta in die.inventory['leaf_interfaces'].items():
        if meta.get('module') == XFIN:
            for p, q in meta.get('ports', {}).items():
                if q.get('dir') == 'input' and p in XFIN_PORTS:
                    wanted.update(f'{name}.{p}[{i}]' for i in range(q['width']))
    return wanted


def import_ring_buffers(die, full):
    """Extra exact $buf glue on the slice-to-slice ring: slice-block scopes (u_s_XX) and the die top only."""
    for k in ('schema', 'source_top', 'source_top_sha256', 'source_asbuilt_sha256'):
        if full.get(k) != die.inventory.get(k):
            raise ValueError(f'buffer inventory {k} differs from the selected inventory')
    li = die.inventory['leaf_interfaces']
    scopes = set(die.slices()) | {''}
    added = 0
    for name, meta in full['leaf_interfaces'].items():
        parent = name.rsplit('.', 1)[0] if '.' in name else ''
        if parent in scopes and BufferSinks.width(meta) is not None:
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


def one_unit(die, sl, masters):
    xs = [n for n, u in die.units.items() if n.startswith(sl + '.') and u['master'] in masters]
    if len(xs) != 1:
        raise ValueError(f'{sl}: need one retained {masters} unit, found {xs}')
    return xs[0]


def word_age(ages, what):
    if len(ages) != 1:
        raise ValueError(f'{what}: incoherent bound ages {sorted(ages)}')
    return next(iter(ages))


def collect_xf(die, entry_rows, return_rows):
    """Leaf VQ xf_v/xf_s/xf -> XG xf_v[k]/xf_s[k]/xf[276k+:276]."""
    li = die.inventory['leaf_interfaces']
    entry = {(r['slice'], r['leaf']): r for r in entry_rows if r.get('status') == 'PASS'}
    ret = {(r['slice'], r['leaf']): r for r in return_rows if r.get('status') == 'PASS'}
    rows = []
    for sl in sorted(die.slices()):
        try:
            xg = one_unit(die, sl, XGS)
            vqs = interfaces_of(li, sl + '.', VQ, VQ_PORTS)
            if len(vqs) != 5:
                raise ValueError(f'need five actual VQ leaf interfaces, found {vqs}')
        except ValueError as exc:
            rows.append(dict(status='BLOCKED', slice=sl, reason=str(exc)))
            continue
        used = {}
        for k in range(5):
            row = dict(slice=sl, leaf=k, xg=xg)
            try:
                pin = unit_in_pin(die, xg, 'xf_v', k)
                if pin is None:
                    raise ValueError(f'{xg}.xf_v[{k}] is a constant, not a forwarded leaf beat')
                check_variant(die, pin)
                d = desc_of(die, pin)
                m = re.fullmatch(r'(.+)\.xf_v\[0\]', d[1])
                if not m or m[1] not in vqs:
                    raise ValueError(f'{pin} is driven by {d[1]}, not an actual VQ xf_v output of this slice')
                vq = m[1]
                if vq in used:
                    raise ValueError(f'{vq} drives XG xf_v[{used[vq]}] and xf_v[{k}]: forward leaf not unique')
                used[vq] = k
                ages = {'xf_v': {d[2]}, 'xf_s': set(), 'xf': set()}
                bits = 1
                for port, w, lsb in (('xf_s', 1, k), ('xf', 276, 276 * k)):
                    for j in range(w):
                        p = unit_in_pin(die, xg, port, lsb + j)
                        if p is None:
                            raise ValueError(f'{xg}.{port}[{lsb + j}] is a constant, not forwarded payload')
                        check_variant(die, p)
                        e = desc_of(die, p)
                        if e[1] != f'{vq}.{port}[{j}]':
                            raise ValueError(f'{p} is driven by {e[1]}, expected {vq}.{port}[{j}]')
                        ages[port].add(e[2]); bits += 1
                per = {p: word_age(a, f'{xg}.{p} leaf {k}') for p, a in ages.items()}
                age = word_age(set(per.values()), f'valid/strobe/payload of leaf {k} ({per})')
                leaf_inst = leaf_of(vq, '.u_vq')
                ent, rr = entry.get((sl, k)), ret.get((sl, k))
                if ent is None or leaf_of(ent['vp'], '.u_vp') != leaf_inst:
                    raise ValueError(f'XR sw_v[{k}] command leaf {ent and ent["vp"]} is not the XG xf leaf {leaf_inst}')
                if rr is None or rr['leaf_instance'] != leaf_inst:
                    raise ValueError(f'XR p_v[{k}] return leaf {rr and rr.get("leaf_instance")} is not the XG xf leaf')
                row.update(status='PASS', vq=vq, leaf_instance=leaf_inst, xf_forward_edges=age, bits_checked=bits,
                           partial_return_edges=rr['partial_return_edges'],
                           command_transport_edges=ent['command_transport_edges'],
                           xf_v_through_buffer=pin in die.sinks.proofs,
                           local_vq_edges=None, local_xg_capture_edges=None)
            except (KeyError, ValueError) as exc:
                row.update(status='BLOCKED', reason=str(exc))
            rows.append(row)
    return rows


def collect_ring(die):
    """Every XG ri_w/ri_e/vi word: driven bit-for-bit by ONE other XG's ro_e/ro_w/vo, one age; or a wholly
    constant / non-XG die edge (recorded, not a neighbour hop)."""
    sl = die.slices()
    xg_of = {}
    for s in sorted(sl):
        xg_of[one_unit(die, s, XGS)] = s
    rows = []
    for xg, s in sorted(xg_of.items(), key=lambda t: sl[t[1]]['sid']):
        for inp, out, w in RING:
            row = dict(slice=s, sid=sl[s]['sid'], xg=xg, port=inp)
            try:
                if die.units[xg]['ports'][inp]['dir'] != 'input' or len(die.units[xg]['ports'][inp]['bits']) != w:
                    raise ValueError(f'{xg}.{inp}: interface differs from RTL (input {w})')
                consts, srcs, ages, drv = [], set(), set(), []
                for i in range(w):
                    pin = unit_in_pin(die, xg, inp, i)
                    if pin is None:
                        consts.append(i); continue
                    check_variant(die, pin)
                    d = desc_of(die, pin)
                    m = re.fullmatch(r'(.+)\.(\w+)\[(\d+)\]', d[1])
                    if not m:
                        raise ValueError(f'{pin}: unparsable driver {d[1]}')
                    srcs.add(m[1]); drv.append((i, m[1], m[2], int(m[3]))); ages.add(d[2])
                if not drv:
                    row.update(status='EDGE_CONSTANT', constant_bits=len(consts)); rows.append(row); continue
                if consts:
                    raise ValueError(f'{len(consts)} constant + {len(drv)} driven bits: partial ring word')
                if len(srcs) != 1:
                    raise ValueError(f'word driven by {len(srcs)} sources {sorted(srcs)[:4]}')
                src = srcs.pop()
                if src not in xg_of:
                    row.update(status='EDGE_EXTERNAL', driver=src, drv_ports=sorted({p for _, _, p, _ in drv}),
                               age_edges=word_age(ages, f'{xg}.{inp}'))
                    rows.append(row); continue
                bad = [(i, p, b) for i, _, p, b in drv if p != out or b != i]
                if bad:
                    raise ValueError(f'{xg}.{inp} not bit-exact from {src}.{out}: e.g. {bad[:3]}')
                if src == xg:
                    raise ValueError(f'{xg}.{inp} loops back to its own {out}')
                row.update(status='PASS', from_xg=src, from_slice=xg_of[src], from_sid=sl[xg_of[src]]['sid'],
                           from_port=out, age_edges=word_age(ages, f'{xg}.{inp} valid/payload'), bits_checked=w,
                           through_buffer=any(f'{xg}.{inp}[{i}]' in die.sinks.proofs for i in range(w)))
            except (KeyError, ValueError) as exc:
                row.update(status='BLOCKED', reason=str(exc))
            rows.append(row)
    return rows


def collect_xfin(die):
    """XG nx_wi/nx_ei -> XFIN wi_*/ei_*; XFIN eo_*/wo_* -> XG nx_eo/nx_wo; XFIN rb_* -> XR x_rbv/x_rbd."""
    li = die.inventory['leaf_interfaces']
    rows = []
    for sl in sorted(die.slices()):
        row = dict(slice=sl)
        try:
            xg, xr = one_unit(die, sl, XGS), one_unit(die, sl, XRS)
            xfs = interfaces_of(li, sl + '.', XFIN, XFIN_PORTS)
            if len(xfs) != 1:
                raise ValueError(f'need one actual XFIN leaf interface, found {xfs}')
            xf = xfs[0]
            row.update(xg=xg, xr=xr, xfin=xf)
            words, bits = {}, 0
            # XG -> XFIN (XFIN input pins are leaf-interface pins, read directly from bind_sinks)
            for nx, side in (('nx_wi', 'wi'), ('nx_ei', 'ei')):
                ages = set()
                for f, w, lsb in NXF:
                    for i in range(w):
                        pin = f'{xf}.{side}_{f}[{i}]'
                        check_variant(die, pin)
                        e = desc_of(die, pin)
                        if e[1] != f'{xg}.{nx}[{lsb + i}]':
                            raise ValueError(f'{pin} is driven by {e[1]}, expected {xg}.{nx}[{lsb + i}]')
                        ages.add(e[2]); bits += 1
                words[f'{nx}->{side}'] = word_age(ages, f'{xg}.{nx} -> {xf}.{side}_*')
            # XFIN -> XG
            for side, nx in (('eo', 'nx_eo'), ('wo', 'nx_wo')):
                ages = set()
                for f, w, lsb in NXF:
                    for i in range(w):
                        pin = unit_in_pin(die, xg, nx, lsb + i)
                        if pin is None:
                            raise ValueError(f'{xg}.{nx}[{lsb + i}] is a constant, not the XFIN {side}_{f}')
                        check_variant(die, pin)
                        e = desc_of(die, pin)
                        if e[1] != f'{xf}.{side}_{f}[{i}]':
                            raise ValueError(f'{pin} is driven by {e[1]}, expected {xf}.{side}_{f}[{i}]')
                        ages.add(e[2]); bits += 1
                words[f'{side}->{nx}'] = word_age(ages, f'{xf}.{side}_* -> {xg}.{nx}')
            # XFIN -> XR result return
            ages = set()
            for src, dst, w in (('rb_v', 'x_rbv', 1), ('rb_d', 'x_rbd', 32)):
                for i in range(w):
                    pin = unit_in_pin(die, xr, dst, i)
                    if pin is None:
                        raise ValueError(f'{xr}.{dst}[{i}] is a constant, not XFIN {src}')
                    check_variant(die, pin)
                    e = desc_of(die, pin)
                    if e[1] != f'{xf}.{src}[{i}]':
                        raise ValueError(f'{pin} is driven by {e[1]}, expected {xf}.{src}[{i}]')
                    ages.add(e[2]); bits += 1
            words['rb->x_rb'] = word_age(ages, f'{xf}.rb_* -> {xr}.x_rb*')
            row.update(status='PASS', edges=words, bits_checked=bits, local_xfin_edges=None)
        except (KeyError, ValueError) as exc:
            row.update(status='BLOCKED', reason=str(exc))
        rows.append(row)
    return rows


def summarise(xf_rows, ring_rows, xfin_rows):
    ok = lambda rows, good=('PASS',): all(r['status'] in good for r in rows)
    ring_good = ('PASS', 'EDGE_CONSTANT', 'EDGE_EXTERNAL')
    hops = [r for r in ring_rows if r['status'] == 'PASS']
    # every XG ro_e/ro_w output that feeds a neighbour must feed exactly one neighbour input of the paired kind
    fan = {}
    for r in hops:
        fan.setdefault((r['from_xg'], r['from_port']), []).append(r['xg'])
    multi = {f'{k[0]}.{k[1]}': v for k, v in fan.items() if len(v) != 1}
    return dict(
        xf=dict(verdict='PASS_BOUND_XG_FORWARD' if len(xf_rows) == 80 and ok(xf_rows) else 'BLOCKED',
                pass_=sum(r['status'] == 'PASS' for r in xf_rows), total=80),
        nx=dict(verdict='PASS_BOUND_NX_BOUNDARY' if len(ring_rows) == 48 and ok(ring_rows, ring_good) and hops and not multi
                else 'BLOCKED',
                neighbour_hops=len(hops), edges=sum(r['status'].startswith('EDGE') for r in ring_rows),
                blocked=sum(r['status'] == 'BLOCKED' for r in ring_rows), multi_fanout=multi, total=48),
        xfin=dict(verdict='PASS_BOUND_XFIN_ENDPOINTS' if len(xfin_rows) == 16 and ok(xfin_rows) else 'BLOCKED',
                  pass_=sum(r['status'] == 'PASS' for r in xfin_rows), total=16))


def main():
    from layer_prog.bound_die import BoundDie
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('bound', 'inventory', 'out'):
        ap.add_argument('--' + name, type=Path, required=True)
    ap.add_argument('--buffer-inventory', type=Path, required=True,
                    help='full inventory of the same source graph; only in-scope $buf glue interfaces are imported')
    a = ap.parse_args()
    if a.out.exists():
        raise ValueError('preserve prior verdict; use a fresh output')
    die = BoundDie(a.bound, a.inventory)
    full = json.loads(a.buffer_inventory.read_text())
    li = die.inventory['leaf_interfaces']
    # VQ leaves share the VN_b leaf scopes import_buffers covers; XFIN shares the XR slice-parent scope.
    imported = dict(slice_leaf=import_buffers(die, full), ring=import_ring_buffers(die, full),
                    xfin_records_in_selected_inventory=sum(m.get('module') == XFIN for m in li.values()),
                    xfin_records_in_full_inventory=sum(m.get('module') == XFIN for m in full['leaf_interfaces'].values()))
    for name, meta in full['leaf_interfaces'].items():          # same-source XFIN records, hash-checked above
        if meta.get('module') == XFIN:
            if name in li and li[name] != meta:
                raise ValueError(f'{name}: XFIN interface differs between inventories')
            li.setdefault(name, meta)
    del full
    enable(die)
    ent = collect_entry(die)
    ret = collect_return(die, ent['leaves'])
    xf_rows, ring_rows, xfin_rows = collect_xf(die, ent['leaves'], ret['leaves']), collect_ring(die), collect_xfin(die)
    summ = summarise(xf_rows, ring_rows, xfin_rows)
    rec = dict(schema='opentallas.s81.bound_xg_transport.v1', die_sha256=die.die_sha,
               source_asbuilt_sha256=die.inventory['source_asbuilt_sha256'], summary=summ,
               entry_verdict=ent['verdict'], return_verdict=ret['verdict'],
               xf_forward=xf_rows, nx_boundary=ring_rows, xfin_endpoints=xfin_rows, buffer_import=imported,
               legacy_geometry_used=False, legacy_dl_depth_used=False,
               scope='output pin event to actual input pin event only: VQ xf -> XG, XG ring/V -> neighbour XG, '
                     'XG <-> XFIN nx, XFIN rb -> XR; ring-stop / XFIN / XR local latency and NX routing policy separate',
               transparent_buffer_proofs=len(die.sinks.proofs),
               readiness_qualified=False, native_job_sealed=False, full_token=False, added_rtl_cycles=0)
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(entry=ent['verdict'], ret=ret['verdict'], **{k: v['verdict'] for k, v in summ.items()},
                          xf_pass=summ['xf']['pass_'], nx_hops=summ['nx']['neighbour_hops'],
                          nx_blocked=summ['nx']['blocked'], xfin_pass=summ['xfin']['pass_'])))
    return 0 if all(v['verdict'].startswith('PASS') for v in summ.values()) else 2


if __name__ == '__main__':
    raise SystemExit(main())
