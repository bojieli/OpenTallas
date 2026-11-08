"""count dry run: QC qc52 vs qc52n with the counter's own functions (release_tree_plan), records from the counter cache"""
import json, os, pathlib, subprocess, sys, tempfile
sys.path.insert(0, '/home/ubuntu/coord/tools')
import release_tree_plan as R
os.environ['GIT_OPTIONAL_LOCKS'] = '0'
TREE, REV = sys.argv[1], sys.argv[2]
R.REPO = pathlib.Path(TREE)
tmp = pathlib.Path(tempfile.mkdtemp(prefix='nldry.', dir='/tmp/dq91'))
p1 = subprocess.Popen(['git', '-C', TREE, 'archive', REV, 'tools', 'physical/die_plan/qwen_compute'], stdout=subprocess.PIPE)
subprocess.run(['tar', '-x', '-C', str(tmp)], stdin=p1.stdout, check=True); p1.wait()
cache = json.load(open(R.CACHE))
recs = cache['signed_records']
names = R.retired_names()
out = {}
for lab in ('plan_qc52.json', 'plan_qc52n.json'):
    src = 'physical/die_plan/qwen_compute/plan_of_record/' + lab
    pj = R.materialize_plan(tmp, 'qwen_compute/plan_of_record', src, ())
    R.fetch_results_refs(tmp, pj, rev=REV)
    P = json.loads(pj.read_text()); T = P['partition_types']
    designs, rows = R.plan_designs(P, pj.parent)
    hard = sorted({h.get('module') for v in T.values() for h in (v.get('hard_cores') or []) if h.get('module') and not R.is_mem_macro(h)})
    tm = {k: (v.get('module') or k) for k, v in T.items()}
    core_recs, st = {}, {}
    for r_ in recs:
        if not (r_.get('versioned') or r_.get('legacy')): continue
        ks = R.rec_keys(r_)
        ref = r_['scan_host'] + ':' + r_['path']
        for k, m in tm.items():
            if (k in ks or m in ks) and not R.name_retired(r_, 'qwen_compute', names, (k, m)): st.setdefault(k, []).append(ref)
        for m in hard:
            if m in ks and not R.name_retired(r_, 'qwen_compute', names, (m,)): core_recs.setdefault(m, []).append((ref, r_))
    rp = R.fetch_rec_pins([r_ for m in core_recs for _, r_ in core_recs[m]])
    signed, unmatched = R.credit_designs(designs, rows, core_recs, rp)
    g = tmp / ('g0c_' + lab)
    secs = R._g0c_run(tmp, pj, g)
    try:
        rep = json.loads((g / 'g0_report.json').read_text()); gs = R.g0c_split(rep, list(T))
        g0 = dict(verdict=rep.get('verdict'), errors=rep.get('errors'), clean=gs['clean'], types=gs['types'], bad=sorted(gs['by_type']), die_level=gs['die_level'], s=secs)
    except Exception as e:
        g0 = dict(error=str(e))
    out[lab] = dict(designs=sorted(designs), signed=sorted(signed), unmatched={m: v for m, v in unmatched.items()},
                    signed_types=sorted(st), g0c=g0,
                    nl_design={k: v for k, v in designs.get('qfd_tile_nl_a0c', {}).items() if k != 'strap_variants'})
a, b = out['plan_qc52.json'], out['plan_qc52n.json']
summ = dict(rev=REV, cache_generated=cache['generated'], designs=(len(a['designs']), len(b['designs'])),
            signed=(len(a['signed']), len(b['signed'])), gained=sorted(set(b['signed']) - set(a['signed'])),
            lost=sorted(set(a['signed']) - set(b['signed'])), signed_types=(len(a['signed_types']), len(b['signed_types'])),
            types_lost=sorted(set(a['signed_types']) - set(b['signed_types'])),
            g0c=(a['g0c'], b['g0c']))
json.dump(dict(summary=summ, detail=out), open('/tmp/dq91/nl_dryrun.json', 'w'), indent=1, default=str)
print(json.dumps(summ, indent=1, default=str))
for m, v in b['unmatched'].items(): print('UNMATCHED(qc52n)', m, v[0][:400])
