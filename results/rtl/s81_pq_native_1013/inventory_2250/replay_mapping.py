import pathlib,subprocess,gzip,re
r=pathlib.Path('/var/tmp/s81rom2250/src');out=r/'results/rtl/s81_pq_native_1013/inventory_2250'
libs=pathlib.Path('/var/tmp/s81rom2250/libs');libs.mkdir(exist_ok=True)
subprocess.run(['docker','run','--rm','-v',str(libs)+':/out','openroad/orfs:latest','bash','-lc','cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT* /out/'],check=True)
blocks=[]; templates={}
for p in sorted(libs.glob('asap7*')):
 s=gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text()
 for m in re.finditer(r'\b(?:cell|lu_table_template|power_lut_template)\s*\([^)]*\)\s*\{',s):
  start=m.start();i=m.end();n=1
  while n:
   if s[i]=='{':n+=1
   if s[i]=='}':n-=1
   i+=1
  if m.group(0).startswith("cell"): blocks.append(s[start:i])
  else: templates[m.group(0)]=s[start:i]
lib=libs/'merged.lib';lib.write_text('library (s81_inventory_tt) {\ntime_unit:"1ps"; capacitive_load_unit (1,ff); voltage_unit:"1V"; current_unit:"1mA";\n'+ '\n'.join(templates.values())+'\n'+'\n'.join(blocks)+'\n}\n')
genlib=libs/'cells.genlib'; gates=[]
for b in blocks:
 if re.search(r'\b(ff|latch)\s*\(',b):continue
 name=re.search(r'cell\s*\(\s*"?([^"\s)]+)',b)[1]
 area=re.search(r'\barea\s*:\s*([\d.eE+-]+)',b)
 fn=re.search(r'function\s*:\s*"([^"]+)"',b)
 if not area or not fn:continue
 # All combinational ASAP7 TT cells in this inventory have one logic output.
 # The lib's function-bearing output is QN/Y/X; find enclosing pin by latest pin before function.
 ports=list(re.finditer(r'pin\s*\(\s*"?([^"\s)]+)',b[:fn.start()]))
 if not ports:continue
 output=ports[-1][1]
 gates.append(f'GATE {name} {area[1]} {output}={fn[1]};\nPIN * UNKNOWN 1 999 1 1 1 1')
genlib.write_text('\n'.join(gates)+'\n')
for p in out.glob('*.json'):
 if p.stem.endswith('_mapped') or p.stem.endswith('_receipt') or p.name=='macro_receipt.json':continue
 top=p.stem;s=f'read_json {p}\ndffunmap\ndfflibmap -liberty {lib}\nabc -liberty {lib}\nstat -liberty {lib}\nwrite_json {out}/{top}_mapped.json\n'
 (out/f'{top}_mapped.ys').write_text(s)
 with (out/f'{top}_mapped.log').open('w') as log:rc=subprocess.run(['docker','run','--rm','-v','/var/tmp/s81rom2250:/var/tmp/s81rom2250','openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys','-s',str(out/f'{top}_mapped.ys')],stdout=log,stderr=subprocess.STDOUT).returncode
 print(top,'maprc',rc,flush=True);print((out/f'{top}_mapped.log').read_text()[-1100:],flush=True)
