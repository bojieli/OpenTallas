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
