#!/usr/bin/env python3
"""Lower genuine DS1M and Qwen8K captured stages into the existing c12 bench.

This executes only the reference for the selected five/three SU instructions,
checks their captured numerical outputs, and serializes existing operands.
It performs no checkpoint loading, prefill, token inference or RTL simulation.
"""
import argparse,hashlib,json,os,pickle
from pathlib import Path
os.environ.setdefault('HDC_V41_ARITH','chunk8')
os.environ.setdefault('HDC_SU_WIDTH','1024')
import numpy as np
import rtl_hdc_v41x_vec_campaign as V
import hbm_su_c12 as C
import hdc_qwen_fullshape_isa_w12 as Q
import hdc_isa as QI

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def blank():
 return V.Mem(np.zeros(1<<V.VMA,np.uint32),np.zeros(1<<V.KVA,np.uint32),
              np.zeros((1<<V.CRA,2),np.uint32),np.zeros(1<<V.WRA,np.uint16))
def emit(out,name,mem,ops,addr,want,origin):
 ref,scheduled,lays,_=V.schedule(ops,mem,1024,256)
 if any(x['bad'] for x in lays):raise ValueError(name+' instruction layout refused')
 got=ref.vm[addr:addr+len(want)]
 bad=int(np.count_nonzero(got!=want))
 if bad:raise ValueError(f'{name}: ISA lowering differs from captured golden in {bad} words')
 d=out/name;V.write_case(d,mem,scheduled)
 V.write_hex(d/'expected_vm.hex',ref.vm,32);V.write_hex(d/'expected_kv.hex',ref.kv,32)
 files=['vm.hex','kv.hex','cr.hex','wr.hex','prog.hex','expected_vm.hex','expected_kv.hex']
 return dict(directory=str(d.resolve()),position=8191 if name=='Qwen8K' else 1048575,
   nops=len(scheduled),source_capture=origin,external_producer=False,
   sha256={n:sha(d/n) for n in files},captured_output_words=len(want),captured_output_mismatches=bad)
def qwen(out,src):
 oracle=json.loads((src/'oracle.json').read_text())
 p=oracle['per_position']['8191']
 if oracle['tp']!=4 or oracle['layers']!=36 or p['token']!=24:raise ValueError('Qwen captured position/target mismatch')
 if sha(src/'L35_die0_x.hex')!=p['layer_x_sha256']['L35_die0']:raise ValueError('Qwen predecessor changed')
 if sha(src/'head_die0_xnorm.hex')!=p['head']['head_die0']['xnorm_sha256']:raise ValueError('Qwen golden changed')
 mem=blank();x=V.read_hex(src/'L35_die0_x.hex').astype(np.uint32)
 if len(x)!=4096:raise ValueError('Qwen full 4096-word head input required')
 mem.vm[4096:8192]=x
 cr=[int(x,16) for x in (src/'crom.hex').read_text().split()]
 mem.cr[:len(cr),0]=np.array([x&0xffffffff for x in cr],np.uint32)
 mem.cr[:len(cr),1]=np.array([x>>32 for x in cr],np.uint32)
 ops=[];decoded=[]
 for line in (src/'program.hex').read_text().split():
  f=Q.decode_instruction(int(line,16))
  if f['unit']!=QI.UNIT_SU:break
  decoded.append({k:v for k,v in f.items() if v})
  # These exact three instructions contain no dynamic, cross-lane rotation,
  # indirect source, optional rounding or kernel/software synchronization.
  allowed={'unit','wait_su','su_nout','su_nin','a_base','a_si','b_base','c_src','c_si',
           'ma','ad','sfu','mc','dst','d_base','d_si','imm1','imm2','red','r_base','red_sq'}
  if any(v and k not in allowed for k,v in f.items()):raise ValueError('unsupported Qwen instruction field')
  g=V.op_defaults();g.update(nout=f['su_nout'],nin=f['su_nin'],abase=f['a_base'],asi=f['a_si'],
   bbase=f['b_base'],csrc=V.I.SRC_CLO if f['c_src'] else V.I.SRC_VM,csi=f['c_si'],
   m1={0:0,QI.MA_AB:V.I.M1_AB,QI.MA_AIMM:V.I.M1_AIMM}[f['ma']],
   ad={0:0,QI.AD_IMM:V.I.AD_IMM}[f['ad']],sfu={0:0,QI.SFU_RSQRT:V.I.SFU_RSQRT}[f['sfu']],
   e1=V.I.E1_MULC if f['mc']==QI.MC_C else 0,dst=f['dst'],obase=f['d_base'],osi=f['d_si'],
   imm1=f['imm1'],imm2=f['imm2'],red=f['red'],redsq=f['red_sq'],rbase=f['r_base'])
  ops.append(g)
 if len(ops)!=3:raise ValueError('Qwen released head prefix must be three SU instructions')
 want=V.read_hex(src/'head_die0_xnorm.hex').astype(np.uint32)
 return emit(out,'Qwen8K',mem,ops,8192,want,dict(target='Qwen3-8B TP4 head RMSNorm at P8191',
  files={n:sha(src/n) for n in ('oracle.json','L35_die0_x.hex','head_die0_xnorm.hex','program.hex','crom.hex')},
  input_origin=str(src.resolve()),decoded_qwen_program=decoded,oracle_next_token=18))
def ds(out,path):
 blob=pickle.loads(path.read_bytes());c=next(x for x in blob['cases'] if x['name']=='L20.attn.hc_pre_norm')
 mem=blank()
 for addr,values in c['init']:mem.vm[addr:addr+len(values)]=np.asarray(values,np.float32).view(np.uint32)
 mem.cr[:,0]=c['cr_lo'];mem.cr[:,1]=c['cr_hi']
 label,addr,want,kind=c['checks'][0]
 if kind!='golden' or len(want)!=5120:raise ValueError('DS captured fullshape golden required')
 return emit(out,'DS1M',mem,c['ops'],addr,want,dict(target=c['name'],pickle_path=str(path.resolve()),
  pickle_sha256=sha(path),snapshots_sha256=blob['snapshots_sha256'],meta=c['meta']))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--qwen-source',type=Path,required=True)
 p.add_argument('--ds-cases',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False);C.set_c12(V);V.BCAST=7;V.RET=8
 cases={'Qwen8K':qwen(a.out,a.qwen_source),'DS1M':ds(a.out,a.ds_cases)}
 (a.out/'spec.json').write_text(json.dumps(dict(cases=cases),indent=2)+'\n')
 print(json.dumps({n:dict(nops=c['nops'],words=c['captured_output_words'],mismatches=c['captured_output_mismatches']) for n,c in cases.items()}))
if __name__=='__main__':main()
