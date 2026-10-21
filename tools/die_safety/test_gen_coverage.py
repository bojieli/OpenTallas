import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from die_safety import gen_check


def full_facts():
    return dict(regions={'a': {'root': 'ca'}, 'b': {'root': 'cb'}},
                crossings=[dict(id='link', src_region='a', dst_region='b', landing='land')],
                wires=[dict(id='wire', pts=[[0, 0], [300, 0]])], channels=[[0, -10, 300, 10]])


def test_hbm_reach_only_pass_is_explicitly_scoped():
    report=gen_check.check_facts(dict(summaries=[gen_check.from_hbm_reach(
        dict(buses_checked=123, over_buses_by_class={}))]))
    assert report['verdict']=='PASS'
    assert report['verdict_scope']=='SCOPED_CHECK_ONLY'
    assert report['check_coverage']==dict(C1='NOT_EXPORTED',C2='NOT_EXPORTED',W1='CHECKED',W2='NOT_EXPORTED')
    assert report['physical_qualification_eligible'] is False
    assert 'scope=SCOPED_CHECK_ONLY' in gen_check.status_line(report)


def test_full_gen_facts_have_all_four_checks():
    report=gen_check.check_facts(full_facts())
    assert report['verdict']=='PASS' and report['coverage_complete']
    assert report['physical_qualification_eligible']
    assert 'native/clock/route/IR signoff remain required' in report['qualification']


def test_missing_channel_export_never_claims_w2_or_full_qualification():
    f=full_facts();del f['channels']
    report=gen_check.check_facts(f)
    assert report['verdict']=='PASS' and report['check_coverage']['W2']=='NOT_EXPORTED'
    assert not report['physical_qualification_eligible']


def test_known_failure_is_never_eligible_even_with_full_coverage():
    f=full_facts();f['crossings'][0]['landing']=None
    report=gen_check.check_facts(f)
    assert report['coverage_complete'] and report['verdict']=='FAIL'
    assert not report['physical_qualification_eligible']


def test_packet_preserves_scoped_coverage(tmp_path):
    report=gen_check.check_facts(dict(summaries=[dict(source='reach_only',wires=10)]))
    packet=tmp_path/'packet.json';gen_check.merge_packet(packet,report)
    saved=json.loads(packet.read_text())['gen_safety']
    assert saved['check_coverage']==report['check_coverage']
    assert saved['verdict_scope']=='SCOPED_CHECK_ONLY' and not saved['physical_qualification_eligible']


def test_diagnostic_full_facts_remain_ineligible(tmp_path):
    path=tmp_path/'facts.json';path.write_text(json.dumps(full_facts()))
    report=gen_check.run(facts=path,diagnostic='planning experiment')
    assert report['coverage_complete'] and report['verdict']=='PASS'
    assert not report['physical_qualification_eligible']
