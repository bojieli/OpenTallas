#!/usr/bin/env python3
"""Generate input-only ROM backend plus assertion-only numerical oracle. Never build/run."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
BASE='results/rtl/dsrom_actual_element_numerical_prepare_20261002'
MODEL=ROOT/BASE/'model.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def mod(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
ORACLE=mod('independent_numerical','tools/dsrom_actual_element_numerical_oracle.py')
def inputs():return json.loads((ROOT/BASE/'input_fixture.json').read_text())
def cpp(image):
    # This function only sees the input image, never expected()/partial() results.
    text=['// Immutable synthetic inputs only; no expected values or activation injection.','#include "svdpi.h"','#include <map>','#include <string>','#include <stdexcept>','#include <cstdint>','static std::map<svScope,unsigned> macro_id;','extern "C" void v41rt_cfg_register() {}','extern "C" long long v41rt_cfg_read(int addr) {',' if(addr<0 || addr>=1600) throw std::runtime_error("cfg bounds");',' switch(addr) {']
    text += [f' case {a}: return {int(w,16)}ull;' for a,w in sorted(image['cfg_words'].items(),key=lambda x:int(x[0]))]
    text+=[' default: return 0;',' }','}','extern "C" void v41rt_rom_register(const char* inst) { std::string s(inst); macro_id.emplace(svGetScope(),s.back()==\'b\'?1u:0u); }','extern "C" void v41rt_rom_read(int addr, svBitVecVal* q) {',' if(addr<0 || addr>=8192) throw std::runtime_error("ROM bounds");',' for(unsigned i=0;i<9;i++) q[i]=0;',' switch(macro_id.at(svGetScope())*8192u+unsigned(addr)) {']
    for macro,words in image['ROM_words'].items():
        for addr,word in sorted(words.items(),key=lambda x:int(x[0])):
            value=int(word,16); assignments=' '.join(f'q[{i}]=0x{(value>>(i*32))&0xffffffff:08x}u;' for i in range(9))
            text.append(f' case {int(macro)*8192+int(addr)}: {assignments} break;')
    return '\n'.join(text+[' default: break;',' }','}',''])
def sv_stimulus(image):
    # Input codebooks/profile arithmetic only; independent expected numbers absent.
    lines=['// Input-only deterministic stimulus codebooks.']
    for name,codes,width in [('q_code',image['Q_CODES'],8),('bf_code',image['BF_CODES'],16)]:
        lines += [f'function automatic [{width-1}:0] {name}(input integer i);',f' case(i%{len(codes)})']+[f' {k}: {name}={width}\'h{v:x};' for k,v in enumerate(codes)]+[f' default: {name}=0;',' endcase','endfunction']
    lines+=['function automatic [7:0] input_xcode(input integer pos,unit_id,block_id,lane,half);',' input_xcode=q_code(lane*3+pos*7+unit_id*5+block_id*11+half*2);','endfunction','function automatic integer input_xexp(input integer pos,unit_id,block_id,half);',' case((pos+unit_id+block_id+half)%5)']+[f' {i}:input_xexp={v};' for i,v in enumerate((-9,-1,0,2,8))]+[' default:input_xexp=0;',' endcase','endfunction','function automatic [15:0] input_xbcode(input integer pos,unit_id,block_id,lane);',' input_xbcode=bf_code(lane*3+pos*7+unit_id*5+block_id*2);','endfunction','function automatic integer active_segments(input integer phase_id);',' active_segments=phase_id<6?8:4;','endfunction','function automatic integer contract_nseg(input integer phase_id);',' contract_nseg=phase_id>=9?2:1;','endfunction','function automatic integer is_BF_phase(input integer phase_id);',' is_BF_phase=(phase_id==3 || phase_id==8 || phase_id==11);','endfunction']
    return '\n'.join(lines)+'\n'
def sv_expected(rows):
    lines=['// EXPECTED ASSERTIONS ONLY: never used to drive any DUT input.','function automatic [32:0] numerical_expected(input integer phase_id,macro_id,segment_id,position_id);',' case((phase_id*2+macro_id)*48+segment_id*6+position_id)']
    for r in rows:
        k=(r['phase']*2+r['macro'])*48+r['segment_slot']*6+r['position']
        lines.append(f' {k}:numerical_expected=33\'h1{r["value_hex"]};')
    return '\n'.join(lines+[' default:numerical_expected=33\'d0;',' endcase','endfunction',''])
def package():
    g=mod('rowfix_prep','tools/prepare_dsrom_actual_element_rowfix.py');files=g.files();m=json.loads(MODEL.read_text())
    del files['tb_dsrom_actual_element_gate_rowfix.sv'];del files['dsrom_actual_element_rom.cpp']
    for p in [m['bench_path'],'rtl/test/dsrom_actual_element_numerical_rom.cpp','rtl/test/dsrom_actual_element_numerical_stimulus.svh','rtl/test/dsrom_actual_element_numerical_expected.svh']:files[Path(p).name]=(ROOT/p).read_text()
    return files

def verify():
    m=json.loads(MODEL.read_text())
    for p,h in m['preserved_files_sha256'].items():
        old=subprocess.check_output(['git','show',m['preserved_commit']+':'+p],cwd=ROOT)
        if sha(old)!=h or (ROOT/p).read_bytes()!=old:raise ValueError('preserved file changed: '+p)
    for p,h in m['new_artifact_pins'].items():
        if sha((ROOT/p).read_bytes())!=h:raise ValueError('numerical prep pin mismatch: '+p)
    for p,h in m['additional_contract_pins'].items():
        if sha(subprocess.check_output(['git','show',h['commit']+':'+p],cwd=ROOT))!=h['sha256']:raise ValueError('contract pin mismatch: '+p)
    mod('rowfix_prep_verify','tools/prepare_dsrom_actual_element_rowfix.py').verify()
    image=inputs();rows=ORACLE.expected(image)
    checks={'rtl/test/dsrom_actual_element_numerical_rom.cpp':cpp(image),'rtl/test/dsrom_actual_element_numerical_stimulus.svh':sv_stimulus(image),'rtl/test/dsrom_actual_element_numerical_expected.svh':sv_expected(rows)}
    for p,text in checks.items():
        if (ROOT/p).read_text()!=text:raise ValueError('generated input/expected fixture changed: '+p)
    if image!=json.loads(json.dumps(ORACLE.build_inputs())):raise ValueError('input fixture differs from modeled synthetic inputs')
    return m

def prepare(out):
    if out.exists():raise FileExistsError(out)
    m=verify();files=package();pins={p:sha(t.encode()) for p,t in files.items()}
    if pins!=m['generated_files_sha256']:raise ValueError('numerical package mismatch')
    out.mkdir(parents=True,exist_ok=False)
    for name,text in files.items():
        with (out/name).open('x') as f:f.write(text)
    receipt=dict(status='NUMERICAL_PREPARED_NOT_COMPILED',model_sha256=sha(MODEL.read_bytes()),files_sha256=pins,preserved_files_verified=len(m['preserved_files_sha256']),expected_use='Assertions only',execution_gate=m['execution_gate'])
    with (out/'preparation.json').open('x') as f:json.dump(receipt,f,indent=2,sort_keys=True);f.write('\n')
    return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);a=p.parse_args();prepare(a.out)
