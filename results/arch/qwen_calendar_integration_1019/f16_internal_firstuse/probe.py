#!/usr/bin/env python3
"""Three source-bound first-edge witnesses; neither RTL simulation nor signoff."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[4]
source = root / 'rtl/qwen_dv/qfd_dv_typed_witness_control.sv'
text = source.read_text()
digest = hashlib.sha256(source.read_bytes()).hexdigest()
assert digest == '8536070ddb594a5b6ae98c3f9ff2d78371cc50ec159ea72d7466142eccd97640'
anchors = [
    'scan=rr+2\'(k);',
    'pending_user<=pick_user;',
    'else begin templates[record_index]<=record_word;loaded[record_index]<=1;end',
    'for(u=0;u<4;u=u+1)if(active[u])begin',
    "if(cycle[u][0]!=8191)begin for(c=0;c<NC;c=c+1)cycle[u][c]<=cycle[u][c]+1'b1;end",
]
assert all(a in text for a in anchors)

# Source priority: ascending k, wrapping two-bit scan, first free bank.
# Both contexts active; empty caches, no pending request, next_group=0.
def pick(rr):
    for k in range(4):
        scan = (rr + k) & 3
        if scan in (0, 1):
            return scan
    raise AssertionError('no pick')

canonical_rr, clone_rr = 0, 1
original_pick, rerouted_pick = pick(canonical_rr), pick(clone_rr)
assert original_pick != rerouted_pick
# Even if canonical rr-D is protected, and both rr FFs capture that D,
# another FF can capture the clone-dependent pick at the same edge.
common_rr_d = (original_pick + 1) & 3
assert (common_rr_d, common_rr_d) == (1, 1)

# A record_index[2] copy is arbitrary before reset; common canonical D is
# protected. On the installation edge the clone-fed sector chooses slot 4,
# while the canonical validation/loaded check chooses slot 0.
canonical_record, clone_record = 0, 4
record_word = 0x40 | (1 << 22)  # group0, nonzero mask, reserved bits zero
assert (record_word >> 130) == canonical_record
assert (record_word >> 22) & 0xfff
assert ((record_word >> 20) & 3) == 0
original_templates = [0] * 13
rerouted_templates = [0] * 13
original_templates[canonical_record] = record_word
rerouted_templates[clone_record] = record_word
assert original_templates != rerouted_templates

# active[1] clone used by one increment sector. Other outputs and active-D
# remain canonical. Equality of active FFs after this edge cannot repair the
# different cycle value already captured at that edge.
canonical_active, clone_active, cycle = 0, 1, 9
original_cycle = cycle + 1 if canonical_active else cycle
rerouted_cycle = cycle + 1 if clone_active else cycle
assert original_cycle != rerouted_cycle

out = {
    'scope': 'Three finite source-bound counterexamples, not an RTL execution',
    'source_sha256': digest,
    'anchors': {a: text[:text.index(a)].count('\n') + 1 for a in anchors},
    'assumptions': {
        'ENABLE': 1, 'rst_n': 1,
        'qualified_reset_before_use': False,
        'canonical_feedback_and_D': 'protected in each witness',
        'copies_share_actual_clock_reset_and_SETN': 'required, not physically qualified',
    },
    'witnesses': {
        'rr_pick_consumer': {'canonical_rr': canonical_rr, 'clone_rr': clone_rr,
            'preedge_state': {'active': 3, 'cache_valid': 0, 'pending': 0,
                'next_group': [0, 0, 0, 0], 'cycle': 0,
                'sealed': 1, 'fault': 0, 'loading': 0},
            'inputs': {'pw_v': 0, 'start_v': 0, 'retire_v': 0,
                'observation': 0, 'all_copies_authenticated': 1,
                'fusedcap': 1, 'installed_digest': '198f7708b478a667',
                'installed_epoch': 7},
            'baseline_pending_user_next': original_pick,
            'clone_consumer_pending_user_next': rerouted_pick,
            'rr_pair_after_common_D_edge': [common_rr_d, common_rr_d]},
        'record_index_template_write': {'canonical_record_index': canonical_record,
            'clone_record_index': clone_record, 'baseline_written_slot': 0,
            'clone_consumer_written_slot': 4,
            'common_record_index_D': 1},
        'active_increment': {'canonical_active1': canonical_active,
            'clone_active1': clone_active, 'baseline_cycle_next': original_cycle,
            'clone_consumer_cycle_next': rerouted_cycle, 'common_active_D': 0},
    },
    'verdict': 'HOLD source choice: no proof that chosen clone consumers are invalid until convergence',
    'limits': 'These witnesses reject naive consumer partitions; they do not prove every protected partition impossible. They use arbitrary pre-reset state and do not claim reset-reachable failure.',
}
Path(__file__).with_name('witnesses.json').write_text(json.dumps(out, indent=2) + '\n')
print('Three first-edge consumer counterexamples preserved; source choice HOLD')
