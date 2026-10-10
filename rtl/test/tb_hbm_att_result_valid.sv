`timescale 1ns/1ps
// Minimum die consumer gate: inject at the hardened quad-result boundary.
// Arithmetic is outside this mechanism; real die merge and hardened-bank RTL run.
module tb_hbm_att_result_valid;
    parameter integer CG = 1;
    reg clk=0; always #1 clk=~clk;
    reg [15:0] valid_heads=0, faults=16'hffff;
    reg [511:0] values={512{1'b1}};
    reg [528:0] chain=0;
    wire [528:0] ot, oh;
    hfd_attn_tile_b #(.CG(CG),.NK(0),.NC(0),.NR(0),.PMID(1),.NFC(1),.NFR(1),.NL(4),.NI(0)) tile
       (.ck(clk),.rst(1'b0),.k(1041'd0),.q(582'd0),.ci(1618'd0),.ri(1618'd0),.i(chain),.o(ot));
    hfd_attn_half_hi #(.CG(CG),.PMID(1),.NFC(1),.NL(4),.NLL(3),.NI(0)) half
       (.ck(clk),.xp(1619'd0),.xr(272'd0),.i(chain),.o(oh));
    integer checks=0, h;
    initial begin
        force tile.gov=valid_heads; force half.gov=valid_heads;
        force tile.oy=values; force half.oy=values;
        force tile.oflt=faults; force half.oflt=faults;
    end
    task check(input [528:0] expected);
        begin
            @(posedge clk); #0.1;
            checks=checks+1;
            if (ot !== expected || oh !== expected) begin
                $display("ATT_VALID FAIL check=%0d mask=%h expected=%h tile=%h half=%h",checks,valid_heads,expected,ot,oh);
                $fatal(1,"consumer admitted held/incoherent result");
            end
            @(negedge clk);
        end
    endtask
    initial begin
        repeat(3) @(negedge clk);
        // An idle held fault and X arithmetic must not become a valid result.
        values={512{1'bx}}; valid_heads=0; faults=16'hffff;
        check(529'd0);
        // Coherent heads retain every value and qualified fault exactly.
        valid_heads=16'hffff; values={16{32'h12345678}}; faults=16'h8001;
        check({1'b1,values,faults});
        // Every missing head, including quad0/head0, is a transaction fault.
        for(h=0;h<16;h=h+1) begin
            valid_heads=16'hffff ^ (16'h1 << h); faults=0; values={512{1'bx}};
            check({1'b1,512'd0,16'hffff});
        end
        // Any isolated arrival is also a fault, never dropped because head0 is idle.
        for(h=0;h<16;h=h+1) begin
            valid_heads=16'h1 << h; faults=16'hffff; values={512{1'bx}};
            check({1'b1,512'd0,16'hffff});
        end
        valid_heads=0; faults=16'hffff; values={512{1'bx}};
        chain={1'b1,{16{32'h89abcdef}},16'h4000};
        // Chain crosses one bank before the existing output bank.
        @(posedge clk); #0.1; @(negedge clk);
        check(chain);
        // A valid local result colliding with the chain keeps local data, faults all.
        valid_heads=16'hffff; values={16{32'h22222222}}; faults=0;
        check({1'b1,values,16'hffff});
        $display("ATT_VALID PASS CG=%0d checks=%0d",CG,checks); $finish;
    end
endmodule
// Hardened quad boundary model: results are injected above, so no arithmetic replay.
module ot_attn_tile_m6h1q #(parameter integer CG=0)(
 input wire clk,rst_n, input wire [7:0] qgid, input wire ld_v,ld_mode,
 input wire [2:0] ld_bank, input wire [7:0] ld_grp,input wire [1023:0] ld_w,
 input wire ld_w2v,iv,input wire [2:0] ibank,input wire [575:0] ib,
 output wire [3:0] gov, output wire [127:0] oy, output wire [3:0] oflt);
 assign gov=0; assign oy=0; assign oflt=0;
endmodule
module ot_attn_rp_reg #(parameter integer W=1)(input wire clk,input wire [W-1:0] d,output reg [W-1:0] q);
 always @(posedge clk) q<=d;
endmodule
