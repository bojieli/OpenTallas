import json,re,sys
from pathlib import Path
b=Path(sys.argv[1]);o=Path(sys.argv[2]);d=json.load(open(o/'emitted/start_stages.json'));s=(b/'top_s/qwen_kvsys_bound_top.sv').read_text(); clocks=[x['clock_port'] for x in d['stages']];pst=sorted({x['net'] for x in d['die_outputs']});parents=sorted({x['net'] for x in d['die_inputs']})
m=re.search(r'module qwen_kvsys_bound_top\s*\((.*?)\);',s,re.S);ports=[x.strip() for x in m[1].split(',')];assert set(pst)<=set(ports)
s=s[:m.start(1)]+', '.join([x for x in ports if x not in pst]+clocks)+s[m.end(1):]
for p in pst:
 s,n=re.subn(r'input wire '+p+r';','wire '+p+';',s);assert n==1
ix=s.index(';')+1;s=s[:ix]+'\n'+''.join('    input wire '+c+';\n' for c in clocks)+s[ix:]
connections={'rst_raw_n':'pad_por_n',**{p:p for p in clocks+parents+pst}}
inst='    // Actual bind5 virtual START stages; real root remains inside hub_C.\n    ot_die_start_stages u_start_provider ('+', '.join('.'+k+'('+v+')' for k,v in connections.items())+');\n'
s=s.replace('endmodule',inst+'endmodule',1);(o/'qwen_kvsys_bound_top.sv').write_text(s)
bench=(b/'tb_kvslice.sv').read_text();profile=json.load(open(o/'phase_profile.json'))['profiles']['TT']; regs=[]
for x in profile:
 c=x['clock_port'];r=x['rise_late_ps']/1000;f=x['fall_late_ps']/1000
 regs.append(f'    reg {c} = 0;\n    always @(ck_core) begin\n        if (ck_core) {c} <= #({r:.9f}) 1\'b1;\n        else {c} <= #({f:.9f}) 1\'b0;\n    end\n')
bench=bench.replace('    qwen_kvsys_bound_top dut (','    // Bind5 measured TT SDF stage clocks; existing regional clocks remain nominal.\n'+''.join(regs)+'    qwen_kvsys_bound_top dut (\n'+''.join('        .'+c+'('+c+'),\n' for c in clocks),1)
(o/'tb_kvslice.sv').write_text(bench)
json.dump(dict(form='bind5_inplace_start_provider_fixture',stage_count=len(clocks),removed_unconnected_pst=pst,parent_feedback=parents,hierarchy='all original partition instances retained directly under dut',phase_basis='TT actual matching SDF late rise/fall; no provider pin-load/route included',qualification='nominal functional only; existing regional clocks are original nominal bench clocks; no physical phase claim',original_top=str(b/'top_s/qwen_kvsys_bound_top.sv'),original_bench=str(b/'tb_kvslice.sv')),open(o/'fixture.json','w'),indent=1)
print('wrote in-place top + bench; stages',len(clocks))
