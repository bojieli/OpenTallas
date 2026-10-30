from pathlib import Path
import json,gzip,re,sys,hashlib
B=Path('/srv/opentallas-scratch2/claude/codex-qc-a0-2249/lib');S=Path('/srv/opentallas-scratch2/claude/codex-flow-s81phy-1030/tool_snapshot/tools/die_plan');sys.path.insert(0,str(S));import die_clock_128 as C
out={'scope':'Actual ASAP7 RVT NLDM tables for prebuild START+raw-reset relay data-path modeling, no physical timing result','corners':{}}
for c in ['TT','FF']:
 inv=B/f'asap7sc7p5t_INVBUF_RVT_{c}_nldm_220122.lib.gz';seq=B/f'asap7sc7p5t_SEQ_RVT_{c}_nldm_220123.lib';it=gzip.open(inv,'rt').read();st=seq.read_text();row={}
 for n,txt in [('DFFHQNx1_ASAP7_75t_R',st),('INVx8_ASAP7_75t_R',it),('BUFx8_ASAP7_75t_R',it),('INVx2_ASAP7_75t_R',it),('CKINVDCx16_ASAP7_75t_R',it)]:
  i=txt.index(f'cell ({n})');j=txt.find('cell (',i+10);blk=txt[i:j if j>=0 else len(txt)]
  row[n]={k:C._table(blk,k) for k in ['cell_rise','cell_fall','rise_transition','fall_transition']}
  if n.startswith('DFF'):
   row[n]['cap_ff']=float(re.search(r'pin \(D\).*?rise_capacitance\s*:\s*([0-9.]+)',blk,re.S)[1])
   row[n]['clock_cap_ff']=max(float(v) for v in re.findall(r'(?:rise|fall)_capacitance\s*:\s*([0-9.]+)',blk[blk.index('pin (CLK)'):blk.index('pin (D)')]))
  else:row[n]['cap_ff']=max(float(v) for v in re.findall(r'(?:rise|fall)_capacitance\s*:\s*([0-9.]+)',blk))
 out['corners'][c]={'cells':row,'sources':[dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [inv,seq]]}
print(json.dumps(out,indent=1))
