`timescale 1ns/1fs
module tb;
reg ck=0;always #0.4165 ck=~ck;
reg rst_n=0;reg[98:0]ctx=0;reg tv=0,ts=0;reg[511:0]td=0;reg[17:0]tt=0;reg[5:0]ti=0;reg[15:0]te=0;reg slot=0;
reg [551:0] hr;
reg [72:0] ctl=0;
reg [298:0] up0=0,up1=0,up2=0,up3=0;
wire pv,pf,ps,pa,mf; wire [547:0] pd,md;wire [17:0]pt;wire[15:0]pe;wire[60:0]po;
wire [173:0]svc,mut_svc;
always @* begin hr=0;hr[3]=ctx[98];hr[551:516]=ctx[96:61];hr[64:4]=ctx[60:0];end
`define PINS .ck(ck),.rst_n(rst_n),.i_head_record(hr),.d2d__svc(174'd0),.d2d__emb_tx_slot(slot),.i_ctl(ctl),.i_hroot_WS(up0),.i_hroot_WN(up1),.i_hroot_ES(up2),.i_hroot_EN(up3)
qkd_kvs_emb_rope p(`PINS,.rowtx__emb_tx_v(pv),.rowtx__emb_tx_payload(pd),.px_tok(pt),.px_tep(pe),.o_ctx_svc(svc),.emb_fault(pf));
qkd_kvs_emb_rope_joinmut mut(`PINS,.rowtx__emb_tx_v(),.rowtx__emb_tx_payload(md),.px_tok(),.px_tep(),.o_ctx_svc(mut_svc),.emb_fault(mf));
assign ps=svc[24],pa=p.u_context.st,po=p.u_context.accepted_owner;
integer rawbeats=0;reg join_check=0;
always@(posedge ck)if(rst_n&&join_check)begin
 if((up0[0]|up1[0]|up2[0]|up3[0])!==p.u_context.u_join.slot)$fatal(1,"STATIC_JOIN_SLOT_MISMATCH cycle%0d",cy);
 if(up0[0]|up1[0]|up2[0]|up3[0])rawbeats=rawbeats+1;
end
integer ci=-1,rx=0,total=0,checks=0,cy=0,first_baseline_fault=-1;reg[17:0]tok=0;reg[12:0]pos=0;reg[15:0]epoch=0;
reg core=0,cre=0,sre=0;reg[23:0]ca=0;reg[17:0]sa=0;wire[511:0]cq;wire[15:0]sq;wire qf;
wire hdr=rx==0;wire wrscale=hdr||pd[512];
wire[5:0]wi=hdr?6'd0:(pd[512]?pd[529:524]+6'd1:pd[529:524]);
qfd_embedding_word_provider #(.ROPE(1),.ROPE_FF(1)) qc(.ck(ck),.rst_n(rst_n),.word_v(pv),.word_data(pd[511:0]),.word_token(pd[547:530]),.word_index(wi),.word_scale(wrscale),.word_epoch(epoch),.expected_word_slot(pv),.expected_token(tok),.expected_word(hdr?6'd0:(rx>=65?6'(rx-64):6'(rx-1))),.expected_scale(hdr||rx>=65),.expected_epoch(epoch),.fill_begin(pa),.fill_token(tok),.fill_epoch(epoch),.core_start(core),.core_token(tok),.core_epoch(epoch),.embed_code_re(cre),.embed_code_addr(ca),.embed_code_q(cq),.embed_scale_re(sre),.embed_scale_addr(sa),.embed_scale_q(sq),.fault(qf));
reg[511:0]sweep[0:255],gold[0:31];reg[511:0]seen[0:31];
function automatic[511:0]embword(input[17:0]t,input integer w);
 reg[511:0]v;begin for(integer l=0;l<16;l=l+1)v[32*l+:32]=32'h40000000|(32'(t)<<10)|32'(16*w+l);embword=v;end
endfunction
always@(posedge ck)begin
 cy<=cy+1;
 if(rst_n&&ci>=0&&pv)begin
  if(pd[547:530]!==tok)$fatal(1,"TX_TOKEN");
  if(rx==0)begin if(pd[47:32]!==epoch||pd[15:0]!==16'h3f80)$fatal(1,"TX_HEADER");end
  else if(rx<=64)begin if(pd[529:524]!==6'(rx-1)||pd[511:0]!==embword(tok,rx-1))$fatal(1,"TX_EMBED_DATA rx%0d",rx);end
  else begin seen[ci*8+rx-65]=pd[511:0];checks=checks+1;if(!pd[512]||pd[529:524]!==6'(rx-65)||pd[511:0]!==gold[ci*8+rx-65])$fatal(1,"TX_ROPE_DATA case%0d rx%0d",ci,rx);end
  rx<=rx+1;total<=total+1;
 end
end

integer input_cy[0:3],accepted_cy[0:3],first_packet_cy[0:3],first_rope_cy[0:3],last_packet_cy[0:3],ready_cy[0:3],drained_cy[0:3];
initial for(integer c=0;c<4;c=c+1)begin input_cy[c]=-1;accepted_cy[c]=-1;first_packet_cy[c]=-1;first_rope_cy[c]=-1;last_packet_cy[c]=-1;ready_cy[c]=-1;drained_cy[c]=-1;end
always@(posedge ck)if(rst_n&&ci>=0)begin
 if(ctx[98]&&input_cy[ci]<0)input_cy[ci]=cy;
 if(pa&&accepted_cy[ci]<0)accepted_cy[ci]=cy;
 if(pv&&rx==0)first_packet_cy[ci]=cy;
 if(pv&&rx==65)first_rope_cy[ci]=cy;
 if(pv&&rx==72)last_packet_cy[ci]=cy;
 if(p.u_context.g_rope.u_rowtx.row_ready&&ready_cy[ci]<0)ready_cy[ci]=cy;
 if(!p.u_context.g_rope.u_rowtx.row_open&&last_packet_cy[ci]>=0&&drained_cy[ci]<0)drained_cy[ci]=cy;
end
task step;@(negedge ck);endtask

task clear_up;begin up0=0;up1=0;up2=0;up3=0;end endtask
task send_half(input[17:0] t,input[15:0] e,input integer wordno,input bit half,
 input[255:0] data,input bit scale,input integer sequence_id);
 reg [298:0] rec;
 begin
  clear_up();rec={e,scale,half,6'(wordno),t,data,1'b1};
  case(sequence_id%4)0:up0=rec;1:up1=rec;2:up2=rec;3:up3=rec;endcase
  step();
 end
endtask

reg [511:0] ew;integer waits,k,b;reg[60:0]owner;reg[35:0]header;
initial begin
 $readmemh("rope_sweep.hex",sweep);$readmemh("rope_expected.hex",gold);
 repeat(32)step();rst_n=1;repeat(96)step();
 // Actual eight-entry native join calendar: 128 code half-beats plus one scale.
 // The RoPE sweep masks out segment1, retaining 128 code half-beats only.
 for(integer seg=0;seg<8;seg=seg+1)begin
  ctl={1'b1,(64'd1<<62)|(64'(seg==0?128:(seg==1?1:0))<<16)|64'(seg==0?32:(seg==1?160:0)),8'(seg)};step();
 end
 ctl=0;repeat(16)step();join_check=1;
 for(integer c=0;c<4;c=c+1)begin
  ci=c;rx=0;tok=c<2?18'd17:18'd29;pos=c==0?13'd0:(c==3?13'd8:13'd1);epoch=16'h1000+16'(4*c);
  owner={2'd0,epoch,6'd0,tok,pos,6'd0};header={5'd0,4'd12,6'd63,epoch,5'd0};ctx={1'b1,1'b1,header,owner};step();ctx=0;
  waits=0;while(!pa&&waits<32)begin step();waits=waits+1;end
  if(!pa||po!==owner)$fatal(1,"CTX_NOT_ACCEPTED");
  // Fixed dates from the accepted native start: cal slot at +35,
  // raw pin capture at +36 (off32 + native start/register pipeline).
  repeat(35)step();
  for(k=0;k<64;k=k+1)begin
   ew=embword(tok,k);send_half(tok,epoch,k,0,ew[255:0],0,2*k);
   send_half(tok,epoch,k,1,ew[511:256],0,2*k+1);
  end
  send_half(tok,epoch,0,0,{16{16'h3f80}},1,128);
  clear_up();
  waits=0;while(!ps&&waits<1100)begin step();waits=waits+1;end
  if(!ps||pt!==18'(151936+(pos>>3))||pe!==epoch)$fatal(1,"POSITION_ROW_REQUEST got%0d want%0d",pt,151936+(pos>>3));
  repeat(35)step();
  for(k=0;k<64;k=k+1)begin
   send_half(18'(151936+(pos>>3)),epoch,k,0,sweep[64*c+k][255:0],0,2*k);
   send_half(18'(151936+(pos>>3)),epoch,k,1,sweep[64*c+k][511:256],0,2*k+1);
  end
  clear_up();repeat(3)step();
  if(!p.u_context.g_rope.u_rowtx.row_ready||pf)$fatal(1,"PRODUCER_NOT_READY fault%b",pf);
  slot=1;repeat(73)step();slot=0;
  waits=0;while(rx!=73&&waits<8)begin step();waits=waits+1;end
  if(rx!=73||pf||qf)$fatal(1,"ROW_TRANSPORT case%0d count%0d pf%b qf%b",c,rx,pf,qf);
  // Throughput recurrence: validate CORE start; prior capsule separately proves SRAM readback.
  core=1;step();core=0;
  if(qf||pf)$fatal(1,"POSITIVE_FAULT");
  $display("REQUEST_PASS token%0d position%0d epoch%0d packets%0d ropewords8",tok,pos,epoch,rx);
  ci=-1;
 end
 if(seen[0]===seen[8])$fatal(1,"SAME_TOKEN_DIFFERENT_POS_NOT_DISTINGUISHED");
 for(b=0;b<8;b=b+1)if(seen[8+b]!==seen[16+b])$fatal(1,"SAME_POS_DIFFERENT_TOKEN_CHANGED_ROPE");
 for(integer c=0;c<4;c=c+1)$display("COMPONENT_DATES case%0d input%0d accepted%0d ready%0d first_packet%0d first_rope%0d last_packet%0d drained%0d input_to_accepted%0d accepted_to_first%0d accepted_to_rope%0d accepted_to_last%0d observed_accepted_spacing%0d",c,input_cy[c],accepted_cy[c],ready_cy[c],first_packet_cy[c],first_rope_cy[c],last_packet_cy[c],drained_cy[c],accepted_cy[c]-input_cy[c],first_packet_cy[c]-accepted_cy[c],first_rope_cy[c]-accepted_cy[c],last_packet_cy[c]-accepted_cy[c],c==0?0:accepted_cy[c]-accepted_cy[c-1]);
 if(!mf)$fatal(1,"JOIN_CALENDAR_MUTANT_NOT_CAUGHT");
 $display("JOIN_CALENDAR_SCALE_SLOT_MUTANT_CAUGHT fault%b",mf);
 $display("FULL_PRODUCTION_RECURRENCE_PASS requests4 packets%0d goldwords%0d same-token-diff-pos same-pos-diff-token",total,checks);$finish;
end
endmodule
