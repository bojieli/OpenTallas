`timescale 1ns/1ps
// LH-UNREAD F-P 10-19: ot_hbm_static_cfg_collar_idx256 (reference) vs ot_hbm_static_cfg_collar_idx256r (packed operand
// face, reserved operand fields rejected). Legal random installs (reserved fields zero): every retained output bit equal
// every cycle (control/fault/ready/active/start/go, pw_addr[7:0]+pw_data on writes, packed prm vs reference prm of every
// loaded row, rec on go); reference pw_addr[11:8]==0 on every write. Then a nonzero reserved bit in every reserved range
// must fault the successor (reference does not), not load the row, and block a concurrent launch.
// MUT=12 (reserved check disabled) must FAIL with IDX256R_FAIL.
module tb_idx256r;
 parameter integer MUT=0;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0,cfg_v=0,desc_v=0,launch_v=0;
 reg [11:0] cfg_addr=0;reg[255:0]cfg_data=0;
 wire[0:0]we0,we1;wire[11:0]a0;wire[7:0]a1;wire[255:0]d0,d1;
 wire[1535:0]p0;wire[768:0]p1;wire s0,s1;wire[1:0]g0,g1;wire[220:0]r0,r1;
 wire rd0,rd1,ac0,ac1,f0,f1;
 ot_hbm_static_cfg_collar_idx256 #(.PAGE_W(1),.NS(1),.NPR(6),.NREC(8),.NGO(2),.NB(2),.NF(5)) ref_c(
 .clk(clk),.clk_in(clk),.rst_n(rst_n),.tgt(8'd120),.cfg_v(cfg_v),.cfg_target(8'd120),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.launch_v(launch_v),.c_busy(2'b0),.c_done(1'b0),.c_fault(5'b0),.pw_we(we0),.pw_addr(a0),.pw_data(d0),.prm(p0),.start_v(s0),.go(g0),.rec(r0),.ready(rd0),.active(ac0),.fault(f0));
 ot_hbm_static_cfg_collar_idx256r #(.PAGE_W(1),.NS(1),.NPR(6),.NREC(8),.NGO(2),.NB(2),.NF(5),.MUT(MUT)) dut(
 .clk(clk),.clk_in(clk),.rst_n(rst_n),.tgt(8'd120),.cfg_v(cfg_v),.cfg_target(8'd120),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.launch_v(launch_v),.c_busy(2'b0),.c_done(1'b0),.c_fault(5'b0),.pw_we(we1),.pw_addr(a1),.pw_data(d1),.prm(p1),.start_v(s1),.go(g1),.rec(r1),.ready(rd1),.active(ac1),.fault(f1));
 // reserved masks per operand row (bit=1 reserved)
 function automatic [255:0] rmask(input integer r);
  rmask=0;
  case(r)
   0: rmask[50:44]={7{1'b1}};
   1: rmask[255:168]={88{1'b1}};
   2: rmask[253:0]={254{1'b1}};
   4: rmask[255:84]={172{1'b1}};
   5: begin rmask[169:0]={170{1'b1}}; rmask[255:180]={76{1'b1}}; end
   default: rmask=0;
  endcase
 endfunction
 function automatic [768:0] pack(input [1535:0] p);
  pack={p[1459:1450],p[1107:766],p[423:51],p[43:0]};
 endfunction
 function automatic [768:0] rowmask(input [5:0] ld);   // packed bits belonging to loaded rows
  reg [1535:0] m; m=0;
  for(integer r=0;r<6;r++) if(ld[r]) m[r*256+:256]={256{1'b1}};
  rowmask=pack(m);
 endfunction
 bit compare=0,forbid_write=0,forbid_start=0; reg[5:0] ld=0;
 integer checks=0,writes=0,launches=0,cases=0,rejects=0;
 always @(posedge clk) begin
  #1;
  if(compare)begin
   checks++;
   if({we0,s0,g0,rd0,ac0,f0} !== {we1,s1,g1,rd1,ac1,f1}) $fatal(1,"IDX256R_FAIL control identity MUT%0d",MUT);
   if(we1 && ({a0[7:0],d0} !== {a1,d1} || a0[11:8]!==4'd0)) $fatal(1,"IDX256R_FAIL write identity");
   if(((pack(p0)^p1)&rowmask(ld))!==0)$fatal(1,"IDX256R_FAIL operand identity");
   if(|g1 && r0!==r1)$fatal(1,"IDX256R_FAIL record identity");
  end
  if(we1)writes++; if(s1)launches++;
  if(forbid_write && we1)$fatal(1,"IDX256R_FAIL bad install wrote");
  if(forbid_start && s1)$fatal(1,"IDX256R_FAIL bad install launched");
 end
 task automatic edges(input integer n); repeat(n)begin @(posedge clk);#2;end endtask
 task automatic reset_case;
  @(negedge clk);compare=0;forbid_write=0;forbid_start=0;ld=0;rst_n=0;cfg_v=0;desc_v=0;launch_v=0;
  edges(6);@(negedge clk);rst_n=1;edges(6);
 endtask
 task automatic frame(input[11:0]a,input[255:0]d);
  @(negedge clk);cfg_addr=a;cfg_data=d;cfg_v=1;
  @(negedge clk);cfg_v=0;edges(3);
 endtask
 task automatic arm; @(negedge clk);desc_v=1;@(negedge clk);desc_v=0;edges(4); endtask
 task automatic launch; @(negedge clk);launch_v=1;@(negedge clk);launch_v=0;edges(4); endtask
 function automatic [255:0] rnd256; for(integer i=0;i<8;i++) rnd256[i*32+:32]=$urandom; endfunction
 task automatic legal_operands;
  for(integer j=0;j<6;j++)begin frame(12'h800+12'(j),rnd256() & ~rmask(j)); ld[j]=1; end
 endtask
 task automatic install(input integer n);
  for(integer j=0;j<n;j++) frame(12'(j),rnd256());
 endtask
 reg [768:0] snap; reg [255:0] bad;
 initial begin
  // Legal random installs: 6 trials, random programme depth 1..256, random records, two launches per trial.
  for(integer trial=0;trial<6;trial++)begin
   integer n; n=(trial==0)?256:1+($urandom%256);
   reset_case();compare=1;
   legal_operands();
   for(integer j=0;j<8;j++)begin bad=rnd256(); bad[31:0]=32'(4+j*3); bad[32]=1; frame(12'hc00+12'(j),bad); end
   frame(12'he00,256'd0);install(n);frame(12'he01,256'(n));arm();
   if(!rd1||f1)$fatal(1,"IDX256R_FAIL legal install not ready trial%0d",trial);launch();edges(40);
   if(f1)$fatal(1,"IDX256R_FAIL legal launch faulted");
   legal_operands(); frame(12'd0,rnd256());frame(12'he01,256'd1);arm();launch();edges(40);cases++;
  end
  // Nonzero reserved operand field: every reserved range, low/high/random bit.
  for(integer r=0;r<6;r++) if(rmask(r)!=0) for(integer t=0;t<3;t++)begin
   integer b; reg [255:0] m;
   m=rmask(r); b=0; for(integer i=0;i<256;i++) if(m[i]) begin if(t==0 && b==0) b=i+1; if(t==1) b=i+1; end
   if(t==2) begin do b=1+($urandom%256); while(!m[b-1]); end
   reset_case();compare=0;
   for(integer j=0;j<6;j++) frame(12'h800+12'(j),rnd256() & ~rmask(j));
   snap=p1; bad=rnd256() & ~rmask(r); bad[b-1]=1'b1;
   frame(12'h800+12'(r),bad);
   if(!f1)$fatal(1,"IDX256R_FAIL nonzero reserved row%0d bit%0d accepted MUT%0d",r,b-1,MUT);
   if(f0)$fatal(1,"IDX256R_FAIL reference faulted on reserved (counterexample lost)");
   if(p1!==snap)$fatal(1,"IDX256R_FAIL rejected reserved row loaded");
   rejects++;
  end
  // Reserved violation concurrent with launch must not launch.
  reset_case();legal_operands();install(4);frame(12'he01,256'd4);arm();forbid_start=1;
  bad=rmask(2) & rnd256(); bad[0]=1'b1;
  @(negedge clk);cfg_addr=12'h802;cfg_data=bad;cfg_v=1;launch_v=1;
  @(negedge clk);cfg_v=0;launch_v=0;edges(5);
  if(!f1)$fatal(1,"IDX256R_FAIL concurrent reserved rejection");cases++;
  $display("IDX256R_PASS cases=%0d reserved_rejects=%0d identity_edges=%0d writes=%0d launches=%0d MUT=%0d",cases,rejects,checks,writes,launches,MUT);$finish;
 end
endmodule
