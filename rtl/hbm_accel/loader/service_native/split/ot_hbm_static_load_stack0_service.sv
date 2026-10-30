`default_nettype none
// PREP mandatory second LOAD source family: real STACK0 PHY-service boundary.
// SOFT integration wrapper: dissolve into32 realPC/8VMKS/2REF children; NEVER
// harden this >400k-cell whole. No STACK2 alias/rebase or target-ID allocation.
// Existing ROLE89 low/high outputs supply fixed fill commands. Parent must gate
// them by the accepted STACK0 LOADcontext before use; no ready/wait replaces
// the dated LOAD deadline. RefreshIDs are explicit planned strap inputs.
// New-family SM and WB clients are inactive, not fictitious response producers.
// PCready/response credit and the existing GrayCDC remain REAL boundary logic.
// All roots share the existing related controller/stream clock; profile833
// defaultOFF, enable only with qualified bootrows, ns/CA and resetphase contract.
module ot_hbm_static_load_stack0_service #(parameter integer TIMING_833=0)(
 input wire clk,rst_n,
 input wire[7:0]strap_refresh_lo_tgt,strap_refresh_hi_tgt,
 input wire cfg_v,input wire[7:0]cfg_target,input wire[11:0]cfg_addr,input wire[255:0]cfg_data,
 input wire lo_calendar_v,hi_calendar_v,input wire[88:0]lo_calendar_payload,hi_calendar_payload,
 input wire[31:0]phy0_dram_rvalid,input wire[8191:0]phy0_dram_rdata,
 output wire[31:0]phy0_row_v,output wire[95:0]phy0_row_op,output wire[159:0]phy0_row_bank,
 output wire[607:0]phy0_row_row,output wire[31:0]phy0_col_v,phy0_col_we,
 output wire[159:0]phy0_col_bank,phy0_col_col,output wire[8191:0]phy0_col_data,output wire[1023:0]phy0_col_strb,
 // Provider ordering is leafb*2+g: physicalPC=half*16+b+8*g.
 output wire[15:0]lo_fill_v,lo_fill_bank,hi_fill_v,hi_fill_bank,
 output wire[95:0]lo_fill_slot,hi_fill_slot,output wire[255:0]lo_fill_epoch,hi_fill_epoch,
 output wire[4095:0]lo_fill_data,hi_fill_data,
 output wire[1:0]refresh_ready,refresh_active,refresh_fault,
 output wire[31:0]pc_fault,output wire[7:0]vmks_fault,output wire source_fault_o
);
 wire[255:0]reload;wire[1:0]pc_rst_n;
 for(genvar h=0;h<2;h=h+1)begin:g_refresh
 ot_hbm_pc_refresh_cfg #(.NPC(16),.RMIN(TIMING_833?144:118),.RMAX(TIMING_833?252:236),.REL_HOLD(64))u_ref(
 .clk(clk),.rst_n(rst_n),.clk_hbm(clk),.rst_hbm_n(rst_n),.tgt(h==0?strap_refresh_lo_tgt:strap_refresh_hi_tgt),
 .cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .refresh_reload(reload[h*128+:128]),.pc_rst_n(pc_rst_n[h]),.ready(refresh_ready[h]),.active(refresh_active[h]),.fault(refresh_fault[h]));
 end
 wire[31:0]kv,krdy,kwe,kdone,krv,krrdy,fv,fb;
 wire[959:0]ka;wire[127:0]kl,kb;wire[543:0]kt,krt;
 wire[8191:0]kwd,krd,fd;wire[1023:0]kws;wire[191:0]fs;wire[511:0]fe;
 for(genvar g=0;g<8;g=g+1)begin:g_group
 localparam[2:0]SM=g;
 wire[88:0]cal=g<4?lo_calendar_payload:hi_calendar_payload;
 wire cal_v=g<4?lo_calendar_v:hi_calendar_v;
 ot_hbm_svc_vm_kshare_splitstrap #(.MUT(0),.KRL1(1))u_vmks(
 .hbm_clk(clk),.hbm_rst_n(rst_n),.stream_clk(clk),.stream_rst_n(rst_n),.sm_stream(SM),.sm_hbm(SM),
 .g_k_v(4'b0),.g_k_rdy(),.g_k_addr(120'b0),.g_k_len(16'b0),.g_k_tag(68'b0),.g_k_we(4'b0),.g_k_wdata(1024'b0),.g_k_wstrb(128'b0),.g_k_wr_done(),
 .g_kr_v(),.g_kr_rdy(4'b1111),.g_kr_tag(),.g_kr_beat(),.g_kr_data(),
 .c_k_v(kv[g*4+:4]),.c_k_rdy(krdy[g*4+:4]),.c_k_addr(ka[g*120+:120]),.c_k_len(kl[g*16+:16]),.c_k_tag(kt[g*68+:68]),
 .c_k_we(kwe[g*4+:4]),.c_k_wdata(kwd[g*1024+:1024]),.c_k_wstrb(kws[g*128+:128]),.c_k_wr_done(kdone[g*4+:4]),
 .c_kr_v(krv[g*4+:4]),.c_kr_rdy(krrdy[g*4+:4]),.c_kr_tag(krt[g*68+:68]),.c_kr_beat(kb[g*16+:16]),.c_kr_data(krd[g*1024+:1024]),
 .vm_v(cal_v&&cal[52]),.vm_bank(cal[53]),.vm_epoch(cal[69:54]),.vm_row(cal[84:70]),.vm_col(cal[88:85]),
 .wbw_v(1'b0),.wbw_base(30'b0),.wbw_total(12'b0),.w_k_v(4'b0),.w_k_rdy(),.w_k_addr(120'b0),.w_k_wdata(1024'b0),.w_k_wr_done(),
 .fill_v(fv[g*4+:4]),.fill_bank(fb[g*4+:4]),.fill_slot(fs[g*24+:24]),.fill_epoch(fe[g*64+:64]),.fill_data(fd[g*1024+:1024]),.fault(vmks_fault[g]));
 end
 for(genvar p=0;p<32;p=p+1)begin:g_pc
 localparam[4:0]PID=p;
 ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.OREG(1),.KREG(1),.KRREG(1),.RREG(1),.WPAY(1),.QREG(1),.RMUT(0),.TIMING_833(TIMING_833))u_pc(
 .clk(clk),.rst_n(pc_rst_n[p/16]),.pc_id(PID),.refresh_reload(reload[p*8+:8]),
 .k_v(kv[p]),.k_rdy(krdy[p]),.k_we(kwe[p]),.k_addr(ka[p*30+:30]),.k_len(kl[p*4+:4]),.k_tag(kt[p*17+:17]),
 .k_wdata(kwd[p*256+:256]),.k_wstrb(kws[p*32+:32]),.kr_v(krv[p]),.kr_rdy(krrdy[p]),.kr_tag(krt[p*17+:17]),.kr_beat(kb[p*4+:4]),.kr_data(krd[p*256+:256]),.k_wr_done(kdone[p]),
 .row_v(phy0_row_v[p]),.row_op(phy0_row_op[p*3+:3]),.row_bank(phy0_row_bank[p*5+:5]),.row_row(phy0_row_row[p*19+:19]),
 .col_v(phy0_col_v[p]),.col_we(phy0_col_we[p]),.col_bank(phy0_col_bank[p*5+:5]),.col_col(phy0_col_col[p*5+:5]),.col_data(phy0_col_data[p*256+:256]),.col_strb(phy0_col_strb[p*32+:32]),
 .dram_rvalid(phy0_dram_rvalid[p]),.dram_rdata(phy0_dram_rdata[p*256+:256]),.pc_fault(pc_fault[p]),.owner_fault_split());
 end
 for(genvar b=0;b<8;b=b+1)begin:g_leaf_order
 for(genvar g=0;g<2;g=g+1)begin:g_source
 localparam integer P=b+8*g,I=b*2+g;
 assign lo_fill_v[I]=fv[P];assign hi_fill_v[I]=fv[16+P];
 assign lo_fill_bank[I]=fb[P];assign hi_fill_bank[I]=fb[16+P];
 assign lo_fill_slot[I*6+:6]=fs[P*6+:6];assign hi_fill_slot[I*6+:6]=fs[(16+P)*6+:6];
 assign lo_fill_epoch[I*16+:16]=fe[P*16+:16];assign hi_fill_epoch[I*16+:16]=fe[(16+P)*16+:16];
 assign lo_fill_data[I*256+:256]=fd[P*256+:256];assign hi_fill_data[I*256+:256]=fd[(16+P)*256+:256];
 end end
 assign source_fault_o=(|refresh_fault)||(|pc_fault)||(|vmks_fault);
endmodule
`default_nettype wire
