import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('binding', ROOT / 'tools/w17_D1_retained_attention_binding.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
E = ROOT / m.EVIDENCE


def test_portable_review():
    result = m.verify(ROOT)
    assert result['tile_instances'] == 64
    assert not result['runtime_admitted']
    assert not result['current_revision_equivalence']
    assert not result['original_process_linkage']


@pytest.mark.parametrize('data,expected', [
    (b'', '47DEQpj8HBSaABTImWA5JCeuQeRkm5NMpJWZG3hS'),
    (b'a', 'ypeBEsobvcr6wjGzmiPcTaeG7BgUfE5yuYB3haBu'),
    (b'The quick brown fox jumps over the lazy dog', '16j7swfXgJRpypq8sAguT41WUeRtPNt2LQLQvzfJ'),
])
def test_official_digest_selftest_vectors(data, expected):
    assert m.digest_symbol(data) == expected


SOURCES = json.loads((E / 'source_manifest.json').read_text())


@pytest.mark.parametrize('source', SOURCES, ids=lambda x: x['recorded_basename'])
def test_changed_historical_source_rejected(source):
    content = {x['path']: (E / x['path']).read_bytes() for x in SOURCES}
    content[source['path']] += b'\n'
    with pytest.raises(ValueError, match='digest/size mismatch'):
        m.validate_source_rows((E / 'metadata/Vattn__verFiles.dat').read_text(), SOURCES, content)


@pytest.mark.parametrize('child', m.CHILDREN)
def test_child_wrong_generation_rejected(child):
    text = (E / f'metadata/{child}/{child}__verFiles.dat').read_text()
    digest = SOURCES[1]['digest_symbol']
    text = text.replace(digest, 'A' * 40)
    content = {x['path']: (E / x['path']).read_bytes() for x in SOURCES}
    with pytest.raises(ValueError, match='digest/size mismatch'):
        m.validate_source_rows(text, SOURCES, content)


def test_current_top_cannot_match_old_record():
    old = SOURCES[1]
    assert old['bytes'] == 26317
    assert old['current_source_bytes'] == 51491
    assert old['sha256'] != old['current_source_sha256']
    assert not old['byte_equal_current']


@pytest.mark.parametrize('port,msb', [('q_w',8191), ('kv_w',16959), ('sc_y',2047),
                                   ('pv_y',32767), ('pv_f',1023), ('job_t',15),
                                   ('kv_m',3), ('p_w',511)])
def test_shrunk_public_abi_detected(port, msb):
    text = (E / 'metadata/Vattn.h').read_text()
    assert m.public_widths(text)[port] == msb + 1
    mutant = text.replace(f'(&{port},{msb},0', f'(&{port},{msb - 1},0')
    assert m.public_widths(mutant)[port] != msb + 1


def test_same_size_source_mutation_rejected():
    content = {x['path']: (E / x['path']).read_bytes() for x in SOURCES}
    path = SOURCES[1]['path']
    data = content[path]
    content[path] = bytes([data[0] ^ 1]) + data[1:]
    with pytest.raises(ValueError, match='digest/size mismatch'):
        m.validate_source_rows((E / 'metadata/Vattn__verFiles.dat').read_text(), SOURCES, content)


@pytest.mark.parametrize('missing', [0, 31, 63])
def test_shrunk_geometry_detected(missing):
    text = (E / 'metadata/Vattn___024root.h.tile_declarations.txt').read_text()
    text = '\n'.join(x for x in text.splitlines() if f'g_t__BRA__{missing}__KET__' not in x)
    assert m.tile_indices(text) != list(range(64))


def test_fake_same_edge_transfer_is_distinguishable():
    assert m.clock_sample(0, 1) == 0
    assert m.clock_sample(0, 1, propagate_before_rising=True) == 1


@pytest.mark.parametrize('driver', ['v41_die_rt.cpp', 'w17_current_fastpp_die_rt.cpp'])
def test_driver_clock_contract_and_early_transfer_mutant(driver):
    text = (E / 'runtime_source' / driver).read_text()
    m.validate_clock_contract(text)
    text = text.replace('if (i < 8) { dies[i - 4]->att_eval(1, rst); return; }',
                        'if (i < 8) { d->att_propagate(); dies[i - 4]->att_eval(1, rst); return; }')
    with pytest.raises(ValueError, match='Transfer before'):
        m.validate_clock_contract(text)


def test_archive_aliases_have_one_identity():
    items = json.loads((E / 'archive_inventory.json').read_text())
    assert len(set(x['sha256'] for x in items[:4])) == 1
    assert items[0]['bytes'] == 77986704


def test_absent_binary_and_service_authority_stays_explicit():
    r = json.loads((E / 'binding_record.json').read_text())
    assert r['compiler_metadata']['historical_compiler_binary_hash'] == 'UNAVAILABLE_VERFILES_UNHASHED'
    assert r['runtime_binding']['original_process_link_map'] == 'UNAVAILABLE'
    assert r['limits']['finite_causal_service_bound'] == 'BOUND_MISSING'
