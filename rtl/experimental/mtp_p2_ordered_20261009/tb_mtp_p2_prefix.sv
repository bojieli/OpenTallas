`timescale 1ns/1ps
module tb_mtp_p2_prefix;
 parameter integer MUT_COPY_FIRST=0,ERROR_MODE=0,DSTAGE=0,ROOTPIPE=0;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0,start_v=0,iv=0,abort=0;wire sr,ir,ov,done,fault,corrected;
 reg [73:0] identity=74'h12345678;reg [26:0] ids={9'd127,9'd65,9'd3};
 reg [8:0] expert;reg [6:0] word;reg last,transaction_last;
 reg [511:0] raw;wire [575:0] enc;
 reg [575:0] incoming;wire [575:0] outgoing;
 wire [73:0] oid;wire [6:0] ow;wire olast;reg ordy=0;
 reg [31:0] inputs[0:3839],gold[0:1279];
 integer cycles=0,received=0,e,w,l,s;
 ot_mtp_p2_prefix #(.ENABLE(1),.MUT_COPY_FIRST(MUT_COPY_FIRST),.DSTAGE(DSTAGE),.ROOTPIPE(ROOTPIPE)) dut(
 .clk(clk),.rst_n(rst_n),.start_v(start_v),.start_r(sr),.start_identity(identity),.start_ids(ids),
 .in_v(iv),.in_r(ir),.in_identity(identity),.in_expert(expert),.in_shared(1'b0),
 .in_row_last(last),.in_transaction_last(transaction_last),.in_word(word),.in_secded(incoming),
 .out_v(ov),.out_r(ordy),.out_identity(oid),.out_word(ow),.out_last(olast),
 .out_secded(outgoing),.abort(abort),.done(done),.fault(fault),.corrected(corrected));
 for(genvar q=0;q<8;q=q+1)begin
 ot_secded_enc #(.K(64),.R(8)) encoder(.clk(clk),.d(raw[64*q+:64]),.q(enc[72*q+:72]));
 end
 always @(negedge clk)ordy<=rst_n&&(cycles%7!=1)&&(cycles%7!=2);
 always @(posedge clk)begin
 cycles=cycles+1;
 if(fault)begin
 if(ERROR_MODE!=0)begin $display("PREFIX NEGATIVE PASS mode%0d abort before output cycles%0d",ERROR_MODE,cycles);$finish;end
 else $fatal(1,"PREFIX unexpected fault atcycle%0d",cycles);
 end
 if(dut.enabled.state==11&&dut.enabled.expert_index==0&&dut.enabled.word_index==0&&dut.enabled.sum_q[31:0]!==32'd0)
 $fatal(1,"PREFIX +0/-0 first-round mutant detected");
 if(ov&&ordy)begin
 if(oid!==identity||ow!==received||olast!==(received==79))$fatal(1,"PREFIX metadata");
 for(l=0;l<16;l=l+1)begin
 if(outgoing[72*(l/2)+32*(l%2)+:32]!==gold[received*16+l])
 $fatal(1,"PREFIX mismatch value%0d got%h exp%h",received*16+l,outgoing[72*(l/2)+32*(l%2)+:32],gold[received*16+l]);
 end
 received=received+1;
 end
 if(cycles>6500)$fatal(1,"PREFIX watchdog");
 end
 initial begin
 $readmemh("inputs.hex",inputs);$readmemh("gold.hex",gold);
 raw=0;incoming=0;expert=0;word=0;last=0;transaction_last=0;
 repeat(3)@(negedge clk);rst_n=1;
 @(negedge clk);start_v=1;@(negedge clk);start_v=0;
 for(e=0;e<3;e=e+1)for(w=0;w<80;w=w+1)begin
 wait(ir);@(negedge clk);
 for(s=0;s<16;s=s+1)raw[32*s+:32]=inputs[e*1280+w*16+s];
 if(ERROR_MODE==2&&e==0&&w==0)raw[0]=1;
 expert=ids[9*e+:9];word=w;last=w==79;transaction_last=(e==2)&&(w==79);
 @(negedge clk);incoming=enc;
 // Actual transport-code single data-bit error: decoder must correct it.
 if(e==1&&w==17)incoming[3]=~incoming[3];
 if(ERROR_MODE==1&&e==0&&w==0)begin incoming[3]=~incoming[3];incoming[5]=~incoming[5];end
 iv=1;@(posedge clk);if(!ir)$fatal(1,"PREFIX input ready");
 @(negedge clk);iv=0;
 end
 wait(done);@(negedge clk);
 if(received!=80||!corrected)$fatal(1,"PREFIX count/CE");
 $display("PREFIX PASS 1280FP32 exact +0/E0/E1/E2 BF16widened, CE corrected, cycles%0d",cycles);
 $finish;
 end
endmodule
