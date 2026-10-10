`timescale 1ns/1ps
`default_nettype none
// Model-before-RTL: hgi_dma_wide_vm_20261010_r1 + local four-bank converter sizing.
// Four immutable raw buffers, four independently held output pin registers.
// Raw E0 capture -> converted/pin-held E1 -> consumer earliest E2.
// Last-piece ownership transfers into the held output before same-edge raw refill.
module ot_hgi_dma_wide_convert_tile #(parameter integer ENABLE=0,TILE=0,NB=512,MUT=0)(
 input wire clk,rst_n,
 input wire[3:0]raw_v,output wire[3:0]raw_r,
 input wire[71:0]raw_sec,input wire[1023:0]raw_data,input wire[7:0]raw_fmt,input wire[15:0]raw_piece_mask,
 output wire[3:0]bank_v,input wire[3:0]bank_r,
 output wire[71:0]bank_sec,output wire[1023:0]bank_data,output wire[31:0]bank_word_mask,
 output reg fault);
    function automatic [31:0] i8_f(input [7:0] c);
        reg [7:0] a; reg [2:0] p; integer k;
        begin
            a = c[7] ? (~c + 8'd1) : c; p = 3'd0;
            for (k = 0; k < 8; k = k + 1) if (a[k]) p = k[2:0];
            i8_f = (a == 8'd0) ? 32'd0 : {c[7], 8'd127 + {5'd0, p}, ({15'd0, a} << (5'd23 - {2'd0, p})) & 23'h7FFFFF};
        end
    endfunction
    function automatic [31:0] e4m3_f(input [7:0] c);
        reg [3:0] e; reg [2:0] m; reg [1:0] p;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 4'hF && m == 3'h7) e4m3_f = 32'h7FC00000;
            else if (e == 4'd0) begin
                if (m == 3'd0) e4m3_f = {c[7], 31'd0};
                else begin
                    p = m[2] ? 2'd2 : m[1] ? 2'd1 : 2'd0;
                    e4m3_f = {c[7], 8'd127 - 8'd9 + {6'd0, p}, ({20'd0, m} << (5'd23 - {3'd0, p})) & 23'h7FFFFF};
                end
            end else e4m3_f = {c[7], 8'd120 + {4'd0, e}, m, 20'd0};
        end
    endfunction
    function automatic [255:0] conv(input [255:0] s, input [2:0] f, input [1:0] j);
        reg [255:0] o; integer w; reg [7:0] b; reg [15:0] h;
        begin
            o = 256'd0;
            for (w = 0; w < 8; w = w + 1) begin
                case (f)
                    3'd1: begin h = s[({3'd0, j} * 8 + w) * 16 +: 16]; if (MUT == 1) h = s[({3'd0, j} * 8 + (7 - w)) * 16 +: 16];
                                o[w*32 +: 32] = {h, 16'd0}; end
                    3'd2: begin b = s[({3'd0, j} * 8 + w) * 8 +: 8]; o[w*32 +: 32] = e4m3_f(b); end
                    3'd4: begin b = s[({3'd0, j} * 8 + w) * 8 +: 8]; o[w*32 +: 32] = i8_f(b); end
                    default: o[w*32 +: 32] = s[w*32 +: 32];
                endcase
            end
            conv = o;
        end
    endfunction

 reg[3:0]remain[0:3],remain_n[0:3];
 reg[17:0]sec[0:3],sec_n[0:3];reg[1:0]fmt[0:3],fmt_n[0:3];
 reg[255:0]data[0:3],data_n[0:3];
 reg[1:0]rr[0:3],rr_n[0:3];
 reg[3:0]ov,ov_n;reg[17:0]os[0:3],os_n[0:3];reg[255:0]od[0:3],od_n[0:3];
 reg bad;integer i,b,j;
 always @*begin
  bad=(ov_n!==~ov)||(NB<4)||(NB%4!=0)||(TILE<0)||(TILE>=NB/4);
  for(integer x=0;x<4;x=x+1)begin
   if(remain_n[x]!==~remain[x]||rr_n[x]!==~rr[x])bad=1;
   if(remain[x]!=0&&(sec_n[x]!==~sec[x]||fmt_n[x]!==~fmt[x]||data_n[x]!==~data[x]))bad=1;
   if(ov[x]&&(os_n[x]!==~os[x]||od_n[x]!==~od[x]))bad=1;
  end
 end
 wire okay=(ENABLE!=0)&&!fault&&!bad;
 reg[3:0]grant[0:3];reg[1:0]pick[0:3],piece[0:3];reg[3:0]fill;
 reg found;integer sidx;reg[18:0]target;
 always @*begin
  for(integer x=0;x<4;x=x+1)begin grant[x]=0;pick[x]=0;piece[x]=0;end
  fill=0;found=0;sidx=0;target=0;
  for(integer bb=0;bb<4;bb=bb+1)begin
   found=0;
   for(integer off=0;off<4;off=off+1)begin
    sidx=(int'(rr[bb])+off)%4;
    for(integer pp=0;pp<4;pp=pp+1)begin
     target={1'b0,sec[sidx]}+19'(pp);
     if(!found&&remain[sidx][pp]&&int'(target)%NB==TILE*4+bb)begin
      found=1;pick[bb]=2'(sidx);piece[bb]=2'(pp);
     end
    end
   end
   if(okay&&found&&(!ov[bb]||bank_r[bb]))begin
    fill[bb]=1;grant[pick[bb]][piece[bb]]=1;
   end
  end
 end
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:ports
  assign raw_r[g]=okay&&((remain[g]&~grant[g])==0);
  assign bank_v[g]=okay&&ov[g];
  assign bank_sec[g*18+:18]=os[g];assign bank_data[g*256+:256]=od[g];
  assign bank_word_mask[g*8+:8]=8'hff;
 end endgenerate
 reg[3:0]incoming_bad;
 reg[18:0]incoming_target;integer count;
 always @*begin
  incoming_bad=0;incoming_target=0;count=0;
  for(integer x=0;x<4;x=x+1)begin
   count=raw_fmt[x*2+:2]==0?1:raw_fmt[x*2+:2]==1?2:4;
   if(raw_fmt[x*2+:2]==3)incoming_bad[x]=1;
   for(integer p=0;p<4;p=p+1)if(raw_piece_mask[x*4+p])begin
    incoming_target={1'b0,raw_sec[x*18+:18]}+19'(p);
    if(p>=count||incoming_target[18]||int'(incoming_target)%NB/4!=TILE)incoming_bad[x]=1;
   end
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   fault<=0;ov<=0;ov_n<=4'hf;
   for(i=0;i<4;i=i+1)begin
    remain[i]<=0;remain_n[i]<=4'hf;rr[i]<=0;rr_n[i]<=2'b11;
    sec[i]<=0;sec_n[i]<='1;fmt[i]<=0;fmt_n[i]<='1;data[i]<=0;data_n[i]<='1;
    os[i]<=0;os_n[i]<='1;od[i]<=0;od_n[i]<='1;
   end
  end else begin
   if(bad)fault<=1;
   for(i=0;i<4;i=i+1)begin
    if(raw_v[i]&&raw_r[i])begin
     if(incoming_bad[i])begin fault<=1;remain[i]<=0;remain_n[i]<=4'hf;end
     else begin
      remain[i]<=raw_piece_mask[i*4+:4];remain_n[i]<=~raw_piece_mask[i*4+:4];
      sec[i]<=raw_sec[i*18+:18];sec_n[i]<=~raw_sec[i*18+:18];
      fmt[i]<=raw_fmt[i*2+:2];fmt_n[i]<=~raw_fmt[i*2+:2];data[i]<=raw_data[i*256+:256];data_n[i]<=~raw_data[i*256+:256];
     end
    end else begin
     remain[i]<=((MUT==3)&&|grant[i])?4'd0:(remain[i]&~grant[i]);
     remain_n[i]<=~(((MUT==3)&&|grant[i])?4'd0:(remain[i]&~grant[i]));
    end
   end
   for(b=0;b<4;b=b+1)begin
    if(okay&&fill[b])begin
     ov[b]<=1;ov_n[b]<=0;
     os[b]<=sec[pick[b]]+18'(piece[b]);os_n[b]<=~(sec[pick[b]]+18'(piece[b]));
     od[b]<=conv(data[pick[b]],(MUT==2)?3'd0:{1'b0,fmt[pick[b]]},(MUT==1)?(piece[b]^2'd1):piece[b]);
     od_n[b]<=~conv(data[pick[b]],(MUT==2)?3'd0:{1'b0,fmt[pick[b]]},(MUT==1)?(piece[b]^2'd1):piece[b]);
     rr[b]<=pick[b]+2'd1;rr_n[b]<=~(pick[b]+2'd1);
    end else if(okay&&bank_r[b])begin ov[b]<=0;ov_n[b]<=1;end
   end
  end
 end
endmodule
`default_nettype wire
