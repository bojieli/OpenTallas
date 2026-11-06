from pathlib import Path
import hashlib,re
old=Path('root.sv').read_text();new=Path('delpipe_v2.sv').read_text()
assert hashlib.sha256(old.encode()).hexdigest()=='2214efc605dac6ac80efbb29fe03a38486a272fde801af7e27ad1f48d27c62ff'
assert hashlib.sha256(new.encode()).hexdigest()=='101a04825316ac0e65b53059f74a282a82abf572ac692dc48c033a3a64c91fc0'
expr={n:re.search(r'^  assign '+n+r' = (.+);$',old,re.M).group(1) for n in ['_20455_','_20456_']}
s=new[:new.index('endmodule')]
inputs=re.findall(r'^  input (?:\[[^\n]+?\] )?(\\\S+|\w+)\s*;',s,re.M)
s='module calendar_actual('+','.join(n+' ' for n in inputs)+',proof_bad);'+s[s.index(');')+2:]
s=re.sub(r'^  output[^\n]+\n','',s,flags=re.M).replace('(* keep *)','')
monitor='\noutput proof_bad;\nwire raw_valid_bad = '+expr['_20455_']+';\nwire raw_slot_bad = '+expr['_20456_']+';\nwire final_extra=((_60260_-32\'d153)==_60228_);\nassign proof_bad=final_extra?(_20455_||_20456_):((_20455_^raw_valid_bad)||(_20456_^raw_slot_bad));\nendmodule\n'
Path('calendar_actual.sv').write_text(s+monitor)
mut=s
for n,rhs in expr.items():
 pat=r'^  assign '+n+r' = (.+);$';matches=list(re.finditer(pat,mut,re.M));assert len(matches)==2
 # First declaration is the feature-on branch; second is its unchanged default-off branch.
 m=matches[0];mut=mut[:m.start()]+'  assign '+n+' = '+rhs+';'+mut[m.end():]
Path('calendar_mutant.sv').write_text(mut+monitor)
