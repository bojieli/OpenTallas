`timescale 1ns/1ps
// Additive native x3 merger. Eight prepaid slots per producer and eight in
// the actual hub. An issued owner's source credit waits for real hub retirement.
// Host runtime KV remains a separate writer; this block never credits it.
module ot_qfd_hub_boot_merge #(parameter integer ENABLE=0)(
 input wire ck,rst_n,
 input wire su_v,input wire [511:0] su_d,input wire [10:0] su_tag,
 output wire su_credit,
 input wire host_v,host_we,input wire [31:0] host_addr,input wire [255:0] host_d,
 output wire host_boot_credit,host_boot_accept,host_runtime_v,
 output wire hub_v,output wire [511:0] hub_d,output wire [10:0] hub_tag,
 input wire hub_credit,output wire fault
);
 // Source-pinned native host convention; no runtime packet is consumed here.
 assign host_runtime_v=host_v && !host_addr[31];
 generate if(ENABLE!=0)begin: enabled
  reg [522:0] su_q[0:7],host_q[0:7];
  reg [2:0] sr,sw,hr,hw,orr,ow;
  reg [3:0] sc,hc,oc,credits,su_debt,host_debt;
  reg owner[0:7];
  reg [522:0] out_packet;reg out_valid,scr,hcr,haccept,sticky_fault;
  wire marker=host_addr==32'hffffffff;
  wire host_selected=host_v && host_addr[31];
  wire host_valid=host_selected && host_we && (marker || (host_addr[30:25]==0 && host_addr[24:0]<25'd19457304));
  wire host_bad=host_selected && !host_valid;
  wire [522:0] boot_packet=marker ? {11'h600,448'b0,host_d[63:0]} : {11'h500,231'b0,host_d,host_addr[24:0]};
  wire choose_host=sc==0;
  wire have=sc!=0 || hc!=0;
  wire range_bad=sc>8 || hc>8 || oc>8 || credits>8 ||
   3'(sw-sr)!=sc[2:0] || 3'(hw-hr)!=hc[2:0] || 3'(ow-orr)!=oc[2:0] || credits+oc!=8;
  wire retirement=hub_credit && oc!=0;
  wire retire_host=retirement && owner[orr];
  wire retire_su=retirement && !owner[orr];
  wire source_bad=su_debt>8 || host_debt>8 || 5'(su_debt)+5'(host_debt)!=5'(sc)+5'(hc)+5'(oc) ||
   (su_v && su_debt==8 && !retire_su) || (host_valid && host_debt==8 && !retire_host);
  wire send=have && credits!=0 && !sticky_fault && !range_bad && !source_bad && !host_bad && !(hub_credit && oc==0);
  wire overflow=(su_v && sc==8 && !(send && !choose_host)) || (host_valid && hc==8 && !(send && choose_host));
  wire go=send && !overflow;
  assign hub_v=!sticky_fault && out_valid;
  assign {hub_tag,hub_d}=out_packet;
  assign su_credit=!sticky_fault && scr;
  assign host_boot_credit=!sticky_fault && hcr;
  assign host_boot_accept=!sticky_fault && haccept;
  assign fault=sticky_fault;
  always @(posedge ck or negedge rst_n)
   if(!rst_n)begin
    sr<=0;sw<=0;hr<=0;hw<=0;orr<=0;ow<=0;sc<=0;hc<=0;oc<=0;credits<=8;su_debt<=0;host_debt<=0;
    out_packet<=0;out_valid<=0;scr<=0;hcr<=0;haccept<=0;sticky_fault<=0;
   end else begin
    out_valid<=0;scr<=0;hcr<=0;haccept<=0;
    if(range_bad||source_bad||host_bad||overflow||(hub_credit&&oc==0))sticky_fault<=1;
    if(!sticky_fault && !range_bad && !source_bad && !host_bad && !overflow && !(hub_credit&&oc==0))begin
     su_debt<=su_debt+su_v-retire_su;host_debt<=host_debt+host_valid-retire_host;
     credits<=credits-go+retirement;oc<=oc+go-retirement;
     sc<=sc+su_v-(go&&!choose_host);hc<=hc+host_valid-(go&&choose_host);
     if(su_v)begin su_q[sw]<={su_tag,su_d};sw<=sw+1'b1;end
     if(host_valid)begin host_q[hw]<=boot_packet;hw<=hw+1'b1;haccept<=1;end
     if(go)begin
      out_packet<=choose_host ? host_q[hr] : su_q[sr];out_valid<=1;
      if(choose_host)hr<=hr+1'b1;else sr<=sr+1'b1;
      owner[ow]<=choose_host;ow<=ow+1'b1;
     end
     if(retirement)begin
      scr<=!owner[orr];hcr<=owner[orr];orr<=orr+1'b1;
     end
    end
   end
 end else begin: disabled
  // Default leaves the historical SU-to-hub path exactly wired.
  assign hub_v=su_v;assign hub_d=su_d;assign hub_tag=su_tag;assign su_credit=hub_credit;
  assign host_boot_credit=1'b0;assign host_boot_accept=1'b0;assign fault=1'b0;
 end endgenerate
endmodule
