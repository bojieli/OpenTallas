"""Source CFG/decoder/descriptor integration; no numerical or HDL qualification."""
import copy
import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_stage_program_join as J
import hdc_isa_v41 as ISA


def stage_map():
    return dict(PHW_required_by_stage=[1]*81,
                region_bounds=[r*2417//128 for r in range(129)],
                BF_site_IDs=[i*2417//519 for i in range(519)],
                rank_dies=[dict(stage=s, rank=r, die_id=4*s+r)
                           for s in range(81) for r in range(4)])


def matrices():
    return [dict(stage=0, layer=0, alias=f'wq_b.rows{off}', original_alias='wq_b',
                 row_offset=off, rows=128, K=512, format='fp8', conversion='native',
                 tensor='layers.0.attn.wq_b.weight', compiled_NP=2417,
                 physical_owner_ranks=[0, 1, 2, 3],
                 rank_slices=[dict(rows=[r*256+off, r*256+off+128], cols=[0, 512]) for r in range(4)],
                 segments=[[0, 512]], plans=[[0, r*2417//128, r, 1, 128, i*16, 16] for r in range(64)])
            for i, off in enumerate((0, 128))]


def join(ms=None):
    return J.StageProgramJoin(matrices() if ms is None else ms, stage_map(),
                              pairs=2417, BF_pairs=519, stage_count=81)


def instruction():
    return dict(unit=3, pred=1, wait=2, qe_mode=0, qe_fp4=0, qe_xbase=400,
                qe_nb=16, qe_nout=256, qe_tiles=2, qe_wbase=0, qe_obase=1000,
                qe_unrounded=0)


def resolved(ms=None):
    ms = matrices() if ms is None else ms
    return dict(node='L0.I8', source_identity_verified=True,
                fragments=[dict(matrix=m, die_id=4*m['stage'],
                                gather_local_rows=[m['row_offset'], m['row_offset']+m['rows']],
                                ordered_K=m['segments'], result_multicast_required=False)
                           for m in ms])


def encode(f):
    return ISA.encode(full_shape=True, **f)


def test_two_colliding_original_keys_resolve_to_actual_distinct_decoder_phases():
    j = join(); keys = j.keys(0, 0)
    assert keys == [0x80020000, 0x80020001]
    assert [j.lookup(0, k & ((1 << 30)-1), ME=False) for k in keys] == [0, 1]
    with pytest.raises(ValueError, match='decoder phase'):
        j.lookup(0, keys[0] & ((1 << 30)-1), ME=True)
    with pytest.raises(ValueError, match='decoder phase'):
        j.lookup(0, 0, ME=False)


def test_source_cfg25_words_exact_existing_compiler_and_odd_row_convention():
    C = importlib.import_module('dsrom_full_owner_compiler')
    ms = matrices(); j = join(ms)
    for phase, m in enumerate(ms):
        assert [j.cfg(0, 0, 0, 25*phase+w) for w in range(25)] == C.phase_cfg(m, 0)
        assert [j.cfg(0, 0, 1, 25*phase+w) for w in range(25)] == [0]*25
    m = dict(ms[0], rows=1, row_offset=0, alias='wq_b', original_alias='wq_b', plans=[ms[0]['plans'][0]])
    assert join([m]).cfg(0, 0, 0, 17) == 0x8000


@pytest.mark.parametrize('args', [(0, 0, 0, 50), (0, 0, 0, -1), (0, 0, 2417, 0),
                                  (81, 0, 0, 0), (0, 4, 0, 0), (1, 0, 0, 0)])
def test_missing_or_bad_cfg_never_zero_fallback(args):
    with pytest.raises(ValueError):
        join().cfg(*args)


def test_real_encoded_fragment_commands_preserve_round_predicate_wait_input_and_k():
    f = instruction(); result = join().dispatch(resolved(), f, encode=encode)
    original = ISA.decode(encode(f), full_shape=True)
    assert result['predicate'] == 1
    for i, r in enumerate(result['fragments']):
        actual = ISA.decode(r['word'], full_shape=True)
        assert actual['qe_wbase'] == 0x20000+i
        assert actual['qe_obase'] == 1000+i*128
        assert actual['qe_nout'] == 128 and actual['qe_tiles'] == 1
        allowed = set(r['changed_fields'])
        assert all(actual[k] == original[k] for k in actual if k not in allowed)
        assert r['ordered_K'] == [[0, 512]]
        assert r['phase'] == i and r['cfg_logical_range'] == [i*25, (i+1)*25]
    assert f == instruction()


def test_production_join_checks_literal_template_before_using_source_execution():
    f = instruction(); n = dict(id='L0.I8', instruction=f,
                 template_word_sha256=hashlib.sha256(encode(f).to_bytes(256, 'little')).hexdigest())
    b = dict(source_node_semantic_sha256=J.digest(n), template_word_sha256=n['template_word_sha256'])
    calls = []
    def resolve(node, rank, *, expert_ids):
        calls.append((node, rank, expert_ids)); return resolved()
    source = SimpleNamespace(nodes={n['id']: n}, bindings={n['id']: b}, resolve=resolve)
    result = join().compile_operation(source, 'L0.I8', 0)
    assert len(result['fragments']) == 2 and calls == [('L0.I8', 0, None)]
    n['instruction']['pred'] = 3
    with pytest.raises(ValueError, match='literal source'):
        join().compile_operation(source, 'L0.I8', 0)
    assert len(calls) == 1


@pytest.mark.parametrize('mutation', ['matrix', 'gather', 'K', 'owner', 'missing', 'nonfield'])
def test_dispatch_refuses_unbound_or_changed_actual_source(mutation):
    r = resolved(); f = instruction()
    if mutation == 'matrix': r['fragments'][0]['matrix']['plans'][0][5] = 2
    if mutation == 'gather': r['fragments'][1]['gather_local_rows'][0] += 1
    if mutation == 'K': f['qe_nb'] += 1
    if mutation == 'owner': r['fragments'][0]['die_id'] = 4
    if mutation == 'missing': r['fragments'].pop()
    if mutation == 'nonfield': f['unit'] = 2
    with pytest.raises(ValueError): join().dispatch(r, f, encode=encode)


def test_me_output_word16_address_and_native_admission_not_repaired():
    ms = matrices()
    for i, m in enumerate(ms):
        m.update(format='bf16', K=128, segments=[[0, 128]],
                 alias=f'gate.rows{i*128}', original_alias='gate', plans=[[*r[:6], 8] for r in m['plans']])
    j = join(ms)
    f = dict(unit=1, pred=3, wait=0, me_wsrc=0, me_wbase=0, me_nout=256,
             me_tiles=1, me_k=128, me_obase=100, me_xks=1, me_xcs=128,
             me_xjs=0, me_ots=8, me_ojs=1, me_round=1, me_oen=1)
    r = j.dispatch(resolved(ms), f, encode=encode)
    assert [ISA.decode(x['word'], full_shape=True)['me_obase'] for x in r['fragments']] == [100, 108]
    assert [j.lookup(x['stage'], x['key'], ME=True) for x in r['fragments']] == [0, 1]
    f['me_xks'] = 2
    with pytest.raises(ValueError, match='native ME admission'): j.dispatch(resolved(ms), f, encode=encode)


def test_multicast_consumer_has_no_valid_field_key_and_cfg_read_refuses():
    ms = matrices(); ms[0]['physical_owner_ranks'] = [0]
    j = join(ms)
    assert j.keys(0, 1)[0] == 0 and j.keys(0, 0)[0] != 0
    with pytest.raises(ValueError, match='not field owner'): j.cfg(0, 1, 0, 0)


def test_source_host_initializer_complete_pairs_and_exact_phase_order(tmp_path):
    j = join(); out = tmp_path/'stage0'
    receipt = j.emit_stage(0, 0, out)
    assert receipt['pairs'] == 2417 and receipt['cfg_words_per_pair'] == 50
    assert len(list(out.glob('e*.cfg.hex'))) == 2417
    assert (out/'spine_keys.hex').read_text().splitlines() == ['80020000', '80020001']
    assert [int(x, 16) for x in (out/'e0.cfg.hex').read_text().splitlines()] == [j.cfg(0, 0, 0, a) for a in range(50)]
    assert set((out/'e2416.cfg.hex').read_text().splitlines()) == {'000000000000'}
    with pytest.raises(FileExistsError): j.emit_stage(0, 0, out)


def test_source_collision_gap_and_old_s82_refused():
    ms = matrices(); ms[1]['row_offset'] += 2
    with pytest.raises(ValueError, match='row gap'): join(ms)
    with pytest.raises(ValueError, match='S81'):
        J.StageProgramJoin(matrices(), stage_map(), pairs=2388, BF_pairs=512, stage_count=82)


def test_native_c8_prog_hex_entry_join_uses_real_isa_and_waitall_end(tmp_path):
    j = join(); dispatch = j.dispatch(resolved(), instruction(), encode=encode)
    output = j.emit_programs([dispatch], tmp_path/'program', program_address_bits=14)
    assert [r['entry'] for r in output['entries']] == [0, 2]
    raw = (tmp_path/'program/s0_r0/prog.hex').read_bytes()
    assert output['artifacts']['s0_r0/prog.hex'] == hashlib.sha256(raw).hexdigest()
    words = [int(x, 16) for x in raw.splitlines()]
    assert words[::2] == [f['word'] for f in dispatch['fragments']]
    for word in words[1::2]:
        fields = ISA.decode(word, full_shape=True)
        assert fields['unit'] == ISA.UNIT_END and fields['wait'] == 31
    for entry, fragment in zip(output['entries'], dispatch['fragments']):
        decoded = ISA.decode(words[entry['entry']], full_shape=True)
        assert j.lookup(entry['stage'], decoded['qe_wbase'], ME=False) == entry['phase']
        assert entry['gather_local_rows'] == fragment['gather_local_rows']


def test_program_capacity_and_mutated_descriptor_refuse_before_output(tmp_path):
    j = join(); d = j.dispatch(resolved(), instruction(), encode=encode)
    with pytest.raises(ValueError, match='capacity exhausted'):
        j.emit_programs([d], tmp_path/'too_small', program_address_bits=1)
    assert not (tmp_path/'too_small').exists()
    d['fragments'][0]['instruction']['pred'] = 2
    with pytest.raises(ValueError, match='dispatch word changed'):
        j.emit_programs([d], tmp_path/'changed', program_address_bits=14)
    assert not (tmp_path/'changed').exists()


@pytest.mark.parametrize('mutation', ['plan_missing', 'wrong_root', 'codec', 'K_gap'])
def test_cfg_refuses_false_allocated_plan_instead_of_silent_zero(mutation):
    ms = matrices()
    if mutation == 'plan_missing': ms[0]['plans'].pop()
    if mutation == 'wrong_root': ms[0]['plans'][0][1] = 2417//128
    if mutation == 'codec': ms[0]['plans'][0][-1] += 2
    if mutation == 'K_gap': ms[0]['segments'][0][0] = 256
    with pytest.raises(ValueError): join(ms)
