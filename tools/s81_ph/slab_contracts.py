#!/usr/bin/env python3
"""S81 hub-slab outline / pin-plan contracts for the control-plane streams (ds-1010/s81die, 2026-10-11).

One JSON per slab (gather, capture, collective, SU, HC, VM, WFC kit) under physical/s81_ph_views/contracts_1011/:
  * outline (um) and die placement of every instance of the slab (SU / HC have a S and a N half),
  * every existing pin group the generator draws for the slab master (port, bits, face, layer, span along the face,
    die nets bound to it and their peers), clock / reset pins included,
  * RESERVED pin groups for the dsfd_sp_ctrl engine adapter ports (physical/s81_ctrl/ADAPTER_CONTRACT_1011.json):
    per bound engine e a command group  c<e>_v + c<e>_d[84]  (85 b in, from cv[e] / cd[e])  and a done group
    d<e>_v + d<e>_t[8] (9 b out, to dv[e] / dt[e]); the VM gets the controller's VM port group
    (vwe/vwa[14]/vwd[512] in, vre/vra[14] in, vrq[512]/vrv out).  Reserved spans are drawn with the generator's own
    face() pin model on the face toward the stage controller, in the widest free span of that face, and checked
    clash-free (same layer, 0.024 um spacing) against the existing pins.

The contract is derived from the generator model of the recipe given (--opts), so it is exactly what the die build
places; re-run it when the recipe or a slab outline changes (version field).

    OT_S81_Q_LEF=physical/s81_die_views/q_elem_qs5f_efs/q_elem.lef.gz \
    python3 tools/s81_ph/slab_contracts.py --opts results/physical/s81_gen_20261010/s81_layer1_full_efs_xbrg_le.opts \
        [--extra '--wfc-kit --wfc-crp --ctrl-role source'] --tag layer1 --out physical/s81_ph_views/contracts_1011
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_s81_fulldie as F  # noqa: E402
import qwen_rom_fulldie as Q  # noqa: E402

ADAPTER = 'physical/s81_ctrl/ADAPTER_CONTRACT_1011.json'
# slab contract -> (hub keys, engines bound to it by the adapter contract, owning stream)
SLABS = {
    'gather': (['gather'], ['fld'], 's81-ctl-1011'),
    'capture': (['capture'], ['fld'], 's81-ctl-1011'),
    'collective': (['collective'], ['coll'], 's81-ctl-1011 / coll-tu'),
    'su_hc': (['su_s', 'su_n', 'hc_s', 'hc_n'], ['su', 'hc'], 's81-suhc-1011'),
    'vm': (['vm'], [], 's81-vm-1011'),
    'wfc_kit': (['wfc'], ['spare'], 'mtp-wfc-1010'),
}
CMD_BITS, DONE_BITS = 85, 9          # {c_cmd_v, c_cmd_d[84]} / {c_done_v, c_done_tag[8]}
VM_GROUPS = (('ctl_vw', 1 + 14 + 512, 'in', 'vwe + vwa[14] + vwd[512] (controller VM write)'),
             ('ctl_vr', 1 + 14, 'in', 'vre + vra[14] (controller VM read request)'),
             ('ctl_vq', 512 + 1, 'out', 'vrq[512] + vrv (VM read response, one cycle: die_binding_contract vm_read_cycles 1)'))
SPACE = 0.024


def face_of(r, w, h):
    x0, y0, x1, y1 = r
    e = 0.25
    if x0 <= e:
        return 'W'
    if x1 >= w - e:
        return 'E'
    if y0 <= e:
        return 'S'
    if y1 >= h - e:
        return 'N'
    return 'area'


def groups(mst, rects):
    g = defaultdict(lambda: dict(bits=0, faces=set(), layers=set(), lo=1e9, hi=-1e9))
    for nm, ly, r in rects:
        port = nm.rsplit('[', 1)[0]
        d = g[port]
        d['bits'] += 1
        f = face_of(r, mst.w, mst.h)
        d['faces'].add(f)
        d['layers'].add(ly)
        a0, a1 = (r[1], r[3]) if f in 'EW' else (r[0], r[2])
        d['lo'], d['hi'] = min(d['lo'], a0), max(d['hi'], a1)
    out = {}
    for p, d in g.items():
        out[p] = dict(bits=d['bits'], face='/'.join(sorted(d['faces'])), layer='/'.join(sorted(d['layers'])),
                      span_um=[round(d['lo'], 3), round(d['hi'], 3)])
    return out


def free_spans(rects, face, along, margin=2.0):
    occ = []
    for nm, ly, r in rects:
        a0, a1 = (r[1], r[3]) if face in 'EW' else (r[0], r[2])
        occ.append((a0 - margin, a1 + margin))
    occ.sort()
    spans, cur = [], 4.0
    for a0, a1 in occ:
        if a0 > cur:
            spans.append((cur, a0))
        cur = max(cur, a1)
    if along - 4.0 > cur:
        spans.append((cur, along - 4.0))
    return spans


def reserve(mst, rects, face, layer, want):
    """want: [(port, bits)] -> {port: dict(face, layer, bits, span_um, centre_um)}; drawn with Master.face()"""
    along = mst.h if face in 'EW' else mst.w
    face_rects = [x for x in rects if face_of(x[2], mst.w, mst.h) == face and x[1] == layer]
    spans = sorted(free_spans(face_rects, face, along), key=lambda s: s[0] - s[1])
    off, p = Q.TRK[layer]
    need = sum(b * p for _, b in want) + 4.0 * len(want)
    s0, s1 = spans[0]
    if s1 - s0 < need:
        raise ValueError(f'{mst.name}: no free span of {need:.1f} um on face {face} ({spans[:3]})')
    t = copy.deepcopy(mst)
    t.ports, t.order = {}, []
    cur = (s0 + s1) / 2 - need / 2
    res = {}
    for port, bits in want:
        c = cur + bits * p / 2 + 2.0
        t.face(port, bits, face, layer, c, 1)
        cur += bits * p + 4.0
    new = Q.pin_rects(t, 1, {q: b for q, b in want})
    for port, bits in want:
        rr = [r for nm, ly, r in new if nm.rsplit('[', 1)[0] == port]
        a = [(r[1], r[3]) if face in 'EW' else (r[0], r[2]) for r in rr]
        res[port] = dict(bits=bits, face=face, layer=layer, span_um=[round(min(x for x, _ in a), 3), round(max(y for _, y in a), 3)])
    # clash check against the existing pins of the same layer
    for nm, ly, r in new:
        for nm2, ly2, r2 in rects:
            if ly2 == ly and r2[0] < r[2] + SPACE and r[0] < r2[2] + SPACE and r2[1] < r[3] + SPACE and r[1] < r2[3] + SPACE:
                raise ValueError(f'reserved pin {nm} clashes with {nm2} on {mst.name}')
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--opts', required=True)
    ap.add_argument('--extra', default='')
    ap.add_argument('--tag', required=True)
    ap.add_argument('--out', default='physical/s81_ph_views/contracts_1011')
    ap.add_argument('--version', default='v1')
    a = ap.parse_args()
    opts = (ROOT / a.opts).read_text().split() + a.extra.split()
    p = argparse.ArgumentParser()
    F.die_options(p)
    da = p.parse_args(opts)
    F.apply_options(da)
    m = F.build()
    F.finalize_r8(m)
    M = F.masters(m, 1)
    pw = F.port_widths(m, 1)
    hub = m['hub']
    nets = defaultdict(list)
    for bid, cls, bits, eps in m['buses']:
        for inst, port in eps:
            nets[(inst, F.pslice(port)[0])].append((bid, cls, bits, [e for e in eps if e[0] != inst][:4]))
    ctl = hub.get('stage_ctrl')
    adapter = json.loads((ROOT / ADAPTER).read_text())
    idx = adapter['controller']['engine_index']
    src = subprocess.run(['git', 'rev-parse', '--short=9', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if not src and (ROOT / 'SOURCE_SHA').exists():          # fleet source snapshot (git archive / hardlinked copy)
        src = (ROOT / 'SOURCE_SHA').read_text().strip()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    W, H = F.DIE
    summary = {}
    for cname, (keys, engines, owner) in SLABS.items():
        insts = []
        for k in keys:
            if k not in hub:
                continue
            it = hub[k]
            mst = M[it.master]
            wmap = {q: pw.get((it.master, q), 0) for q in mst.order}
            rects = F.pin_rects(mst, 1, wmap)
            pg = groups(mst, rects)
            for port in pg:
                pg[port]['nets'] = [dict(net=b, cls=c, bits=bb, peers=['%s.%s' % e for e in pe])
                                    for b, c, bb, pe in nets.get((it.name, port), [])][:3]
            # face toward the stage controller (if the recipe has one), else the face toward the W column centre
            cy = (ctl.y + ctl.h / 2) if ctl else H / 2
            same_col = ctl is not None and abs((ctl.x + ctl.w / 2) - (it.x + it.w / 2)) < it.w
            if it.name.startswith('sp_hc_') or it.x >= m['x_spe'] - 1.0:
                face = 'W'
            elif same_col or ctl is None:
                face = 'N' if cy > it.y + it.h else 'S' if cy < it.y else 'E'
            else:
                face = 'E'
            layer = 'M4' if face in 'EW' else 'M5'
            want = []
            for e in engines:
                if k in ('hc_s', 'hc_n') and e != 'hc' or k in ('su_s', 'su_n') and e != 'su':
                    continue
                want += [(f'c{e}', CMD_BITS), (f'd{e}', DONE_BITS)]
            if cname == 'vm':
                want += [(g, b) for g, b, _, _ in VM_GROUPS]
            res = reserve(mst, rects, face, layer, want) if want else {}
            for port, r_ in res.items():
                e = port[1:]
                if cname == 'vm':
                    g = [x for x in VM_GROUPS if x[0] == port][0]
                    r_.update(direction=g[2], carries=g[3], controller_port=dict(ctl_vw='vwe/vwa/vwd', ctl_vr='vre/vra', ctl_vq='vrq/vrv')[port])
                elif port[0] == 'c':
                    r_.update(direction='in', carries='c_cmd_v + c_cmd_d[84] (adapter controller side)',
                              controller_port='cv[%d] + cd[%d*84 +: 84]' % (idx[e], idx[e]), engine=e)
                else:
                    r_.update(direction='out', carries='c_done_v + c_done_tag[8] (adapter controller side)',
                              controller_port='dv[%d] + dt[%d*8 +: 8]' % (idx[e], idx[e]), engine=e)
                r_['status'] = 'RESERVED'
            insts.append(dict(instance=it.name, master=it.master, domain=it.domain,
                              outline_um=[round(mst.w, 3), round(mst.h, 3)],
                              die_origin_um=[round(it.x, 3), round(it.y, 3)], orient=getattr(it, 'orient', 'R0'),
                              pins=pg, reserved_ctrl=res))
        if not insts:
            summary[cname] = 'absent in this recipe'
            continue
        rec = dict(schema='opentallas.s81.slab-contract.v1', version=a.version, slab=cname, owner=owner,
                   recipe=dict(opts=a.opts, extra=a.extra, tag=a.tag, die_um=[W, H], q_lef=F.Q_LEF,
                               hub_column_width_um=m['variant'].get('hub_column_width_um'),
                               ecol_slabs=m['variant'].get('ecol_slabs')),
                   source_commit=src, generator='tools/dsrom_s81_fulldie.py', tool='tools/s81_ph/slab_contracts.py',
                   adapter_contract=ADAPTER, engines=engines,
                   stage_controller=(dict(instance=ctl.name, master=ctl.master, rect_um=[round(ctl.x, 3), round(ctl.y, 3),
                                          round(ctl.x + ctl.w, 3), round(ctl.y + ctl.h, 3)]) if ctl else
                                     'not in this recipe (--ctrl-slab off): reserved groups face the W hub-column centre; '
                                     'the dsfd_sp_ctrl slab position is fixed when s81-ctl binds it'),
                   rules=['outline and existing pins are what the die build places: a slab master must keep them (or '
                          'publish a new contract version) so the generator netlist binds unchanged',
                          'RESERVED groups: pin names are placeholders; widths, face, layer and span are the contract. '
                          'Each engine adapter (ot_s81_engine_adapter QD 8) sits inside the slab at that face; the die '
                          'nets are fixed-latency pulse nets (relay stations allowed, every die pin lands in a pin flop)',
                          'clock: slab ck from the die domain tree (domain field); serial_0p9 slabs need the adapter CDC'],
                   instances=insts)
        (out / f'{cname}.{a.tag}.json').write_text(json.dumps(rec, indent=1) + '\n')
        summary[cname] = [(i['instance'], i['outline_um'], len(i['pins']), sorted(i['reserved_ctrl'])) for i in insts]
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
