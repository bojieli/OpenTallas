`timescale 1ns/1ps
// Separate DEFAULT_OFF service candidate. OFF keeps strict original CTRLv1.
// ON uses status21v2 ready153/epoch169:154 and addressed BEGIN23v2 epoch63:48.
// Original HC22v1, rawhc182, tk93, kst10 and genuine boot2 stay exact.
// BEGIN reserves one command credit only at a registered HC-idle boundary.
// DIE0 accepts hc commands against four credits. It delivers locally and
// sends one addressed copy to each of the other seven dies. A credit returns
// only after all copies were emitted. Routing preserves per-source FIFO order.
// Status snapshots send on relevant-state change; active cycle counter changes
// alone do not flood the link. Complete tk including final cycle count is sent.
module qkd_host_ctrl_service_packet #(parameter integer DIE=0,MUT=0,STRAPPED=0,ENABLE_SERVICE=0)(
 input wire ck,rst_n,input wire[2:0]die_id,
 input wire rx_v,input wire[511:0]rx_d,output reg rx_cr,
 output reg tx_v,output reg[511:0]tx_d,input wire tx_cr,
 input wire[92:0] local_tk,input wire[9:0]local_kst,input wire[1:0]local_boot,
 input wire cmd_v,input wire[181:0]cmd_hc,output reg cmd_cr,
 output reg[181:0]hc,
 output reg[743:0]tk8,output reg[79:0]kst8,output reg[15:0]boot8,output reg[7:0]seen,
 output reg fault,
 input wire startup_allowed,input wire local_service_ready,input wire[15:0]local_service_epoch,
 input wire begin_v,input wire[15:0]begin_epoch,
 output reg begin_cr,begin_available,
 output reg service_begin_v,output reg[15:0]service_begin_epoch,
 output reg pending_advertised,output reg[15:0]pending_epoch,
 output reg[7:0]service_ready8,pending_ack8,
 output reg[127:0]service_epoch8,output reg ingest_permission
);
 reg[2:0]did_q,die_capture;reg role_valid,die_sampled;
 wire[2:0]role=STRAPPED?did_q:3'(DIE);
 reg rv,tc,cv;reg[511:0]rd;reg[181:0]cd;reg[92:0]lt;reg[9:0]lk;reg[1:0]lb;
 reg[511:0]q[0:3];reg[1:0]wp,rp;reg[2:0]count;
 reg[181:0]cq[0:3];reg[1:0]cw,cr;reg[2:0]cn;
 reg[7:0]credits;reg[15:0]seq_tx;reg[127:0]seq_rx;reg[7:0]seq_seen;
 reg lready,biv,startup_q;reg[15:0]lepoch,bepoch,epoch,last_epoch;
 reg last_ready,begin_pending,begin_busy,epoch_active;
 reg busy;reg[3:0]dst;reg[181:0]active;
 reg[92:0]last_tk;reg[9:0]last_kst;reg[1:0]last_boot;reg sent_once;
 wire[511:0]h=q[rp];wire[2:0]src=h[18:16];wire[7:0]target=h[31:24];
 wire[15:0]rs=h[47:32];wire hdr=(h[15:8]==1||(ENABLE_SERVICE&&h[15:8]==2))&&h[23:19]==0&&target==(8'd1<<role);
 wire take=count!=0&&!fault;
 wire sequence_ok=(!seq_seen[src]&&rs==0)||(seq_seen[src]&&rs==seq_rx[src*16+:16]+16'd1);
 wire stale_service=ENABLE_SERVICE&&h[7:0]==8'h21&&h[15:8]==2&&role==0&&src!=0&&h[511:170]==0&&(h[169:154]!=epoch||(!epoch_active&&!startup_q));
 wire send=!fault&&credits!=0&&!tx_v;
 wire load_begin=ENABLE_SERVICE&&role==0&&!busy&&!begin_busy&&cn==0&&!cv&&begin_pending&&!fault;
 wire load_cmd=(role==0)&&!busy&&!begin_busy&&!load_begin&&cn!=0&&!fault;
 wire status_changed=!sent_once||lt[92:32]!=last_tk[92:32]||lb!=last_boot||lk!=last_kst||(ENABLE_SERVICE&&(lready!=last_ready||lepoch!=last_epoch));
 always @(posedge ck)begin
  rd<=rx_d;cd<=cmd_hc;
  if(rv&&count<4)q[wp]<=rd;
  if(cv&&cn<4)cq[cw]<=cd;
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin
   role_valid<=0;die_sampled<=0;die_capture<=0;did_q<=3'(DIE);rv<=0;tc<=0;cv<=0;lt<=0;lk<=0;lb<=0;wp<=0;rp<=0;count<=0;cw<=0;cr<=0;cn<=0;
   credits<=4;seq_tx<=0;seq_rx<=0;seq_seen<=0;busy<=0;dst<=1;active<=0;
   last_tk<=0;last_kst<=0;last_boot<=0;sent_once<=0;rx_cr<=0;cmd_cr<=0;tx_v<=0;tx_d<=0;
   lready<=0;startup_q<=0;lepoch<=0;biv<=0;bepoch<=0;epoch<=0;last_epoch<=0;last_ready<=0;
   begin_pending<=0;begin_busy<=0;epoch_active<=0;begin_cr<=0;begin_available<=ENABLE_SERVICE;
   service_begin_v<=0;service_begin_epoch<=0;pending_advertised<=0;pending_epoch<=0;
   service_ready8<=0;pending_ack8<=0;service_epoch8<=0;ingest_permission<=0;
   hc<=0;tk8<=0;kst8<=0;boot8<=0;seen<=0;fault<=0;
  end else begin
   startup_q<=startup_allowed;lready<=local_service_ready;lepoch<=local_service_epoch;biv<=begin_v;bepoch<=begin_epoch;
   begin_cr<=0;service_begin_v<=0;pending_advertised<=0;
   if(MUT==6&&role==0&&pending_ack8[7])service_ready8[7]<=1;
   begin_available<=ENABLE_SERVICE&&role==0&&!busy&&cn==0&&!cv&&!begin_pending&&!begin_busy&&(!epoch_active||(&service_ready8));
   ingest_permission<=ENABLE_SERVICE&&epoch_active&&(&pending_ack8)&&!fault;
   if(ENABLE_SERVICE&&lepoch==epoch)begin
    service_epoch8[role*16+:16]<=lepoch;
    if(!lready)begin
     service_ready8[role]<=0;
     if(epoch_active&&role==0&&!pending_ack8[0])begin pending_ack8[0]<=1;pending_advertised<=1;pending_epoch<=epoch;end
    end else if((!epoch_active&&startup_q)||pending_ack8[role])service_ready8[role]<=1;
   end
   if(biv&&ENABLE_SERVICE)begin
    if(role!=0||!begin_available||busy||cn!=0||cv||begin_pending||begin_busy||(epoch_active&&!(&service_ready8))||bepoch<=epoch)fault<=1;
    else begin begin_pending<=1;epoch<=bepoch;epoch_active<=1;
     service_ready8<=0;pending_ack8<=0;service_epoch8<=0;ingest_permission<=0;
     service_begin_v<=1;service_begin_epoch<=bepoch;
    end
   end
   if(load_begin)begin begin_pending<=0;begin_busy<=1;dst<=1;end
   die_capture<=die_id;die_sampled<=1;if(!role_valid&&die_sampled)begin did_q<=die_capture;role_valid<=1;end
   if(role_valid&&STRAPPED&&die_capture!=did_q)fault<=1;rv<=rx_v;tc<=tx_cr;cv<=cmd_v;lt<=local_tk;lk<=local_kst;lb<=local_boot;rx_cr<=take;cmd_cr<=0;tx_v<=0;
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
    if(!hdr)fault<=1;
    else if(stale_service&&MUT!=3)begin
     // An in-order old warm snapshot still advances the unchanged source
     // sequence. A reset-era stale replay with an unrelated sequence is
     // ignored, never used to update TK/KST/BOOT/service readiness.
     if(sequence_ok&&(epoch_active||h[169:154]==epoch))begin seq_seen[src]<=1;seq_rx[src*16+:16]<=rs;end
    end else if(MUT!=5&&!sequence_ok)fault<=1;
    else if(h[7:0]==8'h21&&role==0&&src!=0&&
      ((!ENABLE_SERVICE&&h[15:8]==1&&h[511:153]==0)||(ENABLE_SERVICE&&h[15:8]==2&&h[511:170]==0)))begin
     if(!ENABLE_SERVICE||MUT==3||h[169:154]==epoch)begin
     tk8[src*93+:93]<=(MUT==1&&src==7)?h[140:48]^(93'd1<<64):h[140:48];
     kst8[src*10+:10]<=h[150:141];boot8[src*2+:2]<=h[152:151];seen[src]<=1;
     if(ENABLE_SERVICE)begin
      service_epoch8[src*16+:16]<=h[169:154];
      if((MUT==3||h[169:154]==epoch))begin
       if(!h[153])begin if(epoch_active)pending_ack8[src]<=1;service_ready8[src]<=0;end
       else if((!epoch_active&&startup_q)||pending_ack8[src])service_ready8[src]<=1;
      end
     end
     end seq_seen[src]<=1;seq_rx[src*16+:16]<=rs;
    end else if(ENABLE_SERVICE&&h[7:0]==8'h23&&h[15:8]==2&&role!=0&&src==0&&h[511:64]==0)begin
     if(h[63:48]<=epoch)fault<=1;
     else begin epoch<=h[63:48];epoch_active<=1;service_ready8<=0;pending_ack8<=0;service_epoch8<=0;
      service_begin_v<=1;service_begin_epoch<=h[63:48];
      seq_seen[src]<=1;seq_rx[src*16+:16]<=rs;
     end
    end else if(h[7:0]==8'h22&&h[15:8]==1&&role!=0&&src==0&&h[511:230]==0)begin
     hc<=h[229:48];seq_seen[src]<=1;seq_rx[src*16+:16]<=rs;
    end else fault<=1;
   end
   if(send)begin
    if(role==0&&begin_busy)begin
     tx_v<=1;tx_d<=512'h0223|((512'd1<<dst)<<24)|(512'(seq_tx)<<32)|(512'(epoch)<<48);
     credits<=credits+8'(tc)-1'b1;
     if(dst==7)begin begin_busy<=0;begin_cr<=1;seq_tx<=seq_tx+1'b1;end else dst<=dst+1'b1;
    end else if(role==0&&busy)begin
     tx_v<=1;tx_d<=512'h0122|((512'd1<<dst)<<24)|(512'(seq_tx)<<32)|(512'(active)<<48);
     credits<=credits+8'(tc)-1'b1;
     // Each recipient sees consecutive command sequence numbers, not the
     // sequence of all seven copies. Increment once per broadcast.
     if(dst==7)begin busy<=0;cmd_cr<=1;seq_tx<=seq_tx+1'b1;end else dst<=dst+1'b1;
    end else if(role!=0&&status_changed)begin
     tx_v<=1;tx_d<=(ENABLE_SERVICE?512'h01000221:512'h01000121)|(512'(role)<<16)|(512'(seq_tx)<<32)|(512'(lt)<<48)|(512'(lk)<<141)|(512'(lb)<<151)|(ENABLE_SERVICE?((512'(lready)<<153)|(512'(lepoch)<<154)):512'b0);
     credits<=credits+8'(tc)-1'b1;seq_tx<=seq_tx+1'b1;last_tk<=lt;last_kst<=lk;last_boot<=lb;sent_once<=1;last_ready<=lready;last_epoch<=lepoch;
     if(ENABLE_SERVICE&&epoch_active&&lepoch==epoch&&!lready)begin
      pending_advertised<=1;pending_epoch<=epoch;pending_ack8[role]<=1;
     end
    end
   end
  end
 end
endmodule
