"""Fresh legacy core kits carry only their already-proven die reset contract."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_core_kit_legacy as G
import lec


def contract(tmp_path):
    src = tmp_path / 'source'
    src.mkdir()
    (src / 'reset_contract').mkdir()
    receipt = b'HOLD64 min pin65; HOLD61 mutant child62 CAUGHT\n'
    (src / 'reset_contract/receipt.txt').write_bytes(receipt)
    data = dict(schema='opentallas.reset_contract.v1', die='s81', edges=64,
                modules=['listed_lane'], proof=dict(verdict='PASS', assert_edges=65,
                mutant='CAUGHT', receipt='reset_contract/receipt.txt',
                receipt_sha256=hashlib.sha256(receipt).hexdigest()))
    (src / 'reset_contract.json').write_text(json.dumps(data))
    return src


def test_staged_contract_is_accepted_by_actual_lec_consumer(tmp_path):
    src=contract(tmp_path); kd=tmp_path/'kit';kd.mkdir()
    staged=G.stage_reset_contract(kd,'listed_lane',src/'reset_contract.json')
    assert staged['edges']==64
    result=lec.reset_contract_gate(kd,'listed_lane',environ={})
    assert result['used']==64 and 'refused' not in result
    assert (kd/'reset_contract/receipt.txt').read_bytes()==(src/'reset_contract/receipt.txt').read_bytes()


def test_missing_or_unlisted_contract_keeps_four_edge_default(tmp_path):
    src=contract(tmp_path); kd=tmp_path/'kit';kd.mkdir()
    assert G.stage_reset_contract(kd,'unlisted',src/'reset_contract.json') is None
    assert G.stage_reset_contract(kd,'listed_lane',src/'missing.json') is None
    assert not list(kd.iterdir())
    assert lec.reset_contract_gate(kd,'unlisted',environ={})['used']==4


def test_bad_receipt_is_refused_before_staging(tmp_path):
    src=contract(tmp_path); kd=tmp_path/'kit';kd.mkdir()
    (src/'reset_contract/receipt.txt').write_text('wrong proof')
    with pytest.raises(SystemExit,match='sha256 mismatch'):
        G.stage_reset_contract(kd,'listed_lane',src/'reset_contract.json')
    assert not list(kd.iterdir())
