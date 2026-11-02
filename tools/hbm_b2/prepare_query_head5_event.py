from pathlib import Path
import re,json,hashlib,argparse
p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
rows=[]
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def prune(s,bus,hi,lo):
 # Drop the three high head bits, retaining bit identity everywhere else.
 def num(x):
  n=int(x);return n-3 if n>hi else lo-1 if n>=lo else n
 def sub(m):
  x,y=m.group(1),m.group(2)
  return bus+'['+str(num(x))+(':'+str(num(y)) if y is not None else '')+']'
 s=re.sub(r'\b'+re.escape(bus)+r'\[(\d+)(?::(\d+))?\]',sub,s)
 # Shift only declarations of this exact packed vector.
 s=re.sub(r'\[(\d+):0\](\s+'+re.escape(bus)+r'\b)',lambda m:'['+str(int(m[1])-3)+':0]'+m[2],s)
 return s
for f in sorted(a.inputs.glob('hbm*.sv')):
 old=f.read_text();s=old;carriers=[]
 if 'hub__' in f.name:
  nw='_nw' in f.name; ls=[('L160' if nw else 'L160m',4986,0),('L6' if nw else 'L6b',828,1)]
  for lane,w,q in ls:
   s=prune(s,lane+'_o',519,517)
   s=re.sub(r'(ot_dp_st #\(\.W\()'+str(w)+r'(\)\) u_bout_'+lane+r'_o\b)',lambda m:m[1]+str(w-3)+m[2],s)
   name=f'w_u_hb_idx_q_Q_q{q}_ql_head';s=s.replace(name+'[7:0]',name+'[4:0]');s=re.sub(r'\[7:0\](\s+'+name+r'\b)',r'[4:0]\1',s)
   carriers.append(dict(name=lane+'_o',old_data=w,new_data=w-3,dropped=[519,517],epoch=[w,w-3]))
 else:
  b0='b000' in f.name;lane=('L160' if 'physical' in f.name else 'L160m') if b0 else ('L6b' if 'physical' in f.name else 'L6');w=4986 if b0 else 828
  for suffix in ['_i','_i_q','_i_b']:s=prune(s,lane+suffix,519,517)
  s=re.sub(r'(ot_dp_st #\(\.W\()'+str(w)+r'(\)\) u_bin_'+lane+r'_i\b)',lambda m:m[1]+str(w-3)+m[2],s)
  # Preserve internal eight-bit consumers after the physical cut, but never pack their zeros.
  cap=re.search(r'\breg \[7:0\] (\w*procdff_71764_q);',s)[1];alias=re.search(r'assign (\w*procdff_71764_Q) = '+cap+';',s)[1]
  s=s.replace('reg [7:0] '+cap,'reg [4:0] '+cap).replace('assign '+alias+' = '+cap+';','assign '+alias+" = {3'b000, "+cap+'};')
  if b0:
   s=prune(s,'L14_o',37,35);s=s.replace('#(.W(4127)) u_bout_L14_o','#(.W(4124)) u_bout_L14_o')
   line=next(x for x in s.splitlines() if 'u_bout_L14_o ' in x);s=s.replace(line,line.replace(alias+'[7:0]',alias+'[4:0]'))
   carriers.append(dict(name='L14_o',old_data=4127,new_data=4124,dropped=[37,35],epoch=[4127,4124]))
  else:
   x='xo_procdff_71764_Q';s=prune(s,x,7,5);s=s.replace('#(.W(8)) u_bout_'+x,'#(.W(5)) u_bout_'+x)
   line=next(x for x in s.splitlines() if 'u_bout_xo_procdff_71764_Q ' in x);s=s.replace(line,line.replace(alias+'[7:0]',alias+'[4:0]'))
   carriers.append(dict(name=x,old_data=8,new_data=5,dropped=[7,5],epoch=[8,5]))
 (a.out/f.name).write_text(s);rows.append(dict(module=f.stem,input_sha256=sha(old),output_sha256=sha(s),carriers=carriers))
assert len(rows)==6 and sum(len(r['carriers']) for r in rows)==8
(a.out/'event.json').write_text(json.dumps(dict(status='DISABLED_SOURCE_PREP_NO_BIND_OR_PHYSICAL_CREDIT',selected_source='frozen SOURCE13 selected_preprocessed.sv',rows=rows,new_cycles=0,added_ff=0,removed_boundary_data_bits=24,removed_ff='not counted until actual mapped synthesis; intermediate capture high3 projections also shrink',holds=['Producer native295a8 full7-source versus frozen SOURCE13 closure join must be exact before activation','Six wrapper re-GEN and full typed ABI/carrier lane pin-plan updates required','Upstream/downstream outside six selected wrappers must consume compact physical vectors before logical zero restore','Clock budgets 311.5/262.6 UNSELECTED; no adopted parent/as-built','New canonical wrapper proofs, pin/clock/PG/native geometry gates NOTRUN']),indent=2)+'\n')
