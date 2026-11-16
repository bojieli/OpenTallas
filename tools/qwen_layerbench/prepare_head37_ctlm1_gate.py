#!/usr/bin/env python3
"""Prepare current frozen FQREG CALREG1 controller-only stage37 source gate."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--frontend',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 def show(p):
  q=a.repo/p
  return q.read_text()if q.is_file()else subprocess.run(['git','-C',str(a.repo),'show','HEAD:'+p],capture_output=True,check=True).stdout.decode()
 a.out.mkdir(parents=True,exist_ok=False);d=a.out/'input';d.mkdir();rom=a.out/'rom';rom.mkdir();base=a.frontend/'baseline'
 cal=base/'rtl/qwen_dv/headprep13/frontend_fqreg/qfd_dv_cmd_cal_mu_fqreg.sv';h=cal.read_text();assert 'parameter integer CALREG = 1 'in h and 'parameter integer HEAD_STAGE37 = 0,'in h
 (d/'original.sv').write_text(h[:h.index('endmodule')+len('endmodule')]+'\n')
 successor=h.replace('module qfd_dv_cmd_cal_mu #(','module qfd_dv_cmd_cal_mu_head37 #(',1)
 assert successor.replace('module qfd_dv_cmd_cal_mu_head37 #(','module qfd_dv_cmd_cal_mu #(',1)==h
 (d/'successor.sv').write_text(successor)
 for p in ['rtl/qwen_dv/qfd_dv_calendar_rom.sv','rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv','rtl/qwen_sys/program_receiver_20261014/qkd_program_pw_observer_p.sv','rtl/lib/ot_ks_add.sv','physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v','physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v']:shutil.copy(base/p,d/Path(p).name)
 sys.path.insert(0,str(a.repo/'tools/qwen_layerbench'));import programme_store as P
 words=[0]*4096
 for stage in range(1,38):i=4*(stage-1);words[i//4]|=((8<<116)|(14<<112)|(stage<<4)|9)<<(128*(i%4))
 for lane in (0,1):(rom/f'calendar_m{lane}.viamap.hex').write_text(''.join(f'{v:0532x}\n'for v in P.physical_rows(words,lane)))
 dw=[0x43414c5200000091,1,1,1,1,0,0x4d43000000000000,0];(a.out/'dw.hex').write_text(''.join(f'{v:016x}\n'for v in dw))
 tb=show('tools/qwen_layerbench/tb_head_ctlm37.sv').replace('.CALREG(7)','.CALREG(1)').replace("10'(868+4*(s-1))","10'(4*(s-1))").replace('first=1012','first=144').replace('nent1013 sharedrange1012','nent145 sharedrange144 componentLOCAL4coupon')
 needle='integer s,u,k,idx,existing=1,active=0,requests=0,headrequests=0,cycles=0;';assert needle in tb
 tb=tb.replace(needle,needle+'''
integer receiver_edge=0,cal_start_edge=-1;
reg[8:0]treq=0;
always @(posedge ck or negedge rst_n)if(!rst_n)treq<=0;else treq<={load[2],ts[2],tu[2]};
always @(posedge ck)begin
 receiver_edge=receiver_edge+1;
 if(start)cal_start_edge=receiver_edge;
 if(active&&!existing&&load[2])$display("CALREG1_LOAD user=%0d stage=%0d start=%0d load=%0d delta=%0d",tu[2],ts[2],cal_start_edge,receiver_edge,receiver_edge-cal_start_edge);
 if(active&&!existing&&treq[8])begin
  if(treq[7:2]!=37||treq[1:0]!=2'(u))$fatal(1,"GI_REQUEST_OWNER");
  $display("CALREG1_GI user=%0d stage=%0d start=%0d treq=%0d delta=%0d",treq[1:0],treq[7:2],cal_start_edge,receiver_edge,receiver_edge-cal_start_edge);
 end
end
''')
 needle=' $display("NATIVE_CTLM37_PASS';at=tb.index(needle)
 tb=tb.replace('"CTLM_EXISTING_LOAD_FAULT"','"CTLM_EXISTING_LOAD_FAULT s%0d u%0d fault%b fc%h/%h/%h",s,u,fault,fc[0],fc[1],fc[2]')
 at=tb.index(needle)
 tb=tb[:at]+''' active=0;stage=38;first=144;start=1;@(negedge ck);start=0;repeat(64)@(negedge ck);
 $display("CALREG1_STAGE38 fault=%b code=%h",fault[2],fc[2]);
 if(!fault[2]||!fc[2][0])$fatal(1,"CTLM_ON_ACCEPTED_38");
'''+tb[at:]
 (d/'tb_head_ctlm37.sv').write_text(tb);(a.out/'source.f').write_text(''.join('input/'+p.name+'\n'for p in sorted(d.iterdir())))
 (a.out/'run_gate.sh').write_text(show('tools/qwen_layerbench/run_head_ctlm_gate.sh'))
 rec={'status':'SOURCE_READY_NOT_LAUNCHED','scope':'three actual frozen FQREG controller instances, stage1..36 LOCAL4 coupon and stage37 opt-in; not global calendar','CALREG':1,'source_CALREG7_retagged':False,'source_files':len(list(d.iterdir())),'source_bytes':sum(p.stat().st_size for p in d.iterdir()),'original_fqreg_sha256':hashlib.sha256(cal.read_bytes()).hexdigest(),'frontend_receipt_sha256':hashlib.sha256((a.frontend/'receipt.json').read_bytes()).hexdigest(),'controls':['144 existing-stage requests lockstep','default-off37 rejects','opt-in38 rejects','MUT_USER catches wrongowner'],'source_activation':False}
 (a.out/'preparation.json').write_text(json.dumps(rec,indent=2)+'\n');(a.out/'packet.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(a.out))+'\n'for p in sorted(a.out.rglob('*'))if p.is_file()));print(json.dumps(rec))
if __name__=='__main__':main()
