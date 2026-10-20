`timescale 1ns/1ps
// Initialization-only consumer of the ACTUAL target-aware authenticated HOST
// loader replay. Configurations are installed once after reset, targets1..9,
// then the ISA target0. No input from received data controls normal token issue.
// All HBM-facing cfg outputs here are CORE-domain source pins: they MUST pass
// actual boot CDC queues before reaching their independent HBM clock entries.
// sink_applied is the actual terminal application acknowledgement from those
// queues (including seal acceptance age), never a compiler prediction.
// KVJ-A 10-17 successor (qkd_static_kv_boot_cdc join): front_last[g] marks the
// last (6th, local address 5) target-5 word of front group g, so the front
// calendar's HAS_SEAL=0 boot CDC seals its source and reaches applied (before,
// a front CDC never applied and setup_ready never rose). controller_addr is the
// CDC's 8-bit cfg_addr ({3'b0, local 0..31}). sink_applied order is
// [31:0] = front group 8*stack+g, [159:32] = PC 32*(target-6)+pc; only the AND
// is used. MUT4 = the pre-successor behaviour (front_last never asserted).
// KVJ-F 10-17 (coordinator 0da (d): functional config straps REJECTED; ECTL cfg and the regional reset release delays
// come from the boot load): DIECFG=1 adds the PRE-BOOT image target 10 (die configuration, 32 + NRST + 1 words) for
// qkd_kv_die_cfg, the POR-domain holder of the ECTL a/b/c cfg words and the qkd_rst_region release delays.  Target 10 is
// accepted only as the first image after reset (nothing installed, target 1 expected): pass 1 (POR, unaligned first
// release with dly 0) loads it; the HOST then re-asserts and releases the functional resets (now aligned by the loaded
// delays; the die cfg keeps them, POR-reset only) and replays targets 1..9 then 0.  setup_ready also requires the die
// cfg sealed; its fault joins the sink fault.  DIECFG=0 is the KVJ-A successor unchanged (new ports unused / 0).
// KVJ-SMALL 10-17 (gap item 12: the static D2D link end's cfg_tx_we / cfg_rx_we / cfg_addr / cfg_data had no producer):
// LINKCFG=1 adds boot image target 11, the KV link-end calendar image (2*32+2 = 66 words), installed after target 9 and
// before the ISA target 0 (order 1..9, 11, 0).  Word a (data[31:0], data[63:32] must be 0, else fault code 5) is written
// in exactly the order of the calendar sequencer's init stream (ot_qwen_d2d_cal_seq): a = 2i -> TX entry i, a = 2i+1 ->
// RX entry i (i = 0..31), a = 64 -> TX segment-1 base (cfg_addr 6'b100000), a = 65 -> RX segment-1 base.  The bases are
// the image's INITIAL bases (the admission segment on the KV die, ADM=1).  The registered link_cfg_* outputs feed the link
// end's (pin-registered) cfg port; the end itself refuses a cfg write while its calendar runs.  setup_ready also needs
// target 11 installed.  LINKCFG=0 = unchanged (target 11 refused, code 3; link_cfg_* constant 0).  MUT 5: TX/RX swapped,
// MUT 6: the segment-1 bases written into entry 0 (bench mutants).
// KVJ-SMALL b2 10-17 (KVJ-C3 open: the shared boot bus of qkd_kv_es_fan_root + qkd_embedding_static_join4_cal, 6 ports
// cfg_we/cfg_addr/cfg_data x2, had no producer): ESCFG=1 adds targets 12 and 13, installed after target 9 (and 11) and
// before the ISA target 0 (order 1..9, [11,] 12, 13, 0), on ONE registered bus es_cfg_we / es_cfg_addr[7:0] /
// es_cfg_data[63:0] that the die fans to both C3 cfg ports (each pin-registers it; each takes only its own cfg_data[63:62]).
// Target 12 = the PC players' constants, 1024 words, word a = {stack[1:0], pc[4:0], reg[2:0]} -> es_cfg_addr = a[7:0],
// data passed verbatim; data[63:62] != 0, data[61:18] != 0 or data[17:16] != a[9:8] -> fault code 5.  Target 13 = the
// join4 beat calendar, 8 words (segment a; unused segments len 0), es_cfg_addr = a; data[63:62] != 1 or data[61:24] != 0
// -> fault code 5.  Image = tools/qwen_kv_die/kvjc3_pc_chain.boot_words (kv_static_programme.es_cfg_words).  setup_ready
// also needs targets 12 and 13 installed.  ESCFG=0 = unchanged (12/13 refused, code 3; es_cfg_* constant 0).
// MUT 7: target-12 address with pc and reg swapped; MUT 8: target-13 segment 1 dropped (bench mutants).
// RTL-BUILD-KV/FAULT 10-18 (P8): DIECAP=1 = the die cfg's capability word (qkd_kv_die_cfg CAP=1: word 32+NRST, data[0] =
// the fused attention-programme capability): target 10 is 32 + NRST + 2 words.  DIECAP=0 = unchanged.
module qkd_static_kv_boot_dispatch #(parameter integer MUT=0,parameter integer DIECFG=0,parameter integer NRST=43,parameter integer LINKCFG=0,parameter integer ESCFG=0,parameter integer DIECAP=0)(
 input wire ck,rst_n,input wire[142:0]boot_pr,input wire[3:0]boot_image_target,
 input wire boot_image_ready,boot_image_fault,input wire[15:0]boot_image_epoch,
 input wire[63:0]boot_image_digest,input wire execution_active,
 input wire[159:0]sink_applied,input wire[2:0]local_configured,input wire sink_fault,
 input wire diecfg_sealed,diecfg_fault,
 output reg layer_we,output reg[8:0]layer_addr,output reg[63:0]layer_data,
 output reg writer_we,output reg[7:0]writer_addr,output reg[63:0]writer_data,
 output reg ownership_we,output reg[1:0]ownership_addr,output reg[31:0]ownership_data,
 output reg[31:0]landing_we,front_we,output reg[7:0]group_addr,output reg[63:0]group_data,
 output reg[127:0]controller_we,output reg[7:0]controller_addr,output reg[63:0]controller_data,
 output reg[127:0]controller_last,output reg[31:0]front_last,
 output reg diecfg_we,output reg[7:0]diecfg_addr,output reg[63:0]diecfg_data,
 output reg link_cfg_tx_we,link_cfg_rx_we,output reg[5:0]link_cfg_addr,output reg[31:0]link_cfg_data,
 output reg es_cfg_we,output reg[7:0]es_cfg_addr,output reg[63:0]es_cfg_data,
 output wire setup_ready,output reg fault,output reg[7:0]fault_code,
 output reg[15:0]installed_epoch,output reg[63:0]installed_isa_digest
);
 reg[3:0]expected_target;reg[10:0]next_word;reg ready_q;reg isa_seen;
 reg[8:0]installed;reg have_epoch;reg diecfg_done;reg linkcfg_done;reg es12_done,es13_done;
 wire[9:0]addr=boot_pr[73:64];wire[63:0]data=boot_pr[63:0];
 function automatic[10:0]word_count(input[3:0]t);
 case(t)1:word_count=327;2:word_count=181;3:word_count=4;4,5:word_count=192;
 6,7,8,9:word_count=1024;10:word_count=(DIECFG!=0)?11'(32+NRST+1+((DIECAP!=0)?1:0)):11'd0;11:word_count=(LINKCFG!=0)?11'd66:11'd0;12:word_count=(ESCFG!=0)?11'd1024:11'd0;13:word_count=(ESCFG!=0)?11'd8:11'd0;default:word_count=0;endcase
 endfunction
 // Registered HOST output is consumed one edge later by the real cfg inputs.
 // Final ISA readiness remains tied to the actual loader, so a new BEGIN drops
 // setup_ready immediately even after the first successful setup.
 assign setup_ready=(&installed)&&((MUT==3)||(&sink_applied))&&(&local_configured)&&isa_seen&&boot_image_ready&&boot_image_target==0&&!boot_image_fault&&!sink_fault&&!fault&&((DIECFG==0)||diecfg_sealed)&&((LINKCFG==0)||linkcfg_done)&&((ESCFG==0)||(es12_done&&es13_done));
 integer group_index,pc_index;
 // target 10 (DIECFG): the pre-boot die configuration image, only before anything else is installed
 wire t10=(DIECFG!=0)&&boot_image_target==10;
 wire t10_ok=(installed==0)&&(expected_target==1)&&!diecfg_done;
 wire t11=(LINKCFG!=0)&&boot_image_target==11;
 wire t12=(ESCFG!=0)&&boot_image_target==12;
 wire t13=(ESCFG!=0)&&boot_image_target==13;
 wire[3:0]after9=(LINKCFG!=0)?4'd11:(ESCFG!=0)?4'd12:4'd0;
 wire t_ok=t10?t10_ok:((MUT==1||boot_image_target==expected_target)&&(boot_image_target<=9||t11||t12||t13));
 always @(posedge ck or negedge rst_n)begin
 if(!rst_n)begin
  expected_target<=1;next_word<=0;ready_q<=0;isa_seen<=0;installed<=0;have_epoch<=0;
  installed_epoch<=0;installed_isa_digest<=0;fault<=0;fault_code<=0;
  layer_we<=0;writer_we<=0;ownership_we<=0;landing_we<=0;front_we<=0;controller_we<=0;controller_last<=0;front_last<=0;
  layer_addr<=0;layer_data<=0;writer_addr<=0;writer_data<=0;ownership_addr<=0;ownership_data<=0;
  diecfg_we<=0;diecfg_addr<=0;diecfg_data<=0;diecfg_done<=0;
  link_cfg_tx_we<=0;link_cfg_rx_we<=0;link_cfg_addr<=0;link_cfg_data<=0;linkcfg_done<=0;
  es_cfg_we<=0;es_cfg_addr<=0;es_cfg_data<=0;es12_done<=0;es13_done<=0;
  group_addr<=0;group_data<=0;controller_addr<=0;controller_data<=0;
 end else begin
  ready_q<=boot_image_ready;
  layer_we<=0;writer_we<=0;ownership_we<=0;landing_we<=0;front_we<=0;controller_we<=0;controller_last<=0;front_last<=0;diecfg_we<=0;link_cfg_tx_we<=0;link_cfg_rx_we<=0;es_cfg_we<=0;
  if(boot_image_fault||sink_fault||(DIECFG!=0&&diecfg_fault))begin fault<=1;fault_code[0]<=1;end
  if((boot_pr[74]||boot_pr[142])&&execution_active)begin fault<=1;fault_code[1]<=1;end
  if(boot_pr[142]&&boot_image_target!=0)begin fault<=1;fault_code[2]<=1;end
  if(boot_pr[74]&&boot_image_target!=0&&!fault&&!execution_active)begin
   if(!t_ok||{1'b0,addr}!=next_word||next_word>=word_count(boot_image_target))begin
    fault<=1;fault_code[3]<=1;
   end else if(have_epoch&&boot_image_epoch!=installed_epoch)begin fault<=1;fault_code[4]<=1;end
   else begin
    if(!have_epoch)begin have_epoch<=1;installed_epoch<=boot_image_epoch;end
    next_word<=next_word+1'b1;
    case(boot_image_target)
    1:begin layer_we<=1;layer_addr<=addr[8:0];layer_data<=data;end
    2:begin writer_we<=1;writer_addr<=addr[7:0];writer_data<=data;end
    3:begin
      if(data[63:32]!=0)begin fault<=1;fault_code[5]<=1;end
      else begin ownership_we<=1;ownership_addr<=addr[1:0];ownership_data<=data[31:0];end
    end
    4,5:begin
      group_index=int'(addr)/6;
      if(boot_image_target==4)landing_we<=32'b1<<group_index;
      else begin
       front_we<=32'b1<<group_index;
       if(MUT!=4&&int'(addr)%6==5)front_last<=32'b1<<group_index;
      end
      group_addr<=8'(int'(addr)%6);group_data<=data;
    end
    6,7,8,9:begin
      pc_index=32*(int'(boot_image_target)-6)+int'(addr[9:5]);
      if(MUT==2)pc_index=pc_index^1;
      controller_we<=128'b1<<pc_index;controller_addr<={3'b0,addr[4:0]};controller_data<=data;
      if(addr[4:0]==31)controller_last<=128'b1<<pc_index;
    end
    10:begin diecfg_we<=1;diecfg_addr<=addr[7:0];diecfg_data<=data;end
    11:begin
      if(data[63:32]!=0)begin fault<=1;fault_code[5]<=1;end
      else begin
       link_cfg_data<=data[31:0];
       if(addr<64)begin
        link_cfg_addr<={1'b0,addr[5:1]};
        link_cfg_tx_we<=(MUT==5)?addr[0]:!addr[0];link_cfg_rx_we<=(MUT==5)?!addr[0]:addr[0];
       end else begin
        link_cfg_addr<=(MUT==6)?6'd0:6'b100000;
        link_cfg_tx_we<=(addr==64);link_cfg_rx_we<=(addr==65);
       end
      end
    end
    12:begin
      if(data[63:62]!=0||data[61:18]!=0||data[17:16]!=addr[9:8])begin fault<=1;fault_code[5]<=1;end
      else begin es_cfg_we<=1;es_cfg_addr<=(MUT==7)?{addr[2:0],addr[7:3]}:addr[7:0];es_cfg_data<=data;end
    end
    13:begin
      if(data[63:62]!=2'd1||data[61:24]!=0)begin fault<=1;fault_code[5]<=1;end
      else begin es_cfg_we<=!(MUT==8&&addr[2:0]==1);es_cfg_addr<={5'd0,addr[2:0]};es_cfg_data<=data;end
    end
    default:begin fault<=1;fault_code[3]<=1;end
    endcase
   end
  end
  if(boot_image_ready&&!ready_q&&!fault)begin
   if(boot_image_target==0)begin
    if(expected_target!=0||!have_epoch||boot_image_epoch!=installed_epoch)begin fault<=1;fault_code[6]<=1;end
    else begin isa_seen<=1;installed_isa_digest<=boot_image_digest;end
   end else if(t10)begin
    if(!t10_ok||next_word!=word_count(10))begin fault<=1;fault_code[7]<=1;end
    else begin diecfg_done<=1;next_word<=0;end
   end else if(boot_image_target!=expected_target||next_word!=word_count(boot_image_target))begin fault<=1;fault_code[7]<=1;end
   else if(t11)begin linkcfg_done<=1;expected_target<=(ESCFG!=0)?4'd12:4'd0;next_word<=0;end
   else if(t12)begin es12_done<=1;expected_target<=4'd13;next_word<=0;end
   else if(t13)begin es13_done<=1;expected_target<=4'd0;next_word<=0;end
   else begin installed[boot_image_target-1'b1]<=1;expected_target<=(boot_image_target==9)?after9:expected_target+1'b1;next_word<=0;end
  end
 end
 end
endmodule
