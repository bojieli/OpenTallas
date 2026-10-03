"""Adversarial interlock witnesses and independent stepped-register timing."""
import importlib.util
import sys
import json
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
SPEC = importlib.util.spec_from_file_location('interlock', Path(__file__).parents[1] / 'tools/dsrom_I66_source_interlock.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_wait2_su_not_qe_counterexample():
    # Only SU idle: wait2 succeeds while QE idle is false; mask4 must fail.
    assert M.waited(2, 2, 0)
    assert not M.waited(4, 2, 0)
    # Only QE idle cannot satisfy wait2.
    assert not M.waited(2, 4, 0)


def test_registered_go_excludes_nominally_idle_unit():
    assert not M.waited(2, 31, 2)
    assert M.waited(2, 31, 4)
    assert not M.waited(6, 31, 4)


@pytest.mark.parametrize('bad', [True, 2.0, -1, 32])
def test_mask_bad_types_ranges(bad):
    with pytest.raises(ValueError):
        M.waited(bad, 31, 0)


def test_retirement_interlock_is_not_spine_ready_alone():
    assert not M.rom_ready(5, 1)
    assert not M.adapter_wait_exit(5, 1, 1)
    assert not M.adapter_wait_exit(5, 0, 0)
    assert M.adapter_wait_exit(5, 0, 1)
    assert M.rom_ready(0, 1)
    assert not M.rom_ready(0, 0)


def test_no_source_finite_deadline_from_ready_or_busy():
    # Arbitrarily long finite prefixes of the source-legal held-ready state
    # contain no admission. This witness must not be converted to a timeout.
    for prefix in [1, 1024, 4096]:
        assert not any(M.rom_ready(0, 0) for _ in range(prefix))
    assert M.model()['source_dependencies']['next_issue_upper_bound'] is None


def test_original_ready_does_not_prove_remote_visibility():
    # A retired original adapter can admit the next command even though a
    # proposed remote publication has not occurred. This is the missing fence.
    previous_remote_publication_visible = False
    assert M.rom_ready(0, 1)
    assert not previous_remote_publication_visible
    assert not M.model()['hardware_admission']


def stepped_pipeline(bc, gather):
    """Independent old-state/new-state recurrence, all samples are preedge.

    Push one pulse through broadcast register, bc tree/leaf registers, F0,
    optionally G1/G2, and then M/X. No formula from production helper used.
    """
    regs = [False] * (1 + bc)
    f = g1 = g2 = mv = xv = False
    read_edges, tag_edges = [], []
    for edge in range(16):
        live = regs[-1]
        read = g2 if gather else f
        if read:
            read_edges.append(edge)
        if xv:
            tag_edges.append(edge)
        regs, f, g1, g2, mv, xv = (
            [edge == 0] + regs[:-1], live, f and gather, g1, read, mv)
    return read_edges, tag_edges


@pytest.mark.parametrize('bc', [0, 1, 2, 5])
@pytest.mark.parametrize('gather', [False, True])
def test_pipeline_matches_source_register_recurrence(bc, gather):
    reads, tags = stepped_pipeline(bc, gather)
    expected = M.accepted_emit_relation(0, bc, gather, live_lane=True, reset_free=True)
    assert reads == [expected['VM_read_preedge']]
    assert tags == [expected['X_tag_preedge']]
    assert expected['publication_latest_postNBA_edge'] == reads[0] - 1
    # Mutation controls: collapsing F0 or omitting G1/G2 changes observed edge.
    assert reads != [expected['VM_read_preedge'] - 1]
    if gather:
        assert reads != [bc + 2]


@pytest.mark.parametrize('kwargs', [dict(live_lane=False, reset_free=True),
                                    dict(live_lane=True, reset_free=False),
                                    dict(live_lane=1, reset_free=True)])
def test_reset_or_nonlive_lane_has_no_read_guarantee(kwargs):
    with pytest.raises(ValueError):
        M.accepted_emit_relation(10, 0, False, **kwargs)


def test_preserved_wrong_record_corrected_additively():
    old = json.loads((M.ROOT / M.SOURCE_PATHS['prior_record']).read_text())
    assert 'circularly block wait2' in old['lease_is_not_unit_busy']
    new = M.model()
    assert new['wait_masks']['SU'] == 2
    assert new['wait_masks']['QE_ROM'] == 4
    assert 'incorrect' in new['correction']
    assert new['actual_current_PHW10']['accepted_journal'] is None
    assert new['status'] == 'BOUND_MISSING'


def test_source_mutation_rejected_before_model(monkeypatch, tmp_path):
    # Full content pins, not keyword matches, are authoritative.
    out = tmp_path / 'out'
    out.mkdir()
    pins = json.loads((M.OUT / 'source_pins.json').read_text())
    for name, relative in M.SOURCE_PATHS.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((M.ROOT / relative).read_bytes())
    core = tmp_path / M.SOURCE_PATHS['core']
    core.write_text(core.read_text().replace('qe_idle, su_idle', 'su_idle, qe_idle'))
    (out / 'source_pins.json').write_text(json.dumps(pins))
    monkeypatch.setattr(M, 'ROOT', tmp_path)
    monkeypatch.setattr(M, 'OUT', out)
    with pytest.raises(ValueError, match='source identity changed: core'):
        M.model()


def test_single_context_held_until_su_consumer_blocks_program():
    # In-order core at I67 cannot reach I70 if prior lease release is required
    # for ROM ready. Unrelated SU idle does not break this ordering dependency.
    pc, previous_lease_retired = 67, False
    assert M.waited(2, 2, 0)
    for _ in range(100):
        next_rom_ready = M.rom_ready(0, 1) and previous_lease_retired
        if next_rom_ready:
            pc += 1
        if pc == 70:
            previous_lease_retired = True
    assert pc == 67
    contract = M.model()['one_candidate_required_contract']
    assert 'I66/I67/I68' in contract['ordered_program_lease_lower_bound']
    assert 'not a wait2/QE dependency' in contract['single_context_deadlock_control']
