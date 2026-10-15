`timescale 1ns/1ps
`default_nettype none
// IDX-P admission before legacy18-bit truncation. Full bases/extents use41bits.
module ot_hgi_idx_b2_record_guard(input wire [2074:0] rec,
 output wire index_record, output wire legal, output reg [2074:0] rebased);
 wire [127:0] h=rec[128:1];
 wire [255:0] a=rec[384:129],b=rec[640:385],c=rec[896:641],d=rec[1152:897],o=rec[1408:1153],r=rec[1664:1409];
 wire [39:0] ab=a[47:8],bb=b[47:8],cb=c[47:8],db=d[47:8],ob=o[47:8],rb=r[47:8];
 wire [19:0] cn=c[67:48];wire [31:0] cs=c[119:88],ds=d[119:88];
 wire [11:0] k=h[75:64];wire keep=h[77],cand=h[76],has_r=h[98];
 function automatic mirror_fit(input [39:0] base,input [40:0] words);
  mirror_fit=base>=40'd262144&&{1'b0,base}+words<=41'd294912;
 endfunction
 function automatic local_fit(input [39:0] base,input [40:0] words);
  local_fit={1'b0,base}+words<=41'd65536;
 endfunction
 assign index_record=h[123:118]==6'd0;
 assign legal=!index_record||(mirror_fit(ab,41'd4096)&&ab[2:0]==0&&mirror_fit(bb,41'd32)&&
  (!keep||(cn!=0&&cn<=2048&&cs[4:0]==0&&cs>=cn&&mirror_fit(cb,{9'd0,cs}+{21'd0,cn})))&&
  k!=0&&k<=512&&local_fit(ob,{29'd0,k})&&(!has_r||local_fit(rb,{29'd0,k}))&&
  (!cand||(ds>=1368&&local_fit(db,{9'd0,ds}+41'd1368))));
 always @* begin
  rebased=rec;
  if(index_record)begin
   rebased[176:137]=ab;
   rebased[432:393]=bb-40'd262144;
   rebased[688:649]=cb-40'd262144;
  end
 end
endmodule
`default_nettype wire
