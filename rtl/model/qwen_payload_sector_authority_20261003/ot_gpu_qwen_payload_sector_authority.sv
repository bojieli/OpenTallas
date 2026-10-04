`timescale 1ns/1ps
// Default-off finite authority; no memory or arithmetic implementation.
// One global physical sector lock. ALL same-sector callers must pass guard_*.
// issue/capture/reverse are actual accepted port events, never software flags.
// por_n is fenced cold power-on ONLY; local_reset stops but retains live debt.
module ot_gpu_qwen_payload_sector_authority #(parameter ENABLE=0, IDENTW=207)(
 input wire clk, por_n, run_enable, local_reset,
 input wire alloc_valid, output wire alloc_ready,
 input wire [126:0] alloc_source, input wire alloc_rmw,
 input wire map_valid, map_sector_clear, input wire [33:0] map_addr,
 input wire [6:0] map_PC, input wire [2:0] map_client,
 input wire [31:0] map_tag, input wire [3:0] map_gen,
 output wire grant_live, output wire [IDENTW-1:0] grant_identity,
 output wire grant_rmw, output wire [2:0] grant_phase,
 // Enclosing mux gates EVERY client's same-sector admission with this permit.
 input wire [203:0] guard_addr, input wire [275:0] guard_owner,
 input wire [5:0] guard_write, output wire [5:0] guard_permit,
 input wire issue_valid, output wire issue_ready,
 input wire [IDENTW-1:0] issue_identity, input wire issue_write,
 input wire capture_valid, output wire capture_ready,
 input wire [IDENTW-1:0] capture_identity, input wire capture_write,
 input wire reverse_valid, output wire reverse_ready,
 input wire [IDENTW-1:0] reverse_identity, input wire reverse_write,
 input wire release_valid, output wire release_ready,
 input wire [IDENTW-1:0] release_identity,
 output reg fault
);
 localparam IDLE=0, OLD_REQ=1, OLD_CAP=2, OLD_REV=3,
            NEW_REQ=4, NEW_CAP=5, NEW_REV=6, RELEASE=7;
 reg [2:0] phase;
 reg [IDENTW-1:0] owner;
 reg rmw;
 wire active=ENABLE && IDENTW==207 && por_n && run_enable && !local_reset && !fault;
 wire live=phase!=IDLE;
 wire issue_phase=phase==OLD_REQ || phase==NEW_REQ;
 wire cap_phase=phase==OLD_CAP || phase==NEW_CAP;
 wire rev_phase=phase==OLD_REV || phase==NEW_REV;
 wire issue_we=phase==NEW_REQ;
 wire cap_we=phase==NEW_CAP;
 wire rev_we=phase==NEW_REV;
 // Source layout = identity64,key20,sector9,source_addr34.
 // Physical suffix = addr34,PC7,client3,original_tag32,explicit_gen4.
 wire bad_map=map_client>=6 || map_addr[4:0]!=0 || alloc_source[4:0]!=0
              || alloc_source[42:34]>=272
              || alloc_rmw!=(alloc_source[42:34]<256);
 // map_sector_clear is actual prior-sector AND selected-client copy drain.
 // The selected client is serialized, so its returns cannot be interleaved
 // with a second tag while the payload adapter is capturing a sector.
 // A global idle bit or an unacknowledged write request cannot supply it.
 assign alloc_ready=active && !live && map_valid && map_sector_clear && !bad_map;
 assign grant_live=live; assign grant_identity=owner;
 assign grant_rmw=rmw; assign grant_phase=phase;
 genvar g;
 generate for(g=0;g<6;g=g+1) begin: guards
  assign guard_permit[g]=active && ((!live && (!alloc_valid ||
     (map_valid && guard_addr[g*34+:34]!=map_addr && guard_owner[g*46+36+:3]!=map_client))) ||
     (live && ((guard_addr[g*34+:34]!=owner[79:46] && guard_owner[g*46+36+:3]!=owner[38:36]) ||
     (issue_phase && guard_addr[g*34+:34]==owner[79:46] &&
      guard_owner[g*46+:46]==owner[45:0] && guard_write[g]==issue_we))));
 end endgenerate
 assign issue_ready=active && issue_phase && issue_identity==owner && issue_write==issue_we;
 assign capture_ready=active && cap_phase && capture_identity==owner && capture_write==cap_we;
 assign reverse_ready=active && rev_phase && reverse_identity==owner && reverse_write==rev_we;
 assign release_ready=active && phase==RELEASE && release_identity==owner;
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin phase<=IDLE;owner<=0;rmw<=0;fault<=0;end
  else if(ENABLE) begin
   if(local_reset) fault<=1; // Never erase externally accepted debt.
   else if(run_enable && !fault) begin
    if((alloc_valid && !live && map_valid && bad_map) ||
       (issue_valid && !issue_ready) ||
       (capture_valid && !capture_ready) ||
       (reverse_valid && !reverse_ready) ||
       (release_valid && live && release_identity!=owner)) fault<=1;
    else begin
     if(alloc_valid && alloc_ready) begin
      owner<={alloc_source,map_addr,map_PC,map_client,map_tag,map_gen};
      rmw<=alloc_rmw; phase<=alloc_rmw ? OLD_REQ : NEW_REQ;
     end
     if(issue_valid && issue_ready) phase<=issue_we ? NEW_CAP : OLD_CAP;
     if(capture_valid && capture_ready) phase<=cap_we ? NEW_REV : OLD_REV;
     if(reverse_valid && reverse_ready) phase<=rev_we ? RELEASE : NEW_REQ;
     if(release_valid && release_ready) begin phase<=IDLE;owner<=0;rmw<=0;end
    end
   end
  end
 end
endmodule
