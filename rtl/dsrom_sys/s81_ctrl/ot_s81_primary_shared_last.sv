`timescale 1ns/1ps
// OrdinaryfinitearithmeticFIFO8; no protectedflopFIFO hardware. ActualSRAM
// producers retainSECDED before publishing these nativeframes.
module ot_s81_p2_frame_fifo(
 input wire clk,rst_n,input wire iv,output wire ir,input wire[593:0] id,
 output wire ov,input wire ore,output wire[593:0] od,output reg fault
);
 reg[593:0] frames[0:7];reg[2:0] wp,rp;reg[3:0] count;
 assign ir=!fault&&count<8;assign ov=!fault&&count!=0;assign od=frames[rp];
 wire push=iv&&ir,pop=ov&&ore;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin wp<=0;rp<=0;count<=0;fault<=0;end
  else if(!fault)begin
   if(iv&&!ir)fault<=1;
   else begin
    if(push)begin frames[wp]<=id;wp<=wp+1'b1;end
    if(pop)rp<=rp+1'b1;
    case({push,pop})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:count<=count;endcase
   end
  end
 end
endmodule

// Dedicated serial-domain16lane primary SU final add. Upstream A owns exact
// sorted3expert FP32 prefix; shared comes from actual BF16 W2 publisher widened
// to32b/element. The shared operand is LAST, followed by one finalBF16 RNE.
// Native output is80x512b widened32values, not an inventedpacked40flit endpoint.
// CDC and nativeVM rangevisibility/transaction caller must bind separately.
module ot_s81_primary_shared_last #(parameter integer ENABLE=0)(
 input wire clk,rst_n,
 input wire p_valid,output wire p_ready,input wire[511:0] p_data,
 input wire[73:0] p_tag,input wire[6:0] p_word,input wire p_last,
 input wire s_valid,output wire s_ready,input wire[511:0] s_data,
 input wire[73:0] s_tag,input wire[6:0] s_word,input wire s_last,
 output wire out_valid,input wire out_ready,output wire[511:0] out_data,
 output wire[73:0] out_tag,output wire[6:0] out_word,output wire out_last,
 output reg context_done,output wire busy,output wire fault
);
 reg active;reg[73:0] ctx;
 reg[6:0] pn,sn;reg pdone,sdone;
 reg[3:0] reserved;reg bad;
 wire p_ir,s_ir,p_ov,s_ov,o_ir;wire[593:0] pq,sq,oq;
 wire pf,sf,of;
 wire safe=ENABLE&&!bad&&!pf&&!sf&&!of;
 assign busy=active;assign fault=bad|pf|sf|of;
 function automatic legal_tag(input[73:0] tag);
  legal_tag=(tag[62:42]<21'd1048576)&&(tag[68:67]<3)&&(tag[73:71]<5);
 endfunction
 wire p_identity=!active||(p_tag==ctx[73:0]);
 wire s_identity=!active||(s_tag==ctx[73:0]);
 wire p_legal=p_identity&&legal_tag(p_tag)&&(p_word==pn)&&(p_last==(pn==79));
 reg s_low_zero;integer k;
 always @*begin s_low_zero=1;for(integer j=0;j<16;j=j+1)if(s_data[32*j+:16]!=0)s_low_zero=0;end
 wire s_legal=s_identity&&legal_tag(s_tag)&&(s_word==sn)&&(s_last==(sn==79))&&s_low_zero;
 assign p_ready=safe&&!pdone&&p_ir&&p_legal;
 assign s_ready=safe&&!sdone&&s_ir&&s_legal&&(!p_valid||active||p_tag==s_tag);
 wire pa=p_valid&&p_ready,sa=s_valid&&s_ready;
 ot_s81_p2_frame_fifo pqueue(.clk(clk),.rst_n(rst_n),.iv(pa),.ir(p_ir),
  .id({p_last,p_word,p_tag,p_data}),.ov(p_ov),.ore(issue),.od(pq),.fault(pf));
 ot_s81_p2_frame_fifo squeue(.clk(clk),.rst_n(rst_n),.iv(sa),.ir(s_ir),
  .id({s_last,s_word,s_tag,s_data}),.ov(s_ov),.ore(issue),.od(sq),.fault(sf));
 wire pair_ok=pq[593:512]==sq[593:512];
 wire issue=safe&&p_ov&&s_ov&&pair_ok&&reserved<8;
 wire[15:0] av;wire[31:0] errors;wire[511:0] sums,rounded;
 genvar g;
 generate for(g=0;g<16;g=g+1)begin:lane
  ot_hdc_fp32_add_lat #(.LAT(3)) add(.clk(clk),.rst_n(rst_n),.valid_in(issue),
   `ifdef P2_MUT_PRE_ROUND
   .a({16'((pq[32*g+:32]+32'h7fff+pq[32*g+16])>>16),16'd0}),
`else
   .a(pq[32*g+:32]),
`endif.b(sq[32*g+:32]),.y(sums[32*g+:32]),.err(errors[2*g+:2]),.valid_out(av[g]));
  wire[31:0] r=sums[32*g+:32]+32'h00007fff+sums[32*g+16];
  assign rounded[32*g+:32]={r[31:16],16'd0};
 end endgenerate
 reg[81:0] pipeline_meta[0:2];reg[2:0] pv;
 wire arithmetic_ok=(av==16'hffff)&&errors==0;
 wire opush=safe&&av[0]&&arithmetic_ok;
 ot_s81_p2_frame_fifo oqueue(.clk(clk),.rst_n(rst_n),.iv(opush),.ir(o_ir),
  .id({pipeline_meta[2][81:0],rounded}),.ov(out_qv),.ore(out_ready&&safe),.od(oq),.fault(of));
 wire out_qv;assign out_valid=out_qv&&safe;
 assign {out_last,out_word,out_tag,out_data}=oq;
 wire pop=out_valid&&out_ready;
 wire[3:0] next_reserved=reserved+issue-pop;
 wire[6:0] next_pn=pa?pn+1'b1:pn,next_sn=sa?sn+1'b1:sn;
 wire next_pd=pa&&p_last?1'b1:pdone,next_sd=sa&&s_last?1'b1:sdone;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   active<=0;ctx<=0;pn<=0;sn<=0;
   pdone<=0;sdone<=0;reserved<=0;bad<=0;context_done<=0;pv<=0;
  end else begin
   context_done<=0;pv<={pv[1:0],issue};
   if(issue)pipeline_meta[0]<=pq[593:512];
   pipeline_meta[1]<=pipeline_meta[0];pipeline_meta[2]<=pipeline_meta[1];
   if(!bad)begin
    if((!ENABLE&&(p_valid||s_valid))||
      (safe&&!pdone&&p_ir&&p_valid&&!p_legal)||
      (safe&&!sdone&&s_ir&&s_valid&&!s_legal)||
      (safe&&!active&&p_valid&&s_valid&&p_tag!=s_tag)||
      (p_ov&&s_ov&&!pair_ok)||(av[0]&&(!arithmetic_ok||!o_ir))||
      (pop&&out_last&&(!pdone||!sdone||reserved!=1)))bad<=1;
    else begin
     reserved<=next_reserved;
     pn<=next_pn;sn<=next_sn;
     pdone<=next_pd;sdone<=next_sd;
     if(!active&&(pa||sa))begin active<=1;
      ctx<=pa?p_tag:s_tag;end
     if(pop&&out_last)begin active<=0;context_done<=1;
      pn<=0;sn<=0;pdone<=0;sdone<=0;end
    end
   end
  end
 end
endmodule

// Both published streams originate in streaming1.2GHz. Each source sees only
// its LOCAL finitecapacity-ready; native serial.9GHz consumer ready never
// crosses as a combinationalwire. Entireactualnative594bitframe moves
// through existingprovenFIFO primitive. Reset is COMMON, assertsbothdomains.
module ot_s81_primary_shared_receive #(parameter integer ENABLE=0)(
 input wire stream_clk,serial_clk,rst_n,
 input wire p_valid,output wire p_ready,input wire[511:0] p_data,
 input wire[73:0] p_tag,input wire[6:0] p_word,input wire p_last,
 input wire s_valid,output wire s_ready,input wire[511:0] s_data,
 input wire[73:0] s_tag,input wire[6:0] s_word,input wire s_last,
 output wire out_valid,input wire out_ready,output wire[511:0] out_data,
 output wire[73:0] out_tag,output wire[6:0] out_word,output wire out_last,
 output wire context_done,busy,fault
);
 wire sr,er;ot_reset_sync sreset(.clk(stream_clk),.async_rst_n(rst_n),.sync_rst_n(sr));
 ot_reset_sync ereset(.clk(serial_clk),.async_rst_n(rst_n),.sync_rst_n(er));
 wire pc,sc,pf,sf,pv,sv,pr,rr;wire[593:0] pd,sd;
 assign p_ready=ENABLE&&sr&&pc&&!pf;assign s_ready=ENABLE&&sr&&sc&&!sf;
 ot_s81_pulse_cdc #(.W(594),.QD(8)) pcdc(.s_clk(stream_clk),.s_rst_n(sr),
  .i_v(p_valid&&p_ready),.i_d({p_last,p_word,p_tag,p_data}),
  .i_accept(pc),.fault(pf),.d_clk(serial_clk),.d_rst_n(er),.o_v(pv),.o_r(pr),.o_d(pd));
 ot_s81_pulse_cdc #(.W(594),.QD(8)) scdc(.s_clk(stream_clk),.s_rst_n(sr),
  .i_v(s_valid&&s_ready),.i_d({s_last,s_word,s_tag,s_data}),
  .i_accept(sc),.fault(sf),.d_clk(serial_clk),.d_rst_n(er),.o_v(sv),.o_r(rr),.o_d(sd));
 (* async_reg="true" *)reg cf1,cf2;
 wire cp,cs,core_fault,core_valid;
 assign pr=cp&&!cf2;assign rr=cs&&!cf2;
 wire guard=!cf2;
 ot_s81_primary_shared_last #(.ENABLE(ENABLE)) core(.clk(serial_clk),.rst_n(er),
  .p_valid(pv&&guard),.p_ready(cp),.p_data(pd[511:0]),.p_tag(pd[585:512]),.p_word(pd[592:586]),.p_last(pd[593]),
  .s_valid(sv&&guard),.s_ready(cs),.s_data(sd[511:0]),.s_tag(sd[585:512]),.s_word(sd[592:586]),.s_last(sd[593]),
  .out_valid(core_valid),.out_ready(out_ready&&guard),.out_data(out_data),.out_tag(out_tag),
  .out_word(out_word),.out_last(out_last),.context_done(context_done),.busy(busy),.fault(core_fault));
 assign out_valid=core_valid&&guard;assign fault=core_fault|cf2;
 always @(posedge serial_clk or negedge er)begin
  if(!er)begin cf1<=0;cf2<=0;end
  else begin cf1<=pf|sf;cf2<=cf1;end
 end
endmodule
