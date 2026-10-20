import pathlib,json,re,hashlib
D=pathlib.Path('/srv/opentallas-scratch/claude/s81-mu5/case_mu5k/views');rows=[]
for p in sorted(D.rglob('*rlyh*.lib')):
 text=p.read_text();m=re.search(r'\bpin\s*\(\s*"?ck_o"?\s*\)\s*\{',text)
 if not m:rows.append(dict(path=str(p),error='missing ck_o'));continue
 dep=0
 for i in range(m.end()-1,len(text)):
  dep+=(text[i]=='{')-(text[i]=='}')
  if dep==0:break
 group=text[m.start():i+1];rel=re.findall(r'related_pin\s*:\s*"([^"]+)"',group);sense=re.findall(r'timing_sense\s*:\s*(\w+)',group);typ=re.findall(r'timing_type\s*:\s*(\w+)',group)
 rows.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),related_pin=rel,timing_sense=sense,timing_type=typ,truthful_halfcycle=(rel==['ck'] and sense==['negative_unate'] and typ==['combinational']),ck_o_group=group))
O=pathlib.Path('/srv/opentallas-scratch/claude/codex-s81-mu6-realctrl-1020/bound_halfclock_family.json');O.write_text(json.dumps(dict(source_case=str(D.parent),die_source='804d68ef69adab4aca463317d74bbed100da330d',expected='actual h relay ck_o=~ck, single kept inverter, generated clock divide1 invert; all loaded corners require ck to ck_o negative_unate native combinational transfer',loaded_libs=rows),indent=2));print(len(rows),sum(x.get('truthful_halfcycle',False) for x in rows),'truthful',sorted(set(tuple(x.get('related_pin',[])) for x in rows)))
