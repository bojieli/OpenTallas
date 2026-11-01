from importlib.machinery import SourceFileLoader
from pathlib import Path
import pytest
M=SourceFileLoader('completion_samples',str(Path(__file__).with_name('ot-heavy-reconcile'))).load_module()

def row(cls='elab_hbm_whole_hierarchy.sh',status='0'):
 return ['2026-11-01T00:00:00','unit',cls,'64','19.9','300',status]

@pytest.mark.parametrize('status,qualified',[('0',True),('1',False),('137',False),('unknown',False),('legacy',False)])
def test_new_whole_hierarchy_class_requires_actual_success(status,qualified):
 assert M.completed_peak_qualified(row(status=status))==qualified


def test_legacy_history_retained_without_fabricating_success():
 assert M.completed_peak_qualified(row('older.sh','legacy'))
 assert M.completed_peak_qualified(row('older.sh')[:6])
 assert not M.completed_peak_qualified(row('older.sh','1'))


def test_failed_peak_remains_raw_lower_bound_without_downcharge(tmp_path,monkeypatch):
 peaks=tmp_path/'peaks.tsv'; raw='\t'.join(row(status='1'))+'\n';peaks.write_text(raw)
 monkeypatch.setattr(M,'PEAKS',str(peaks));monkeypatch.setattr(M,'SIZES',str(tmp_path/'sizes.json'))
 table=M.rebuild_sizes({});e=table['elab_hbm_whole_hierarchy.sh']
 assert e['n']==0 and e['partial']==1 and e['peak_gb']==19.9
 assert M.admit_size(64,'elab_hbm_whole_hierarchy.sh',table) is None
 assert peaks.read_text()==raw


def test_running_completion_is_unknown_and_real_exit_preserved(tmp_path,monkeypatch):
 monkeypatch.setattr(M,'D',str(tmp_path));d=tmp_path/'completions';d.mkdir()
 assert M.completion_status('old')=='legacy'
 p=d/'unit';p.write_text('unit\t100\t\trunning\n');assert M.completion_status('unit')=='unknown'
 p.write_text('unit\t100\t200\t1\n');assert M.completion_status('unit')=='1'
