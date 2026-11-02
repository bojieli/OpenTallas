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
