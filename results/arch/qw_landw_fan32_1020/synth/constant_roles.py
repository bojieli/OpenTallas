import pathlib,glob,re,json,hashlib,gzip
records=[];constants={}
for fn in sorted(glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_TT_*')):
 p=pathlib.Path(fn);raw=p.read_bytes();s=gzip.decompress(raw).decode()if p.suffix=='.gz'else raw.decode();entries=[]
 for m in re.finditer(r'cell\s*\(\s*"?([^"\)]+)"?\s*\)\s*\{',s):
  pos=m.end();depth=1
  while depth and pos<len(s):
   if s[pos]=='{':depth+=1
   elif s[pos]=='}':depth-=1
   pos+=1
  body=s[m.end():pos-1];fs=re.findall(r'function\s*:\s*"([^"\n]+)"',body);name=m.group(1).strip()
  if fs and all(x.strip()in['0','1']for x in fs):constants[name]=dict(functions=fs,library=str(p),library_sha256=hashlib.sha256(raw).hexdigest(),cell_text_sha256=hashlib.sha256(body.encode()).hexdigest())
 records.append(dict(library=str(p),sha256=hashlib.sha256(raw).hexdigest()))
pathlib.Path('/out/lib_roles.json').write_text(json.dumps(dict(libraries=records,actual_literal_constant_cells=constants),indent=2)+'\n');print('ACTUAL_CONSTANT_ROLE_CELLS',constants)
