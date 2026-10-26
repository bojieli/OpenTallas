#!/usr/bin/env python3
"""Minimum q3 TOPK programme, actual TP192/ROWS256/VM_RT81 core; G4/N1/K1.
Four actual VM pairs traverse qslots to TKM. All delays are static schedule
parameters, never reactive waits; repeated idle rows use the native issuer loop.
This is a mechanism vehicle, not a production-shape throughput qualification.
"""
import argparse, json, pathlib, sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'hbm_coll_static'))
import argmax_rows as A

def compile_rows(start=84, slot=94, done=608, halt=620, mutant=None, write=None):
 A.set_rows(256);A.LIDS.clear()
 fs=json.loads(A.LAYOUT.read_text())['fields']
 config=dict(tkm_cfg_n=1,tkm_cfg_k=1,tkm_cfg_nout=1,tkm_cfg_g=4,tkm_cfg_gbase=0,tkm_cfg_pf=1,tkm_cfg_obase=64,tkm_cfg_rbase=128,tkm_cfg_has_r=0)
 def fields(c):
  d=dict(config)
  if c==0:
   d['vm_rq']=sum(((1<<16)|0x400)<<(17*b) for b in range(8))
   d['vm_pair_select']=sum((((2*j+1)<<3)|(2*j))<<(6*j) for j in range(4))
   d['vm_meta']=sum(((1<<32)|(0xff<<24)|(j<<16)|j)<<(33*j) for j in range(4))
  if c==start:d['tkm_start']=1
  if c==91:d['capture_slot']=0xf<<5
  if c==92:
   d['sink_slot']=0xf<<11;d['sink_select']=sum((5+j)<<(4*(11+j)) for j in range(4))
  if c==slot:d['tkm_del_slot']=0xf
  if c==done:d['tkm_done_slot']=1
  if write is not None:
   if c==write:d['vm_ingress_slot']=1<<4
   if c==write+1:d.update(vm_slot_valid=1,vm_slot_owner=4)
   if c==write+2:d.update(vm_slot_valid=2,vm_slot_owner=9<<4)
  if mutant=='no_start':d.pop('tkm_start',None)
  return d
 def pack(d):
  out=0
  for k,v in d.items():
   f=fs[k];assert 0<=v<1<<f['width'];out|=v<<f['lsb']
  return out
 seq=[pack(fields(c)) for c in range(halt)];words=[];meta=[];c=0
 while c<halt:
  end=c+1
  while end<halt and seq[end]==seq[c]:end+=1
  pc=len(words);words.append(seq[c]);n=end-c
  meta.append(A.enc_meta(pc+1,pc,n,pc) if n>1 else A.enc_meta(pc+1))
  c=end
 words.append(pack(config));meta.append(A.enc_meta(len(meta),halt=1))
 assert len(words)<=256
 A.unroll(words,meta,fs,fields,halt)
 return words,meta,dict(rows=len(words),halt=halt,tkm_start_instr=start,tkm_slot_instr=slot,tkm_done_instr=done,profile='NLINK3 TP192 ROWS256 VM_RT81 G4 N1 K1',qualification='MECHANISM_ONLY',predicted_path_age=271,vm_writer_ingress_instr=write,vm_return_calendar='EXPLICIT' if write is not None else 'NOT_INSTALLED')

def main():
 p=argparse.ArgumentParser();p.add_argument('out',type=pathlib.Path);p.add_argument('--start',type=int,default=84);p.add_argument('--slot',type=int,default=94);p.add_argument('--done',type=int,default=608);p.add_argument('--halt',type=int,default=620);p.add_argument('--mutant',choices=['no_start']);p.add_argument('--write',type=int,help='Measured writer ingress instruction; low/high bank reservations follow at+1/+2');a=p.parse_args()
 w,m,info=compile_rows(a.start,a.slot,a.done,a.halt,a.mutant,a.write);a.out.mkdir(parents=True,exist_ok=False)
 (a.out/'d0q0.rows.hex').write_text(''.join(f'{x:0384x}\n' for x in w));(a.out/'d0q0.meta.hex').write_text(''.join(f'{x:016x}\n' for x in m));(a.out/'manifest.json').write_text(json.dumps(info,indent=2)+'\n');print('TOPK_ROWS PASS',info)
if __name__=='__main__':main()
