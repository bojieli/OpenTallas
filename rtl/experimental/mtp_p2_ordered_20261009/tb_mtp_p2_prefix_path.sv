`timescale 1ns/1ps
module tb_mtp_p2_prefix_path;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0,sv=0,abort=0;wire sr,done,fault,corrected;
 reg [73:0] identity=74'h12345678;reg [26:0] ids={9'd127,9'd65,9'd3};
 reg [1:0] iv=0,ish=0,ilast=0;wire [1:0] ir;
 reg [147:0] itag=0;reg [17:0] ie=0;reg [13:0] iw=0;reg [1023:0] data=0;
 wire ov,olast;reg ordy=0;wire [511:0] out;wire [73:0] oid;wire [6:0] ow;
 reg [31:0] inputs[0:3839],gold[0:1279];
 integer cycles=0,received=0,w,l,tail_hold=0;reg [511:0] held_tail;reg tail_seen=0;
 ot_mtp_p2_prefix_path #(.ENABLE(1)) dut(.clk(clk),.rst_n(rst_n),
 .start_v(sv),.start_r(sr),.start_identity(identity),.start_ids(ids),
 .in_v(iv),.in_r(ir),.in_identity(itag),.in_expert(ie),.in_shared(ish),
 .in_last(ilast),.in_word(iw),.in_data(data),.out_v(ov),.out_r(ordy),
 .out_data(out),.out_identity(oid),.out_word(ow),.out_last(olast),
 .abort(abort),.done(done),.fault(fault),.corrected(corrected));
 always @(negedge clk)begin
 if(ov&&olast&&tail_hold<16)begin ordy<=0;tail_hold=tail_hold+1;
 if(!tail_seen)begin held_tail=out;tail_seen=1;end
 else if(out!==held_tail)$fatal(1,"PATH tail changed under backpressure");
 if(sr)$fatal(1,"PATH context released before final handshake");end
 else ordy<=rst_n&&(cycles%7!=1)&&(cycles%7!=2);
 end
 always @(posedge clk)begin
 cycles=cycles+1;
 if(fault)$fatal(1,"PATH unexpected fault cycle%0d",cycles);
 if(ov&&ordy)begin
 if(oid!==identity||ow!==received||olast!==(received==79))$fatal(1,"PATH metadata");
 for(l=0;l<16;l=l+1)if(out[32*l+:32]!==gold[received*16+l])
 $fatal(1,"PATH numeric word%0d lane%0d",received,l);
 received=received+1;
 end
 if(cycles>7600)$fatal(1,"PATH model-bound exceeded");
 end
 function automatic [511:0] flit(input integer e,w);
 integer s;begin for(s=0;s<16;s=s+1)flit[32*s+:32]=inputs[e*1280+w*16+s];end
 endfunction
 task automatic pair(input integer w);
 begin @(negedge clk);iv=3;itag={identity,identity};ie={9'd3,9'd127};
 iw={7'(w),7'(w)};ilast={2{w==79}};data={flit(0,w),flit(2,w)};
 @(posedge clk);if(ir!==3)$fatal(1,"PATH parallel readiness");@(negedge clk);iv=0;end
 endtask
 initial begin
 $readmemh("inputs.hex",inputs);$readmemh("gold.hex",gold);
 repeat(3)@(negedge clk);rst_n=1;@(negedge clk);sv=1;
 @(posedge clk);if(!sr)$fatal(1,"PATH atomic start");@(negedge clk);sv=0;
 // Opposite arrival order; the actual producer must preserve E0,E1,E2.
 for(w=0;w<80;w=w+1)pair(w);
 for(w=0;w<80;w=w+1)begin
 @(negedge clk);iv=1;itag={identity,identity};ie={9'd0,9'd65};
 iw={7'd0,7'(w)};ilast={1'b0,w==79};data={512'd0,flit(1,w)};
 @(posedge clk);if(!ir[0])$fatal(1,"PATH single readiness");@(negedge clk);iv=0;
 end
 wait(done);@(negedge clk);
 if(received!=80||tail_hold!=16||!sr)$fatal(1,"PATH completion/context ownership");
 $display("PATH PASS actual9SRAM transport +3SRAM/16LAT8prefix +native decode,1280values, finalhold16 cycles%0d",cycles);
 $finish;
 end
endmodule
