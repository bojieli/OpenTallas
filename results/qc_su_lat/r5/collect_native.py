#!/usr/bin/env python3
"""Collect the LAST native GRT clock record per named tap. Never reuse copied R3 summaries."""
import json,re,sys
from pathlib import Path
kit=Path(sys.argv[1]);text=(kit/'cts_grt.log').read_text();corners={}
for c,target in [('TT',250.0),('FF',202.5)]:
 taps={}
 for name,n,mean,lo,hi in re.findall(r'OT_MSCTS_TAP grt '+c+r' (\S+) n (\d+) mean ([-.\d]+) min ([-.\d]+) max ([-.\d]+)',text):
  taps[name]=(int(n),float(mean),float(lo),float(hi))
 if not taps:continue
 vals=list(taps.values());n=sum(x[0] for x in vals);mean=sum(n*v for n,v,_,_ in vals)/n
 window=max(x[1] for x in vals)-min(x[1] for x in vals)
 corners[c]=dict(n=n,mean_ps=mean,min_ps=min(x[2] for x in vals),max_ps=max(x[3] for x in vals),tap_mean_window_ps=window,target_ps=target,latency_target='PASS' if abs(mean-target)<=20 else 'FAIL',window='PASS' if window<=20 else 'FAIL')
out=dict(scope='GRT clock structural diagnostic only; native records rounded to0.1ps; NOT SIGNED; no independent number-check',source='cts_grt.log',corners=corners)
(kit/'r4_native_collection.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(out))
