import json
import pytest
import dv_lower as D
import dv_lower_vec as V


@pytest.mark.parametrize('loader,required', [
    (D.load_ages, dict(ssq_psum_out=[171,187,203], root_cfg_lead=4)),
    (V.load_ages, dict(add_psum_out=[171], xs_out=[181], silu_out=[197], d2d={}, red_vm=211, root_cfg_lead=4))])
def test_selected_memory_requires_matching_measured_ages(tmp_path, monkeypatch, loader, required):
    path=tmp_path/'ages.json'
    path.write_text(json.dumps(required))
    monkeypatch.setenv('DV_LOWER_VFLAGS','')
    assert loader(path)==required
    monkeypatch.setenv('DV_LOWER_VFLAGS','+define+OT_QC_SRAM_MIF +define+OT_S8_CROM_ALIGN')
    with pytest.raises(D.LowerError,match='memory_profile'):
        loader(path)
    required['memory_profile']=dict(sram_if_mif=1,relative_memory_alignment=3)
    path.write_text(json.dumps(required))
    assert loader(path)==required
    monkeypatch.setenv('DV_LOWER_VFLAGS','+define+OT_S8_CROM_ALIGN')
    with pytest.raises(D.LowerError,match='memory_profile'):
        loader(path)


def test_zero_valued_define_still_selects_ifdef_profile(monkeypatch):
    monkeypatch.setenv('DV_LOWER_VFLAGS','+define+OT_QC_SRAM_MIF=0+OT_S8_CROM_ALIGN=0')
    assert D.memory_profile()==dict(sram_if_mif=1,relative_memory_alignment=3)
