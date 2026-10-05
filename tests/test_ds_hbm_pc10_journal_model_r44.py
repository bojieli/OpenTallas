import ast,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from ds_hbm_pc10_journal_model_r44 import model
from h4_hbm_w19_pc10_endpoints import inputs


def test_success_event_extras_are_covered_without_payload_restore():
    raw=inputs()['sector.py'];tree=ast.parse(raw)
    success={'request_accept','write_residence_reserved','software_owned_issue',
             'software_service_phases_reserved','software_backing_visible',
             'software_read_capture','consumer_accept','reverse_credit_accept','validated_reverse_grant'}
    record=model()['conservative_union_schema']
    found=set()
    for n in ast.walk(tree):
        if not isinstance(n,ast.Call) or not isinstance(n.func,ast.Attribute) or n.func.attr!='log':continue
        event=n.args[0].value
        if event not in success:continue
        found.add(event)
        assert len(event)<=len(record['event'])
        assert all(k.arg in record for k in n.keywords)
        assert all(k.arg not in ('payload','returned','data') for k in n.keywords)
    assert found==success


def test_journal_reservation_and_refusal_to_call_it_full_projection():
    r=model()
    assert r['shared_only_journal_reservation_bytes']==97114914816
    assert r['accepted_requests_for_schema_derivation']==0
    assert len(json.dumps(r['conservative_union_schema'],sort_keys=True,separators=(',',':')).encode())==790
    assert not r['full_projection_complete'] and len(r['missing'])==3
