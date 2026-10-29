# DIE-HEAD-15: swap the start-stage tap ports in a die combo (combo.v/combo.tcl) for a new start_stage_emit ctree.
import re,sys
src,emit,out=sys.argv[1:4]
v=open(src+'/combo.v').read(); t=open(src+'/combo.tcl').read()
ev=open(emit+'/ctree.v').read(); et=open(emit+'/ctree.tcl').read()
new_ports=re.findall(r'output (t_st_\w+);',ev)
new_assign=re.findall(r'assign (t_st_\w+) = (\w+);',ev)
new_pins=[l for l in et.split('\n') if l.startswith('place_pin -pin_name t_st_')]
assert len(new_ports)==len(new_assign)==len(new_pins),(len(new_ports),len(new_assign),len(new_pins))
mh=re.match(r'module die_combo \(([^)]*)\);',v)
ports=[p.strip() for p in mh.group(1).split(',') if not p.strip().startswith('t_st_')]
body=v[mh.end():]
lines=[l for l in body.split('\n') if not re.match(r'\s*(output t_st_\w+;|assign t_st_\w+ = \w+;)',l)]
old=len(body.split('\n'))-len(lines)
end=max(i for i,l in enumerate(lines) if l.strip()=='endmodule')
decl=[f'  output {p};' for p in new_ports]
asg=[f'  assign {p} = ck_{n};' for p,n in new_assign]
nets=set(re.findall(r'wire (ck_\w+);',v))|set(re.findall(r'\((ck_\w+)\)',v))
miss=[n for p,n in new_assign if 'ck_'+n not in nets]
assert not miss,miss[:5]
lines=decl+lines[:end]+asg+lines[end:]
open(out+'/combo.v','w').write(f"module die_combo ({', '.join(ports+new_ports)});\n"+'\n'.join(lines))
tl=[l for l in t.split('\n') if not l.startswith('place_pin -pin_name t_st_')]
k=max(i for i,l in enumerate(tl) if l.startswith('place_pin'))
tl=tl[:k+1]+new_pins+tl[k+1:]
open(out+'/combo.tcl','w').write('\n'.join(tl))
print('removed v lines',old,'old pins',len(t.split('\n'))-len(tl)+len(new_pins),'new stages',len(new_ports))
