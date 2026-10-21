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
    p.add_argument('--mu-link')
    p.add_argument('--layers')
    p.add_argument('--owner-fold')
    p.add_argument('--kv-consumer')
    p.add_argument('--dense-source')
    p.add_argument('--head-die')
    p.add_argument('--layer-gaps')
    p.add_argument('--die-v')
    a = p.parse_args()
    evidence = {}
    for name in ('head', 'mu', 'mu_link', 'layers', 'owner_fold', 'kv_consumer', 'dense_source', 'head_die', 'layer_gaps'):
        path = getattr(a, name)
        f = Path(path) if path else None
        evidence[name] = dict(path=path, status='PENDING')
        if f and f.is_file():
            raw = f.read_bytes()
            evidence[name].update(sha256=hashlib.sha256(raw).hexdigest(), receipt=json.loads(raw))
            evidence[name]['status'] = 'RECORDED'
    # A phase0 component run may share the same graph digest. Only explicit
    # terminal phase2/deadline proof qualifies the current source link scope.
    link = evidence['mu_link'].get('receipt') or {}
    phase = link.get('phase_congruence') or {}
    checks = dict(terminal_pass=link.get('result') == 'PASS' and (link.get('run') or {}).get('exit') == 0,
                  graph_phase_two=phase.get('quantum') == 4 and phase.get('graph_first_send') == 18138,
                  exact_rebase=phase.get('bench_first_issue') == 12002 and phase.get('offset') == -6136,
                  phase_preserved=phase.get('preserved') is True,
                  deadlines=link.get('absolute_deadlines_checked') is True,
                  landing_lower_bounds=link.get('first_landing_lower_bounds_checked') is True,
                  all_positions=link.get('positions_executed') == 6 and link.get('beats') == 3840)
    current_link = dict(status='PASS_SOURCE_COMPONENT' if all(checks.values()) else 'PENDING_CURRENT_SOURCE_LINK',
                        checks=checks, current_token_provenance_qualified=link.get('current_token_provenance_qualified', False),
                        qualification_scope=link.get('qualification_scope', 'PENDING_EXPLICIT_COMPONENT_SCOPE'),
                        cycle_domain='absolute bench cycles with certified offset -6136; no HOST/KS global epoch',
                        qualification='Explicit phase2 source link only; HOST/KS, whole stage, rates and full token remain separate')
    selected_calendar = (evidence['mu'].get('receipt') or {}).get('calendar', {}).get('selected')
    # Component receipts remain scoped. A serial composition and independent
    # endpoint benches do not establish an end-to-end token delivery verdict.
    record = dict(schema='opentallas.tokfunc_s81.v1', source_ref=a.ref,
        grade='die-netlist' if a.grade == 'netlist' else 'RTL-functional (source assembly)',
        verdict='INCOMPLETE', full_token_pass=False,
        evidence=evidence, current_mu_link_qualification=current_link,
        selected_calendar_model=selected_calendar or dict(status='PENDING_EXPLICIT_SELECTED_CALENDAR'),
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
