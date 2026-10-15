`timescale 1ns/1ps
// Native mask-ROM composition, full64lanes/48realmacro models/all36layers+head.
// Golden compares outputs only; it never drives an internal DUT result.
module tb_native_crom_tp8;
parameter integer WRONG_TP=0;
reg clk=0,rst_n=0; always #1 clk=~clk;
reg [63:0] re=0;
reg [1535:0] addr=0;
reg [5:0] stage=0;
wire [4095:0] q; wire [7:0] fault; wire [15:0] code;
genvar g;
generate for(g=0;g<8;g=g+1) begin: groups
 ot_qfd_crom_gs #(.TP(WRONG_TP?4:8),.IMG_LB(8*g)) dut (
 .clk(clk),.rst_n(rst_n),.crom_re(re[8*g+:8]),.crom_addr(addr[192*g+:192]),
 .crom_stage(stage),.crom_lb(6'(8*g)),.crom_q(q[512*g+:512]),
 .fault(fault[g]),.fault_code(code[2*g+:2]));
end endgenerate
integer errors=0,lane,layer,kind,row;
reg [63:0] expected[0:63];
function automatic [31:0] narrow(input integer r,input integer l);
 narrow=32'h40000000 ^ (r<<8) ^ l;
endfunction
function automatic [63:0] wide(input integer r,input integer l);
 wide={32'h3f000000 ^ (r<<8) ^ l,32'hbf000000 ^ (r<<8) ^ l};
endfunction
task automatic test_read(input integer st,input integer k,input integer offset);
integer l,base,rr;
reg [4095:0] old_q;
begin
 @(negedge clk);old_q=q;stage=6'(st);re=64'hffffffffffffffff;
 for(l=0;l<64;l=l+1)begin
  case(k)
   0:begin base=8832;rr=0;expected[l]=64'h3db504f300000000;end
   1:begin base=4096+64*offset;rr=st*138+offset;expected[l]={32'd0,narrow(rr,l)};end
   2:begin base=8833+64*offset;rr=offset;expected[l]=wide(rr,l);end
   3:begin base=533121+64*offset;rr=st*138+10+offset;expected[l]={32'd0,narrow(rr,l)};end
   4:begin base=537217+64*offset;rr=st*138+74+offset;expected[l]={32'd0,narrow(rr,l)};end
   5:begin base=64*offset;rr=4968+offset;expected[l]={32'd0,narrow(rr,l)};end
   default:begin base=0;rr=0;expected[l]=0;end
  endcase
  addr[24*l+:24]=24'(base+(k==0?0:l));
 end
 @(negedge clk);re=0;
 repeat(3)@(negedge clk);
 if(q!==old_q)begin errors=errors+1;if(errors<8)$display("EARLY_RESPONSE stage=%0d kind=%0d",st,k);end
 @(negedge clk); // Exact E5: both real ROM and SRAM-buffer pipelines.

 for(l=0;l<64;l=l+1)if(q[64*l+:64]!==expected[l])begin
  errors=errors+1;if(errors<8)$display("MISMATCH stage=%0d kind=%0d row=%0d lane=%0d got=%h expected=%h",st,k,offset,l,q[64*l+:64],expected[l]);
 end
 if(|fault)begin errors=errors+1;if(errors<8)$display("FAULT stage=%0d kind=%0d codes=%h",st,k,code);end
end
endtask
initial begin
 repeat(4)@(negedge clk);rst_n=1;repeat(12)@(negedge clk);
 for(layer=0;layer<36;layer=layer+1)begin
  test_read(layer,0,0);
  test_read(layer,1,0);test_read(layer,1,9);
  test_read(layer,3,0);test_read(layer,3,63);
  test_read(layer,4,0);test_read(layer,4,63);
 end
 test_read(0,2,0);test_read(35,2,4095);test_read(35,2,4096);test_read(35,2,8191);
 test_read(36,5,0);test_read(36,5,63);
 if(errors)$display("FAIL native_tp8_crom errors=%0d",errors);
 else $display("PASS native_tp8_crom full64lanes48macros36layers+head cycles=%0t",$time);
 $finish;
end
endmodule
