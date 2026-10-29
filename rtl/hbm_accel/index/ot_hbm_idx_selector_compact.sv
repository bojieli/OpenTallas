`default_nettype none
// Same-edge bounded stable compaction, preserving unwritten buffer words.
// N is a power of two. No state and no calendar/port latency change.
module ot_hbm_idx_selector_compact #(parameter integer N=16,EW=37,MUT=0)(
 input wire compact,
 input wire[N*EW-1:0] raw,
 input wire[15:0] threshold,
 input wire[13:0] ties,
 input wire[$clog2(2*N)-1:0] fill,
 input wire[2*N*EW-1:0] buf_q,
 output wire[2*N*EW-1:0] packed_next,
 output wire[$clog2(2*N):0] fill_next,
 output wire[13:0] ties_next,chosen_next,
 output wire[N-1:0] mask_choose
);
 localparam integer CW=$clog2(N+1), FW=$clog2(2*N), BW=2*N*EW;
 // Match the reference procedural if on uninitialised SRAM data as well:
 // an unknown condition does not select a word or consume a tie.
 function automatic known_true(input value);
  begin known_true=0;if(value)known_true=1;end
 endfunction
 wire[N-1:0] eq;
 wire[CW-1:0] prefix[0:N];
 wire[N*EW-1:0] words;
 wire[CW-1:0] count;
 wire[2*N-1:0] write_words;
 wire[BW-1:0] write_mask;
 assign prefix[0]=0;
 for(genvar l=0;l<N;l=l+1)begin:lane
  wire[15:0] x=raw[l*EW+1+:16];
  wire[15:0] ky=x[15]?~x:(x^16'h8000);
  assign eq[l]=known_true(raw[l*EW]&&(ky==threshold));
  assign prefix[l+1]=prefix[l]+CW'(eq[l]);
  assign mask_choose[l]=known_true(compact&&raw[l*EW]&&
   ((MUT==1)?(ky>=threshold):((ky>threshold)||((ky==threshold)&&(14'(prefix[l])<ties)))));
 end
 ot_hbm_idx_compact_tree #(.N(N),.W(EW)) tree(
  .mask(mask_choose),.words(raw),.packed_words(words),.count(count));
 assign chosen_next=14'(count);
 assign fill_next={1'b0,fill}+(FW+1)'(count);
 assign ties_next=compact?(ties-((ties<14'(prefix[N]))?ties:14'(prefix[N]))):ties;
 // Variable shifts are bounded to the actual buffer index width. Unlike a
 // serial partial write, this creates one barrel network after the tree.
 assign write_words=({2*N{1'b1}} << fill)&~({2*N{1'b1}} << fill_next);
 for(genvar j=0;j<2*N;j=j+1)begin:word_mask
  assign write_mask[j*EW+:EW]={EW{write_words[j]}};
 end
 assign packed_next=(buf_q&~write_mask)|
  ({{N*EW{1'b0}},words} << ($clog2(BW+1))'(fill*EW));
endmodule
`default_nettype wire
