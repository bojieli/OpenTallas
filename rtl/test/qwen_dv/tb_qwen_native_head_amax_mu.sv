`timescale 1ns/1fs
// Qualified native post values, assembled across sequential two-lane contexts.
// This executes the logical NU4 MU component, not flattened hardctl or ROOT.
module tb_qwen_native_head_amax_mu;
 reg ck=0;always #0.416500 ck=~ck;
 reg rst=0,c_stn=0,stn_amax_bit=0,r_v=0,c_am=0,am_clr=0,am_emit_cmd=0;
 reg[1:0] stn_user=0,am_user=0;
 reg[23:0] r_addr=0;reg[511:0] r_d=0;
 reg[8:0] stn_left=0,next_words=0;
 reg[23:0] stn_dbase=0,next_dbase=0;
 wire stn_pend=(stn_left!=0)&&!(stn_left==1&&r_v);
 // Exact selected logical ctl pending rule; sender mode is never used here.
 always @(posedge ck or negedge rst)
  if(!rst)stn_left<=0;
  else if(c_stn)begin stn_left<=next_words;stn_dbase<=next_dbase;end
  else if(r_v&&stn_left!=0)stn_left<=stn_left-1;
 wire[3:0] av,empty,fault;
 wire[23:0] ai[0:3];wire[31:0] ax[0:3];wire[1:0] au[0:3];
 reg[511:0] rows[0:10];reg[56:0] gold[0:3];
 reg[2:0] detected=0;
 integer cycle=0,inputs=0,emits=0,m;string dir;
 for(genvar g=0;g<4;g=g+1)begin:models
  localparam integer MUTATION=g==0?0:g==1?2:g==2?3:4;
  qfd_dv_amax_mu #(.NU(4),.MUT(MUTATION)) dut(
   .ck(ck),.rst(rst),.c_stn(c_stn),.stn_amax_bit(stn_amax_bit),.stn_user(stn_user),.stn_pend(stn_pend),
   .r_v(r_v),.r_addr(r_addr),.r_d(r_d),.c_am(c_am),.am_clr(am_clr),.am_emit_cmd(am_emit_cmd),.am_user(am_user),
   .am_v(av[g]),.am_idx(ai[g]),.am_val(ax[g]),.am_u(au[g]),.emit_empty(empty[g]),.mu_fault(fault[g]));
 end
 always @(posedge ck) begin
  cycle=cycle+1;
  if(cycle>200)$fatal(1,"AMAX watchdog inputs=%0d emits=%0d",inputs,emits);
 end
 task automatic tick;
  @(posedge ck);#0.2;
  if(rst&&fault[0])$fatal(1,"baseline native MU fault cycle=%0d",cycle);
 endtask
 task automatic quiet(input integer n);
  repeat(n)begin @(negedge ck);c_stn=0;r_v=0;c_am=0;am_clr=0;am_emit_cmd=0;tick();end
 endtask
 task automatic clear_user(input integer u);
  @(negedge ck);c_stn=0;r_v=0;c_am=1;am_clr=1;am_emit_cmd=0;am_user=2'(u);tick();
 endtask
 task automatic issue(input integer u,input integer words);
  @(negedge ck);c_am=0;am_clr=0;am_emit_cmd=0;r_v=0;c_stn=1;stn_amax_bit=1;stn_user=2'(u);next_words=9'(words);next_dbase=0;tick();
 endtask
 task automatic beat(input integer vi,input bit change,input integer nu,input integer words,input bit armed);
  @(negedge ck);c_am=0;am_clr=0;am_emit_cmd=0;r_v=1;r_d=rows[vi];
  r_addr=vi<8?24'(16*vi):24'(18944+16*(vi-8));
  c_stn=change;if(change)begin
   stn_user=2'(nu);next_words=9'(words);stn_amax_bit=armed;
   case(vi)
    0:next_dbase=64;4:next_dbase=18944;8:next_dbase=16;
    1:next_dbase=80;5:next_dbase=18960;9:next_dbase=32;
    2:next_dbase=96;6:next_dbase=18976;10:next_dbase=48;
    3:next_dbase=112;7:next_dbase=0;
   endcase
  end
  if(r_addr!==stn_dbase||stn_left!=1)$fatal(1,"illegal one-word STN result address got=%0d descriptor=%0d left=%0d",r_addr,stn_dbase,stn_left);
  if(change&&!(stn_left==1&&r_v))$fatal(1,"illegal STN overlap");
  inputs=inputs+1;tick();
 endtask
 task automatic emit_user(input integer u);
  @(negedge ck);c_stn=0;r_v=0;c_am=1;am_clr=0;am_emit_cmd=1;am_user=2'(u);tick();
  if(!av[0]||empty[0]||au[0]!==2'(u)||{ai[0],ax[0]}!==gold[u][55:0])
   $fatal(1,"AMAX mismatch user=%0d valid=%b empty=%b tag=%0d idx=%0d value=%h expected=%h",u,av[0],empty[0],au[0],ai[0],ax[0],gold[u]);
  for(m=1;m<4;m=m+1)if(!av[m]||empty[m]||au[m]!==2'(u)||{ai[m],ax[m]}!==gold[u][55:0])begin
   detected[m-1]=1;
   $display("DETECTED_NATIVE_MUTANT mut=%0d command_user=%0d valid=%b tag=%0d idx=%0d value=%h",m+1,u,av[m],au[m],ai[m],ax[m]);
  end
  emits=emits+1;
  $display("AMAX_CANDIDATE user=%0d index=%0d value=%h",u,ai[0],ax[0]);
 endtask
 initial begin
  if(!$value$plusargs("INPUT=%s",dir))$fatal(1,"INPUT required");
  $readmemh({dir,"/checked_scaled_rows.hex"},rows);$readmemh({dir,"/expected_candidates.hex"},gold);
  repeat(6)tick();@(negedge ck);rst=1;quiet(2);
  clear_user(0);clear_user(1);issue(0,1);
  beat(0,1,0,1,1);beat(4,1,0,1,1);beat(8,1,1,1,1);
  beat(1,1,1,1,1);beat(5,1,1,1,1);beat(9,1,2,1,1);
  quiet(6);clear_user(2);
  beat(2,1,2,1,1);beat(6,1,2,1,1);beat(10,1,3,1,1);
  quiet(6);clear_user(3);
  beat(3,1,3,1,1);beat(7,1,2,1,0);
  quiet(6);
  emit_user(0);emit_user(1);emit_user(2);emit_user(3);quiet(2);
  if(inputs!=11||emits!=4||detected!==3'b111)$fatal(1,"AMAX counts/control causal coverage inputs=%0d emits=%0d detected=%b",inputs,emits,detected);
  $display("PASS_NATIVE_AMAX_MU_COMPONENT checked_scalars176 vectors11 users4 native_MUT2_MUT3_MUT4_detected nominal833ps");$finish;
 end
endmodule
