"""Build opt-in same-cycle selected-only source from the pinned die master."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[2]
src=subprocess.check_output(['git','show','d34578d6f:rtl/hbm_accel/index/ot_hbm_idx_selector_static_sel.sv'],cwd=root,text=True)
src=src.replace('parameter integer MUT=0','parameter integer MUT=0,STRUCT=0')
src=src.replace('#(.MUT(MUT)) core(', '#(.MUT(MUT),.STRUCT(STRUCT)) core(')
start=src.index('  always @*begin\n   packed_next=buf_q;')
end=src.index('  always @(posedge clk_q[q]',start)
legacy=src[start:end]
bounded='''  if(STRUCT)begin:bounded_pack
   ot_hbm_idx_selector_compact #(.N(W),.EW(EW),.MUT(MUT)) pack(
    .compact(compact),.raw(raw[W*EW-1:0]),.threshold(threshold),
    .ties(comp_started?tie_rem:ties[q]),.fill(fill),.buf_q(buf_q),
    .packed_next(packed_next),.fill_next(fill_next),.ties_next(ties_next),
    .chosen_next(chosen_next),.mask_choose(mask_choose));
  end else begin:legacy_pack
'''+legacy+'''  end
'''
src=src[:start]+bounded+src[end:]
function=''' function automatic [4:0] pop16(input [15:0] v);
  reg[1:0] p[0:7];reg[2:0] q[0:3];reg[3:0] h[0:1];
  begin
   for(integer i=0;i<8;i=i+1)p[i]={1'b0,v[2*i]}+{1'b0,v[2*i+1]};
   for(integer i=0;i<4;i=i+1)q[i]={1'b0,p[2*i]}+{1'b0,p[2*i+1]};
   for(integer i=0;i<2;i=i+1)h[i]={1'b0,q[2*i]}+{1'b0,q[2*i+1]};
   pop16={1'b0,h[0]}+{1'b0,h[1]};
  end
 endfunction
'''
src=src.replace(' reg [15:0] threshold;',function+' reg [15:0] threshold;',1)
src=src.replace('  integer count;','  integer count;\n  reg[15:0] hist_hits;')
before='''      count=0;
      for(integer l=0;l<W;l=l+1)begin
       if(op==2)begin
        if(in_line[q*LW+l*EW]&&(orderkey(in_line[q*LW+l*EW+1+:16])>>11)==16'(b))count=count+1;
       end else if(raw[l*EW]&&((orderkey(raw[l*EW+1+:16])&prior_mask)==(threshold&prior_mask))&&
         ((orderkey(raw[l*EW+1+:16]) >> shift)&binmask)==16'(b))count=count+1;
      end
      hist[q][b]<=hist[q][b]+14'(count);
'''
after='''      if(STRUCT)begin
       hist_hits=0;
       for(integer l=0;l<W;l=l+1)begin
        if(op==2)begin
         if(in_line[q*LW+l*EW]&&((orderkey(in_line[q*LW+l*EW+1+:16])>>11)==16'(b)))hist_hits[l]=1;
        end else if(raw[l*EW]&&((orderkey(raw[l*EW+1+:16])&prior_mask)==(threshold&prior_mask))&&
         (((orderkey(raw[l*EW+1+:16])>>shift)&binmask)==16'(b)))hist_hits[l]=1;
       end
       hist[q][b]<=hist[q][b]+14'(pop16(hist_hits));
      end else begin
'''+before+'''      end
'''
assert before in src
src=src.replace(before,after,1)
(root/'rtl/hbm_accel/index/ot_hbm_idx_selector_static_sel.sv').write_text(src)
(root/'results/hbm_selector_1028/hist_proof.sv').write_text('''module hist_proof(input wire[15:0] v,output wire bad);
'''+function+''' integer old_count;
 always @*begin
  old_count=0;
  for(integer l=0;l<16;l=l+1)if(v[l])old_count=old_count+1;
 end
 assign bad=(old_count!=32'(pop16(v)));
endmodule
''')
