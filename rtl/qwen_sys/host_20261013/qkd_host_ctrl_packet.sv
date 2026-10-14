`timescale 1ns/1ps
// CTRL v1 endpoint for original RAW hc182 and tk93, ND8 package only.
// DIE0 accepts hc commands against four credits. It delivers locally and
// sends one addressed copy to each of the other seven dies. A credit returns
// only after all copies were emitted. Routing preserves per-source FIFO order.
// Status snapshots send on relevant-state change; active cycle counter changes
// alone do not flood the link. Complete tk including final cycle count is sent.
module qkd_host_ctrl_packet #(parameter integer DIE=0,MUT=0,STRAPPED=0)(
 input wire ck,rst_n,input wire[2:0]die_id,
 input wire rx_v,input wire[511:0]rx_d,output reg rx_cr,
 output reg tx_v,output reg[511:0]tx_d,input wire tx_cr,
 input wire[92:0] local_tk,input wire[9:0]local_kst,input wire[1:0]local_boot,
 input wire cmd_v,input wire[181:0]cmd_hc,output reg cmd_cr,
 output reg[181:0]hc,
 output reg[743:0]tk8,output reg[79:0]kst8,output reg[15:0]boot8,output reg[7:0]seen,
 output reg fault
);
 reg[2:0]did_q;reg role_valid;
 wire[2:0]role=STRAPPED?did_q:3'(DIE);
 reg rv,tc,cv;reg[511:0]rd;reg[181:0]cd;reg[92:0]lt;reg[9:0]lk;reg[1:0]lb;
 reg[511:0]q[0:3];reg[1:0]wp,rp;reg[2:0]count;
 reg[181:0]cq[0:3];reg[1:0]cw,cr;reg[2:0]cn;
 reg[7:0]credits;reg[15:0]seq_tx;reg[127:0]seq_rx;reg[7:0]seq_seen;
 reg busy;reg[3:0]dst;reg[181:0]active;
 reg[92:0]last_tk;reg[9:0]last_kst;reg[1:0]last_boot;reg sent_once;
 wire[511:0]h=q[rp];wire[2:0]src=h[18:16];wire[7:0]target=h[31:24];
 wire[15:0]rs=h[47:32];wire hdr=h[15:8]==1&&h[23:19]==0&&target==(8'd1<<role);
 wire take=count!=0&&!fault;
 wire send=!fault&&credits!=0&&!tx_v;
 wire load_cmd=(role==0)&&!busy&&cn!=0&&!fault;
 wire status_changed=!sent_once||lt[92:32]!=last_tk[92:32]||lb!=last_boot||lk!=last_kst;
 always @(posedge ck)begin
  rd<=rx_d;cd<=cmd_hc;
  if(rv&&count<4)q[wp]<=rd;
  if(cv&&cn<4)cq[cw]<=cd;
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin
   role_valid<=0;did_q<=3'(DIE);rv<=0;tc<=0;cv<=0;lt<=0;lk<=0;lb<=0;wp<=0;rp<=0;count<=0;cw<=0;cr<=0;cn<=0;
   credits<=4;seq_tx<=0;seq_rx<=0;seq_seen<=0;busy<=0;dst<=1;active<=0;
   last_tk<=0;last_kst<=0;last_boot<=0;sent_once<=0;rx_cr<=0;cmd_cr<=0;tx_v<=0;tx_d<=0;
   hc<=0;tk8<=0;kst8<=0;boot8<=0;seen<=0;fault<=0;
  end else begin
   role_valid<=1;if(role_valid&&STRAPPED&&die_id!=did_q)fault<=1;did_q<=die_id;rv<=rx_v;tc<=tx_cr;cv<=cmd_v;lt<=local_tk;lk<=local_kst;lb<=local_boot;rx_cr<=take;cmd_cr<=0;tx_v<=0;
   // Pulse fields must be cleared each edge; token/generation/write data persist.
   hc[38]<=0;hc[113]<=0;hc[181]<=0;
   tk8[role*93+:93]<=lt;kst8[role*10+:10]<=lk;boot8[role*2+:2]<=lb;seen[role]<=1;
   if(tc)begin if(credits==4)fault<=1;else credits<=credits+1'b1;end
   if(rv&&!fault)begin if(count==4)fault<=1;else wp<=wp+1'b1;end
   if(take)rp<=rp+1'b1;
   case({rv&&!fault&&count<4,take})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;endcase
   if(cv&&!fault)begin if(role!=0||cn==4)fault<=1;else cw<=cw+1'b1;end
   if(load_cmd)begin
    active<=cq[cr];hc<=cq[cr];busy<=1;dst<=1;cr<=cr+1'b1;
   end
   case({cv&&!fault&&role==0&&cn<4,load_cmd})2'b10:cn<=cn+1'b1;2'b01:cn<=cn-1'b1;default:;endcase
   if(take)begin
    if(!hdr||(!seq_seen[src]&&rs!=0)||(seq_seen[src]&&rs!=seq_rx[src*16+:16]+16'd1))fault<=1;
    else if(h[7:0]==8'h21&&role==0&&src!=0&&h[511:153]==0)begin
     tk8[src*93+:93]<=(MUT==1&&src==7)?h[140:48]^(93'd1<<64):h[140:48];
     kst8[src*10+:10]<=h[150:141];boot8[src*2+:2]<=h[152:151];seen[src]<=1;seq_seen[src]<=1;seq_rx[src*16+:16]<=rs;
    end else if(h[7:0]==8'h22&&role!=0&&src==0&&h[511:230]==0)begin
     hc<=h[229:48];seq_seen[src]<=1;seq_rx[src*16+:16]<=rs;
    end else fault<=1;
   end
   if(send)begin
    if(role==0&&busy)begin
     tx_v<=1;tx_d<=512'h0122|((512'd1<<dst)<<24)|(512'(seq_tx)<<32)|(512'(active)<<48);
     credits<=credits+8'(tc)-1'b1;
     // Each recipient sees consecutive command sequence numbers, not the
     // sequence of all seven copies. Increment once per broadcast.
     if(dst==7)begin busy<=0;cmd_cr<=1;seq_tx<=seq_tx+1'b1;end else dst<=dst+1'b1;
    end else if(role!=0&&status_changed)begin
     tx_v<=1;tx_d<=512'h01000121|(512'(role)<<16)|(512'(seq_tx)<<32)|(512'(lt)<<48)|(512'(lk)<<141)|(512'(lb)<<151);
     credits<=credits+8'(tc)-1'b1;seq_tx<=seq_tx+1'b1;last_tk<=lt;last_kst<=lk;last_boot<=lb;sent_once<=1;
    end
   end
  end
 end
endmodule
