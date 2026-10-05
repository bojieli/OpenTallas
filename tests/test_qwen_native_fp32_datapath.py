import json,subprocess,hashlib
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'rtl/experimental/qwen_native_fp32_20261003/ot_qwen_native_fp32_lanes.sv'
TB=ROOT/'rtl/test/qwen_native_fp32_20261003/tb.sv'
CPP=ROOT/'rtl/test/qwen_native_fp32_20261003/reference_vectors.cpp'
MODEL=ROOT/'results/uarch/qwen_native_fp32_20261003/model_before_RTL.json'

def run(tmp,source=SRC):
 d=json.loads(MODEL.read_text())
 subprocess.run(['g++','-std=c++17','-O1','-frounding-math','-ffp-contract=off',str(CPP),'-o',str(tmp/'reference')],check=True)
 with (tmp/'vectors.txt').open('w') as f:subprocess.run([str(tmp/'reference')],stdout=f,check=True)
 subprocess.run(['iverilog','-g2012','-s','tb','-o',str(tmp/'gate.vvp'),str(TB),str(source),*[str(ROOT/p) for p in d['source_SHA256']]],check=True,capture_output=True,text=True)
 r=subprocess.run(['vvp',str(tmp/'gate.vvp'),'+VECTORS='+str(tmp/'vectors.txt')],capture_output=True,text=True)
 (tmp/'actual.log').write_text(r.stdout+r.stderr)
 (tmp/'actual.json').write_text(json.dumps({'exit_code':r.returncode,'source_SHA256':hashlib.sha256(source.read_bytes()).hexdigest(),'vector_SHA256':hashlib.sha256((tmp/'vectors.txt').read_bytes()).hexdigest(),'arithmetic_reference':'native C++ float32,std::sqrt,FE_TONEAREST,-frounding-math,-ffp-contract=off; no numerical Python/constructor','simulator':'iverilog -g2012 / vvp','RTL_sources':d['source_SHA256']},sort_keys=True,indent=2)+'\n')
 return r

def test_actual_fourlane_RNE_signedzero_faults_reset_and_held_result(tmp_path):
 p=run(tmp_path);assert p.returncode==0,p.stdout+p.stderr
 assert 'vectors=512' in p.stdout

@pytest.mark.parametrize('old,new',[
 ('(canon?1\'b0:zero_sign)','1\'b0'),
 ('assign result_valid[i]=rst_n&&held;','assign result_valid[i]=rst_n&&held&&result_ready[i];'),
 ('accept&&select_div[i]','accept&&select_mul[i]'),
])
def test_actual_mutants_fail_gate(tmp_path,old,new):
 s=SRC.read_text();assert old in s;p=tmp_path/'mutant.sv';p.write_text(s.replace(old,new))
 r=run(tmp_path,p);assert r.returncode!=0 and 'FATAL' in r.stdout

def test_model_pins_existing_sources_and_no_controller_or_physical_claim():
 d=json.loads(MODEL.read_text())
 for p,h in d['source_SHA256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
 assert d['ports']['operand_beat_bytes']==32 and d['ports']['lanes']==4
 assert d['default_OPT']==0 and not d['physical']['clock_adoption']
 assert d['capacity']['wrapper_total_FF_bits']==156
 assert 'opcode' in d['scope'] and 'NOT established' in d['faults']
