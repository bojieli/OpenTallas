import re
s=open('../mu.sv').read()
hdr=s[s.index(')(\n')+3:s.index('\n);')]
ports=[]  # (dir,width,name)
for decl in re.split(r',\s*(?=input|output)',hdr.replace('\n',' ')):
    m=re.match(r'\s*(input|output)\s+(?:wire|reg)?\s*(\[[^\]]+\])?\s*(.*)',decl)
    d,w,names=m.groups()
    for n in names.split(','):
        n=n.strip()
        if n: ports.append((d,(w or '').replace('HCW-1','38'),n))
ins=[p for p in ports if p[0]=='input']; outs=[p for p in ports if p[0]=='output']
L=[]
L.append("`timescale 1ns/1ps\nmodule tb;\nparameter integer SEED=1, N=200000;\nreg ck=0; always #1 ck=~ck;")
for d,w,n in ins:
    if n!='ck': L.append(f"reg {w} {n};")
for d,w,n in outs: L.append(f"wire {w} r_{n}, d_{n};")
def inst(mod,pre,params):
    c=",".join(f".{n}({n})" if d=='input' else f".{n}({pre}{n})" for d,w,n in ports)
    return f"{mod} #({params}) u_{pre[0]}({c});"
P=".DIE(0),.MUT(0),.STRAPPED(1),.ENABLE_SERVICE(1),.ENABLE_TOKEN(1),.MU(1),.HCW(39)"
L.append(inst("qkd_host_ctrl_token_service_packet_collected_mu_ref","r_",P+",.CONST_LANE_WRITES(0)"))
L.append(inst("qkd_host_ctrl_token_service_packet_collected_mu","d_",P+",.CONST_LANE_WRITES(1),.HDR_PREDECODE(HP)"))
L.insert(1,"")
cmp=" || ".join(f"(r_{n}!==d_{n})" for d,w,n in outs)
names=" ".join(n for d,w,n in outs)
L.append("parameter integer HP=1;")
L.append("""integer sd; integer cyc, mism=0, nrxw=0, nfault=0, ntake=0, cut, b; reg [2:0] die; reg [511:0] f; reg [1:0] e;
function [511:0] frame(input integer dummy);
 reg [511:0] x; integer t,c,k;
 begin
  x={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
  t=$urandom%8; x[7:0]= t<3?8'h21: t<5?8'h22: t<7?8'h23: $urandom;
  c=$urandom%8; x[15:8]= c<3?8'd1: c<7?8'd2: $urandom;
  if($urandom%8) x[23:19]=0;
  x[18:16]= ($urandom%3==0)?3'd0:$urandom;
  x[31:24]= ($urandom%6)? (8'd1<<die) : (($urandom%2)?8'd1:$urandom);
  x[47:32]= $urandom%4;
  x[63:48]= $urandom%4; x[169:154]=$urandom%4; x[245:230]=$urandom%8; x[262:247]=$urandom%4;
  if($urandom%4) x[63:61]=0;
  if($urandom%4) x[231:230]=x[65:64];
  if($urandom%4) x[83:66]=$urandom%151936; else x[83:66]=151930+$urandom%12;
  k=$urandom%9; cut= k==0?64: k==1?65: k==2?87: k==3?153: k==4?170: k==5?230: k==6?263: k==7?512: 48+$urandom%464;
  for(b=0;b<512;b=b+1) if(b>=cut && !(b>=48 && b<87 && cut==87)) x[b]=0;
  if(cut==87 || cut==230 || cut==263) begin for(b=87;b<230;b=b+1) x[b]=0; end
  if($urandom%5==0) x[$urandom%512]=~x[$urandom%512];
  if($urandom%7==0) begin b=cut-1-($urandom%3); if(b>=24 && b<512) x[b]=1; end
  if($urandom%20<19) begin  // well-formed frame for the current role (expected sequence from the reference state)
   for(b=87;b<512;b=b+1) x[b]=0;
   x[23:19]=0; x[31:24]=8'd1<<die;
   if(die==0) begin x[7:0]=8'h21; x[15:8]=8'd2; x[18:16]=1+$urandom%7; x[169:154]=u_r.g_mu.epoch; x[153]=$urandom; for(b=87;b<154;b=b+1) x[b]=$urandom; end
   else begin x[18:16]=0; x[86]=0;
    if($urandom%3==0) begin x[7:0]=8'h22; x[15:8]=8'd1; end
    else if($urandom%2) begin x[7:0]=8'h22; x[15:8]=8'd2; x[86]=1; x[246]=1; x[65:64]=$urandom; x[231:230]=x[65:64]; x[83:66]=$urandom%151936;
      x[245:232]=$urandom; x[262:247]=u_r.g_mu.epoch; end
    else begin x[7:0]=8'h23; x[15:8]=8'd2; x[64]=$urandom%4==0; x[63:48]=u_r.g_mu.epoch+(x[64]?0:1); end end
   x[47:32]= u_r.g_mu.seq_seen[x[18:16]] ? u_r.g_mu.seq_rx[x[18:16]*16+:16]+16'd1+u_r.g_mu.count : 16'd0;
   if($urandom%20==0) x[$urandom%512]=1;
   if($urandom%10==0) begin k=$urandom%7; x[k==0?64:k==1?65:k==2?87:k==3?153:k==4?170:k==5?230:263]=1; end
  end
  frame=x;
 end
endfunction
initial begin
 rst_n=0; por_n=0; die=0; die_id=0; rx_v=0; rx_d=0; tx_cr=0; local_tk=0; local_kst=0; local_boot=0; cmd_v=0; cmd_hc=0;
 startup_allowed=0; local_service_ready=0; local_service_epoch=0; begin_v=0; begin_epoch=0; token_wrap_fence_valid=0; token_wrap_drained=0;
 token_wrap_link_reset_seen=0; token_wrap_retraining_done=0; token_allocator_fault=0; package_abort=0; abort_drained=0; token_request_ready=0;
 token_grant_valid=0; token_grant_epoch=0; token_grant_token=0; token_grant_position=0; token_grant_generation=0; token_grant_tag=0;
 allocated_valid=0; allocated_delivered=0; allocated_epoch=0; allocated_token=0; allocated_position=0; allocated_generation=0; terminal_accepted=0;
 sd=SEED; e=$urandom(sd);
 for(cyc=0;cyc<N;cyc=cyc+1) begin
  @(negedge ck);
  if(cyc==3) por_n=1;
  if(cyc==4) rst_n=1;
  if(cyc>10 && $urandom%250==0) begin rst_n=0; if($urandom%2) begin die=($urandom%3==0)?$urandom:0; end end else if(!rst_n && $urandom%3==0 && cyc>4) rst_n=1;
  if(cyc>10 && $urandom%20000==0) por_n=0; else if(!por_n && cyc>4) por_n=1;
  if($urandom%9000==0) die=$urandom;
  die_id=die;
  rx_v=($urandom%3==0) && u_r.g_mu.count+u_r.g_mu.rv<4; rx_d=frame(0);
  tx_cr=($urandom%4==0) && u_r.g_mu.credits<4;
  if($urandom%50==0) begin local_tk={$urandom,$urandom,$urandom}; local_kst=$urandom; local_boot=$urandom; end
  cmd_v=($urandom%25==0) && die==0 && u_r.g_mu.cn+u_r.g_mu.cv<4; cmd_hc={$urandom,$urandom}; if($urandom%3) cmd_hc[15:13]=0; cmd_hc[35:18]=$urandom%160000;
  if($urandom%200==0) startup_allowed=$urandom; if($urandom%40==0) local_service_ready=$urandom; if($urandom%60==0) local_service_epoch=$urandom%4;
  begin_v=($urandom%3000==0); begin_epoch=$urandom%5;
  token_wrap_fence_valid=($urandom%2000==0) || (r_fault && !u_r.g_mu.retained_request && !allocated_valid && !u_r.g_mu.allocated_vq && !r_cancel_valid && $urandom%40==0); token_wrap_drained=($urandom%64!=0); token_wrap_link_reset_seen=($urandom%64!=0); token_wrap_retraining_done=($urandom%64!=0);
  token_allocator_fault=($urandom%50000==0); package_abort=($urandom%1500==0); abort_drained=$urandom; token_request_ready=$urandom;
  token_grant_valid=($urandom%10==0); token_grant_epoch=$urandom%8; token_grant_token=$urandom; token_grant_position=$urandom%4; token_grant_generation=$urandom; token_grant_tag={$urandom,$urandom};
  allocated_valid=($urandom%32==0); allocated_delivered=($urandom%4==0); allocated_epoch=$urandom%8; allocated_token=$urandom; allocated_position=$urandom%4; allocated_generation=$urandom; terminal_accepted=$urandom;
  @(posedge ck); #0.5;
  if(u_r.g_mu.take) ntake=ntake+1;
  if(u_r.g_mu.take && u_r.g_mu.hdr && u_r.g_mu.sequence_ok && !u_r.fault) nrxw=nrxw+1;
  if(r_fault) nfault=nfault+1;
  if(""" + cmp + """) begin
   mism=mism+1;
   if(mism<6) begin $display("MISMATCH cyc=%0d", cyc);
""")
for d,w,n in outs:
    L.append(f'    if(r_{n}!==d_{n}) $display("  {n} ref=%h dut=%h", r_{n}, d_{n});')
L.append("""   end
  end
 end
 if(mism==0) $display("PASS SEED=%0d HP=%0d cycles=%0d take=%0d rx_accept=%0d fault_cycles=%0d", SEED, HP, N, ntake, nrxw, nfault);
 else $display("FAIL SEED=%0d HP=%0d mismatching cycles=%0d take=%0d rx_accept=%0d", SEED, HP, mism, ntake, nrxw);
 $finish;
end
endmodule""")
open('tb_hr_tx_predecode_lockstep.sv','w').write("\n".join(L)+"\n")
