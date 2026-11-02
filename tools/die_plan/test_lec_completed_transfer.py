import json
import shutil
import time
from pathlib import Path
import pytest
from lec_completed_transfer import transfer


def fixture(tmp_path):
    k=tmp_path/'original'; k.mkdir(); (k/'rtl').mkdir(); (k/'lec').mkdir()
    rows={'config.mk':'export VERILOG_FILES = /work/rtl/top.v\n', 'freeze.json':json.dumps({'schema':'frozen.v1','source_commit':'a'*40}),
          'lec.py':'# retained original proof driver\n','rtl/top.v':'module top;endmodule\n',
          'lec_async.ready':'1\npython3 /work/lec.py --netlist /work/net.v\n','net.v':'module top;endmodule\n'}
    for n,text in rows.items(): (k/n).write_text(text)
    time.sleep(.005)
    (k/'lec/lec.json').write_text(json.dumps({'verdict':'EQUIVALENT','netlist':'/work/net.v','counts':{'proved':87187},'provenance':{'commit':None,'source':'historically invalid'}}))
    (k/'lec_async.rc').write_text('0\n');(k/'image.txt').write_text('end 2026-11-01T13:42:54 rc 0\n')
    c=tmp_path/'copy';shutil.copytree(k,c);return k,c


def test_honest_current_byte_transfer_preserves_historical_limitation(tmp_path):
    k,c=fixture(tmp_path); before=(c/'lec/lec.json').read_bytes();r=transfer(k,c)
    assert not r['historical_identity_available'] and not r['source_qualified']
    assert r['historical_provenance']['commit'] is None
    assert (c/'lec/lec.json').read_bytes()==before
    assert r['current_files_sha256']['net.v']
    assert transfer(k,c)==r


def test_changed_copy_and_non_eq_are_rejected(tmp_path):
    k,c=fixture(tmp_path);(c/'net.v').write_text('mutant')
    with pytest.raises(ValueError,match='differs'):transfer(k,c)
    (k/'lec_async.rc').write_text('1')
    with pytest.raises(ValueError,match='not completed'):transfer(k,c)


def test_original_input_newer_than_proof_is_rejected(tmp_path):
    k,c=fixture(tmp_path);time.sleep(.005);(k/'rtl/top.v').write_text('changed');shutil.copy2(k/'rtl/top.v',c/'rtl/top.v')
    with pytest.raises(ValueError,match='newer'):transfer(k,c)


def finished_fixture(tmp_path):
    k,c=fixture(tmp_path)
    for root in (k,c):
        (root/'lec_async.ready').write_text('1\npython3 -I /work/lec.py /work --netlist /work/net.v --out /work/lec > /work/lec_run.log 2>&1\n')
        (root/'PROVENANCE.json').write_text(json.dumps({'provenance':{'commit':'a'*40,'dirty':False},'files':{}}))
        (root/'image.txt').unlink()
    (k/'lec_async.done').touch()
    time.sleep(.005)
    (k/'lec/lec.json').write_text(json.dumps({'verdict':'EQUIVALENT','netlist':'/work/net.v',
        'counts':{'compare_points':123,'proved':123,'differs':0,'undecided':0},
        'provenance':{'commit':'a'*40,'dirty':False,'source':'validated kit PROVENANCE.json'},
        'kept_registers':{'missing':{'n':0}},'reset_contract':{'default':4,'used':4,'requested':None,'contract':None,'debug_overrides':{}}}))
    return k,c


def test_finished_proof_can_transfer_when_physical_scope_failed(tmp_path):
    k,c=finished_fixture(tmp_path)
    old=(c/'lec/lec.json').read_bytes();r=transfer(k,c,finished_proof=True)
    assert not r['physical_success_claimed'] and not r['historical_async_lease']
    assert (c/'lec_before_finished_import/lec.json').read_bytes()==old
    assert (c/'lec/lec.json').read_bytes()==(k/'lec/lec.json').read_bytes()
    assert transfer(k,c,finished_proof=True)==r


def test_native64_receipt_is_preserved_and_wrong_receipt_refused(tmp_path):
    import hashlib
    k,c=finished_fixture(tmp_path)
    receipt='actual native reset proof'
    staged={'schema':'opentallas.reset_contract.v1','die':'hbm','edges':64,'modules':['top'],
            'proof':{'verdict':'PASS','mutant':'CAUGHT','assert_edges':66,'receipt':'reset_contract/receipt.txt',
                     'receipt_sha256':hashlib.sha256(receipt.encode()).hexdigest()}}
    for root in (k,c):
        (root/'reset_contract').mkdir();(root/'reset_contract/receipt.txt').write_text(receipt)
        (root/'reset_contract.json').write_text(json.dumps(staged))
    report=json.loads((k/'lec/lec.json').read_text());report['top']='top'
    report['reset_contract'].update(used=64,contract={'file':'/work/reset_contract.json','die':'hbm','edges':64,'assert_edges':66,'receipt':'/work/reset_contract/receipt.txt'})
    time.sleep(.005);(k/'lec/lec.json').write_text(json.dumps(report))
    result=transfer(k,c,finished_proof=True,validate_only=True)
    assert 'reset_contract/receipt.txt' in result['current_files_sha256']
    assert not (c/'lec_before_finished_import').exists()
    (k/'reset_contract/receipt.txt').write_text('wrong')
    with pytest.raises(ValueError,match='receipt proof'):transfer(k,c,finished_proof=True,validate_only=True)


def test_old_component_override_cannot_become_a_new_default(tmp_path, monkeypatch):
    k,c=finished_fixture(tmp_path)
    report=json.loads((k/'lec/lec.json').read_text())
    report['reset_contract'].update(default=64,requested=4,used=4)
    (k/'lec/lec.json').write_text(json.dumps(report))
    monkeypatch.delenv('OT_LEC_RESET_CYCLES',raising=False)
    with pytest.raises(ValueError,match='component reset default'):
        transfer(k,c,finished_proof=True,validate_only=True)
    monkeypatch.setenv('OT_LEC_RESET_CYCLES','4')
    assert transfer(k,c,finished_proof=True,validate_only=True)['source_qualified'] is False


@pytest.mark.parametrize('mutant',['pending','unclean','pid','reset_added','input_changed','incomplete'])
def test_finished_proof_refuses_incomplete_or_changed_context(tmp_path,mutant):
    k,c=finished_fixture(tmp_path)
    if mutant=='pending':(k/'lec_async.done').unlink()
    elif mutant=='unclean':
        p=json.loads((k/'PROVENANCE.json').read_text());p['provenance']['dirty']=True;(k/'PROVENANCE.json').write_text(json.dumps(p))
    elif mutant=='pid':(c/'lec_async.pid').write_text('123')
    elif mutant=='reset_added':(c/'reset_contract.json').write_text('{}')
    elif mutant=='input_changed':(c/'net.v').write_text('mutant')
    else:
        p=json.loads((k/'lec/lec.json').read_text());p['counts']['undecided']=1;(k/'lec/lec.json').write_text(json.dumps(p))
    with pytest.raises(ValueError):transfer(k,c,finished_proof=True)
    assert not (c/'lec_before_finished_import').exists()
