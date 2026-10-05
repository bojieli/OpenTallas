"""Selected source hook: native carried reduction and actual ME admission."""
import importlib.util,subprocess,json
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[1]
D=R/'rtl/dsrom_sys/s81_native_head'
COL=[R/'rtl/rom/collectives/ot_rom_coll_pkg.sv',R/'rtl/rom/collectives/ot_rom_coll_skid.sv']

def compile_run(tmp_path,top,files):
    exe=tmp_path/'test.vvp'
    c=subprocess.run(['iverilog','-g2012','-s',top,'-o',str(exe),*[str(p) for p in files]],capture_output=True,text=True)
    assert c.returncode==0,c.stderr
    r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
    (tmp_path/'runtime.log').write_text(r.stdout+r.stderr)
    return r.stdout

def test_native_four_rank_full_head(tmp_path):
    s=compile_run(tmp_path,'tb_head_hook',COL+[D/'ot_rom_argmax_rows.sv',D/'ot_dsrom_s81_head_amax.sv',D/'tb_head_hook.sv'])
    assert 'PASS_ACTUAL_NATIVE_CARRIED_HEAD_FOUR_RANKS_129280_ROWS_EXPLICIT_ID_HELD_ACK' in s and 'FATAL' not in s

def test_real_lane_id_mutant(tmp_path):
    s=(D/'ot_rom_argmax_rows.sv').read_text().replace('lg_ids[32*l +:32]','l')
    p=tmp_path/'wrong_ids.sv';p.write_text(s)
    out=compile_run(tmp_path,'tb_head_hook',COL+[p,D/'ot_dsrom_s81_head_amax.sv',D/'tb_head_hook.sv'])
    assert 'FATAL' in out and 'native global explicit-ID tie/owner' in out

def test_generated_adapter_and_core_connections(tmp_path):
    spec=importlib.util.spec_from_file_location('hook',R/'tools/dsrom_s81_native_head_hook.py')
    h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);out=tmp_path/'source';h.emit(out)
    s=compile_run(tmp_path,'tb_head_admission',[out/'ot_v41_rom_adapt.sv',D/'tb_head_admission.sv'])
    assert 'PASS_SOURCE_HEAD_ROUND0_AMAX_FP32_AND_INVALID_ADMISSION' in s and 'FATAL' not in s
    c=(out/'ot_hdc_core_v41x.sv').read_text()
    assert '((X_ROM != 0 && OPT_NATIVE_HEAD) || X_ME != 0)' in c
    assert 'rom_ready_w && !head_busy' in c and 'rom_idle_w && !head_busy' in c
    assert '.write_valid(rom_we),.write_accept(capture_vm_accept)' in c
    assert 'OPT_NATIVE_HEAD ? head_idx' in c and '.OPT_NATIVE_HEAD(OPT_NATIVE_HEAD)' in c
    assert '.final_valid(head_final_valid)' in c
    a=(out/'ot_v41_rom_adapt.sv').read_text();assert "s_fmt <= 2'd1;" in a
    assert 'OPT_NATIVE_HEAD=0' in c and 'OPT_NATIVE_HEAD=0' in a


def test_model_prices_actual_roots():
    spec=importlib.util.spec_from_file_location('u',R/'tools/uarch_model.py');u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
    for roots in [64,128]:
        a=u.dsrom_s81_head_result_hook(roots)
        assert not a['new_dot_arithmetic'] and not a['opt_in_default']
        assert a['source_return_bytes_per_cycle']==roots*4
        assert a['added_explicit_ID_state_bits_per_rank']>0
        assert a['selected_storage_macros']==10100 and a['retained_storage_increment_mm2']==0
        assert a['SS_FF'] is False
