#!/usr/bin/env python3
"""KV-BOOTAGE 2026-10-19 (coordinator decision; spec lanes/KVR-DERIVE.md "SPEC for the ONE later re-harden"): the KV die's
static-schedule ages as BOOT-PROGRAMMABLE registers instead of RTL parameters hard-coded in closed tiles.

OT_KV_BOOT_AGES=1 (default 0: every existing GEN / tile text unchanged):
  * graph (boot_ages_join, called from kv_static_die.graph after the attention / die cfg joins):
      diecfg     qkd_kv_die_cfg -> qkd_kv_die_cfg_a (AGES=1: 19 age words between the capability word and the seal)
      attn_root  qkd_attn_service_root -> _b   cfg_pv_lead <- age_attn[7:0], cfg_f_dly <- age_attn[15:8]
      attn_face  qkd_attn_result_face_s -> _sb cfg_f_dly <- age_attn[15:8]
      attn_cal   qkd_attn_cal_gen -> _b        cfg_cal = {F_DLY, D_RL, D_QK} <- age_attn[15:8], [31:24], [23:16]
      vport_*    qkd_pv16_vport -> _b          cfg_age = {DQ, RT} <- age_vport[16 i +: 16], i = 4 s + k
      pvw_<p> pair control (ot_qwen_tp8_pv_wide_ctl_tb, inside the kv_die pvw cluster): die join
                 cfg_fia <- diecfg.age_pv[8 p +: 8] (recorded in graph die_joins; the cluster successor wires it)
    The RTL parameters become the hardware BOUNDS (BOUNDS below); the tile's delay lines are sized for them.
  * image (image_ages): the compiler's boot image words for those 19 addresses, from a derived static schedule
    (kv_static_params.schedule): attention {D_RL, D_QK, F_DLY, PV_LEAD}, pair FIRST_INPUT_AGE x2, 16 x {DQ, RT}.
    D_QK = ECTL QK_ISSUE_AGE - 34, D_RL = RL - 19 (kv_static_programme.profile die), F_DLY / PV_LEAD / RT / DQ / RL from
    the schedule.  kv_static_kvjf_join.die_cfg_image(..., ages=words) places them before the seal.
  * check (check_image): the boot image the generator emitted (plan schedule) against the schedule derived on the
    post-station die netlist table: every value must be EQUAL, inside its bound, and resolved -> else FAIL ids
    BOOT_AGE_MISMATCH / BOOT_AGE_BOUND / BOOT_AGE_UNRESOLVED.  Structural equalities stay generator pads (never
    programmable): V port sides (VPORT_SIDES), equal pair starts (PV_LEAD_PAIR_EQ), pvfin start alignment
    (PVFIN_START_ALIGN), W equal on the 16 ports (folded into DQ per port).
No handshake, credit or ready anywhere: configuration nets, sealed before the first token, POR-held.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ON = os.environ.get('OT_KV_BOOT_AGES', '0') == '1'
D = 'rtl/qwen_sys/kv_bootage_20261019/'
SUCC = dict(
    diecfg=(D + 'qkd_kv_die_cfg_a.sv', 'qkd_kv_die_cfg_a'),
    attn_root=(D + 'qkd_attn_service_root_b.sv', 'qkd_attn_service_root_b'),
    attn_face=(D + 'qkd_attn_result_face_sb.sv', 'qkd_attn_result_face_sb'),
    attn_cal=(D + 'qkd_attn_cal_gen_b.sv', 'qkd_attn_cal_gen_b'),
    vport=(D + 'qkd_pv16_vport_b.sv', 'qkd_pv16_vport_b'),
    pv_ctl=('rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_ctl_tb.sv', 'ot_qwen_tp8_pv_wide_ctl_tb'))
# hardware bounds (RTL parameters of the successors: delay-line depth / register range)
BOUNDS = dict(PV_LEAD=63, F_DLY=127, D_QK=255, D_RL=255, VPORT_RT=31, VPORT_DQ=15, PV_FIRST_INPUT_AGE=127)
MIN = dict(PV_LEAD=0, F_DLY=1, D_QK=0, D_RL=0, VPORT_RT=1, VPORT_DQ=0, PV_FIRST_INPUT_AGE=1)
NAGE = 19
# kv_static_params.schedule_check ids the boot image check replaces (hard tile value comparisons)
REPLACED_CHECKS = ('VPORT_RT', 'PV_FIRST_INPUT_AGE', 'PV_LEAD', 'F_DLY', 'VPORT_BOUND', 'PV_AGE_BOUND', 'PV_LEAD_BOUND',
                   'F_DLY_BOUND')
QK_CONSUME = 34          # attn_calendar QK consume age (cal gen law D_QK = QK_ISSUE_AGE - 34)
RL_BASE = 19             # cal gen law D_RL = RL - 19
STACKS = ('WS', 'WN', 'ES', 'EN')


def vport_index(inst):
    st, k = inst.split('_')[1], int(inst.split('_')[2])
    return 4 * STACKS.index(st) + k


def boot_ages_join(graph, root=ROOT, cfg='diecfg'):
    """swap the age consumers to their boot-age successors and bind their cfg ports to the die cfg (see module doc)"""
    import kv_static as K
    import kv_static_boot_join as B
    import kv_static_kvjf_join as F
    ins = {i['name']: i for i in graph['instances']}

    def swap(i, key, params):
        path, mod = SUCC[key]
        spec = K.source(path, mod, root)
        i['source'], i['module'], i['sha256'] = path, mod, spec['sha256']
        i['parameters'] = dict(params)
        pp = K.ports(spec, {k: (1 if v is None else v) for k, v in params.items() if k in spec['parameters']})
        for p, v in pp.items():
            if v['direction'] == 'input' and p not in i['inputs']:
                i['inputs'][p] = None
        if not any(d['path'] == path for d in graph['source_files']):
            graph['source_files'].append(dict(path=path, sha256=hashlib.sha256((root / path).read_bytes()).hexdigest()))
            graph['source_files'].sort(key=lambda d: d['path'])
    c = ins[cfg]
    if c['parameters'].get('CAP') != 1:
        raise ValueError('kv_bootage: diecfg CAP=1 required')
    swap(c, 'diecfg', dict(NRST=c['parameters']['NRST'], CAP=1, AGES=1, MUT=0))
    r = ins['attn_root']
    swap(r, 'attn_root', dict(PV_LEAD=BOUNDS['PV_LEAD'], CAL_PIPE=r['parameters'].get('CAL_PIPE', 0), MUT=0))
    f = ins['attn_face']
    fp = dict(f['parameters'])
    fp.update(F_DLY=BOUNDS['F_DLY'])
    swap(f, 'attn_face', fp)
    g = ins['attn_cal']
    gp = {k: v for k, v in g['parameters'].items() if k not in ('D_QK', 'D_RL')}
    gp.update(D_QK=BOUNDS['D_QK'], D_RL=BOUNDS['D_RL'], F_DLY=BOUNDS['F_DLY'])
    swap(g, 'attn_cal', gp)
    vps = sorted(n for n in ins if n.startswith('vport_'))
    for n in vps:
        swap(ins[n], 'vport', dict(MUT=0, DQ=BOUNDS['VPORT_DQ'], RT=BOUNDS['VPORT_RT']))
    _ins, width_of, ep = F._ctx(graph, root)
    bound = []

    def bind(i, port, items):
        B._bind(i, port, items, width_of)
        bound.append(f'{i["name"]}.{port}')
    bind(r, 'cfg_pv_lead', [ep(cfg, 'age_attn', 0, 8)])
    bind(r, 'cfg_f_dly', [ep(cfg, 'age_attn', 8, 8)])
    bind(f, 'cfg_f_dly', [ep(cfg, 'age_attn', 8, 8)])
    # items are MSB first (the tile text concatenates them in order): cfg_cal = {F_DLY, D_RL, D_QK}
    bind(g, 'cfg_cal', [ep(cfg, 'age_attn', 8, 8), ep(cfg, 'age_attn', 24, 8), ep(cfg, 'age_attn', 16, 8)])
    for n in vps:
        bind(ins[n], 'cfg_age', [ep(cfg, 'age_vport', 16 * vport_index(n), 16)])
    joins = [dict(consumer=f'pvw_ctl:{p}.cfg_fia', producer=f'{cfg}.age_pv', lo=8 * p, width=8,
                  note='KV-BOOTAGE: the pair control (ot_qwen_tp8_pv_wide_ctl_tb) sits inside the kv_die pvw cluster '
                       '(qkd_pvw_die_t, pv_trunk_gen.py): its cfg_fia is a die join')
             for p in (0, 1)]
    graph.setdefault('die_joins', []).extend(joins)
    graph.setdefault('joins_added', []).append(dict(producer=f'{cfg}:qkd_kv_die_cfg_a (AGES=1)', bound_inputs=len(bound),
        die_joins=len(joins), owner_note='KV-BOOTAGE 10-19: boot-programmable static-schedule ages (attn PV_LEAD / F_DLY '
        '/ D_QK / D_RL, 16 V port RT / DQ, 2 pair FIRST_INPUT_AGE) from the sealed die cfg; bounds ' + json.dumps(BOUNDS)))
    return bound


def pvw_file(src):
    """the boot-age variant of a generated PV pair cluster file (qkd_pvw_die_t*.sv -> *_ba.sv, module qkd_pvw_die_tb)"""
    return str(src)[:-3] + '_ba.sv'


def pvw_variant(text, src='qkd_pvw_die_t'):
    """qkd_pvw_die_t (pv_trunk_gen.py output) -> qkd_pvw_die_tb: + input cfg_age[15:0] (die cfg age_pv, both pairs'
    FIRST_INPUT_AGE; this pair reads byte PAIR), the control tile ot_qwen_tp8_pv_wide_ctl_t -> ot_qwen_tp8_pv_wide_ctl_tb
    with cfg_fia; FIRST_INPUT_AGE becomes the bound.  Everything else (stations, columns, trunks) byte-identical."""
    reps = [(f'module {src} #(', 'module qkd_pvw_die_tb #('),
            (' parameter integer FIRST_INPUT_AGE=20,', f' parameter integer FIRST_INPUT_AGE={BOUNDS["PV_FIRST_INPUT_AGE"]},'),
            (' input wire rst_n,start,', ' input wire[15:0] cfg_age,  // KV-BOOTAGE: boot-loaded pair FIRST_INPUT_AGE {pair 1, pair 0}\n'
                                         ' input wire rst_n,start,'),
            (' ot_qwen_tp8_pv_wide_ctl_t #(.FIRST_INPUT_AGE(FIRST_INPUT_AGE),',
             ' ot_qwen_tp8_pv_wide_ctl_tb #(.FIRST_INPUT_AGE(FIRST_INPUT_AGE),'),
            ('  .clk(col_clk[32]),.rst_n(rst_n),', '  .clk(col_clk[32]),.rst_n(rst_n),.cfg_fia(cfg_age[8*PAIR+:8]),')]
    for a, b in reps:
        if text.count(a) != 1:
            raise ValueError(f'kv_bootage.pvw_variant: anchor {a!r} found {text.count(a)} times')
        text = text.replace(a, b)
    hdr = ('// KV-BOOTAGE 2026-10-19: DERIVED from the pv_trunk_gen.py output by tools/qwen_kv_die/kv_bootage.py --pvw '
           '(boot-programmable pair FIRST_INPUT_AGE); do not edit.\n')
    return text.replace('`timescale 1ns/1ps\n', '`timescale 1ns/1ps\n' + hdr, 1)


def ages_of(sched, tile):
    """the per-instance boot values a derived schedule needs (None where unresolved)"""
    A, pv = sched['attn'], sched['pv']
    lead = A['PV_LEAD_by_pair']
    fia = pv.get('FIRST_INPUT_AGE')
    qk = tile.get('ECTL_QK_ISSUE_AGE')
    return dict(attn=dict(PV_LEAD=A.get('PV_LEAD'), F_DLY=A.get('F_DLY'),
                          D_QK=None if qk is None else qk - QK_CONSUME,
                          D_RL=None if fia is None else fia - 1 - RL_BASE),
                pv={str(p): fia for p in (0, 1)},
                vport={i: dict(RT=v.get('RT'), DQ=v.get('DQ')) for i, v in sorted(sched['vport'].items())},
                pv_lead_by_pair=lead)


def words_of(ages):
    """the 19 die cfg words (address order after the capability word); raises on an unresolved / out-of-range value"""
    a = ages['attn']
    vals = [('PV_LEAD', a['PV_LEAD']), ('F_DLY', a['F_DLY']), ('D_QK', a['D_QK']), ('D_RL', a['D_RL'])]
    vals += [('PV_FIRST_INPUT_AGE', ages['pv'][str(p)]) for p in (0, 1)]
    for i in sorted(ages['vport'], key=vport_index):
        vals += [('VPORT_RT', ages['vport'][i]['RT']), ('VPORT_DQ', ages['vport'][i]['DQ'])]
    for k, v in vals:
        if v is None or not MIN[k] <= v <= BOUNDS[k]:
            raise ValueError(f'kv_bootage: {k} = {v} outside [{MIN[k]}, {BOUNDS[k]}]')
    w = [a['PV_LEAD'] | (a['F_DLY'] << 8) | (a['D_QK'] << 16) | (a['D_RL'] << 24)]
    w += [ages['pv'][str(p)] for p in (0, 1)]
    w += [ages['vport'][i]['RT'] | (ages['vport'][i]['DQ'] << 8) for i in sorted(ages['vport'], key=vport_index)]
    if len(w) != NAGE:
        raise ValueError(f'kv_bootage: {len(w)} age words, {NAGE} expected (16 V ports?)')
    return w


def image_ages(sched, tile):
    """{ages, words, error}: what the generator writes into the boot image (case boot_ages.json)"""
    ages = ages_of(sched, tile)
    try:
        return dict(schema='opentallas.qwen_kv.boot_ages.v1', ages=ages, words=words_of(ages), bounds=BOUNDS, error=None)
    except ValueError as e:
        return dict(schema='opentallas.qwen_kv.boot_ages.v1', ages=ages, words=None, bounds=BOUNDS, error=str(e))


def check_image(image, sched, tile):
    """FAIL ids: the boot image values vs the schedule derived here (the post-station netlist table), plus range"""
    fails = []
    want = ages_of(sched, tile)
    got = (image or {}).get('ages') or {}

    def F(id_, what, rows, fix):
        if rows:
            fails.append(dict(id=id_, what=f'{len(rows)} {what}', rows=rows[:64], fix=fix))
    mis, unres, rng = [], [], []
    flat = lambda d: {f'attn.{k}': v for k, v in d.get('attn', {}).items()} | \
        {f'pv{p}.FIRST_INPUT_AGE': v for p, v in d.get('pv', {}).items()} | \
        {f'{i}.{k}': v for i, r in d.get('vport', {}).items() for k, v in r.items()}   # noqa: E731
    fw, fg = flat(want), flat(got)
    bk = lambda k: ('VPORT_' + k.split('.')[1]) if k.startswith('vport_') else \
        ('PV_FIRST_INPUT_AGE' if k.startswith('pv') else k.split('.')[1])   # noqa: E731
    for k, v in sorted(fw.items()):
        if v is None:
            unres.append(dict(age=k))
        elif fg.get(k) != v:
            mis.append(dict(age=k, boot=fg.get(k), derived=v))
        if v is not None and not MIN[bk(k)] <= v <= BOUNDS[bk(k)]:
            rng.append(dict(age=k, derived=v, bound=[MIN[bk(k)], BOUNDS[bk(k)]]))
    F('BOOT_AGE_UNRESOLVED', 'static-schedule ages unresolved on this table (no boot value can be derived)', unres,
      'resolve the path (kv_static_params.table_paths)')
    F('BOOT_AGE_MISMATCH', 'boot image ages != the ages derived on this table', mis,
      're-emit the boot image from this table (kv_die case boot_ages.json) -- never boot a stale image')
    F('BOOT_AGE_BOUND', 'derived ages outside the hardware bounds of the boot-age successors', rng,
      're-place (shorter path) or re-harden with a larger bound')
    if image is not None and image.get('words') is None and not unres and not rng:
        F('BOOT_AGE_IMAGE', 'boot image not emitted', [dict(error=image.get('error'))], 'kv_bootage.image_ages')
    lead = want['pv_lead_by_pair']
    F('PV_LEAD_PAIR_EQ', 'PV pairs: D(ks_pvst) differs between the pairs (one PV_LEAD for both)',
      [dict(pvst=lead)] if None not in lead and lead[0] != lead[1] else [],
      'pad the shorter ks_pvst branch (core-clock pads) -- structural, not programmable')
    return fails


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--schedule', type=Path, help='static_model.json / kv_static_params record')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--pvw', nargs='+', type=Path, help='write the boot-age variant of these pv_trunk_gen files (*_ba.sv)')
    a = ap.parse_args(argv)
    if a.pvw:
        for p in a.pvw:
            q = Path(pvw_file(p))
            q.write_text(pvw_variant(p.read_text()))
            print(f'wrote {q}')
        if not a.schedule:
            return 0
    d = json.loads(a.schedule.read_text())
    ss = d.get('static_schedule') or d.get('params', {}).get('static_schedule')
    img = image_ages(ss['schedule'], ss.get('tile_ages') or {})
    txt = json.dumps(img, indent=1)
    if a.out:
        a.out.write_text(txt + '\n')
    print(txt[:3000])
    return 0 if img['words'] else 1


if __name__ == '__main__':
    sys.exit(main())
