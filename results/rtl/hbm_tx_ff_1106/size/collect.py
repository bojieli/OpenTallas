from pathlib import Path
import json,re,collections,hashlib
p=Path('/srv/opentallas-scratch2/claude/codex-hbm-tx-ff-size');run=p/'run';base='asap7/hbc_ot_pdie_serdes_tx_ff_size/base'
j=json.loads((run/'logs'/base/'1_synth.json').read_text());v=(run/'results'/base/'1_2_yosys.v').read_text()
c=collections.Counter();q=[]
for typ,name,b in re.findall(r'^\s*(\w+)\s+(\\?\S+)\s*\((.*?)\);',v,re.S|re.M):
 if typ.startswith('DFF'):
  m=re.search(r'\.Q[N]?\((.*?)\)',b,re.S)
  if m:
   x=m[1].strip()
   a=re.search(r'g_ff.cq\[(\d+)\]',x)
   if a:c[a[1]]+=1;q.append(x)
# Netlist aliases may rename corresponding drivers; report literal Q map separately.
out={'schema':'opentallas.tx_ff_mapped_size.v1','source_encoder_sha256':hashlib.sha256((p/'rtl/ot_s81_kp4_enc_la.sv').read_bytes()).hexdigest(),'source_commit':'dc98564b80a','dimensions_um':[285.12,207.36],'core_dimensions_um':[276.48,198.72],'stdcell_count':j['synth__design__instance__count__stdcell'],'stdcell_area_um2':j['synth__design__instance__area__stdcell'],'stdutil':j['synth__design__instance__area__stdcell']/(276.48*198.72),'cq_mapped_qdriver_cells':dict(c),'max_cell_count':150000,'max_stdutil':.45,'physical_status':'NOT RUN (synth estimate only)'}
out['size_admission_pass']=out['stdcell_count']<=150000 and out['stdutil']<=.45
(p/'mapped_size.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
