#!/usr/bin/env python3
"""Export historical source releases; never infer provider deadlines or overlap."""
import argparse
import hashlib
import json
from pathlib import Path


def export(replay):
    if replay['status'] != 'PASS_HISTORICAL_DISPATCH_PRODUCER_SNAPSHOT_CONSISTENCY':
        raise ValueError('historical replay required')
    expected = {f'L{l}/die{r}' for l in range(36) for r in range(4)}
    if set(replay['states']) != expected:
        raise ValueError('all144 source identities required')
    releases = {}
    for key, state in replay['states'].items():
        life = state['source_lifetimes']
        writes = life['committed_writes']
        if len(writes) != 512 or len({w['address'] for w in writes}) != 512:
            raise ValueError('512 unique actual writes required')
        completions = life['producer_completions']
        for p in completions:
            actual = [w for w in writes if w['pc'] == p['pc']]
            if not actual or len(actual) != p['write_count'] or any(
                w['ticket'] != p['ticket'] or w['edge'] < p['accepted_edge'] for w in actual
            ) or (min(w['edge'] for w in actual), max(w['edge'] for w in actual)) != (
                p['first_write_edge'], p['last_write_edge']
            ):
                raise ValueError('producer completion differs from actual writes')
        if sum(p['write_count'] for p in completions) != 512 or len({p['pc'] for p in completions}) != len(completions):
            raise ValueError('producer completion partition')
        releases[key] = {
            'source_lifetimes': life,
            'deadline_scope': 'actual source KV host read edge when supplied; accepted ME edge otherwise; no future provider deadline',
            'actual_source_read_deadlines_complete': life.get('source_read_deadlines_complete',False),
            'provider_owner_generation': None,
            'attention_effective_lane_mask_qualified': False,
            'next_layer_prefetch_release': None,
            'published_prefix_masked_macro_visible': None,
            'window_reader_drain_reverse_grant_retire': None,
        }
    return {
        'status': 'SOURCE_RELEASE_EXPORT_ONLY_PROVIDER_JOIN_UNQUALIFIED',
        'source_provenance_independently_qualified': replay['source_provenance_independently_qualified'],
        'identity_scope': replay['identity_scope'],
        'historical_position': 0,
        'source_edge_unit': 'original simulator edges; no service-clock conversion',
        'current_8192_context_state_supplied': False,
        'calendar_overlap_credit_s': None,
        'provider_calendar_adoption': False,
        'releases': releases,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--replay', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    raw = args.replay.read_bytes()
    result = export(json.loads(raw))
    result['replay_sha256'] = hashlib.sha256(raw).hexdigest()
    with args.out.open('x') as f:
        json.dump(result, f, sort_keys=True, indent=2)
        f.write('\n')


if __name__ == '__main__':
    main()
