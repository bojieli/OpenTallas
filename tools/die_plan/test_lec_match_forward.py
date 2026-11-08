"""IQN opt-ins survive config/env precedence, Docker ingress and proof identity."""
import os
from pathlib import Path
import subprocess
import sys
import pytest

HERE=Path(__file__).parent
sys.path.insert(0,str(HERE))
import resign
import gen_phys

FLAGS=('OT_LEC_REPLICA_MATCH','OT_LEC_MEM_LANES','OT_LEC_ENABLE_FILL_GUARD')

@pytest.mark.parametrize('flag',FLAGS)
def test_resign_config_and_env_override(tmp_path,flag):
    (tmp_path/'config.mk').write_text('export '+flag+' = 1 # explicit opt-in\n')
    assert resign.lec_env_args(str(tmp_path),{})==['-e',flag+'=1']
    assert resign.lec_env_args(str(tmp_path),{flag:'0'})==['-e',flag+'=0']
    assert resign.lec_env_args(str(tmp_path),{flag:''})==['-e',flag+'=1']

@pytest.mark.parametrize('flag',FLAGS)
def test_resign_boolean_rejects_nonbinary(tmp_path,flag):
    (tmp_path/'config.mk').write_text('export '+flag+' = 2\n')
    with pytest.raises(resign.ResignError,match='0 or 1'):
        resign.lec_env_args(str(tmp_path),{})


def test_resign_unset_flags_preserve_empty_default(tmp_path):
    (tmp_path/'config.mk').write_text('export DESIGN_NAME = example\n')
    assert resign.lec_env_args(str(tmp_path),{})==[]


def run_gen_block(tmp_path,cfg,env=None):
    (tmp_path/'config.mk').write_text(cfg)
    marker='# LEC-IQN proof option forwarding:'
    block=marker+gen_phys.RUN_KIT.split(marker,1)[1].split('# End LEC-IQN proof option forwarding.',1)[0]
    script=block+'\nprintf "%s\\n" "${LEC_MATCH_DOCKER[@]}"\n'
    actual={k:v for k,v in os.environ.items() if k not in FLAGS};actual.update(env or {});actual['K']=str(tmp_path)
    return subprocess.run(['bash','-c',script],env=actual,capture_output=True,text=True)

@pytest.mark.parametrize('flag',FLAGS)
def test_generated_runner_reads_config_and_env(tmp_path,flag):
    r=run_gen_block(tmp_path,'export '+flag+' = 1\n')
    assert r.returncode==0 and r.stdout.splitlines()==['-e',flag+'=1']
    r=run_gen_block(tmp_path,'export '+flag+' = 1\n',{flag:''})
    assert r.returncode==0 and r.stdout.splitlines()==['-e',flag+'=1']
    r=run_gen_block(tmp_path,'export '+flag+' = 1\n',{flag:'0'})
    assert r.returncode==0 and r.stdout.splitlines()==['-e',flag+'=0']


def test_generated_runner_unset_and_invalid(tmp_path):
    r=run_gen_block(tmp_path,'export DESIGN_NAME = example\n')
    assert r.returncode==0 and not r.stdout.strip()
    r=run_gen_block(tmp_path,'export OT_LEC_MEM_LANES = yes\n')
    assert r.returncode==10 and 'must be 0 or 1' in r.stderr

@pytest.mark.parametrize('flag',FLAGS)
def test_async_forwards_and_fingerprints_actual_option(tmp_path,flag):
    script=(HERE/'lec_async.sh').read_text()
    loop=next(l for l in script.splitlines() if l.strip().startswith('for v in OT_LEC_HINTS_PRESEED'))
    env=dict(os.environ);env[flag]='1'
    r=subprocess.run(['bash','-c','ENVS=(); '+loop+'\nprintf "%s\\n" "${ENVS[@]}"'],env=env,capture_output=True,text=True)
    assert r.returncode==0 and flag+'=1' in r.stdout.splitlines()
    (tmp_path/'config.mk').write_text('export DESIGN_NAME = example\n')
    (tmp_path/'lec.py').write_text('# immutable driver\n')
    def identity(e):return subprocess.check_output(['bash',str(HERE/'lec_async.sh'),'identity',str(tmp_path),'source'],env=e,text=True).strip()
    absent={k:v for k,v in os.environ.items() if k!=flag}
    assert identity(absent)!=identity(env)
