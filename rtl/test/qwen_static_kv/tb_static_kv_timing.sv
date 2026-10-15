`timescale 1ns/1ps
// Profile the actual JEDEC timing RTL, then replay the frozen RD-slot table on
// separate production PROFILE=0 instances after a fresh declared reset. No
// response/ready signal enters the production controller. Raw row/column
// commands and all 128 PC sector addresses must match the compiled profile.
module tb_static_kv_timing;
 localparam N=128,CYCLES=7000;
 reg ck=0;always #0.512 ck=~ck;
 reg rst=0,dv=0,go=0,desired=0;reg [9:0] first=0;reg [10:0] last=0;
 reg [N-1:0] reserved=0;
 wire [N-1:0] pcv,prv,pf,psf,cv,rv,ff,sf;
 wire [4:0] pcb[0:N-1],pcc[0:N-1],prb[0:N-1],cb[0:N-1],cc[0:N-1],rb[0:N-1];
 wire [2:0] pro[0:N-1],ro[0:N-1];wire [18:0] prr[0:N-1],rr[0:N-1];
 reg [N-1:0] cmask[0:CYCLES-1],rmask[0:CYCLES-1];
 reg [9:0] caddr[0:CYCLES-1][0:N-1];
 reg [26:0] rcmd[0:CYCLES-1][0:N-1];
 integer count[0:N-1],errors=0,total=0,mode=0,fd;
 genvar p;
 generate for(p=0;p<N;p=p+1)begin:pcs
  wire unused0,unused1,unused2,unused3,unused4;
  ot_qkd_static_kv_timing #(.ENABLE(1),.PC(p%32),.REF_PHASE(((p%32)*118)/32),.PROFILE(2))profile(
   .clk(ck),.rst_n(rst),.desc_v(dv),.desc_r(),.desc_row(19'd67),.desc_n(last),.desc_first(first),.go(go),.next_posted(1'b0),
   .reserved_rd(desired),.reserved_static_col(1'b0),.reserved_write_col(1'b0),.schedule_fault(psf[p]),.row_v(prv[p]),.row_prio(),.row_gnt(1'b1),.row_op(pro[p]),.row_bank(prb[p]),.row_row(prr[p]),
   .col_v(pcv[p]),.col_bank(pcb[p]),.col_col(pcc[p]),.busy(),.ref_fault(pf[p]),
   .wr_v(1'b0),.wr_bank(5'b0),.wr_col(5'b0),.wr_r(),.col_we(),.wr_rd(1'b0),.col_aq(),
   .s_context(347'b0),.col_context(),.s_v(1'b0),.s_we(1'b0),.s_bank(5'b0),.s_col(5'b0),.s_row(19'b0),.s_r(),.col_sr(),.s_pop());
  ot_qkd_static_kv_timing #(.ENABLE(1),.PC(p%32),.REF_PHASE(((p%32)*118)/32),.PROFILE(0))production(
   .clk(ck),.rst_n(rst),.desc_v(dv),.desc_r(),.desc_row(19'd67),.desc_n(last),.desc_first(first),.go(go),.next_posted(1'b0),
   .reserved_rd(reserved[p]),.reserved_static_col(1'b0),.reserved_write_col(1'b0),.schedule_fault(sf[p]),.row_v(rv[p]),.row_prio(),.row_gnt(1'b1),.row_op(ro[p]),.row_bank(rb[p]),.row_row(rr[p]),
   .col_v(cv[p]),.col_bank(cb[p]),.col_col(cc[p]),.busy(),.ref_fault(ff[p]),
   .wr_v(1'b0),.wr_bank(5'b0),.wr_col(5'b0),.wr_r(),.col_we(),.wr_rd(1'b0),.col_aq(),
   .s_context(347'b0),.col_context(),.s_v(1'b0),.s_we(1'b0),.s_bank(5'b0),.s_col(5'b0),.s_row(19'b0),.s_r(),.col_sr(),.s_pop());
 end endgenerate
 task automatic drive(input integer t);
  desired=t<1200||(t>=1264&&(t-1264)%13==0);
  dv=(t==32||t==1200);go=(t==96||t==1264);first=t<1200?10'd0:10'd512;last=t<1200?11'd256:11'd768;
 endtask
 task automatic bad(input string msg);
  if(errors<10)$display("BAD %s",msg);errors++;
 endtask
 initial begin
  void'($value$plusargs("faultmode=%d",mode));
  for(integer p=0;p<N;p=p+1)count[p]=0;
  repeat(8)@(negedge ck);rst=1;
  fd=$fopen("compiled_pc_read_slots.hex","w");
  for(integer t=0;t<CYCLES;t=t+1)begin
   drive(t);@(posedge ck);
   cmask[t]=pcv;rmask[t]=prv;$fwrite(fd,"%032h\n",pcv);
   for(integer p=0;p<N;p=p+1)begin
    caddr[t][p]={pcb[p],pcc[p]};rcmd[t][p]={pro[p],prb[p],prr[p]};
    if(pcv[p])begin
     automatic integer j={pcb[p][4:2],pcc[p],pcb[p][1:0]};
     automatic integer o=count[p]-256;
     automatic integer expected=count[p]<256?count[p]:512+((o&8)<<4)+((o>>4)<<3)+(o&7);
     if(j!=expected)bad($sformatf("profile p%0d j%0d expected%0d",p,j,expected));
     count[p]++;total++;
    end
    if((p%2)==0&&prv[p]&&prv[p+1])bad("twoPC shared row-slot collision");
   end
   if(|pf)bad($sformatf("profile refreshfault t%0d %h",t,pf));
   @(negedge ck);
  end
  $fclose(fd);
  for(integer p=0;p<N;p=p+1)if(count[p]!=512)bad($sformatf("p%0d produced%0d sectors",p,count[p]));
  rst=0;dv=0;go=0;reserved=0;repeat(8)@(negedge ck);rst=1;
  for(integer t=0;t<CYCLES;t=t+1)begin
   drive(t);reserved=cmask[t];
   if(mode==1&&t>0)reserved=cmask[t-1];
   if(mode==2&&t==200)reserved[0]=0;
   if(mode==3&&t>=1200)first=10'd513;
   @(posedge ck);
   if(cv!==cmask[t])bad($sformatf("replay colmask t%0d",t));
   if(rv!==rmask[t])bad($sformatf("replay rowmask t%0d",t));
   for(integer p=0;p<N;p=p+1)begin
    if(cv[p]&&{cb[p],cc[p]}!==caddr[t][p])bad($sformatf("replay column p%0d t%0d",p,t));
    if(rv[p]&&{ro[p],rb[p],rr[p]}!==rcmd[t][p])bad($sformatf("replay row p%0d t%0d",p,t));
   end
   if((|ff)||(|sf))bad($sformatf("replay timing/schedule fault t%0d",t));
   @(negedge ck);
  end
  if(errors)begin $display("FAIL staticKV128 timing errors%0d mode%0d",errors,mode);$fatal(1);end
  $display("PASS staticKV128 timing PCs128 K256 V256consumerOrder sectors%0d period1024ps profilecycles7000 Vpace13 exactProductionReplay noCreditPort",total);$finish;
 end
endmodule
