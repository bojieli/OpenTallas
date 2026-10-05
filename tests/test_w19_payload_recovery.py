"""Source-binding and incomplete-input rejection for the retained compact gate."""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import w19_payload_recovery as R

RECORD = ROOT / 'results/rtl/w19_payload_transport_historical_3b15b18e.json'

@pytest.mark.parametrize('mutation', ['failed_verdict', 'missing_case', 'changed_source', 'missing_fixtures'])
def test_recovery_refuses_unbound_or_incomplete_evidence(tmp_path, mutation):
    record = copy.deepcopy(json.loads(RECORD.read_text()))
    if mutation == 'failed_verdict':
        record['status'] = 'fail'
    elif mutation == 'missing_case':
        record['cases'].pop()
    elif mutation == 'changed_source':
        record['source_sha256']['rtl/gpu/ot_gpu_payload_assemble.sv'] = '0' * 64
    with pytest.raises(AssertionError):
        R.audit(record, tmp_path)


def test_receipt_keeps_original_source_and_narrow_scope():
    record = json.loads(RECORD.read_text())
    assert record['source_commit'] == '3b15b18e997ad0a05cc7acf474a7329847e38845'
    assert 'No router, multi-SM/rank runtime, complete token, adoption or SS/FF claim' in record['claim_boundary']
    assert record['model_preflight']['enabled_default'] is False
