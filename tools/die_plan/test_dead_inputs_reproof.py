"""S81-B3-CLK 11-14: dead-input proof accepted under a changed define list only with a matching re-proof."""
import json
import pytest
import dead_inputs as DI


def _proof(defines, params):
    return dict(schema='opentallas.dead_inputs.v1', verdict='PASS', defines=defines,
                dependency_modules=[dict(module='m', source='a.sv', module_sha256='x')],
                declarations=[dict(partition_type='t', module='m', parameters=params, ports={'p': [[0, 1]]},
                                   source='a.sv', module_sha256='y', method='yosys.proc.opt.no_fanout', remaining_loads=0)])


def test_reproof_matches(tmp_path):
    old = _proof(['A'], {'W': '4', 'H': '16'})
    new = _proof(['A', 'B'], {'W': '4'})
    (tmp_path / 'rp.json').write_text(json.dumps(new))
    man = dict(defines=['A', 'B'])
    assert DI._reproof_matches(old, tmp_path, 'rp.json', man)
    assert not DI._reproof_matches(old, tmp_path, 'rp.json', dict(defines=['A', 'C']))   # re-proof under other defines
    bad = _proof(['A', 'B'], {'W': '8'})
    (tmp_path / 'bad.json').write_text(json.dumps(bad))
    assert not DI._reproof_matches(old, tmp_path, 'bad.json', man)                    # parameter differs
    extra = _proof(['A', 'B'], {'W': '4', 'Z': '1'})
    (tmp_path / 'extra.json').write_text(json.dumps(extra))
    assert not DI._reproof_matches(old, tmp_path, 'extra.json', man)                  # key the proof lacks
    deps = _proof(['A', 'B'], {'W': '4'}); deps['dependency_modules'][0]['module_sha256'] = 'z'
    (tmp_path / 'deps.json').write_text(json.dumps(deps))
    assert not DI._reproof_matches(old, tmp_path, 'deps.json', man)                   # dependency differs
    fail = dict(new, verdict='FAIL')
    (tmp_path / 'fail.json').write_text(json.dumps(fail))
    assert not DI._reproof_matches(old, tmp_path, 'fail.json', man)
    with pytest.raises(ValueError):
        DI._reproof_matches(old, tmp_path, '/abs.json', man)


def test_define_change_without_reproof_still_fails(tmp_path):
    (tmp_path / 'p.json').write_text(json.dumps(_proof(['A'], {})))
    with pytest.raises(ValueError, match='stale dead-input preprocessor defines'):
        DI.ProvenDead(dict(defines=['A', 'B'], dead_input_proofs=['p.json']), tmp_path, {})
