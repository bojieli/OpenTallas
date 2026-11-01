#!/usr/bin/env python3
"""Source-bound control-cut proof; does not alter production RTL or qualify a kit."""
import hashlib,json,os,re,subprocess
from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--source-dir',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
rev='ea4199488a6829a302614165d9fd5f30fc2bea80'
expected={
'ot_s81dv_norm.sv':'fcf117b4d9bea108d167f59c0cad567f518a4615401f59acf91e2f324350df02',
'ot_hdc_delay.sv':'7b37c18daacc0e2c592dc3acf1e65e2225a69697a39de9c1e4d2fc22421cb688',
'ot_hdc_sfu.sv':'c11a2d3341d952ca221f4478193e5ef3f817ac51abe8744274bf59f59e146923'}
def source(path):
 raw=(a.source_dir/Path(path).name).read_bytes() if a.source_dir else subprocess.check_output(['git','show',rev+':'+path])
 assert hashlib.sha256(raw).hexdigest()==expected[Path(path).name], 'actual source differs from pinned used kit: '+path
 return raw.decode()
s=source('rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv');s=s[s.index('module ot_s81dv_eng_finish'):];s=s[:s.index('endmodule')]
params=s[s.index('    localparam integer T '):s.index('    function automatic integer ca')]
assert 'localparam integer CW  = $clog2(NC)' in params
ut=re.search(r'    ot_hdc_delay #\(\.W\(CW\), \.D\(LAV\)\) u_t .*?;',s).group()
assert '.d(t_q), .q(wr_n)' in ut
assert len(re.findall(r'wr_v && wr_n == t \* NVP \+ n',s))==2
assert 'w_hh = wr_v && wr_n == 1' in s
assert 'w_kk = wr_v && wr_n == NVP + 1' in s
assert 'w_dd = wr_v && wr_n == 2 * NVP + 1' in s
v=source('rtl/hdc/ot_hdc_sfu.sv');v=v[v.index('module ot_hdc_vline'):];v=v[:v.index('endmodule')+len('endmodule')]
d=source('rtl/hdc/ot_hdc_delay.sv')
# The cut is immediately after the original t_q/f_q registers: arbitrary tags
# and valid bits are stronger than the actual source's encoded issue stream.
top='''module top #(parameter NV=80, LA=6, MUT=0)(input clk,rstn,input [$clog2(3*((NV<=1)?1:(1<<$clog2(NV))))-1:0] t_q,input f_q);
PARAMS
wire [CW-1:0] wr_n;
UT
wire [LAV:0] av;
ot_hdc_vline #(.D(LAV)) u_v(.clk(clk),.rst_n(rstn),.v(f_q),.vd(av));
wire wr_v=av[LAV];
wire [NC-1:0] early,late,newwrite;
genvar t,n;
generate for(t=0;t<T;t=t+1) begin:g_tree
 for(n=0;n<NVP;n=n+1) begin:g_node
  localparam C=t*NVP+n;
  if(n>=1 && isadd(n)) begin:g_live
   assign early[C]=(t_q==C);
   assign late[C]=wr_v && (wr_n==C);
  end else begin:g_dead
   assign early[C]=0;
   assign late[C]=0;
  end
 end
end endgenerate
wire [NC-1:0] delayed;
ot_hdc_delay #(.W(NC),.D(LAV)) u_oh(.clk(clk),.rst_n(rstn),.d(early),.q(delayed));
assign newwrite=delayed & {NC{wr_v}};
reg initialized=0;
always @(posedge clk) begin
 if(!rstn) initialized<=1;
 if(initialized) assert(late==(newwrite ^ ((MUT && wr_v)? {{(NC-2){1'b0}},2'b10}: {NC{1'b0}})));
end
endmodule
'''.replace('PARAMS',params).replace('\nUT\n','\n'+ut+'\n')
(a.out/'control_cut.sv').write_text(d+'\n'+v+'\n'+top)
binding=dict(revision=rev,full_file_hashes=expected,source_sha256=hashlib.sha256(s.encode()).hexdigest(),native_delay_sha256=hashlib.sha256(d.encode()).hexdigest(),native_valid_sha256=hashlib.sha256(v.encode()).hexdigest(),params_and_isadd=params,old_delay_instance=ut,cut='actual t_q/f_q outputs, arbitrary tag/valid; original native delay and valid modules',claim='every valid-qualified write enable, including all three root sites, same edge; no complete child qualification')
(a.out/'binding.json').write_text(json.dumps(binding,indent=2)+'\n')
results=[]
for nv in [5,80]:
 for mut in [0,1]:
  name=f'nv{nv}_mut{mut}'
  script=f'''read_verilog -formal -sv {a.out}/control_cut.sv
chparam -set NV {nv} -set MUT {mut} top
prep -top top
async2sync
dffunmap
flatten
opt_clean
sat -set-def-inputs -seq 12 -tempinduct -set-at 1 rstn 0 -prove-asserts -verify -dump_vcd {a.out}/{name}.vcd
'''
  (a.out/f'{name}.ys').write_text(script)
  with (a.out/f'{name}.log').open('w') as f:r=subprocess.run([os.environ.get('YOSYS','yosys'),'-Q','-s',str(a.out/f'{name}.ys')],stdout=f,stderr=subprocess.STDOUT)
  log=(a.out/f'{name}.log').read_text();verdict='PROVED' if r.returncode==0 and 'SUCCESS' in log else 'COUNTEREXAMPLE' if ('proof did fail' in log or 'model found: FAIL' in log) else 'ERROR'
  results.append(dict(NV=nv,mutant=mut,returncode=r.returncode,verdict=verdict,expected='COUNTEREXAMPLE' if mut else 'PROVED'))
(a.out/'results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results))
raise SystemExit(0 if all(x['verdict']==x['expected'] for x in results) else 1)
