`default_nettype none
// Reviewable fallback only: actual canonical NW COLL kq + SU wq0 packets.
// Explicit arm is a NEW programme/window contract, not an implicit enable.
// cfg289 supplies four role-local query bases; N1 only, no automatic allocation.
// Original NW writes remain on their original ports. Three replicas use owner1.
// Source capture -> destination capture -> bank sample adds TWO edges to the
// original canonical bank sample. Cross-role setup/hold/taps require adoption.
module ot_vms_idx_query_replica_n1 #(parameter integer MUT=0)(
 input wire clk_source,input wire[31:0]clk_destination,input wire rst_n,
 input wire arm,input wire[288:0]native_cfg,
 input wire[2247:0]canonical_coll_kq,canonical_su_wq,
 input wire[31:0]destination_write_valid,
 output wire[9023:0]replica_wq,
 output wire[31:0]collision,
 output wire pending,
 output wire fault
);
 wire rst_source;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) source_reset(.clk(clk_source),.rst_n_in(rst_n),.rst_n(rst_source));
 reg armed,bad,map_fault;reg[67:0]bases;
 reg config_bad;reg[16:0]base,tail;
 always @*begin
  config_bad=native_cfg[276:272]!=1;
  base=0;tail=0;
  for(integer r=0;r<4;r=r+1)begin
   base=native_cfg[r*68+17+:17];tail=base+17'd511;
   if(base[16] || base[14:13]!=2'(r) || tail[16] || tail[14:13]!=2'(r))config_bad=1;
   if(r==2 && (base[15] || tail[15]))config_bad=1; // actual old canonical producers cannot express high regular
  end
 end
 wire[31:0]dest_fault;wire any_pipe;
 always @(posedge clk_source or negedge rst_source)begin
  if(!rst_source)begin armed<=0;bad<=0;bases<=0;end
  else begin
   if(arm && !armed)begin
    if(config_bad)bad<=1;
    else begin armed<=1;for(integer r=0;r<4;r=r+1)bases[r*17+:17]<=native_cfg[r*68+17+:17];end
   end
   if(!arm)begin if(armed && any_pipe)bad<=1;armed<=0;end
  end
 end
 reg[9023:0]mapped;
 reg map_bad;reg[15:0]oldsec;reg[16:0]sec,delta,target;
 reg[280:0]cp,sp,chosen;reg cm,sm;
 integer dest;
 always @*begin
  mapped=0;map_bad=0;oldsec=0;sec=0;delta=0;target=0;cp=0;sp=0;chosen=0;cm=0;sm=0;dest=0;
  for(integer bank=0;bank<8;bank=bank+1)begin
   cp=canonical_coll_kq[bank*281+:281];sp=canonical_su_wq[bank*281+:281];
   oldsec=cp[279:264];sec={oldsec[15],1'b0,oldsec[14:0]};
   cm=cp[280] && !sec[16] && sec>=bases[34+:17] && (sec-bases[34+:17])<17'd512;
   oldsec=sp[279:264];sec={oldsec[15],1'b0,oldsec[14:0]};
   sm=sp[280] && !sec[16] && sec>=bases[34+:17] && (sec-bases[34+:17])<17'd512;
   if(armed && arm && (cm||sm))begin
    if(cm && sm)map_bad=1;
    else begin
     chosen=cm?cp:sp;oldsec=chosen[279:264];sec={1'b0,1'b0,oldsec[14:0]};delta=sec-bases[34+:17];
     if(oldsec[2:0]!=3'(bank) || oldsec[14:13]!=2'd2)map_bad=1;
     else for(integer role=0;role<4;role=role+1)if(role!=2)begin
      target=bases[role*17+:17]+delta;
      if(MUT==1)target[15]=0; // actual upper regular address loss
      if(MUT==2)target[14:13]=2'd2; // wrong role
      if(MUT==3)target=target+17'd8; // wrong sector offset
      dest=role*8+32'(target[2:0]);
      if(mapped[dest*282+281])map_bad=1;
      mapped[dest*282+:282]={1'b1,target,chosen[263:0]};
     end
    end
   end
  end
  if(map_bad || bad || map_fault)mapped=0;
 end
 reg[9023:0]source_q;reg[31:0]source_v;
 always @(posedge clk_source)source_q<=mapped;
 always @(posedge clk_source or negedge rst_source)
  if(!rst_source)begin source_v<=0;map_fault<=0;end
  else begin
   for(integer d=0;d<32;d=d+1)source_v[d]<=mapped[d*282+281];
   if(map_bad)map_fault<=1;
  end
 wire[31:0]dest_pending;
 for(genvar d=0;d<32;d=d+1)begin:g_destination
  wire rst_dest;
  ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) reset(.clk(clk_destination[d]),.rst_n_in(rst_n),.rst_n(rst_dest));
  reg[280:0]captured;reg captured_v;reg sticky;reg[2:0]drain;
  wire[281:0]packet=(MUT==4)?mapped[d*282+:282]:{captured_v,captured};
  assign collision[d]=packet[281] && destination_write_valid[d];
  assign replica_wq[d*282+:282]={packet[281] && (!collision[d] || MUT==5),packet[280:0]};
  assign dest_pending[d]=source_v[d] || packet[281] || drain!=0;
  assign dest_fault[d]=sticky;
  always @(posedge clk_destination[d])captured<=source_q[d*282+:281];
  always @(posedge clk_destination[d] or negedge rst_dest)
   if(!rst_dest)begin captured_v<=0;sticky<=0;drain<=0;end
   else begin
    captured_v<=source_v[d];
    if(collision[d])sticky<=1;
    if(packet[281])drain<=3'd5;else if(drain!=0)drain<=drain-1'b1;
   end
 end
 assign any_pipe=|dest_pending;
 assign pending=any_pipe;
 assign fault=bad || map_fault || (|dest_fault);
endmodule
`default_nettype wire
