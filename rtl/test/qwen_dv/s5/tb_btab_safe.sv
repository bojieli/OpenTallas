`timescale 1ns/1ps
// Exact legacy source snapshot from b484119db; smallest mechanism comparison.
module qfd_dv_s5_btab_ref (
    input  wire           ck,
    input  wire           bt_re,
    input  wire [8:0]     bt_word,
    output wire [255:0]   bt_q,
    input  wire           tw_we,
    input  wire [1:0]     tw_kind,
    input  wire [23:0]    tw_addr,
    input  wire [1023:0]  tw_data
);
    wire bt_w = tw_we && tw_kind == 2'd2;
    wire [4*256-1:0] bt_rd;
    genvar bk;
    generate for (bk = 0; bk < 4; bk = bk + 1) begin : g_btb
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(ck), .r_ce_in(bt_re && bt_word[1:0] == bk[1:0]), .r_addr_in(bt_word[8:2]),
            .rd_out(bt_rd[bk*256 +: 256]), .w_ce_in(bt_w), .w_addr_in(tw_addr[8:2]),
            .wd_in(tw_data[256*bk +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    reg [1:0] t1_bank, t2_bank;
    reg [1023:0] btcap;
    always @(posedge ck) begin t1_bank <= bt_word[1:0]; btcap <= bt_rd; t2_bank <= t1_bank; end

    assign bt_q = btcap[256*t2_bank +: 256];

endmodule
module tb_btab_safe;
reg ck=0;always #0.5 ck=~ck;
reg bt_re=0,tw_we=0;reg [8:0]bt_word=0;reg[1:0]tw_kind=0;reg[23:0]tw_addr=0;reg[1023:0]tw_data=0;
wire[255:0]a,b;
qfd_dv_s5_btab_ref u_a(.ck(ck),.bt_re(bt_re),.bt_word(bt_word),.bt_q(a),.tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data(tw_data));
qfd_dv_s5_btab_safe u_b(.ck(ck),.bt_re(bt_re),.bt_word(bt_word),.bt_q(b),.tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data(tw_data));
integer c,j,nz=0;
initial begin
// Fill every row in all four banks, then random reads/writes with no same-address collisions.
for(c=0;c<12000;c=c+1) begin
@(negedge ck);
bt_re=(c>=132);tw_we=(c<128)||(c%4==0);tw_kind=2;tw_addr=(c<128)?(c*4):(($urandom%128)*4);
bt_word=$urandom%512;
if(tw_we && bt_word[8:2]==tw_addr[8:2])bt_word[8:2]=bt_word[8:2]+1;
for(j=0;j<32;j=j+1)tw_data[32*j+:32]=$urandom;
@(posedge ck);#0.1;
if(c>136)begin
if(a!==b)$fatal(1,"BTAB_EQ FAIL cycle=%0d ref=%h got=%h",c,a,b);
if(|a)nz=nz+1;
end
end
if(nz<10000)$fatal(1,"BTAB_EQ FAIL no data coverage nz=%0d",nz);
$display("BTAB_EQ PASS cycles=%0d nonzero=%0d",c,nz);$finish;
end
endmodule
