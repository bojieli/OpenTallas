`timescale 1ns/1ps
`default_nettype none
// Opt-in physical 256-sector bank. Model: hgi_dma_wide_vm_20261010_r1.
// Eight golden39,32 SECDED words occupy two real256x256 macros.
// Accepted write E0 -> encode E1 -> macro pins E2 -> commit E3 -> ACK E4.
// Accepted read E0 -> macro E1 -> capture E2 -> syndrome E3 -> correct E4 -> response E5.
// Independent ports II2; prior accepted same-row writes reserve until real commit.
// R and W accepted together read old contents: macro read E1 precedes commit E3.
// UE returns unmodified word + UE so the owner drains, then sticky fault stops admission.
module ot_hgi_vm_wide_bank #(parameter integer ENABLE=0, parameter integer MUT=0)(
 input wire clk,rst_n,
 input wire w_v, output wire w_rdy, input wire [7:0] w_addr,
 input wire [255:0] w_data,input wire [7:0] w_mask,input wire [19:0] w_tag,
 output reg w_done,output reg [19:0] w_done_tag,
 input wire r_v,output wire r_rdy,input wire [7:0] r_addr,input wire [19:0] r_tag,
 output reg r_done,output reg [19:0] r_done_tag,output reg [255:0] r_data,
 output reg [3:0] r_ce,output reg r_ue,output reg fault,
 input wire inj_v,input wire [2:0] inj_word,input wire [38:0] inj_mask);
    function automatic [6:0] chk(input [31:0] d);
        integer i; reg [6:0] c; reg [6:0] col;
        begin
            c = 7'd0;
            for (i = 0; i < 32; i = i + 1) begin
                col = colv(i);
                if (d[i]) c = c ^ col;
            end
            chk = c;
        end
    endfunction
    // column of data bit i: the i-th 7-bit vector with 3 ones (35 of them; the first 32 used)
    function automatic [6:0] colv(input integer i);
        integer a, b, c, n; reg [6:0] v;
        begin
            n = 0; v = 7'd0;
            for (a = 0; a < 7; a = a + 1)
                for (b = a + 1; b < 7; b = b + 1)
                    for (c = b + 1; c < 7; c = c + 1) begin
                        if (n == i) v = (7'd1 << a) | (7'd1 << b) | (7'd1 << c);
                        n = n + 1;
                    end
            colv = v;
        end
    endfunction
    function automatic [38:0] enc(input [31:0] d);
        enc = {chk(d), d};
    endfunction
    // decode: {ue, ce, corrected data}
    function automatic [33:0] dec(input [38:0] w);
        reg [6:0] syn; integer i; reg [31:0] d; reg hit;
        begin
            d = w[31:0]; syn = chk(w[31:0]) ^ w[38:32]; hit = 1'b0;
            if (syn != 7'd0) begin
                for (i = 0; i < 32; i = i + 1) if (syn == colv(i)) begin d[i] = ~d[i]; hit = 1'b1; end
                // a check-bit error (weight-1 syndrome) leaves the data correct
                if (syn == 7'd1 || syn == 7'd2 || syn == 7'd4 || syn == 7'd8 || syn == 7'd16 || syn == 7'd32 || syn == 7'd64) hit = 1'b1;
            end
            dec = {(syn != 7'd0) && !hit, (syn != 7'd0) && hit, (MUT == 1) ? w[31:0] : d};
        end
    endfunction

 // Correct only after the registered syndrome stage; exactly the golden's selection rule.
 function automatic [33:0] finish(input [38:0] word,input [6:0] syn);
  reg [31:0] d;reg hit;integer i;
  begin
   d=word[31:0];hit=0;
   if(syn!=0)begin
    for(i=0;i<32;i=i+1)if(syn==colv(i))begin d[i]=~d[i];hit=1;end
    if(syn==1||syn==2||syn==4||syn==8||syn==16||syn==32||syn==64)hit=1;
   end
   finish={(syn!=0)&&!hit,(syn!=0)&&hit,(MUT==1)?word[31:0]:d};
  end
 endfunction
 reg [3:0] wvalid,wvalid_n;
 reg [4:0] rvalid,rvalid_n;
 reg wcool,wcool_n,rcool,rcool_n;
 reg [35:0] wm[0:3],wm_n[0:3]; // immutable tag20,address8,wordmask8
 reg [27:0] rm[0:4],rm_n[0:4]; // immutable tag20,address8
 reg [255:0] wd0,wd0_n;
 reg [42:0] inj0,inj0_n; // {enabled,word3,mask39}
 reg [311:0] code1,code2;
 reg [311:0] raw2,raw3,raw2_n,raw3_n;
 reg [55:0] syn3,syn3_n;
 reg [255:0] corrected4,corrected4_n;
 reg [3:0] ce4,ce4_n;reg ue4,ue4_n;
 wire [255:0] mq0,mq1;
 wire [311:0] macro_read={mq1[55:0],mq0};
 reg bad;integer j;
 always @* begin
  bad=(wvalid_n!==~wvalid)||(rvalid_n!==~rvalid)||(wcool_n!==~wcool)||(rcool_n!==~rcool);
  for(integer a=0;a<4;a=a+1)if(wvalid[a]&&(wm_n[a]!==~wm[a]))bad=1;
  for(integer a=0;a<5;a=a+1)if(rvalid[a]&&(rm_n[a]!==~rm[a]))bad=1;
  if(wvalid[0]&&((wd0_n!==~wd0)||(inj0_n!==~inj0)))bad=1;
  if(rvalid[2]&&raw2_n!==~raw2)bad=1;
  if(rvalid[3]&&((raw3_n!==~raw3)||(syn3_n!==~syn3)))bad=1;
  if(rvalid[4]&&((corrected4_n!==~corrected4)||(ce4_n!==~ce4)||(ue4_n!==~ue4)))bad=1;
 end
 wire okay=(ENABLE!=0)&&!fault&&!bad;
 assign w_rdy=okay&&((MUT==6)||!wcool);
 reg raw_hazard;
 always @* begin
  raw_hazard=0;
  for(integer a=0;a<3;a=a+1)if(wvalid[a]&&wm[a][15:8]==r_addr)raw_hazard=1;
 end
 assign r_rdy=okay&&((MUT==6)||!rcool)&&!raw_hazard;
 wire wa=w_v&&w_rdy,ra=r_v&&r_rdy;
 wire mw=okay&&wvalid[2],mr=okay&&rvalid[0];
 wire [7:0] mwa=wm[2][15:8]^((MUT==4)?8'd1:8'd0);
 wire [7:0] wordmask=(MUT==2)?8'hff:wm[2][7:0];
 wire [511:0] md={200'd0,code2};wire [511:0] mm;
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:maskwords
  assign mm[g*39+:39]={39{wordmask[g]}};
 end endgenerate
 assign mm[511:312]=200'd0;
 generate if(ENABLE!=0)begin:mem
 ot_sram_1r1w_256x256_m2_r2c2 u_payload(.clk(clk),.r_ce_in(mr),.r_addr_in(rm[0][7:0]),.rd_out(mq0),
  .w_ce_in(mw),.w_addr_in(mwa),.wd_in(md[255:0]),.w_mask_in(mm[255:0]),
  .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
 ot_sram_1r1w_256x256_m2_r2c2 u_sidecar(.clk(clk),.r_ce_in(mr),.r_addr_in(rm[0][7:0]),.rd_out(mq1),
  .w_ce_in(mw),.w_addr_in(mwa),.wd_in(md[511:256]),.w_mask_in(mm[511:256]),
  .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
 end else begin:disabled
 assign mq0=256'd0;assign mq1=256'd0;
 end endgenerate
 reg [311:0] encode_comb;
 reg [255:0] correct_comb;
 reg [3:0] ce_comb;reg ue_comb;reg[33:0] tmp;
 always @* begin
  encode_comb=312'd0;
  for(integer a=0;a<8;a=a+1)begin
   encode_comb[a*39+:39]=enc(wd0[a*32+:32]);
   if(inj0[42]&&inj0[41:39]==3'(a))encode_comb[a*39+:39]=encode_comb[a*39+:39]^inj0[38:0];
  end
  correct_comb=256'd0;ce_comb=4'd0;ue_comb=0;tmp=34'd0;
  for(integer a=0;a<8;a=a+1)begin
   tmp=finish(raw3[a*39+:39],syn3[a*7+:7]);
   correct_comb[a*32+:32]=tmp[31:0];ce_comb=ce_comb+4'(tmp[32]);ue_comb=ue_comb|tmp[33];
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   wvalid<=0;wvalid_n<=4'hf;rvalid<=0;rvalid_n<=5'h1f;
   wcool<=0;wcool_n<=1;rcool<=0;rcool_n<=1;
   w_done<=0;w_done_tag<=0;r_done<=0;r_done_tag<=0;r_data<=0;r_ce<=0;r_ue<=0;fault<=0;
  end else begin
   w_done<=0;r_done<=0;r_ce<=0;r_ue<=0;
   if(bad)fault<=1;
   wcool<=wa;wcool_n<=~wa;rcool<=ra;rcool_n<=~ra;
   wvalid<={wvalid[2:0],wa};wvalid_n<=~{wvalid[2:0],wa};
   rvalid<={rvalid[3:0],ra};rvalid_n<=~{rvalid[3:0],ra};
   if(wa)begin
    wm[0]<={w_tag,w_addr,w_mask};wm_n[0]<=~{w_tag,w_addr,w_mask};
    wd0<=w_data;wd0_n<=~w_data;inj0<={inj_v,inj_word,inj_mask};inj0_n<=~{inj_v,inj_word,inj_mask};
   end
   for(j=1;j<4;j=j+1)if(wvalid[j-1])begin wm[j]<=wm[j-1];wm_n[j]<=wm_n[j-1];end
   if(wvalid[0])code1<=encode_comb;
   if(wvalid[1])code2<=code1;
   if(ra)begin rm[0]<={r_tag,r_addr};rm_n[0]<=~{r_tag,r_addr};end
   for(j=1;j<5;j=j+1)if(rvalid[j-1])begin rm[j]<=rm[j-1];rm_n[j]<=rm_n[j-1];end
   if(rvalid[1])begin raw2<=macro_read;raw2_n<=~macro_read;end
   if(rvalid[2])begin
    raw3<=raw2;raw3_n<=raw2_n;
    for(j=0;j<8;j=j+1)begin
     syn3[j*7+:7]<=chk(raw2[j*39+:32])^raw2[j*39+32+:7];
     syn3_n[j*7+:7]<=~(chk(raw2[j*39+:32])^raw2[j*39+32+:7]);
    end
   end
   if(rvalid[3])begin
    corrected4<=correct_comb;corrected4_n<=~correct_comb;ce4<=ce_comb;ce4_n<=~ce_comb;ue4<=ue_comb;ue4_n<=~ue_comb;
   end
   if(okay&&((MUT==3)?wvalid[1]:wvalid[3]))begin
    w_done<=1;w_done_tag<=((MUT==3)?wm[1][35:16]:wm[3][35:16])^((MUT==5)?20'd1:20'd0);
   end
   if(okay&&rvalid[4])begin
    r_done<=1;r_done_tag<=rm[4][27:8];r_data<=corrected4;r_ce<=ce4;r_ue<=ue4;
    if(ue4)fault<=1;
   end
  end
 end
endmodule
`default_nettype wire
