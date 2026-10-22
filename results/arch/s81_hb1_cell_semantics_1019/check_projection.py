#!/usr/bin/env python3
"""Text-only bench generation locally; compilation/simulation must run on fleet."""
import json,re,pathlib,hashlib
p=pathlib.Path(__file__).resolve().parent
out=p/'validation'; out.mkdir(exist_ok=True)
m=json.loads((p/'manifest.json').read_text())['used_masters']
comb=[n for n in m if not n.startswith('DFF')]
off='\n'.join((p/'official'/f).read_text() for f in sorted({m[n]['file'] for n in comb}))
for n in sorted(m,key=len,reverse=True): off=re.sub(r'\b'+n+r'\b','official_'+n,off)
seq=(p/'official/asap7sc7p5t_SEQ_RVT_TT_220101.v').read_text()
prims='\n'.join(re.search(r'primitive '+n+r'\b.*?endprimitive',seq,re.S).group() for n in ['altos_dff','altos_dff_sr_0','altos_dff_err','altos_dff_sr_err'])
(out/'official_reference.v').write_text(off+'\n'+prims+'\n')
s=['`timescale 1ns/1ps','module tb; integer count=0; integer i,j,k;']
loops=[]; total=0
for z,n in enumerate(comb):
    ins=[x for x in m[n]['ports'] if m[n]['directions'][x]=='input']; outs=[x for x in m[n]['ports'] if m[n]['directions'][x]=='output']
    if ins:s.append(f'reg [{len(ins)-1}:0] a{z};')
    s.append(f'wire p{z},o{z};')
    args=','.join('.'+x+'('+ (f'a{z}[{ins.index(x)}]' if x in ins else f'p{z}')+')' for x in m[n]['ports'])
    s.append(f'{n} p_{z}({args});');s.append(f'official_{n} o_{z}({args.replace(f"p{z}",f"o{z}")});')
    loops.append((f'for(i=0;i<{2**len(ins)};i=i+1) begin '+(f'a{z}=i;' if ins else '')+f' #1; if(p{z} !== o{z}) $fatal(1,"COMB_MISMATCH {n} i=%0d",i); count=count+1; end'))
    total+=2**len(ins)
s += ['reg clk=0,d=0,r=1,t=1; wire pa,oa,ph,oh;', 'DFFASRHQNx1_ASAP7_75t_R a(pa,d,r,t,clk);','DFFHQNx1_ASAP7_75t_R h(ph,d,clk);','wire ax,hx; altos_dff_sr_err ae(ax,clk,~d,~r,~t); altos_dff_err he(hx,clk,~d);','altos_dff_sr_0 ua(oa,1\'b0,clk,~d,~r,~t,ax);','altos_dff uh(oh,1\'b0,clk,~d,hx);', '''task check; begin #1; if(pa !== oa) $fatal(1,"ASR_MISMATCH clk=%b d=%b resetn=%b setn=%b projection=%b official=%b",clk,d,r,t,pa,oa); if(ph !== oh) $fatal(1,"HQ_MISMATCH"); count=count+1; end endtask
initial begin
#1; if(ph !== 1'bx || pa !== 1'bx) $fatal(1,"INITIAL_STATE_FORCED");
#1;clk=1;#1;clk=0;#1;
''']
s += loops
s += ['''for(k=0;k<2;k=k+1) for(i=0;i<16;i=i+1) for(j=0;j<16;j=j+1) begin
// Seed storage, then visit every binary source/target tuple. Every step checked.
clk=0; r=1;t=1;d=k;check(); clk=1;check();clk=0;check();
{clk,d,r,t}=i;check(); {clk,d,r,t}=j;check();
end
// Explicit troublesome SETN release under held reset, at both clock levels.
for(i=0;i<2;i=i+1) begin clk=i;r=0;t=0;check();t=1;check();if(pa!==1'b1) $fatal(1,"SET_RELEASE_MISSED");r=1;check();end
$display("CELL_PROJECTION_PASS comb_checks='''+str(total)+''' seq_checks=2564 total=%0d",count);$finish;end endmodule''']
(out/'tb.v').write_text('\n'.join(s)+'\n')
projection=(p/'functional_projection.v').read_text()
(out/'mut_polarity.v').write_text(projection.replace('QN <= ~D','QN <= D'))
(out/'mut_priority.v').write_text(projection.replace("if (!SETN) QN <= 1'b0;\n    else if (!RESETN) QN <= 1'b1;", "if (!RESETN) QN <= 1'b1;\n    else if (!SETN) QN <= 1'b0;"))
(out/'mut_comb.v').write_text(projection.replace('assign Y = (A & B);','assign Y = ~(A & B);',1))
(out/'inventory.json').write_text(json.dumps({'projection_sha256':hashlib.sha256(projection.encode()).hexdigest(),'comb_masters':len(comb),'comb_checks':total,'sequence_source_target_pairs':512,'reservation':{'memory_gb':4,'threads':2,'disk_gb':2},'scope':'binary controls; direct original UDP, constant notifier/xcr; no timing wrapper/SDF/X edge equivalence'},indent=2)+'\n')
