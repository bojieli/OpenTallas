from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import run_w17_D1_disjoint_native_shard_r2 as m

def test_readonly_image_has_writable_disk_temporary_files():
 a=m.docker_argv(Path('/scratch'),Path('/inputs'),Path('/manifest'))
 assert '--read-only' in a and '/scratch/tmp:/tmp' in a
 assert a.index('/scratch/tmp:/tmp')<a.index(m.base.IMAGE)
 assert '--tmpfs' not in a and '--as' not in str(a)
 assert a[-1]=='D1_VM_SHARD'

def test_bad_go_creates_no_scratch_and_launches_no_process(tmp_path,monkeypatch):
 packet=tmp_path/'packet.json';packet.write_text('{"node":"VM","owner_quiescent":false}')
 monkeypatch.setattr(m.base.subprocess,'Popen',lambda *a,**kw:pytest.fail('must not launch'))
 with pytest.raises(ValueError):m.run(packet,tmp_path)
 assert not (tmp_path/'tmp').exists()
