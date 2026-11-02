from pathlib import Path
import re,csv,json,hashlib
R=Path.cwd();actual={};roots={}
for r in csv.DictReader(open(R/'graph.tsv'),delimiter='\t'):
 if r['kind']=='BTERM'and r['io']=='INPUT':roots[r['net']]=r['owner']
 if r['kind']=='ITERM'and r['mastertype']=='BLOCK':
  c=actual.setdefault(r['owner'],dict(master=r['master'],placement=r['placement'],xy_dbu=[int(r['x']),int(r['y'])],clock_pins=[]))
  if r['signal']=='CLOCK':c['clock_pins'].append(dict(pin=r['pin'],net=r['net'],io=r['io']))
s=(R/'macro_placement.tcl').read_text();planned=re.findall(r'^\s*\{([^{}]+)\}\s+(\S+)\s+([\d.]+)\s+([\d.]+)\s+(\w+)\s*$',s,re.M);assert len(planned)==len(actual)==32,(len(planned),len(actual))
assert len({r[0]for r in planned})==32
bycanonical={}
for n,c in actual.items():
 canonical=n.replace('.u_b.genblk1.genblk1.g_m11.u_m','.u_b.g_m11.u_m');assert canonical!=n,(n,'unexpected native shape')
 assert canonical not in bycanonical,(canonical,'ambiguous actual native macro binding');bycanonical[canonical]=(n,c)
assert set(bycanonical)=={r[0]for r in planned},'incomplete native/planned bank identity'
rows=[];patched=s
for old,master,x,y,orient in planned:
 n,c=bycanonical[old];assert c['master']==master;assert len(c['clock_pins'])==1 and c['clock_pins'][0]['io']=='INPUT'
 clk=c['clock_pins'][0];assert clk['net']in roots,('unrooted native SRAM clock',n,clk);clk['root_input_bterm']=roots[clk['net']]
 rows.append(dict(planned_name=old,actual_native_name=n,master=master,planned_xy_um=[float(x),float(y)],planned_orient=orient,source_native_placement=c['placement'],source_native_xy_dbu=c['xy_dbu'],native_clock=clk))
 assert patched.count('{'+old+'}')==1
 patched=patched.replace('{'+old+'}','{'+n+'}')
# Prove only braced instance-name tokens changed: restore names and compare bytes.
restored=patched
for row in rows:restored=restored.replace('{'+row['actual_native_name']+'}','{'+row['planned_name']+'}')
assert restored==s
(R/'macro_placement_native_names.tcl').write_text(patched)
res=dict(status='PASS_UNIQUE_NATIVE32_PLANNED32_NAMES_ONLY',source_odb_sha256=(R/'source_odb.sha256').read_text().split()[0],original_macro_placement_sha256=hashlib.sha256(s.encode()).hexdigest(),corrected_macro_placement_sha256=hashlib.sha256(patched.encode()).hexdigest(),actual_native_macros=len(actual),planned_macros=len(planned),unique_bijection=True,all_masters_match=True,all_xy_orient_preserved=True,only_name_tokens_changed=True,canonical_rule='exact .u_b.genblk1.genblk1.g_m11.u_m -> .u_b.g_m11.u_m after actual native ODB enumeration; rejects all other shapes/duplicates/incomplete sets',rows=rows,scope='read-only saved native synth ODB and names-only proposed macro placement; no PLACE or source change')
(R/'native_macro_binding.json').write_text(json.dumps(res,indent=2)+'\n');print(res['status'],len(rows))
