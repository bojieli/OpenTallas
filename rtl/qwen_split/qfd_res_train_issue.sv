`timescale 1ns/1ps
// Q-VMWB (2026-10-15): the source of the result-train command (train_start / count / stride / payload / slot_count)
// for the three qfd_res_train_par band serializers.  Closes the Q-ATTN r3 open item "train_start/count/stride/payload
// are explicit join inputs: the TT ME-issue calendar must source them".
// Static derivation, no handshake: both inputs are existing TT outputs.
//   * ME instruction fields at its go edge (tt_ib = the TT's rom_cmd: go, tiles, ts, split, oen): pushed in program
//     order into a 4-entry descriptor queue (count = tiles, stride = max(ts, 8), payload = oen, slot_count = the
//     active slot prefix of the port bframe law: 8 for split <= 7, 8 >> (split - 7) for 8..10, 1 above).
//   * the controller's result tag (c-bundle p_v_e2 with p_f_e2.last = the tag that becomes the ports' burst marker
//     o_ov a FIXED number of edges later): the first tag of an instruction pops its descriptor; every ME instruction
//     emits exactly 8 * tiles such tags (one per burst), counted down.
// train_start leaves TRAIN_EDGES edges after the first tag's edge: the fixed tag -> port -> port-tile -> serializer
// latency (port pipeline + rq register + the die's assigned relay edges; -1 = unassigned: refuses elaboration, as the
// other native route ages).  Queue overflow / underflow or an instruction outside the train contract is a sticky
// fault; the serializers check every capture against the calendar (off-calendar = their fault).
// MUT (bench): 1 = start one edge late (negative control); 2 = slot_count always 8 (no row compression: the measured
// 3-lane/8-slot option, legal); 3 = slot_count halved (negative control: real rows outside the reserved slots).
module qfd_res_train_issue #(parameter integer TRAIN_EDGES=-1, MUT=0)(
 input wire ck,rst_n,
 input wire me_go,input wire[17:0]me_tiles,input wire[23:0]me_ts,input wire[3:0]me_split,input wire me_oen,
 input wire tag_v,tag_last,
 output wire train_start,output wire[3:0]train_count,output wire[31:0]capture_stride,output wire payload_write,
 output wire[3:0]slot_count,output reg fault);
 initial if(TRAIN_EDGES<2)$fatal(1,"qfd_res_train_issue: TRAIN_EDGES (tag -> serializer capture edges) must be assigned (>= 2)");
 localparam integer TE=(TRAIN_EDGES<2)?2:TRAIN_EDGES;
 localparam integer DW=4+32+1+4;
 function automatic [3:0] ns_of(input [3:0] sp);
  ns_of=(MUT==2||sp<=7)?4'd8:(sp==8)?4'd4:(sp==9)?4'd2:4'd1;
  if(MUT==3&&ns_of>1)ns_of=ns_of>>1;
 endfunction
 reg[DW-1:0]q[0:3];reg[1:0]wp,rp;reg[2:0]n;
 reg[6:0]left;          // tags of the current instruction still to come
 wire tag=tag_v&&tag_last;
 wire pop=tag&&left==0;
 wire push=me_go;
 wire[DW-1:0]din={me_tiles[3:0],(me_ts<24'd8)?32'd8:32'(me_ts),me_oen,ns_of(me_split)};
 reg launch;reg[DW-1:0]ldesc;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin wp<=0;rp<=0;n<=0;left<=0;launch<=0;ldesc<=0;fault<=0;end
  else begin
   launch<=pop&&n!=0;
   if(push)begin q[wp]<=din;wp<=wp+1'b1;end
   if(pop&&n!=0)begin ldesc<=q[rp];rp<=rp+1'b1;left<=7'({q[rp][DW-1-:4],3'b0})-7'd1;end
   else if(tag&&left!=0)left<=left-1'b1;
   n<=n+3'(push)-3'(pop&&n!=0);
   if(push&&n==4&&!(pop&&n!=0) || pop&&n==0 || push&&(me_tiles==0||me_tiles>8))fault<=1;
  end
 end
 // fixed delay: launch is one edge after the tag edge; TE - 1 more edges to the serializer capture edge
 localparam integer LD=TE-1+((MUT==1)?1:0);
 reg[DW:0]dl[0:LD];
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin for(integer i=0;i<=LD;i=i+1)dl[i]<=0;end
  else begin dl[0]<={launch,ldesc};for(integer i=1;i<=LD;i=i+1)dl[i]<=dl[i-1];end
 wire[DW:0]o=(LD==0)?{launch,ldesc}:dl[LD-1];
 assign {train_start,train_count,capture_stride,payload_write,slot_count}=o;
endmodule
