"""DIE-PROTO-3: per signed type, find its signed-store record (alias = counted signoff ref) and emit a die_sta_related
--kit partition interface model {corners:{TT,FF:{lat_min_ps,lat_max_ps,clkq_*,setup_ps,hold_ps}}}.
lat = the SIGNED view's own pin-register clock insertion (signoff.json corners.<c>.insertion_pinflops min/max).
Register arcs (clkq/setup/hold) = the die STA's declared ASAP7 DFF characterisation at that corner (passed in), since the
signoff record carries no per-register arcs; labelled in 'basis'."""
import gzip, json, glob, sys, os
refs, die, reg_json, outdir = sys.argv[1:5]
R = json.load(open(refs))[die]
reg = json.load(open(reg_json))
os.makedirs(outdir, exist_ok=True)
want = {}
for t, rs in R['signed_types'].items():
    for r in rs:
        want[r] = t
found = {}
for f in glob.glob(os.path.expanduser('~/coord/signed-store/records/*/*.json.gz')):
    d = json.load(gzip.open(f))
    al = set(d.get('aliases') or []) | {d.get('origin') or ''}
    for a in al:
        t = want.get(a)
        if t and t not in found:
            found[t] = (a, f, d)
summary = {}
for t in sorted(R['signed_types']):
    if t not in found:
        summary[t] = dict(status='NO_STORE_RECORD', refs=R['signed_types'][t]); continue
    a, f, d = found[t]
    so = d.get('signoff_json')
    if isinstance(so, str):
        import base64
        try: so = json.loads(gzip.decompress(base64.b64decode(so)))
        except Exception:
            try: so = json.loads(so)
            except Exception: so = None
    if not isinstance(so, dict) or 'corners' not in so:
        summary[t] = dict(status='NO_SIGNOFF_JSON', ref=a, store=f, keys=list(d)); continue
    corners = {}
    for C, c in (('TT', 'tt'), ('FF', 'ff')):
        ip = so['corners'][c]['insertion_pinflops']
        r = reg[C]
        corners[C] = dict(lat_min_ps=ip['min'], lat_max_ps=ip['max'], clkq_max_ps=r['clkq_max_wire_ps'],
                          clkq_min_ps=r['clkq_min_nowire_ps'], setup_ps=r['setup_ps'], hold_ps=r['hold_ps'],
                          pinflops_n=ip['n'], pinflops_mean=ip['mean'])
    m = dict(schema='dieproto3.kit_model.v1', type=t, verdict=so.get('verdict'), store_verdict=d.get('verdict'), ref=a, store=f,
             src_commit=d.get('src_commit'), flow_tag=d.get('flow_tag'), top=d.get('top'),
             basis='lat = signed signoff insertion_pinflops min/max per corner; clkq/setup/hold = declared ASAP7 DFF arcs '
                   '(die_sta_related REG at the corner; record carries no register arcs)',
             signoff_checks={k: (v.get('wns_ps') if isinstance(v, dict) else v) for k, v in (so.get('checks') or {}).items()},
             corners=corners)
    json.dump(m, open(os.path.join(outdir, t + '.kit.json'), 'w'), indent=1)
    summary[t] = dict(status='OK', verdict=so.get('verdict'), lat_TT=[corners['TT']['lat_min_ps'], corners['TT']['lat_max_ps']],
                      lat_FF=[corners['FF']['lat_min_ps'], corners['FF']['lat_max_ps']], ref=a)
json.dump(summary, open(os.path.join(outdir, 'SUMMARY.json'), 'w'), indent=1)
for t, s in summary.items(): print(t, s['status'], s.get('lat_TT'), s.get('lat_FF'))
