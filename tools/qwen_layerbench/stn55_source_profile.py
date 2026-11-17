#!/usr/bin/env python3
"""Explicit candidate binding of the measured native CB55 station; no default adoption."""
import argparse,hashlib,json,re
from pathlib import Path

def bind(source,out,profile):
 source,out,profile=map(Path,(source,out,profile))
 if source.resolve()==out.resolve():raise ValueError('candidate output must differ from pinned source')
 text=source.read_text();pat=r'(?m)^(\s*)qfd_dv_s8_station_tail1\s+(u_r[0-7])\s*\('
 names=re.findall(pat,text)
 if sorted(n for _,n in names)!=['u_r'+str(i) for i in range(8)]:raise ValueError('actual8 native station calls required')
 replace=lambda m:m[1]+'qfd_dv_s8_station_tail1_cb55 #(.SKEW(55),.ENABLE_DELAY55(1)) '+m[2]+' ('
 new,n=re.subn(pat,replace,text);assert n==8
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(new)
 contract=dict(schema='opentallas.qwen.native-cb55-source-profile.v1',status='CANDIDATE_COMPONENT_PASS',default_adoption=False,
   source=str(source),source_sha256=hashlib.sha256(text.encode()).hexdigest(),output=str(out),output_sha256=hashlib.sha256(new.encode()).hexdigest(),
   stations=[n for _,n in names],selected_master='qfd_dv_s8_station_tail1_cb55',parameters=dict(SKEW=55,ENABLE_DELAY55=1),
   age_scope='Native near/far55 only; bound external transport must be composed separately.',source_receipt='results/rtl/qc_stn55_1116/qualification.json',physical_qualified=False)
 profile.parent.mkdir(parents=True,exist_ok=True);profile.write_text(json.dumps(contract,indent=2)+'\n');return contract

def main():
 p=argparse.ArgumentParser();p.add_argument('--flat-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--profile',type=Path,required=True);a=p.parse_args();r=bind(a.flat_source,a.out,a.profile);print(json.dumps(r))
if __name__=='__main__':main()
