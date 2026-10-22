#!/usr/bin/env python3
"""tok_func_hbm_xdie_report.py OUTROOT [--record record.json] [--grade G]  (TOK-FUNC-HBM-XDIE 2026-10-21)

Reads OUTROOT/<variant>/{src.manifest.json, run/cases.txt, run/*_pass.log} written by
rtl/hbm_accel/generic/collective/xdie/tok_func_xdie.sh and writes OUTROOT/report.json: per variant and case PASS/FAIL,
measured E (first VM request -> last delivery, max of the two dies, 1.2 GHz cycles) vs the reference values of
results/rtl/xdie_hbm_1019/record.json, plus the token-level composites (HBM-DS o-group AR = RS144 + AG144, MoE AG144,
HBM-Qwen TP8 hypercube AR = RS64 + RS32 + RS16 + AG16 + AG32 + AG64)."""
import argparse, json, pathlib, re

COMPOSITES = {
    'hbm_ds_ar_ogroup_rs144_ag144': ['ds_rs144', 'ds_ag144'],
    'hbm_ds_moe_ag144': ['ds_ag144'],
    'hbm_ds_ag144': ['ds_ag144'],
    'hbm_ds_rs144': ['ds_rs144'],
    'hbm_qwen_tp8_ar_hypercube': ['qw_rs64', 'qw_rs32', 'qw_rs16', 'qw_ag16', 'qw_ag32', 'qw_ag64'],
}


def refs(record):
    r = {}
    try:
        c = record['composed']['AG']
        for p, k in (('64', 'qw_ag64'), ('32', 'qw_ag32'), ('16', 'qw_ag16')):
            r[k] = {'ref': c['qw'][p], 'src': 'record.composed.AG.qw (= XDIE-HBM3 measured)'}
        r['ds_ag48'] = {'ref': c['ds']['48'], 'src': 'record.composed.AG.ds.48'}
        r['ds_ag144'] = {'ref': record['ag144_measured_vs_composed']['measured'],
                         'composed': record['ag144_measured_vs_composed']['composed_old'], 'src': 'record.ag144_measured_vs_composed'}
        for k, v in record['rs_measured_vs_composed'].items():
            r[k] = {'ref': v['measured'], 'composed': v['composed_old'], 'src': 'record.rs_measured_vs_composed'}
        r['ds_rs144'] = {'ref': record['rs144_measured_vs_composed']['measured'],
                         'composed': record['rs144_measured_vs_composed']['composed_old'], 'src': 'record.rs144_measured_vs_composed'}
    except (KeyError, TypeError):
        pass
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('outroot', type=pathlib.Path)
    ap.add_argument('--record', type=pathlib.Path)
    ap.add_argument('--grade', default='')
    a = ap.parse_args()
    rec = a.record or (a.outroot / 'ref_record.json')
    record = json.loads(rec.read_text()) if rec.exists() else {}
    R = refs(record)
    rep = {'schema': 'opentallas.tok_func_hbm_xdie.report.v1', 'outroot': str(a.outroot), 'reference_record': str(rec),
           'variants': {}}
    for vd in sorted(p for p in a.outroot.iterdir() if p.is_dir()):
        man = vd / 'src.manifest.json'
        if not man.exists():
            continue
        m = json.loads(man.read_text())
        run = vd / 'run'
        grade = a.grade or ('die-netlist' if m['variant'] == 'gen' else 'RTL-functional (source assembly)')
        V = {'grade': grade, 'rtl_rev': m['rtl_rev'], 'bench_rev': m['bench_rev'], 'dut_module': m['dut_module'],
             'defines': m['defines'], 'die_contract': m.get('die_contract'),
             'files_by_role': {}, 'host': (run / 'host.txt').read_text().strip() if (run / 'host.txt').exists() else None,
             'cases': {}, 'composites': {}}
        for f in m['files']:
            V['files_by_role'].setdefault(f['role'], 0)
            V['files_by_role'][f['role']] += 1
        V['successor_files'] = [f for f in m['files'] if f['role'] == 'successor']
        ct = run / 'cases.txt'
        txt = ct.read_text() if ct.exists() else ''
        done = re.search(r'TOKFUNC_XDIE_DONE \S+ rc=(\d+)', txt)
        V['status'] = 'DONE rc=%s' % done.group(1) if done else ('RUNNING' if (run / 'client.log').exists() else 'NOT RUN')
        for line in txt.splitlines():
            mm = re.match(r'CASE (\S+) (PASS|FAIL)\s*(.*)', line)
            if not mm:
                continue
            n, verdict, rest = mm.groups()
            c = {'verdict': verdict, 'detail': rest.strip()}
            e = re.search(r'XDIE3_E d0 (\d+) d1 (\d+)', rest)
            if e:
                c['E_dies'] = [int(e.group(1)), int(e.group(2))]
                c['E'] = max(c['E_dies'])
            pl = run / f'{n}_pass.log'
            if pl.exists():
                c['log'] = str(pl.relative_to(a.outroot))
                x = re.search(r'^XDIE2 .*$', pl.read_text(errors='replace'), re.M)
                if x:
                    c['xdie2'] = x.group(0)
            if n in R:
                c.update({k: v for k, v in R[n].items()})
                if 'E' in c:
                    c['delta_vs_ref'] = c['E'] - c['ref']
            V['cases'][n] = c
        for k, parts in COMPOSITES.items():
            cs = [V['cases'].get(p) for p in parts]
            if not any(cs):
                continue
            ok = all(c and c['verdict'] == 'PASS' and 'E' in c for c in cs)
            d = {'parts': parts, 'verdict': 'PASS' if ok else 'FAIL',
                 'failed_parts': [p for p, c in zip(parts, cs) if not (c and c['verdict'] == 'PASS')]}
            if ok:
                d['E'] = sum(c['E'] for c in cs)
                if all('ref' in c for c in cs):
                    d['ref'] = sum(c['ref'] for c in cs)
                    d['delta_vs_ref'] = d['E'] - d['ref']
                if all(('composed' in c or 'ref' in c) for c in cs):
                    d['composed_old'] = round(sum(c.get('composed', c.get('ref')) for c in cs), 1)
            V['composites'][k] = d
        rep['variants'][m['variant']] = V
    out = a.outroot / 'report.json'
    out.write_text(json.dumps(rep, indent=1) + '\n')
    for v, V in rep['variants'].items():
        print(v, V['status'], ' '.join('%s=%s%s' % (n, c['verdict'], '/%d' % c['E'] if 'E' in c else '') for n, c in V['cases'].items()))
    print('wrote', out)


if __name__ == '__main__':
    main()
