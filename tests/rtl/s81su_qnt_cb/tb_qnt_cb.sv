`timescale 1ns/1ps
module tb_qnt_cb #(parameter integer MUT=0);
reg clk=0; always #5 clk=~clk;
reg rst_in=0, dn_st_i=0;
reg [3:0] dn_kind_i=0;
reg [1:0] dn_gsel_i=0;
reg [7:0] dn_jid_i=0;
reg [15:0] dn_v_i=0;
reg [4095:0] dn_d_i=0;
reg [32:0] i_f=0;
integer cycles=0, checks=0, jobs=0, starts=0, resets=0, valid_rows=0, go_count=0;
integer valid_cycles=0, fault_cycles=0, mask_empty=0, mask_full=0, mask_partial=0;
reg [3:0] qn_selectors=0, gq_selectors=0;
integer counts[0:15];
wire [15:0] ref_e_v;
wire [4095:0] ref_e_d;
wire [127:0] ref_e_t;
wire [0:0] ref_e_gq;
wire [1:0] ref_e_gr;
wire [1:0] ref_e_gw;
wire [0:0] ref_e_go;
wire [13:0] ref_e_ob;
wire [31:0] ref_e_eps;
wire [0:0] ref_o_fu;
wire [0:0] ref_o_fo;
wire [0:0] ref_o_alive;
wire [0:0] ref_o_den;
wire [0:0] ref_o_rdy;
wire [7:0] ref_o_rjid;
ot_s81_su_qnt_reference #(.N(256),.S_RD(16),.NFI(33),.MUT(0)) u_ref (.clk(clk),.rst_in(rst_in),.dn_st_i(dn_st_i),.dn_kind_i(dn_kind_i),.dn_gsel_i(dn_gsel_i),.dn_jid_i(dn_jid_i),.dn_v_i(dn_v_i),.dn_d_i(dn_d_i),.i_f(i_f),.e_v(ref_e_v),.e_d(ref_e_d),.e_t(ref_e_t),.e_gq(ref_e_gq),.e_gr(ref_e_gr),.e_gw(ref_e_gw),.e_go(ref_e_go),.e_ob(ref_e_ob),.e_eps(ref_e_eps),.o_fu(ref_o_fu),.o_fo(ref_o_fo),.o_alive(ref_o_alive),.o_den(ref_o_den),.o_rdy(ref_o_rdy),.o_rjid(ref_o_rjid));
wire [15:0] cb32_e_v;
wire [4095:0] cb32_e_d;
wire [127:0] cb32_e_t;
wire [0:0] cb32_e_gq;
wire [1:0] cb32_e_gr;
wire [1:0] cb32_e_gw;
wire [0:0] cb32_e_go;
wire [13:0] cb32_e_ob;
wire [31:0] cb32_e_eps;
wire [0:0] cb32_o_fu;
wire [0:0] cb32_o_fo;
wire [0:0] cb32_o_alive;
wire [0:0] cb32_o_den;
wire [0:0] cb32_o_rdy;
wire [7:0] cb32_o_rjid;
ot_s81_su_qnt #(.N(256),.S_RD(16),.NFI(33),.CB(32),.MUT(MUT)) u_cb32 (.clk(clk),.rst_in(rst_in),.dn_st_i(dn_st_i),.dn_kind_i(dn_kind_i),.dn_gsel_i(dn_gsel_i),.dn_jid_i(dn_jid_i),.dn_v_i(dn_v_i),.dn_d_i(dn_d_i),.i_f(i_f),.e_v(cb32_e_v),.e_d(cb32_e_d),.e_t(cb32_e_t),.e_gq(cb32_e_gq),.e_gr(cb32_e_gr),.e_gw(cb32_e_gw),.e_go(cb32_e_go),.e_ob(cb32_e_ob),.e_eps(cb32_e_eps),.o_fu(cb32_o_fu),.o_fo(cb32_o_fo),.o_alive(cb32_o_alive),.o_den(cb32_o_den),.o_rdy(cb32_o_rdy),.o_rjid(cb32_o_rjid));
wire [15:0] cb16_e_v;
wire [4095:0] cb16_e_d;
wire [127:0] cb16_e_t;
wire [0:0] cb16_e_gq;
wire [1:0] cb16_e_gr;
wire [1:0] cb16_e_gw;
wire [0:0] cb16_e_go;
wire [13:0] cb16_e_ob;
wire [31:0] cb16_e_eps;
wire [0:0] cb16_o_fu;
wire [0:0] cb16_o_fo;
wire [0:0] cb16_o_alive;
wire [0:0] cb16_o_den;
wire [0:0] cb16_o_rdy;
wire [7:0] cb16_o_rjid;
ot_s81_su_qnt #(.N(256),.S_RD(16),.NFI(33),.CB(16),.MUT(0)) u_cb16 (.clk(clk),.rst_in(rst_in),.dn_st_i(dn_st_i),.dn_kind_i(dn_kind_i),.dn_gsel_i(dn_gsel_i),.dn_jid_i(dn_jid_i),.dn_v_i(dn_v_i),.dn_d_i(dn_d_i),.i_f(i_f),.e_v(cb16_e_v),.e_d(cb16_e_d),.e_t(cb16_e_t),.e_gq(cb16_e_gq),.e_gr(cb16_e_gr),.e_gw(cb16_e_gw),.e_go(cb16_e_go),.e_ob(cb16_e_ob),.e_eps(cb16_e_eps),.o_fu(cb16_o_fu),.o_fo(cb16_o_fo),.o_alive(cb16_o_alive),.o_den(cb16_o_den),.o_rdy(cb16_o_rdy),.o_rjid(cb16_o_rjid));
wire [15:0] default_e_v;
wire [4095:0] default_e_d;
wire [127:0] default_e_t;
wire [0:0] default_e_gq;
wire [1:0] default_e_gr;
wire [1:0] default_e_gw;
wire [0:0] default_e_go;
wire [13:0] default_e_ob;
wire [31:0] default_e_eps;
wire [0:0] default_o_fu;
wire [0:0] default_o_fo;
wire [0:0] default_o_alive;
wire [0:0] default_o_den;
wire [0:0] default_o_rdy;
wire [7:0] default_o_rjid;
ot_s81_su_qnt #(.N(256),.S_RD(16),.NFI(33),.MUT(0)) u_default (.clk(clk),.rst_in(rst_in),.dn_st_i(dn_st_i),.dn_kind_i(dn_kind_i),.dn_gsel_i(dn_gsel_i),.dn_jid_i(dn_jid_i),.dn_v_i(dn_v_i),.dn_d_i(dn_d_i),.i_f(i_f),.e_v(default_e_v),.e_d(default_e_d),.e_t(default_e_t),.e_gq(default_e_gq),.e_gr(default_e_gr),.e_gw(default_e_gw),.e_go(default_e_go),.e_ob(default_e_ob),.e_eps(default_e_eps),.o_fu(default_o_fu),.o_fo(default_o_fo),.o_alive(default_o_alive),.o_den(default_o_den),.o_rdy(default_o_rdy),.o_rjid(default_o_rjid));
wire [4304:0] ref_all = {ref_e_v,ref_e_d,ref_e_t,ref_e_gq,ref_e_gr,ref_e_gw,ref_e_go,ref_e_ob,ref_e_eps,ref_o_fu,ref_o_fo,ref_o_alive,ref_o_den,ref_o_rdy,ref_o_rjid};
wire [4304:0] cb32_all = {cb32_e_v,cb32_e_d,cb32_e_t,cb32_e_gq,cb32_e_gr,cb32_e_gw,cb32_e_go,cb32_e_ob,cb32_e_eps,cb32_o_fu,cb32_o_fo,cb32_o_alive,cb32_o_den,cb32_o_rdy,cb32_o_rjid};
wire [4304:0] cb16_all = {cb16_e_v,cb16_e_d,cb16_e_t,cb16_e_gq,cb16_e_gr,cb16_e_gw,cb16_e_go,cb16_e_ob,cb16_e_eps,cb16_o_fu,cb16_o_fo,cb16_o_alive,cb16_o_den,cb16_o_rdy,cb16_o_rjid};
wire [4304:0] default_all = {default_e_v,default_e_d,default_e_t,default_e_gq,default_e_gr,default_e_gw,default_e_go,default_e_ob,default_e_eps,default_o_fu,default_o_fo,default_o_alive,default_o_den,default_o_rdy,default_o_rjid};
wire [15:0] active_data_bad;
genvar ap;
generate for(ap=0;ap<16;ap=ap+1) begin : g_active_check
 assign active_data_bad[ap]=ref_e_v[ap] && (cb32_e_d[ap*256+:256] !== ref_e_d[ap*256+:256]);
end endgenerate
task tick;
 begin
  @(posedge clk); #1;
  cycles=cycles+1;
  if (cycles>8) begin
   checks=checks+1;
   if ((MUT==0 && (cb32_all !== ref_all || cb16_all !== ref_all || default_all !== ref_all)) ||
       (MUT!=0 && (|active_data_bad))) begin
    $display("FAIL QNT_CB active_data=%0d cycle=%0d MUT=%0d ev_ref=%h ev_cb32=%h ev_cb16=%h diff32=%h diff16=%h diff_default=%h",|active_data_bad,cycles,MUT,ref_e_v,cb32_e_v,cb16_e_v,cb32_all^ref_all,cb16_all^ref_all,default_all^ref_all);
    $fatal(1,"cycle-by-cycle output mismatch");
   end
   if (|ref_e_v) valid_cycles=valid_cycles+1;
   for (integer b=0;b<16;b=b+1) if(ref_e_v[b]) begin valid_rows=valid_rows+1; counts[b]=counts[b]+1; end
   if(ref_e_go) go_count=go_count+1;
   if(ref_o_fu) fault_cycles=fault_cycles+1;
  end
  @(negedge clk);
 end
endtask
task payload;
 begin
  for(integer b=0;b<128;b=b+1) dn_d_i[b*32+:32]=$urandom;
 end
endtask
task group(input reg [15:0] mask);
 begin
  dn_v_i=mask; payload();
  if(mask==0) mask_empty=mask_empty+1;
  else if(mask==16'hffff) mask_full=mask_full+1;
  else mask_partial=mask_partial+1;
  tick();
 end
endtask
task reset_now;
 begin
  rst_in=0; dn_st_i=0; dn_v_i=0; i_f=0; dn_d_i=0; resets=resets+1;
  repeat(5) tick();
  rst_in=1; repeat(5) tick();
 end
endtask
task job(input integer kind, input integer selector, input integer length, input integer sparse);
 integer n, left, sz;
 reg [15:0] mask;
 begin
  jobs=jobs+1; starts=starts+1;
  dn_st_i=1; dn_kind_i=kind; dn_gsel_i=selector; dn_jid_i=jobs;
  dn_v_i=0; payload(); tick(); dn_st_i=0;
  if(kind==0) qn_selectors[selector]=1;
  if(kind==6) gq_selectors[selector]=1;
  // Parameter row must be slot zero, as on the production spine.
  dn_v_i=1; payload(); dn_d_i[13:0]=14'(jobs*73); dn_d_i[96+:32]=32'h358637bd ^ jobs; tick();
  left=length;
  while(left>0) begin
   if (($urandom%5)==0) group(0);
   sz=1+($urandom%16); if(sz>left) sz=left;
   mask=(17'd1<<sz)-1;
   if(sparse!=0) begin
    // Uneven valid slots preserve the immutable component's existing slot-index semantics.
    mask=$urandom;
    if(mask==0) mask=1;
    sz=$countones(mask);
   end
   group(mask); left=left-sz;
  end
  group(0); group(0); group(0);
 end
endtask
initial begin
 integer seed, dummy;
 seed=32'h5181c032; dummy=$urandom(seed);
 for(integer b=0;b<16;b=b+1) counts[b]=0;
 reset_now();
 for(integer sel=0;sel<4;sel=sel+1) begin job(6,sel,256,0); job(0,sel,256,0); end
 for(integer j=0;j<96;j=j+1) begin
  if(j%13==0) reset_now();
  job(j%9==0 ? 3 : (j%2==0 ? 0 : 6),j%4,16+($urandom%1024),j%3==0);
  if(j%17==0) begin i_f=33'd1<<(j%33); group(0); i_f=0; end
 end
 // Reset while a job is live, then start immediately after reset synchronization.
 dn_st_i=1; dn_kind_i=0; dn_gsel_i=3; dn_v_i=16'hffff; payload(); tick(); reset_now();
 job(0,3,8192,0);
 // Long stream exercises vector index wrap and the 16-bit row counter.
 job(6,2,66000,0);
 repeat(8) group(0);
 if(qn_selectors!=15 || gq_selectors!=15 || valid_rows<1000 || go_count<4 || mask_partial==0 || mask_full==0 || mask_empty==0) $fatal(1,"coverage incomplete");
 for(integer b=0;b<16;b=b+1) if(counts[b]==0) $fatal(1,"uncovered position %0d",b);
 $display("PASS QNT_CB N=256 S_RD=16 NFI=33 MUT=%0d cycles=%0d checks=%0d jobs=%0d starts=%0d resets=%0d valid_rows=%0d valid_cycles=%0d parameter_pulses=%0d fault_cycles=%0d empty=%0d full=%0d uneven=%0d qn_selectors=%h gq_selectors=%h added_cycles=0",MUT,cycles,checks,jobs,starts,resets,valid_rows,valid_cycles,go_count,fault_cycles,mask_empty,mask_full,mask_partial,qn_selectors,gq_selectors);
 $finish;
end
endmodule
