import pathlib,json,gzip,re,hashlib
out=[]
for corner in ['TT','FF']:
 p=pathlib.Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')/('asap7sc7p5t_SIMPLE_RVT_'+corner+'_nldm_211120.lib.gz');s=gzip.decompress(p.read_bytes()).decode();m=re.search(r'cell\s*\(\s*TIELOx1_ASAP7_75t_R\s*\)\s*\{',s);assert m
 i=m.end();j=i;depth=1
 while depth:
  if s[j]=='{':depth+=1
  elif s[j]=='}':depth-=1
  j+=1
 cell=s[m.start():j];assert re.search(r'pin\s*\(\s*L\s*\)',cell);assert re.search(r'function\s*:\s*"0"',cell)
 out.append({'corner':corner,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'cell':cell,'function':'0','pin':'L'})
pathlib.Path('/audit/tielo_actual_liberty.json').write_text(json.dumps(out,indent=2)+'\n');print('TIELO_ACTUAL_LIBERTY_TT_FF_FUNCTION0_PASS')
