import pathlib,gzip,re,sys
flow=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);cells=[];templates={}
for p in sorted(flow.glob('*RVT*TT*.lib*')):
 s=gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text()
 for m in re.finditer(r'\b(?:cell|lu_table_template|power_lut_template)\s*\(',s):
  start=m.start();i=s.index('{',m.end());depth=1;j=i+1;quoted=False;esc=False
  while depth:
   c=s[j]
   if esc:esc=False
   elif c=='\\':esc=True
   elif c=='"':quoted=not quoted
   elif not quoted:
    if c=='{':depth+=1
    elif c=='}':depth-=1
   j+=1
  block=s[start:j]
  if block.startswith('cell'):cells.append(block)
  else:templates.setdefault(block[:block.index('{')].strip(),block)
out.write_text('library (btab_safe_cells) {\n delay_model : table_lookup;\n time_unit : "1ps";\n capacitive_load_unit (1,ff);\n'+'\n'.join(templates.values())+'\n'+'\n'.join(cells)+'\n}\n')
print('merged',len(cells),'cells')
