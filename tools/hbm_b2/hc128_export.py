#!/usr/bin/env python3
"""Export a physical master and the exact current elaborated module closure."""
import argparse,json,hashlib,subprocess
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--netlist',type=Path,required=True);ap.add_argument('--master',required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--source-commit',required=True);ap.add_argument('--blackbox',action='append',default=[]);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
j=json.loads(a.netlist.read_text());mods=j['modules']
for n in a.blackbox:
 m=mods[n];m['attributes']={'blackbox':'1'};m['cells']={};m['netnames']={};m.pop('memories',None)
seen=set();todo=[a.master]
while todo:
 n=todo.pop()
 if n in seen:continue
 assert n in mods,n
 seen.add(n);todo.extend(c['type'] for c in mods[n].get('cells',{}).values() if not c['type'].startswith('$') and c['type'] not in seen)
pruned={**j,'modules':{n:mods[n] for n in sorted(seen)}};jp=a.out/(a.master+'.json');jp.write_text(json.dumps(pruned));sv=a.out/(a.master+'.sv');ys=a.out/(a.master+'.ys');ys.write_text(f'read_json {jp.resolve()}\nwrite_verilog -noattr {sv.resolve()}\n');subprocess.run([str(Path.home()/'.local/opentallas-tools/bin/yosys'),'-ql',str(a.out/(a.master+'.log')),'-s',str(ys)],check=True)
receipt=dict(source_commit=a.source_commit,input_sha256=hashlib.sha256(a.netlist.read_bytes()).hexdigest(),master=a.master,ports={n:(p['direction'],len(p['bits'])) for n,p in mods[a.master]['ports'].items()},closure_modules=sorted(seen),verilog_sha256=hashlib.sha256(sv.read_bytes()).hexdigest(),qualification='EXACT_CUT_NOT_ROUTED',added_cycles=0,boundary_masters=a.blackbox)
(a.out/(a.master+'_receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='closure_modules'}))
