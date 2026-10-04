"""Actual native arithmetic, full rank shape, ownership and failing controls."""
import importlib.util
import subprocess
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'rtl/test/s81_native_head_terminal/native_head_terminal.sv'
TB=ROOT/'rtl/test/s81_native_head_terminal/tb.sv'
FP=ROOT/'rtl/hdc/ot_hdc_fastfp.sv'
MARK='PASS_NATIVE_HEAD_TERMINAL_FULL32320_TIES_HOLD_STALE_NONFINITE_CANCEL'

def run(tmp_path, text):
    source=tmp_path/'leaf.sv';source.write_text(text)
    obj=tmp_path/'tb.vvp'
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(obj),str(source),str(TB),str(FP)],check=True,capture_output=True,text=True)
    return subprocess.run(['vvp',str(obj)],capture_output=True,text=True)

def test_full_rank_native_and_ownership(tmp_path):
    r=run(tmp_path,SRC.read_text())
    assert r.returncode==0 and MARK in r.stdout and 'FATAL' not in r.stdout

@pytest.mark.parametrize('old,new,marker',[
 ('(key==best_key && row_delay[8]<best_row)','(key==best_key && row_delay[8]>best_row)','full native row/tie terminal'),
 ('owned+fire-ack','owned+fire-v3','finite seat hold'),
 ('in_owner==owner','1\'b1','stale identity'),
])
def test_required_real_mutants(tmp_path,old,new,marker):
    text=SRC.read_text();assert old in text
    r=run(tmp_path,text.replace(old,new))
    assert 'FATAL' in r.stdout and marker in r.stdout and MARK not in r.stdout

def test_model_default_and_positive_resources():
    spec=importlib.util.spec_from_file_location('uarch_model',ROOT/'tools/uarch_model.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    a=m.dsrom_s81_native_head_terminal()
    assert a['opt_in_default'] is False and a['retained_head_macros']==10100
    assert a['state_FF_bits_lower_bound']==1312
    assert a['accepted_pair_II_cycles']==1 and a['reserved_logit_seats']==16
    assert a['composed_single_user_cycles_lower_bound']==32330
    assert not a['physical_SS_FF'] and not a['trained_payload_qualified']
    assert a['new_adders_and_comparator_mapped_area_mm2'] is None
