#!/usr/bin/env python3
"""KV-P6-BOOT 10-23: the KV static BOOT IMAGE + programme on the BOUND die lane depths (plan v3.6 = v3.5 lanes, bind kv35).

    kv_boot_v36.py prep    --rs RS --model SM --groups BG --out DIR      # depth maps, relay tables, ages, boot-age words
    kv_boot_v36.py compile --ages AGES --rs RS --out DIR [--qk Q]        # kv_static_programme die compile (--no-mu)

ONE flow, run twice: on the AS-BUILT depths (rtl6 GEN die e33504a6f: relay_stages.json + static_model.json paths) and on the
BOUND depths (BINDER2 kv35 bus_groups landing members: sink leaf.port <- source leaf.port, asbuilt_stages, landed_stages).
Every bound value = as-built value + lane-depth delta of the mapped crossing (D_bound - D_asbuilt of the SAME bus_groups
members); where the as-built table value equals the bus_groups as-built full-path count the bound value is the landed depth
itself.  A path with no crossing member is intra-partition -> unchanged.  Every mapping is listed in depth_map.json.

Generators (unchanged, imported): kv_static_params.schedule (vport RT/DQ/W, pv RL/FIRST_INPUT_AGE, attn PV_LEAD/F_DLY,
ECTL RESPONSE_LAT), kv_bootage.image_ages (19 boot age words), kv_static_ages.derive (k_issuer / ectla / qk ages: K_RT
budget = the uniform natural round trip), kv_static_programme.compile_all (targets 0..13, writer_die, emb_fill).
Link ages the kvs13l4 source cannot express (GEN die: attention + writer + programme in hub_C, d2d end in sys_c) are
taken from the die table, same function for both variants (link_overlay).
"""
import argparse
import copy
import gzip
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools/qwen_kv_die'), str(ROOT / 'tools')]
STACKS = ('WS', 'WN', 'ES', 'EN')
KVS13L4 = ROOT / 'results/arch/qwen_kv_static_programme_1017/kvs13l4_plan_ages_source.json'


# ---------------------------------------------------------------------------------------------------------------- depths
class Groups:
    """bus_groups landing members indexed by sink leaf"""
    def __init__(self, path):
        g = json.load(gzip.open(path)) if str(path).endswith('.gz') else json.load(open(path))
        self.by_sink = {}
        for x in g['landing']:
            for m in x['members']:
                sl, sp = m['source'].rsplit('.', 1)
                self.by_sink.setdefault(x['sink'], []).append(dict(sink=x['sink'], sink_port=m['sink_port'], src=sl, src_port=sp,
                                                                   asb=m['asbuilt_stages'], bnd=m['landed_stages'], lane=m['lane']))

    def find(self, sink_re, port_re, src_re, src_port_re='.*'):
        out = []
        for s, ms in self.by_sink.items():
            if re.fullmatch(sink_re, s):
                out += [m for m in ms if re.fullmatch(port_re, m['sink_port']) and re.fullmatch(src_re, m['src'])
                        and re.fullmatch(src_port_re, m['src_port'])]
        return out


def bound_value(asb_value, members, key):
    """as-built table value -> bound value + the mapping record"""
    if not members:
        return asb_value, dict(key=key, asbuilt=asb_value, bound=asb_value, cls='INTRA_OR_UNMAPPED', members=0)
    a = max(m['asb'] for m in members)
    b = max(m['bnd'] for m in members)
    if asb_value == a:
        v, cls = b, 'LANDED'
    else:
        v, cls = asb_value + (b - a), 'DELTA'
        if v < 0:      # the as-built table counts a shorter segment than the full path: take the full landed depth
            v, cls = b, 'DELTA_NEG_TO_LANDED'
    lanes = sorted({m['lane'] for m in members})
    return v, dict(key=key, asbuilt=asb_value, bound=v, cls=cls, bg_asbuilt=a, bg_bound=b, delta=b - a,
                   bg_asbuilt_set=sorted({m['asb'] for m in members}), bg_bound_set=sorted({m['bnd'] for m in members}),
                   members=len(members), lanes=lanes[:6] + (['...'] if len(lanes) > 6 else []),
                   example=f"{members[0]['src']}.{members[0]['src_port']} -> {members[0]['sink']}.{members[0]['sink_port']}")


def path_members(G, key):
    """kv_static_params.path_keys() key -> the bus_groups members of that path"""
    m = re.fullmatch(r'krq_(\w\w)_(\d)', key)
    if m:
        return G.find(f'slg_{m[1]}_{m[2]}', 'kreq', rf'ectl_{m[1]}_\d')
    m = re.fullmatch(r'krs_(\w\w)_(\d)', key)
    if m:
        return G.find(rf'ectl_{m[1]}_\d', r'rsp_\w+', f'slg_{m[1]}_{m[2]}', 'krsp')
    m = re.fullmatch(r'pvvq_(\w\w)_(\d)_(\d)', key)
    if m:
        return G.find(f'slg_{m[1]}_{2 * int(m[2]) + int(m[3])}', 'vreq', f'vport_{m[1]}_{m[2]}', rf'vq{m[3]}_\w+')
    m = re.fullmatch(r'pvrs_(\w\w)_(\d)_(\d)', key)
    if m:
        return G.find(f'vport_{m[1]}_{m[2]}', rf'in{m[3]}_\w+', f'slg_{m[1]}_{2 * int(m[2]) + int(m[3])}', 'rsp')
    m = re.fullmatch(r'pvrq_(\w\w)_(\d)', key)
    if m:
        return G.find(f'vport_{m[1]}_{m[2]}', r'pr_(t|valid)', r'pvw_\d__u_ctl', r'req_\w+')
    m = re.fullmatch(r'O_(\w\w)_(\d)', key)
    if m:
        return G.find(r'pvw_\d__u_ctl', r'in_\w+', f'vport_{m[1]}_{m[2]}', r'out_\w+')
    return []          # pvst / pvp / pvfst / fin: kvs_attn, pv ctl, pvfin all in hub_C (no lane)


def bus_members(G, b):
    """relay_stages bus (src inst.port -> dst inst.port) -> bus_groups members (sink leaf = dst inst or its expansion)"""
    s, d = b['src'], b['dst']
    sink, src = re.escape(d['inst']) + r'(__\w+)?', re.escape(s['inst']) + r'(__\w+)?'
    m = G.find(sink, re.escape(d['port']), src)
    # GEN cluster port renamed by the expansion (e.g. ectl .kg -> kgo/epoch/layer): match on the source leaf port instead
    return m or G.find(sink, '.*', src, re.escape(s['port']))


def overlay_relay_stages(rs, G):
    out, rows = copy.deepcopy(rs), []
    for b in out['buses']:
        v, r = bound_value(b['stages'], bus_members(G, b), b['id'])
        if r['cls'] != 'INTRA_OR_UNMAPPED':
            rows.append(r)
        b['stages'] = v
    out['note'] = ('KV-P6-BOOT: as-built rtl6 relay_stages with every crossing bus re-valued on the BINDER2 kv35 bound depth '
                   '(landed_stages; DELTA where the as-built table counts a different path segment than bus_groups)')
    return out, rows


# ------------------------------------------------------------------------------------------------------------------ ages
def link_overlay(rs):
    """the GEN die's link ages from a relay table (same function for both variants)"""
    B = {(b['src']['inst'], b['src']['port'], b['dst']['inst'], b['dst']['port']): b['stages'] for b in rs['buses']}

    def g(*k):
        if k not in B:
            raise SystemExit(f'link_overlay: no die bus {k}')
        return B[k]
    kg = {}
    for st in STACKS:
        down = g('kvs_ctl', f'o_hroot_{st}', f'kvs_hroot_{st}', 'i_ctl')
        rows = [v for (si, sp, di, dp), v in B.items() if si == f'kvs_hroot_{st}' and sp == 'o_kg' and di.startswith(f'ectl_{st}_')]
        kg[st] = dict(o_hroot=down, o_kg_max=max(rows) if rows else None, total=down + (max(rows) if rows else 0))
    return dict(
        programme_start=dict(edges=g('dcal', 'tks', 'kvs_ctl', 'st'), cls='DIE_TABLE', bus='dcal.tks -> kvs_ctl.st (sys_c -> hub_C)'),
        programme_to_attention=dict(edges=g('kvs_ctl', 'o_attn', 'kvs_attn', 'i_ctl'), cls='DIE_TABLE',
                                    bus='kvs_ctl.o_attn -> kvs_attn.i_ctl (intra hub_C)'),
        d2d_to_attention_rx=dict(edges=g('d2d_kv', 'srx', 'kvs_attn', 'd2d__srx'), cls='DIE_TABLE',
                                 bus='d2d_kv.srx -> kvs_attn.d2d__srx (sys_c -> hub_C)'),
        programme_to_writer=dict(edges=0, cls='COLOCATED', note='layer programme and native writer both in kvs_ctl'),
        d2d_to_writer=dict(edges=g('d2d_kv', 'skw', 'kvs_ctl', 'd2d__skw'), cls='DIE_TABLE', bus='d2d_kv.skw -> kvs_ctl.d2d__skw'),
        programme_to_groups=dict(edges=max(v['total'] for v in kg.values()), cls='DIE_TABLE', per_stack=kg,
                                 note='kvs_ctl.o_hroot_s -> hroot (+ hroot fan, compiler cal_deltas) -> o_kg -> ECTL frames; '
                                      'rows padded to the stack max (KV-P5 kg landing pads), one root for all 32 groups'))


def derive_ages(paths, rs, k_rt, qk_override=None):
    """kv_static_ages.derive on the kvs13l4 source with the die's K paths, then the schedule / link overlays"""
    os.environ['OT_KV_K_RT'] = str(k_rt)
    import importlib
    import kv_static_ages as KA
    KA = importlib.reload(KA)
    import kv_static_params as KP
    src = json.loads(KVS13L4.read_text())
    for b in src['buses']:
        if re.fullmatch(r'kr[qs]_\w\w_\d', b['bid']):
            b['stages'] = paths[b['bid']]
    a = KA.derive(src)
    a['source'] = dict(a['source'], note='KV-P6-BOOT: kvs13l4 source with the die K paths krq/krs (kv_static_params.path_keys) '
                       f'and OT_KV_K_RT={k_rt}; vport / pv from kv_static_params.schedule; link from link_overlay(die table)')
    sched = KP.schedule(paths, face_land_fin=1)
    a['vport'] = {k: dict(v, cls='DIE_TABLE') for k, v in sched['vport'].items()}
    a['pv'] = dict(sched['pv'], rule='kv_static_params.schedule: RL = 4 + W + DQ + RT, W = pvrq + O; FIRST_INPUT_AGE = RL + 1')
    ld = a['link']['return_to_landing_ld']
    a['link'] = dict(link_overlay(rs), group_internal=a['link']['group_internal'], return_to_landing_ld=ld)
    if qk_override is not None:
        a['qk']['QK_ISSUE_AGE_rule'] = a['qk']['QK_ISSUE_AGE']
        a['qk']['QK_ISSUE_AGE'] = qk_override
        for e in a['ectla'].values():
            e['QK_ISSUE_AGE'] = qk_override
    a['schedule'] = sched
    return a


def boot_words(sched, qk):
    import kv_bootage as BA
    return BA.image_ages(sched, dict(ECTL_QK_ISSUE_AGE=qk))


def prep(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    G = Groups(a.groups)
    rs = json.loads(Path(a.rs).read_text())
    sm = json.loads(Path(a.model).read_text())
    P_asb = sm['static_schedule']['paths']
    P_bnd, prow = {}, []
    for k, v in P_asb.items():
        P_bnd[k], r = bound_value(v, path_members(G, k), k)
        prow.append(r)
    rs_bnd, rrow = overlay_relay_stages(rs, G)
    (out / 'relay_stages_asbuilt.json').write_text(json.dumps(rs) + '\n')
    (out / 'relay_stages_bound.json').write_text(json.dumps(rs_bnd) + '\n')
    rec = dict(schema='opentallas.kv_p6_boot.depth_map.v1', inputs=dict(relay_stages=str(a.rs), static_model=str(a.model),
               bus_groups=str(a.groups)), schedule_paths=prow, relay_buses=rrow,
               summary=dict(paths=len(prow), paths_unmapped=[r['key'] for r in prow if r['cls'] == 'INTRA_OR_UNMAPPED'],
                            paths_delta=[r['key'] for r in prow if r['cls'].startswith('DELTA')],
                            relay_buses_total=len(rs['buses']), relay_buses_mapped=len(rrow),
                            relay_buses_delta=[r['key'] for r in rrow if r['cls'].startswith('DELTA')]))
    (out / 'depth_map.json').write_text(json.dumps(rec, indent=1) + '\n')
    # V port DQ bound 15 (qkd_pv16_vport_b): a port whose DQ = RL - (4 + W + RT) exceeds it gets (DQ - 15) pad stages on its
    # W request lane (pvw ctl req_t/req_valid -> vport pr_t/pr_valid, 15 b); RL (= the longest port) is unchanged
    import kv_static_params as KP
    sch = KP.schedule(P_bnd, face_land_fin=1)
    pads = {k: max(0, v['DQ'] - 15) for k, v in sch['vport'].items()}
    P_pad = dict(P_bnd)
    for k, n in pads.items():
        P_pad['pvrq_' + k[len('vport_'):]] += n
    padrec = dict(rule='pad (DQ - 15) stages on the port W request lane pvw_<p>__u_ctl.req_t/req_valid -> vport pr_t/pr_valid '
                       '(15 b): DQ <= 15 (RTL bound of qkd_pv16_vport_b), RL unchanged',
                  dq_unpadded={k: v['DQ'] for k, v in sch['vport'].items()}, pad_stages=pads,
                  pad_flops=15 * sum(pads.values()), RL=sch['pv']['RL'])
    (out / 'vport_dq_pads.json').write_text(json.dumps(padrec, indent=1) + '\n')
    res = dict(vport_dq_pads={k: v for k, v in padrec.items() if k != 'rule'})
    for tag, P, rtab, k_rt in (('asbuilt', P_asb, rs, 80), ('bound', P_bnd, rs_bnd, None), ('bound_padded', P_pad, rs_bnd, None)):
        natural = max(8 + P[f'krq_{st}_{g}'] + P[f'krs_{st}_{g}'] for st in STACKS for g in range(8))
        ages = derive_ages(P, rtab, k_rt or natural)
        (out / f'die_ages_{tag}.json').write_text(json.dumps(ages, indent=1) + '\n')
        qk = ages['qk']['QK_ISSUE_AGE']
        img = boot_words(ages['schedule'], qk)
        (out / f'boot_ages_{tag}.json').write_text(json.dumps(img, indent=1) + '\n')
        res[tag] = dict(QK_ISSUE_AGE=qk, response_lat=ages['qk']['response_lat_range'], pv=ages['pv'],
                        link={k: v.get('edges') for k, v in ages['link'].items()}, boot_error=img['error'],
                        boot_attn=img['ages']['attn'], vport={k: (v['RT'], v['DQ']) for k, v in ages['vport'].items()})
    # QK 23 alternative (TOKi / BINDER3 RL + 11): only the boot D_QK word changes; record what it needs
    ab = json.loads((out / 'die_ages_bound_padded.json').read_text())
    res['bound_qk23'] = dict(D_QK=boot_words(ab['schedule'], 23)['ages']['attn']['D_QK'],
                             boot_error=boot_words(ab['schedule'], 23)['error'])
    sv = json.loads((Path(a.model).parent / 'boot_ages.json').read_text()) if (Path(a.model).parent / 'boot_ages.json').is_file() else None
    res['asbuilt_boot_reproduces_case_boot_ages'] = None if sv is None else \
        json.loads((out / 'boot_ages_asbuilt.json').read_text())['words'] == sv['words']
    print(json.dumps(res, indent=1))


def compile_(a):
    from tools.qwen_kv_die import kv_static_programme as P
    P.MU = False          # --no-mu: kv_frame_search fails on main for every setting (KV-PROG17 blocker 3), as KDIE5-RTL2
    P.AGES = str(Path(a.ages).resolve())   # priced_template (write) reads the SAME ages file the compile used
    ages = json.loads(Path(a.ages).read_text())
    if a.qk is not None:
        ages['qk']['QK_ISSUE_AGE'] = a.qk
    os.environ['OT_KV_EMB_FILL_RELAYS'] = str(a.rs)
    os.environ['OT_KV_WRITER_DIE'] = '1'
    pr = P.profile('die', ages)
    r = P.compile_all(pr, 0x0b0b)
    rep = P.write(r, Path(a.out))
    keep = dict(status=rep['status'], profile={k: pr[k] for k in ('start_relays', 'att', 'rx', 'writer', 'kvn', 'groups', 'qk_age',
                                                                  'qk_row_latency', 'v_rl', 'd_rl', 'd_qk', 'f_dly')},
                link=r['link'], leads={k: v for k, v in r['leads'].items() if k != 'law'},
                writer=dict(slots=r['writer']['slots'], stop=r['writer']['stop']), writer_die=r['writer_die'],
                emb_fill=r['emb_fill'], ownership=r['ownership']['words'][:3],
                attention={k: r['attention'][k] for k in ('compiled_rx_cmd', 'compiled_tx_first', 'compiled_end', 'service_end',
                                                          'start_qk_run_age')},
                attention_control=r['attention']['control']['cal_gen'],
                stage1_roots=r['layer']['rows'][0]['roots'], token_core_cycles=r['layer']['token_core_cycles'],
                phase_outside=None if r['phase'] is None else len(r['phase']['outside_window']),
                groups={k: {kk: v[kk] for kk in ('H0_front', 'H0_landing', 'XU', 'K', 'V')} for k, v in r['groups'].items()},
                es_cfg=dict(relay=r['es_cfg']['relay'], return_relay=r['es_cfg']['return_relay']),
                link_cfg_check=r['link_cfg']['check'], images={str(im['target']): len(im['program']) + len(im['descriptors'])
                                                                 for im in r['images']},
                link_image=P.LINK_IMAGE, mu_images='skipped (--no-mu)')
    (Path(a.out) / 'kv_p6_summary.json').write_text(json.dumps(keep, indent=1, default=str) + '\n')
    print(json.dumps(dict(status=keep['status'], profile=keep['profile'], writer_die=dict(kvn=r['writer_die']['kvn_relays']),
                          emb_fill={k: r['emb_fill'][k] for k in ('status', 'margin')}, token=keep['token_core_cycles']), default=str))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('prep')
    p.add_argument('--rs', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--groups', required=True)
    p.add_argument('--out', required=True)
    c = sp.add_parser('compile')
    c.add_argument('--ages', required=True)
    c.add_argument('--rs', required=True)
    c.add_argument('--out', required=True)
    c.add_argument('--qk', type=int)
    a = ap.parse_args()
    prep(a) if a.cmd == 'prep' else compile_(a)
