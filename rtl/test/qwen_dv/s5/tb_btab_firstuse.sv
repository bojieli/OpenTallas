`timescale 1ns/1ps
// Exact legacy source snapshot from b484119db; smallest mechanism comparison.
module qfd_btab_firstuse_ref (
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
module tb_btab_firstuse #(parameter integer MUT_AGE=0, MUT_DROP=0);
reg ck=0;always #5 ck=~ck;
reg bt_re=0,tw_we=0,drop_phase=0;
reg [8:0]bt_word=0;reg [1:0]tw_kind=0;reg[23:0]tw_addr=0;reg[1023:0]tw_data=0;
wire [255:0] a,b;
qfd_btab_firstuse_ref u_a(.ck(ck),.bt_re(bt_re),.bt_word(bt_word),.bt_q(a),.tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data(tw_data));
qfd_dv_s5_btab_s4 u_b(.ck(ck),.bt_re(bt_re),.bt_word(bt_word),.bt_ql(b[127:0]),.bt_qh(b[255:128]),.tw_we(tw_we&&!(MUT_DROP&&drop_phase)),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_lo(tw_data[511:0]),.tw_hi(tw_data[1023:512]));
reg [255:0] b_late;
always @(posedge ck)b_late<=b;
wire [255:0] checked_b=MUT_AGE?b_late:b;
function automatic [255:0] rand256;
 for(integer i=0;i<8;i=i+1)rand256[32*i+:32]=$urandom;
endfunction
function automatic [257:0] rand258;
 rand258={2'($urandom),rand256()};
endfunction
// Actual physical SRAM arrays and read registers have different independent
// random draws. Unwritten rows stay unrelated; only shared interface writes
// establish common payload. OT_MEM_NO_INIT disables the model's zero default.
for(genvar g=0;g<4;g=g+1)begin:g_initial_memory
 initial begin
  for(integer r=0;r<130;r=r+1)begin
   u_a.g_btb[g].u_m.arr[r]=rand258();
   u_b.u_core.g_btb[g].u_m.arr[r]=rand258();
  end
  u_a.g_btb[g].u_m.rd_out=rand256();
  u_b.u_core.g_btb[g].u_m.rd_out=rand256();
 end
end
for(genvar g=0;g<16;g=g+1)begin:g_initial_FF
 initial begin
  u_b.u_core.g_read[g].q=16'($urandom);
  u_b.u_core.g_read[g].u_sel.q=4'($urandom);
 end
end
initial begin
 for(integer i=0;i<32;i=i+1)u_a.btcap[32*i+:32]=$urandom;
 u_a.t1_bank=2'($urandom);u_a.t2_bank=2'($urandom);
end
reg [1023:0] model[0:127];reg known[0:127];reg first_seen[0:127][0:3];
reg pending_valid=0;reg[255:0]pending_data;integer pending_row,pending_bank,pending_sample;
integer cycles=0,checks=0,first_checks=0,written_rows=0,collisions=0,early_checks=0;
always @(posedge ck)begin:monitor
 reg valid_now;reg [255:0]want_now;integer row_now,bank_now,sample_now;
 cycles=cycles+1;sample_now=cycles;row_now=bt_word[8:2];bank_now=bt_word[1:0];
 // Read-before-write is the exact actual macro model's contract. A first
 // simultaneous write/read of an unwritten row remains undefined on that read.
 valid_now=bt_re&&known[row_now];want_now=model[row_now][256*bank_now+:256];
 if(bt_re&&tw_we&&tw_kind==2&&bt_word[8:2]==tw_addr[8:2])collisions=collisions+1;
 if(tw_we&&tw_kind==2)begin
  if(!known[tw_addr[8:2]])written_rows=written_rows+1;
  model[tw_addr[8:2]]=tw_data;known[tw_addr[8:2]]=1;
 end
 #0.2;
 if(pending_valid)begin
  if(a!==pending_data||checked_b!==pending_data)
   $fatal(1,"BTAB_FIRSTUSE_FAIL cycle=%0d sample=%0d row=%0d bank=%0d initialized_rows=%0d age=%0d drop=%0d ref=%h got=%h expected=%h",cycles,pending_sample,pending_row,pending_bank,written_rows,MUT_AGE,MUT_DROP,a,checked_b,pending_data);
  checks=checks+1;
  if(written_rows<128)early_checks=early_checks+1;
  if(!first_seen[pending_row][pending_bank])begin
   first_seen[pending_row][pending_bank]=1;first_checks=first_checks+1;
   if(first_checks<=4)$display("BTAB_FIRST_DEFINED sample=%0d output=%0d row=%0d bank=%0d initialized_rows=%0d",pending_sample,cycles,pending_row,pending_bank,written_rows);
  end
 end
 pending_valid=valid_now;pending_data=want_now;pending_row=row_now;pending_bank=bank_now;pending_sample=sample_now;
end
function automatic [1023:0] payload(input integer tag,input integer row);
 for(integer k=0;k<32;k=k+1)payload[32*k+:32]=32'hD31B0000^(32'(tag)*32'h9E3779B9)^(32'(row)<<8)^32'(k*65537);
endfunction
task automatic drive(input bit re,input integer word,input bit we,input integer row,input integer tag,input bit drop);
 @(negedge ck);bt_re=re;bt_word=9'(word);tw_we=we;tw_kind=2;tw_addr=24'(row*4);tw_data=payload(tag,row);drop_phase=drop;
 @(posedge ck);#1;
endtask
integer row,word,wrrow;
initial begin
 for(integer i=0;i<128;i=i+1)begin known[i]=0;for(integer j=0;j<4;j=j+1)first_seen[i][j]=0;end
 #1;
 if(a===b)$fatal(1,"BTAB_FIRSTUSE_FIXTURE_FF_STATES_NOT_DISTINCT");
 if(u_a.g_btb[0].u_m.arr[38]===u_b.u_core.g_btb[0].u_m.arr[38])$fatal(1,"BTAB_FIRSTUSE_FIXTURE_SRAM_STATES_NOT_DISTINCT");
 $display("BTAB_INDEPENDENT_STARTUP ff_distinct=1 unwritten_SRAM_distinct=1 physical_model=1 mem_no_init=1 reset_ports=0");
 // No full-table preload or cycle warmup. First row37 is written while all
 // 127 other rows are unrelated, then every bank's FIRST defined output checks.
 for(integer i=0;i<128;i=i+1)begin
  row=(53*i+37)%128;
  drive(1,row*4,1,row,i+1,i==0); // same-edge first read remains undefined
  for(integer bank=0;bank<4;bank=bank+1)drive(1,row*4+bank,0,0,0,0);
 end
 for(integer i=0;i<512;i=i+1)begin
  word=$urandom%512;wrrow=(i%3==0)?(word/4):($urandom%128);
  drive(i%5!=0,word,i%4==0,wrrow,1000+i,0);
 end
 drive(0,0,0,0,0,0);drive(0,0,0,0,0,0);
 if(first_checks!=512||early_checks<500||collisions<129)$fatal(1,"BTAB_FIRSTUSE_COVERAGE_FAIL first=%0d early=%0d collisions=%0d",first_checks,early_checks,collisions);
 $display("BTAB_FIRSTUSE_PASS checks=%0d first_defined=%0d early_before_global_init=%0d collisions=%0d cycles=%0d read_sample_to_output_edges=1 no_warmup_mask=1",checks,first_checks,early_checks,collisions,cycles);$finish;
end
initial begin repeat(2000)@(posedge ck);$fatal(1,"BTAB_FIRSTUSE_PROGRESS_FAIL");end
endmodule
