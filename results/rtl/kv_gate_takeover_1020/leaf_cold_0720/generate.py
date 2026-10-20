from pathlib import Path
import re,subprocess,json,hashlib
r=Path(__file__).resolve().parent
core=subprocess.check_output(['git','show','295504c93:rtl/qwen_sys/static_kv_die_20261017/qkd_kv_hroot_safe32.sv']).decode();top=subprocess.check_output(['git','show','295504c93:rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_hroot_safe32.sv']).decode();ref=subprocess.check_output(['git','show','295504c93:results/rtl/kv_hroot_safe32_1020/reference.sv']).decode();abi_path='rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba.sv';abi=subprocess.check_output(['git','show','295504c93:'+abi_path]).decode();abi=re.search(r'\bmodule qkd_kvs_hroot\s*\(.*?endmodule',abi,re.S)[0]
header=top[top.index('(')+1:top.index(');')];decl=[];ports=[];outs=[]
for direction,width,name in re.findall(r'\b(input|output) wire\s*(\[[^]]+\])?\s*(\w+)',header):
 ports.append(name);decl.append(('reg ' if direction=='input' else 'wire ')+(width+' ' if width else '')+name+';')
 if direction=='output':outs.append(name)
params=ref[ref.index('    localparam'):ref.index('    (* keep *)')];fn=re.search(r'    function automatic.*?    endfunction',ref,re.S)[0];fn=fn.replace('input [783:0] x);','input [783:0] x, input [1:0] s);')
assigns=[]
for name,rhs in re.findall(r'assign\s+(o_\w+)\s*=\s*(.*?);',abi,re.S):
 rhs=rhs.replace('w_esh__d','expect_head').replace('w_rly__fan','expect_fan').replace('w_rly__g','expect_g').replace('w_rly__r','expect_r');assigns.append(f'wire [{779 if name=="o_pc" else (143 if name=="o_ctl" else 298 if name=="o_emb" else 270 if name=="o_ch0" else 22 if name=="o_kg" else 4)}:0] expected_{name} = {rhs};')
init=[]
def initreg(name,width):
 for j in range(width):init.append(f'dut.{name}[{j}] = $urandom; init_count++; init_ones += dut.{name}[{j}];' if width>1 else f'dut.{name} = $urandom; init_count++; init_ones += dut.{name};')
for c in range(2):initreg(f'u_esh.ctl_root[{c}]',13);initreg(f'u_esh.sid_root[{c}]',2)
initreg('u_esh.rst_root',2)
ex={0,1,2,3,4,5,6,7,721,756,757,758,783}
for b in range(784):
 if b not in ex:
  initreg(f'u_esh.cap[{b}].dat.q0',1);initreg(f'u_esh.cap[{b}].dat.q1',1)
for i in range(60):
 for n,w in [('rn',1),('sid',2),('ctl',13),('q',13)]:initreg(f'u_esh.region[{i}].{n}',w)
for n,w in [('fan',334),('fan_c',334),('fan_mid',334),('g',144),('g_c',144),('g_mid',144),('r',299),('r_c',299),('r_mid',299)]:initreg('u_rly.'+n,w)
assert len(init)==5645
comparisons='\n'.join(f'if ({"head_known" if n=="o_pc" else "relay_known"}) begin checks++; if({n} !== expected_{n}) begin errors++; if(errors<8) $display("MISMATCH edge=%0d port={n} reset=%0d rel=%0d",edges,rst_n,release_edges); end end' for n in outs)
pack='{'+','.join(outs)+'}'
tb='''`timescale 1ns/1ps
module tb;
'''+ '\n'.join(decl)+f'\nqkd_kvs_hroot_safe32 dut({", ".join("."+n+"("+n+")" for n in ports)});\n'+params+fn+'''
reg [779:0] expect_head;
reg [333:0] expect_fan; reg [143:0] expect_g;reg [298:0] expect_r;
reg [1117:0] h0,h1;reg [143:0] g0,g1;reg [298:0] r0,r1;reg [1:0] s0,s1;
bit h0_known=0,h1_known=0,head_known=0,relay_known=0;
bit reset0_known=0,reset1_known=0;reg reset0,reset1;
integer edges=0,checks=0,errors=0,unconstrained_head=0,unconstrained_relay=0,release_edges=0,assert_edges=0,firstuses=0,pulses=0,stops=0;
integer init_count=0,init_ones=0,seed,seed_copy,j,ep;
reg [1556:0] stopped_outputs;
'''+ '\n'.join(assigns)+'''
task stimulus(input bit held);
 begin
  if(!held)begin
   esh__stack=$urandom;
   for(integer j=0;j<1118;j++)i_ctl[j]=$urandom;
   for(integer j=0;j<144;j++)i_g[j]=$urandom;
   for(integer j=0;j<299;j++)i_r[j]=$urandom;
   i_ctl[5:4]=esh__stack;i_ctl[7:6]=esh__stack;
  end
 end
endtask
task tick;
 bit next_reset1,next_reset1_known;
 begin
  #4;ck=1;#0.1;
  edges++;
  if(rst_n)begin release_edges++;assert_edges=0;end else begin release_edges=0;assert_edges++;end
  next_reset1=reset0;next_reset1_known=reset0_known;
  if((reset1_known && !reset1)||(next_reset1_known && !next_reset1))begin expect_head=0;head_known=1;end
  else if(reset1_known && reset1 && head_known && h1_known)expect_head=head(expect_head,h1[783:0],s1);
  else head_known=0;
  relay_known=h1_known;
  if(relay_known)begin expect_fan=h1[784+:334];expect_g=g1;expect_r=r1;end
  if(!head_known)unconstrained_head++;
  if(!relay_known)unconstrained_relay++;
  #0.001; // settle oracle continuous port-map wires on the SAME observed edge
'''+comparisons+'''
  if(assert_edges==2 && (!head_known || o_pc!==780'd0))begin errors++;$display("RESET_DEADLINE edge=%0d",edges);end
  if(release_edges==3 && i_ctl[0] && i_ctl[783])begin firstuses++;if(o_pc[1:0]!==2'b11 || o_pc[779]!==1'b1)begin errors++;$display("FIRST_USE_MISSING edge=%0d",edges);end end
  $display("EDGE edge=%0d rst=%0d assert_age=%0d release_age=%0d head_known=%0d relay_known=%0d observed_valid=%b boot=%b errors=%0d",edges,rst_n,assert_edges,release_edges,head_known,relay_known,o_pc[1:0],o_pc[779],errors);
  reset1=next_reset1;reset1_known=next_reset1_known;reset0=rst_n;reset0_known=1;
  h1=h0;g1=g0;r1=r0;s1=s0;h1_known=h0_known;
  h0=i_ctl;g0=i_g;r0=i_r;s0=esh__stack;h0_known=1;
  #0.9;ck=0;
 end
endtask
task stop_and_short_assert;
 begin
  stopped_outputs='''+pack+''';
  #1;rst_n=0;stimulus(0);#0.1;
  if('''+pack+'''!==stopped_outputs)begin errors++;$display("STOP_CLOCK_CHANGED");end
  #0.9;rst_n=1;#2;
  if('''+pack+'''!==stopped_outputs)begin errors++;$display("SHORT_ASSERT_CHANGED");end
  pulses++;stops++;
 end
endtask
initial begin
 ck=0;rst_n=1;esh__stack=0;i_ctl=0;i_g=0;i_r=0;
 if(!$value$plusargs("SEED=%d",seed))seed=17;seed_copy=seed;j=$urandom(seed_copy);
 #0.001;
'''+ '\n'.join(init)+'''
 $display("INITIAL_STATES seed=%0d independently_drawn_bits=%0d ones=%0d",seed,init_count,init_ones);
 if(init_count!=5645)$fatal(1,"bad state coupon");
 #0.009;rst_n=0;stimulus(0);
 for(ep=0;ep<8;ep++)begin
  rst_n=0;
  for(j=0;j<5;j++)begin stimulus(0);tick();end
  rst_n=1;esh__stack=2;
  for(j=0;j<1118;j++)i_ctl[j]=$urandom;
  i_ctl[1:0]=3;i_ctl[3:2]=3;i_ctl[5:4]=2;i_ctl[7:6]=2;i_ctl[783]=1;
  for(j=0;j<5;j++)begin stimulus(1);tick();end
  for(j=0;j<35;j++)begin stimulus(0);tick();end
  stop_and_short_assert();
 end
 $display("LEAF_COLD seed=%0d edges=%0d checks=%0d errors=%0d unconstrained_head=%0d unconstrained_relay=%0d firstuses=%0d short_pulses=%0d stopped_clock=%0d",seed,edges,checks,errors,unconstrained_head,unconstrained_relay,firstuses,pulses,stops);
 if(errors || firstuses!=8 || unconstrained_head!=1 || unconstrained_relay!=2)$fatal(1,"leaf cold contract failed");
 $display("LEAF_COLD_PASS");$finish;
end
endmodule
'''
(r/'tb.sv').write_text(tb);(r/'core.sv').write_text(core);(r/'top.sv').write_text(top)
manifest={'actual_source':'295504c93','core_sha256':hashlib.sha256(core.encode()).hexdigest(),'top_sha256':hashlib.sha256(top.encode()).hexdigest(),'oracle_abi_source':'295504c93:'+abi_path,'oracle_abi_sha256':hashlib.sha256(abi.encode()).hexdigest(),'oracle_function_source':'295504c93:results/rtl/kv_hroot_safe32_1020/reference.sv','independent_initial_state_bits':len(init),'scope':'Exactfullwrapper leafRTL localreset2 sampled edges, datathreeFF stages(inputE→outE+2), everyedgeobserver explicitprecontract unknown1head/2relay edges; physical2face resetFFs not inserted inDUT and composeport4separately.'};(r/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for variant,m in [('wrong',1),('bypass',2),('reset',3)]:
 (r/f'top_{variant}.sv').write_text(top.replace('#(.MUT(0))','#(.MUT('+str(m)+'))',1))
needle=' wire [779:0] n=head(prev,x,(MUT==1) ? sid^2\'d1 : sid);';assert core.count(needle)==1
late=core.replace(needle," wire [779:0] n_raw=head(prev,x,(MUT==1) ? sid^2'd1 : sid);\n reg first_valid_q; always @(posedge ck or negedge rn) if(!rn) first_valid_q<=1'b0;else first_valid_q<=1'b1;\n wire [779:0] n=first_valid_q ? n_raw : 780'd0;")
(r/'core_late.sv').write_text(late)
