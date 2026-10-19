#!/usr/bin/env python3
"""HC-XRDU 10-18 (RELEASE_TREE H.STA.WIRE.8): hc_eng XRD / XRU = the LANDED root <-> quarter-hub latency, per quarter.

    d4g_hc_xr.py CONTRACT.json[.gz] [--apply OUT.json[.gz]] [--report R.json]

On the d4g die the HC root (hc_eng = ot_hbm_hc_root_static, die centre) talks to the 4 quarter hubs hc_<q>
(ot_hbm_hc_qhub_static) over long landed lanes: half-cycle forwarded stations + a 4-slot landing (fixed latency, no
backpressure).  The root's compiled schedule depends on the latency of those links:
  XRD  root out flop -> quarter pin flop, descriptor qd_* + ingest event qi_*   (hc_eng.qd_*/qi_* -> hc_<q>.d_*/i_*)
  XRU  quarter out flop -> root pin flop, subtree sums + faults + gathered mix (hc_<q>.ps*/eng_fault/gathered_mix_* ->
       hc_eng.qps*/q_fault/gathered_mix_*)
This tool reads the COMPILED contract (after the relay / landing layer), traces every bit of those paths through the die
relays and landings (d4g_functional_bind.trace semantics), and takes each bit's compiled latency from the instances on its
path (d4g_functional_bind.chain_latency: plain relay = 1 edge, landed lane = ceil(N/2) + 1 + E = 1 + K' with K' from the
landing's K strap).  Every bit of one quarter and direction must agree.  Result:
  XRDQ / XRUQ = per-quarter latency bytes (byte q, q = SW, SE, NW, NE)   XRD / XRU = their maxima (compiler constants)
ot_hbm_hc_root_static pads quarter q internally by XRD - XRDQ[q] / XRU - XRUQ[q] so every quarter runs on the one
compiled timeline (RAW0 = 167 + XRD + XRU, ingest events 2 + XRD edges ahead of the wave cadence; QDRLY 2 form).
--apply writes these 4 parameters into hc_eng's params (no other change; the strict port bind and
d4g_functional_bind.py -- slot rules now enabled on landed paths -- then check the result).
Exit 0 when every path was resolved and agrees, 1 otherwise.  Prints HC_XR {...}.
"""
import argparse, collections, gzip, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4g_functional_bind as FB  # noqa: E402

RAW0_BASE = 167   # ot_hbm_hc_root_static RAW0 at XRD = XRU = 0, QDRLY 2 (claude/eg-hbmb-hcroot-1018 hcroot_m0 / raw165 witnesses)


def derive(c):
    I = c['instances']
    drv = {}
    for e in c['edges']:
        si, sp, slo, shi = e['source']; ki, kp, klo, khi = e['sink']
        for b in range(khi - klo):
            drv[(ki, kp, klo + b)] = (si, sp, slo + b)
    strap_v = {(s['inst'], s['port']): s.get('value', 0) for s in c.get('straps', []) if s['hi'] - s['lo'] == 1}

    def trace(i, p, b):
        ch = []
        while True:
            d = drv.get((i, p, b))
            if d is None:
                return None, ch
            si, sp, sb = d
            m = I.get(si, {}).get('master', '')
            if FB.RELAY.match(m) and sp in FB.THRU:
                ch.append((si, m)); i, p, b = si, FB.THRU[sp], sb; continue
            return d, ch

    per = collections.defaultdict(lambda: collections.defaultdict(set))   # (dir, q) -> latency -> {path}
    detail, problems = [], []
    for x in FB.spec():
        st = x.get('stages')
        if not st or st[0] != 'hc_eng':
            continue
        dirn, q = st[1], FB.QS[st[3]]
        (si, sp, slo), (di, dp, dlo), w = x['src'], x['dst'], x['w']
        pid = f'{si}.{sp}[{slo}+:{w}]->{di}.{dp}[{dlo}]'
        lats, nst, landed = set(), set(), False
        for b in range(w):
            d, ch = trace(di, dp, dlo + b)
            if d != (si, sp, slo + b):
                problems.append(f'{pid}: bit {b} not driven by its producer ({d})'); break
            L, ld, pr = FB.chain_latency(ch, I, strap_v)
            if pr:
                problems.append(f'{pid}: {pr}'); break
            lats.add(L); nst.add(len(ch)); landed |= ld
        for L in lats:
            per[(dirn, q)][L].add(pid)
        detail.append(dict(path=pid, dir=dirn, q=q, latency=sorted(lats), relays=sorted(nst), landed=landed))
    out = {}
    for dirn in ('XRD', 'XRU'):
        byq = {}
        for q in FB.QS:
            ls = per.get((dirn, q), {})
            if len(ls) != 1:
                problems.append(f'{dirn} {q}: latencies {sorted(ls)} (must be one value per quarter and direction)')
                byq[q] = None
            else:
                byq[q] = next(iter(ls))
        out[dirn] = byq
    ok = not problems and all(v is not None and 0 <= v <= 255 for d in out.values() for v in d.values())
    res = dict(ok=ok, problems=problems[:40], per_quarter=out, paths=detail)
    if ok:
        xrd, xru = max(out['XRD'].values()), max(out['XRU'].values())
        pack = lambda d: sum(d[q] << (8 * i) for i, q in enumerate(FB.QS))
        res['params'] = dict(XRD=xrd, XRU=xru, XRDQ=pack(out['XRD']), XRUQ=pack(out['XRU']))
        res['params_hex'] = {k: f"32'h{v:08x}" for k, v in res['params'].items() if k.endswith('Q')}
        res['pads'] = {d: {q: (xrd if d == 'XRD' else xru) - out[d][q] for q in FB.QS} for d in ('XRD', 'XRU')}
        res['compiler'] = dict(RAW0=RAW0_BASE + xrd + xru, ingest_lead=2 + xrd,
                               note='RAW0 = 167 + XRD + XRU (QDRLY 2); ingest event fires 2 + XRD edges before the wave '
                                    'cadence; every quarter on the same timeline (root pads)')
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('contract'); ap.add_argument('--apply'); ap.add_argument('--report')
    a = ap.parse_args()
    c = FB.load(a.contract)
    if 'hc_eng' not in c['instances']:
        print('HC_XR FAIL no hc_eng instance'); sys.exit(1)
    res = derive(c)
    res['contract'] = str(a.contract)
    if a.apply and res['ok']:
        P = c['instances']['hc_eng'].setdefault('params', {})
        res['params_before'] = {k: P.get(k) for k in ('XRD', 'XRU', 'XRDQ', 'XRUQ')}
        P.update(res['params'])
        op = gzip.open if a.apply.endswith('.gz') else open
        with op(a.apply, 'wt') as f:
            json.dump(c, f, indent=0)
    if a.report:
        Path(a.report).write_text(json.dumps(res, indent=1) + '\n')
    print('HC_XR', 'PASS' if res['ok'] else 'FAIL', json.dumps(dict(per_quarter=res['per_quarter'], params=res.get('params'),
                                                                   compiler=res.get('compiler'), problems=res['problems'][:6])))
    sys.exit(0 if res['ok'] else 1)


if __name__ == '__main__':
    main()
