`timescale 1ps/1fs
`default_nettype none
// Opt-in native 1R1W SRAM IKS return store. 34 complete sectors form eight
// 136-byte lines. Adjacent j values use parity banks; each bank reads once.
// Credits are reserved at read issue, slots returned only after explicit capture.
// Check sidecars are FF arrays (32x10 per bank), protected with their data word.
module ot_hbm_index_lines_sram #(
 parameter integer ENABLE=0,DEPTH=64,CRED=64,
 parameter integer MUT_DATA=0,MUT_CHECK=0,MUT_DOUBLE=0,MUT_SCOREBOARD=0
)(input wire clk,rst_n,start,input wire[8:0] blocks,
 input wire[31:0] sector_v,input wire[383:0] sector_j,input wire[8191:0] sector_data,
 input wire[7:0] credit,output reg[8791:0] lines,output reg[63:0] pop,
 output reg done,output reg fault,output wire retained,output wire[63:0] corrected);
 localparam integer AW=5;
 reg active,active_n;reg[10:0] next_line,nlines,next_line_n,nlines_n;
 reg[6:0] credits[0:7],credits_n[0:7];
 reg[63:0] valid[0:31],valid_n[0:31];
 wire[31:0] wv;wire[383:0] wj;
 reg can,control_bad;
 reg[63:0] need;reg[767:0] rj;
 wire[16383:0] decoded;wire[63:0] dec_v,dec_ue;
 reg[3:0] pipe_v,pipe_v_n;
 reg[10:0] group_tag[0:3],group_tag_n[0:3];reg[63:0] read_need[0:3],read_need_n[0:3];reg[767:0] read_j[0:3],read_j_n[0:3];
 wire[31:0] write_bad;
 integer p,l,b,g,pc,j,bank,k,slot,count,base_sector,delta;
 assign retained=active;
 initial begin
  if(DEPTH!=64)$fatal(1,"native bank successor requires DEPTH64");
  if(CRED<1||CRED>64)$fatal(1,"credit shape");
 end
 always @*begin
  control_bad=(active_n!==~active)||(next_line_n!==~next_line)||(nlines_n!==~nlines);
  for(l=0;l<8;l=l+1)if(credits_n[l]!==~credits[l])control_bad=1;
  for(p=0;p<32;p=p+1)if(valid_n[p]!==~valid[p]||write_bad[p])control_bad=1;
  if(pipe_v_n!==~pipe_v)control_bad=1;
  for(k=0;k<4;k=k+1)if(pipe_v[k]&&((group_tag_n[k]!==~group_tag[k])||(read_need_n[k]!==~read_need[k])||(read_j_n[k]!==~read_j[k])))control_bad=1;
  can=ENABLE!=0&&active&&!fault&&!control_bad&&(next_line<nlines);
  need=0;rj=0;base_sector=(next_line*136)/32;
  for(l=0;l<8;l=l+1)if(credits[l]==0)can=0;
  for(k=0;k<34;k=k+1)begin
   g=base_sector+k;pc=g%32;j=g/32;bank=j%2;
   if(g<((nlines*136+31)/32))begin
   need[pc*2+bank]=1;rj[(pc*2+bank)*12+:12]=12'(j);
   if(!valid[pc][j%64])can=0;end
  end
 end
 genvar gp,gb;
 generate for(gp=0;gp<32;gp=gp+1)begin:pcs
  wire[265:0] encoded;reg ev,ev_n;reg[11:0] ej,ej_n;
  assign write_bad[gp]=(ev_n!==~ev)||(ev&&(ej_n!==~ej));
  assign wv[gp]=ev;assign wj[gp*12+:12]=ej;
  ot_secded_enc #(.K(256),.R(10)) enc(.clk(clk),.d(sector_data[gp*256+:256]),.q(encoded));
  always @(posedge clk or negedge rst_n)if(!rst_n)begin ev<=0;ev_n<=1;end else begin ev<=sector_v[gp];ev_n<=~sector_v[gp];end
  always @(posedge clk)begin ej<=sector_j[gp*12+:12];ej_n<=~sector_j[gp*12+:12];end
  for(gb=0;gb<2;gb=gb+1)begin:banks
   localparam integer ID=gp*2+gb;
   wire[11:0] read_index=rj[ID*12+:12];
   wire we=ENABLE!=0&&ev&&active&&!fault&&ej[0]==gb&&((ej*32+gp)<((nlines*136+31)/32));
   wire re=can&&need[ID];wire[255:0] rd;
   reg[9:0] check[0:31];reg[9:0] check_q;
   reg[265:0] capture;
   ot_sram_1r1w_128x256_m1_r2c2 mem(.clk(clk),.r_ce_in(re),.r_addr_in({2'd0,read_index[5:1]}),.rd_out(rd),
    .w_ce_in(we),.w_addr_in({2'd0,ej[5:1]}),.wd_in(encoded[255:0]),.w_mask_in({256{1'b1}}),
    .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
   always @(posedge clk)begin
    if(we)check[ej[5:1]]<=encoded[265:256];
    if(re)check_q<=check[read_index[5:1]];
    if(pipe_v[0]&&read_need[0][ID])capture<={check_q,rd} ^
     ((ID==0&&MUT_DATA!=0)?266'd1:266'd0) ^
     ((ID==0&&MUT_CHECK!=0)?(266'd1<<256):266'd0) ^
     ((ID==0&&MUT_DOUBLE!=0)?266'd3:266'd0);
   end
   ot_secded_dec #(.K(256),.R(10)) dec(.clk(clk),.rst_n(rst_n),.v(pipe_v[1]&&read_need[1][ID]),.w(capture),
    .ov(dec_v[ID]),.d(decoded[ID*256+:256]),.ce(corrected[ID]),.ue(dec_ue[ID]),.n_ce(),.n_ue());
  end
 end endgenerate
 reg[8791:0] assembled;reg output_bad;
 always @*begin
  assembled=0;output_bad=0;
  for(k=0;k<64;k=k+1)if(read_need[3][k]&&(!dec_v[k]||dec_ue[k]))output_bad=1;
  for(l=0;l<8;l=l+1)begin
   assembled[l*1099]=1;assembled[l*1099+1+:10]=10'(group_tag[3]+l);
   if(group_tag[3]+l<nlines)for(b=0;b<136;b=b+1)begin
    g=(group_tag[3]+l)*136+b;pc=(g/32)%32;j=g/1024;bank=j%2;
    assembled[l*1099+11+b*8+:8]=decoded[(pc*2+bank)*256+(g%32)*8+:8];
   end
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   active<=0;active_n<=1;next_line<=0;next_line_n<=~11'd0;nlines<=0;nlines_n<=~11'd0;
   lines<=0;pop<=0;done<=0;fault<=0;pipe_v<=0;pipe_v_n<=~4'd0;
   for(p=0;p<32;p=p+1)begin valid[p]<=0;valid_n[p]<=~64'd0;end
   for(l=0;l<8;l=l+1)begin credits[l]<=CRED;credits_n[l]<=~7'(CRED);end
  end else if(ENABLE!=0)begin
   lines<=0;pop<=0;done<=0;pipe_v<={pipe_v[2:0],can};pipe_v_n<=~{pipe_v[2:0],can};
   group_tag[0]<=next_line;group_tag_n[0]<=~next_line;read_need[0]<=need;read_need_n[0]<=~need;read_j[0]<=rj;read_j_n[0]<=~rj;
   for(k=1;k<4;k=k+1)begin group_tag[k]<=group_tag[k-1];group_tag_n[k]<=group_tag_n[k-1];read_need[k]<=read_need[k-1];read_need_n[k]<=read_need_n[k-1];read_j[k]<=read_j[k-1];read_j_n[k]<=read_j_n[k-1];end
   if(control_bad)fault<=1;
   for(l=0;l<8;l=l+1)begin
    if(credit[l]&&credits[l]==CRED&&!can)fault<=1;
    credits[l]<=credits[l]+7'(credit[l])-7'(can);
    credits_n[l]<=~(credits[l]+7'(credit[l])-7'(can));
   end
   if(start)begin
    if(active||pipe_v!=0||blocks>342)fault<=1;
    else begin
     active<=blocks!=0;active_n<=blocks==0;done<=blocks==0;next_line<=0;next_line_n<=~11'd0;nlines<=11'(blocks)*4;nlines_n<=~(11'(blocks)*4);
     for(p=0;p<32;p=p+1)begin valid[p]<=0;valid_n[p]<=~64'd0;end
    end
   end
   if(can)begin next_line<=next_line+11'd8;next_line_n<=~(next_line+11'd8);end
   // At this edge each bank's explicit capture receives the actual macro word.
   // Only now may the producer regain and reuse the corresponding slot.
   for(p=0;p<32;p=p+1)begin
    count=0;
    for(bank=0;bank<2;bank=bank+1)if(pipe_v[0]&&read_need[0][p*2+bank])begin
     slot=read_j[0][(p*2+bank)*12+:12]%64;
     valid[p][slot]<=0;valid_n[p][slot]<=1;count=count+1;
    end
    if(wv[p])begin
     j=wj[p*12+:12];
     if(j*32+p>=((nlines*136+31)/32))count=count+1;
     else if(!active||valid[p][j%64])fault<=1;
     else begin valid[p][j%64]<=1;valid_n[p][j%64]<=0;end
    end
    if(count>3)fault<=1;
    pop[p*2+:2]<=2'(count);
   end
   if(MUT_SCOREBOARD!=0&&can)valid_n[0][0]<=valid[0][0];
   if(pipe_v[3])begin
    if(output_bad||fault||control_bad)fault<=1;
    else begin
     lines<=assembled;
     if(group_tag[3]+8>=nlines)begin active<=0;active_n<=1;done<=1;end
    end
   end
  end
 end
endmodule
`default_nettype wire
