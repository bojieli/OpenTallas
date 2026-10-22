#!/usr/bin/env python3
"""Private legacy-TT envelope fixtures only. Never emits an SC2 master."""
import pathlib,subprocess,json,re,hashlib,math
P=pathlib.Path(__file__).resolve().parent
OR='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
IMAGE='openroad/orfs:asap7lock'
PLAT='/OpenROAD-flow-scripts/flow/platforms/asap7'
M='ot_sram_1r1w_32x546_m1'
assert '_sc2' not in M
analysis=json.loads((P/'analysis.json').read_text())['envelopes']
inv=[x for x in analysis if x['instance']=='dependent']
mins=min(x['delay_or_check']['lower'] for x in inv);maxs=max(x['delay_or_check']['upper'] for x in inv)
slewmax=max(x['output_transition']['upper'] for x in inv)
checks={role:max(x['delay_or_check']['upper'] for x in analysis if x['instance']=='capture' and x['role']==role) for role in ('setup','hold')}
def docker(args):
 r=subprocess.run(['docker','run','--rm','-v',str(P)+':/work',IMAGE,*args],capture_output=True,text=True)
 return r.returncode,r.stdout+r.stderr
code,native=docker(['sh','-ec','zcat '+PLAT+'/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz'])
assert code==0
(P/'native_invbuf_tt.lib').write_text(native)
def end_block(s,start):
 p=s.index('{',start);depth=1;j=p+1
 while depth:
  depth+=(s[j]=='{')-(s[j]=='}');j+=1
 return j
def values_constant(block,val):
 def sub(m):
  text=m[0]
  return re.sub(r'"([^"\n]*)"',lambda q:'"'+', '.join([f'{val*1e12:.12g}']*len(q[1].split(',')))+'"',text)
 return re.sub(r'values\s*\(.*?\)\s*;',sub,block,flags=re.S)
files={}
for role in ('min','max'):
 # Retain the real gate cell truth function, pins/caps, complete arc topology;
 # replace only its delay/transition LUT values with the analytical envelope.
 text=native;start=re.search(r'cell\s*\(\s*INVx1_ASAP7_75t_R\s*\)',text).start();end=end_block(text,start);cell=text[start:end]
 edits=[]
 for q in re.finditer(r'\b(cell_rise|cell_fall|rise_transition|fall_transition)\s*\(',cell):
  fin=end_block(cell,q.start());val=(mins if role=='min' else maxs) if q[1].startswith('cell_') else (0 if role=='min' else slewmax)
  edits.append((q.start(),fin,values_constant(cell[q.start():fin],val)))
 for a,b,v in reversed(edits):cell=cell[:a]+v+cell[b:]
 text=text[:start]+cell+text[end:];text=re.sub(r'(library\s*\()([^)]*)',lambda q:q[1]+'CALIBRATION_ONLY_INV_TT_'+role,text,count=1)
 fi=P/f'CALIBRATION_ONLY_inv_{role}.lib';fi.write_text(text);files['inv_'+role]=fi.name
 macro=(P/(M+'_tt.lib')).read_text();edits=[]
 for q in re.finditer(r'\btiming\s*\([^)]*\)\s*\{',macro):
  fin=end_block(macro,q.start());block=macro[q.start():fin];which=re.search(r'timing_type\s*:\s*(setup|hold)_rising',block)
  if which:edits.append((q.start(),fin,values_constant(block,checks[which[1]])))
 assert edits,'actual capture checks required'
 for a,b,v in reversed(edits):macro=macro[:a]+v+macro[b:]
 macro=re.sub(r'(library\s*\()([^)]*)',lambda q:q[1]+'CALIBRATION_ONLY_SRAM_TT_'+role,macro,count=1)
 fi=P/f'CALIBRATION_ONLY_sram_{role}.lib';fi.write_text(macro);files['sram_'+role]=fi.name
def admit_roles(mapping):
 # The calibration's expected identities are explicit and closed. This is
 # deliberately independent of filename-based corner/role inference.
 if set(mapping)!={'min','max'}:raise ValueError('missing explicit role')
 for b in ('min','max'):
  if mapping[b]!=[files['inv_'+b],files['sram_'+b]]:raise ValueError('swapped/aliased role identity')
  if any(not (P/f).is_file() for f in mapping[b]):raise ValueError('missing role file')
records=[]
for case in ('correct','swapped','missing'):
 if case=='missing':
  try:admit_roles({'min':[files['inv_min'],files['sram_min']]})
  except ValueError:pass
  else:raise AssertionError('missing max role was admitted')
  (P/'missing_role_refusal.log').write_text('REFUSED: explicit TT max role absent; no native library load or alias fallback.\n');records.append(dict(case=case,refused=True,loaded=False));continue
 mi,ma=('min','max') if case=='correct' else ('max','min')
 libs={b:[files['inv_'+r],files['sram_'+r]] for b,r in [('min',mi),('max',ma)]}
 if case=='correct':admit_roles(libs)
 else:
  try:admit_roles(libs)
  except ValueError:pass
  else:raise AssertionError('swapped roles admitted')
 # The swapped case below deliberately bypasses the refused preflight for
 # a read-only native discriminator. Its timing result is never accepted.
 t=f'read_lef {PLAT}/lef/asap7_tech_1x_201209.lef\nread_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef\nread_lef /work/{M}.lef\n'
 for f in files.values():t+=f'read_liberty /work/{f}\n'
 t+='read_verilog /work/probe.v\nlink_design probe\nset_mode calibration\ncreate_clock -name core -period 2000 [get_ports clk]\nset_clock_transition 20 [all_clocks]\n'
 t+='define_scene TT -mode calibration -liberty_min [list '+' '.join('/work/'+f for f in libs['min'])+'] -liberty_max [list '+' '.join('/work/'+f for f in libs['max'])+']\nset_scene TT\nload /work/native_accessor.so Otenvelope\n'
 t+=f'set stream [open /work/{case}_role_tables.ndjson w]\n'
 for b in ('min','max'):
  for inst,fr,to,x,y in [('dependent','A','Y',20e-12,2.88e-15),('capture','clk','wd_in[0]',20e-12,20e-12)]:
   t+=f'puts $stream "TABLE {inst} {b} [ot_envelope_query {inst} {b} {x} {y} {{{fr}}} {{{to}}}]"\n'
 t+='close $stream\nreport_checks -path_delay min_max -from [get_pins {launch/rd_out[0]}] -to [get_pins {capture/wd_in[0]}] -format full_clock_expanded -digits 6\n'
 t+='puts "MIN_ARR [get_property [get_pins dependent/Y] arrival_min_rise]"\nputs "MAX_ARR [get_property [get_pins dependent/Y] arrival_max_rise]"\nexit\n'
 (P/f'{case}_roles.tcl').write_text(t);code,out=docker([OR,'-no_init','-exit',f'/work/{case}_roles.tcl']);(P/f'{case}_roles.log').write_text(out)
 assert code==0 and '[ERROR' not in out
 actual=[]
 for line in (P/f'{case}_role_tables.ndjson').read_text().splitlines():
  _,inst,b,data=line.split(' ',3)
  for a in json.loads(data):
   expected='CALIBRATION_ONLY_'+('INV' if inst=='dependent' else 'SRAM')+'_TT_'+b
   numeric=(mins if b=='min' else maxs) if inst=='dependent' else checks[a['role']]
   if case=='correct':assert math.isclose(a['value'],numeric,rel_tol=3e-6,abs_tol=1e-17),'native envelope value mismatch'
   actual.append(dict(instance=inst,bound=b,library=a['library'],role=a['role'],value=a['value'],identity_matches=a['library']==expected))
 if case=='correct':assert all(x['identity_matches'] for x in actual)
 else:
  assert not any(x['identity_matches'] for x in actual)
  (P/'swapped_role_refusal.log').write_text('REFUSED: actual mapped native TT envelope libraries are swapped for both gate delay and capture setup/hold; observed scene mapping differs from expected role identities.\n')
 records.append(dict(case=case,refused=case!='correct',actual=actual))
(P/'role_receipt.json').write_text(json.dumps(dict(scope='Private legacy TT native API calibration only; no SC2 library emitted',delay_lower_ps=mins*1e12,delay_upper_ps=maxs*1e12,check_upper_ps={k:v*1e12 for k,v in checks.items()},transition_upper_ps=slewmax*1e12,cases=records,fixture_sha256={f:hashlib.sha256((P/f).read_bytes()).hexdigest() for f in files.values()}),indent=2)+'\n')
print('SAME_CORNER_ENVELOPE_ROLE_CALIBRATION_PASS correct/swapped/missing')
