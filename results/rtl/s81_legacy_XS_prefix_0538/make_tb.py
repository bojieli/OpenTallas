from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-ds-legacy-xs-gate-0538')
ports=[('ro_e',1104),('ro_w',1104),('vo',276),('nx_wi',173),('nx_ei',173),('dl_ev',1),('dl_e',1104),('dl_wv',1),('dl_w',1104),('dl_vv',1),('dl_vb',276),('xw_d',1101),('fault',1)]
W=sum(n for _,n in ports)
s='''`timescale 1ps/1ps
module tb;
reg clk=0;always begin #416 clk=1;#417 clk=0;end
reg rst_n=0,is_v=0;reg[159:0]is_d=0;reg[1103:0]rw=0,re=0;reg[4:0]xv=0,xs=0;reg[1379:0]xd=0;
integer cyc=0,ep=0,ne=0,ct[0:127],rc,fd,tt,fill=-1,wait_n=0,gathers=0,gopulses=0,xwords=0,checks=0;
reg[159:0]cmd[0:127],vv;reg[71:0]gold[0:28671];
initial begin $readmemh("oracle.hex",gold);fd=$fopen("control.txt","r");
 while(!$feof(fd))begin rc=$fscanf(fd,"%d %h\\n",tt,vv);if(rc==2)begin ct[ne]=tt;cmd[ne]=vv;ne++;end end $fclose(fd);end
function automatic[1103:0]beat(input integer index,input bit bf);reg[1103:0]v;begin
 v=0;v[0]=1;v[3:1]=bf?3'd2:3'd1;v[8:4]=1;v[12:9]=7;v[19:13]=7'(index);
 if(bf)begin for(integer k=0;k<64;k++)v[21+16*k+:16]=16'h3f00+16'((index+k)&255);end
 else begin for(integer k=0;k<32;k++)begin v[21+8*k+:8]=8'h20+8'(index%32);v[287+8*k+:8]=8'ha0+8'(index%32);end v[277+:10]=127;v[543+:10]=127;end
 beat=v;end endfunction
'''
for name in ['old_o','def_o','equ_o','south_o']:s+=f'wire[{W-1}:0]{name};\n'
common='.clk(clk),.rst_n(rst_n),.ri_w(rw),.ri_e(re),.vi(276\'d0),.xf_v(xv),.xf_s(xs),.xf(xd),.nx_eo(173\'d0),.nx_wo(173\'d0),.ci_dir(3\'d0),.ci_b(1076\'d0),.is_v(is_v),.is_d(is_d)'
for typ,param,inst,sid,out in [('ot_s81sl_xg_gate_ref','','refx',7,'old_o'),('ot_s81sl_xg','','defx',7,'def_o'),('ot_s81sl_xg','#(.INSTANCE("u_s_3N.u_slice.u_xg"))','eqx',7,'equ_o'),('ot_s81sl_xg','#(.INSTANCE("u_s_3S.u_sl.u_xg"))','southx',6,'south_o')]:
 off=0;op=[]
 for port,n in ports:op.append(f'.{port}({out}[{off}+:{n}])');off+=n
 s+=f'{typ} {param} {inst}({common},.sid(4\'d{sid}),'+','.join(op)+');\n'
s+='''always@(negedge clk)begin
 is_v=0;is_d=0;rw=0;re=0;xv=0;xs=0;xd=0;
 if(cyc==8)rst_n=1;
 if(ep<ne&&ct[ep]==cyc)begin is_v=1;is_d=cmd[ep];ep++;end
 if(refx.u_s.o_gw&&!refx.u_s.o_gw_fam)begin fill=0;wait_n=8;end
 else if(fill>=0&&fill<40)begin
  if(wait_n>0)wait_n--;else begin rw=beat(fill,0);re=beat(fill+40,0);fill++;end
 end
 if(cyc==900)begin is_v=1;is_d=160'd1<<120|160'd1<<121;end
 if(cyc>=920&&cyc<952)begin
  xv[2]=1;xs[2]=((cyc-920)%4==0);xd[552+:276]=beat((cyc-920)/4,1)>>((cyc-920)%4*276);
 end
end
always@(posedge clk)begin cyc++;#2;
 if(cyc>20)begin
  if(old_o!==def_o||old_o!==equ_o)$fatal(1,"NATIVE_LEGACY_PORT_MISMATCH cycle=%0d",cyc);
  if({refx.u_s.gv_q,refx.u_s.gf_q,refx.u_s.gi_q,refx.u_s.gd_q,refx.u_s.isv_q,refx.u_s.isd_q,refx.u_s.o_go,refx.u_s.o_gw} !== {defx.u_s.gv_q,defx.u_s.gf_q,defx.u_s.gi_q,defx.u_s.gd_q,defx.u_s.isv_q,defx.u_s.isd_q,defx.u_s.o_go,defx.u_s.o_gw})$fatal(1,"LEGACY_CAPTURE_DEFAULT_MISMATCH");
  if({refx.u_s.gv_q,refx.u_s.gf_q,refx.u_s.gi_q,refx.u_s.gd_q,refx.u_s.isv_q,refx.u_s.isd_q,refx.u_s.o_go,refx.u_s.o_gw} !== {eqx.u_s.gv_q,eqx.u_s.gf_q,eqx.u_s.gi_q,eqx.u_s.gd_q,eqx.u_s.isv_q,eqx.u_s.isd_q,eqx.u_s.o_go,eqx.u_s.o_gw})$fatal(1,"LEGACY_CAPTURE_PREFIX_MISMATCH");
  checks++;
 end
 gathers+=refx.g_v[0]+refx.g_v[1]+refx.g_v[2];
 if(refx.u_s.o_go)begin gopulses++;$display("LEGACY_NATIVE_DECODED_GO %0d",cyc);end
 if(old_o[5317])xwords++;
end
integer addr;reg[71:0]nword,sword;
always@(negedge clk)begin #2;
 if(cyc>20)begin addr=(cyc*131)%4096;
'''
roms=['u_cal_action','u_cal_time','u_phase0','u_stream0','u_stream1','u_stream2','u_stream3']
for j,rom in enumerate(roms):
 marker=sum((0xa0+j+i)<<(8*i) for i in range(9))
 s+=f'''if(refx.u_s.{rom}.word_read(addr)!==gold[{j}*4096+addr]||defx.u_s.{rom}.word_read(addr)!==gold[{j}*4096+addr]||eqx.u_s.{rom}.word_read(addr)!==gold[{j}*4096+addr])$fatal(1,"LEGACY_NATIVE_IMAGE_MISMATCH ROM={rom} addr=%0d",addr);
if(southx.u_s.{rom}.word_read(addr)!==72'h{marker:018x})$fatal(1,"LEGACY_NATIVE_NAMESPACE_LEAK ROM={rom}");\n'''
s+='''end
 if(cyc==1200)begin
  if(gopulses<1||gathers<88||checks<1000)$fatal(1,"NATIVE_GATE_INSUFFICIENT_ACTIVITY go=%0d gathers=%0d checks=%0d",gopulses,gathers,checks);
  $display("PASS_NATIVE_LEGACY_XG_XS_PREFIX cycles=%0d checks=%0d gathers=%0d go=%0d xwords=%0d fault=%b defaultempty_and_identicalprefix_exact distinct_namespaces2 native_ROMs7 added_capture0",cyc,checks,gathers,gopulses,xwords,old_o[6418]);$finish;
 end
end
endmodule
'''
(R/'tb.sv').write_text(s)
