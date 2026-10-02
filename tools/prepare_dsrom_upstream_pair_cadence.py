#!/usr/bin/env python3
"""PREPARE ONLY: real adapter/spine/VM -> unchanged full-sized selected pair.
No compiler, simulator or implementation entrypoint; expected data only assertions.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import w17_runtime_v41_die_images as PROD
import v41_die_images_w17w10 as FAST
import prepare_dsrom_actual_element_rne_wake as JOIN
import hdc_golden_v41 as G
BASE='results/rtl/dsrom_upstream_pair_cadence_prepare_20261002'
BENCH='rtl/test/tb_dsrom_upstream_pair_cadence.sv'
def sha(data):return hashlib.sha256(data).hexdigest()
class ImmutableMat:
 name='synthetic_unit_FP4';fmt='fp4';rows=257;K=512;r0=0;k0=0
 def block_word(self,row,c,b):
  assert 0<=row<257 and 0<=c<2 and 0<=b<8
  return (127<<128)|sum(2<<(4*j) for j in range(32))
def images(profile):
 if profile not in ('production5','existing_fast8'):raise ValueError('profile')
 I=PROD if profile=='production5' else FAST
 f=I.Field(8192,128,1024,**({} if I is PROD else {'pp':True,'fast':True}))
 ph=I.add_phase(f,[ImmutableMat()],fmt_fp32=(True,True))
 assert not f.bf[1] and ph['K']==512 and ph['nrows']==257
 cfg=f.cfg[0][1]
 assert cfg[0]&65535==256 and cfg[17]==0x8080 and cfg[8]&1 and cfg[16]==0
 assert len(f.words[2])==8 and not any(f.words[3].values())
 files={'spine_keys.hex':''.join(f'{(0x80000000 if i==0 else 0):08x}\n' for i in range(64)),
 'spine_phase.hex':''.join(f'{w:016x}\n' for w in (*I.phase_words(ph),*([0]*126))),
 'spine_stream.hex':''.join(f'{w:012x}\n' for w in (f.stream+[0]*(16384-len(f.stream)))),
 'e1.cfg.hex':''.join(f'{w:012x}\n' for w in (cfg+[0]*1575)),
 'VM_input.hex':''.join(f'{(0x3f800000 if i<1024 else 0):08x}\n' for i in range(524288))}
 rom=[[f.words[2+mb].get(i,0) for i in range(8192)] for mb in range(2)]
 files['ROM_input.json']=json.dumps({'words':rom},separators=(',',':'))+'\n'
 return files,ph,rom

def input_cpp(rom):
 # Literal ROM words only, never values from expected()/golden/public scoreboards.
 arrays=[]
 for mb,words in enumerate(rom):
  entries=[]
  for w in words:
   entries.append('{'+','.join(str((w>>(32*k))&0xffffffff)+'u' for k in range(9))+'}')
  arrays.append('{'+','.join(entries)+'}')
 return '''// Immutable ROM input-only DPI. No golden/expected data.
#include "svdpi.h"
#include <map>
#include <string>
#include <stdexcept>
static std::map<svScope,unsigned> ids;
static const svBitVecVal words[2][8192][9]={'''+','.join(arrays)+'''};
extern "C" void v41rt_rom_register(const char* name){
 std::string s(name);if(s!="e1" && s!="e1b")throw std::runtime_error("ROM instance");
 ids.emplace(svGetScope(),s=="e1b");
}
extern "C" void v41rt_rom_read(int addr,svBitVecVal* q){
 if(addr<0 || addr>=8192)throw std::runtime_error("ROM bounds");
 auto mb=ids.at(svGetScope());for(unsigned k=0;k<9;k++)q[k]=words[mb][addr][k];
}
'''

def sources():
 s=JOIN.L.load_sources()
 for old,new in JOIN.COPIES.items():s[old]=(ROOT/new).read_text()
 for p in JOIN.EXTRA:s[p]=(ROOT/p).read_text()
 for p in ('rtl/v41die/ot_v41_rom_adapt.sv','rtl/v41die/ot_v41_spine_w17w10.sv','rtl/hdc/v41/ot_hdc_actquant.sv','rtl/test/v41_runtime/ot_rom_4096x274_m8_rt.sv','rtl/test/v41_runtime/ot_rom_8192x274_m8_rt.sv'):
  s[p]=(ROOT/p).read_text()
 return s

def package():
 s=sources();files={Path(p).name:t for p,t in s.items()}
 assert len(files)==len(s)
 files[Path(BENCH).name]=(ROOT/BENCH).read_text()
 rom0=None
 for mode in ('production5','existing_fast8'):
  fs,ph,rom=images(mode)
  if rom0 is None:rom0=rom
  else:assert rom==rom0,'ROM words must match'
  files.update({mode+'/'+p:t for p,t in fs.items()})
 files['dsrom_upstream_pair_ROM.cpp']=input_cpp(rom0)
 return files

def expected():
 # Source golden chunked exact sum of unit products: two 256-element chunks,
 # block dots -> sequential chunk8 -> final ordered two-chunk padded tree.
 q,e=G.quant_fp8(np.ones(512,dtype=np.float32))
 dots=np.asarray([np.ldexp(np.float32(sum(q[32*i:32*(i+1)])),int(e[i])) for i in range(16)],dtype=np.float32)
 chunks=[G.csum(dots[i:i+8]) for i in (0,8)]
 value=G.csum(np.asarray(chunks,dtype=np.float32))
 return {'FP32':f'{np.float32(value).view(np.uint32).item():08x}','row':256,'seg':0,'nseg':1,'positions':[0,1],'err':0,'chunks':[float(x) for x in chunks],'activation_code_values':sorted(set(float(x) for x in q)),'activation_exponents':sorted(set(int(x) for x in e)),'block_dots':[float(x) for x in dots]}

def prepare(out):
 plan=json.loads((ROOT/BASE/'sourceplan.json').read_text())
 for p,h in plan['input_source_sha256'].items():
  if sha((ROOT/p).read_bytes())!=h:raise ValueError('source changed '+p)
 files=package()
 if {p:sha(t.encode()) for p,t in files.items()}!=plan['generated_files_sha256']:raise ValueError('package changed')
 out.mkdir(parents=True,exist_ok=False)
 for p,t in files.items():
  dst=out/p;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(t)
 rec={'status':'PREPARED_NOT_COMPILED','compile_authorized':False,'simulation_authorized':False,'sourceplan_sha256':sha((ROOT/BASE/'sourceplan.json').read_bytes()),'files_sha256':plan['generated_files_sha256']}
 (out/'preparation.json').write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n')
 return rec
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--out',required=True,type=Path);prepare(a.parse_args().out)
