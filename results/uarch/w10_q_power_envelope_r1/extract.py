import gzip,hashlib,json,re
from pathlib import Path
base=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM'); records={}
for corner in ['SS','TT','FF']:
 for group,names in [('SIMPLE',['NAND2x1_ASAP7_75t_R']),('INVBUF',['BUFx12_ASAP7_75t_R']),('SEQ',['DFFASRHQNx1_ASAP7_75t_R','ICGx1_ASAP7_75t_R'])]:
  date={'SIMPLE':'211120','INVBUF':'220122','SEQ':'220123'}[group]
  path=base/f'asap7sc7p5t_{group}_RVT_{corner}_nldm_{date}.lib';path=path if path.exists() else Path(str(path)+'.gz')
  raw=path.read_bytes();s=gzip.decompress(raw).decode() if path.suffix=='.gz' else raw.decode()
  chunks=[]
  for name in names:
   m=re.search(r'cell\s*\('+name+r'\)',s);assert m,name
   start=s.index('{',m.start());i=start+1;depth=1
   while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
   chunks.append(s[m.start():i])
  out=Path('/out')/f'{group}_{corner}.cells.lib';out.write_text('\n'.join(chunks)+'\n')
  records[out.name]={'source_path':str(path),'source_raw_sha256':hashlib.sha256(raw).hexdigest(),'source_uncompressed_sha256':hashlib.sha256(s.encode()).hexdigest(),'selected_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'nom_voltage':re.search(r'nom_voltage\s*:\s*([^;]+)',s)[1].strip(),'units':{'time':'ps','capacitance':'fF','current':'mA','voltage':'V','leakage':'pW'}}
Path('/out/inputs.json').write_text(json.dumps(records,indent=2)+'\n')
