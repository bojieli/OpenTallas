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


def test_whole_hierarchy_cannot_borrow_an_incomplete_live_phase():
 e=dict(n=0,proved=1,peak_gb=19.9)
 assert M.capacity_sample_count('elab_hbm_whole_hierarchy.sh',e)==0
 assert M.capacity_sample_count('elab_hbm_whole_hierarchy.sh:mode',e)==0
 assert M.admit_size(64,'elab_hbm_whole_hierarchy.sh',{'elab_hbm_whole_hierarchy.sh':e}) is None
 assert M.class_peak('elab_hbm_whole_hierarchy.sh',{'elab_hbm_whole_hierarchy.sh':e}) is None


def test_wrapper_records_real_exit_without_changing_command_status(tmp_path):
 import subprocess
 wrapper=Path(__file__).with_name('ot-heavy-exit').read_text()
 wrapper=wrapper.replace('D=/var/tmp/ot-heavy;', 'D='+str(tmp_path)+';')
 wrapper=wrapper.replace('/usr/local/bin/ot-heavy-reconcile','/nonexistent-test-reconcile')
 wrapper=wrapper.replace('CG=/sys/fs/cgroup$(awk -F:', 'CG=/sys/fs/cgroup$(awk -F:')
 script=tmp_path/'wrapper';script.write_text(wrapper)
 for status in (0,3):
  unit='test-'+str(status)
  p=subprocess.run(['bash',str(script),unit,'bash','-c','exit '+str(status)],capture_output=True,text=True)
  assert p.returncode==status
  fields=(tmp_path/'completions'/unit).read_text().strip().split('\t')
  assert fields[0]==unit and fields[-1]==str(status)
