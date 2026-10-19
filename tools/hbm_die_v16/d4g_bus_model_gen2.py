#!/usr/bin/env python3
"""H-D4G GEN2 10-18: the bus / lever-2 model (plan_d4g.py's d4g_vs_b) re-run on the d4g netlist itself.

Why a new tool: d4g_vs_b.json was computed on the run8 (d4f) bus rows mapped from the run8 d4f die placement into the
plans; that manifest is deleted everywhere (local, epyc4/epyc5/pve1/agidock checked 10-18), and d4g is the adopted plan,
so the honest metric is the d4g netlist on the d4g geometry ("plan a" mode = positions are the real placement):
  rows      tools/hbm_die_v16/d4g_bus_rows.py on a d4g contract (pre-relay layers output or a generated contract);
  positions --manifest M.json   die-case manifest placement (die_case_v16), exact; or
            --grants G.json     (no manifest) the grants as die_case_v16 places them: an instance alone in its grant
                                slot at the slot origin / outline; an instance sharing a slot or hosted by a plan block
                                at the slot / block centre (its size from the slot when alone, else a 100x100 um token).
  metrics   plan_study_1017.bus_metrics (bit-mm, relay tiles at 380-um spacing / 405-um reach, equal-age depth per
            domain, longest bus, clock-region pairs on a 4-mm grid) + plan_d4g.bundle_metrics (lever 2: lane bundles
            per (driver block, sink blocks, domain), relay tiles, station rows, landing tiles) with the blocks of --plan.
    d4g_bus_model_gen2.py --contract C.json[.gz] (--manifest M.json | --grants G.json) --plan P.json --label L
                          [--slot-map a=b,...] --out OUT.json [--png OUT.png] [--merge-into EXISTING.json]"""
import argparse, collections, gzip, json, math, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/hbm_die_v15'))
sys.path.insert(0, str(ROOT / 'tools/hbm_die_v16'))
import plan_study_1017 as S  # noqa: E402
import plan_d4g as PD  # noqa: E402

SM_DEFAULT = ('wbk_SW=wbk_SW,wbk_NW=wbk_NW,sfup_SW=sfup_SW,sfup_SE=sfup_SE,sfup_NW=sfup_NW,sfup_NE=sfup_NE,'
              'refcfg_SW=refcfg_SW,refcfg_NW=refcfg_NW')   # = gen_d4g1.sh --slot-map


def ld(p):
    return json.load(gzip.open(p, 'rt') if str(p).endswith('.gz') else open(p))


def grants_placement(C, G, P, slot_map, fallback=False):
    """die_case_v16's grant homes at plan resolution: slot = the instance's 'slot' (or --slot-map), else a slot / plan
    block named like the instance; child slots in die coordinates (parent origins added); alone in a slot -> slot rect,
    sharing -> slot centre; plan block -> its centre; none -> the quadrant's sucore_<q> block (die-level: idx_op) and
    counted as 'fallback' (only with --fallback; default: unplaced, its buses listed as missing)."""
    I = C['instances']
    allslots = {s['name']: s for s in G['slots']}
    slots = {k: s for k, s in allslots.items() if s.get('origin') and s['kind'] != 'die'}

    def absxy(s):
        x, y = s['origin']['x'], s['origin']['y']
        p = allslots.get(s.get('parent') or 'die')
        while p is not None and p['kind'] != 'die':
            x += p['origin']['x']; y += p['origin']['y']; p = allslots.get(p.get('parent') or 'die')
        return x, y
    sm = dict(kv.split('=') for kv in slot_map.split(',') if kv)
    inP = lambda k: k in P and isinstance(P[k], dict) and 'x' in P[k]

    def eslot(n):
        for k in (sm.get(n), I[n].get('slot'), n):
            if k and (k in slots or inP(k)):
                return k
        return None
    users = collections.defaultdict(list)
    for n in I:
        users[eslot(n)].append(n)
    pl, how = {}, collections.Counter()
    tok = lambda m, cx, cy: dict(m=m, x=cx - 50, y=cy - 50, w=100, h=100, o='R0')
    for n, v in I.items():
        if v['master'].startswith(('hbfd_rly', 'hfd_stn', 'hbfd_lh', 'hbfd_land')):
            continue
        s = eslot(n)
        if s in slots:
            (x, y), w = absxy(slots[s]), slots[s]['outline']
            if len(users[s]) == 1:
                pl[n] = dict(m=v['master'], x=x, y=y, w=w['w'], h=w['h'], o=slots[s]['origin'].get('orient', 'R0')); how['slot'] += 1
            else:
                pl[n] = tok(v['master'], x + w['w'] / 2, y + w['h'] / 2); how['shared_slot'] += 1
        elif s is not None:
            b = P[s]; pl[n] = tok(v['master'], b['x'] + b['w'] / 2, b['y'] + b['h'] / 2); how['plan_block'] += 1
        elif not fallback:
            how['unplaced'] += 1                 # its rows are counted in bus.missing, not routed
        else:
            q = S.inst_quadrant(n)
            b = P.get(f'sucore_{q}') if q else None
            b = b or P['idx_op']
            pl[n] = tok(v['master'], b['x'] + b['w'] / 2, b['y'] + b['h'] / 2); how['fallback'] += 1
    return pl, dict(how)


def buses_from_rows(rows):
    out = []
    for r in rows:
        drv, port = r['driver'].split('.', 1)
        dq = S.inst_quadrant(drv)
        xq = any(S.inst_quadrant(x) not in (None, dq) for x in r['sinks']) if dq else False
        out.append(dict(driver=drv, port=port, sinks=list(r['sinks']), bits=r['bits'], domain=r['domain'], xq=xq,
                        cls=r['cls'], cfg=r['cls'] == 'cfg_no_pad' or (drv.startswith('host_cp') and r['domain'] == 'serial')))
    return out


def run(a):
    C = ld(a.contract)
    with tempfile.TemporaryDirectory() as td:
        cj = Path(td) / 'c.json'
        cj.write_text(json.dumps(C))
        rj = Path(td) / 'rows.json'
        subprocess.run([sys.executable, str(ROOT / 'tools/hbm_die_v16/d4g_bus_rows.py'), str(cj), '--out', str(rj)], check=True,
                       stdout=subprocess.DEVNULL)
        rows = json.loads(rj.read_text())['rows']
    P = ld(a.plan)
    P = {k: v for k, v in P.items() if isinstance(v, dict) and 'x' in v}
    if a.manifest:
        man = ld(a.manifest)
        pl = {k: v for k, v in man['placement'].items() if not v['m'].startswith(('hbfd_rly', 'hfd_stn', 'hbfd_lh', 'hbfd_land'))}
        how = dict(manifest=len(pl)); W, H = man['die_um']
    else:
        G = ld(a.grants)
        pl, how = grants_placement(C, G, P, a.slot_map, a.fallback)
        W, H = G['floorplan']['die_um']
    pos = {n: dict(x=v['x'], y=v['y'], w=v['w'], h=v['h']) for n, v in pl.items()}
    buses = buses_from_rows(rows)
    bm = S.bus_metrics(buses, pos, (W, H, math.ceil(W / 4000), math.ceil(H / 4000)))
    bm['relay_tiles_calibrated'] = int(round(bm['tiles'] * 1.376))
    deep = sorted(bm.pop('deep', []), reverse=True)[:12]
    l2 = PD.bundle_metrics(buses, pos, P)
    res = dict(label=a.label, mode='manifest' if a.manifest else 'grants', contract=str(a.contract),
               positions=str(a.manifest or a.grants), plan=str(a.plan), die_um=[W, H], die_mm2=round(W * H / 1e6, 2),
               rows=len(rows), placement=how, bus=bm, deepest=deep, lever2=l2)
    return res, pos, buses


def draw(png, results):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    keys = ['bit_mm', 'tiles', 'relay_tiles_calibrated']
    l2k = ['relay_tiles', 'station_rows', 'landing_tiles', 'bundles']
    labs = list(results)
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6), dpi=150)
    for ax, ks, src in ((axs[0], keys, 'bus'), (axs[1], l2k, 'lever2')):
        x = range(len(ks)); wd = 0.8 / max(len(labs), 1)
        for i, l in enumerate(labs):
            vals = [results[l][src].get(k, 0) for k in ks]
            bars = ax.bar([j + i * wd for j in x], vals, wd, label=l)
            for b_, v in zip(bars, vals):
                ax.text(b_.get_x() + b_.get_width() / 2, b_.get_height(), f'{v:,.0f}', ha='center', va='bottom', fontsize=5)
        ax.set_xticks([j + wd * (len(labs) - 1) / 2 for j in x]); ax.set_xticklabels(ks, fontsize=7)
        ax.set_title(f'{src} model', fontsize=8); ax.tick_params(labelsize=6); ax.legend(fontsize=6)
    fig.suptitle('H-D4G GEN2 bus / lever-2 model on the d4g netlist (positions: ' +
                 ', '.join(f"{l}={results[l]['mode']}" for l in labs) + ')', fontsize=8)
    fig.tight_layout(); fig.savefig(png); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--contract', required=True); ap.add_argument('--manifest'); ap.add_argument('--grants')
    ap.add_argument('--plan', required=True); ap.add_argument('--label', required=True)
    ap.add_argument('--slot-map', default=SM_DEFAULT); ap.add_argument('--out', required=True); ap.add_argument('--png')
    ap.add_argument('--fallback', action='store_true', help='grants mode: home unslotted instances at their quadrant sucore block')
    ap.add_argument('--merge-into', help='add this run under its label to an existing result file (written to --out)')
    a = ap.parse_args()
    if not (a.manifest or a.grants):
        raise SystemExit('need --manifest or --grants')
    res, _, _ = run(a)
    allr = {}
    if a.merge_into and Path(a.merge_into).is_file():
        allr = json.loads(Path(a.merge_into).read_text()).get('runs', {})
    allr[a.label] = res
    doc = dict(schema='opentallas.hbm.d4g.gen2_bus_model.v1', tool='tools/hbm_die_v16/d4g_bus_model_gen2.py',
               note='d4g netlist on d4g geometry (plan "a" mode); replaces the stale run8-manifest d4g_vs_b for GEN2 '
                    '(d4g_vs_b.json left untouched)', runs=allr)
    if len(allr) > 1:
        ks = list(allr)
        base, new = allr[ks[0]], allr[ks[-1]]
        doc['delta'] = {f'{ks[-1]} - {ks[0]}': dict(
            bit_mm=round(new['bus']['bit_mm'] - base['bus']['bit_mm'], 1), tiles=new['bus']['tiles'] - base['bus']['tiles'],
            l2_relay_tiles=new['lever2']['relay_tiles'] - base['lever2']['relay_tiles'],
            l2_station_rows=new['lever2']['station_rows'] - base['lever2']['station_rows'],
            l2_landing_tiles=new['lever2']['landing_tiles'] - base['lever2']['landing_tiles'],
            die_mm2=round(new['die_mm2'] - base['die_mm2'], 2))}
    Path(a.out).write_text(json.dumps(doc, indent=1, default=list))
    if a.png:
        draw(a.png, allr)
    b, l2 = res['bus'], res['lever2']
    print('BUS_MODEL', a.label, res['mode'], 'rows', res['rows'], 'placement', res['placement'], 'bit_mm', round(b['bit_mm']),
          'tiles', b['tiles'], 'longest', b['longest'], 'missing', len(b['missing']), '| L2 tiles', l2['relay_tiles'],
          'rows', l2['station_rows'], 'landing', l2['landing_tiles'], 'bundles', l2['bundles'])


if __name__ == '__main__':
    main()
