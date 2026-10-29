module proof #(parameter integer N=4,EW=37,MUTANT=0,REF_MUT=0)(
 input wire compact,input wire[N*EW-1:0]raw,
 input wire[15:0]threshold,input wire[13:0]ties,
 input wire[$clog2(2*N)-1:0]fill,
 input wire[2*N*EW-1:0]buf_q,
 output wire bad
);
 localparam integer FW=$clog2(2*N);
 reg[2*N*EW-1:0] old_p;
 reg[FW:0] old_f;
 reg[13:0]old_t,old_c;
 reg[N-1:0]old_m;
 reg[15:0]x,ky;
 reg choose;
 always @*begin
  old_p=buf_q;old_f={1'b0,fill};old_t=ties;old_c=0;old_m=0;
  for(integer l=0;l<N;l=l+1)begin
   x=raw[l*EW+1+:16];ky=x[15]?~x:(x^16'h8000);
   choose=raw[l*EW]&&(ky>threshold||(ky==threshold&&old_t!=0));
   if(REF_MUT==1)choose=raw[l*EW]&&(ky>=threshold);
   if(compact&&choose)begin
    old_p[old_f*EW+:EW]=raw[l*EW+:EW];old_f=old_f+1;old_c=old_c+1;old_m[l]=1;
    if(ky==threshold&&old_t!=0)old_t=old_t-1;
   end
  end
 end
 wire[2*N*EW-1:0]p;
 wire[FW:0]f;
 wire[13:0]t,c;
 wire[N-1:0]m;
 ot_hbm_idx_selector_compact #(.N(N),.EW(EW),.MUT(MUTANT)) dut(
  .compact(compact),.raw(raw),.threshold(threshold),.ties(ties),.fill(fill),.buf_q(buf_q),
  .packed_next(p),.fill_next(f),.ties_next(t),.chosen_next(c),.mask_choose(m));
 assign bad=({old_p,old_f,old_t,old_c,old_m}!={p,f,t,c,m});
endmodule
