import importlib.util
from pathlib import Path
import pytest
s=importlib.util.spec_from_file_location('adopt_eng_split',Path(__file__).with_name('adopt_eng_split.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def test_boot_decode_and_core_pin_names_preserved():
    boot='module dsdv_eng_cfg; endmodule\nmodule dsdv_eng_rr #(parameter RETURN_AGE=640) ();\n wire en,ly; wire[1:0]rk; wire[3:0]st;\n dsdv_eng_cfg u_cfg(.cfg_en(en),.cfg_rank(rk));\n dsdv_eng_rr_c #(.RETURN_AGE(RETURN_AGE)) u_c();\nendmodule\n'
    split='module dsdv_eng_rr_split #(parameter RETURN_AGE=640) (\n input cfg_en,cfg_layer, input[1:0]cfg_rank\n);\n dsdv_eng_rr_e u_e(.cfg_en(cfg_en),.cfg_layer(cfg_layer),.cfg_rank(cfg_rank));\n dsdv_eng_rr_h0 u_h0(); dsdv_eng_rr_h1 u_h1();\nendmodule\n'
    out=m.emit(boot,split)
    assert 'dsdv_eng_cfg u_cfg(.cfg_en(en),.cfg_rank(rk));' in out
    assert 'dsdv_eng_rr_e u_e(.cfg_en(en),.cfg_layer(ly),.cfg_rank(rk));' in out
    assert 'dsdv_eng_rr_c #' not in out
    assert out[:out.index('module dsdv_eng_rr #')] == boot[:boot.index('module dsdv_eng_rr #')]

def test_unconfigured_legacy_master_is_rejected():
    with pytest.raises(ValueError,match='real CTL boot decoder'):
        m.emit('module dsdv_eng_rr #(parameter X=0) (); endmodule\n', 'module dsdv_eng_rr_split #(parameter X=0) (); endmodule\n')
