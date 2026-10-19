#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
mkdir -p native
yosys -Q -T -p 'read_json retained/reimport.json; dfflibmap -liberty mapped/combined.lib; abc -liberty mapped/combined.lib; clean; write_json native/net.json; write_verilog native/qfd_dv_stream_controls.v; stat -liberty mapped/combined.lib' > native/map.log 2>&1
python3 - <<'PY'
import collections,json,pathlib,xml.etree.ElementTree as ET,re
p=pathlib.Path('native');d=json.loads((p/'net.json').read_text())['modules']['qfd_dv_stream_controls'];loads=collections.defaultdict(list);drivers={}
for n,c in d['cells'].items():
 assert not c['type'].startswith('$_'),(n,c['type'])
 for pn,bs in c['connections'].items():
  for b in bs:
   if not isinstance(b,int):continue
   if c['port_directions'][pn]=='input':loads[b].append((n,pn))
   else:drivers[b]=(n,pn)
clock=set(d['ports']['ck']['bits']);viols=[(b,len(ls)) for b,ls in loads.items() if b not in clock and len(ls)>32]
collapsed=[]
for b in set(loads)-clock:
 if b in drivers and d['cells'][drivers[b][0]]['type'].startswith(('INV','BUF')):continue
 pending=[b];seen=set();end=set()
 while pending:
  x=pending.pop()
  if x in seen:continue
  seen.add(x)
  for n,pn in loads.get(x,[]):
   c=d['cells'][n]
   if c['type'].startswith(('INV','BUF')):pending.extend(bb for op,bs in c['connections'].items() if c['port_directions'][op]=='output' for bb in bs)
   else:end.add((n,pn))
 collapsed.append((b,len(end)))
info={'cells':len(d['cells']),'masters':dict(collections.Counter(c['type'] for c in d['cells'].values())),'native_ff':sum(c['type'].startswith('DFF') for c in d['cells'].values()),'max_nonclock_load':max(len(ls) for b,ls in loads.items() if b not in clock),'max_transparent_ultimate_load':max(n for b,n in collapsed),'violations':viols,'transparent_violations':[(b,n) for b,n in collapsed if n>32],'qualified':False,'scope':'Actual ASAP7 TT primitive mapping. No physical timing/clock/geometry qualification. Boundary aliases require real predecessor copies.'}
p.joinpath('census.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info,indent=2));assert not viols and not info['transparent_violations']
PY
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_stream --Mdir native/obj candidate/tb_controls.sv native/qfd_dv_stream_controls.v candidate/models.v rtl/qwen_dv/qfd_dv_stream.sv > native/build.log 2>&1
native/obj/Vtb_stream > native/run.log 2>&1
grep 'STREAM_CONTROLS_EQ PASS' native/run.log
