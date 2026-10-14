`timescale 1ns/1ps
module tb_hgi_dma_front_xs_vm2;
 parameter integer MUT=0;
 localparam NIN=16,NB=8;
 reg clk=0; always #1 clk=~clk;
 reg [NB*NIN-1:0] xo=0; reg [NIN*277-1:0] ls=0;
 wire [NB*280-1:0] wd; wire [NB-1:0] v_o,bad_o;
 ot_hgi_dma_front_xs_vm2 #(.NIN(NIN),.NBS(NB),.MUT(MUT)) dut(.clk(clk),.xo(xo),.ls_a(ls[0+:8*277]),.ls_b(ls[8*277+:8*277]),.wd(wd),.v_o(v_o),.bad_o(bad_o));
    function automatic [31:0] f32(input real v);
        reg [63:0] d;
        begin
            d = $realtobits(v);
            f32 = (d[62:0] == 63'd0) ? {d[63], 31'd0} : {d[63], 8'(d[62:52] - 11'd1023 + 11'd127), d[51:29]};
        end
    endfunction
    function automatic [31:0] e4(input [7:0] c);
        real v; integer e, m; reg [31:0] r;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 15 && m == 7) e4 = 32'h7FC00000;
            else begin
                v = (e == 0) ? (m / 8.0) * (2.0 ** -6) : (1.0 + m / 8.0) * (2.0 ** (e - 7));
                r = f32(v); r[31] = c[7];
                if (v == 0.0) r = {c[7], 31'd0};
                e4 = r;
            end
        end
    endfunction
    function automatic [31:0] i8(input [7:0] c); i8 = f32(real'($signed(c))); if (c == 0) i8 = 0; endfunction

 integer errors=0,records=0;
 reg [255:0] data;
 reg [17:0] sec;
 reg [2:0] fmt;
 integer lane,esize,slots;
 reg [NB-1:0] expect_v [0:4],expect_bad [0:4];
 reg [279:0] expect_frame [0:4][0:NB-1];
 initial for(integer depth=0;depth<5;depth=depth+1) begin expect_v[depth]=0;expect_bad[depth]=0;end
 always @(posedge clk) begin
  for(integer depth=4;depth>0;depth=depth-1) begin
   expect_v[depth]<=expect_v[depth-1];expect_bad[depth]<=expect_bad[depth-1];
   for(integer bank=0;bank<NB;bank=bank+1) expect_frame[depth][bank]<=expect_frame[depth-1][bank];
  end
  for(integer bank=0;bank<NB;bank=bank+1) begin
   reg valid;reg [17:0] sector;reg [255:0] want;integer pos;
   valid=xo[bank*NIN+:NIN]!='0;pos=0;want=0;
   for(integer slot=0;slot<slots;slot=slot+1) if((sec+slot)%NB==bank)pos=slot;
   sector=sec+pos;
   for(integer w=0;w<8;w=w+1) begin
    case(fmt)
     1:want[w*32+:32]={data[(pos*8+w)*16+:16],16'b0};
     2:want[w*32+:32]=e4(data[(pos*8+w)*8+:8]);
     4:want[w*32+:32]=i8(data[(pos*8+w)*8+:8]);
     default:want[w*32+:32]=data[w*32+:32];
    endcase
   end
   expect_v[0][bank]<=valid;expect_bad[0][bank]<=valid && sector>=36864;
   expect_frame[0][bank]<={sector>=32768 && sector<36864,sector[14:0],want,sector>=36864?8'h00:8'hff};
  end
 end
 integer cycles=0;
 always @(negedge clk) begin
  cycles=cycles+1;
  if(cycles>7)for(integer bank=0;bank<NB;bank=bank+1)begin
   if(v_o[bank]!==expect_v[4][bank] || bad_o[bank]!==expect_bad[4][bank] ||
    (expect_v[4][bank] && wd[bank*280+:280]!==expect_frame[4][bank]))begin
     if(errors<8)$display("FAIL nativeframe cycle%0d bank%0d valid%0b/%0b bad%0b/%0b got%h want%h",cycles,bank,v_o[bank],expect_v[4][bank],bad_o[bank],expect_bad[4][bank],wd[bank*280+:280],expect_frame[4][bank]);
     errors=errors+1;
   end
  end
 end
 initial begin
  repeat(7) @(negedge clk);
  for(integer mode=0;mode<5;mode=mode+1) begin
   fmt=mode==3?3'd4:mode==4?3'd5:3'(mode);
   esize=(fmt==0||fmt==5)?4:fmt==1?2:1; slots=4/esize;
   for(integer range_case=0;range_case<6;range_case=range_case+1) begin
    sec=range_case==0?18'd6:range_case==1?18'd19584:range_case==2?18'd32768:range_case==3?18'd36862:range_case==4?18'd36864:18'd65536;
    for(integer turn=0;turn<16;turn=turn+1) begin
     xo=0;ls=0;lane=turn;
     for(integer byte_idx=0;byte_idx<32;byte_idx=byte_idx+1) data[byte_idx*8+:8]=8'((byte_idx*73+turn*37+range_case*29)^8'hb5);
     ls[lane*277+:277]={fmt,sec,data};
     for(integer slot=0;slot<slots;slot=slot+1) xo[((sec+slot)%NB)*NIN+lane]=1'b1;
     @(negedge clk);
     records=records+1;
    end
   end
  end
  xo=0; repeat(7) @(negedge clk); #0.01;
  if(errors) $fatal(1,"FATAL XS_VM errors=%0d records=%0d",errors,records);
  $display("PASS XS_VM records=%0d globalmain/mirror/unsupported_range valid_mask_data exact",records);$finish;
 end
endmodule
