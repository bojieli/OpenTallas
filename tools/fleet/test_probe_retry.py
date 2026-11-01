from importlib.machinery import SourceFileLoader
from pathlib import Path
import pytest
M=SourceFileLoader('queued_probe_retry',str(Path(__file__).with_name('ot-run'))).load_module()

@pytest.mark.parametrize('note',[
 'SSH probe exit255: kex_exchange_identification: read: Connection reset by peer',
 'SSH probe exit255: Connection closed by remote host',
 'SSH probe exit255: Connection timed out',
 'Command ssh timed out after40seconds',
 'SSH probe returned no admission JSON',
])
def test_previously_queued_transport_failures_retry(note):
 assert M.retryable_queued_probe_failures(False,{'localhost'},{'localhost':note})==['localhost']
 assert M.retryable_queued_probe_failures(True,{'localhost'},{'localhost':note})==[]
 assert M.retryable_queued_probe_failures(False,set(),{'localhost':note})==[]

@pytest.mark.parametrize('note',['no /missing/input','request128GB exceeds physical RAM','disk19GB <50','SSH probe exit255: Permission denied','probe without ncpu'])
def test_real_or_unknown_refusals_are_not_masked(note):
 assert M.retryable_queued_probe_failures(False,{'localhost'},{'localhost':note})==[]
