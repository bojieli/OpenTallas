`timescale 1ns/1ps
// KV-CTL10 2026-10-20: copy of qkd_kv_ctl_s32_boot.sv (codex/kv-ctl3-native36-1020 b5d750822) with the modules renamed
// _s32 -> _c32 and ONE change: the dispatcher decodes boot_image_target once into kept one-hot wires (see tdec below),
// because the c32 tile has no face pin registers (the die charges 0 tile pin edges) and the port net drove 34 loads.
// KV-CTL3 10-20 (fork S32-D2; PRE-GATE NATIVE CENSUS, no driver > 32 mapped loads): census successors of the KV boot
// dispatcher as NEW modules (the originals stay byte-identical):
//   qkd_static_kv_boot_dispatch_s32    = qkd_static_kv_boot_dispatch (same ports / params, same outputs on every edge)
//   qkd_static_kv_boot_dispatch_mu_s32 = qkd_static_kv_boot_dispatch_mu around the _s32 dispatcher
// mu6c census (results/arch/kv_ctl3_1020/cls.txt): the word accept term (274 loads), the per-target data / address hold
// enables (34..143), the one-hot landing / front / controller strobe decodes feeding the o_hroot pins (53..138), the MU
// wrapper's g_we layer-bus select (147) and its GAP word hold (136).  Structure (0 added edges):
//   * acc (the original's word-check else branch) -> 14 per-target accepts through ONE ot_s32_and leaf (rtl/lib/ot_s32_cells.sv);
//   * every held register is written in <= 16-bit slices: next = ot_s32_sel(cond && rs_s[j], new, held), rs_s = KEPT copies
//     of the reset (identical D = rst_n), one per slice, so no select gate is shared and ABC cannot fold the condition;
//   * one-hot strobes: group-select leaves ot_s32_and(acc_t && group && rs_s[j], dec16) over shared 16-way decodes
//     (controller: groups {target - 6, addr[9]} x addr[8:5] (MUT 2: ^1); landing / front: groups gi[4] x gi[3:0], gi = addr/6).
// Lockstep vs the originals: rtl/test/mu_qwen_1018/run_kv_ctl_s32_d2.sh.
module qkd_static_kv_boot_dispatch_c32 #(parameter integer MUT=0,parameter integer DIECFG=0,parameter integer NRST=43,parameter integer LINKCFG=0,parameter integer ESCFG=0,parameter integer DIECAP=0,parameter integer SRQ=0,parameter integer RS=24)(
 input wire ck,rst_n,input wire[142:0]boot_pr,input wire[9:0]boot_addr_b,input wire[3:0]boot_image_target,
 input wire[4:0]boot_gix,input wire[2:0]boot_rem6,
 input wire boot_image_ready,boot_image_fault,input wire[15:0]boot_image_epoch,
 input wire[63:0]boot_image_digest,input wire execution_active,
 input wire[159:0]sink_applied,input wire[2:0]local_configured,input wire sink_fault,
 input wire diecfg_sealed,diecfg_fault,
 output reg layer_we,output wire[8:0]layer_addr,output wire[63:0]layer_data,
 output reg writer_we,output wire[7:0]writer_addr,output wire[63:0]writer_data,
 output reg ownership_we,output wire[1:0]ownership_addr,output wire[31:0]ownership_data,
 output wire[31:0]landing_we,front_we,output wire[7:0]group_addr,output wire[63:0]group_data,
 output wire[127:0]controller_we,output wire[7:0]controller_addr,output wire[63:0]controller_data,
 output wire[127:0]controller_last,output wire[31:0]front_last,
 output reg diecfg_we,output wire[7:0]diecfg_addr,output wire[63:0]diecfg_data,
 output reg link_cfg_tx_we,link_cfg_rx_we,output wire[5:0]link_cfg_addr,output wire[31:0]link_cfg_data,
 output reg es_cfg_we,output wire[7:0]es_cfg_addr,output wire[63:0]es_cfg_data,
 output wire setup_ready,output reg fault,output reg[7:0]fault_code,
 output reg[15:0]installed_epoch,output wire[63:0]installed_isa_digest
);
 reg[3:0]expected_target;reg[10:0]next_word;reg ready_q;reg isa_seen;
 reg[8:0]installed;reg have_epoch;reg diecfg_done;reg linkcfg_done;reg es12_done,es13_done;
 wire[9:0]addr=boot_pr[73:64];wire[63:0]data=boot_pr[63:0];
 // KV-CTL3 census: boot_addr_b = a second copy of the address field (the parent's seal re-address mux, duplicated):
 // the data / address-field consumers read it, the decode / compare / divide consumers read addr.
 wire[9:0]addr_b=boot_addr_b;
 function automatic[10:0]word_count(input[3:0]t);
 case(t)1:word_count=327;2:word_count=181;3:word_count=4;4,5:word_count=192;
 6,7,8,9:word_count=1024;10:word_count=(DIECFG!=0)?11'(32+NRST+1+((DIECAP!=0)?1:0)):11'd0;11:word_count=(LINKCFG!=0)?11'd66:11'd0;12:word_count=(ESCFG!=0)?11'd1024:11'd0;13:word_count=(ESCFG!=0)?11'd8:11'd0;default:word_count=0;endcase
 endfunction
 // KV-CTL10 10-20 (native census without face pin registers: the boot_image_target input PORT drove 33/34 mapped loads):
 // the target is decoded ONCE into KEPT one-hot wires (an ABC boundary) and every former target compare / case / index /
 // word_count(target) reads them (same function: tdec is one-hot over the 14 targets, target 14/15 = all zero = the original
 // default / out-of-range terms).  The port then feeds the 14 decoders, the expected_target compare and the MU wrapper only.
 // two-level predecode behind kept-hierarchy leaves (ABC boundary): the port bits feed only the leaf's 2-bit one-hots
 wire[3:0]t_hi,t_lo,e_hi,e_lo;
 qkd_kv_ctl_c32_tpre u_tpre(.t(boot_image_target),.hi(t_hi),.lo(t_lo));
 qkd_kv_ctl_c32_tpre u_epre(.t(expected_target),.hi(e_hi),.lo(e_lo));
 (* keep *) wire[13:0]tdec;
 (* keep *) wire[13:0]edec;
 genvar gi_;
 generate for(gi_=0;gi_<14;gi_=gi_+1)begin:g_td assign tdec[gi_]=t_hi[gi_/4]&&t_lo[gi_%4]; assign edec[gi_]=e_hi[gi_/4]&&e_lo[gi_%4]; end endgenerate
 // target == expected_target (expected_target <= 13; target 14 / 15 never equals it): one-hot match
 wire t_eq_e=|(tdec&edec);
 wire[10:0]wc_t=({11{tdec[1]}}&11'd327)|({11{tdec[2]}}&11'd181)|({11{tdec[3]}}&11'd4)|({11{tdec[4]|tdec[5]}}&11'd192)|
  ({11{tdec[6]|tdec[7]|tdec[8]|tdec[9]}}&11'd1024)|({11{tdec[10]}}&word_count(4'd10))|({11{tdec[11]}}&word_count(4'd11))|
  ({11{tdec[12]}}&word_count(4'd12))|({11{tdec[13]}}&word_count(4'd13));
 // Registered HOST output is consumed one edge later by the real cfg inputs.
 // Final ISA readiness remains tied to the actual loader, so a new BEGIN drops
 // setup_ready immediately even after the first successful setup.
 // KV-CTL mu2 10-19: SRQ=2 (MU release view of qkd_kvs_ctl; SRQ=0 = unchanged) = setup_ready exactly 2 edges after
 // the combinational term: stage 1 registers the internal reduction (160 applied + installed + local + seals) and the
 // pin terms separately, stage 2 ANDs them.  p1-d7af727c1: boot_image_target pin -> setup_ready pin was a -698 ps
 // in->out path.  setup_ready is a boot status (HOST reads it before go), not a production edge.
 wire setup_int=(&installed)&&((MUT==3)||(&sink_applied))&&(&local_configured)&&isa_seen&&!sink_fault&&!fault&&((DIECFG==0)||diecfg_sealed)&&((LINKCFG==0)||linkcfg_done)&&((ESCFG==0)||(es12_done&&es13_done));
 wire setup_ext=boot_image_ready&&tdec[0]&&!boot_image_fault;
 wire setup_c=setup_int&&setup_ext;
 generate if(SRQ==0)begin:g_sr0 assign setup_ready=setup_c; end
 else begin:g_sr2
  reg sr_int_q,sr_ext_q,sr_q;
  always @(posedge ck or negedge rst_n)
   if(!rst_n)begin sr_int_q<=0;sr_ext_q<=0;sr_q<=0;end
   else begin sr_int_q<=setup_int;sr_ext_q<=setup_ext;sr_q<=sr_int_q&&sr_ext_q;end
  assign setup_ready=sr_q;
 end endgenerate
 integer group_index,pc_index;
 // target 10 (DIECFG): the pre-boot die configuration image, only before anything else is installed
 wire t10=(DIECFG!=0)&&tdec[10];
 wire t10_ok=(installed==0)&&(expected_target==1)&&!diecfg_done;
 wire t11=(LINKCFG!=0)&&tdec[11];
 wire t12=(ESCFG!=0)&&tdec[12];
 wire t13=(ESCFG!=0)&&tdec[13];
 wire[3:0]after9=(LINKCFG!=0)?4'd11:(ESCFG!=0)?4'd12:4'd0;
 wire t_ok=t10?t10_ok:((MUT==1||t_eq_e)&&((|tdec[9:0])||t11||t12||t13));
 // ---- accept term (the original's else-branch of the word checks) and per-target accepts ----
 wire tv=boot_pr[74]&&!tdec[0]&&!fault&&!execution_active;
 wire wbad=!t_ok||{1'b0,addr}!=next_word||next_word>=wc_t;
 wire ebad=have_epoch&&boot_image_epoch!=installed_epoch;
 wire acc=tv&&!wbad&&!ebad;
 wire[13:0]acc_t;
 ot_s32_and #(.W(14)) u_acc(.s(acc),.a(tdec),.y(acc_t));
 wire ok3=acc_t[3]&&data[63:32]==0;
 wire ok11=acc_t[11]&&data[63:32]==0;
 wire ok12=acc_t[12]&&!(data[63:62]!=0||data[61:18]!=0||data[17:16]!=addr[9:8]);
 wire ok13=acc_t[13]&&!(data[63:62]!=2'd1||data[61:24]!=0);
 wire isa_w=boot_image_ready&&!ready_q&&!fault&&tdec[0]&&!(expected_target!=0||!have_epoch||boot_image_epoch!=installed_epoch);
 // ---- slice literals: kept copies of the reset (identical D = rst_n) ----
 (* keep *) reg[RS-1:0]rs_s;
 always @(posedge ck)rs_s<={RS{rst_n}};
 // ---- held registers, sliced <= 16 bits (ot_s32_sel leaves, distinct select nets) ----
 // KV-CTL12 10-21 (gate222038 c32a/b: boot_image_epoch -> o_hroot 1037 ps, the /6 chain u_gix ~350 ps in series behind the
 // MU seal re-address mux): the parent computes addr/6 and addr%6 of the RAW address in parallel with the seal accept and
 // selects the constants of word 326 (54 r 2) on an accepted seal.  Same values as addr/6, addr%6 of the re-addressed word.
 wire[9:0]a6={7'd0,boot_rem6};
 wire[5:0]lk_a=(addr_b<64)?{1'b0,addr_b[5:1]}:((MUT==6)?6'd0:6'b100000);
 wire[7:0]es_a=ok13?{5'd0,addr_b[2:0]}:((MUT==7)?{addr_b[2:0],addr_b[7:3]}:addr_b[7:0]);
 wire[72:0]s_layer={addr_b[8:0],data};
 reg[72:0]layer_q;wire[72:0]layer_n;
 generate for(gi_=0;gi_<5;gi_=gi_+1)begin:g_layer
  localparam integer LO=16*gi_,W=((73-LO)<16)?(73-LO):16;
  ot_s32_sel #(.W(W)) u_s(.s((acc_t[1])&&rs_s[(0+gi_)%RS]),.a(s_layer[LO+:W]),.b(layer_q[LO+:W]),.y(layer_n[LO+:W]));
 end endgenerate
 always @(posedge ck or negedge rst_n)if(!rst_n)layer_q<=0;else layer_q<=layer_n;
 wire[71:0]s_writer={addr_b[7:0],data};
 reg[71:0]writer_q;wire[71:0]writer_n;
 generate for(gi_=0;gi_<5;gi_=gi_+1)begin:g_writer
  localparam integer LO=16*gi_,W=((72-LO)<16)?(72-LO):16;
  ot_s32_sel #(.W(W)) u_s(.s((acc_t[2])&&rs_s[(5+gi_)%RS]),.a(s_writer[LO+:W]),.b(writer_q[LO+:W]),.y(writer_n[LO+:W]));
 end endgenerate
 always @(posedge ck or negedge rst_n)if(!rst_n)writer_q<=0;else writer_q<=writer_n;
 wire[33:0]s_own={addr_b[1:0],data[31:0]};
 reg[33:0]own_q;wire[33:0]own_n;
 generate for(gi_=0;gi_<3;gi_=gi_+1)begin:g_own
  localparam integer LO=16*gi_,W=((34-LO)<16)?(34-LO):16;
  ot_s32_sel #(.W(W)) u_s(.s((ok3)&&rs_s[(10+gi_)%RS]),.a(s_own[LO+:W]),.b(own_q[LO+:W]),.y(own_n[LO+:W]));
 end endgenerate
 always @(posedge ck or negedge rst_n)if(!rst_n)own_q<=0;else own_q<=own_n;
 wire[71:0]s_group={a6[7:0],data};
 reg[71:0]group_q;wire[71:0]group_n;
 generate for(gi_=0;gi_<5;gi_=gi_+1)begin:g_group
  localparam integer LO=16*gi_,W=((72-LO)<16)?(72-LO):16;
  ot_s32_sel #(.W(W)) u_s(.s((acc_t[4]||acc_t[5])&&rs_s[(13+gi_)%RS]),.a(s_group[LO+:W]),.b(group_q[LO+:W]),.y(group_n[LO+:W]));
 end endgenerate
 always @(posedge ck or negedge rst_n)if(!rst_n)group_q<=0;else group_q<=group_n;
 wire[71:0]s_ctl={3'b0,addr_b[4:0],data};
 reg[71:0]ctl_q;wire[71:0]ctl_n;
 generate for(gi_=0;gi_<5;gi_=gi_+1)begin:g_ctl
  localparam integer LO=16*gi_,W=((72-LO)<16)?(72-LO):16;
  ot_s32_sel #(.W(W)) u_s(.s((acc_t[6]||acc_t[7]||acc_t[8]||acc_t[9])&&rs_s[(18+gi_)%RS]),.a(s_ctl[LO+:W]),.b(ctl_q[LO+:W]),.y(ctl_n[LO+:W]));
 end endgenerate
 always @(posedge ck or negedge rst_n)if(!rst_n)ctl_q<=0;else ctl_q<=ctl_n;
 wire[71:0]s_dcf={addr_b[7:0],data};
 reg[71:0]dcf_q;wire[71:0]dcf_n;
 generate for(gi_=0;gi_<5;gi_=gi_+1)begin:g_dcf
  localparam integer LO=16*gi_,W=((72-LO)<16)?(72-LO):16;
  ot_s32_sel #(.W(W)) u_s(.s((acc_t[10])&&rs_s[(23+gi_)%RS]),.a(s_dcf[LO+:W]),.b(dcf_q[LO+:W]),.y(dcf_n[LO+:W]));
 end endgenerate
 always @(posedge ck or negedge rst_n)if(!rst_n)dcf_q<=0;else dcf_q<=dcf_n;
 wire[37:0]s_lk={lk_a,data[31:0]};
 reg[37:0]lk_q;wire[37:0]lk_n;
 generate for(gi_=0;gi_<3;gi_=gi_+1)begin:g_lk
  localparam integer LO=16*gi_,W=((38-LO)<16)?(38-LO):16;
  ot_s32_sel #(.W(W)) u_s(.s((ok11)&&rs_s[(28+gi_)%RS]),.a(s_lk[LO+:W]),.b(lk_q[LO+:W]),.y(lk_n[LO+:W]));
 end endgenerate
 always @(posedge ck or negedge rst_n)if(!rst_n)lk_q<=0;else lk_q<=lk_n;
 wire[71:0]s_es={es_a,data};
 reg[71:0]es_q;wire[71:0]es_n;
 generate for(gi_=0;gi_<5;gi_=gi_+1)begin:g_es
  localparam integer LO=16*gi_,W=((72-LO)<16)?(72-LO):16;
  ot_s32_sel #(.W(W)) u_s(.s((ok12||ok13)&&rs_s[(31+gi_)%RS]),.a(s_es[LO+:W]),.b(es_q[LO+:W]),.y(es_n[LO+:W]));
 end endgenerate
 always @(posedge ck or negedge rst_n)if(!rst_n)es_q<=0;else es_q<=es_n;
 wire[63:0]s_isa=boot_image_digest;
 reg[63:0]isa_q;wire[63:0]isa_n;
 generate for(gi_=0;gi_<4;gi_=gi_+1)begin:g_isa
  localparam integer LO=16*gi_,W=((64-LO)<16)?(64-LO):16;
  ot_s32_sel #(.W(W)) u_s(.s((isa_w)&&rs_s[(36+gi_)%RS]),.a(s_isa[LO+:W]),.b(isa_q[LO+:W]),.y(isa_n[LO+:W]));
 end endgenerate
 always @(posedge ck or negedge rst_n)if(!rst_n)isa_q<=0;else isa_q<=isa_n;
 assign layer_addr=layer_q[72:64];assign layer_data=layer_q[63:0];
 assign writer_addr=writer_q[71:64];assign writer_data=writer_q[63:0];
 assign ownership_addr=own_q[33:32];assign ownership_data=own_q[31:0];
 assign group_addr=group_q[71:64];assign group_data=group_q[63:0];
 assign controller_addr=ctl_q[71:64];assign controller_data=ctl_q[63:0];
 assign diecfg_addr=dcf_q[71:64];assign diecfg_data=dcf_q[63:0];
 assign link_cfg_addr=lk_q[37:32];assign link_cfg_data=lk_q[31:0];
 assign es_cfg_addr=es_q[71:64];assign es_cfg_data=es_q[63:0];
 assign installed_isa_digest=isa_q;
 // ---- one-hot write strobes (no hold: 0 unless a word is accepted): group-select leaves over shared 16-way decodes ----
 // Keep each small remainder step separate: monolithic /6 remapping gave addr[9] 37 loads.
 wire[4:0]gix=boot_gix;
 wire[15:0]dg,dp;
 generate for(gi_=0;gi_<16;gi_=gi_+1)begin:g_dec
  assign dg[gi_]=gix[3:0]==gi_;
  assign dp[gi_]={addr[8:6],addr[5]^(MUT==2)}==gi_;
 end endgenerate
 wire l5=(MUT!=4)&&boot_rem6==3'd5;
 wire c31=addr[4:0]==31;
 reg[31:0]lw_q,fw_q,fl_q;reg[127:0]cw_q,cl_q;
 wire[31:0]lw_n,fw_n,fl_n;wire[127:0]cw_n,cl_n;
 generate for(gi_=0;gi_<2;gi_=gi_+1)begin:g_lf
  ot_s32_and #(.W(16)) u_l(.s(acc_t[4]&&gix[4]==gi_&&rs_s[(40+gi_)%RS]),.a(dg),.y(lw_n[16*gi_+:16]));
  ot_s32_and #(.W(16)) u_f(.s(acc_t[5]&&gix[4]==gi_&&rs_s[(42+gi_)%RS]),.a(dg),.y(fw_n[16*gi_+:16]));
  ot_s32_and #(.W(16)) u_x(.s(acc_t[5]&&l5&&gix[4]==gi_&&rs_s[(44+gi_)%RS]),.a(dg),.y(fl_n[16*gi_+:16]));
 end
 for(gi_=0;gi_<8;gi_=gi_+1)begin:g_cw
  localparam integer T=6+gi_/2,H=gi_%2;
  ot_s32_and #(.W(16)) u_w(.s(acc_t[T]&&addr[9]==H&&rs_s[(46+gi_)%RS]),.a(dp),.y(cw_n[16*gi_+:16]));
  ot_s32_and #(.W(16)) u_l(.s(acc_t[T]&&c31&&addr[9]==H&&rs_s[(54+gi_)%RS]),.a(dp),.y(cl_n[16*gi_+:16]));
 end endgenerate
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin lw_q<=0;fw_q<=0;fl_q<=0;cw_q<=0;cl_q<=0;end
  else begin lw_q<=lw_n;fw_q<=fw_n;fl_q<=fl_n;cw_q<=cw_n;cl_q<=cl_n;end
 assign landing_we=lw_q;assign front_we=fw_q;assign front_last=fl_q;assign controller_we=cw_q;assign controller_last=cl_q;
 // ---- control process (the original's, without the sliced registers) ----
 always @(posedge ck or negedge rst_n)begin
 if(!rst_n)begin
  expected_target<=1;next_word<=0;ready_q<=0;isa_seen<=0;installed<=0;have_epoch<=0;
  installed_epoch<=0;fault<=0;fault_code<=0;
  layer_we<=0;writer_we<=0;ownership_we<=0;
  diecfg_we<=0;diecfg_done<=0;
  link_cfg_tx_we<=0;link_cfg_rx_we<=0;linkcfg_done<=0;
  es_cfg_we<=0;es12_done<=0;es13_done<=0;
 end else begin
  ready_q<=boot_image_ready;
  layer_we<=0;writer_we<=0;ownership_we<=0;diecfg_we<=0;link_cfg_tx_we<=0;link_cfg_rx_we<=0;es_cfg_we<=0;
  if(boot_image_fault||sink_fault||(DIECFG!=0&&diecfg_fault))begin fault<=1;fault_code[0]<=1;end
  if((boot_pr[74]||boot_pr[142])&&execution_active)begin fault<=1;fault_code[1]<=1;end
  if(boot_pr[142]&&!tdec[0])begin fault<=1;fault_code[2]<=1;end
  if(tv)begin
   if(wbad)begin
    fault<=1;fault_code[3]<=1;
   end else if(ebad)begin fault<=1;fault_code[4]<=1;end
   else begin
    if(!have_epoch)begin have_epoch<=1;installed_epoch<=boot_image_epoch;end
    next_word<=next_word+1'b1;
    case(1'b1)
    tdec[1]:layer_we<=1;
    tdec[2]:writer_we<=1;
    tdec[3]:begin
      if(data[63:32]!=0)begin fault<=1;fault_code[5]<=1;end
      else ownership_we<=1;
    end
    tdec[4],tdec[5],tdec[6],tdec[7],tdec[8],tdec[9]:;
    tdec[10]:diecfg_we<=1;
    tdec[11]:begin
      if(data[63:32]!=0)begin fault<=1;fault_code[5]<=1;end
      else begin
       if(addr<64)begin
        link_cfg_tx_we<=(MUT==5)?addr[0]:!addr[0];link_cfg_rx_we<=(MUT==5)?!addr[0]:addr[0];
       end else begin
        link_cfg_tx_we<=(addr==64);link_cfg_rx_we<=(addr==65);
       end
      end
    end
    tdec[12]:begin
      if(data[63:62]!=0||data[61:18]!=0||data[17:16]!=addr[9:8])begin fault<=1;fault_code[5]<=1;end
      else es_cfg_we<=1;
    end
    tdec[13]:begin
      if(data[63:62]!=2'd1||data[61:24]!=0)begin fault<=1;fault_code[5]<=1;end
      else es_cfg_we<=!(MUT==8&&addr[2:0]==1);
    end
    default:begin fault<=1;fault_code[3]<=1;end
    endcase
   end
  end
  if(boot_image_ready&&!ready_q&&!fault)begin
   if(tdec[0])begin
    if(expected_target!=0||!have_epoch||boot_image_epoch!=installed_epoch)begin fault<=1;fault_code[6]<=1;end
    else isa_seen<=1;
   end else if(t10)begin
    if(!t10_ok||next_word!=word_count(10))begin fault<=1;fault_code[7]<=1;end
    else begin diecfg_done<=1;next_word<=0;end
   end else if(!t_eq_e||next_word!=wc_t)begin fault<=1;fault_code[7]<=1;end
   else if(t11)begin linkcfg_done<=1;expected_target<=(ESCFG!=0)?4'd12:4'd0;next_word<=0;end
   else if(t12)begin es12_done<=1;expected_target<=4'd13;next_word<=0;end
   else if(t13)begin es13_done<=1;expected_target<=4'd0;next_word<=0;end
   else begin installed<=installed|tdec[9:1];expected_target<=tdec[9]?after9:expected_target+1'b1;next_word<=0;end
  end
 end
 end
endmodule

// ===== MU wrapper =====
module qkd_static_kv_boot_dispatch_mu_c32 #(parameter integer MUT=0,parameter integer DIECFG=0,parameter integer NRST=43,parameter integer LINKCFG=0,parameter integer ESCFG=0,parameter integer DIECAP=0,parameter integer MU=1,parameter integer WMUT=0,parameter integer SRQ=0)(
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
 wire[142:0]pr_o;wire[9:0]pr_ab;wire[4:0]pr_gix;wire[2:0]pr_rem6;
 reg x_fault;reg[7:0]x_fc;
 qkd_static_kv_boot_dispatch_c32 #(.MUT(MUT),.DIECFG(DIECFG),.NRST(NRST),.LINKCFG(LINKCFG),.ESCFG(ESCFG),.DIECAP(DIECAP),.SRQ(SRQ))u_disp(
  .ck(ck),.rst_n(rst_n),.boot_pr(pr_o),.boot_addr_b(pr_ab),.boot_gix(pr_gix),.boot_rem6(pr_rem6),.boot_image_target(boot_image_target),.boot_image_ready(boot_image_ready),
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
  assign pr_o=boot_pr;assign pr_ab=boot_pr[73:64];assign setup_ready=o_setup;
  qkd_kv_ctl_c32_div6r u_gixr(.a(boot_pr[73:64]),.q(pr_gix),.r(pr_rem6));
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
  // KV-CTL3 census: the address field of pr_o (word 470 -> 326 on an accepted seal) is formed TWICE behind kept-hierarchy
  // leaves with distinct selects (the select and a kept reset-copy literal; the select is 0 on the first edge after reset:
  // open_q / o_lw are reset), so the dispatcher's address consumers split over two drivers (boot_pr[69/70]: 33-38 loads).
  // KV-CTL12b: u_pg gets its own select copy rs_a[2] (c32c native census: as&&rs_a[0] drove u_pa+u_pg = 36 > 32 loads)
  (* keep *) reg[2:0]rs_a;
  always @(posedge ck)rs_a<={3{rst_n}};
  wire as=seal_w&&ok_seal&&!bad_epoch;
  wire[9:0]pa_a;
  ot_s32_sel #(.W(10)) u_pa(.s(as&&rs_a[0]),.a(10'd326),.b(boot_pr[73:64]),.y(pa_a));
  ot_s32_sel #(.W(10)) u_pb(.s(as&&rs_a[1]),.a(10'd326),.b(boot_pr[73:64]),.y(pr_ab));
  // KV-CTL12: /6 and %6 of the RAW address (parallel to the seal accept), then the word-326 constants on an accepted seal
  wire[4:0]gix_r;wire[2:0]rem_r;
  qkd_kv_ctl_c32_div6r u_gixr(.a(boot_pr[73:64]),.q(gix_r),.r(rem_r));
  ot_s32_sel #(.W(8)) u_pg(.s(as&&rs_a[2]),.a({5'd22,3'd2}),.b({gix_r,rem_r}),.y({pr_gix,pr_rem6}));
  wire v74=gap_w?1'b0:(seal_w?(ok_seal&&!bad_epoch):boot_pr[74]);
  assign pr_o={boot_pr[142:75],v74,pa_a,boot_pr[63:0]};
  always @(posedge ck or negedge rst_n)
  if(!rst_n)begin open_q<=0;gcnt<=0;g_we<=0;x_fault<=0;x_fc<=0;end
  else begin
   g_we<=0;
   if(o_lw&&o_la==9'd325)open_q<=1;
   if(gap_w||seal_w)begin
    if(execution_active)begin x_fault<=1;x_fc[1]<=1;end
    else if(bad_epoch&&!o_fault&&!x_fault)begin x_fault<=1;x_fc[4]<=1;end
    else if(gap_w&&!ok_gap&&!o_fault)begin x_fault<=1;x_fc[3]<=1;end
    else if(seal_w&&!ok_seal&&!o_fault)begin x_fault<=1;x_fc[3]<=1;end
    else if(ok_gap)begin gcnt<=gcnt+1'b1;g_we<=(WMUT!=1);end
    else if(ok_seal)begin open_q<=0;gcnt<=0;end
   end
   // a new target-1 image (BEGIN) re-opens only through the original's word 325 again
   if(boot_image_target!=1)begin open_q<=0;gcnt<=0;end
  end
  assign setup_ready=o_setup&&!x_fault;
  // KV-CTL3 S32: the GAP word hold (g_a, g_d) and the layer-bus select (g_we) in <= 16-bit slices (ot_s32_sel leaves, one
  // kept reset-copy literal per slice): same function, 0 added edges.
  (* keep *) reg[9:0]rs_m;
  always @(posedge ck)rs_m<={10{rst_n}};
  wire gw=(gap_w||seal_w)&&!execution_active&&!(bad_epoch&&!o_fault&&!x_fault)&&!(gap_w&&!ok_gap&&!o_fault)&&!(seal_w&&!ok_seal&&!o_fault)&&ok_gap;
  wire[72:0]gsrc={addr[8:0],data},gnx;
  wire[72:0]gq={g_a,g_d};
  wire[8:0]la_m=(o_lw&&o_la==9'd326)?9'd470:o_la;
  wire[72:0]lsel;wire[72:0]lo_b={la_m,o_ld};
  genvar gs;
  for(gs=0;gs<5;gs=gs+1)begin:g_sl
   localparam integer LO=16*gs,W=(gs==4)?9:16;
   ot_s32_sel #(.W(W)) u_h(.s(gw&&rs_m[gs]),.a(gsrc[LO+:W]),.b(gq[LO+:W]),.y(gnx[LO+:W]));
   ot_s32_sel #(.W(W)) u_o(.s(g_we&&rs_m[5+gs]),.a(gq[LO+:W]),.b(lo_b[LO+:W]),.y(lsel[LO+:W]));
  end
  always @(posedge ck or negedge rst_n)if(!rst_n)begin g_a<=0;g_d<=0;end else begin g_a<=gnx[72:64];g_d<=gnx[63:0];end
  always @*begin
   layer_we=o_lw||g_we;
   layer_addr=lsel[72:64];
   layer_data=lsel[63:0];
   fault=o_fault||x_fault;fault_code=o_fc|x_fc;
  end
 end endgenerate
endmodule


// Low five bits of unsigned floor(a/6), exactly the original group-index cast.
// Consume the high five bits as a remainder, then emit one quotient bit per
// low input bit. Small kept cones bound fanout without adding clock edges.
(* keep_hierarchy *)
module qkd_kv_ctl_c32_rem6(input wire[4:0]a, output wire[2:0]r);
 assign r=3'(a % 5'd6);
endmodule
(* keep_hierarchy *)
module qkd_kv_ctl_c32_div6_step(input wire[2:0]r, input wire b, output wire[2:0]s, output wire q);
 wire[3:0]n={r,b};
 assign q=n>=4'd6;
 assign s=q?3'(n-4'd6):n[2:0];
endmodule
(* keep_hierarchy *)
module qkd_kv_ctl_c32_div6(input wire[9:0]a, output wire[4:0]q);
 wire[2:0]r[0:5];
 qkd_kv_ctl_c32_rem6 u_hi(.a(a[9:5]),.r(r[5]));
 genvar j;
 generate for(j=0;j<5;j=j+1)begin:g_s
  qkd_kv_ctl_c32_div6_step u_s(.r(r[j+1]),.b(a[j]),.s(r[j]),.q(q[j]));
 end endgenerate
endmodule

// KV-CTL12 10-21: qkd_kv_ctl_c32_div6 plus the final remainder (= a % 6).
(* keep_hierarchy *)
module qkd_kv_ctl_c32_div6r(input wire[9:0]a, output wire[4:0]q, output wire[2:0]r);
 wire[2:0]rr[0:5];
 qkd_kv_ctl_c32_rem6 u_hi(.a(a[9:5]),.r(rr[5]));
 genvar j;
 generate for(j=0;j<5;j=j+1)begin:g_s
  qkd_kv_ctl_c32_div6_step u_s(.r(rr[j+1]),.b(a[j]),.s(rr[j]),.q(q[j]));
 end endgenerate
 assign r=rr[0];
endmodule

// KV-CTL10 10-20: 2-bit one-hot predecode of a 4-bit target (kept hierarchy: the ABC boundary that keeps the boot target
// port net at <= 8 mapped loads).  hi = one-hot t[3:2], lo = one-hot t[1:0]; t == k  <=>  hi[k/4] && lo[k%4].
(* keep_hierarchy *)
module qkd_kv_ctl_c32_tpre(input wire[3:0]t, output wire[3:0]hi, output wire[3:0]lo);
 assign hi={t[3:2]==2'd3,t[3:2]==2'd2,t[3:2]==2'd1,t[3:2]==2'd0};
 assign lo={t[1:0]==2'd3,t[1:0]==2'd2,t[1:0]==2'd1,t[1:0]==2'd0};
endmodule
