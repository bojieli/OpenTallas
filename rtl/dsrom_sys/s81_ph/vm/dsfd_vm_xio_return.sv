`timescale 1ns/1ps
`default_nettype none
module dsfd_vm_xio_return(
 input wire ck,rst_n,input wire[2:0] return_valid,input wire[5:0] return_lane,
 input wire[3:0] e_v,input wire[2047:0] e_d,input wire[10:0] f_xgo,
 output reg[512:0] t_crs,output wire q_v,output wire[511:0] q_d,
 output wire g_v,output wire[510:0] g_d,output reg fault
);
 // rq[2] is a registered copy of rn: the rn qualification of the e_v / return_valid / f_xgo captures is applied after
 // plain pin capture flops (ev_raw / valid_raw / xq_raw), so every input pin feeds its own flop D directly (anchored at
 // the pin by io_flop_at_pins).  rn_d ? raw : 0 after the edge equals the former rn ? pin : 0 captured at that edge:
 // zero cycle change.  (r2: ev_pin<=rn?e_v:0 mapped to AND2 + SDFF, which the pin walk does not cross, so the e_v
 // flops sat 162 um from the W face; e_v[0] capture S+R 220 ps.)
 reg[2:0] rq;
 always @(posedge ck or negedge rst_n)if(!rst_n)rq<=0;else rq<={rq[1:0],1'b1};
`ifdef OT_VM_XIO_MUT_RNQ
 wire rn=rq[1],rn_d=rq[1];
`else
 wire rn=rq[1],rn_d=rq[2];
`endif
 reg[3:0] ev_raw;reg[2047:0] ed_pin;reg[2:0] valid_raw;reg[5:0] lane_pin;
 always @(posedge ck)begin ev_raw<=e_v;ed_pin<=e_d;valid_raw<=return_valid;lane_pin<=return_lane;end
 wire[3:0] ev_pin=rn_d?ev_raw:4'd0;wire[2:0] valid_pin=rn_d?valid_raw:3'd0;
 function automatic[511:0] lane512(input[2047:0] d,input[1:0] l);
  begin lane512=({512{l==0}}&d[0+:512])|({512{l==1}}&d[512+:512])|({512{l==2}}&d[1024+:512])|({512{l==3}}&d[1536+:512]);end
 endfunction
 wire rC=valid_pin[0],rQ=valid_pin[1],rG=valid_pin[2];
 wire[1:0]lC=lane_pin[1:0],lQ=lane_pin[3:2],lG=lane_pin[5:4];
 wire[3:0]expected=(rC?(4'b1<<lC):4'b0)|(rQ?(4'b1<<lQ):4'b0)|(rG?(4'b1<<lG):4'b0);
 wire[511:0]dCw=lane512(ed_pin,lC),dQw=lane512(ed_pin,lQ),dGw=lane512(ed_pin,lG);
 reg[1:0]qv,gv;reg[511:0]qd[0:1];reg[510:0]gd[0:1];
 assign q_v=qv[1];assign q_d=qd[1];assign g_v=gv[1];assign g_d=gd[1];
 reg[10:0]xq_raw;always @(posedge ck)xq_raw<=f_xgo;
 wire[10:0]xq=rn_d?xq_raw:11'd0;
 reg[2:0]gn;reg[9:0]gph[0:3];reg[1:0]gw,gr;integer k;
 always @(posedge ck)begin: p_return
  reg push,pop;
  if(!rn)begin qv<=0;gv<=0;t_crs<=0;fault<=0;gn<=0;gw<=0;gr<=0;end
  else begin
   qv<={qv[0],rQ};gv<={gv[0],rG};
`ifdef OT_VM_XIO_MUT_RETURN
   t_crs<={dQw,rC};
`else
   t_crs<={dCw,rC};
`endif
   if(ev_pin!=expected)fault<=1;
   // Mirror the phase queue at the final real Q/G output edge, not before tail stages.
   push=gv[0]&&gd[0][1:0]==0;pop=xq[10];
   if(push)begin gph[gw]<=gd[0][58:49];gw<=gw+1'b1;end
   if(pop)begin
    if(gn==0&&!push)fault<=1;
    else if(gph[gr]!=xq[9:0])fault<=1;
    gr<=gr+1'b1;
   end
   gn<=gn+(push?3'd1:3'd0)-((pop&&(gn!=0||push))?3'd1:3'd0);
   if(push&&!pop&&gn==4)fault<=1;
  end
  qd[0]<=dQw;
`ifdef OT_VM_XIO_MUT_GATHER
  gd[0]<=dGw[510:0]^511'd4;
`else
  gd[0]<=dGw[510:0];
`endif
  for(k=1;k<2;k=k+1)begin qd[k]<=qd[k-1];gd[k]<=gd[k-1];end
 end
endmodule
`default_nettype wire
