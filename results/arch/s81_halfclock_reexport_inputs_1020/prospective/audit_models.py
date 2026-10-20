from pathlib import Path
import tarfile,json,re,hashlib,math
B=Path(__file__).parent;archive=B/'evidence/private_model_evidence.tar.gz';t=tarfile.open(archive);names=set(t.getnames())
def raw(p):return t.extractfile(p).read()
def group(s,pin):
 ms=list(re.finditer(r'\bpin\s*\(\s*"?'+re.escape(pin)+r'"?\s*\)\s*\{',s));assert len(ms)==1;start=ms[0].start();depth=0;quote=False;esc=False
 for i in range(ms[0].end()-1,len(s)):
  c=s[i]
  if esc:esc=False
  elif c=='\\' and quote:esc=True
  elif c=='"':quote=not quote
  elif not quote:
   depth+=(c=='{')-(c=='}')
   if depth==0:return start,i+1
 raise ValueError('unterminated')
rows=[]
for name in sorted(n for n in names if n.endswith('/views/abstract.json')):
 d=json.loads(raw(name));assert d['ok'] and d['checked'];base=name.rsplit('/',1)[0];bycorner={}
 for c in ['ss','ff','tt']:
  fc=d['forwarded_clock'][c];assert fc['timing_sense']=='negative_unate' and fc['input_pin']=='ck' and fc['output_pin']=='ck_o' and fc['output_rise_input_edge']=='fall' and fc['output_fall_input_edge']=='rise';main=raw(base+'/'+d['name']+'_'+c+'.lib').decode();before=raw(base+'/sequential_'+c+'.lib.raw').decode();a,b=group(main,'ck_o');x,y=group(before,'ck_o');assert main[:a]+main[b:]==before[:x]+before[y:];comb=raw(base+'/forwarded_'+c+'.lib.raw').decode();u,v=group(comb,'ck_o');assert main[a:b]==comb[u:v]
  assert re.findall(r'related_pin\s*:\s*"([^"]+)"',main[a:b])==['ck'];assert re.findall(r'timing_sense\s*:\s*(\w+)',main[a:b])==['negative_unate'];local=fc['clk_in_to_clk_out_ps']
  for output,inputedge in [('rise','fall'),('fall','rise')]:
   for extremum in ['max','min']:
    ov=fc['output_absolute_ps']['arrival_'+extremum+'_'+output];iv=fc['input_absolute_ps']['arrival_'+extremum+'_'+inputedge];got=local['arrival_'+extremum+'_'+output];assert all(map(math.isfinite,[ov,iv,got])) and abs((ov-iv)-got)<1e-3
  bycorner[c]=dict(local_ps=local,root_waveform_ps=fc['root_waveform_ps'],native_negative_unate_ck_to_ck_o=True,all_nonforward_pin_and_FF_bytes_identical=True,forward_pin_exact_native_clockfree_bytes=True,original_pre_mutation_OT_WS=d['corners'][c]['ws'],native_combinational_lib_sha256=fc['native_combinational_lib_sha256'],repaired_odb_sha256=fc['odb_sha256'],full_spef_sha256=fc['spef_sha256'])
 rows.append(dict(master=d['name'],scope='PROSPECTIVE_PG_REPAIRED_CURRENT_IMAGE_MODEL_ONLY',original_status='PGFAIL',old_TT_FF_checks=d['verdict']['check'],corners=bycorner))
receipt=dict(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),scope='PROSPECTIVE_MODEL_ONLY not historical signoff or view adoption',native_cases=6,native_corner_extractions=18,all18_nonforward_bytes_identical=True,all18_native_NEGATIVE_UNATE=True,all12_TT_FF_original_expect_checks_pass=True,originals_unchanged=json.loads(raw('CURRENT_IMAGE_PG_REPAIRED_MODEL_ONLY/original_inputs_still_unchanged.json'))['unchanged'],cases=rows)
(B/'private_model_audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print([(r['master'],round(r['corners']['tt']['local_ps']['arrival_max_rise'],3),round(r['corners']['tt']['local_ps']['arrival_max_fall'],3)) for r in rows])
