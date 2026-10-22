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
    p.add_argument('--entry-norm')
    p.add_argument('--aggregate-source')
    p.add_argument('--entry-producer')
    p.add_argument('--entry-replay', help='run_entry_replay.py entry_replay.json (native HOST jobs on the u_seqhost cut)')
    p.add_argument('--ladder', help='rung/gap ledger (results/token_pass/tokfunc3_s81_1021/ladder.json)')
    p.add_argument('--die-v')
    a = p.parse_args()
    evidence = {}
    for name in ('head', 'mu', 'mu_link', 'layers', 'owner_fold', 'kv_consumer', 'dense_source',
                 'entry_norm', 'aggregate_source', 'entry_producer', 'entry_replay'):
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
    model_identity = dict(calendar_sha256='04145d2cd1b03ff3ff29d5047fb9791a0d77a6f80caaf6cdd58ccffc81f0b233',
                          graph_sha256='8fde842fb6f61fb31d6024c300dcbcd27538836d63f50f1faa90454f9d98ddc5')
    checks = dict(exact_bound_model=all(link.get(k) == v for k,v in model_identity.items()),
                  terminal_pass=link.get('result') == 'PASS' and (link.get('run') or {}).get('exit') == 0,
                  graph_phase_two=phase.get('quantum') == 4 and phase.get('graph_first_send') == 18138,
                  exact_rebase=phase.get('bench_first_issue') == 12002 and phase.get('offset') == -6136,
                  phase_preserved=phase.get('preserved') is True,
                  deadlines=link.get('absolute_deadlines_checked') is True,
                  landing_lower_bounds=link.get('first_landing_lower_bounds_checked') is True,
                  all_positions=link.get('positions_executed') == 6 and link.get('beats') == 3840)
    current_link = dict(status='PASS_SOURCE_COMPONENT' if all(checks.values()) else 'PENDING_CURRENT_SOURCE_LINK',
                        checks=checks, bound_model={k:link.get(k) for k in model_identity},
                        bound_model_grade='MODEL identity attached to one source transport component',
                        current_token_provenance_qualified=link.get('current_token_provenance_qualified', False),
                        qualification_scope=link.get('qualification_scope', 'PENDING_EXPLICIT_COMPONENT_SCOPE'),
                        cycle_domain='absolute bench cycles with certified offset -6136; no HOST/KS global epoch',
                        qualification='Explicit phase2 source link only; HOST/KS, whole stage, rates and full token remain separate')
    selected_calendar = (evidence['mu'].get('receipt') or {}).get('calendar', {}).get('selected')
    chosen_mtp = (selected_calendar or {}).get('mtp') or {}
    current_link['selected_mu_model_identity_matches'] = bool(
        checks['exact_bound_model'] and chosen_mtp.get('sha256') == link.get('calendar_sha256')
        and (chosen_mtp.get('checker') or {}).get('position_graph_sha256') == link.get('graph_sha256'))
    # Component receipts remain scoped. A serial composition and independent
    # endpoint benches do not establish an end-to-end token delivery verdict.
    record = dict(schema='opentallas.tokfunc_s81.v1', source_ref=a.ref,
        grade='die-netlist' if a.grade == 'netlist' else 'RTL-functional (source assembly)',
        verdict='INCOMPLETE', full_token_pass=False,
        evidence=evidence, current_mu_link_qualification=current_link,
        current_entry_producer=dict(status='INCOMPLETE',
            norm_programme_status=(evidence['entry_norm'].get('receipt') or {}).get('status', 'PENDING'),
            aggregate_source_status=(evidence['aggregate_source'].get('receipt') or {}).get('status', 'PENDING'),
            producer_receipt_status=(evidence['entry_producer'].get('receipt') or {}).get('status', 'PENDING'),
            producer_qualification=('CONDITIONAL_EXACT_42_FILE_FIXTURE_ONLY'
                if len((evidence['entry_producer'].get('receipt') or {}).get('source_sha256', {})) == 42
                else 'CONDITIONAL_EXACT_RECEIPT_SOURCE_ONLY'),
            source_continuity='UNVERIFIED',
            shipping_equivalence=False,
            qualification='Recorded source programmes/components retain their own fixture, die, clocks and scope; recording them does not seal entry HOST, NX/XQ, END or a whole stage',
            full_stage=False, full_token=False),
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
    # Ladder: per-layer -> chained -> token (1 user) -> MU, each rung with real cycles and named blocking gaps.
    if a.ladder and Path(a.ladder).is_file():
        lad = json.loads(Path(a.ladder).read_text())
        er = evidence['entry_replay'].get('receipt')
        if er:
            jobs = er.get('jobs', [])
            lad['rungs']['entry']['native_host_replay'] = dict(
                verdict=er.get('verdict'), jobs=[(j['job'], j['verdict']) for j in jobs],
                mutants=[(m['mutant'], m['verdict']) for m in er.get('mutants', [])],
                line_faces={j['job']: {f: (v['verdict'], v['observed'], v['offsets']) for f, v in (j.get('line') or {}).items()}
                            for j in jobs},
                bench_cycles={j['job']: (j.get('bench') or {}).get('cycles') for j in jobs})
            if er.get('verdict') == 'PASS_CUT_COMPONENT':
                lad['gaps'].pop('G-HOSTCUT-BUILD', None)
                lad['rungs']['entry']['blocked_by'] = [g for g in lad['rungs']['entry']['blocked_by'] if g != 'G-HOSTCUT-BUILD']
        record['ladder'] = lad
        record['highest_rung_pass'] = next((r for r in ('multi_user_50AR', 'token_1user', 'chained', 'per_layer')
                                            if lad['rungs'].get(r, {}).get('status') == 'PASS'), None)
    if a.die_v:
        f = Path(a.die_v)
        record['die_v'] = dict(path=str(f), sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + '\n')
    print(f'{out}: INCOMPLETE (component receipts preserved, full-token PASS not established)')


if __name__ == '__main__':
    main()
