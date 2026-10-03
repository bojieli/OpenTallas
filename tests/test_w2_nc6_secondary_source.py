"""Source-enrollment gates; these are not a controller runtime verdict."""
import hashlib
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import w2_nc6_secondary_source as s
import w2_nc6_count_utility_closure as m


def test_exact_disjoint_physical_ownership():
    secondary = set(s.mapping())
    primary = set(range(219)) - secondary
    assert len(secondary) == 37 and len(primary) == 182
    assert secondary | primary == set(range(219))
    assert not secondary & primary
    assert secondary == set(range(125,131)) | {132} | set(range(189,219))
    assert 72 * (len(primary) + len(secondary)) == 15768


def test_generated_source_exact():
    assert s.RTL.read_text() == s.source()


def test_original_codec_byte_identical():
    codec = ROOT / 'rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv'
    assert hashlib.sha256(codec.read_bytes()).hexdigest() == '7bcbb4f38bdf4d75c054dbc266a09344f4f0de4c115cbb05240ef6430d5f941a'


def test_full_controller_unavailable_is_explicit():
    p = s.plan()
    assert not p['full_NC6'] and not p['readiness']['runtime']
    assert not p['full_controller_enrollment']['primary_source_present']
    assert p['full_controller_enrollment']['full_controller_terminal'] is None
    assert 'CAP4+FIX4' in p['full_controller_enrollment']['build_blockers'][1]


@pytest.mark.parametrize('fragment', [
    'parameter integer OPT_PROTECTION=0',
    'input wire [17:0] reserve_roles,accept_intent',
    'provider_fenced,reverse_fenced,reset_fenced,local_other_idle',
    'commit_roles=accept_intent',
    'scrub_original[72*lane+:72]!=cw[wordno]',
    'scrub_repaired[72*lane+:72]!=corrected[wordno]',
    'if(scrub_v[lane]&&index>=219)semantic_bad=1',
    'if(semantic_bad||integrity_bad||logic_fault)',
    'assign inspect_original[72*w+:72]=cw[w]',
    'assign inspect_corrected[72*w+:72]=corrected[w]',
])
def test_source_enrolls_negative_guard(fragment):
    assert fragment in s.source()


def test_inspection_is_not_state_copy():
    x = s.source()
    assert x.count('always_ff') == 1
    assert 'logic [71:0] cw[0:NW-1]' in x
    assert 'output wire [2663:0] inspect_original,inspect_corrected' in x
    assert s.plan()['source_interfaces']['current_private_inspection_bits'] == 7067
    assert s.plan()['ports']['new_extra_storage_bits'] == 0


def test_count_pending_and_source_copies_are_typed():
    p = s.plan()['source_interfaces']
    assert 'count-changing' in p['table_pending_semantics']
    assert 'separately cover every table mutator' in p['table_pending_semantics']
    assert 'ONLY consumed offer snapshots' in p['positive_offer_drain']


def test_illegal_roles_do_not_silently_fold():
    x = m.Counts()
    x.accepted(0, alloc=1)
    with pytest.raises(m.Refusal, match='offer-budget'):
        x.accepted(0, alloc=1)
    assert x.fault


def test_role_fold_and_foreign_copy_debt_remain_distinct():
    x = m.Counts()
    # Independent clients may each retire a write; this is six physical ports.
    for client in range(6):
        m.write_record(x.memory, x.pc, 'outstanding_cache', client, 1)
        row = client * 16
        x.memory[row] = m.c.seal(m.r.Ledger.pack(m.r.ISSUED), x.pc, row, 0)
        x.accepted(client, write_retire=1)
    assert [x.pending(i) for i in range(6)] == [-1] * 6
    assert not any(x.admission_allowed(i) for i in range(6))
