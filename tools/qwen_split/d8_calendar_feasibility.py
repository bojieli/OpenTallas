#!/usr/bin/env python3
"""Fail-closed D8 calendar model. Never emits production binding or normalizes corner phase."""
import argparse
import hashlib
import json
import math
from pathlib import Path

FLOP = {1, 3, 10, 32, 107, 116}
SRAM = {453: [151, 151, 151], 520: [174, 173, 173], 548: [183, 183, 182]}

def geometry(width):
    if width in FLOP:
        return 'flop', [width], 1, 1, 3
    if width in SRAM:
        return 'sram', SRAM[width], 3, 2, 4
    raise ValueError('unsupported native D8 width')

def interval(phi, period, kind, setup_reserve=150., hold_reserve=100.):
    """Same named receiver edge at TT/FF. No per-corner modulo/phase wrapping."""
    if set(phi) != {'tt', 'ff'} or any(not math.isfinite(v) for v in phi.values()):
        raise ValueError('complete finite TT/FF phase required')
    offset = 1 if kind == 'flop' else 3
    lower = 1.25 * period + setup_reserve
    upper = 4.125 * period - hold_reserve
    lo = max(offset, max(math.ceil((lower-v)/period+offset) for v in phi.values()))
    hi = min(math.floor((upper-v)/period+offset) for v in phi.values())
    return lo, hi

def reset_candidate(L, G, R0, kind):
    # G/R0 are RAW external en/rs release edges, before the module's two-stage landings.
    subtract, warm_base = (1, 3) if kind == 'flop' else (2, 4)
    K = (L + G - R0 - subtract) % 16
    return dict(K=K, straps=[(K >> i) & 1 for i in range(4)],
                receiver_output_unblocked_edge=R0 + warm_base + (K or 16),
                source_first_write_edge=G+3,
                note='warm unblock is not valid-data first use; first-use/epoch bench receipt also required')

def analyze(lanes, phases, oldplan, contracts=None, setup=150., hold=100.):
    contracts = contracts or {}
    pd = {r['bid']: r for r in phases['lanes']}
    old = {r['bid']: r for r in oldplan['links']}
    rows = []; period = oldplan['T_ps']
    for lane in lanes['lanes']:
        if lane.get('lane') == 'reset': continue
        bid = lane['bid']; failures = []; row = dict(bid=bid, bits=lane['bits'])
        phase = pd.get(bid, {})
        if not all(k in phase for k in ['dck_tt', 'dck_ff']): failures.append('MISSING_TTFF_PHASE')
        measured = old.get(bid, {})
        if measured.get('E') is None or set(measured.get('s1', {})) != {'tt', 'ff'} or set(measured.get('h0', {})) != {'tt', 'ff'}:
            failures.append('MISSING_TTFF_DATA_SLACK')
        try:
            kind, slices, offset, sub, warm = geometry(lane['bits'])
            row.update(kind=kind, slices_low_to_high=slices, receiver_edges_vs_flop=offset-1)
        except ValueError:
            failures.append('UNSUPPORTED_NATIVE_WIDTH'); kind = None
        if kind and all(k in phase for k in ['dck_tt', 'dck_ff']):
            phi = dict(tt=phase['dck_tt'], ff=phase['dck_ff'])
            lo, hi = interval(phi, period, kind, setup, hold)
            row.update(phi_ps=phi, L_interval=[lo, hi])
            if lo > hi: failures.append('NO_RESERVED_COMMON_TTFF_L')
            else:
                row.update(candidate_L=lo, age_ps={c:(lo-offset)*period+v for c,v in phi.items()})
                # Schedule price must include every edge; do not subtract SRAM macro edges again.
                row['schedule_price_status'] = 'BLOCKED: actual source-to-input/output-to-consumer edge exports required'
                row['mandatory_sram_receiver_edges_vs_flop'] = offset-1
        c = contracts.get(bid)
        if not c: failures.append('MISSING_NATIVE_INSTANCE_RESET_CONTRACT')
        else:
            required = ['landing', 'source_commit', 'netlist_sha256', 'native_receipt_sha256',
                        'reset_trace_sha256', 'phase_receipt_sha256', 'G_raw', 'R0_raw',
                        'raw_release_verified', 'first_use_epoch_verified', 'all_roots_max_load',
                        'width', 'kind', 'straps', 'source_clock', 'receiver_clock',
                        'source_to_input_edges', 'output_to_consumer_edges', 'compiled_total_edges']
            missing = [k for k in required if k not in c]
            if missing: failures.append('INCOMPLETE_NATIVE_CONTRACT:'+','.join(missing))
            else:
                if c['landing'] != lane['landing'] or c['width'] != lane['bits'] or c['kind'] != kind:
                    failures.append('NATIVE_INSTANCE_IDENTITY_MISMATCH')
                if c['source_clock'] != lane.get('src_ck') or c['receiver_clock'] != lane.get('dst_ck'):
                    failures.append('NATIVE_CLOCK_IDENTITY_MISMATCH')
                for k in ['netlist_sha256','native_receipt_sha256','reset_trace_sha256','phase_receipt_sha256']:
                    if not isinstance(c[k],str) or len(c[k]) != 64 or any(x not in '0123456789abcdef' for x in c[k]):
                        failures.append('INVALID_DIGEST:'+k)
                if not c['raw_release_verified'] or not c['first_use_epoch_verified']: failures.append('RESET_EPOCH_UNPROVEN')
                if c['all_roots_max_load'] > 32: failures.append('NATIVE_FANOUT_OVER32')
                if not all(type(c[k]) is int for k in ['G_raw','R0_raw']): failures.append('NONINTEGER_RAW_RELEASE')
                if len(c['straps']) != 4 or any(x not in (0,1) for x in c['straps']): failures.append('INVALID_FOUR_STRAPS')
                if not failures and 'candidate_L' in row:
                    proposal = reset_candidate(row['candidate_L'],c['G_raw'],c['R0_raw'],kind)
                    if proposal['straps'] != c['straps']: failures.append('ACTUAL_K_STRAPS_MISMATCH')
                    row['reset_model'] = proposal
                    priced = c['source_to_input_edges'] + row['candidate_L'] + c['output_to_consumer_edges']
                    row['priced_total_edges'] = priced
                    row['schedule_price_status'] = 'EXPLICIT_MODEL_PRICE'
                    if c['compiled_total_edges'] != priced: failures.append('COMPILER_AGE_UNPRICED_OR_MISMATCH')
        # Legacy G_reset_tree includes HOP0_EN_REG already; never cast it to raw G.
        row['legacy_release_metadata'] = {k:lane[k] for k in ['G_reset_tree','R0_reset_tree','reset_calendar_root'] if k in lane}
        row['blockers'] = failures; rows.append(row)
    counts = {}
    for r in rows:
        for f in r['blockers']: counts[f] = counts.get(f,0)+1
    return dict(schema='opentallas.qwen.d8-calendar-feasibility.v1',qualified=False,
                status='BLOCKED' if counts else 'MODEL_INPUTS_COMPLETE_NOT_PHYSICAL_SIGNOFF',
                period_ps=period, setup_reserve_ps=setup, hold_reserve_ps=hold,
                age_window_T=[1.25,4.125], phase_rule='same named edges TT+FF; no modulo normalization',
                blockers=counts, lanes=rows)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ['lanes','phases','oldplan','out']:ap.add_argument('--'+k,type=Path,required=True)
    ap.add_argument('--contracts',type=Path);ap.add_argument('--setup-reserve',type=float,default=150.)
    ap.add_argument('--hold-reserve',type=float,default=100.); a=ap.parse_args()
    if a.setup_reserve<150 or a.hold_reserve<100:ap.error('reserve relaxation prohibited: minima150/100ps')
    files={k:getattr(a,k) for k in ['lanes','phases','oldplan','contracts'] if getattr(a,k)}
    out=analyze(*(json.loads(getattr(a,k).read_text()) for k in ['lanes','phases','oldplan']),
                contracts=json.loads(a.contracts.read_text()) if a.contracts else None,
                setup=a.setup_reserve,hold=a.hold_reserve)
    out['source_sha256']={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in files.items()}
    a.out.write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(dict(status=out['status'],blockers=out['blockers'])))
    return int(out['status']=='BLOCKED')
if __name__=='__main__':raise SystemExit(main())
