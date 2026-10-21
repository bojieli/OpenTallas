`timescale 1ns/1ps
module provider_tb;
reg ck=0;always #5 ck=~ck;integer tick=0,phase;always @(negedge ck)tick<=tick+1;
wire rst=((tick>=1596)&&(tick<2400))||(tick>=3996);
reg word_v=0,word_scale=0,fill_begin=0,code_re=0,scale_re=0;
reg[5:0]word_index=0;reg[511:0]word_data=0;reg[23:0]code_addr=0;
wire[511:0]code_q;wire[15:0]scale_q;wire fault;
qfd_embedding_word_provider original_provider(
 .ck(ck),.rst_n(rst),.word_v(word_v),.word_data(word_data),.word_token(18'd1),.word_index(word_index),.word_scale(word_scale),.word_epoch(16'd5),
 .expected_word_slot(word_v),.expected_token(18'd1),.expected_word(word_index),.expected_scale(word_scale),.expected_epoch(16'd5),
 .fill_begin(fill_begin),.fill_token(18'd1),.fill_epoch(16'd5),.core_start(1'b0),.core_token(18'd1),.core_epoch(16'd5),
 .embed_code_re(code_re),.embed_code_addr(code_addr),.embed_code_q(code_q),.embed_scale_re(scale_re),.embed_scale_addr(18'd1),.embed_scale_q(scale_q),.fault(fault));
always @(negedge ck)begin
 phase=(tick>=2400?tick-3996:tick-1596)%128;
 word_v=0;word_scale=0;fill_begin=0;code_re=0;scale_re=0;
 if(rst&&phase>=10)begin
  fill_begin=(phase==10);
  if(phase>=12&&phase<=75)begin word_v=1;word_index=phase-12;word_data={16{32'h1051+phase*17+tick/128}};end
  if(phase==76)begin word_v=1;word_index=0;word_scale=1;word_data={496'd0,16'(tick/128+73)};end
  if(phase>=80)begin code_re=1;scale_re=1;code_addr={18'd1,6'(tick%64)};end
 end
end
wire[1:0]done,failed;
age_case #(.ID(5),.W(512),.N(3),.K(3),.E(2),.G(1597),.R0(1596),.EXTERNAL(1)) a(.ck(ck),.external_source(code_q),.done(done[0]),.failed(failed[0]));
age_case #(.ID(6),.W(16),.N(2),.K(2),.E(1),.G(1597),.R0(1596),.EXTERNAL(1)) b(.ck(ck),.external_source(scale_q),.done(done[1]),.failed(failed[1]));
integer faultchecks=0;
always @(posedge ck)begin #0.2;if(rst)begin faultchecks=faultchecks+1;if(fault)$fatal(1,"PROVIDER_SOURCE_FAULT t=%0d phase=%0d",tick,phase);end end
initial begin wait(&done);if(|failed)$fatal(1,"PROVIDER_AGE_FAIL cases=%b",failed);$display("PROVIDER_AGE_PASS cases=2 source=original_full_provider_and_store macro=original_64x512 faultchecks=%0d",faultchecks);$finish;end
endmodule
