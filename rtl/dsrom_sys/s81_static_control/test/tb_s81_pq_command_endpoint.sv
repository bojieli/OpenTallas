`timescale 1ns/1ps
module tb_s81_pq_command_endpoint;
`ifndef ENDPOINT_MUT
`define ENDPOINT_MUT 0
`endif
`ifndef ENDPOINT_PHW
`define ENDPOINT_PHW 9
`endif
`ifndef ENDPOINT_PINREG
`define ENDPOINT_PINREG 0
`endif
 localparam PHW=`ENDPOINT_PHW,NATIVE_BITS=81+PHW,PINREG=`ENDPOINT_PINREG;
 reg ck=0,rst_n=0;always #5 ck=~ck;
 reg pw_v=0,job_v=0;reg[6:0]pw_a=0;reg[27:0]pw_d=0;reg[35:0]desc_pw=0;
 wire[12:0]cv;wire[1091:0]cd;wire[8:0]done;wire[1:0]st;
 wire[NATIVE_BITS+1:0]f_iss;reg[38:0]t_iss=3;wire sealed,fault,busy,jdone;wire[1:0]phase;
 wire[12:0]dv={12'd0,done[8]};wire[103:0]dt={96'd0,done[7:0]};
 ot_s81_fixed_issue #(.STAGE(7),.ENG_PRESENT(1))issuer(
 .clk(ck),.rst_n(rst_n),.pw_v(pw_v),.pw_a(pw_a),.pw_d(pw_d),.prog_len(8'd128),
 .job_v(job_v),.job_user(10'd37),.job_pos(21'd1048575),.job_tok(21'd21946),
 .busy(busy),.job_done(jdone),.cmd_v(cv),.cmd_d(cd),.engine_available({12'd0,st[1]}),
 .dn_v(dv),.dn_tag(dt),.fault(fault),.phase(phase));
 ot_s81_pq_command_endpoint #(.MUT(`ENDPOINT_MUT),.PHW(PHW),.PINREG(PINREG))endpoint(
 .ck(ck),.rst_n(rst_n),.c_cmd({cv[0],cd[83:0]}),.f_desc_pw(desc_pw),.t_iss(t_iss),
 .f_iss(f_iss),.c_done(done),.c_st(st),.image_sealed(sealed));
 reg[34:0]program_words[0:385];reg[35:0]descs[0:21];
 integer mode=0,i,tick=0,commands=0,gos=0,completions=0,ends=0;
 reg fault_seen=0;
 integer cmd_tick=-1,expected_done=-1,expected_go=-1;
 integer pq_age[0:3];integer next_native_tag=0,z;reg[7:0]due_tags[0:3999];reg due_valid[0:3999];
 reg[7:0]expected_tag;reg[NATIVE_BITS-1:0]expected_fields;
 initial begin
  if($value$plusargs("mode=%d",mode))begin end
  $readmemh("program.hex",program_words);$readmemh("descriptor.hex",descs);$readmemh("fields.hex",expected_fields_mem);
  expected_fields=expected_fields_mem[0];
  for(z=0;z<4000;z=z+1)begin due_valid[z]=0;due_tags[z]=0;end
  repeat(4)@(negedge ck);rst_n=1;
  for(i=0;i<22;i=i+1)begin @(negedge ck);desc_pw=descs[i]|36'h800000000;end
  @(negedge ck);desc_pw=0;
  for(i=0;i<386;i=i+1)begin
   @(negedge ck);pw_v=1;pw_a=program_words[i][34:28];pw_d=program_words[i][27:0];
  end
  @(negedge ck);pw_v=0;repeat(140)@(negedge ck);
  if(!sealed)$fatal(1,"actual descriptor image did not seal");
  while(phase!=3)@(negedge ck);job_v=1;@(negedge ck);job_v=0;
  repeat(603)@(negedge ck);
  while(phase!=3)@(negedge ck);job_v=1;@(negedge ck);job_v=0;
  repeat(600)@(negedge ck);
  if(commands!=252||gos!=252||completions!=252||ends!=2)$fatal(1,"lost hardware commands %0d/%0d/%0d/%0d",commands,gos,completions,ends);
  if((mode==0&&(fault||st[0]))||(mode!=0&&(!fault||!st[0])))$fatal(1,"fault expectation mode%0d",mode);
  $display("PASS actual PW issuer->PQ endpoint mode%0d commands%0d GO%0d done%0d END%0d fixedGO%0d fixedCompletion%0d fourtags",mode,commands,gos,completions,ends,1+PINREG,13+2*PINREG);$finish;
 end
 reg[NATIVE_BITS-1:0]expected_fields_mem[0:0];
 // Declared PQ status boundary model, not arithmetic/core timing evidence.
 // It is driven by the true hardware-produced f_iss GO, never a bench f_iss.
 always @(posedge ck)begin
  if(!rst_n)begin t_iss<=3;next_native_tag=0;for(z=0;z<4;z=z+1)pq_age[z]=-1;end
  else begin
   t_iss<=mode==1?39'd2:39'd3;
   if(job_v)next_native_tag=0;
   for(z=0;z<4;z=z+1)if(pq_age[z]>=0)begin
    pq_age[z]=pq_age[z]+1;
    if(pq_age[z]==(mode==3?8:10))begin
     if(mode!=2)begin t_iss[36]<=1;t_iss[38:37]<=mode==4?2'(z^1):2'(z);end
     pq_age[z]=-1;
    end
   end
   if(f_iss[0])begin pq_age[next_native_tag]=0;t_iss[35]<=1;next_native_tag=(next_native_tag+1)%4;end
  end
  tick=tick+1;#1;
  if((fault||st[0])&&!fault_seen)begin $display("firstfault tick%0d issuer%0d code%0d endpoint%0d age%0d status%h",tick,fault,issuer.fault_code,st[0],endpoint.age[0],t_iss);fault_seen=1;end
  if(cv[0])begin
   if(cmd_tick>=0&&tick-cmd_tick!=4&&commands!=126)$fatal(1,"command cadence moved");
   cmd_tick=tick;expected_go=tick+1+PINREG;expected_done=tick+13+2*PINREG;expected_tag={cd[83],cd[6:0]};due_valid[expected_done]=1;due_tags[expected_done]=expected_tag;commands=commands+1;
  end
  if(f_iss[0])begin
   if(tick!=expected_go||f_iss[NATIVE_BITS:1]!=expected_fields)$fatal(1,"actual descriptor/GO mismatch");gos=gos+1;
  end
  if(done[8])begin
   if(!due_valid[tick]||done[7:0]!=due_tags[tick])$fatal(1,"fixed completion/tag moved");completions=completions+1;
  end
  if(jdone)ends=ends+1;
 end
 initial begin #60000;$fatal(1,"timeout");end
endmodule
