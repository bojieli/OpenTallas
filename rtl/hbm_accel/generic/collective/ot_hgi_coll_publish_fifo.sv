`timescale 1ns/1ps
`default_nettype none
// One protected publisher lane. All128 admitted entries include input/read/head
// stages. Data remains SECDED encoded through SRAM and prefetched flop heads.
module ot_hgi_coll_publish_fifo #(parameter integer ENABLE=0,W=544,MUT=0)(
 input wire clk,rst_n,push,pop,input wire[W-1:0] din,
 output wire valid,output wire[W-1:0] dout,output wire corrected,
 output reg fault,output wire[7:0] occupancy
);
 localparam integer NW=(W+31)/32,EW=NW*39;
 reg[EW-1:0] din_p,raw_q,head[0:3];wire[EW-1:0]rd;
 reg[7:0] sc,si,total,ti;reg[6:0]wp,wi,rp,ri;
 reg[2:0]ocr,oi,hc,hi;reg[1:0]hp,hpi,ht,hti;
 reg pp,ppi,v1,v1i,v2,v2i;
 wire corrupt=(sc^si)!=8'hff||(total^ti)!=8'hff||(wp^wi)!=7'h7f||
  (rp^ri)!=7'h7f||(ocr^oi)!=3'h7||(hc^hi)!=3'h7||
  (hp^hpi)!=2'h3||(ht^hti)!=2'h3||(pp^ppi)!=1'b1||
  (v1^v1i)!=1'b1||(v2^v2i)!=1'b1||total>128||sc>128||hc>4||ocr>4||
  total!=(integer'(sc)+integer'(hc)+integer'(pp)+integer'(v1)+integer'(v2))||
  integer'(ocr)+integer'(hc)+integer'(v1)+integer'(v2)!=4;
 wire safe=ENABLE!=0&&!fault&&!corrupt;
 wire[NW*32-1:0] padded={{(NW*32-W){1'b0}},din};wire[EW-1:0]encoded;
 wire[NW*32-1:0]decoded;wire[NW-1:0]ce,ue;
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

 for(genvar w=0;w<NW;w=w+1)begin: g_ecc
  assign encoded[w*39+:39]=enc(padded[w*32+:32]);
  wire[33:0] result=dec(head[hp][w*39+:39]);
  assign decoded[w*32+:32]=result[31:0];assign ce[w]=result[32];assign ue[w]=result[33];
 end
 assign valid=safe&&hc!=0&&!(|ue);
 assign dout=decoded[W-1:0];assign corrected=valid&&(|ce);assign occupancy=total;
 wire dp=pop&&valid;
 wire accept=push&&safe&&(total<128||dp);
 wire put=pp&&safe&&sc<128;
 wire fetch=safe&&sc!=0&&ocr!=0;
 wire hput=safe&&v2;
 wire[7:0] sn=sc+8'(put)-8'(fetch),tn=total+8'(accept)-8'(dp);
 wire[6:0]wn=wp+7'(put),rn=rp+7'(fetch);
 wire[2:0]onext=ocr-3'(fetch)+3'(dp),hn=hc+3'(hput)-3'(dp);
 wire[1:0]hpn=hp+2'(dp),htn=ht+2'(hput);
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   sc<=0;si<=8'hff;total<=0;ti<=8'hff;wp<=0;wi<=7'h7f;rp<=0;ri<=7'h7f;
   ocr<=4;oi<=~3'd4;hc<=0;hi<=3'h7;hp<=0;hpi<=3;ht<=0;hti<=3;
   pp<=0;ppi<=1;v1<=0;v1i<=1;v2<=0;v2i<=1;fault<=0;
  end else if(ENABLE!=0)begin
   if(corrupt||(hc!=0&&(|ue))||(push&&!accept)||(pop&&!valid)||(pp&&sc==128)||(hput&&hc==4&&!dp))fault<=1;
   if(safe)begin
    sc<=sn;si<=~sn;total<=tn;ti<=~tn;wp<=wn;wi<=~wn;rp<=rn;ri<=~rn;
    ocr<=onext;oi<=~onext;hc<=hn;hi<=~hn;hp<=hpn;hpi<=~hpn;ht<=htn;hti<=~htn;
    pp<=accept;ppi<=~accept;v1<=fetch;v1i<=~fetch;v2<=v1;v2i<=~v1;
   end
  end
 end
 // No combinational logic after SRAM input pin flops or before capture flops.
 always @(posedge clk)begin din_p<=encoded;raw_q<=rd;if(hput)head[ht]<=raw_q;end
 ot_hcoll_sram128 #(.W(EW)) mem(.clk(clk),.r_ce(fetch),.r_addr(rp),.rd(rd),
  .w_ce(put),.w_addr(wp),.wd(din_p));
`ifndef SYNTHESIS
 initial if(W<1)$fatal(1,"publisher FIFO W must bepositive");
`endif
endmodule
`default_nettype wire
