#!/usr/bin/env python3
"""Exact source ABI and declared clock families; not physical qualification."""
import re,json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'rtl/qwen_sys/host_integrated_20261014';out={}
for module in ['qkd_host_root_integrated','qkd_host_rank_integrated','qkd_host_tp8_coordinator']:
 p=base/(module+'.sv');s=p.read_text();start=s.index('module ');header=s[start:s.index(');',start)];header=header[header.index(')(')+2:] if ')(' in header else header[header.index('(')+1:]
 ports=[];direction=None;width=''
 for part in header.split(','):
  part=re.sub(r'//[^\n]*','',part).strip();d=re.search(r'\b(input|output)\b',part)
  if d:direction=d.group(1);width='';part=part[d.end():]
  w=re.search(r'\[(\d+):(\d+)\]',part)
  if w:width=w.group()
  name=re.findall(r'\b\w+\b',re.sub(r'\[[^]]*\]',' ',part))[-1]
  n=int(width[1:-1].split(':')[0])-int(width[1:-1].split(':')[1])+1 if width else 1
  entry={'name':name,'direction':direction,'width':n}
  if name.startswith('ck_'):
   if name in ['ck_phy','ck_pad','ck_phy_rx_w','ck_phy_tx_r']:period=1043000
   elif name in ['ck_qm_host','ck_qm_ing_r','ck_qm_credit','ck_qm_done_w','ck_fence_host']:period=1000000
   elif name in ['ck_qm_ingest','ck_qm_bank','ck_qm_out']:period=1666668
   else:period=833334
   entry['period_fs']=period
   entry['clock_entries']=[name] if n==1 else [f'{name}[{i}]' for i in range(n)]
  ports.append(entry)
 assert len({p['name'] for p in ports})==len(ports)
 out[module]={'source':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'ports':ports,'clock_entry_count':sum(len(p.get('clock_entries',[])) for p in ports)}
print(json.dumps(out,indent=2))
