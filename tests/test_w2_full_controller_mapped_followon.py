import importlib.util
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('followon',ROOT/'tools/w2_full_controller_mapped_followon.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)

def terminal():
 return dict(exit_code=0,status='MAPPED_SOURCE_AVAILABLE_CENSUS_PENDING',source_commit=M.PIN,
             top=M.TOP,parameters=M.PARAMS.copy(),source_sha256={'SOURCE':'PIN'},
             all_top_ports_exposed=True,blackboxes=False,pruned_proxy=False)

@pytest.mark.parametrize('key,value',[('exit_code',1),('source_commit','other'),('top','proxy'),
 ('pruned_proxy',True),('blackboxes',True),('all_top_ports_exposed',False)])
def test_bad_source_or_failed_terminal_cannot_admit_analysis(key,value):
 t=terminal();t[key]=value
 with pytest.raises(ValueError):M.enroll(t,{'SOURCE':'PIN'})

def test_exact_parameters_and_source_bytes_are_required():
 t=terminal();M.enroll(t,{'SOURCE':'PIN'})
 t['parameters']['MAX_OUT']=8
 with pytest.raises(ValueError):M.enroll(t,{'SOURCE':'PIN'})
 with pytest.raises(ValueError):M.enroll(terminal(),{'SOURCE':'OTHER'})

def test_intrinsic_screen_does_not_tie_ports_or_invent_context():
 for corner,mode in [('SS','max'),('FF','min')]:
  t=M.script(corner)
  assert 'set_cmd_units -time ps' in t
  assert '-setup 60' in t and '-hold 25' in t and '833.3333333333334' in t
  assert 'all_registers -output_pins' in t and 'all_registers -data_pins' in t
  assert f'-path_delay {mode}' in t and 'missing internal timing path' in t
  assert 'set_input_delay' not in t and 'set_case_analysis' not in t
  assert 'FAKE' not in t and '250407' not in t
  assert all(f'RVT_{corner}' in str(p) for p in M.libraries(corner))

def test_price_scales_with_actual_inventory_without_runtime_caps():
 small=M.admission_model({'json':1000,'verilog':1000})
 large=M.admission_model({'json':1024**3,'verilog':1024**3})
 assert large['expected_peak_GiB']>small['expected_peak_GiB']
 assert large['shared_reserve_GiB']==150
 assert all(large[n] is None for n in ['wall_limit','memory_limit','file_limit','AS_limit'])
 with pytest.raises(ValueError):M.admission_model({'missing':0})
