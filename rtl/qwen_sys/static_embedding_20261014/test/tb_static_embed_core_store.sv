`timescale 1ns/1ps
module tb_static_embed_core_store;
 reg ck=0;always #0.416667 ck=~ck;
 reg rn=0,fill=0,slot=0,pv=0,ps=0,start=0,cr=0,sr=0;
 reg [17:0] token=151935;reg [5:0] pw=0;reg [511:0] pd=0;
 reg [23:0] ca=0;wire [511:0] cq;wire [15:0] sq;wire fault;
 qkd_embedding_static_core_store dut(.ck(ck),.rst_n(rn),.fill_begin(fill),.fill_token(token),.fill_epoch(16'd43),
 .preload_slot(slot),.preload_v(pv),.preload_scale(ps),.preload_word(pw),.preload_token(token),.preload_epoch(16'd43),.preload_data(pd),
 .core_start(start),.core_token(token),.core_epoch(16'd43),.embed_code_re(cr),.embed_code_addr(ca),.embed_code_q(cq),
 .embed_scale_re(sr),.embed_scale_addr(token),.embed_scale_q(sq),.fault(fault));
 reg [511:0] expected[0:63];reg [15:0] scale[0:0];integer w,mut=0;string dir;
 initial begin
 if(!$value$plusargs("VECTORS=%s",dir))$fatal(1,"vectors");void'($value$plusargs("MUT=%d",mut));
 $readmemh({dir,"/codes.hex"},expected);$readmemh({dir,"/scale.hex"},scale);
 repeat(3)@(negedge ck);rn=1;fill=1;@(negedge ck);fill=0;
 for(w=0;w<64;w=w+1)begin slot=1;pv=1;ps=0;pw=w;pd=expected[w];@(negedge ck);end
 ps=1;pd=0;pd[15:0]=scale[0];@(negedge ck);slot=0;pv=0;ps=0;
 @(negedge ck);start=1;sr=1;@(posedge ck);#0.01;if(sq!==scale[0])$fatal(1,"scale");
 @(negedge ck);start=0;sr=0;cr=1;
 for(w=0;w<64;w=w+1)begin ca=token*64+w;if(mut==1&&w==63)ca=ca^24'd64;
 @(posedge ck);#0.01;if(cq!==expected[w])$fatal(1,"code %0d",w);@(negedge ck);end
 cr=0;@(negedge ck);if(fault)$fatal(1,"identity/calendar fault");
 $display("PASS native core store64codewords+BF16scale fulltoken151935 actualSRAM oneedge");$finish;
 end
endmodule
