// HBM-REFORM-B4 d44v part 26: plan module ot_hbm_svc_sm_group_rel_id = thin parent glue of the split hard core (wires only).
`default_nettype none
module ot_hbm_svc_sm_group_rel_id__fcore  #(parameter integer LBANKS=4,parameter integer LB=(LBANKS>2)?2:1,
 parameter integer NID=6,parameter integer IDW=9,parameter integer PAW=11,parameter integer PREL=1,parameter integer DD=256,parameter integer IMUT=0,
 parameter integer DAW=(DD>128)?8:7,parameter integer ID_COHORT=0,
 // HBM-SMXL 2026-10-19: XSLOT 1 = the descriptor's x-store slot base relocates every command's xaddr (die op_xb from
 // the static programme; issuer + feed headers).  0 (default) = unchanged.
 parameter integer XSLOT=0,parameter integer CTXW=(XSLOT!=0)?53:46,
 parameter integer OPEN_IL=0,    // HBM-SMXL: open interlock of the producer (feed / cdc OPEN_IL)
 parameter integer ATT_MARK=0)(  // HBM-PV-ATTMARK: feed programme word [119] attention mark (default 0 = unchanged)
 // strap identity: id_stack = HBM stack / quadrant (SW0 SE1 NW2 NE3), id_sm = SM index k (PCs 4k..4k+3)
 input wire[1:0]id_stack,input wire[2:0]id_sm,
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire[1:0]stream_bank_clk,hbm_fifo_clk,input wire[3:0]hbm_pc_clk,
 input wire program_cfg_we,input wire[PAW-1:0]program_cfg_addr,input wire[255:0]program_cfg_data,
 input wire desc_we,input wire[DAW-1:0]desc_addr,input wire[255:0]desc_data,
 input wire run_v,input wire[DAW-1:0]run_base,input wire[DAW:0]run_count,input wire[7:0]run_layer,
 input wire ids_v,input wire[7:0]ids_layer,input wire[IDW*NID-1:0]ids,
 input wire[15:0]ids_cohort,
 output wire running,run_done,program_active,fault,
 output wire[1098:0]sm_packet,output wire[82:0]sm_command,
 output wire[42:0]expected_request,output wire[1081:0]lt0,lt1,output wire[569:0]lb0,lb1,output wire[11:0]fm,
 output wire[3:0]k_v,input wire[3:0]k_rdy,output wire[119:0]k_addr,
 output wire[15:0]k_len,output wire[67:0]k_tag,output wire[3:0]k_we,
 output wire[1023:0]k_wdata,output wire[127:0]k_wstrb,input wire[3:0]k_wr_done,
 input wire[3:0]kr_v,output wire[3:0]kr_rdy,input wire[67:0]kr_tag,input wire[15:0]kr_beat,input wire[1023:0]kr_data
);
 ot_hbm_svc_sm_group_rel_id__p26comp u_core (.id_stack(id_stack), .id_sm(id_sm), .stream_clk(stream_clk), .stream_rst_n(stream_rst_n), .hbm_clk(hbm_clk), .hbm_rst_n(hbm_rst_n), .stream_bank_clk(stream_bank_clk), .hbm_fifo_clk(hbm_fifo_clk), .hbm_pc_clk(hbm_pc_clk), .program_cfg_we(program_cfg_we), .program_cfg_addr(program_cfg_addr), .program_cfg_data(program_cfg_data), .desc_we(desc_we), .desc_addr(desc_addr), .desc_data(desc_data), .run_v(run_v), .run_base(run_base), .run_count(run_count), .run_layer(run_layer), .ids_v(ids_v), .ids_layer(ids_layer), .ids(ids), .ids_cohort(ids_cohort), .running(running), .run_done(run_done), .program_active(program_active), .fault(fault), .sm_packet(sm_packet), .sm_command(sm_command), .expected_request(expected_request), .lt0(lt0), .lt1(lt1), .lb0(lb0), .lb1(lb1), .fm(fm), .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr), .k_len(k_len), .k_tag(k_tag), .k_we(k_we), .k_wdata(k_wdata), .k_wstrb(k_wstrb), .k_wr_done(k_wr_done), .kr_v(kr_v), .kr_rdy(kr_rdy), .kr_tag(kr_tag), .kr_beat(kr_beat), .kr_data(kr_data));
endmodule
module ot_hbm_svc_sm_group_rel_id  #(parameter integer LBANKS=4,parameter integer LB=(LBANKS>2)?2:1,
 parameter integer NID=6,parameter integer IDW=9,parameter integer PAW=11,parameter integer PREL=1,parameter integer DD=256,parameter integer IMUT=0,
 parameter integer DAW=(DD>128)?8:7,parameter integer ID_COHORT=0,
 // HBM-SMXL 2026-10-19: XSLOT 1 = the descriptor's x-store slot base relocates every command's xaddr (die op_xb from
 // the static programme; issuer + feed headers).  0 (default) = unchanged.
 parameter integer XSLOT=0,parameter integer CTXW=(XSLOT!=0)?53:46,
 parameter integer OPEN_IL=0,    // HBM-SMXL: open interlock of the producer (feed / cdc OPEN_IL)
 parameter integer ATT_MARK=0)(  // HBM-PV-ATTMARK: feed programme word [119] attention mark (default 0 = unchanged)
 // strap identity: id_stack = HBM stack / quadrant (SW0 SE1 NW2 NE3), id_sm = SM index k (PCs 4k..4k+3)
 input wire[1:0]id_stack,input wire[2:0]id_sm,
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire[1:0]stream_bank_clk,hbm_fifo_clk,input wire[3:0]hbm_pc_clk,
 input wire program_cfg_we,input wire[PAW-1:0]program_cfg_addr,input wire[255:0]program_cfg_data,
 input wire desc_we,input wire[DAW-1:0]desc_addr,input wire[255:0]desc_data,
 input wire run_v,input wire[DAW-1:0]run_base,input wire[DAW:0]run_count,input wire[7:0]run_layer,
 input wire ids_v,input wire[7:0]ids_layer,input wire[IDW*NID-1:0]ids,
 input wire[15:0]ids_cohort,
 output wire running,run_done,program_active,fault,
 output wire[1098:0]sm_packet,output wire[82:0]sm_command,
 output wire[42:0]expected_request,output wire[1081:0]lt0,lt1,output wire[569:0]lb0,lb1,output wire[11:0]fm,
 output wire[3:0]k_v,input wire[3:0]k_rdy,output wire[119:0]k_addr,
 output wire[15:0]k_len,output wire[67:0]k_tag,output wire[3:0]k_we,
 output wire[1023:0]k_wdata,output wire[127:0]k_wstrb,input wire[3:0]k_wr_done,
 input wire[3:0]kr_v,output wire[3:0]kr_rdy,input wire[67:0]kr_tag,input wire[15:0]kr_beat,input wire[1023:0]kr_data
);
 ot_hbm_svc_sm_group_rel_id__fcore u_fcore (.id_stack(id_stack), .id_sm(id_sm), .stream_clk(stream_clk), .stream_rst_n(stream_rst_n), .hbm_clk(hbm_clk), .hbm_rst_n(hbm_rst_n), .stream_bank_clk(stream_bank_clk), .hbm_fifo_clk(hbm_fifo_clk), .hbm_pc_clk(hbm_pc_clk), .program_cfg_we(program_cfg_we), .program_cfg_addr(program_cfg_addr), .program_cfg_data(program_cfg_data), .desc_we(desc_we), .desc_addr(desc_addr), .desc_data(desc_data), .run_v(run_v), .run_base(run_base), .run_count(run_count), .run_layer(run_layer), .ids_v(ids_v), .ids_layer(ids_layer), .ids(ids), .ids_cohort(ids_cohort), .running(running), .run_done(run_done), .program_active(program_active), .fault(fault), .sm_packet(sm_packet), .sm_command(sm_command), .expected_request(expected_request), .lt0(lt0), .lt1(lt1), .lb0(lb0), .lb1(lb1), .fm(fm), .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr), .k_len(k_len), .k_tag(k_tag), .k_we(k_we), .k_wdata(k_wdata), .k_wstrb(k_wstrb), .k_wr_done(k_wr_done), .kr_v(kr_v), .kr_rdy(kr_rdy), .kr_tag(kr_tag), .kr_beat(kr_beat), .kr_data(kr_data));
endmodule
`default_nettype wire
