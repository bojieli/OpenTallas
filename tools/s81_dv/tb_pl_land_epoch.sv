`timescale 1ns/1fs
module tb;
parameter integer BIAS=0,DEPTH=4;
reg clk=0;always #0.4165 clk=~clk;
reg rw=0,rr=0;integer skew=0,cyc=0,ncheck=0;reg[31:0]lfsr=32'h42531549;
localparam integer AW=$clog2(DEPTH);wire[DEPTH*32-1:0]bank;wire[DEPTH*(AW+1)-1:0]epo;wire[DEPTH-1:0]vld;wire[31:0]o,gold;
reg[31:0]hist[0:2];
ot_pl_land_local_kw #(.W(32),.D(DEPTH)) w(.ck(clk),.rsi(rw),.i(lfsr),.bank(bank),.epo(epo),.vld(vld));
ot_pl_land_local_r #(.W(32),.D(DEPTH),.K(2),.EPOCH_BIAS(BIAS)) r(.ck(clk),.rsi(rr),.bank(bank),.epo(epo),.vld(vld),.o(o));
generate if(BIAS==0)begin:g_ref
 ot_pl_land_local_r_ref #(.W(32),.D(DEPTH),.K(2)) ref_r(.ck(clk),.rsi(rr),.bank(bank),.epo(epo),.vld(vld),.o(gold));
end else assign gold=0;endgenerate
always @(negedge clk)if(BIAS==0&&skew==0&&o!==gold)$fatal(1,"DEFAULT_REFERENCE_MISMATCH");
initial begin
 if($value$plusargs("SKEW=%d",skew));
 repeat(16)@(negedge clk);
 if(skew>=0)begin rw=1;repeat(skew)@(negedge clk);rr=1;end
 else begin rr=1;repeat(-skew)@(negedge clk);rw=1;end
 repeat(80)@(negedge clk);
 if(ncheck<40)$fatal(1,"few data checks");
 $display("LAND_ORIGIN_PASS skew=%0d bias=%0d arbitrary_data=%0d",skew,BIAS,ncheck);$finish;
end
always @(posedge clk)begin
 cyc<=cyc+1;lfsr<={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};hist[0]<=lfsr;hist[1]<=hist[0];hist[2]<=hist[1];
 $display("LAND_EDGE edge=%0d rw=%0d rr=%0d wrq=%0d rrq=%0d wc=%0d rc=%0d oh=%h warm=%0d",cyc,rw,rr,w.rq,r.rq,w.wc,r.rc,r.read_oh,r.warm);
end
always @(negedge clk)if(cyc>40&&rw&&rr)begin
 if(o!==hist[2])$fatal(1,"LAND_DATA edge%0d got%h expected%h",cyc,o,hist[2]);ncheck=ncheck+1;
end
endmodule

// Frozen zero-bias reader reference from the source before this change.
`timescale 1ns/1ps
module ot_pl_land_local_r_ref #(
    parameter integer W = 24, D = 4, K = 2,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [D*W-1:0] bank,
    input wire [D*(AW+1)-1:0] epo,
    input wire [D-1:0] vld,
    output reg [W-1:0] o
);
    reg rq, warm;
    reg [AW:0] rc;
    (* keep *) reg [D-1:0] read_oh;
    wire [AW:0] expected_epoch = rc - (AW+1)'(K);
    reg [W-1:0] selected;
    reg selected_valid;
    integer s;
    always @* begin
        selected = 0;
        selected_valid = 0;
        for (integer j=0;j<D;j=j+1) begin
            selected = selected | (bank[j*W+:W] & {W{read_oh[j]}});
            selected_valid = selected_valid | (vld[j] & read_oh[j]);
        end
    end
    always @(posedge ck) rq <= rsi;
    always @(posedge ck)
        if (!rq) begin
            rc <= 0; warm <= 0;
            for (s=0;s<D;s=s+1) read_oh[s] <= (s == ((D-K) % D));
        end else begin
            rc <= rc + 1'b1;
            if (32'(rc) == K-1) warm <= 1;
            read_oh <= {read_oh[D-2:0], read_oh[D-1]};
        end
    always @(posedge ck) o <= (warm && selected_valid) ? selected : {W{1'b0}};
`ifndef SYNTHESIS
    reg fault = 0;
    always @(posedge ck) if (warm && selected_valid && !fault) begin
        for (integer j=0;j<D;j=j+1) if (read_oh[j] && epo[j*(AW+1)+:AW+1] != expected_epoch) begin
            fault <= 1;
            $error("LAND_FAULT %m: slot%0d epoch%0d expected%0d",j,epo[j*(AW+1)+:AW+1],expected_epoch);
        end
    end
`endif
endmodule
