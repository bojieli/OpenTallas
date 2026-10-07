`timescale 1ns/1ps
// Native controller-domain write ownership. No CDC or physical CA encoder.
// Cold rst_n requires no physical transactions; epoch_advance is NOT cold reset.
// upstream_quiescent is the external failed-epoch fence: all bridge frames
// and completion FIFOs drained, old sequences rejected, and canceled service
// ownership isolated for atomic epoch invalidation without synthetic wd.
// epoch_ready grants local readiness, not global fence completion. Before epoch_advance,
// the external owner must establish all banks closed and initialize the reset
// controller timing epoch. A bare cancel_count is never retirement authority.
// External protected refresh owner continuously observes phy_row/col, preserving
// JEDEC bank timing and absolute refresh epoch even when this ledger quarantines.
module ot_qwen_ctrl_write_ledger #(parameter integer ENABLE=0, PC=0)(
 input wire clk,rst_n,
 input wire w_v, input wire [23:0] w_sec,
 input wire [255:0] w_data, input wire [8:0] w_tag, output wire w_room,
 output wire sched_v, output wire [4:0] sched_bank,sched_col,
 input wire sched_take,
 input wire row_v, input wire [2:0] row_op,
 input wire [4:0] row_bank, input wire [18:0] row_row,
 input wire col_v,col_we, input wire [4:0] col_bank,col_col,
 output wire phy_row_v, output wire [2:0] phy_row_op,
 output wire [4:0] phy_row_bank, output wire [18:0] phy_row_row,
 output wire phy_col_v,phy_col_we, output wire [4:0] phy_col_bank,phy_col_col,
 output wire [23:0] phy_w_sec, output wire [255:0] phy_w_data,
 output wire [8:0] phy_w_tag,
 input wire done_v, input wire [8:0] done_tag,
 output wire wd_v, output wire [8:0] wd_tag,
 input wire ctrl_fault, output wire stop,quarantine,
 output wire refresh_req, input wire refresh_ack,
 input wire upstream_quiescent,epoch_advance, output wire epoch_ready,
 output wire [4:0] cancel_count, output wire [6:0] committed_count
);
 localparam integer STATE_BITS=7419;
 wire [STATE_BITS-1:0] state[0:1];
 wire [288:0] hand[0:1],head[0:1];
 wire [32:0] completed[0:1];
 wire [4:0] occupied[0:1],handed[0:1];
 wire [6:0] committed[0:1];
 wire aborted[0:1],acknowledged[0:1],bank_open[0:1];
 wire [18:0] bank_row[0:1];
 wire push,hand_fire,commit_fire,done_fire,abort_event,ack_event,advance,row_fire;
 for(genvar g=0;g<2;g=g+1) begin:g_copy
  (* keep=1,dont_touch=1,keep_hierarchy=1 *)
  ot_qwen_ctrl_write_ledger_state u(
   .clk(clk),.rst_n(rst_n),.push(push),.hand_fire(hand_fire),
   .commit_fire(commit_fire),.done_fire(done_fire),.abort_event(abort_event),
   .ack_event(ack_event),.advance(advance),.row_fire(row_fire),
   .w_sec(w_sec),.w_data(w_data),.w_tag(w_tag),
   .row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_bank(col_bank),
   .state(state[g]),.hand(hand[g]),.head(head[g]),.completed(completed[g]),
   .occupied(occupied[g]),.handed(handed[g]),.committed(committed[g]),
   .aborted(aborted[g]),.acknowledged(acknowledged[g]),
   .bank_open(bank_open[g]),.bank_row(bank_row[g]));
 end
 wire agree=(state[0]==state[1]);
 (* keep=1,dont_touch=1 *) reg trip_seen;
 (* keep=1,dont_touch=1 *) reg permit_state;
 wire en=(ENABLE!=0)&&rst_n;
 wire stopped=ctrl_fault||aborted[0];
 wire [14:0] ws={w_sec[12:6],w_sec[16],w_sec[15],w_sec[5:0]};
 wire input_bad=w_v && (occupied[0]>=16 || ws[6:2]!=5'(PC) ||
                         w_sec[14:13]!=0 || !w_tag[8]);
 // Explicit native sector extraction avoids any tag-width or hub-tag cast.
 wire [23:0] hand_sec=hand[0][288:265];
 wire [14:0] hand_s={hand_sec[12:6],hand_sec[16],hand_sec[15],hand_sec[5:0]};
 wire [14:0] physical_s={col_bank[4:2],col_col,5'(PC),col_bank[1:0]};
 wire [16:0] physical_l={physical_s[7],physical_s[6],2'b00,physical_s[14:8],physical_s[5:0]};
 wire [23:0] physical_sec={bank_row[0][6:0],physical_l};
 wire write_bad=!stopped && col_v && col_we &&
   (handed[0]==0 || !bank_open[0] || bank_row[0][18:7]!=0 ||
    head[0][288:265]!=physical_sec || committed[0]>=64);
 wire done_bad=done_v && (committed[0]==0 || completed[0][8:0]!=done_tag);
 wire row_bad=!stopped && row_v &&
   ((row_op!=0 && row_op!=1 && row_op!=6) ||
    ((row_op==1 || row_op==6) && state[0][6779+20*row_bank+19]) ||
    (row_op==0 && !state[0][6779+20*row_bank+19]));
 wire hand_bad=!stopped && sched_take && !(occupied[0]>handed[0] &&
                     ({1'b0,committed[0]}+{3'b0,handed[0]}<8'd64));
 wire raw_quarantine=!agree || input_bad || write_bad || done_bad || row_bad || hand_bad;
 wire blocked=trip_seen || !permit_state || raw_quarantine;
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin trip_seen<=0;permit_state<=1;end
  else if(en && blocked) begin trip_seen<=1;permit_state<=0;end
 // Notifications use sticky sampled state; raw comparison only gates the
 // synchronous accepting edge, avoiding delta settling pulses at CDC inputs.
 assign quarantine=en && (trip_seen || !permit_state);
 assign stop=en && (stopped || trip_seen || !permit_state);
 // Three free slots reserve the old registered advertisement plus two late
 // native emissions. A bridge with a longer loop must terminate it in a FIFO.
 assign w_room=en && !stopped && !blocked && occupied[0]<=13;
 assign sched_v=en && !stopped && !blocked && occupied[0]>handed[0] &&
                ({1'b0,committed[0]}+{3'b0,handed[0]}<8'd64);
 assign sched_bank=sched_v?{hand_s[14:12],hand_s[1:0]}:5'b0;
 assign sched_col=sched_v?hand_s[11:7]:5'b0;
 assign hand_fire=sched_v && sched_take;
 assign phy_row_v=en && !stopped && !blocked && row_v;
 assign phy_row_op=phy_row_v?row_op:3'b0;
 assign phy_row_bank=phy_row_v?row_bank:5'b0;
 assign phy_row_row=phy_row_v?row_row:19'b0;
 assign phy_col_v=en && !stopped && !blocked && col_v;
 assign phy_col_we=phy_col_v && col_we;
 assign phy_col_bank=phy_col_v?col_bank:5'b0;
 assign phy_col_col=phy_col_v?col_col:5'b0;
 assign phy_w_sec=phy_col_we?head[0][288:265]:24'b0;
 assign phy_w_data=phy_col_we?head[0][264:9]:256'b0;
 assign phy_w_tag=phy_col_we?head[0][8:0]:9'b0;
 assign row_fire=phy_row_v;
 assign commit_fire=phy_col_we;
 // Actual PHY acceptance above transfers payload custody. Real completion is
 // mandatory; no latency counter, abort acknowledgment or refresh ACK emits wd.
 assign wd_v=en && !blocked && done_v;
 assign wd_tag=wd_v?completed[0][8:0]:9'b0;
 assign done_fire=wd_v;
 assign push=en && !blocked && w_v;
 assign abort_event=en && ctrl_fault;
 assign ack_event=en && !blocked && (stopped) && refresh_ack;
 assign refresh_req=en && (stopped || trip_seen || !permit_state);
 assign epoch_ready=en && !blocked && aborted[0] && acknowledged[0] &&
                    committed[0]==0 && upstream_quiescent && !w_v && !done_v && !ctrl_fault;
 assign advance=epoch_ready && epoch_advance;
 assign cancel_count=en && stopped && !blocked?occupied[0]:5'b0;
 assign committed_count=en && !blocked?committed[0]:7'b0;
endmodule

// Storage updates are deliberately duplicated, not a shared memory with two
// views. Mapped independent state roots are a separate adoption requirement.
module ot_qwen_ctrl_write_ledger_state(
 input wire clk,rst_n,push,hand_fire,commit_fire,done_fire,abort_event,ack_event,advance,row_fire,
 input wire [23:0] w_sec,input wire [255:0] w_data,input wire [8:0] w_tag,
 input wire [2:0] row_op,input wire [4:0] row_bank,col_bank,input wire [18:0] row_row,
 output wire [7418:0] state,output wire [288:0] hand,head,
 output wire [32:0] completed,output reg [4:0] occupied,handed,
 output reg [6:0] committed,output reg aborted,acknowledged,
 output wire bank_open,output wire [18:0] bank_row
);
 reg [288:0] ingress[0:15];
 reg [32:0] completion[0:63];
 reg [18:0] rows[0:31];reg [31:0] open_bank;
 reg [3:0] wp,hp,cp; reg [5:0] awp,arp;
 assign hand=ingress[hp];assign head=ingress[cp];assign completed=completion[arp];
 assign bank_open=open_bank[col_bank];assign bank_row=rows[col_bank];
 assign state[42:0]={wp,hp,cp,occupied,handed,awp,arp,committed,aborted,acknowledged};
 for(genvar i=0;i<16;i=i+1) begin:pack_i
  assign state[43+289*i+:289]=ingress[i];
 end
 for(genvar i=0;i<64;i=i+1) begin:pack_c
  assign state[4667+33*i+:33]=completion[i];
 end
 for(genvar i=0;i<32;i=i+1) begin:pack_r
  assign state[6779+20*i+:20]={open_bank[i],rows[i]};
 end
 integer j;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   wp<=0;hp<=0;cp<=0;awp<=0;arp<=0;occupied<=0;handed<=0;committed<=0;
   aborted<=0;acknowledged<=0;open_bank<=0;
   for(j=0;j<16;j=j+1) ingress[j]<=0;
   for(j=0;j<64;j=j+1) completion[j]<=0;
   for(j=0;j<32;j=j+1) rows[j]<=0;
  end else if(advance) begin
   wp<=0;hp<=0;cp<=0;awp<=0;arp<=0;occupied<=0;handed<=0;committed<=0;
   aborted<=0;acknowledged<=0;open_bank<=0;
   for(j=0;j<16;j=j+1) ingress[j]<=0;
   for(j=0;j<64;j=j+1) completion[j]<=0;
   for(j=0;j<32;j=j+1) rows[j]<=0;
  end else begin
   if(abort_event) aborted<=1;
   if(ack_event) acknowledged<=1;
   case({push,commit_fire}) 2'b10:occupied<=occupied+1'b1;2'b01:occupied<=occupied-1'b1;default:;endcase
   case({hand_fire,commit_fire}) 2'b10:handed<=handed+1'b1;2'b01:handed<=handed-1'b1;default:;endcase
   case({commit_fire,done_fire}) 2'b10:committed<=committed+1'b1;2'b01:committed<=committed-1'b1;default:;endcase
   if(push) begin ingress[wp]<={w_sec,w_data,w_tag};wp<=wp+1'b1;end
   if(hand_fire) hp<=hp+1'b1;
   if(commit_fire) begin
    completion[awp]<={ingress[cp][288:265],ingress[cp][8:0]};
    awp<=awp+1'b1;cp<=cp+1'b1;
   end
   if(done_fire) arp<=arp+1'b1;
   if(row_fire) begin
    if(row_op==1) begin open_bank[row_bank]<=1;rows[row_bank]<=row_row;end
    else if(row_op==0) open_bank[row_bank]<=0;
   end
  end
 end
endmodule
