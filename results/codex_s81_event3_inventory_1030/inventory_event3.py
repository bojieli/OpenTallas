"""Extract actual event3 emitted SID/XR literals, without graph elaboration."""
from pathlib import Path
import hashlib,json,re
D=Path('/srv/opentallas-scratch2/claude/die-s81-34/ev3bind/out/rtl')
O=Path('/srv/opentallas-scratch2/claude/codex-s81-inventory-1030');O.mkdir(exist_ok=True)
top=D/'s81_bound_top.sv';ts=top.read_text()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def params(s):return dict(re.findall(r'\.(\w+)\(([^()]*)\)',s))
def val(s):
 s=s.replace('_','').strip();m=re.fullmatch(r"(\d+)'([bhd])([0-9a-fA-F]+)",s)
 return int(m[3],{'b':2,'h':16,'d':10}[m[2]])if m else int(s,0)
rows=[];sources={str(top):sha(top)}
for f in sorted(D.glob('s81p_dsdv_slice_*_C__t*.sv')):
 text=f.read_text()
 if 'PDSK'not in text:continue
 mod=re.search(r'^module (\w+)',text,re.M)[1]
 xr=list(re.finditer(r'^\s*(ot_s81sl_xrt[13])\s+#\((.*?)\)\s+(\w+)\s*\((.*?)^\s*\);',text,re.M|re.S))
 assert len(xr)==1,(f,len(xr));xr=xr[0];xp=params(xr[2]);assert all(k in xp for k in ['PDSK','FACE_LAND','FOREG','QDELAYS'])
 sidexpr=re.search(r'\.sid\(([^)]+)\)',xr[4])[1];sidname=re.fullmatch(r'(\w+)\[3:0\]',sidexpr)[1]
 defaults=dict(re.findall(r'parameter\s+\[3:0\]\s+(\w+)\s*=\s*([^,\n]+)',text))
 instances=list(re.finditer(r'^\s+'+re.escape(mod)+r'(?:\s+#\((.*?)\))?\s+(\w+)\s*\(',ts,re.M))
 assert instances,(mod,'no topinstance')
 for inst in instances:
  override=params(inst[1]or'');sidlit=override.get(sidname,defaults[sidname]).strip();sid=val(sidlit)
  part=inst[2];assert re.fullmatch(r's_[0-7][SN]_C',part),part
  allsid={n:override.get(n,v).strip()for n,v in defaults.items()if n.endswith('_sid')};assert all(val(v)==sid for v in allsid.values())
  before=text[:xr.start()];canon=re.findall(r'// as-built (\S+)',before)[-1]
  rows.append(dict(logical_slice='u_'+part[:-2],part=part,sid=sid,sid_parameter=sidname,sid_expression=sidexpr,sid_raw_literal=sidlit,sid_top_override=override.get(sidname),all_sid_literals=allsid,xr_instance=xr[3],xr_master=xr[1],canonical_emitted_leaf_path=canon,params_raw=xp,params_integer={k:val(v)for k,v in xp.items()},wrapper_module=mod,wrapper_file=str(f),wrapper_sha256=sha(f)))
 sources[str(f)]=sha(f)
rows.sort(key=lambda r:r['sid']);print('EXTRACTED',len(rows),[(r['part'],r['sid'])for r in rows]);assert len(rows)==16;assert [r['sid']for r in rows]==list(range(16));assert len({r['logical_slice']for r in rows})==16
x=dict(schema='opentallas.s81.event3_emitted_sid_xr_inventory.v1',scope='ACTUAL_EMITTED_SOURCE_LITERALS_ONLY_NOT_FULL_GRAPH_OR_TRANSPORT_AGES',source_bind='die-s81-34/ev3bind BIND_RC0 event3b19',source_top=str(top),source_top_sha256=sha(top),source_files_sha256=sources,slices=rows,not_claimed=['global transport/START dates','oldc092/062ef0 cohort equality','wholeRTL/physical/G5 qualification'])
x['source_view_sha256']=hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
(O/'inventory.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(dict(count=len(rows),sid=[r['sid']for r in rows],source_top_sha256=x['source_top_sha256'],source_view_sha256=x['source_view_sha256'],xr_masters=sorted({r['xr_master']for r in rows})),indent=2))
