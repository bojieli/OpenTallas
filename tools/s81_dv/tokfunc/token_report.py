#!/usr/bin/env python3
"""Compose scoped receipts without promoting models or missing coverage to PASS."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--work', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--grade', choices=['source', 'netlist'], default='source')
    p.add_argument('--ref', required=True)
    p.add_argument('--head')
    p.add_argument('--mu')
    p.add_argument('--layers')
    p.add_argument('--owner-fold')
    p.add_argument('--die-v')
    a = p.parse_args()
    evidence = {}
    for name in ('head', 'mu', 'layers', 'owner_fold'):
        path = getattr(a, name)
        f = Path(path) if path else None
        evidence[name] = dict(path=path, status='PENDING')
        if f and f.is_file():
            raw = f.read_bytes()
            evidence[name].update(sha256=hashlib.sha256(raw).hexdigest(), receipt=json.loads(raw))
            evidence[name]['status'] = 'RECORDED'
    # Component receipts remain scoped. A serial composition and independent
    # endpoint benches do not establish an end-to-end token delivery verdict.
    record = dict(schema='opentallas.tokfunc_s81.v1', source_ref=a.ref,
        grade='die-netlist' if a.grade == 'netlist' else 'RTL-functional (source assembly)',
        verdict='INCOMPLETE', full_token_pass=False,
        evidence=evidence,
        calendar_model=dict(grade='SUPERSEDED FAILED MODEL (same-user MTP circuit collision)', stages=241,
            attention='G4', source_ref='6f8bbf5c4',
            ar=dict(users=50, per_user_tokens_s=952.8, aggregate_tokens_s=47642),
            mtp=dict(users=10, per_user_tokens_s=2963.4, aggregate_tokens_s=29634),
            qualification='Prior selected rates invalid as a qualified calendar: 200/240 MTP hops collide, max424 cycles. Historical inputs only; corrected schedule required.'),
        required_coverage=['four representative layer replays against fixtures',
            'chained layer and full-token boundary identity',
            'LM head and MTP draft body/sequence',
            'AR50 and MTP10 calendar traffic with all required hops'],
        netlist_coverage='PENDING: every required component must consume the exact GEN netlist; source-only component benches remain source evidence')
    if a.die_v:
        f = Path(a.die_v)
        record['die_v'] = dict(path=str(f), sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + '\n')
    print(f'{out}: INCOMPLETE (component receipts preserved, full-token PASS not established)')


if __name__ == '__main__':
    main()
