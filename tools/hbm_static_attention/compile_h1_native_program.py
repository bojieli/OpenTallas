#!/usr/bin/env python3
"""Source-bound H1 target49 programme for exact frozen G25 records."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(Path(__file__).resolve().parent))
from hgi_sim.records import decode_one
from physical_calendar import resident_event_frames,outer_record
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();payload=a.source.read_bytes();assert hashlib.sha256(payload).hexdigest()=='43c1652f3c2348fd711c770c4769e041caa51a63209c34670c9993ccbbbe4d1d';source=json.loads(payload);a.out.mkdir(parents=True,exist_ok=True)
records=[r for layer in source['layers'] for r in layer['records']];profiles,config=resident_event_frames();(a.out/'config.hex').write_text(''.join(f'{x:056x}\n' for x in config+[0]*(512-len(config))))
proof=[]
for profile,(ordinal,op,T) in enumerate(((22,'QK',128),(26,'PV',128),(316,'QK',640),(322,'PV',640))):
 raw=bytes.fromhex(records[ordinal]['hex']);r,_=decode_one(raw,0);assert r.encode()==raw
 assert r.unit=='ATT' and r.op==op and r.param==369 and (r.param&15)==1,(ordinal,r)
 A,O=r.desc['A'],r.desc['O'];assert A.space==O.space=='VM' and A.fmt==O.fmt=='FP32';assert A.n==(512 if op=='QK' else T) and O.n==(T if op=='QK' else 512)
 assert A.base==(53376 if op=='QK' else 55296) and O.base==(53888 if op=='QK' else 56128)
 words=outer_record(profile,profile//2,query_base_sector=53376//8,P_base_sector=55296//8,P_head_stride_sectors=T//8)
 # Inactive fill opcodes explicitly carry no source address; hardware executes
 # actual zero SRAM writes on these slots and emits no VM request.
 words=[w&~(0xffff<<12) if (w&15)==4 and ((w>>5)&15)!=0 else w for w in words]
 (a.out/f'outer{profile}.hex').write_text(''.join(f'{w:056x}\n' for w in words+[0]*(256-len(words))))
 active=8 if op=='QK' else T//64;sw=[0]*900
 for cycle in range(343,343+active):sw[cycle]=255<<80 # actual SW202 rslot_v; RG0 selectors arezero
 (a.out/f'sw{profile}.hex').write_text(''.join(f'{w:056x}\n' for w in sw))
 s=profiles[profile];(a.out/f'event{profile}.hex').write_text(''.join(f'{w:02x}\n' for w in s['words']+[0]*(512-len(s['words']))))
 proof.append({'profile':profile,'ordinal':ordinal,'layer':0 if T==128 else 2,'record_sha256':hashlib.sha256(raw).hexdigest(),'op':op,'param':r.param,'logical_heads':1,'T':T,'A':vars(A),'O':vars(O),'outer_words':len(words),'active_VM_bursts':active,'total_fill_slots':128 if op=='QK' else 16*T//64})
record={'source_sha256':hashlib.sha256(payload).hexdigest(),'source_profile':'Exact G25 rank0 L0T128/L2T640, no descriptor relocation/expansion','profiles':proof,'hardware':'FullH16D512TD32NL2, inactive local slots realzero initialized','component_port':'ActualSID0 SW202 NC7/RG6/WG2, exclusive barebankRG0/WG0; no global sharedslot or SWLG14/NEtransport grant','qualification':False,'remaining':'Actualhost source proof, completearithmetic producer and wholekernel calendar/physical binding'}
(a.out/'source_lowering.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS exactG25 decoded/reencoded H1 QK/PV target49 programme T128/T640')
