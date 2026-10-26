`timescale 1ns/1ps
// MU-KV-BOOT 10-19 (Qwen ROM 4 users): the KV boot dispatcher for the multi-context layer programme
// qkd_static_kv_layer_programme_mu #(.MU(1)).  Same ports as qkd_static_kv_boot_dispatch (the original file is untouched).
//   MU 0: instantiates the unchanged original (identical by construction).
//   MU 1: boot image target 1 is the MU form, 471 words: 0..323 rows, 324 digest64, 325 epoch16, 326..469 GAP[u][s-1]
//         (u-major, compiled by tools/qwen_static_schedule/mu_calendar.kv_gap_table), 470 seal.  The unchanged original
//         dispatcher still sequences every target, checks every word's order / epoch / target and seals the image; this
//         wrapper extends target 1 only:
//           * words 326..469 (the GAP block) are taken here: legal only in order, right after the original accepted
//             word 325 of target 1 (its layer_we at address 325), with the installed epoch, while not faulted and not
//             executing; each goes out on the same layer bus (layer_we/addr/data, one register like the original's);
//           * word 470 (the seal) is legal only after all 144 GAP words: it reaches the original as its word 326 (the
//             single-user seal position), so the original's 327-word count and its end-of-image check are unchanged,
//             and its layer write is re-addressed 326 -> 470;
//           * an out-of-order / early / extra / wrong-epoch GAP or seal word is a sticky fault (fault_code[3], as the
//             original's order fault; fault_code[4] epoch), and the word is not passed on.
//         A single-user image (seal at 326) loaded at MU 1 is refused: word 326 is taken as GAP[0][0] and the layer
//         programme faults on its non-zero upper half (and the original's end-of-image count fails).
//   Static boot path only: no ready / credit; the GAP block adds 144 boot words, no runtime cycle.
//   SRQ (MU-KV-CTL3 10-19, KV-CTL mu2): passed to the original (SRQ=2: its setup_ready = combinational term + 2 edges;
//         0 = unchanged); the MU 1 extension fault still masks it here (x_fault is a register).
//   WMUT (bench mutants, 0 = off): 1 GAP words not forwarded to the layer bus; 2 seal accepted before the GAP block.
module qkd_static_kv_boot_dispatch_mu_raw #(parameter integer MUT=0,parameter integer DIECFG=0,parameter integer NRST=43,parameter integer LINKCFG=0,parameter integer ESCFG=0,parameter integer DIECAP=0,parameter integer MU=1,parameter integer WMUT=0,parameter integer SRQ=0)(
 input wire ck,rst_n,input wire[142:0]boot_pr,input wire[3:0]boot_image_target,
 input wire boot_image_ready,boot_image_fault,input wire[15:0]boot_image_epoch,
 input wire[63:0]boot_image_digest,input wire execution_active,
 input wire[159:0]sink_applied,input wire[2:0]local_configured,input wire sink_fault,
 input wire diecfg_sealed,diecfg_fault,
 output reg layer_we,output reg[8:0]layer_addr,output reg[63:0]layer_data,
 output wire writer_we,output wire[7:0]writer_addr,output wire[63:0]writer_data,
 output wire ownership_we,output wire[1:0]ownership_addr,output wire[31:0]ownership_data,
 output wire[31:0]landing_we,front_we,output wire[7:0]group_addr,output wire[63:0]group_data,
 output wire[127:0]controller_we,output wire[7:0]controller_addr,output wire[63:0]controller_data,
 output wire[127:0]controller_last,output wire[31:0]front_last,
 output wire diecfg_we,output wire[7:0]diecfg_addr,output wire[63:0]diecfg_data,
 output wire link_cfg_tx_we,link_cfg_rx_we,output wire[5:0]link_cfg_addr,output wire[31:0]link_cfg_data,
 output wire es_cfg_we,output wire[7:0]es_cfg_addr,output wire[63:0]es_cfg_data,
 output wire setup_ready,output reg fault,output reg[7:0]fault_code,
 output wire[15:0]installed_epoch,output wire[63:0]installed_isa_digest
);
 wire o_lw,o_fault;wire[8:0]o_la;wire[63:0]o_ld;wire[7:0]o_fc;wire o_setup;
 wire[142:0]pr_o;
 reg x_fault;reg[7:0]x_fc;
 qkd_static_kv_boot_dispatch #(.MUT(MUT),.DIECFG(DIECFG),.NRST(NRST),.LINKCFG(LINKCFG),.ESCFG(ESCFG),.DIECAP(DIECAP),.SRQ(SRQ))u_disp(
  .ck(ck),.rst_n(rst_n),.boot_pr(pr_o),.boot_image_target(boot_image_target),.boot_image_ready(boot_image_ready),
  .boot_image_fault(boot_image_fault),.boot_image_epoch(boot_image_epoch),.boot_image_digest(boot_image_digest),
  .execution_active(execution_active),.sink_applied(sink_applied),.local_configured(local_configured),.sink_fault(sink_fault),
  .diecfg_sealed(diecfg_sealed),.diecfg_fault(diecfg_fault),
  .layer_we(o_lw),.layer_addr(o_la),.layer_data(o_ld),.writer_we(writer_we),.writer_addr(writer_addr),.writer_data(writer_data),
  .ownership_we(ownership_we),.ownership_addr(ownership_addr),.ownership_data(ownership_data),
  .landing_we(landing_we),.front_we(front_we),.group_addr(group_addr),.group_data(group_data),
  .controller_we(controller_we),.controller_addr(controller_addr),.controller_data(controller_data),
  .controller_last(controller_last),.front_last(front_last),
  .diecfg_we(diecfg_we),.diecfg_addr(diecfg_addr),.diecfg_data(diecfg_data),
  .link_cfg_tx_we(link_cfg_tx_we),.link_cfg_rx_we(link_cfg_rx_we),.link_cfg_addr(link_cfg_addr),.link_cfg_data(link_cfg_data),
  .es_cfg_we(es_cfg_we),.es_cfg_addr(es_cfg_addr),.es_cfg_data(es_cfg_data),
  .setup_ready(o_setup),.fault(o_fault),.fault_code(o_fc),.installed_epoch(installed_epoch),.installed_isa_digest(installed_isa_digest));
 generate if(MU==0)begin:g_plain
  assign pr_o=boot_pr;assign setup_ready=o_setup;
  always @*begin layer_we=o_lw;layer_addr=o_la;layer_data=o_ld;fault=o_fault;fault_code=o_fc;x_fault=0;x_fc=0;end
 end else begin:g_mu
  wire[9:0]addr=boot_pr[73:64];wire[63:0]data=boot_pr[63:0];
  wire w1=boot_pr[74]&&boot_image_target==1;
  wire gap_w=w1&&addr>=10'd326&&addr<10'd470;
  wire seal_w=w1&&addr==10'd470;
  reg open_q;reg[7:0]gcnt;reg g_we;reg[8:0]g_a;reg[63:0]g_d;
  // the GAP block opens on the original's write of word 325 (its epoch word) and closes at the seal
  wire open=open_q||(o_lw&&o_la==9'd325);
  wire ok_gap=gap_w&&open&&({2'b0,gcnt}==addr-10'd326)&&!o_fault&&!x_fault&&!execution_active;
  wire ok_seal=seal_w&&open&&((WMUT==2)||gcnt==8'd144)&&!o_fault&&!x_fault&&!execution_active;
  wire bad_epoch=(gap_w||seal_w)&&boot_image_epoch!=installed_epoch;
  // the original sees every word except the GAP block; the seal reaches it as its own word 326
  assign pr_o=gap_w?{boot_pr[142:75],1'b0,boot_pr[73:0]}:
              seal_w?(ok_seal&&!bad_epoch?{boot_pr[142:74],10'd326,boot_pr[63:0]}:{boot_pr[142:75],1'b0,boot_pr[73:0]}):boot_pr;
  always @(posedge ck or negedge rst_n)
  if(!rst_n)begin open_q<=0;gcnt<=0;g_we<=0;g_a<=0;g_d<=0;x_fault<=0;x_fc<=0;end
  else begin
   g_we<=0;
   if(o_lw&&o_la==9'd325)open_q<=1;
   if(gap_w||seal_w)begin
    if(execution_active)begin x_fault<=1;x_fc[1]<=1;end
    else if(bad_epoch&&!o_fault&&!x_fault)begin x_fault<=1;x_fc[4]<=1;end
    else if(gap_w&&!ok_gap&&!o_fault)begin x_fault<=1;x_fc[3]<=1;end
    else if(seal_w&&!ok_seal&&!o_fault)begin x_fault<=1;x_fc[3]<=1;end
    else if(ok_gap)begin gcnt<=gcnt+1'b1;g_we<=(WMUT!=1);g_a<=addr[8:0];g_d<=data;end
    else if(ok_seal)begin open_q<=0;gcnt<=0;end
   end
   // a new target-1 image (BEGIN) re-opens only through the original's word 325 again
   if(boot_image_target!=1)begin open_q<=0;gcnt<=0;end
  end
  assign setup_ready=o_setup&&!x_fault;
  always @*begin
   layer_we=o_lw||g_we;
   layer_addr=g_we?g_a:((o_lw&&o_la==9'd326)?9'd470:o_la);
   layer_data=g_we?g_d:o_ld;
   fault=o_fault||x_fault;fault_code=o_fc|x_fc;
  end
 end endgenerate
endmodule

// Independent reference: delay complete legacy write interface one boot edge.
module qkd_static_kv_boot_dispatch_mu #(parameter integer MUT=0,parameter integer DIECFG=0,parameter integer NRST=43,parameter integer LINKCFG=0,parameter integer ESCFG=0,parameter integer DIECAP=0,parameter integer MU=1,parameter integer WMUT=0,parameter integer SRQ=0,parameter integer DSTG=0)(
 input wire ck,rst_n,input wire[142:0]boot_pr,input wire[3:0]boot_image_target,
 input wire boot_image_ready,boot_image_fault,input wire[15:0]boot_image_epoch,
 input wire[63:0]boot_image_digest,input wire execution_active,
 input wire[159:0]sink_applied,input wire[2:0]local_configured,input wire sink_fault,
 input wire diecfg_sealed,diecfg_fault,
 output wire layer_we,output wire[8:0]layer_addr,output wire[63:0]layer_data,
 output wire writer_we,output wire[7:0]writer_addr,output wire[63:0]writer_data,
 output wire ownership_we,output wire[1:0]ownership_addr,output wire[31:0]ownership_data,
 output wire[31:0]landing_we,front_we,output wire[7:0]group_addr,output wire[63:0]group_data,
 output wire[127:0]controller_we,output wire[7:0]controller_addr,output wire[63:0]controller_data,
 output wire[127:0]controller_last,output wire[31:0]front_last,
 output wire diecfg_we,output wire[7:0]diecfg_addr,output wire[63:0]diecfg_data,
 output wire link_cfg_tx_we,link_cfg_rx_we,output wire[5:0]link_cfg_addr,output wire[31:0]link_cfg_data,
 output wire es_cfg_we,output wire[7:0]es_cfg_addr,output wire[63:0]es_cfg_data,
 output wire setup_ready,output wire fault,output wire[7:0]fault_code,
 output wire[15:0]installed_epoch,output wire[63:0]installed_isa_digest
);
 wire r_layer_we;
 wire[8:0] r_layer_addr;
 wire[63:0] r_layer_data;
 wire r_writer_we;
 wire[7:0] r_writer_addr;
 wire[63:0] r_writer_data;
 wire r_ownership_we;
 wire[1:0] r_ownership_addr;
 wire[31:0] r_ownership_data;
 wire[31:0] r_landing_we;
 wire[31:0] r_front_we;
 wire[7:0] r_group_addr;
 wire[63:0] r_group_data;
 wire[127:0] r_controller_we;
 wire[7:0] r_controller_addr;
 wire[63:0] r_controller_data;
 wire[127:0] r_controller_last;
 wire[31:0] r_front_last;
 wire r_diecfg_we;
 wire[7:0] r_diecfg_addr;
 wire[63:0] r_diecfg_data;
 wire r_link_cfg_tx_we;
 wire r_link_cfg_rx_we;
 wire[5:0] r_link_cfg_addr;
 wire[31:0] r_link_cfg_data;
 wire r_es_cfg_we;
 wire[7:0] r_es_cfg_addr;
 wire[63:0] r_es_cfg_data;
 wire r_setup_ready;
 wire r_fault;
 wire[7:0] r_fault_code;
 wire[15:0] r_installed_epoch;
 wire[63:0] r_installed_isa_digest;
 qkd_static_kv_boot_dispatch_mu_raw #(.MUT(MUT),.DIECFG(DIECFG),.NRST(NRST),.LINKCFG(LINKCFG),.ESCFG(ESCFG),.DIECAP(DIECAP),.MU(MU),.WMUT(WMUT),.SRQ(SRQ)) u_raw(.ck(ck),.rst_n(rst_n),.boot_pr(boot_pr),.boot_image_target(boot_image_target),.boot_image_ready(boot_image_ready),.boot_image_fault(boot_image_fault),.boot_image_epoch(boot_image_epoch),.boot_image_digest(boot_image_digest),.execution_active(execution_active),.sink_applied(sink_applied),.local_configured(local_configured),.sink_fault(sink_fault),.diecfg_sealed(diecfg_sealed),.diecfg_fault(diecfg_fault),.layer_we(r_layer_we),.layer_addr(r_layer_addr),.layer_data(r_layer_data),.writer_we(r_writer_we),.writer_addr(r_writer_addr),.writer_data(r_writer_data),.ownership_we(r_ownership_we),.ownership_addr(r_ownership_addr),.ownership_data(r_ownership_data),.landing_we(r_landing_we),.front_we(r_front_we),.group_addr(r_group_addr),.group_data(r_group_data),.controller_we(r_controller_we),.controller_addr(r_controller_addr),.controller_data(r_controller_data),.controller_last(r_controller_last),.front_last(r_front_last),.diecfg_we(r_diecfg_we),.diecfg_addr(r_diecfg_addr),.diecfg_data(r_diecfg_data),.link_cfg_tx_we(r_link_cfg_tx_we),.link_cfg_rx_we(r_link_cfg_rx_we),.link_cfg_addr(r_link_cfg_addr),.link_cfg_data(r_link_cfg_data),.es_cfg_we(r_es_cfg_we),.es_cfg_addr(r_es_cfg_addr),.es_cfg_data(r_es_cfg_data),.setup_ready(r_setup_ready),.fault(r_fault),.fault_code(r_fault_code),.installed_epoch(r_installed_epoch),.installed_isa_digest(r_installed_isa_digest));
 generate if(DSTG!=0)begin:g_layer_we reg q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_layer_we;assign layer_we=q;end else assign layer_we=r_layer_we;endgenerate
 generate if(DSTG!=0)begin:g_layer_addr reg[8:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_layer_addr;assign layer_addr=q;end else assign layer_addr=r_layer_addr;endgenerate
 generate if(DSTG!=0)begin:g_layer_data reg[63:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_layer_data;assign layer_data=q;end else assign layer_data=r_layer_data;endgenerate
 generate if(DSTG!=0)begin:g_writer_we reg q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_writer_we;assign writer_we=q;end else assign writer_we=r_writer_we;endgenerate
 generate if(DSTG!=0)begin:g_writer_addr reg[7:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_writer_addr;assign writer_addr=q;end else assign writer_addr=r_writer_addr;endgenerate
 generate if(DSTG!=0)begin:g_writer_data reg[63:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_writer_data;assign writer_data=q;end else assign writer_data=r_writer_data;endgenerate
 generate if(DSTG!=0)begin:g_ownership_we reg q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_ownership_we;assign ownership_we=q;end else assign ownership_we=r_ownership_we;endgenerate
 generate if(DSTG!=0)begin:g_ownership_addr reg[1:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_ownership_addr;assign ownership_addr=q;end else assign ownership_addr=r_ownership_addr;endgenerate
 generate if(DSTG!=0)begin:g_ownership_data reg[31:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_ownership_data;assign ownership_data=q;end else assign ownership_data=r_ownership_data;endgenerate
 generate if(DSTG!=0)begin:g_landing_we reg[31:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_landing_we;assign landing_we=q;end else assign landing_we=r_landing_we;endgenerate
 generate if(DSTG!=0)begin:g_front_we reg[31:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_front_we;assign front_we=q;end else assign front_we=r_front_we;endgenerate
 generate if(DSTG!=0)begin:g_group_addr reg[7:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_group_addr;assign group_addr=q;end else assign group_addr=r_group_addr;endgenerate
 generate if(DSTG!=0)begin:g_group_data reg[63:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_group_data;assign group_data=q;end else assign group_data=r_group_data;endgenerate
 generate if(DSTG!=0)begin:g_controller_we reg[127:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_controller_we;assign controller_we=q;end else assign controller_we=r_controller_we;endgenerate
 generate if(DSTG!=0)begin:g_controller_addr reg[7:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_controller_addr;assign controller_addr=q;end else assign controller_addr=r_controller_addr;endgenerate
 generate if(DSTG!=0)begin:g_controller_data reg[63:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_controller_data;assign controller_data=q;end else assign controller_data=r_controller_data;endgenerate
 generate if(DSTG!=0)begin:g_controller_last reg[127:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_controller_last;assign controller_last=q;end else assign controller_last=r_controller_last;endgenerate
 generate if(DSTG!=0)begin:g_front_last reg[31:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_front_last;assign front_last=q;end else assign front_last=r_front_last;endgenerate
 generate if(DSTG!=0)begin:g_diecfg_we reg q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_diecfg_we;assign diecfg_we=q;end else assign diecfg_we=r_diecfg_we;endgenerate
 generate if(DSTG!=0)begin:g_diecfg_addr reg[7:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_diecfg_addr;assign diecfg_addr=q;end else assign diecfg_addr=r_diecfg_addr;endgenerate
 generate if(DSTG!=0)begin:g_diecfg_data reg[63:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_diecfg_data;assign diecfg_data=q;end else assign diecfg_data=r_diecfg_data;endgenerate
 generate if(DSTG!=0)begin:g_link_cfg_tx_we reg q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_link_cfg_tx_we;assign link_cfg_tx_we=q;end else assign link_cfg_tx_we=r_link_cfg_tx_we;endgenerate
 generate if(DSTG!=0)begin:g_link_cfg_rx_we reg q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_link_cfg_rx_we;assign link_cfg_rx_we=q;end else assign link_cfg_rx_we=r_link_cfg_rx_we;endgenerate
 generate if(DSTG!=0)begin:g_link_cfg_addr reg[5:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_link_cfg_addr;assign link_cfg_addr=q;end else assign link_cfg_addr=r_link_cfg_addr;endgenerate
 generate if(DSTG!=0)begin:g_link_cfg_data reg[31:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_link_cfg_data;assign link_cfg_data=q;end else assign link_cfg_data=r_link_cfg_data;endgenerate
 generate if(DSTG!=0)begin:g_es_cfg_we reg q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_es_cfg_we;assign es_cfg_we=q;end else assign es_cfg_we=r_es_cfg_we;endgenerate
 generate if(DSTG!=0)begin:g_es_cfg_addr reg[7:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_es_cfg_addr;assign es_cfg_addr=q;end else assign es_cfg_addr=r_es_cfg_addr;endgenerate
 generate if(DSTG!=0)begin:g_es_cfg_data reg[63:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_es_cfg_data;assign es_cfg_data=q;end else assign es_cfg_data=r_es_cfg_data;endgenerate
 assign setup_ready=r_setup_ready;
 assign fault=r_fault;
 assign fault_code=r_fault_code;
 assign installed_epoch=r_installed_epoch;
 generate if(DSTG!=0)begin:g_installed_isa_digest reg[63:0] q; always @(posedge ck or negedge rst_n)if(!rst_n)q<=0;else q<=r_installed_isa_digest;assign installed_isa_digest=q;end else assign installed_isa_digest=r_installed_isa_digest;endgenerate
endmodule
