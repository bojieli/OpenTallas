import pathlib,json,importlib.util,collections
r=pathlib.Path(__file__).parent
s=importlib.util.spec_from_file_location('lint',r/'tools/textbook_lint.py');T=importlib.util.module_from_spec(s);s.loader.exec_module(T)
g,top=T.flatten(T.parse_verilog((r/'r7w_reuse/qkd_d2d_static_safe24.v').read_text()),None)
md={'macros':[{'name':n,'master':t,'pins':[(pn,0,0,'OUTPUT'if pn=='rd_out'else'INPUT')for pn in p]}for t,n,p in g.cells if t.startswith('ot_sram_')]};A=T.build(g,md)
# First actual unreset feedback clone in independent inventory.
j=json.loads((r/'r7w.readback.json').read_text());chosen=next(x for x in j['cloned_flops'] if not x['has_async_pins'] and g.cells[x['origin']][2]['D'] != g.cells[x['copy']][2]['D'])
pairs=[(x['origin'],x['copy']) for x in j['cloned_flops'] if not x['has_async_pins']];a,b=pairs[0];todo=[g.cells[i][2]['D'][0] for pair in pairs for i in pair];cells=set();boundary=set()
while todo:
 x=todo.pop()
 if x<4:continue
 driver=A['driver'].get(x)
 if not driver or driver[0]<0:boundary.add(x);continue
 ci,pn=driver
 if A['kind'][ci] in ('ff','macro'):boundary.add(x);continue
 if ci in cells:continue
 cells.add(ci);todo.extend(z for pin,bs in g.cells[ci][2].items() if A['pin_dir'][ci][pin]=='in' for z in bs)
def net(x):return ["1'b0","1'b1","1'bx","1'bz"][x]if x<4 else f'n{x}'
used={x for ci in cells for bs in g.cells[ci][2].values()for x in bs}|boundary
lines=['module cold_all('+','.join('n'+str(x)for x in sorted(boundary))+',same,matches);','output same;','output ['+str(len(pairs)-1)+':0] matches;']+['input '+net(x)+';'for x in sorted(boundary)]+['wire '+net(x)+';'for x in sorted(used-boundary)if x>=4]
for ci in sorted(cells):
 t,n,p=g.cells[ci];lines.append(t+' '+n+' ('+','.join('.'+pin+'('+net(bs[0])+')'for pin,bs in p.items())+');')
lines += ['assign matches['+str(k)+'] = ('+net(g.cells[a][2]['D'][0])+' == '+net(g.cells[b][2]['D'][0])+');' for k,(a,b) in enumerate(pairs)];lines += ['assign same = &matches;','endmodule']
(r/'cold_all.v').write_text('\n'.join(lines)+'\n')
info=dict(pairs=pairs,chosen=chosen,original_D=g.cells[a][2]['D'],copy_D=g.cells[b][2]['D'],boundary=[dict(net=x,name=g.net_name[x],driver=A['driver'].get(x))for x in sorted(boundary)],cells=len(cells),same_direct_D=g.cells[a][2]['D']==g.cells[b][2]['D'])
(r/'cold_all.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info,indent=2))
