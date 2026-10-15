import json,pathlib,hashlib
assert json.load(open('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock'))['owner']=='codex'
p=pathlib.Path(__file__).resolve().parents[3]; out=p/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ctfn_columns_candidate.sv'
d=json.loads((p/'physical/s81_die_pins/v22_hc_local_split/ot_s81_hc_ctfn.json').read_text())
col=lambda pin,i:min(3,int(d['ports'][pin]['per_bit'][i][2]//144.18))
ins=[[i for i in range(2920) if col('fd_in',i)==c] for c in range(4)]
outs=[[i for i in range(2920) if col('fdm',i)==c] for c in range(4)]
s=['// Experimental fixed NG256/GS8/NCOL3/S_RD2 stage partition. NOT adopted or physically qualified.', '// Eight actual clocks, no parent registers, no added data edge. Parent wires join actual registered leaf ports.', '// Requires a new exact pin/clock/reset contract before any physical gate. Do not substitute for current production module.']
for c in range(4):
 n=len(ins[c]);s += [f'module ot_s81_hc_ctfn_input_c{c}(input wire clk, rst_in, input wire [6:0] fv_in, input wire [{n-1}:0] d, output reg [{n-1}:0] q, output reg [6:0] fv, (* keep = "true" *) output reg [3:0] ysel, output wire rst_c,rst_n);', 'reg [1:0] rr; always @(posedge clk) rr <= {rr[0],rst_in};', 'assign rst_c=rr[0]; assign rst_n=rr[1];', 'always @(posedge clk or negedge rst_n) if(!rst_n) begin fv<=0;ysel<=0;end else begin fv<=fv_in;ysel<={4{fv_in[2]}};end', 'always @(posedge clk) q<=d;', 'endmodule']
for c in range(4):
 bits=outs[c];n=len(bits);srcbits=sorted(set(bits)|{i+128 for i in bits if i>=104 and i+128<2920});lookup={i:j for j,i in enumerate(srcbits)}
 s += [f'module ot_s81_hc_ctfn_output_c{c}(input wire clk,rst_n, input wire [6:0] fv, output reg [6:0] fvm, input wire [15:0] ysel, input wire [{len(srcbits)-1}:0] source, output reg [{n-1}:0] q);','always @(posedge clk or negedge rst_n) if(!rst_n) fvm<=0;else fvm<=fv;']
 for j,i in enumerate(bits):
  normal=f'source[{lookup[i]}]';shift=f'source[{lookup[i+128]}]' if i>=104 and i+128<2920 else "1'b0"
  expr=f'ysel[{(i-104)//176}] ? {shift} : {normal}' if i>=104 else normal
  s += [f'always @(posedge clk) q[{j}] <= {expr};']
 s += ['endmodule']
s += ['module ot_s81_hc_ctfn_columns_candidate(input wire [3:0] clk_input,clk_output,rst_in, input wire [6:0] fv_in, input wire [2919:0] fd_in, output wire rst_c, output wire [6:0] fvm, output wire [2919:0] fdm);', 'wire [2919:0] fd;wire [15:0] ysel;wire [3:0] rn,rc;wire [6:0] fv[4];']
for c in range(4):
 n=len(ins[c]); concat=lambda xs:'{'+','.join(xs[::-1])+'}'
 s += [f'wire [{n-1}:0] di{c},dq{c};assign di{c}='+concat([f'fd_in[{i}]' for i in ins[c]])+';',f'ot_s81_hc_ctfn_input_c{c} u_input{c}(.clk(clk_input[{c}]),.rst_in(rst_in[{c}]),.fv_in(fv_in),.d(di{c}),.q(dq{c}),.fv(fv[{c}]),.ysel(ysel[{4*c} +:4]),.rst_c(rc[{c}]),.rst_n(rn[{c}]));']
 for j,i in enumerate(ins[c]):s += [f'assign fd[{i}]=dq{c}[{j}];']
for c in range(4):
 n=len(outs[c]);srcbits=sorted(set(outs[c])|{i+128 for i in outs[c] if i>=104 and i+128<2920})
 s += [f'wire [{n-1}:0] qo{c};wire [{len(srcbits)-1}:0] src{c};',f'assign src{c}='+concat([f'fd[{i}]' for i in srcbits])+';',f'wire [6:0] fv_unused{c};',f'ot_s81_hc_ctfn_output_c{c} u_output{c}(.clk(clk_output[{c}]),.rst_n(rn[3]),.fv(fv[3]),.fvm('+('fvm' if c==3 else f'fv_unused{c}')+f'),.ysel(ysel),.source(src{c}),.q(qo{c}));']
 for j,i in enumerate(outs[c]):s += [f'assign fdm[{i}]=qo{c}[{j}];']
s += ['assign rst_c=rc[0];','endmodule']
out.write_text('\n'.join(s)+'\n')
# Preserve exact independently extracted old module for proof, rather than reimplement it in the test.
txt=(p/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cth.sv').read_text();ref=txt[txt.index('module ot_s81_hc_ctfn #('):];ref=ref[:ref.index('endmodule')+len('endmodule')]
a=p/'tools/s81/norm_stage_partition_candidate';a.mkdir(parents=True,exist_ok=True);(a/'ctfn_original.sv').write_text(ref+'\n')
# Count all actual bit pair geometry, not just vector spans.
rows=[]
for i in range(2920):
 for mode,src in [('normal',i),('yshift',i+128)]:
  if mode=='yshift' and (i<104 or src>=2920):continue
  x=d['ports']['fd_in']['per_bit'][src][2];y=d['ports']['fdm']['per_bit'][i][2]
  rows.append({'output_bit':i,'input_bit':src,'mode':mode,'input_column':col('fd_in',src),'output_column':col('fdm',i),'horizontal_um':round(abs(x-y),6)})
report={'scope':'candidate only, no physical or integration qualification','source_pin_sha256':hashlib.sha256((p/'physical/s81_die_pins/v22_hc_local_split/ot_s81_hc_ctfn.json').read_bytes()).hexdigest(),'input_bits_per_column':list(map(len,ins)),'output_bits_per_column':list(map(len,outs)),'input_clock_sinks_expected_postprune':[len(ins[c])+6+(7 if c==3 else 0) for c in range(4)],'output_clock_sinks_expected_postprune':[len(outs[c])+(7 if c==3 else 0) for c in range(4)],'added_reset_flops':6,'added_data_edges':0,'pair_count':len(rows),'cross_column_pairs':sum(r['input_column']!=r['output_column'] for r in rows),'max_horizontal_um':max(r['horizontal_um'] for r in rows),'pairs':rows,'remaining':['Actual mapped per-leaf sink/pin census (formula is not mapped evidence)','Exact row/site legality at half-height144.18x12.96','Port density and channel capacity for normal+shifted intermediate wires','Dedicated registered reset/FV producers and eight phi-R deliveries','All incident neighbor pins and source contracts','Old/new lockstep, reset and missing-clock mutants','Native CTS/route/TT/FF/DRC/launch/capture/spread','No NT swap or die adoption']}
report['cross_cut_unique_data_bits']=[len({r['input_bit'] for r in rows if (r['input_column']<c)!=(r['output_column']<c)}) for c in range(1,4)]
report['output_leaf_unique_source_bits']=[len({r['input_bit'] for r in rows if r['output_column']==c}) for c in range(4)]
report['candidate_source_sha256']=hashlib.sha256(out.read_bytes()).hexdigest()
(a/'pin_graph.json').write_text(json.dumps(report,indent=2)+'\n')
