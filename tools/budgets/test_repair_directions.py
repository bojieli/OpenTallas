"""Source port/bundle evidence, old missing-default-glue regression, fail-closed mutants."""
import gzip
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('repair_directions', Path(__file__).with_name('repair_directions.py'))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def case(tmp_path):
    src = tmp_path / 'immutable_source'
    src.mkdir()
    # An absent default results/.../dsfd_glue.sv is intentionally never consulted.
    glue = tmp_path / 'actual_case_glue.sv'
    glue.write_text('module tile(input [W-1:0] i, output o); parameter W=2; assign o=i[0]; endmodule\n')
    die = tmp_path / 'die.v'
    die.write_text('module die(); wire [2:0] n_bus; tile u(.i(n_bus[1:0]), .o(n_bus[2])); endmodule\n')
    manifest = src / 'layer1.f'
    manifest.write_text('+define+ONE+TWO\n')
    params = tmp_path / 'die.v.params.json'
    params.write_text(json.dumps({'masters': {'tile': {'W': 2}}}))
    model = dict(insts=[['u', 'tile', 'kind', 'region', 'domain', 1, 2, 3, 4, 'MY']],
                 buses=[['bus', 'bundle', 3, [['u', 'bundle', '?']]]], ports={'tile': {'bundle': [1, 2]}},
                 real_masters=[], endpoint_dir_failures=1, outline_um=[10, 20])
    inp = tmp_path / 'original.json.gz'
    with gzip.open(inp, 'wt') as f:
        json.dump(model, f)
    out = tmp_path / 'repaired.json.gz'
    expected = tmp_path / 'source_hashes.json'
    expected.write_text(json.dumps({'source_commit': 'immutable-case-id', 'files': {'layer1.f': R.digest(manifest)}}))
    args = ['--source-hashes', str(expected), '--model-in', str(inp), '--src', str(src), '--source-commit', 'immutable-case-id',
            '--die-v', str(die), '--glue', str(glue), '--manifest', str(manifest),
            '--params', str(params), '--out', str(out)]
    return args, model, glue, die, inp, out


def test_actual_glue_parameterized_mixed_directions_and_geometry(tmp_path):
    args, original, glue, die, inp, out = case(tmp_path)
    before = inp.read_bytes()
    assert R.main(args) == 1  # exact mixed bits cannot qualify a scalar direction
    with gzip.open(out, 'rt') as f:
        fixed = json.load(f)
    assert inp.read_bytes() == before
    assert R.invariants(original) == R.invariants(fixed)
    assert fixed['real_masters'] == []
    assert fixed['buses'][0][3][0][2] == 'mixed'
    assert fixed['endpoint_dir_segments'] == {'0:0': [[0, 2, 'in'], [2, 3, 'out']]}
    assert fixed['direction_repair']['defines'] == {'ONE': '', 'TWO': ''}
    assert fixed['direction_repair']['artifact_sha256'][str(glue)] == R.digest(glue)


@pytest.mark.parametrize('mutation', ['port', 'width', 'missing_instance', 'missing_bit'])
def test_source_or_connection_mutant_fails_closed(tmp_path, mutation):
    args, model, glue, die, inp, out = case(tmp_path)
    if mutation == 'port':
        glue.write_text(glue.read_text().replace('output o', 'output renamed'))
    elif mutation == 'width':
        glue.write_text(glue.read_text().replace('[W-1:0]', '[W:0]'))
    elif mutation == 'missing_instance':
        die.write_text(die.read_text().replace('tile u(', 'tile other('))
    else:
        die.write_text(die.read_text().replace('.i(n_bus[1:0])', '.i({1\'b0,n_bus[0]})'))
    assert R.main(args) == 1
    fixed = json.load(gzip.open(out, 'rt'))
    assert fixed['endpoint_dir_failures'] == 1
    assert fixed['buses'][0][3][0][2] == '?'
    assert fixed['direction_repair']['status'] == 'INCOMPLETE'


def test_missing_case_glue_does_not_use_default_or_publish(tmp_path):
    args, model, glue, die, inp, out = case(tmp_path)
    glue.unlink()
    with pytest.raises(FileNotFoundError):
        R.main(args)
    assert not out.exists()


def test_source_direction_mutant_changes_evidence_and_direction(tmp_path):
    args, model, glue, die, inp, out = case(tmp_path)
    assert R.main(args) == 1
    baseline = json.load(gzip.open(out, 'rt'))
    glue.write_text(glue.read_text().replace('output o', 'input o'))
    assert R.main(args) == 0
    mutant = json.load(gzip.open(out, 'rt'))
    assert mutant['buses'][0][3][0][2] == 'in'
    assert mutant['direction_repair']['artifact_sha256'] != baseline['direction_repair']['artifact_sha256']


def test_overlapping_bits_are_not_misreported_as_complete():
    with pytest.raises(ValueError, match='gap/overlap'):
        R.collapse([(0, 2, 'in'), (1, 3, 'out')], 3)


def test_committed_source_mutant_rejected_before_publication(tmp_path):
    args, model, glue, die, inp, out = case(tmp_path)
    manifest = Path(args[args.index('--manifest') + 1])
    manifest.write_text(manifest.read_text() + '// post-snapshot change\n')
    with pytest.raises(ValueError, match='immutable Git-blob manifest'):
        R.main(args)
    assert not out.exists()


def test_repeated_abstract_endpoints_share_exact_source_net_evidence(tmp_path):
    args, model, glue, die, inp, out = case(tmp_path)
    model['buses'][0][3].append(['u', 'bundle_alias[0:2]', '?'])
    with gzip.open(inp, 'wt') as f:
        json.dump(model, f)
    assert R.main(args) == 1
    fixed = json.load(gzip.open(out, 'rt'))
    assert [e[2] for e in fixed['buses'][0][3]] == ['mixed', 'mixed']
    assert fixed['direction_repair']['counts']['mixed'] == 2


def test_top_input_uses_actual_unprefixed_net(tmp_path):
    args, model, glue, die, inp, out = case(tmp_path)
    die.write_text(die.read_text().replace('module die();', 'module die(pad); input pad;'))
    model['buses'].append(['pad', 'top', 1, [['TOP', 'pad', '?']]])
    with gzip.open(inp, 'wt') as f:
        json.dump(model, f)
    assert R.main(args) == 1  # the separate tile bundle is still mixed
    fixed = json.load(gzip.open(out, 'rt'))
    assert fixed['buses'][1][3][0][2] == 'out'


def test_one_instance_reads_and_drives_same_net_at_distinct_ports(tmp_path):
    args, model, glue, die, inp, out = case(tmp_path)
    glue.write_text('module tile(input i, output o); assign o=i; endmodule\n')
    die.write_text('module die(); wire n_bus; tile u(.i(n_bus), .o(n_bus)); endmodule\n')
    model['buses'] = [['bus', 'clock_loop', 1, [['u', 'o', '?'], ['u', 'i', '?']]]]
    with gzip.open(inp, 'wt') as f:
        json.dump(model, f)
    assert R.main(args) == 0
    fixed = json.load(gzip.open(out, 'rt'))
    assert [e[2] for e in fixed['buses'][0][3]] == ['out', 'in']


def test_explicit_partial_load_is_not_an_unexplained_coverage_gap(tmp_path):
    args, model, glue, die, inp, out = case(tmp_path)
    model['buses'][0][3] = [['u', 'i[0:1]@0', '?']]
    with gzip.open(inp, 'wt') as f:
        json.dump(model, f)
    assert R.main(args) == 0
    fixed = json.load(gzip.open(out, 'rt'))
    assert fixed['buses'][0][3][0][2] == 'in'
    assert fixed['endpoint_dir_segments'] == {'0:0': [[0, 2, 'in']]}
    assert fixed['direction_repair']['counts']['partial'] == 1
    # A changed model-to-source offset must not pass against the same netlist.
    model['buses'][0][3][0][1] = 'i[0:1]@1'
    with gzip.open(inp, 'wt') as f:
        json.dump(model, f)
    assert R.main(args) == 1
