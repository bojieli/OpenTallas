"""Join retained NF2 compare coverage with one newly proved state relation; never rewrites old verdicts."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def join(subject, replay, out):
    subject, replay, out = map(Path, (subject, replay, out))
    identity = json.loads((replay/'IDENTITY.json').read_text())
    mismatches = [p for p, h in identity['hashes'].items() if not Path(p).is_file() or sha(p) != h]
    if mismatches:
        raise ValueError(f'changed native source/graph/replay inputs: {mismatches}')
    old = json.loads((subject/'proof/normal/lec.json').read_text())
    new = json.loads((replay/'RESULT.json').read_text())
    context = json.loads((replay/'CONTEXT.json').read_text())
    prepared = json.loads((subject/'prepared.json').read_text())
    point = 'ff:u_dut.u_leaf.u_core.fault'
    assert old['counts'] == dict(compare_points=6370, proved=6369, differs=1, undecided=0)
    assert old['failing'] == []
    assert [p['point'] for p in old['unproven_points']] == [point]
    assert new['pending_point_statuses'] == {point: 'proved'}
    assert new['missing_prior'] == [] and new['original_profile_unchanged'] is True
    assert new['all_hypotheses_jointly_reproved'] is True
    assert new['original_hypotheses'] == 944 and new['final_hypotheses'] == 945 and new['constraints'] == 0
    assert old['reset_contract'] == new['reset_contract'] == context['reset_contract']
    assert old['reset_contract']['used'] == 16 and not old['reset_contract']['debug_overrides']
    assert new['prior_sha256'] == sha(subject/'proof/normal/hyp.json')
    assert new['base'][0]['covered'] and new['base'][0]['target'] == new['base'][0]['predicate'] == 0
    assert new['base'][0]['reset_cycles'] == 16
    assert sha(subject/'reference.v') == prepared['reference_netlist_sha256']
    assert sha(subject/'base/rtl/qkd_ahub_static_dw.sv') == prepared['baseline_sha256']
    bad_readset = [n for n,h in prepared['normal']['kit_readset'].items() if sha(subject/'normal/rtl'/n) != h]
    assert not bad_readset, bad_readset
    spec = importlib.util.spec_from_file_location('nf2', subject/'ahub_fault_groups.py')
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    assert sha(subject/'ahub_fault_groups.py') == prepared['helper_sha256']
    transformed = helper.factor_fault_capture((subject/'base/rtl/qkd_ahub_static_dw.sv').read_text(), 'qkd_ahub_static_core_la_ck7')
    assert hashlib.sha256(transformed.encode()).hexdigest() == prepared['normal']['source_sha256']
    assert transformed == (subject/'normal/rtl/qkd_ahub_static_dw.sv').read_text()
    result = dict(schema='opentallas.nf2.composite_source_qualification.v1',
        verdict='EQUIVALENT_COMPOSITE_6370_OF_6370', status='QUALIFIED_DISABLED_SOURCE_ONLY',
        normal_source_sha256=prepared['normal']['source_sha256'], baseline_source_sha256=prepared['baseline_sha256'],
        reference_netlist_sha256=prepared['reference_netlist_sha256'], helper_sha256=prepared['helper_sha256'],
        checked_identity_files=len(identity['hashes']), identity_mismatches=[], unchanged_normal_readset=len(prepared['normal']['kit_readset']),
        old_proved_coverage=6369, newly_proved_points=[point], combined_coverage=6370, constraints=0,
        old_hypotheses=944, joint_reproved_hypotheses=945, reset_contract=old['reset_contract'],
        coverage_argument='Same native graphs/readset/reset. All944 original hypotheses remain unchanged and are jointly reproved with the one new relation. The original6369 covered points remain valid under this true strengthened invariant; the sole omitted point is now proved. Coverage is disjoint and complete.',
        preserved_original=dict(path=str(subject/'proof/normal/lec.json'), sha256=sha(subject/'proof/normal/lec.json'), verdict=old['verdict'], counts=old['counts']),
        replay=str(replay), no_full_rerun=True, activation='OFF; no canonical source/recipe/plan changes',
        physical_status='NOT RUN; source proof gives no timing/clock/tree/model qualification',
        full_mutant_status='terminal' if (subject/'proof/mutant/lec.json').exists() else 'running; existing job preserved')
    out.mkdir(parents=True, exist_ok=False)
    (out/'COMPOSITE.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    a=argparse.ArgumentParser();a.add_argument('--subject',required=True);a.add_argument('--replay',required=True);a.add_argument('--out',required=True);v=a.parse_args()
    print(json.dumps(join(v.subject,v.replay,v.out),indent=2))
