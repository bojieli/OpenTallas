#!/usr/bin/env python3
"""Prepare default-OFF actual native XRT/XS/landing/CFG7/GB boundary experiment."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,sys

def main():
 p=argparse.ArgumentParser()
 for name in ('source','field','fixture','out'):p.add_argument('--'+name,required=True,type=Path)
 p.add_argument('--gb-source',type=Path)
 p.add_argument('--phases',type=int,default=2)
 p.add_argument('--period',type=int,default=512)
 p.add_argument('--phase-sequence',help='Explicit comma-separated current field phases; default repeats phase0')
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 sys.path[:0]=[str(a.source/'tools'),str(a.source/'tools/s81_dv'),str(a.source/'tools/s81_dv/layer_prog'),str(a.source/'tools/s81_static_control')]
 import lower_xs as L
 import xs_calendar as X
 import hdc_golden_v41 as G
 import numpy as np
 from pq_calendar import viamap
 field=json.loads((a.field/'field.json').read_text());assert field['frame']=='u_f_0L01'
 raw=a.field/'images.phase_local/_field'
 P=[int(v,16)for v in(raw/'spine_phase.hex').read_text().split()];S=[int(v,16)for v in(raw/'spine_stream.hex').read_text().split()]
 assert X.phase_word(P,0)['K']==5120 and X.phase_word(P,0)['bf']==0
 files=json.loads((a.fixture/'files.json').read_text());name='ops/attn.norm.scale.bin';meta=files[name]
 x=np.fromfile(a.fixture/name,dtype=np.dtype(meta['dtype'])).reshape(-1);assert len(x)==5120
 q,e=G.quant_fp8(x);codes={float(f):i for i,f in enumerate(G.E4M3)if np.isfinite(f)};qb=[codes[float(f)]if f!=0 else 0 for f in q]
 phase_sequence=[int(v)for v in a.phase_sequence.split(',')]if a.phase_sequence else [0]*a.phases
 assert phase_sequence and phase_sequence[0]==0 and all(0<=v<field['nphases']for v in phase_sequence)
 epoch=256;receipts={}
 for label,lead in [('old',0),('advance1',1)]:
  os.environ['OT_XS_Q_CPR']=str(lead)
  c=X.compile_pipeline(P,S,phase_sequence,0,a.period,cfg_lead=63,acc_gap=20,retire_gap=30)
  d=a.out/label;d.mkdir();L.xs_roms(raw,d)
  (d/'pq_calendar_action.viamap.hex').write_text(viamap([v&((1<<72)-1)for v in c['packed']]))
  (d/'pq_calendar_time.viamap.hex').write_text(viamap([v>>72 for v in c['packed']]))
  iss=dict(c['iss']);iss[X.GW_IT]=X.isd(gw=1,gw_fam=0,gw_par=0)
  events=[]
  for date,body in iss.items():
   payload=1|(2<<16)|(body<<26);flit=1|(4<<9)|(payload<<21)
   events.append((date+epoch-3,0,flit)) # actual measured XRT target2 pin stage=3, checked at run time
  for bt in range(80):
   data=0
   for half in range(2):
    block=2*bt+half;word=sum(int(v)<<(8*i)for i,v in enumerate(qb[32*block:32*block+32]));word|=(int(e[block])&1023)<<256;data|=word<<(266*half)
   events.append((200+bt+epoch,1,(bt<<1024)|data))
  (d/'producer.txt').write_text(''.join(f'{t} {k} {v:x}\n'for t,k,v in sorted(events)))
  for bank in range(7):
   src=a.field/'images'/f'u_f_0L01_c0_{bank}.viamap.hex';os.link(src,d/f'u_f_0L01.u_r0.u_c0_{bank}.viamap.hex')
  receipts[label]=dict(calendar_rows=c['cal_rows'],source_commands={str(t+epoch-3):f'{v:x}'for t,v in iss.items()},expected_issuer_pin={str(t+epoch):f'{v:040x}'for t,v in iss.items()},q_issue_advance=lead,phases=c['phases'],end=c['end_iter']+epoch+300)
 gb=a.gb_source or a.source/'rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb.sv';s=gb.read_text();body=s[s.index('    wire rst_n_e;'):s.index('    /* verilator lint_off PINCONNECTEMPTY */')]
 body=body.replace('    wire go_e_in;\n','').replace('    wire [1:0] go_tag_e_in;\n','')
 (a.out/'native_gb_capture.sv').write_text('module native_gb_capture #(parameter integer RSTP=1, GO_BOUNDARY=1)(input wire clk,rst_n,go,input wire[1:0]go_tag,output wire go_e_in,output wire[1:0]go_tag_e_in);\n'+body+'\nendmodule\n')
 report=dict(status='PREPARED_NATIVE_GO_BOUNDARY_EXPERIMENT',production_enabled=False,native_provider_qualified=False,under_test_flag_used=False,field=str(a.field),fixture_input=name,fixture_sha256=hashlib.sha256((a.fixture/name).read_bytes()).hexdigest(),native_gb_source_sha256=hashlib.sha256(gb.read_bytes()).hexdigest(),boundary_exact_source_logic=True,declarations_lifted_to_ports=True,programmes=receipts,scope='Actual dated producer and GO/TAG capture boundary; Q arithmetic/EF residency/production clocks remain unqualified',parallel_tag_candidate=dict(extra_reset_free_FF=4,tag_bits=2,depth=2,added_GO_CFG_XS_cycles=0),conditional_hold_candidate=dict(extra_reset_free_FF=2,tested_period_only=512))
 (a.out/'programme.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],flush=True)
if __name__=='__main__':main()
