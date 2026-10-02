from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import run_w17_D1_disjoint_native_shard as m

@pytest.mark.parametrize('node,threads,goal',[('local',24,'D1_LOCAL_SHARD'),('VM',48,'D1_VM_SHARD')])
def test_only_explicit_shard_goal(node,threads,goal):
 a=m.make_argv('/obj','/manifest',node)
 assert a[-1]==goal and '-j'+str(threads) in a and not any('__ALL.a' in x for x in a)
 assert not any('prlimit' in x or 'timeout' in x for x in a)

def test_container_exact_toolchain_mounts_and_no_restrictive_pilot_caps():
 a=m.docker_argv(Path('/scratch'),Path('/pinned'),Path('/manifest'))
 assert m.IMAGE in a and 'fsize=-1:-1' in a and '--as' not in str(a) and 'timeout' not in a
 assert '/pinned/sysroot/usr/include:/usr/include:ro' in a
 assert a[-1]=='D1_VM_SHARD' and '--cpus' in a and a[a.index('--cpus')+1]=='48'

@pytest.mark.parametrize('field,value',[('node','other'),('owner_quiescent',False),('fleet_lease_verified',False),('runtime_authorized',True),('wall_limit',900),('per_process_AS',3*2**30),('per_file_limit',512*2**20),('engine_source','wrong')])
def test_invalid_packet_rejected_before_any_process(monkeypatch,field,value):
 p={'node':'VM','owner_quiescent':True,'fleet_lease_verified':True,'runtime_authorized':False,'engine_source':'4e38326d6f361bc85e660f48c59c355e2bb95274'};p[field]=value
 monkeypatch.setattr(m.subprocess,'check_output',lambda *a,**kw:pytest.fail('must reject before process'))
 with pytest.raises(ValueError):m.validate(p)
