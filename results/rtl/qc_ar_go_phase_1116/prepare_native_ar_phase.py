#!/usr/bin/env python3
"""Select the optional same-port AR phase tap with one explicit12x16 table."""
import argparse,hashlib,json,re
from pathlib import Path

def bind(source,out,phase_profile,receipt):
 source,out,phase_profile,receipt=map(Path,(source,out,phase_profile,receipt))
 if source.resolve()==out.resolve():raise ValueError('candidate output must differ from retained source')
 p=json.loads(phase_profile.read_text());v=p if isinstance(p,list) else p['go_delay_edges']
 if len(v)!=12 or any(type(x)is not int or not 2<=x<=65535 for x in v):
  raise ValueError('explicit twelve integer receiver delays2..65535 required')
 value=sum(x<<(16*i) for i,x in enumerate(v));text=source.read_text()
 pat=r'(?m)^(\s*)qfd_dv_s8_tap_bounded\s+(u_tap)\s*\('
 if len(re.findall(pat,text))!=1:raise ValueError('exact one selected bounded tap call required; review changed source first')
 new,n=re.subn(pat,lambda m:m[1]+f"qfd_dv_s8_tap_phase #(.ENABLE(1),.HGD_TABLE(192'h{value:048x})) "+m[2]+' (',text)
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(new)
 r=dict(schema='opentallas.qwen.native-ar-phase-source.v1',default_adoption=False,
  source=str(source),source_sha256=hashlib.sha256(text.encode()).hexdigest(),output=str(out),output_sha256=hashlib.sha256(new.encode()).hexdigest(),
  phase_profile=str(phase_profile),phase_profile_sha256=hashlib.sha256(phase_profile.read_bytes()).hexdigest(),
  go_delay_edges=v,packed192=f'{value:048x}',selected_master='qfd_dv_s8_tap_phase',ENABLE=1,
  required_sources=['rtl/qwen_dv/s5/s8/qfd_dv_ar_go_phase.sv','existing selected qfd_dv_s8_tap_bounded and ot_rst_relay source'],
  boundary='HRreceiver beforeactualtap tophaseHRreceiver atactualtap; applied once; XPF originalvalid preserved',
  reset_release_edges=3,physical_qualified=False,installed=False)
 receipt.parent.mkdir(parents=True,exist_ok=True);receipt.write_text(json.dumps(r,indent=2)+'\n');return r

def main():
 a=argparse.ArgumentParser();a.add_argument('--flat-source',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--phase-profile',type=Path,required=True);a.add_argument('--receipt',type=Path,required=True);v=a.parse_args();bind(v.flat_source,v.out,v.phase_profile,v.receipt)
if __name__=='__main__':main()
