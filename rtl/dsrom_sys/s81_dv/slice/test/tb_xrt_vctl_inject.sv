`timescale 1ns/1ps
// Smallest real path for the compiler's V_CTL_INJECT price:
// V pin -> real ring-stop delivery -> selected XRT -> real ring-stop line output.
module tb_xrt_vctl_inject #(parameter integer HB=0);
  reg clk=0; always #0.5 clk=~clk;
  reg rst_n=0; reg [3:0] sid=0; reg [275:0] vi=0;
  wire [1103:0] re, rw, de, dw; wire [275:0] dv;
  wire ev,wv,vv; wire [1075:0] cb; wire [2:0] cd;
  wire rf,xf;
  ot_s81sl_rstop rs(.clk(clk),.rst_n(rst_n),.sid(sid),.ri_w(1104'd0),.ri_e(1104'd0),
    .ro_e(re),.ro_w(rw),.vi(vi),.vo(),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),
    .nx_wi(),.nx_ei(),.nx_eo(173'd0),.nx_wo(173'd0),.g_v(),.g_fam(),.g_idx(),.g_d(),
    .dl_ev(ev),.dl_e(de),.dl_wv(wv),.dl_w(dw),.dl_vv(vv),.dl_vb(dv),
    .ci_dir(cd),.ci_b({28'd0,cb}),.fault(rf));
  ot_s81sl_xrt #(.HB(HB),.FACE_LAND(1),.PDSK(15'o01234)) xr(
    .clk(clk),.rst_n(rst_n),.sid(sid),.dl_ev(ev),.dl_e(de[1075:1]),.dl_wv(wv),.dl_w(dw[1075:1]),
    .dl_vv(vv),.dl_vb(dv[275:1]),.ci_dir(cd),.ci_b(cb),.bi(1046'd0),.lo_v(5'd0),.lo_d(1280'd0),
    .p_v(5'd0),.p_d(160'd0),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),.eg_v(1'b0),.eg_c(2'd0),
    .eg_d(32'd0),.x_rbv(1'b0),.x_rbd(32'd0),.fault(xf));
  reg [275:0] word_; reg [1103:0] ee,ew; integer s,j,k,n,errors=0,checks=0,expected_age=7;
  initial begin
    if ($value$plusargs("age=%d",expected_age)) begin end
    repeat(15) @(negedge clk); rst_n=1; repeat(15) @(negedge clk);
    for(s=0;s<16;s=s+1) begin
      sid=s; repeat(5) @(negedge clk);
      for(j=0;j<12;j=j+1) begin
        // All CTL targets 0..5, both own and non-own slice masks. No arithmetic payloads needed.
        word_=276'd0;word_[0]=1;word_[3:1]=0;word_[8:4]=5'd19;word_[12:9]=4'd13;
        word_[21+:16]=(j[0]?16'hffff:(16'd1<<s));word_[37+:5]=j%6;
        word_[42+:5]=5'b10101;word_[47+:160]={32'h12345678+s,32'h76543210+j,32'hdeadbeef,64'h0807060504030201};
        // Avoid invalid send configs / row writes; focus V re-injection, all CTL payload bits retained.
        if(j%6==4) word_[47+:160]=160'd0;
        vi=word_;ee={828'd0,word_};ew=ee;ee[8:4]=7-(s>>1);ew[8:4]=(s>>1);ee[12:9]=s;ew[12:9]=s;
        for(k=1;k<=11;k=k+1) begin
          @(posedge clk);#0.01;
          checks=checks+2;
          if(re!==(k==expected_age?ee:1104'd0)) begin errors=errors+1;if(errors<5)$display("XRT_INJECT_BAD E sid=%0d job=%0d edge=%0d expected_age=%0d got=%h exp=%h",s,j,k,expected_age,re,ee);end
          if(rw!==(k==expected_age?ew:1104'd0)) begin errors=errors+1;if(errors<5)$display("XRT_INJECT_BAD W sid=%0d job=%0d edge=%0d expected_age=%0d got=%h exp=%h",s,j,k,expected_age,rw,ew);end
          @(negedge clk);vi=0;
        end
      end
    end
    $display("XRT_INJECT hb=%0d jobs=192 checks=%0d age=%0d errors=%0d",HB,checks,expected_age,errors);
    if(errors==0)$display("PASS");else $display("FAIL");$finish;
  end
endmodule
