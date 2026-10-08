// Generated installed native weight span ROM. Default off; not a loader receipt.
// Source sha256: 966e26b3ae32d310ced8a3667b8076a45b7d13ca4a449035cd8d90bc16516427
// Model: tools/hbm_sm_native_allocation_model.py. Actual-flow DMR preservation unqualified.
module ot_hbm_sm_native_allocation #(parameter ENABLE=0)(
 input wire clk,rst_n,input wire req_valid,output wire req_ready,
 input wire[15:0] req_record,input wire[23:0] req_lines,
 output wire rsp_valid,input wire rsp_ready,output wire[15:0] rsp_record,
 output wire[31:0] rsp_base,output wire rsp_error,output wire fault);
 reg found;reg[31:0]rom_base;reg[23:0]rom_lines;
 always @* begin found=0;rom_base=0;rom_lines=0;case(req_record)
 16'd0:begin found=1;rom_base=32'd744759;rom_lines=24'd80;end
 16'd1:begin found=1;rom_base=32'd746504;rom_lines=24'd80;end
 16'd2:begin found=1;rom_base=32'd748249;rom_lines=24'd32;end
 16'd3:begin found=1;rom_base=32'd748615;rom_lines=24'd256;end
 16'd4:begin found=1;rom_base=32'd749044;rom_lines=24'd128;end
 16'd5:begin found=1;rom_base=32'd750504;rom_lines=24'd24;end
 16'd6:begin found=1;rom_base=32'd751028;rom_lines=24'd240;end
 16'd7:begin found=1;rom_base=32'd752933;rom_lines=24'd256;end
 16'd8:begin found=1;rom_base=32'd753525;rom_lines=24'd32;end
 16'd9:begin found=1;rom_base=32'd753558;rom_lines=24'd80;end
 16'd10:begin found=1;rom_base=32'd755303;rom_lines=24'd48;end
 16'd11:begin found=1;rom_base=32'd755851;rom_lines=24'd32;end
 16'd12:begin found=1;rom_base=32'd756217;rom_lines=24'd256;end
 default:begin end
 endcase end
 (* keep=1,dont_touch=1 *) reg[49:0] a,b;
 (* keep=1,dont_touch=1 *) reg bad,bad_n;
 wire mismatch=(a[49]!=b[49]) || (a[49] && a[48:0]!=b[48:0]) || (bad==bad_n);
 wire stop=bad || mismatch;
 assign req_ready=ENABLE && !stop && !a[49];
 assign rsp_valid=ENABLE && !stop && a[49];
 assign rsp_record=a[48:33];assign rsp_base=a[32:1];assign rsp_error=a[0];
 assign fault=stop;
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin a<=0;b<=0;bad<=0;bad_n<=1;end
 else if(ENABLE)begin
 if(mismatch)begin bad<=1;bad_n<=0;end
 if(!stop)begin
 if(rsp_valid && rsp_ready)begin a[49]<=0;b[49]<=0;end
 if(req_valid && req_ready)begin
 a<={1'b1,req_record,rom_base,(!found || req_lines!=rom_lines)};
 b<={1'b1,req_record,rom_base,(!found || req_lines!=rom_lines)};
 end
 end
 end
 end
endmodule
