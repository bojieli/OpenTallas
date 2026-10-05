
module tb;
localparam AW=30,VM_AW=19,ROM_R=128,G=4,W=16,SW=8,SUN=256;
localparam S81_CAPTURE=1,X_ROM=1;
reg clk=0,rst_n=0,capture_reset_request=0,phase_valid=0;
always #5 clk=~clk;
reg [127:0] rv=0,re=0;reg [2047:0] row=0,bf=0;reg [383:0] pos=0;
reg [4095:0] fp=0;reg [2431:0] quota=0;
wire [127:0] rom_we,capture_vm_accept;wire [3839:0] rom_waddr;wire [4095:0] rom_wdata;
wire ready,live,drained,fault;wire [46:0] identity;
wire capture_live=live,capture_drained=drained,capture_fault=fault;
wire capture_visibility_quiet=!S81_CAPTURE || (!capture_live && capture_drained && !capture_fault && !(|capture_vm_accept));
    
reg [127:0] rom_duplicate=0;
reg [G-1:0] vw_me_we=0;reg [G*W-1:0] vw_me_mask=0;reg [G*AW-1:0] vw_me_addr=0;
reg [SW-1:0] vw_su_we=0,vw_rd_we=0;reg [SW*AW-1:0] vw_su_addr=0,vw_rd_addr=0;
reg [SUN-1:0] xs_vm_we=0;reg [SUN*AW-1:0] xs_vm_waddr=0;
reg [SUN/8-1:0] xs_res_we=0;reg [SUN/8*AW-1:0] xs_res_addr=0;
reg vw_xe_we=0,ww_q_we=0,ww_x_we=0,xa_we=0;
reg [AW-1:0] vw_xe_addr=0,ww_q_addr=0,ww_x_addr=0;
reg [31:0] ww_q_mask=0,ww_x_mask=0;
reg [VM_AW-5:0] xa_waddr=0;reg [3:0] xb_we4=0;reg [4*(VM_AW-4)-1:0] xb_waddr4=0;
reg [31:0] vm[0:(1<<VM_AW)-1];

    // Literal retained last-write-wins VM semantics: credit only surviving rows.
    // This is a behavioral mutable-VM context, NOT a 128-port SRAM fit claim.
    reg [ROM_R-1:0] capture_commit;
    integer cr,cs,cl;
    reg [VM_AW-1:0] ca;
    always @* begin
      capture_commit=0;ca=0;
      for(cr=0;cr<ROM_R;cr=cr+1)begin
        ca=rom_waddr[cr*AW +: VM_AW];
        capture_commit[cr]=S81_CAPTURE && rst_n && !capture_reset_request && X_ROM && rom_we[cr] && (rom_waddr[cr*AW +:AW] < (AW'(1)<<VM_AW));
        // Later ROM ports and all later source-owned writers retain precedence.
        for(cs=cr+1;cs<ROM_R;cs=cs+1)
          if(rom_we[cs] && ca==rom_waddr[cs*AW +:VM_AW])capture_commit[cr]=0;
        for(cs=0;cs<G;cs=cs+1)for(cl=0;cl<W;cl=cl+1)
          if(vw_me_we[cs] && vw_me_mask[cs*W+cl] && ca==VM_AW'({vw_me_addr[cs*AW +:VM_AW-4],4'b0}+cl))capture_commit[cr]=0;
        for(cs=0;cs<SW;cs=cs+1)begin
          if(vw_su_we[cs] && ca==vw_su_addr[cs*AW +:VM_AW])capture_commit[cr]=0;
          if(vw_rd_we[cs] && ca==vw_rd_addr[cs*AW +:VM_AW])capture_commit[cr]=0;
        end
        for(cs=0;cs<SUN;cs=cs+1)
          if(xs_vm_we[cs] && ca==xs_vm_waddr[cs*AW +:VM_AW])capture_commit[cr]=0;
        for(cs=0;cs<SUN/8;cs=cs+1)
          if(xs_res_we[cs] && ca==xs_res_addr[cs*AW +:VM_AW])capture_commit[cr]=0;
        if(vw_xe_we && ca==vw_xe_addr[VM_AW-1:0])capture_commit[cr]=0;
        for(cl=0;cl<32;cl=cl+1)begin
          if(ww_q_we && ww_q_mask[cl] && ca==VM_AW'(ww_q_addr[VM_AW-1:0]+cl))capture_commit[cr]=0;
          if(ww_x_we && ww_x_mask[cl] && ca==VM_AW'(ww_x_addr[VM_AW-1:0]+cl))capture_commit[cr]=0;
        end
        for(cl=0;cl<16;cl=cl+1)begin
          if(xa_we && ca=={xa_waddr,4'(cl)})capture_commit[cr]=0;
          for(cs=0;cs<4;cs=cs+1)
            if(xb_we4[cs] && ca=={xb_waddr4[cs*(VM_AW-4) +:(VM_AW-4)],4'(cl)})capture_commit[cr]=0;
        end
      end
    end
    assign capture_vm_accept=capture_commit;

// Literal original ROM then XU assignment precedence (the tested competitor).
always @(posedge clk)begin
 for(integer q=0;q<ROM_R;q=q+1)if(rom_we[q]&&capture_vm_accept[q])vm[rom_waddr[q*AW+:VM_AW]]<=rom_wdata[q*32+:32];
 if(vw_xe_we)vm[vw_xe_addr[VM_AW-1:0]]<=32'h12345678;
end
ot_dsrom_rd64_vm_capture #(.ENABLE(1),.ROOTS(128),.CAPACITY(1),.VM_AW(19),.VM_ALWAYS_ACCEPT(1)) dut (
 .clk(clk),.rst_n(rst_n),.reset_request(capture_reset_request),.phase_valid(phase_valid),.phase_ready(ready),
 .phase_identity(47'h123456789),.phase_id(10'd9),.phase_root_rows(quota),.phase_obase(30'd16),.phase_ops(30'd256),.phase_np(3'd0),.phase_fmt(2'd1),.phase_rsplit(16'd0),.phase_fp32_low(1'b1),.phase_fp32_high(1'b1),
 .r_valid(rv),.r_error(re),.r_row(row),.r_pos(pos),.r_fp32(fp),.r_bf16(bf),
 .vm_valid(rom_we),.vm_accept(capture_vm_accept),.vm_addr(rom_waddr),.vm_data(rom_wdata),.vm_row(),.vm_pos(),
 .held_identity(identity),.held_phase(),.phase_live(live),.phase_idle(),.phase_drained(drained),.fault(fault));
task tick;begin @(posedge clk);#1;end endtask
task cold_new_diagnostic;begin
 @(negedge clk);rst_n=0;rv=0;phase_valid=0;capture_reset_request=0;vw_xe_we=0;tick;
 @(negedge clk);rst_n=1;quota=0;quota[0+:19]=1;tick;
 @(negedge clk);if(!ready)$fatal(1,"initial admission blocked");if(!capture_visibility_quiet)$fatal(1,"SU-only zero-debt retirement blocked");phase_valid=1;tick;
 @(negedge clk);phase_valid=0;end endtask
initial begin
 cold_new_diagnostic;
 rv[0]=1;row[0+:16]=0;fp[0+:32]=32'h80000000;tick;
 @(negedge clk);rv=0;if(!capture_vm_accept[0])$fatal(1,"real VM write refused");tick;
 if(vm[16]!==32'h80000000||identity!==47'h123456789||drained)$fatal(1,"raw/identity/earlydrain");
 tick;if(!drained||live||fault)$fatal(1,"actual commit not drained");
 // Later XU writer overwrites this address: no ROM credit, sticky fault.
 cold_new_diagnostic;rv[0]=1;fp[0+:32]=32'hffffffff;tick;
 @(negedge clk);rv=0;vw_xe_we=1;vw_xe_addr=16;#1;
 if(capture_vm_accept[0]||!fault)$fatal(1,"overwritten assignment credited");tick;
 if(drained||vm[16]!==32'h12345678)$fatal(1,"overwrite order/drain changed");
 // Warm reset after accepted but undelivered work cannot erase its owner/debt.
 cold_new_diagnostic;rv[0]=1;fp[0+:32]=32'h7f800000;tick;
 @(negedge clk);rv=0;capture_reset_request=1;tick;
 if(dut.count[0]!==1||dut.received[0]!==1||dut.committed[0]!==0||!live||drained||!fault)$fatal(1,"warm reset erased debt");
 @(negedge clk);capture_reset_request=0;tick;
 if(capture_visibility_quiet||!fault||drained||ready||dut.count[0]!==1)$fatal(1,"warm quarantine released itself");
 // Source same-edge writers other than XU must likewise refuse positive ACK.
 cold_new_diagnostic;rv[0]=1;tick;
 @(negedge clk);rv=0;xs_vm_we[0]=1;xs_vm_waddr[0+:AW]=16;#1;
 if(capture_vm_accept[0])$fatal(1,"SU overwrite credited");xs_vm_we=0;
 xb_we4[0]=1;xb_waddr4[0+:VM_AW-4]=1;#1;
 if(capture_vm_accept[0])$fatal(1,"collective overwrite credited");xb_we4=0;
 $display("PASS S81 actual VM accept/reset 5 cases");$finish;
end
endmodule
