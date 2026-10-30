module cache_refinement #(parameter integer MUT=0)(
 input wire ck,rst_n,input wire begin0,begin1,active0,active1,
 input wire [58:0] begin_tag0,begin_tag1,
 input wire complete0,complete1,input wire [15:0] epoch16,
 input wire [61:0] obs_ctx,input wire [46:0] obs_res,
 output wire status_bad,output wire invariant_bad,output wire mask_bad,output wire proof_bad
);
 reg [58:0] tag0,tag1;
 wire legal0=begin_tag0[42:37]>=1&&begin_tag0[42:37]<=36&&begin_tag0[36:19]<151936&&begin_tag0[5:0]==0;
 wire legal1=begin_tag1[42:37]>=1&&begin_tag1[42:37]<=36&&begin_tag1[36:19]<151936&&begin_tag1[5:0]==0;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin tag0<=0;tag1<=0;end
  else begin
   if(begin0&&!(active0||!legal0))tag0<=begin_tag0;
   if(begin1&&!(active1||!legal1))tag1<=begin_tag1;
  end
 wire c0=rst_n&&complete0,c1=rst_n&&complete1;
 wire [14:0] cached0,cached1;
 qfd_status_obs_hold_chunk #(.W(15)) s0(.ck(ck),.a(c0),.b(1'b1),.c(1'b1),.d(tag0[14:0] ^ (MUT==1 ? 15'd1 : 15'd0)),.q(cached0));
 qfd_status_obs_hold_chunk #(.W(15)) s1(.ck(ck),.a(c1),.b(1'b1),.c(1'b1),.d(tag1[14:0]),.q(cached1));
 reg last_slot,completed,seen;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin last_slot<=0;completed<=0;seen<=0;end
  else begin
   completed<=c0||c1;
   if(c0||c1)seen<=1;
   if(c0)last_slot<=(MUT==2)?1'b1:1'b0;
   else if(c1)last_slot<=(MUT==2)?1'b0:1'b1;
  end
 wire [5:0] selected_tag=last_slot?cached1[5:0]:cached0[5:0];
 wire [59:0] original={completed,53'd0,selected_tag};
 wire [59:0] folded={completed,59'd0};
 wire [207:0] so,sf;wire fo,ff;
 ot_qwen_status_obs_v1_state actual(.ck(ck),.rst_n({3{rst_n}}),.epoch16(epoch16),.obs_ctx(obs_ctx),.obs_res(obs_res),.obs_native(original),.snapshot(so),.fault(fo));
 ot_qwen_status_obs_v1_state constant_bits(.ck(ck),.rst_n({3{rst_n}}),.epoch16(epoch16),.obs_ctx(obs_ctx),.obs_res(obs_res),.obs_native(folded),.snapshot(sf),.fault(ff));
 assign invariant_bad=(|tag0[5:0])||(|tag1[5:0])||(seen&&(|selected_tag))||(completed&&!seen);
 assign status_bad=(so!=sf)||(fo!=ff);
 assign mask_bad=invariant_bad||(so[94]&&!seen)||(|so[7:2]);
 assign proof_bad=invariant_bad||status_bad;
endmodule
