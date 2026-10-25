#!/usr/bin/env python3
"""Balance fixed SU programme/config bundles in a bound die, preserving every bit.

Source-functional correction only. Report every inserted stage; full token, clock,
VM calendar and round-trip qualification remain separate gates.
"""
from pathlib import Path
import argparse,json,re,sys
sys.path.insert(0,str(Path(__file__).parent))
import coll_transport as C,prog_transport as T
PAD='''module ot_codex_prog_r8_pad #(parameter W=1, D=1)(input clk,rst_n,input [W-1:0] a,output [W-1:0] y);
generate if(D==0) begin assign y=a; end else begin
reg [W-1:0] q[0:D-1];integer i;
always @(posedge clk) begin
 if(!rst_n) begin for(i=0;i<D;i=i+1) q[i]<=0;end
 else begin q[0]<=a;for(i=1;i<D;i=i+1)q[i]<=q[i-1];end
end
assign y=q[D-1];end endgenerate
endmodule
'''
def pieces(e):
 e=e.strip()
 if not e.startswith('{'):return [e]
 out=[];start=1;depth=0
 for i,c in enumerate(e[1:-1],1):
  if c in '{(':depth+=1
  elif c in '})':depth-=1
  elif c==',' and depth==0:out.append(e[start:i].strip());start=i+1
 return out+[e[start:-1].strip()]
def width(e):
 m=re.fullmatch(r"\w+\[(\d+)(?::(\d+))?\]",e)
 if m:return abs(int(m[1])-int(m[2]))+1 if m[2] else 1
 m=re.fullmatch(r"(\d+)'[bhd].*",e)
 if m:return int(m[1])
 raise ValueError('cannot safely infer width: '+e)
def plan(path, command_depth=None):
 names={f'su_{q}{g}' for q in T.QS for g in range(4)}|{f'sucore_{q}' for q in T.QS}|{f'pgp_{q}' for q in T.QS}
 I=C.parse_instances(path,names);groups={};legs=[]
 for q in T.QS:
  consumers=[f'su_{q}{g}' for g in range(4)]+[f'sucore_{q}']
  for n in consumers:
   if n not in I:continue
   for p,e in I[n][1].items():
    ps=pieces(e);ls=T.lanes_of_concat(I,n,p)
    if not any(f'pgp_{q}__command' in l['root'] for l in ls):continue
    if len(ps)!=len(ls) or any(f'pgp_{q}__command' not in l['root'] for l in ls):raise ValueError(f'mixed-source command {n}.{p}')
    for k,(ex,l) in enumerate(zip(ps,ls)):
     legs.append(dict(group='command_all',quarter=q,instance=n,port=p,piece=k,expr=ex,width=width(ex),old=l['latency_edges']))
  n=f'pgp_{q}'
  if n not in I:continue
  for p in T.SU_PORTS:
   for k,(ex,l) in enumerate(zip(pieces(I[n][1][p]),T.lanes_of_concat(I,n,p))):
    legs.append(dict(group=f'config_{q}',quarter=q,instance=n,port=p,piece=k,expr=ex,width=width(ex),old=l['latency_edges']))
 for l in legs:groups[l['group']]=max(groups.get(l['group'],0),l['old'])
 if command_depth is not None:
  if command_depth < groups['command_all']:raise ValueError('requested command depth shorter than existing path')
  groups['command_all']=command_depth
 for l in legs:l.update(target=groups[l['group']],added=groups[l['group']]-l['old'])
 return I,groups,legs

def apply(path,out,command_depth=None):
 I,groups,legs=plan(path,command_depth);s=path.read_text();decl=[];replace={};clocks={q:I[f'pgp_{q}'][1] for q in T.QS if f'pgp_{q}' in I}
 for q in T.QS:
  if q not in clocks:
   candidate=next((ports for name,(_,ports) in I.items() if re.match(r'(su_|sucore_)'+q, name) and 'clk_ctl' in ports and 'rst_n' in ports),None)
   if candidate:clocks[q]=dict(clk=candidate['clk_ctl'],rst_n=candidate['rst_n'])
 for j,l in enumerate(legs):
  key=(l['instance'],l['port']);replace.setdefault(key,pieces(I[key[0]][1][key[1]]))
  if not l['added']:continue
  q=l['quarter'];w=l['width'];net=f'codex_r8_{j}'
  decl += [f'wire [{w-1}:0] {net};',f"ot_codex_prog_r8_pad #(.W({w}),.D({l['added']})) pad_{net} (.clk({clocks[q]['clk']}),.rst_n({clocks[q]['rst_n']}),.a({l['expr']}),.y({net}));"]
  replace[key][l['piece']]=net
 for (n,p),ps in replace.items():
  orig=I[n][1][p];new=ps[0] if len(ps)==1 else '{'+', '.join(ps)+'}'
  # Match the named instance block; no global expression replacement.
  rx=re.compile(r'(?ms)(^\s*\w+\s*(?:#\(.*?\))?\s+'+re.escape(n)+r'\s*\(\s*\n)(.*?)(^\s*\);)')
  m=rx.search(s)
  if not m:raise ValueError('instance not found '+n)
  body=m[2];old=f'.{p}({orig})'
  if body.count(old)!=1:raise ValueError('non-unique port '+n+'.'+p)
  body=body.replace(old,f'.{p}({new})');s=s[:m.start(2)]+body+s[m.end(2):]
 s=s.replace('\nendmodule','\n'+'\n'.join(decl)+'\nendmodule',1)+'\n'+PAD
 out.mkdir(parents=True,exist_ok=True);(out/'die.v').write_text(s);(out/'prog_pad.sv').write_text(PAD)
 report=dict(status='SOURCE PATCH: exact transport miter pending; native token NOT QUALIFIED',groups=groups,legs=legs,pad_flops=sum(l['width']*l['added'] for l in legs),cycle_pricing=dict(root_config_serial_edges=55,command_serial_edges=groups['command_all'],compiler_start_advance_serial=9,pgp_head_first_valid_serial=6,required_root_start_advance_serial=55+groups['command_all']+6-9,required_root_start_advance_stream=(4*(55+groups['command_all']+6-9)+2)//3),rule='all pieces of each config/command group land at its maximum measured fixed depth')
 (out/'balance.json').write_text(json.dumps(report,indent=1)+'\n');return report

def bench(r,out):
 lines=['module tb;reg clk=0,rst_n=0;always #5 clk=~clk;integer cycle;reg [31:0] seq=1;']
 for j,l in enumerate(r['legs']):
  w=l['width'];old=l['old'];add=l['added'];tar=l['target'];lines += [f'wire [{w-1}:0] a{j}={{{(w+31)//32}{{seq}}}};',f'wire [{w-1}:0] o{j},d{j},r{j};',f'ot_codex_prog_r8_pad #(.W({w}),.D({old})) old{j}(clk,rst_n,a{j},o{j});',f'ot_codex_prog_r8_pad #(.W({w}),.D({add})) dut{j}(clk,rst_n,o{j},d{j});',f'ot_codex_prog_r8_pad #(.W({w}),.D({tar})) ref{j}(clk,rst_n,a{j},r{j});',f'always @(negedge clk) if(rst_n && cycle>150 && d{j} !== r{j}) $fatal(1,"leg{j} mismatch");']
 l=next(x for x in r['legs'] if x['added']>0);j=r['legs'].index(l);w=l['width'];lines += [f'wire [{w-1}:0] mutant;integer caught=0;',f'ot_codex_prog_r8_pad #(.W({w}),.D({l["added"]-1})) mut(clk,rst_n,o{j},mutant);',f'always @(negedge clk) if(rst_n && cycle>150 && mutant!==r{j}) caught=1;', 'initial begin cycle=0;repeat(4)@(negedge clk);rst_n=1;for(cycle=0;cycle<500;cycle=cycle+1)begin @(negedge clk);seq={seq[30:0],seq[31]^seq[21]^seq[1]^seq[0]};end if(!caught)$fatal(1,"mutant not caught");$display("PROGRAMME_R8_MITER PASS legs=%0d mutant=CAUGHT",'+str(len(r['legs']))+');$finish;end endmodule']
 (out/'tb.sv').write_text('\n'.join(lines)+'\n')
def main():
 a=argparse.ArgumentParser();a.add_argument('--die-v',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--command-depth',type=int);z=a.parse_args();r=apply(z.die_v,z.out,z.command_depth);bench(r,z.out);print(json.dumps(dict(groups=r['groups'],legs=len(r['legs']),pad_flops=r['pad_flops'])))
if __name__=='__main__':main()
