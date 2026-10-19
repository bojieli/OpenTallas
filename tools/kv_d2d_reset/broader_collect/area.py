import pathlib,re,gzip,json,collections,hashlib
r=pathlib.Path(__file__).parent;areas={};libs={}
for p in (r/'libs').glob('*'):
 s=gzip.decompress(p.read_bytes()).decode()if p.suffix=='.gz'else p.read_text();libs[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
 for m in re.finditer(r'cell\s*\(\s*([^\s)]+)\s*\)\s*\{(.*?)(?=\n\s*cell\s*\(|\Z)',s,re.S):
  a=re.search(r'\barea\s*:\s*([\d.]+)',m[2]);
  if a:areas[m[1]]=float(a[1])
for mode,top in [('r7w','qkd_d2d_static_safe24'),('ovl','qkd_d2d_static_ovl_safe24')]:
 j=json.load(open(r/f'{mode}.native.json'))['modules'][top];count=collections.Counter(x['type']for x in j['cells'].values());missing={t:n for t,n in count.items()if t not in areas and not t.startswith('ot_sram_')};assert not missing,missing
 out=dict(libs=libs,inventory=count,standard_cell_area_um2=sum(areas[t]*n for t,n in count.items()if t in areas),macro_count=sum(n for t,n in count.items()if t.startswith('ot_sram_')),ff_clocks=sum(n for t,n in count.items()if t.startswith('DFF')),qualified=False)
 (r/f'{mode}.area.json').write_text(json.dumps(out,indent=2)+'\n');print(mode,out)
