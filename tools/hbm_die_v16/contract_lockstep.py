#!/usr/bin/env python3
"""HBMc/CHAIN 10-22 r18h: contract-level LOCKSTEP of a relay/station layer against its base contract.

Every input bit of every non-relay instance is traced back through relay stations (hbfd_rly* o[j] <- i[j],
hbfd_lh*/hbfd_land* b[j] <- a[j]; each station = one register edge) to its ROOT source bit; result (root bit, depth).
Base vs new contract, per load PORT:
  identity  every bit keeps its root bit (no swap / drop / re-route)                       else FAIL
  lockstep  every bit of the port moves by the SAME depth delta (lanes in lockstep)        else FAIL
  plan      the port's delta equals the planned delta of its group (layer report)          listed per group
plus named equal-age checks: phy_<q>.row_v[p] at the same depth as row_op/row_bank/row_row of that PC (both 0 here).
Mutants (--mut, applied to the NEW contract in memory, each must FAIL): lane_stage (one bit of one station group
re-driven one stage later), bitswap (two bits of one station edge swapped), branch_drop (one station -> load edge removed).
    contract_lockstep.py BASE.json NEW.json --report R.json [--mut lane_stage|bitswap|branch_drop]
"""
import argparse, collections, json, re, sys
from pathlib import Path

RELAY = re.compile(r'^hbfd_(rly|lh|land)')
THRU = {'o': 'i', 'b': 'a'}


def trace(c):
    I = c['instances']
    drv = {}
    for e in c['edges']:
        si, sp, slo, shi = e['source']; di, dp, dlo, dhi = e['sink']
        for j in range(shi - slo):
            drv[(di, dp, dlo + j)] = (si, sp, slo + j)
    memo = {}

    def root(si, sp, b):
        key = (si, sp, b); path = []
        while True:
            if key in memo:
                r, d = memo[key]; break
            m = I.get(key[0], {}).get('master', '')
            if RELAY.match(m) and key[1] in THRU:
                path.append(key)
                nxt = drv.get((key[0], THRU[key[1]], key[2]))
                if nxt is None:
                    r, d = ('UNDRIVEN', key[0], key[2]), 0; break
                key = nxt; continue
            r, d = key, 0; break
        for k in reversed(path):
            d += 1; memo[k] = (r, d)
        return memo[path[0]] if path else (r, d)
    out = {}
    for (di, dp, b), (si, sp, sb) in drv.items():
        m = I.get(di, {}).get('master', '')
        if RELAY.match(m):
            continue
        out[(di, dp, b)] = root(si, sp, sb)
    return out


def mutate(c, mut):
    E = c['edges']
    st = [e for e in E if e.get('region') == 'r18h_stations' and not RELAY.match(c['instances'][e['sink'][0]]['master'])]
    st.sort(key=lambda e: e['name'])
    if mut == 'branch_drop':
        e = st[0]; E.remove(e); return f"dropped {e['name']} {e['source']} -> {e['sink']}"
    if mut == 'bitswap':
        e = next(e for e in st if e['bits'] >= 2)
        si, sp, lo, hi = e['source']; di, dp, dlo, dhi = e['sink']
        E.remove(e)
        E.append(dict(e, name=e['name'] + '_a', bits=1, source=[si, sp, lo, lo + 1], sink=[di, dp, dlo + 1, dlo + 2]))
        E.append(dict(e, name=e['name'] + '_b', bits=1, source=[si, sp, lo + 1, lo + 2], sink=[di, dp, dlo, dlo + 1]))
        if e['bits'] > 2:
            E.append(dict(e, name=e['name'] + '_c', bits=e['bits'] - 2, source=[si, sp, lo + 2, hi], sink=[di, dp, dlo + 2, dhi]))
        return f"swapped bits 0/1 of {e['name']}"
    if mut == 'lane_stage':
        # one bit of one station group passes through one more station (an existing relay re-used as an extra stage:
        # a fresh 1-bit relay instance on that bit)
        e = next(e for e in st if e['bits'] >= 2)
        si, sp, lo, hi = e['source']; di, dp, dlo, dhi = e['sink']
        I = c['instances']; m = I[si]
        n = 'mut_lane_stage'
        I[n] = dict(m, ports={'ck': {'direction': 'input', 'bits': 1}, 'rs': {'direction': 'input', 'bits': 1},
                              'i': {'direction': 'input', 'bits': 1}, 'o': {'direction': 'output', 'bits': 1}})
        E.remove(e)
        E.append(dict(e, name=e['name'] + '_m0', bits=1, source=[si, sp, lo, lo + 1], sink=[n, 'i', 0, 1]))
        E.append(dict(e, name=e['name'] + '_m1', bits=1, source=[n, 'o', 0, 1], sink=[di, dp, dlo, dlo + 1]))
        E.append(dict(e, name=e['name'] + '_m2', bits=e['bits'] - 1, source=[si, sp, lo + 1, hi], sink=[di, dp, dlo + 1, dhi]))
        return f"lane 0 of {e['name']} +1 stage"
    raise SystemExit(f'unknown mutant {mut}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('base'); ap.add_argument('new'); ap.add_argument('--report', required=True); ap.add_argument('--mut')
    a = ap.parse_args()
    B = json.loads(Path(a.base).read_text()); N = json.loads(Path(a.new).read_text())
    mdesc = mutate(N, a.mut) if a.mut else None
    tb, tn = trace(B), trace(N)
    port = collections.defaultdict(list)
    ident_fail, missing = [], []
    for k, (r0, d0) in tb.items():
        v = tn.get(k)
        if v is None:
            if k[0] in N['instances']:
                missing.append(k)
            continue
        r1, d1 = v
        if r1 != r0:
            ident_fail.append((k, r0, r1))
        port[(k[0], k[1])].append(d1 - d0)
    new_only = [k for k in tn if k not in tb and k[0] in B['instances']]
    # PHY row_v is checked by its own equal-age rule below (moved to age 0 on purpose: per-bit delta differs, new age is uniform)
    lock_fail = {f'{p[0]}.{p[1]}': sorted(set(v)) for p, v in port.items() if len(set(v)) > 1
                 and not (p[0].startswith('phy_') and p[1] == 'row_v')}
    deltas = collections.Counter()
    fam = collections.defaultdict(collections.Counter)
    for p, v in port.items():
        d = v[0]
        if d:
            deltas[d] += 1
            fam[re.sub(r'_(SW|SE|NW|NE)', '_<q>', re.sub(r'\d+', '#', p[0])) + '.' + p[1]][d] += 1
    # named equal-age check: PHY row_v vs row_op/row_bank/row_row per PC (controller)
    phy = []
    for n, v in N['instances'].items():
        if not n.startswith('phy_') or 'row_v' not in v['ports']:
            continue
        for b in range(v['ports']['row_v']['bits']):
            rv = tn.get((n, 'row_v', b))
            ctl = rv[0][0] if rv else None
            sib = {p: [tn[(n, p, j)][1] for j in range(v['ports'][p]['bits']) if (n, p, j) in tn and tn[(n, p, j)][0][0] == ctl]
                   for p in ('row_op', 'row_bank', 'row_row')}
            phy.append(dict(phy=n, bit=b, ctl=ctl, row_v=rv[1] if rv else None, **{p: sorted(set(x)) for p, x in sib.items()}))
    phy_bad = [x for x in phy if not all(x[p] == [x['row_v']] for p in ('row_op', 'row_bank', 'row_row'))]
    ok = not ident_fail and not lock_fail and not missing and not phy_bad
    rep = dict(schema='opentallas.hbm.contract_lockstep.v1', base=a.base, new=a.new, mutant=a.mut, mutant_applied=mdesc,
               load_bits_base=len(tb), load_bits_new=len(tn), identity_fail=len(ident_fail), identity_examples=[str(x) for x in ident_fail[:10]],
               missing_load_bits=len(missing), missing_examples=[str(x) for x in missing[:10]], new_load_bits=len(new_only),
               lockstep_fail_ports=len(lock_fail), lockstep_examples=dict(list(lock_fail.items())[:10]),
               ports_moved_by_delta=dict(sorted(deltas.items())), moved_families={k: dict(v) for k, v in sorted(fam.items())},
               phy_rowv_checked=len(phy), phy_rowv_mismatch=len(phy_bad), phy_rowv_examples=phy[:4] + phy_bad[:4],
               verdict='PASS' if ok else 'FAIL')
    Path(a.report).write_text(json.dumps(rep, indent=1))
    print('CONTRACT_LOCKSTEP', rep['verdict'], json.dumps({k: rep[k] for k in ('mutant', 'identity_fail', 'missing_load_bits',
          'lockstep_fail_ports', 'phy_rowv_checked', 'phy_rowv_mismatch', 'ports_moved_by_delta')}))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
