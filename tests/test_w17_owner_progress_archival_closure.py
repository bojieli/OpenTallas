import importlib.util,json,hashlib
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('archival',ROOT/'tools/w17_owner_progress_archival_replay.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def test_archived_records_exact():
    x=m.replay()
    assert all(v['all_fields_identical'] for v in x['records'].values())
    assert not x['private_worktree_reads'] and not x['compile_or_runtime_launched']
@pytest.mark.parametrize('bad',['bytes','hash','escape'])
def test_bad_archival_input_fails_before_replay(tmp_path,monkeypatch,bad):
    a=tmp_path/'archive';a.mkdir();p=a/'source.sv';p.write_bytes(b'module source;endmodule\n')
    entry={'archival_path':'archive/source.sv','bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    if bad=='bytes':p.write_bytes(p.read_bytes()+b' ')
    if bad=='hash':entry['sha256']='0'*64
    if bad=='escape':entry['archival_path']='../outside'
    (a/'manifest.json').write_text(json.dumps({'files':{'origin':entry}}))
    monkeypatch.setattr(m,'ROOT',tmp_path);monkeypatch.setattr(m,'ARCHIVE',a)
    with pytest.raises(ValueError):m.manifest()
