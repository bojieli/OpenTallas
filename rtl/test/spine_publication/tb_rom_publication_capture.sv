`timescale 1ns/1ps
// Control/transport unit gate only. No arithmetic/checkpoint/token claim.
module tb_rom_publication_capture;
 reg clk=0;always #5 clk=~clk;
 reg rn=0,warm=0,phase_v=0,rv=0,re=0,ff=0,permit=1;
 reg [15:0] row=0,bf=0;reg [2:0] pos=0;reg [31:0] fp=0;
 wire pf,pv,pe;wire [15:0] pr,pb;wire [2:0] pp;wire [31:0] pd;
 wire [69:0] incoming, outgoing;
 assign incoming={ff,rv,row,pos,fp,bf,re};
 ot_v41_rom_publication_capture #(.ENABLE(1),.WIDTH(70)) publication(
 .clk(clk),.rst_n(rn),.publication_in(incoming),.publication_out(outgoing));
 assign {pf,pv,pr,pp,pd,pb,pe}=outgoing;
 wire ready,live,idle,drained,fault,v;
 wire [29:0] addr;wire [31:0] data;wire [46:0] identity;wire [9:0] phase;
 wire accept=v&&permit; // This selected unit VM commits every accepted write.
 wire quarantine=warm||pf||(pv&&pe);
 ot_dsrom_rd64_vm_capture #(.ENABLE(1),.ROOTS(1),.CAPACITY(4),.VM_AW(19)) capture(
 .clk(clk),.rst_n(rn),.reset_request(quarantine),.phase_valid(phase_v),.phase_ready(ready),
 .phase_identity(47'h1234567),.phase_id(10'd18),.phase_root_rows(19'd2),
 .phase_obase(30'd64),.phase_ops(30'd16),.phase_np(3'd1),.phase_fmt(2'd1),
 .phase_rsplit(16'd0),.phase_fp32_low(1'b1),.phase_fp32_high(1'b1),
 .r_valid(pv),.r_error(pe),.r_row(pr),.r_pos(pp),.r_fp32(pd),.r_bf16(pb),
 .vm_valid(v),.vm_accept(accept),.vm_addr(addr),.vm_data(data),.vm_row(),.vm_pos(),
 .held_identity(identity),.held_phase(phase),.phase_live(live),.phase_idle(idle),.phase_drained(drained),.fault(fault));
 integer commits=0;reg [31:0] vm[0:127];
 always @(posedge clk) if(rn&&accept)begin
  if(quarantine)$fatal(1,"write accepted under paired fault quarantine");
  vm[addr]<=data;commits<=commits+1;
 end
 task tick;begin @(posedge clk);#1;end endtask
 task cold;begin @(negedge clk);rn=0;rv=0;ff=0;re=0;warm=0;phase_v=0;permit=1;
 tick;@(negedge clk);rn=1;tick;end endtask
 task start;begin @(negedge clk);if(!ready)$fatal(1,"actual descriptor not ready");phase_v=1;
 tick;@(negedge clk);phase_v=0;end endtask
 initial begin
 cold;start;
 @(negedge clk);rv=1;row=3;pos=1;fp=32'h3f812345;bf=16'h3f81;
 tick;if(outgoing!==incoming)$fatal(1,"publication tuple not aligned");
 @(negedge clk);row=4;pos=0;fp=32'hc0234567;bf=16'hc023;
 tick;if(outgoing!==incoming)$fatal(1,"back-to-back publication mismatch");
 @(negedge clk);rv=0;repeat(6)tick;
 if(!drained||fault||commits!=2||vm[83]!==32'h3f812345||vm[68]!==32'hc0234567)
  $fatal(1,"positive VM receipts/metadata mismatch");
 // Stage a real owned row while the selected VM is unavailable. The aligned
 // field fault must inhibit VM use and preserve the existing capture debt.
 cold;start;permit=0;
 @(negedge clk);rv=1;row=5;fp=32'h40812345;tick;
 @(negedge clk);rv=0;tick;
 if(capture.count[0]!=1||!live)$fatal(1,"missing actual retained row");
 @(negedge clk);ff=1;tick;
 if(v||!fault)$fatal(1,"paired field fault did not quarantine SAME visible tuple");
 @(negedge clk);ff=0;permit=1;tick;tick;
 if(drained||idle||!live||capture.count[0]!=1||identity!=47'h1234567||phase!=18||commits!=2)
  $fatal(1,"fault cleared debt/owner or fabricated commit/drain");
 // A valid/error tuple takes the same quarantine path, across ALL writes.
 cold;start;
 @(negedge clk);rv=1;re=1;row=6;fp=32'h7fc12345;tick;
 if(v||!fault||!pe||!pv)$fatal(1,"same-edge row error not quarantined");
 @(negedge clk);rv=0;re=0;tick;tick;
 if(drained||idle||commits!=2||identity!=47'h1234567)$fatal(1,"error discarded accepted phase debt");
 $display("PASS paired publication exact tuple/II1 + positive VM writes + field/error quarantine retained identity/debt; no token/physical claim");
 $finish;
 end
endmodule
