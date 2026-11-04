`timescale 1ns/1ps
// qwen-split/kvsys die lead r6 2026-10-15: per-PC physical slice of the actual HOST root (qkd_host_root_integrated).
// The root's 128-PC static ingest/return path (land_es/land_er 36,864 + 33,408 b, ctrl_es/ctrl_er 36,864 + 33,408 b)
// cannot enter one HOST block (cut rule), so the die places one slice beside each controller/landing pair:
//   landing.es -> u_static (qkd_host_static_pc_emback) -> u_boot (qkd_hbm_boot_static_completion) -> controller.es
//   controller.er -> u_boot -> u_static -> landing.er           (all 288/261-b words stay local to the PC)
// and the ingest station (qkd_host_ingest_station) chains slice to slice along the stack column (f / c / a / fault,
// pin-registered both ways).  Only 1-b status (all_ack, boot_done/ok/fault) and the stack chain ends reach the root
// core (qkd_host_root_pt).  Same three source modules, same connections as qkd_host_ingest_chain_splitboot.g_pc and
// qkd_host_rank_services.g_boot: a hierarchy move, no logic added except the wire-level OR the parent already had
// (all_acks[ID] = host_ack | land_ack).  lpc = the logical PC strap (5'(pc) in the source parent).
module qkd_host_pc_slice #(parameter integer MUT=0)(
 input wire ck_station,ck_static,ck_boot,ck_boot_test,
 input wire host_rst_n,hbm_rst_n,boot_go,
 input wire[4:0]lpc,
 input wire[290:0]fi,output wire[290:0]fo,
 input wire[31:0]ci,output wire[31:0]co,
 input wire[31:0]ai,output wire[31:0]ao,
 input wire fault_i,output wire fault_o,
 input wire[287:0]land_es,output wire[260:0]land_er,
 output wire[287:0]ctrl_es,input wire[260:0]ctrl_er,
 input wire ctrl_completion_v,ctrl_completion_we,
 output wire all_ack,boot_done,boot_ok,boot_fault
);
 wire[287:0]host_es,normal_es;wire[260:0]normal_er;
 wire host_cr,host_ack,land_ack,host_fault,completion_v,completion_we;
 assign all_ack=host_ack|land_ack;
 qkd_host_ingest_station u_station(.ck(ck_station),.rst_n(host_rst_n),.lpc(lpc),.fi(fi),.fo(fo),
 .host_es(host_es),.host_cr(host_cr),.host_ack(host_ack),.host_fault(host_fault),
 .ci(ci),.co(co),.ai(ai),.ao(ao),.fault_i(fault_i),.fault_o(fault_o));
 qkd_host_static_pc_emback #(.MUT(MUT))u_static(.ck(ck_static),.rst_n(host_rst_n),
 .land_es(land_es),.land_er(land_er),.host_es(host_es),.host_cr(host_cr),.host_ack(host_ack),.land_ack(land_ack),
 .ctrl_es(normal_es),.ctrl_er(normal_er),.completion_v(completion_v),.completion_we(completion_we),.fault(host_fault));
 qkd_hbm_boot_static_completion u_boot(.ck(ck_boot),.ck_test(ck_boot_test),.rst_n(hbm_rst_n),.boot_go(boot_go),
 .normal_es(normal_es),.normal_er(normal_er),.ctrl_es(ctrl_es),.ctrl_er(ctrl_er),
 .completion_v(ctrl_completion_v),.completion_we(ctrl_completion_we),
 .normal_completion_v(completion_v),.normal_completion_we(completion_we),
 .boot_completion_v(),.boot_completion_we(),.boot_done(boot_done),.boot_ok(boot_ok),.boot_cause(),.fault(boot_fault));
endmodule
