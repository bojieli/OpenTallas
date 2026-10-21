#!/usr/bin/env python3
"""Exact old-vs-new native pure cone, scalar and four-state witness vehicle."""
import json,re,sys,pathlib
old,new,mod,outdir=sys.argv[1:5];model=json.load(open(mod));od=pathlib.Path(outdir);od.mkdir(exist_ok=True,parents=True)
pattern=re.compile(r'^\s*(?:\(\*[^*]*\*\)\s*)?(\w+)\s+(c\w+)\s*\((.*)\);\s*$',re.M)
def read(p):return {n:(m,dict((k,v.strip()) for k,v in re.findall(r'\.(\w+)\(([^()]*)\)',ps))) for m,n,ps in pattern.findall(open(p).read())}
a,b=read(old),read(new);leafs=sorted(model['leaves'])
def module(name,cells,names):
 chosen=[(n,*cells[n]) for n in names];nets={v for n,m,ps in chosen for v in ps.values()}
 s=['module '+name+'(input wire[26:0]q,output wire y);']
 s+=['wire '+n+';' for n in sorted(nets)]
 s+=['assign '+q+'=q['+str(i)+'];' for i,q in enumerate(leafs)]
 for n,m,ps in chosen:s+=[m+' '+n+'('+','.join('.'+p+'('+v+')' for p,v in ps.items())+');']
 s+=['assign y='+model['root']+';','endmodule'];return s
oldnames=sorted(set(model['removed_cells'])|{v['input_inverse'] for v in model['leaves'].values()})
newnames=[n['name'] for n in model['nodes']]
s=module('old_cone',a,oldnames)+module('new_cone',b,newnames)
s+=['module truth_tb;','reg[26:0]q;wire a,b;integer checks=0;','old_cone o(q,a);new_cone n(q,b);',
 'task automatic chk; #1; if(a!==b || b!==(&q))begin $display("BALANCED27_TRUTH_FAIL q=%b old=%b new=%b expected=%b",q,a,b,&q);$fatal(1);end checks++;endtask',
 'function automatic logic state4(input integer v);case(v%4)0:return 0;1:return 1;2:return 1\'bx;3:return 1\'bz;endcase endfunction',
 'initial begin q=0;chk();q=\'1;chk();',
 'for(int background=0;background<2;background++)for(int bitno=0;bitno<27;bitno++)for(int state=0;state<4;state++)begin q={27{background[0]}};q[bitno]=state4(state);chk();end',
 'for(int k=0;k<8192;k++)begin for(int p=0;p<27;p++)q[p]=state4($urandom_range(0,3));chk();end',
 '$display("BALANCED27_TRUTH_PASS checks=%0d all_basis_fourstates=216",checks);$finish;end','endmodule']
(od/'truth_tb.sv').write_text('\n'.join(s)+'\n')
