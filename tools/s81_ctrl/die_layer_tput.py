#!/usr/bin/env python3
"""Per-layer throughput record of the S81 one-layer die bench (owner 2026-10-13: DS ROM throughput is qualified at
the PER-LAYER level).  Reads a run_die_layer.sh output directory (stim_<L>/meta.json + prog.txt, run_base_<L>.log
with the bench's "OPT" per-op lines) and the committed token path (results/arch/token_path_20261009/ds_rom*.json).

Per op of the layer: measured = the bench's own start -> end cycles, price = the token-path node of the same id
(the price the token is charged; never changed here).  Only ops whose engine is REAL RTL at production shape in the
bench are measured: hc (dsfd_sp_hc_c: fused hc_pre NORM at D 5,120, hc_post) and coll (dsfd_sp_collective_c, 4-die
TP4, production record counts).  Field phases run the real gather / capture but on synthetic phase shapes, and su /
svc / sel / col / hcx are behavioural at their program duration: both stay AT PRICE and are listed as not covered.
The layer is re-solved on the bench program's own DAG: every op at price, then measured ops at their measured
cycles; end to end, each measured op class's (measured - price) is put on every layer's node of that op in the AR
and MTP token paths (tools/throughput/accepted_cost.py solve).

    python3 tools/s81_ctrl/die_layer_tput.py --run NAME=DIR:MODE:L0,L2 ... --mut NAME=DIR:MODE:L0 ... --primary NAME
        [--split NAME] [--extra extra.json] --out results/rtl/<record>/record.json
"""
import argparse, collections, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/throughput'))
import accepted_cost as AC  # noqa: E402

REAL = ('hc', 'coll')
FUSED = {'attn.hc_pre': ['attn.quant'], 'ffn.hc_pre': ['ffn.norm.scale', 'ffn.quant']}   # SU ops inside the HC NORM
UNPRICED = ('hc.gain_attn', 'hc.gain_ffn', 'hc.h_load', 'hc.h_store', 'attn.hc.coef', 'ffn.hc.coef', 'attn.hc.coef_a',
            'ffn.hc.coef_a')


def lpath(ops, dur):
    end = {}
    for o in ops:                                        # program order is topological
        end[o['k']] = max((end[p] for p in o['preds']), default=0.0) + dur[o['k']]
    return max(end.values())


def layer(run, L, tp, mode='base'):
    meta = json.loads((run / f'stim_{L}/meta.json').read_text())
    prog = [l.split() for l in (run / f'stim_{L}/prog.txt').read_text().splitlines()]
    log = (run / f'run_{mode}_{L}.log').read_text()
    verdict = re.search(r'TB_S81_DIE_LAYER (PASS|FAIL)', log).group(1)
    summ = re.search(r'SUMMARY .*', log).group(0)
    opt = {int(m[1]): (int(m[3]), int(m[4]), int(m[5])) for m in re.finditer(r'OPT (\d+) port (\d+) dur (-?\d+) start (-?\d+) end (-?\d+)', log)}
    by = {n['id']: n for n in tp['nodes']}
    ops = []
    for o in meta['program']:
        k = o['k']; tail = o['id'].split('.', 1)[1]
        d, st, en = opt[k]
        assert d == int(prog[k][2])
        price = None
        if o['id'] in by:
            price = by[o['id']]['cycles'] + sum(by[f"{L}.{f}"]['cycles'] for f in FUSED.get(tail, []) if f"{L}.{f}" in by)
        pend = max((opt[p][2] for p in o['preds']), default=None)
        ops.append(dict(k=k, id=o['id'], op=tail, eng=o['eng'], preds=o['preds'], program_dur=d, start=st, end=en,
                        measured=en - st, price=price, real=o['eng'] in REAL,
                        critical=bool(by.get(o['id'], {}).get('critical')), slack=by.get(o['id'], {}).get('slack'),
                        dispatch_wait=None if pend is None else st - pend))
    base = {o['k']: float(o['price'] if o['price'] is not None and o['real'] else o['program_dur']) for o in ops}
    meas = dict(base)
    for o in ops:
        if o['real']:
            meas[o['k']] = float(o['measured'])
    cls = collections.OrderedDict()
    for o in ops:
        if not o['real']:
            continue
        key = ('hc.unpriced' if o['op'] in UNPRICED else o['eng'] + ':' + o['op'])
        c = cls.setdefault(key, dict(runs=0, measured=0, price=0.0, critical=o['critical']))
        c['runs'] += 1; c['measured'] += o['measured']; c['price'] += o['price'] or 0.0
    for c in cls.values():
        c['price'] = round(c['price'], 1)
        c['ratio'] = round(c['measured'] / c['price'], 3) if c['price'] else None
    waits = [o['dispatch_wait'] for o in ops if o['dispatch_wait'] is not None and o['eng'] != 'fld']
    byop = {o['op']: o for o in ops}
    hc = {}
    for k, names in (('GAIN', ('hc.gain_attn', 'hc.gain_ffn')), ('H_LOAD', ('hc.h_load',)), ('COEF', ('attn.hc.coef', 'ffn.hc.coef')),
                     ('COEF_A', ('attn.hc.coef_a', 'ffn.hc.coef_a')), ('NORM', ('attn.hc_pre', 'ffn.hc_pre')),
                     ('POST', ('attn.hc_post', 'ffn.hc_post')), ('H_STORE', ('hc.h_store',))):
        v = [byop[n]['measured'] for n in names if n in byop]
        if v:
            hc[k] = v
    # POST streams on its all-reduce: tail = POST end - all-reduce end; pair = all-reduce start -> POST end
    pair = {}
    for blk, ar in (('attn', 'attn.out_allreduce'), ('ffn', 'ffn.combine_allreduce')):
        a, p_ = byop[ar], byop[blk + '.hc_post']
        pair[blk] = dict(allreduce=a['measured'], post_tail=p_['end'] - a['end'], pair=p_['end'] - a['start'],
                         price=round(a['price'] + p_['price'], 1), ratio=round((p_['end'] - a['start']) / (a['price'] + p_['price']), 3))
    # block entry: what the bench puts between the h being ready and the NORM start (the coefficient chain when the
    # program has ONE COEF a block; H_LOAD / COEF-a only with --coef-split)
    entry = dict(attn=byop['attn.hc_pre']['start'] - byop['hc.h_load']['start'],
                 ffn=byop['ffn.hc_pre']['start'] - byop['attn.hc_post']['end'])
    # the layer with ONLY the HC master at its measured cycles (collective, field and the behavioural engines at price):
    # the POST streams on its all-reduce, so its own cycles are the tail after the all-reduce ends
    hconly = dict(base)
    for o in ops:
        if o['eng'] == 'hc':
            hconly[o['k']] = float(pair[o['op'].split('.')[0]]['post_tail'] if o['op'].endswith('hc_post') else o['measured'])
    return dict(layer=L, mode=mode, verdict=verdict, summary=summ, ops=ops, classes=cls, hc_jobs=hc, allreduce_post=pair,
                norm_entry_wait=entry, coef_split=bool(meta.get('coef_split')), ng=meta.get('ng'),
                layer_path_at_price=round(lpath(ops, base), 1), layer_path_measured=round(lpath(ops, meas), 1),
                layer_path_hc_measured=round(lpath(ops, hconly), 1), layer_ratio_hc=round(lpath(ops, hconly) / lpath(ops, base), 4),
                layer_ratio=round(lpath(ops, meas) / lpath(ops, base), 4),
                bench_layer_cycles=int(re.search(r'layer_cycles=(\d+)', summ).group(1)),
                dispatch_wait=dict(n=len(waits), median=sorted(waits)[len(waits) // 2], max=max(waits)),
                not_covered=dict(field_ops=sum(o['eng'] == 'fld' for o in ops),
                                 behavioural_ops={e: sum(o['eng'] == e for o in ops) for e in sorted({o['eng'] for o in ops} - set(REAL) - {'fld'})}),
                cases_sha256=meta['cases_sha256'])


def e2e(delta_by_op):
    """delta_by_op: {token-path op name: added cycles}; -> per workload loss with every layer's node moved"""
    out = {}
    for wl, name in AC.DESIGNS['s81']['workloads'].items():
        doc = json.loads((AC.TP / f'{name}.json').read_text())
        base, _ = AC.solve(doc['nodes'], doc['edges'])
        per = {}
        for sel in list(delta_by_op) + ['ALL']:
            delta = {n['id']: delta_by_op[n['op']] for n in doc['nodes'] if n.get('op') in delta_by_op and (sel == 'ALL' or n['op'] == sel)}
            wave = [n['id'] for n in doc['nodes'] if n.get('op') == 'wave.busy']
            if wave:                                     # as accepted_cost.rom_loss: the slowest verify stage's share once per wave position
                stages = [g for g in doc.get('groups', []) if g.get('kind') in ('stage', 'layer', 'embed')]
                worst = max(stages, key=lambda g: g['cycles'])['id']
                add = sum(delta.get(n['id'], 0.0) for n in doc['nodes'] if n.get('group') == worst)
                for i in wave:
                    delta[i] = delta.get(i, 0.0) + add
            new, _ = AC.solve(doc['nodes'], doc['edges'], delta)
            per[sel] = dict(nodes=len(delta) - len(wave), added_cycles=round(new - base, 1), e2e_loss_pct=round(AC.loss_pct(base, new), 3))
        out[wl] = dict(base_cycles=round(base, 1), by_op=per)
    return out


def run_set(spec, tp):
    """NAME=DIR:MODE:L0,L2[:label]  ->  the layers of one run directory"""
    name, rest = spec.split('=', 1)
    parts = rest.split(':')
    d, mode, Ls = Path(parts[0]), parts[1], parts[2].split(',')
    out = []
    for L in Ls:
        l = layer(d, L, tp, mode)
        log = (d / f'run_{mode}_{L}.log').read_text()
        m = re.search(r'MUT (\d+) HMUT (\d+) NG (\d+)', log)
        l['ng'] = int(m[3]) if m else None
        out.append(l)
    return name, dict(dir=str(d), mode=mode, label=parts[3] if len(parts) > 3 else '', layers=out)


def mutant(spec):
    """NAME=DIR:MODE:L -> verdict of a negative control (must FAIL)"""
    name, rest = spec.split('=', 1)
    d, mode, L = rest.split(':')[:3]
    log = (Path(d) / f'run_{mode}_{L}.log').read_text()
    v = re.search(r'TB_S81_DIE_LAYER (PASS|FAIL)', log)
    s_ = re.search(r'SUMMARY .*', log)
    return name, dict(mode=mode, layer=L, verdict=v.group(1) if v else 'NO_RESULT', fails_as_required=bool(v and v.group(1) == 'FAIL'),
                      summary=s_.group(0) if s_ else '')


def token_loss(delta_by_op, hop_delta=None):
    """per workload: {token-path op: added cycles} on every node of that op (+ hop_delta on the substage_hop0 / head.hop
    nodes: one h transfer each) -> added cycles and tok/s loss on the solved token path"""
    out = {}
    for wl, name in AC.DESIGNS['s81']['workloads'].items():
        doc = json.loads((AC.TP / f'{name}.json').read_text())
        base, _ = AC.solve(doc['nodes'], doc['edges'])
        delta = {n['id']: delta_by_op[n['op']] for n in doc['nodes'] if n.get('op') in delta_by_op}
        nh = 0
        if hop_delta:
            for n in doc['nodes']:
                if n.get('op') in ('substage_hop0', 'head.hop'):
                    delta[n['id']] = delta.get(n['id'], 0.0) + hop_delta
                    nh += 1
        new, _ = AC.solve(doc['nodes'], doc['edges'], delta)
        out[wl] = dict(nodes=len(delta), h_transfers=nh, added_cycles=round(new - base, 1), e2e_loss_pct=round(AC.loss_pct(base, new), 3))
    return out


# ---- hand-offs of the element streams (el1013-rom-layer-tput-s81.log), each with the unit it was measured on
SU_CLASSES = dict(   # slab class -> (measured, priced cycles): dsfd_sp_su_h full shape, tools/s81_suhc/su_gate.py --hier @b132ae0da
    QN=(301, 288.0), KV=(357, 283.0), QB=(166, 80.0), SW=(352, 191.0), SO=(303, 244.9))
VM_STREAM_CLASSES = ('field', 'su')          # ops that open one dependent X-streamer read (t_pq / t_su lanes)


def su_class_rows():
    """each SU slab class on the token-path nodes that carry its price (matched by price), solved per workload"""
    rows, alld = [], {wl: {} for wl in AC.DESIGNS['s81']['workloads']}
    docs = {wl: json.loads((AC.TP / f'{name}.json').read_text()) for wl, name in AC.DESIGNS['s81']['workloads'].items()}
    for k, (m, p) in SU_CLASSES.items():
        r = dict(cls=k, measured=m, price=p, ratio=round(m / p, 3), over_1p10=m / p > AC.QUALIFY, token={})
        for wl, doc in docs.items():
            base, _ = AC.solve(doc['nodes'], doc['edges'])
            nodes = [n for n in doc['nodes'] if n['cls'] == 'su' and abs(n['cycles'] - p) < 0.6]
            dl = {n['id']: m - p for n in nodes}
            alld[wl].update(dl)
            new, _ = AC.solve(doc['nodes'], doc['edges'], dl)
            r['token'][wl] = dict(ops=sorted({n['op'] for n in nodes}), nodes=len(nodes), critical=sum(bool(n.get('critical')) for n in nodes),
                                  added_cycles=round(new - base, 1), e2e_loss_pct=round(AC.loss_pct(base, new), 3))
        rows.append(r)
    tot = {}
    for wl, doc in docs.items():
        base, _ = AC.solve(doc['nodes'], doc['edges'])
        new, _ = AC.solve(doc['nodes'], doc['edges'], alld[wl])
        tot[wl] = dict(added_cycles=round(new - base, 1), e2e_loss_pct=round(AC.loss_pct(base, new), 3))
    return dict(source='hierarchical slab dsfd_sp_su_h, full shape, tools/s81_suhc/su_gate.py --hier @b132ae0da (1,722 rows bit-exact in '
                       '3,146 cycles); prices = token-path node cycles; hand-off 10-13 07:30 [s81su]', rows=rows, all_classes=tot,
                note='unit ratios of the slab classes put on the layer: KV (attn.kv_rope_qdq) is off the critical path (0), '
                     'QB / SW / SO are critical once a layer each; no ledger row is proposed by this stream (the SU owner proposes)')


def vm_read_rows():
    """+N cycles of first-row latency on every op that opens a dependent VM read stream (zero-cycle fused nodes excluded)"""
    out = {}
    for wl, name in AC.DESIGNS['s81']['workloads'].items():
        doc = json.loads((AC.TP / f'{name}.json').read_text())
        base, _ = AC.solve(doc['nodes'], doc['edges'])
        per = {}
        for label, classes in (('field', ('field',)), ('field+su', VM_STREAM_CLASSES), ('every_vm_fed_class', ('field', 'su', 'hbm', 'coll', 'select'))):
            sel = [n for n in doc['nodes'] if n['cls'] in classes and n['cycles'] >= 10]
            per[label] = dict(nodes=len(sel), critical=sum(bool(n.get('critical')) for n in sel))
            for dly in (40, 20, 44, 24, 4):
                new, _ = AC.solve(doc['nodes'], doc['edges'], {n['id']: dly for n in sel})
                per[label]['+%d' % dly] = dict(added_cycles=round(new - base, 1), e2e_loss_pct=round(AC.loss_pct(base, new), 3))
        out[wl] = per
    return out


def handoffs():
    return dict(
        su_classes=su_class_rows(),
        vm_read=dict(
            measured_unit='dsfd_sp_vm_m master gate tools/s81_vm/s81_vm_gate.py: 8-leaf bgq28 split (branch claude/s81-bgq28-1013 '
                          '@d415c687f) read latency 41 -> 81 (+40 = 4 tiles x 10), capture / write path + 0; front-end hierarchy '
                          'dsfd_vm_fe_h (branch claude/el1013-s81-vmfe @693940a56) read latency 41 -> 45 (+4), write landing + 4 / + 7',
            model='streams are pipelined (rate unchanged); an op opens its operand stream only after the producer\'s rows completed '
                  '(ARM slot t_rdy), so the first-row latency is serial once per VM-fed op.  The + 160 of the tp case is the MTP '
                  'P2RD (4 chained reads): head / draft dies, once per MTP wave, not per layer',
            token=vm_read_rows(),
            status='MODELLED on the token path from a measured unit delta: tb_s81_die_layer has a behavioural VM (LVM 10), no VM master',
            verdict='> 1 % of a layer except "field phases only at hop 1": hop 2 -> 1, and prefetch of the next op\'s stream on the '
                    'producer\'s row-completion event'),
        collective_split=dict(measured='tb_s81ph_coll_sys dut_last, 277 records / 40 messages, all 4 lane slices split (XLD 3 / PTD 2), '
                                       'claude/s81-cesn-1013 @1c376777a: production FIFOs 3,014 -> 3,021 cycles', ratio=1.002,
                              stress=dict(cstress=0.983, slow_vm_drain=1.013), clock='core insertion 353-358 ps, ~100 ps spread (coordinator 10-13)',
                              status='unit bench of the collective against the flat (priced) design; inside 1.10'),
        gather_root=dict(status='UNMEASURED (no RTL): +<= 5 (step A) / +<= 15 (step B) cycles per field phase drain, <= 0.07 % / 0.7 % of a layer'),
        engram=dict(measured=508.7, budget=500.0, ratio=1.017, back_to_back=355.1,
                    status='dsfd_engram_c ALL-TILE, tools/s81_svceng/engram_c_gate.py; off the token critical path (slack L1 ~8.5k / '
                           'L14 ~235k cycles): 0 cycles on the priced layer; the L14 layer run hosts eng.* behaviourally'))


def vm_read_measured(specs):
    """--lvm NAME=DIR:LVM (the first is the base): the production-shape layer at several read latencies of the bench's
    behavioural VM (tb_s81_die_layer LVM).  Which jobs of the HC master pay the latency serially, measured."""
    runs = []
    for sp in specs:
        name, rest = sp.split('=', 1)
        d, lvm = rest.rsplit(':', 1)
        lay = {}
        for f in sorted(Path(d).glob('run_nom_L*.log')):
            log = f.read_text()
            m = re.search(r'layer_cycles=(\d+)', log)
            opt = {int(x[1]): (int(x[2]), int(x[4]), int(x[5])) for x in re.finditer(r'OPT (\d+) port (\d+) dur (-?\d+) start (-?\d+) end (-?\d+)', log)}
            lay[f.stem.split('_')[-1]] = dict(layer_cycles=int(m[1]), verdict='PASS' if 'TB_S81_DIE_LAYER PASS' in log else 'FAIL', opt=opt)
        runs.append(dict(name=name, dir=str(d), lvm=int(lvm), layers=lay))
    base = runs[0]
    out = dict(what='tb_s81_die_layer, production shape (NG 256, hierarchical HC slab, nominal link, --coef-split), read latency of '
                    'the behavioural VM raised from the bench default: + 20 = the bgq28 leaf chain at hop 1, + 44 = hop 2 (+ 40) with '
                    'the front-end hierarchy (+ 4).  Only the HC master reads this VM in the bench (SU / svc / select are '
                    'behavioural, the field has its own capture path): the field + SU share of the VM read cost stays modelled',
               base=dict(name=base['name'], lvm=base['lvm'], layers={L: v['layer_cycles'] for L, v in base['layers'].items()}), runs=[])
    for r in runs[1:]:
        d = r['lvm'] - base['lvm']
        row = dict(name=r['name'], dir=r['dir'], lvm=r['lvm'], added_latency=d, layers={})
        worst = 0
        for L, v in r['layers'].items():
            b = base['layers'][L]
            own = sorted(k for k in v['opt'] if (v['opt'][k][2] - v['opt'][k][1]) - (b['opt'][k][2] - b['opt'][k][1]) == d and v['opt'][k][0] == 2)
            dl = v['layer_cycles'] - b['layer_cycles']
            worst = max(worst, dl)
            row['layers'][L] = dict(layer_cycles=v['layer_cycles'], verdict=v['verdict'], delta=dl, serial_reads=round(dl / d, 2),
                                    hc_jobs_longer_by_the_latency=len(own))
        base_tok = {}
        for wl, name in AC.DESIGNS['s81']['workloads'].items():
            doc = json.loads((AC.TP / f'{name}.json').read_text())
            t, _ = AC.solve(doc['nodes'], doc['edges'])
            nl = sum(n.get('op') == 'attn.hc_post' for n in doc['nodes'])          # layers of the token (AR 40; MTP + its draft layers)
            base_tok[wl] = dict(layers=nl, added_cycles=worst * nl, e2e_loss_pct=round(AC.loss_pct(t, t + worst * nl), 3))
        row['token_measured_layer_delta_on_every_layer'] = base_tok
        row['token_model_h_load_and_coef_a'] = token_loss({'attn.hc_pre': d, 'ffn.hc_pre': d}, hop_delta=d)
        out['runs'].append(row)
    out['finding'] = ('three VM read round trips of the HC master are serial in a layer: H_LOAD (layer entry) and the COEF-a in front of '
                      'each of the two NORMs; COEF-b and the boot GAIN loads take the latency too but are off the critical chain')
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--lvm', action='append', default=[], help='NAME=DIR:LVM, the first is the base (VM read latency runs)')
    ap.add_argument('--run', action='append', default=[], help='NAME=DIR:MODE:L0,L2[:label] (repeat)')
    ap.add_argument('--mut', action='append', default=[], help='NAME=DIR:MODE:L (negative controls, repeat)')
    ap.add_argument('--primary', required=True, help='the production-shape run the ratios and the ledger rows come from')
    ap.add_argument('--split', default=None, help='the --coef-split run of the same shape (two COEF jobs a block)')
    ap.add_argument('--extra', type=Path, default=None, help='JSON merged into the record (hand-offs, families, registry)')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    tp = json.loads((AC.TP / 'ds_rom.json').read_text())
    runs = dict(run_set(r, tp) for r in a.run)
    muts = dict(mutant(m) for m in a.mut)
    P = runs[a.primary]['layers']
    # worst measured - price per priced HC op over the primary run's layers (hc_pre: the fused NORM against hc_pre +
    # its SU ops; the delta goes on the hc_pre node)
    d = {}
    for l in P:
        for o in l['ops']:
            if o['eng'] == 'hc' and o['price'] is not None and o['op'].endswith('hc_pre'):
                d[o['op']] = max(d.get(o['op'], -1e9), o['measured'] - o['price'])
    norm = max(max(l['hc_jobs']['NORM']) for l in P)
    hl, hs = max(max(l['hc_jobs']['H_LOAD']) for l in P), max(max(l['hc_jobs']['H_STORE']) for l in P)
    cf = max(max(l['hc_jobs'].get('COEF_A', l['hc_jobs'].get('COEF'))) for l in P)
    serial = dict(
        per_h_transfer=dict(H_STORE=hs, H_LOAD=hl, where='one H_STORE (stage exit) + one H_LOAD (stage entry) per h transfer: '
                            'the 40 substage_hop0 nodes + head.hop of the token path; neither has a token-path node',
                            token=token_loss({}, hop_delta=hs + hl)),
        coef_before_norm=dict(cycles=cf, token=token_loss({'attn.hc_pre': cf, 'ffn.hc_pre': cf}),
                              where='one COEF job in front of every NORM (serial in the HC master, no token-path node)'),
        all=dict(token=token_loss({'attn.hc_pre': cf, 'ffn.hc_pre': cf}, hop_delta=hs + hl)))
    chain = None
    if a.split:
        S = {l['layer']: l for l in runs[a.split]['layers']}
        chain = dict(what='ONE COEF a block reads the pre + post + combine rows, so it waits for the block\'s own coefficient '
                          'chain (hc.fn / sumsq -> rsqrt -> pre_post -> sinkhorn) and the NORM waits for it; the priced token '
                          'path starts hc_pre from the PREVIOUS block\'s pre_post.  --coef-split = COEF-a (previous block\'s pre '
                          'row) before the NORM, COEF-b (this block\'s post / combine rows) after it: same RTL, same golden',
                     layers=[dict(layer=l['layer'], single_coef=dict(layer_cycles=l['bench_layer_cycles'], norm_entry_wait=l['norm_entry_wait']),
                                  coef_split=dict(layer_cycles=S[l['layer']]['bench_layer_cycles'], norm_entry_wait=S[l['layer']]['norm_entry_wait'],
                                                  verdict=S[l['layer']]['verdict']),
                                  saved=l['bench_layer_cycles'] - S[l['layer']]['bench_layer_cycles']) for l in P if l['layer'] in S])
        # what the single-COEF program costs a token if the die program is written like the bench: per block, the
        # entry wait it adds over the split program
        add = {}
        for l in P:
            if l['layer'] in S:
                for blk in ('attn', 'ffn'):
                    add[blk + '.hc_pre'] = max(add.get(blk + '.hc_pre', 0),
                                               l['norm_entry_wait'][blk] - S[l['layer']]['norm_entry_wait'][blk])
        chain['token_if_single_coef'] = dict(added_per_block=add, token=token_loss(add))
    rec = dict(schema='opentallas.s81_layer_tput.v2', primary=a.primary, runs=runs, mutants=muts,
               hc_production=dict(NORM=norm, H_LOAD=hl, H_STORE=hs, COEF=cf,
                                  POST_tail=max(v['post_tail'] for l in P for v in l['allreduce_post'].values())),
               delta_by_op={k: round(v, 1) for k, v in d.items()}, e2e_norm=token_loss(d), unpriced_serial=serial,
               coefficient_chain=chain)
    rec['handoffs'] = handoffs()
    if a.lvm:
        rec['vm_read_measured'] = vm_read_measured(a.lvm)
    if a.extra:
        rec.update(json.loads(a.extra.read_text()))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    for name, r in runs.items():
        for l in r['layers']:
            print('%-10s %-4s %s NG %s split %d layer %6d  HC %s  pair %s  entry %s' % (
                name, l['layer'], l['verdict'], l['ng'], l['coef_split'], l['bench_layer_cycles'], l['hc_jobs'],
                {k: (v['pair'], v['ratio'], v['post_tail']) for k, v in l['allreduce_post'].items()}, l['norm_entry_wait']))
            for k, c in l['classes'].items():
                if k.startswith('coll'):
                    print('      %-28s measured %6d price %8.1f ratio %s' % (k, c['measured'], c['price'], c['ratio']))
    for k, m in muts.items():
        print('mutant', k, m['mode'], m['layer'], m['verdict'])
    print('NORM delta', rec['delta_by_op'], rec['e2e_norm'])
    print('serial', json.dumps(serial))
    if chain:
        print('chain', json.dumps({k: v for k, v in chain.items() if k != 'what'}))


if __name__ == '__main__':
    main()
