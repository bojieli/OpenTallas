from pathlib import Path
import pytest
from runtime_rom import stage


def test_runtime_rom_is_staged_before_sim_and_wrong_content_refused(tmp_path):
    build=tmp_path/'build';build.mkdir()
    src=tmp_path/'dcal.sv';src.write_text('module qkd_d2d_cal_seq_pin_bc4 #(parameter VIAMAP="physical/p/profile.hex"); endmodule')
    (build/'vl.f').write_text(str(src)+'\n')
    image=tmp_path/'image.hex';image.write_text('0000000000000001\n'*32)
    out=tmp_path/'run';out.mkdir()
    rec=stage(build,out,image)
    assert (out/'physical/p/profile.hex').read_bytes()==image.read_bytes()
    assert rec['rows']==32
    assert stage(build,out)['sha256']==rec['sha256']
    image.write_text('0000000000000002\n'*32)
    with pytest.raises(ValueError,match='different content'):stage(build,out,image)
    image.unlink()
    with pytest.raises(ValueError,match='missing functional'):stage(build,out,image)


def test_missing_or_zero_profile_fails_before_sim(tmp_path):
    build=tmp_path/'build';build.mkdir();(build/'vl.f').write_text('')
    with pytest.raises(ValueError,match='one DCAL'):stage(build,tmp_path,tmp_path/'missing')


def test_unstaged_default_rom_fails_before_binary_launch(tmp_path):
    build=tmp_path/'build';build.mkdir()
    src=tmp_path/'dcal.sv';src.write_text('module qkd_d2d_cal_seq_pin_bc4 #(parameter VIAMAP="physical/p/profile.hex"); endmodule')
    (build/'vl.f').write_text(str(src)+'\n')
    with pytest.raises(ValueError,match='KV_DCAL_VIAMAP'):stage(build,tmp_path/'run')


@pytest.mark.parametrize('mutant',[False,True])
def test_boot_runner_propagates_preflight_failure_without_starting_binary(tmp_path,mutant):
    import os,subprocess
    build=tmp_path/'build';(build/'obj').mkdir(parents=True)
    src=tmp_path/'dcal.sv';src.write_text('module qkd_d2d_cal_seq_pin_bc4 #(parameter VIAMAP="physical/p/profile.hex"); endmodule')
    (build/'vl.f').write_text(str(src)+'\n')
    marker=tmp_path/'binary_started'
    binary=build/'obj/Vtb_kvslice';binary.write_text('#!/bin/bash\ntouch '+str(marker)+'\n');binary.chmod(0o755)
    image=tmp_path/'image';image.mkdir();(image/'epoch.txt').write_text('1\n')
    env=dict(os.environ);env.pop('KV_DCAL_VIAMAP',None)
    args=['bash',str(Path(__file__).with_name('run.sh')),str(build),str(image),str(tmp_path/'run')]+(['100'] if mutant else [])
    r=subprocess.run(args,env=env,capture_output=True,text=True)
    assert r.returncode==2 and not marker.exists(),(r.returncode,r.stdout,r.stderr)
    assert 'missing functional DCAL ROM' in r.stderr
