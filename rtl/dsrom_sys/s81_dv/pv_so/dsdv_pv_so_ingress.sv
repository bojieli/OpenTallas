`timescale 1ns/1ps
`default_nettype none
// All-quarter FP32 transpose and SMJ9 serializer. No arithmetic or rescheduling.
// ENABLE=0 removes the candidate. ENABLE=1 requires source-stamped PV_IDENTITY
// headers from actual dsdv_svc_att producers and a statically reserved q window.
module dsdv_pv_so_ingress #(parameter integer ENABLE=0)(
 input wire clk,rst_n,
 input wire cfg_v,input wire[19:0]cfg_owner,input wire[20:0]cfg_position,input wire[7:0]cfg_se_jid,cfg_so_jid,
 input wire pv_v,input wire[1:0]pv_quarter,input wire[512:0]pv_d,
 input wire param_v,input wire[2:0]param_row,input wire[19:0]param_owner,input wire[20:0]param_position,input wire[511:0]param_d,
 input wire den_v,input wire[15:0]den_mask,input wire[19:0]den_owner,input wire[7:0]den_jid,
 input wire launch,
 output wire q_v,output wire[511:0]q_d,output wire ready,done,
 output wire fault,output wire[11:0]fault_code
);
 generate if(ENABLE==0)begin:g_disabled
  assign q_v=0;assign q_d=0;assign ready=0;assign done=0;assign fault=0;assign fault_code=0;
 end else begin:g_enabled
  reg[1:0]rs;always @(posedge clk or negedge rst_n)if(!rst_n)rs<=0;else rs<={rs[0],1'b1};wire rn=rs[1];
  // All data inputs land before decode/storage. Event pins have reset-held valid.
  reg cv,pv,pp,dv,lv;reg[19:0]co,po,do_;reg[20:0]cp,ppos;reg[7:0]cj,sj,dj;reg[1:0]pq;
  reg[512:0]pd;reg[511:0]par;reg[2:0]pr;reg[15:0]dm;
  always @(posedge clk)begin co<=cfg_owner;cp<=cfg_position;ppos<=param_position;cj<=cfg_se_jid;sj<=cfg_so_jid;pq<=pv_quarter;pd<=pv_d;par<=param_d;pr<=param_row;po<=param_owner;do_<=den_owner;dj<=den_jid;dm<=den_mask;end
  always @(posedge clk or negedge rn)if(!rn)begin cv<=0;pv<=0;pp<=0;dv<=0;lv<=0;end else begin cv<=cfg_v;pv<=pv_v;pp<=param_v;dv<=den_v;lv<=launch;end
  reg active,emitting;reg[19:0]owner;reg[20:0]position;reg[7:0]se_jid,so_jid;
  reg[127:0]headers;reg[9:0]ndata;reg[4:0]params;reg[15:0]den;
  reg[2:0]wi[0:3];reg[3:0]tile[0:3];reg[2:0]col[0:3];
  reg[11:0]fc;assign fault_code=fc;assign fault=|fc;
  // Header provenance is checked before payload is admitted to any SRAM bank.
  wire header=pd[512];wire[3:0]ht=pd[97:94];wire[2:0]hc=pd[66:64];
  wire header_ok=pd[98] && pd[91:72]==owner && pd[119:99]==position && pd[93:92]==pq && ht[3:2]==pq && pd[71:67]==0 && !headers[{ht,hc}] && wi[pq]==0;
  wire data_ok=wi[pq]>=1 && wi[pq]<=4;
  wire put=pv && active && !emitting && !fault && !header && data_ok;
  wire[8:0]dim={tile[pq],5'd0}+9'(8*(wi[pq]-1))+{6'd0,col[pq]};
  wire pp_ok=pp && active && !emitting && !fault && po==owner && ppos==position && pr<5 && !params[pr];
  assign ready=active && !emitting && !fault && (&headers) && ndata==512 && (&params) && (&den);
  // Producer launches are never inferred from readiness: compiler must reserve a
  // fixed window, assert launch there, and fault if the all-quarter fence is late.
  reg[1:0]phase;reg[2:0]pi;reg[3:0]head;reg[4:0]row;
  wire[4:0]pra=(phase==1 && pi<4)?{2'd0,pi}+5'd1:5'd0;
  wire[3:0]rhead=(phase==3 && row==31)?head+1'b1:head;
  wire[4:0]rrow=(phase==3 && row!=31)?row+1'b1:5'd0;
  wire[511:0]param_q;wire[8191:0]head_q;
  // Sixteen head stores, each32rows x512b =128 physical single-clock banks.
  // Each incoming dimension writes one32-bit half of one64-bit bank per head.
  for(genvar h=0;h<16;h=h+1)begin:g_head
   for(genvar b=0;b<8;b=b+1)begin:g_bank
    ot_sram_1r1w_32x64_m1 u_m(.clk(clk),.r_ce_in(emitting && rhead==4'(h)),.r_addr_in(rrow),.rd_out(head_q[512*h+64*b+:64]),
     .w_ce_in(put && dim[3:1]==3'(b)),.w_addr_in(dim[8:4]),.wd_in({2{pd[32*h+:32]}}),.w_mask_in(dim[0]?64'hffffffff00000000:64'h00000000ffffffff));
   end
  end
  // Five parameter rows exceed2kb: eight additional32x64 banks, not a flop table.
  for(genvar b=0;b<8;b=b+1)begin:g_param
   ot_sram_1r1w_32x64_m1 u_m(.clk(clk),.r_ce_in(emitting),.r_addr_in(pra),.rd_out(param_q[64*b+:64]),
    .w_ce_in(pp_ok),.w_addr_in({2'd0,pr}),.wd_in(par[64*b+:64]),.w_mask_in(64'hffffffffffffffff));
  end
  reg qv,dn;reg[511:0]qd;assign q_v=qv;assign q_d=qd;assign done=dn;
  function automatic[511:0]hdr(input op,input[3:0]h);
   reg[511:0]x;begin x=0;x[511:508]=9;x[503]=1;x[502:495]=owner[7:0];x[479:459]=position;x[491:480]=op?12'd32:12'd5;
    x[458:449]=owner[17:8];x[0]=!op;x[4:1]=5;x[12:5]=so_jid;x[13]=op;if(op)x[14+:16]=16'd1<<h;hdr=x;end
  endfunction
  always @(posedge clk)begin
   if(emitting)case(phase)
    0:qd<=hdr(0,0);
    1:qd<=param_q;
    2:qd<=hdr(1,head);
    3:qd<=head_q[512*head+:512];
   endcase
  end
  integer k;
  always @(posedge clk or negedge rn)if(!rn)begin
   active<=0;emitting<=0;owner<=0;position<=0;se_jid<=0;so_jid<=0;headers<=0;ndata<=0;params<=0;den<=0;fc<=0;
   phase<=0;pi<=0;head<=0;row<=0;qv<=0;dn<=0;
   for(k=0;k<4;k=k+1)begin wi[k]<=0;tile[k]<=0;col[k]<=0;end
  end else begin
   qv<=emitting;dn<=0;
   if(cv)begin
    if(active || emitting || pv || pp || dv || lv)fc[0]<=1;
    else begin active<=1;owner<=co;position<=cp;se_jid<=cj;so_jid<=sj;headers<=0;ndata<=0;params<=0;den<=0;for(k=0;k<4;k=k+1)wi[k]<=0;end
   end
   if(pv)begin
    if(!active || emitting)fc[1]<=1;
    else if(header)begin
     if(|pd[63:0])fc[8]<=1;
     if(!header_ok)fc[2]<=1;
     else begin headers[{ht,hc}]<=1;tile[pq]<=ht;col[pq]<=hc;wi[pq]<=1;end
    end else if(!data_ok)fc[3]<=1;
    else begin wi[pq]<=wi[pq]==4?3'd0:wi[pq]+1'b1;if(ndata==512)fc[4]<=1;else ndata<=ndata+1'b1;end
   end
   if(pp)begin if(!active || emitting || po!=owner || ppos!=position || pr>=5 || params[pr])fc[5]<=1;else params[pr]<=1;end
   if(dv)begin if(!active || emitting || do_!=owner || dj!=se_jid || |(den&dm))fc[6]<=1;else den<=den|dm;end
   if(lv)begin if(!ready || pv || pp || dv)fc[7]<=1;else begin emitting<=1;phase<=0;pi<=0;head<=0;row<=0;end end
   if(emitting)case(phase)
    0:begin phase<=1;pi<=0;end
    1:if(pi==4)begin phase<=2;head<=0;end else pi<=pi+1'b1;
    2:begin phase<=3;row<=0;end
    3:if(row==31)begin if(head==15)begin emitting<=0;active<=0;dn<=1;end else begin head<=head+1'b1;phase<=2;end end else row<=row+1'b1;
   endcase
  end
 end endgenerate
endmodule
`default_nettype wire
