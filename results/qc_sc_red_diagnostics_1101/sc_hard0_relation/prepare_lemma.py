from pathlib import Path
import re,json,hashlib
b=Path('.')
old=(b/'old_qfd_dv_s5_sc2_k79.sv').read_text();new=(b/'new_qfd_dv_s5_sc2_k79.sv').read_text()
pat=re.compile(r'generate if \(HARD_PINREG\) begin : \w+\n.*?\nend else begin : \w+\n(.*?)\nend endgenerate',re.S)
def h0(t):
 t=pat.sub(lambda m:m[1],t)
 t=re.sub(r"HARD_PINREG\s*\?\s*1'b1\s*:\s*(\w+)",r'\1',t)
 return re.sub(r'HARD_PINREG\s*\?\s*\([^()]*\)\s*:\s*(\w+)',r'\1',t)
inst=re.compile(r'\b(qfd_s2_bmath_\w+)\s*#\(\.ID\((\d+)\)\)\s+(\w+)\((.*?)\);')
ports=re.compile(r'\.(\w+)\(([^()]*)\)')
def model(t):
 uf={}
 def get(x):
  if x not in uf:uf[x]=x
  if uf[x]!=x:uf[x]=get(uf[x])
  return uf[x]
 for a,c in re.findall(r'\bassign\s+(\w+)\s*=\s*(\w+)\s*;',t):
  if not(a.startswith('sc_pin_')or c.startswith('sc_pin_')):continue
  a,c=get(a),get(c);uf[max(a,c)]=min(a,c)
 def canon(s):return re.sub(r'\b(?:n_\d+|sc_pin_\w+)\b',lambda m:get(m[0]),re.sub(r'\s+','',s))
 d={}
 for m in inst.finditer(t):
  assert m[3] not in d
  d[m[3]]=[m[1],int(m[2]),sorted((k,canon(v))for k,v in ports.findall(m[4]))]
 return d
og=model(old);ng=model(h0(new));fg=model((b/'gold.v').read_text());fn=model(h0((b/'gate0.v').read_text()))
assert len(fg)==len(fn)==509
for label,fixture,actual in [('gold',fg,og),('gateHARD0',fn,ng)]:
 bad={k:[v,actual.get(k)]for k,v in fixture.items()if actual.get(k)!=v}
 assert not bad,(label,list(bad.items())[:2])
y=re.search(r'assign y\s*=\s*\{([^}]+)\}',(b/'gold.v').read_text())[1].split(',')
assert len(y)==len(set(y))==509
assert set(y)=={dict(v[2])['Q']for v in fg.values()}
gate=(b/'gate0.v').read_text()
tb=(b/'tb.v').read_text().replace('sc_pin_gate h(', 'sc_pin_gate #(.HARD_PINREG(0)) h(')
assert '.HARD_PINREG(0)' in tb
(b/'tb_hard0.v').write_text(tb)
mutants={}
for tag,name,oldport,newport in [
 ('wrong_plain_data','u_227258','.D(n_105)','.D(n_106)'),
 ('reset_support_OR','u_228347','.R(n_240513)','.R(n_240513 | n_239764)'),
 ('control_forced_one','u_228347',".D(HARD_PINREG ? 1'b1 : n_104)",".D(HARD_PINREG ? 1'b1 : 1'b1)")]:
 lines=gate.splitlines();hits=[i for i,l in enumerate(lines)if re.search(r'\b'+name+r'\(',l)and oldport in l]
 assert len(hits)==1,(tag,hits)
 i=hits[0];before=lines[i];lines[i]=before.replace(oldport,newport);(b/(tag+'.v')).write_text('\n'.join(lines)+'\n')
 mutants[tag]={'instance':name,'old_literal':before,'mutant_literal':lines[i],'active_parameter':0}
(b/'correct.v').write_text(gate)
for tag in ['correct']+list(mutants):
 text='read_verilog -sv -noautowire actual_helpers.sv gold.v '+tag+'.v tb_hard0.v\nhierarchy -top tb\nsetattr -unset keep_hierarchy\nsetattr -mod -unset keep_hierarchy\nsetattr -unset keep\nproc\nflatten\nasync2sync\nopt\n'
 args=' -verify'if tag=='correct'else' -show-inputs -show-outputs -dump_vcd '+tag+'.vcd'
 text+='sat -seq 4 -set-init-undef -set-def-inputs -prove-x bad 0'+args+'\n';(b/(tag+'.ys')).write_text(text)
receipt={'scope':'PREP_EXACT_SELECTED_DEFAULT_HARD0_CAPTURE_LEMMA_PLUS_LITERAL_SOURCE_COVERAGE','actual_old':'051340895d9','actual_new':'98bbbbd8184','fixture_archive':'41612e22eac','explicit_parameter':0,'data_inputs':107,'independent_reset_supports':5,'observed_old_capture_Qs':509,'gold_capture_primitives_match_actual_old':len(fg),'gate_HARD0_capture_primitives_match_actual_new':len(fn),'all509_Qs_observed_exactly_once':True,'primitive_helpers':'actual unchanged old/new helpers blob, not invented primitive model','relation_after':'first capture edge; no arithmetic/data edge changed','proof_cycles':4,'input_assumptions':'defined arbitrary data/reset supports each cycle; independent reset support, no protocol/ready constraints','mutants':mutants,'source_native_mapped_count_or_default_adoption':False,'resources_proposed':{'memGB':4,'threads':1,'diskGB':1},'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in b.glob('*')if p.is_file()and p.suffix in ['.v','.sv','.ys','.py']}}
(b/'lemma_prep.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items()if k not in ['files','mutants']},indent=2))
