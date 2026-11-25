#!/usr/bin/env python3
"""Derive the head's real no-repair LEP core from current selected S81 source.

Existing S81 masters stay byte-identical. New head-only module names retain
all arithmetic, queues, credits and timing; the SRAM helper uses real r0c0
macros with no repair pins. Physical hardening remains a fresh head build.
"""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['physical/die_plan/s81/bind/source_modules/portfix178/ot_s81sl_slice_lep.sv','rtl/lib/ot_sram_oldread_wreg.sv','rtl/dsrom_sys/s81_dv/slice/dsdv_mu_land.sv','rtl/lib/ot_sram_showahead_1r1w.sv']

def module(text,name):
 m=re.search(r'^module\s+'+re.escape(name)+r'\b.*?^endmodule\b',text,re.M|re.S)
 if not m:raise ValueError('missing exact source module '+name)
 return m.group()

# HEAD-PLAN-R4 11-17 (NF15f, opt-in RXH; default 0 = every net and flop of the delivery unchanged): RXH 1 = one registered
# rank on the shared RX head word between the four RX FIFO heads and the ring delivery (rid) / landing (mwd) registers.
# The ring delivery block g_rxm reads the head word and every ring-side term aligned with it (pair release, ring / land /
# tag metadata, the look-ahead selects) through *_h names; RXH 0 makes them plain aliases, RXH 1 the same one register.
RXH_NAMES=['rhd','rhk','relp','rpb','ring_meta_regions','active_ring_flags','rnex','rringx','rhkx','rtagx','rne_return','rb']
RXH_DECL=r"""
    // HEAD-PLAN-R4 11-17 NF15f (opt-in RXH, default 0 = the *_h names below are aliases of the originals, no added cycle):
    // RXH 1 puts ONE registered rank on the shared RX head word (rhd: 4 lanes x 552 data bits = 2,208 flops in four kept
    // leaves g_rxh.g_l[t].u_st, placeable mid-trunk) between the RX FIFO heads and the ring delivery (rid) / landing (mwd)
    // registers.  Every ring-side term the delivery block g_rxm reads with that word -- pair release (rne), ring / land /
    // tag metadata, the look-ahead select inputs, the return-tag non-empty flags -- takes the same one register (kept leaf
    // g_rxh.u_ctl, 44 control flops cleared by rnx), so ri, mu_rt and ml_wv / ml_wd move by exactly +1 edge together: same
    // beats, same order, same tags.  The replay word (ml_rv / ml_rd) is not delayed: a ring beat behaves as if its K link were
    // one cycle longer (as one more KRX stage, without the credit round trip).  FIFO pops, credits, rxv and the perr / pair
    // parity checks still read the undelayed head.  Supported at MU_EN 1 + RX_SRAM 1 + NATIVE32 1 + AB_EN 1 (hd_lep0N) only.
    wire [NL*(H+1)-1:0] rhd_h; wire [NL-1:0] rhk_h, rne_return_h, rnex_h, rringx_h, rhkx_h, rtagx_h;
    wire [NL*4-1:0] ring_meta_regions_h; wire [1:0] relp_h; wire rpb_h; wire [3:0] active_ring_flags_h; wire [1103:0] rb_h;
    generate if (RXH == 0) begin : g_rxh0
        assign rhd_h = rhd; assign rhk_h = rhk; assign rne_return_h = rne_return; assign rnex_h = rnex;
        assign rringx_h = rringx; assign rhkx_h = rhkx; assign rtagx_h = rtagx; assign ring_meta_regions_h = ring_meta_regions;
        assign relp_h = relp; assign rpb_h = rpb; assign active_ring_flags_h = active_ring_flags; assign rb_h = rb;
    end else begin : g_rxh
        initial if (RXH != 1 || MU_EN == 0 || RX_SRAM == 0 || NATIVE32 == 0 || NL != 4) $fatal(1, "RXH 1 needs MU_EN, RX_SRAM, NATIVE32, AB_EN 1");
        wire [NL-1:0] rne_q;
        for (genvar t = 0; t < NL; t = t + 1) begin : g_l
            wire [H-1:0] hq;
            ot_s81hd_lep_rxh_st #(.W(H)) u_st(.clk(clk), .d_i(rhd[t*(H+1)+:H]), .d_o(hq));
`ifdef OT_S81HD_LEPK_MUT_RXHBIT
            if (t == 1) begin : g_mut assign rhd_h[t*(H+1)+:H] = {hq[H-1:41], rhd[t*(H+1)+40], hq[39:0]}; end   // MUTANT: lane 1 bit 40 skips the rank
            else begin : g_ok assign rhd_h[t*(H+1)+:H] = hq; end
`else
            assign rhd_h[t*(H+1)+:H] = hq;
`endif
            assign rhd_h[t*(H+1)+H] = 1'b0;            // lane sequence-parity bit: g_rxm reads [H-1:0] of each lane only
        end
        wire [43:0] cd = {rtagx, rhkx, rringx, rnex, rhk, ring_meta_regions, rne_return, rne};
        wire [43:0] cq;
        ot_s81hd_lep_rxh_ctl #(.W(44)) u_ctl(.clk(clk), .rn(rnx), .d_i(cd), .d_o(cq));
`ifdef OT_S81HD_LEPK_MUT_RXHSKEW
        assign {rtagx_h, rhkx_h, rringx_h, rnex_h} = {rtagx, rhkx, rringx, rnex};   // MUTANT: look-ahead selects skip the rank
        assign {rhk_h, ring_meta_regions_h, rne_return_h, rne_q} = cq[27:0];
`else
        assign {rtagx_h, rhkx_h, rringx_h, rnex_h, rhk_h, ring_meta_regions_h, rne_return_h, rne_q} = cq;
`endif
        assign relp_h = {rne_q[2] && rne_q[3], rne_q[0] && rne_q[1]};
        assign rpb_h = relp_h[1] && !relp_h[0];
        assign active_ring_flags_h = rpb_h ? ring_meta_regions_h[2*4+:4] : ring_meta_regions_h[0+:4];
        assign rb_h = rpb_h ? {rhd_h[4*H+2:3*H+3], rhd_h[3*H+1:2*H+2]} : {rhd_h[2*H:H+1], rhd_h[H-1:0]};
    end endgenerate
"""
RXH_LEAVES=r"""
// HEAD-PLAN-R4 11-17: the RXH rank leaves (kept: lanes 0 / 2 and 1 / 3 can hold equal head words; flattened (* keep *) regs
// would fold across lanes as in DIE-HEAD-85).  Data is reset-free; the control copies clear on the RX reset.
(* keep_hierarchy, keep *)
module ot_s81hd_lep_rxh_st #(parameter integer W = 552) (input wire clk, input wire [W-1:0] d_i, output reg [W-1:0] d_o);
    always @(posedge clk) d_o <= d_i;
endmodule

(* keep_hierarchy, keep *)
module ot_s81hd_lep_rxh_ctl #(parameter integer W = 44) (input wire clk, rn, input wire [W-1:0] d_i, output reg [W-1:0] d_o);
    always @(posedge clk or negedge rn) if (!rn) d_o <= '0; else d_o <= d_i;
endmodule"""

def rxh_core(core):
 old="    parameter [15:0]  TXI = 16'h0000   // DIE-HEAD-84: per-lane TX ingress stages (see g_tx); 0 = none\n) ("
 new=("    parameter [15:0]  TXI = 16'h0000,  // DIE-HEAD-84: per-lane TX ingress stages (see g_tx); 0 = none\n"
      "    parameter integer RXH = 0          // HEAD-PLAN-R4 NF15f: RX head rank before ri / ml_wd (see g_rxh); 0 = none\n) (")
 if core.count(old)!=1:raise ValueError('RXH parameter pattern changed')
 core=core.replace(old,new)
 anchor='    wire [1103:0] rb = {h1[H-1:0], h0[H-1:0]};          // the released frame (ring beat when bit 0)\n'
 if core.count(anchor)!=1:raise ValueError('RXH anchor pattern changed')
 core=core.replace(anchor,anchor+RXH_DECL.lstrip('\n'))
 a=core.index('    end else begin : g_rxm\n');b=core.index('    assign ml_wv = mwv; assign ml_wd = mwd; assign mcol_w = mcol;\n',a)
 blk=core[a:b]
 if re.search(r'\brne\b',blk):raise ValueError('g_rxm reads rne directly: extend RXH_NAMES')
 for n in RXH_NAMES:
  blk,k=re.subn(r'\b'+n+r'\b',n+'_h',blk)
  if k==0:raise ValueError('RXH: g_rxm no longer reads '+n)
 return core[:a]+blk+core[b:]

def derive(root):
 src=[(root/p).read_text() for p in SOURCES]
 core=module(src[0],'ot_s81sl_lep_core').replace('module ot_s81sl_lep_core','module ot_s81hd_lep_core_nr',1)
 # Slang requires a declared generate index even in the inactive SAFE_FIFO branch.
 core=core.replace('for(c=0;c<NA;c=c+1)', 'for(genvar c=0;c<NA;c=c+1)')
 core=core.replace('ot_sram_oldread_wreg #(', 'ot_sram_oldread_wreg_nr #(')
 core=core.replace('ot_sram_showahead_1r1w #(', 'ot_sram_showahead_1r1w_head_nr #(')
 idx=module(src[0],'ot_s81sl_lep_mu_ab_idx').replace('module ot_s81sl_lep_mu_ab_idx','module ot_s81hd_lep_idx_nr',1).replace('ot_s81sl_lep_core #(', 'ot_s81hd_lep_core_nr #(')
 # Expose the wrapper's existing mode as an explicit opt-in. Default1 keeps
 # every prior caller identical; the current head no-index leaf selects0.
 idx=idx.replace('IN_PIPE = 0, parameter integer NATIVE32 = 0',
                 'IN_PIPE = 0, parameter integer NATIVE32 = 0, parameter integer IDX_EN = 1')
 idx=idx.replace('.IDX_EN(1)) u', '.IDX_EN(IDX_EN)) u')
 mem=module(src[1],'ot_sram_oldread_wreg').replace('module ot_sram_oldread_wreg','module ot_sram_oldread_wreg_nr',1)
 mem=mem.replace('ot_sram_1r1w_512x128_m4_r2c2 u_m','ot_sram_1r1w_512x128_m4_r0c0 u_m')
 old=".w_mask_in({128{1'b1}}),\n     .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(14'd0));"
 if old not in mem:raise ValueError('repair-port source pattern changed')
 mem=mem.replace(old,".w_mask_in({128{1'b1}}));")
 # DIE-HEAD-71 (hd_lep0N l48ub a6 LEC NOT EQ, 11-05): the MU TX window tag bit 0 is the constant 1 of
 # {pos, user, land, 1}.  The source keeps it as a no-reset flop that only ever loads 1'b1, so synthesis
 # removes it and the register-mapped LEC finds a gold-only free register (w_t[0], X until the first load).
 # Head-only safe form: w_t holds bits 32:1 and wtag bit 0 is the constant wire.  wtag is read only while a
 # window is open (wn != 0, set by the same mcv load), so every observed value is unchanged: 0 added cycles.
 for old,new in [('reg w_ab, te; reg [32:0] w_t;','reg w_ab, te; reg [32:1] w_t;'),
                  ("w_t <= {mcq[33:13], mcq[12:3], mcq[2], 1'b1};","w_t <= {mcq[33:13], mcq[12:3], mcq[2]};"),
                  ('localparam integer LO=wt*9,W=(33-LO<9)?33-LO:9;',
                   'localparam integer LO0=wt*9,W0=(33-LO0<9)?33-LO0:9,LO=(LO0==0)?1:LO0,W=(LO0==0)?W0-1:W0;'),
                  ('assign wtag = w_t;',"assign wtag = {w_t, 1'b1};")]:
  if core.count(old)!=1:raise ValueError('MU TX tag source pattern changed: '+old)
  core=core.replace(old,new)
 # DIE-HEAD-84 11-07 (opt-in TXI, default 0 = every line above unchanged in function): TXI[4t+:4] registered stages
 # on TX lane t's ingress {push, address-group pushes, write word} so the lane FIFO (its SRAM column, pointers,
 # credits, read pipeline) can sit beside its own pair while the frame stays at the hub.  The TX path is feed-forward
 # (no lane state reaches the frame), so the stages only delay every write of lane t by TXI cycles: same words, same
 # order, same overflow fault.  Each stage is one instance g_tx[t].g_txi.g_s[j] (FIRM-placeable along the leg).
 for old,new in [('    parameter integer IN_PIPE = 0      // 1 (LEPCAP 10-19)','    parameter integer IN_PIPE = 0,     // 1 (LEPCAP 10-19)'),
                 ('\n) (\n    input  wire            clk,',"\n    parameter [15:0]  TXI = 16'h0000   // DIE-HEAD-84: per-lane TX ingress stages (see g_tx); 0 = none\n) (\n    input  wire            clk,"),
                 ('        wire psh = (SAFE_FIFO)?push_lane[2*t+t/2]:pp[t / 2];\n',
                  '        wire psh_s = (SAFE_FIFO)?push_lane[2*t+t/2]:pp[t / 2];\n'
                  '        wire psh; wire [TX_NA-1:0] pg_s, pgx; wire [H:0] wdx;\n'
                  '        for(genvar gi=0;gi<TX_NA;gi=gi+1)begin:g_pgs assign pg_s[gi]=push_group[2*gi+t/2]; end\n'
                  '        ot_s81hd_lep_txi #(.W(H+1),.NG(TX_NA),.N(TXI[4*t+:4])) g_txi(.clk(clk),.rn(rt),.psh_i(psh_s),.pg_i(pg_s),\n'
                  '            .wd_i({sq[t/2],(t%2==0)?hf0:hf1}),.psh_o(psh),.pg_o(pgx),.wd_o(wdx));\n'),
                 ('.wd({sq[t/2],(t%2==0)?hf0:hf1})','.wd(wdx)'),
                 ('.wd({sq[t / 2], (t % 2 == 0) ? hf0 : hf1})','.wd(wdx)')]:
  if core.count(old)!=1:raise ValueError('TXI source pattern changed: '+old[:50])
  core=core.replace(old,new)
 if core.count('push_group[2*c+t/2]')!=4:raise ValueError('TXI push-group pattern changed')
 core=core.replace('push_group[2*c+t/2]','pgx[c]')

 # HEAD-TYPES-OPUS 11-18 (TXI lanes only; TXI 0 = the original statements): late push select on the TX address-group
 # state.  hd_lep0N p2 CTS (TT, placement RC): 37 of the 44 setup violators, worst -460 ps (count_r[8]), all start at the
 # lane's last TXI stage (g_txi.g_s[N-1] v_o[c] = pgx[c]) and end at g_safe_write.g_address[c].count_r / wp_r: the
 # pushes arrive after the long TXI leg (about 380 ps) and synthesis put them on the LSB of the count adder, so the
 # carry chain (about 500 ps) sits behind the late push.  Here the two next values are formed from local state only
 # and the push selects between them in a kept leaf (ot_s81hd_lep_late_sel): count_r + wr - rd == wr ? count_r + 1 - rd
 # : count_r - rd, and the wp_r wrap form likewise.  Same flops, same names, same values every cycle: 0 added cycles.
 for old,new in [("                        count_r<=count_r+(AT+1)'(wr_update)-(AT+1)'(rd_update);\n",
                  "                        count_r<=count_nx;\n"),
                 ("                        wp_r<=(wp_r==AT'(DT-1) && wr_pointer)?AT'(0):wp_r+AT'(wr_pointer);\n",
                  "                        wp_r<=wp_nx;\n"),
                 ("                wire pointer_reset=rr[TX_RSTBASE+t*TX_RST_STRIDE+TX_NS+2*c];\n",
                  "                wire [AT:0] count_nx; wire [AT-1:0] wp_nx;\n"
                  "                if(TXI[4*t+:4]!=0) begin:g_late_sel   // HEAD-TYPES-OPUS 11-18: late push select (0 added cycles)\n"
                  "                  (* keep=1 *) ot_s81hd_lep_late_sel #(.W(AT+1)) u_count(.s(wr_update),\n"
                  "                    .a(count_r+(AT+1)'(1)-(AT+1)'(rd_update)),.b(count_r-(AT+1)'(rd_update)),.y(count_nx));\n"
                  "                  (* keep=1 *) ot_s81hd_lep_late_sel #(.W(AT)) u_wp(.s(wr_pointer),\n"
                  "                    .a((wp_r==AT'(DT-1))?AT'(0):wp_r+AT'(1)),.b(wp_r),.y(wp_nx));\n"
                  "                end else begin:g_add_sel\n"
                  "                  assign count_nx=count_r+(AT+1)'(wr_update)-(AT+1)'(rd_update);\n"
                  "                  assign wp_nx=(wp_r==AT'(DT-1) && wr_pointer)?AT'(0):wp_r+AT'(wr_pointer);\n"
                  "                end\n"
                  "                wire pointer_reset=rr[TX_RSTBASE+t*TX_RST_STRIDE+TX_NS+2*c];\n")]:
  if core.count(old)!=1:raise ValueError('TXI late-select source pattern changed: '+old[:60])
  core=core.replace(old,new)
 idx=idx.replace('parameter integer IDX_EN = 1\n',"parameter integer IDX_EN = 1, parameter [15:0] TXI = 16'h0000\n",1)
 if '.IDX_EN(IDX_EN)) u' not in idx:raise ValueError('idx pattern changed')
 idx=idx.replace('.IDX_EN(IDX_EN)) u','.IDX_EN(IDX_EN), .TXI(TXI)) u',1)
 core=rxh_core(core)
 idx=idx.replace("parameter [15:0] TXI = 16'h0000\n","parameter [15:0] TXI = 16'h0000, parameter integer RXH = 0\n",1)
 idx=idx.replace('.TXI(TXI)) u','.TXI(TXI), .RXH(RXH)) u',1)
 if '.RXH(RXH)) u' not in idx or 'parameter integer RXH = 0' not in idx:raise ValueError('idx RXH pattern changed')
 txi=r"""module ot_s81hd_lep_txi #(parameter integer W = 553, parameter integer NG = 18, parameter integer N = 0) (
    input  wire          clk, rn,
    input  wire          psh_i, input wire [NG-1:0] pg_i, input wire [W-1:0] wd_i,
    output wire          psh_o, output wire [NG-1:0] pg_o, output wire [W-1:0] wd_o
);
    // DIE-HEAD-84: N registered stages on a TX lane's ingress; the pushes clear on the lane reset, the word is reset-free
    wire [NG:0] v [0:N]; wire [W-1:0] d [0:N];
    assign v[0] = {pg_i, psh_i}; assign d[0] = wd_i;
    // DIE-HEAD-85: each stage is a kept leaf (ot_s81hd_lep_txi_st, keep_hierarchy): lanes 0 / 1 share the push-group D
    // and lanes 0 / 2 (1 / 3) the word D, so flattened (* keep *) regs were folded across lanes by opt_merge (vD kit LEC
    // NOT EQUIVALENT 485 on lane 0's FIFO state: gate lane 0 read lane 1's g_txi.g_s[0].vq); a kept leaf cannot fold.
    for (genvar j = 0; j < N; j = j + 1) begin : g_s
        ot_s81hd_lep_txi_st #(.W(W), .NV(NG + 1)) u_st(.clk(clk), .rn(rn), .v_i(v[j]), .d_i(d[j]), .v_o(v[j + 1]), .d_o(d[j + 1]));
    end
    assign {pg_o, psh_o} = v[N];
`ifdef OT_S81HD_LEPK_MUT_TXISKEW
    assign wd_o = d[(N > 0) ? N - 1 : 0];             // MUTANT: the word one stage ahead of its pushes
`else
    assign wd_o = d[N];
`endif
endmodule

(* keep_hierarchy, keep *)
module ot_s81hd_lep_txi_st #(parameter integer W = 553, parameter integer NV = 19) (
    input  wire          clk, rn,
    input  wire [NV-1:0] v_i, input wire [W-1:0] d_i,
    output reg  [NV-1:0] v_o, output reg  [W-1:0] d_o
);
    // one TXI stage: the pushes clear on the lane reset, the word is reset-free
    always @(posedge clk or negedge rn) if (!rn) v_o <= '0; else v_o <= v_i;
    always @(posedge clk) d_o <= d_i;
endmodule

// HEAD-TYPES-OPUS 11-18: the late push select of the TXI address-group state (kept leaf: the select stays the last
// gate before the count_r / wp_r D pins; flattened, ABC folds the push back into the adder carry chain).
(* keep_hierarchy, keep *)
module ot_s81hd_lep_late_sel #(parameter integer W = 10) (input wire s, input wire [W-1:0] a, b, output wire [W-1:0] y);
    assign y = s ? a : b;
endmodule"""
 land=module(src[2],'dsdv_mu_land').replace('module dsdv_mu_land','module dsdv_mu_land_head_nr',1)
 land=land.replace('ot_sram_1r1w_128x256_m1_r2c2 u_m','ot_sram_1r1w_128x256_m1_r0c0 u_m')
 old_land=".w_mask_in({256{1'b1}}),\n                    .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));"
 # Only the D<=128 branch is active for the head's NS1/NB80. Preserve the
 # inactive D>128 branch as source history; reject selecting it in this master.
 if old_land not in land:raise ValueError('MU landing repair-port pattern changed')
 land=land.replace(old_land,".w_mask_in({256{1'b1}}));",1)
 land=land.replace('    localparam integer TG = 1045;', '    initial if(NS*NB>128)$fatal(1,"head NR landing supports <=128 words");\n    localparam integer TG = 1045;')
 # DIE-HEAD-91 (hd_lep0N gen2 kit LEC NOT EQ, 11-09: 7 differs u_land.cnt[0..6]): with NS=1 the slot indices ws/rs
 # are 1-bit registers that only ever load nxs()=0, while cnt/tag are 1-entry arrays, so gold reads cnt[1]/tag[1]
 # (X) at an index the circuit never reaches; synthesis drops the constant ws and the miter sees the X as free.
 # Head-only safe form: every array read/write and address uses wsi/rsi = (NS>1) ? ws/rs : 0.  Identical logic
 # under reset for every NS (NS>1: wsi == ws), 0 added cycles.
 dec='    reg [SB-1:0] ws, rs;\n'
 if land.count(dec)!=1:raise ValueError('MU landing slot index source pattern changed')
 land=land.replace(dec,dec+"    wire [SB-1:0] wsi = (NS > 1) ? ws : '0;  // width-safe slot index (DIE-HEAD-91)\n"
                   "    wire [SB-1:0] rsi = (NS > 1) ? rs : '0;\n",1)
 for old,new,n in [('cnt[ws]','cnt[wsi]',2),('tag[ws]','tag[wsi]',2),('cnt[rs]','cnt[rsi]',2),('tag[rs]','tag[rsi]',1),
                   ("AW'(ws)","AW'(wsi)",1),("AW'(rs)","AW'(rsi)",1),('w_ok && ws == rs','w_ok && wsi == rsi',1)]:
  if land.count(old)!=n:raise ValueError('MU landing slot index source pattern changed: '+old)
  land=land.replace(old,new)
 show=module(src[3],'ot_sram_showahead_1r1w').replace('module ot_sram_showahead_1r1w','module ot_sram_showahead_1r1w_head_nr',1)
 show=show.replace('ot_sram_1r1w_32x128_m1 u_m','ot_sram_1r1w_32x128_m1_r0c0 u_m')
 record=dict(schema='opentallas.s81.head-lep-nr-source.v1',sources={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in SOURCES},
             changes=['head-only module names','real512x128_m4_r0c0 instead of tied-repair r2c2','no data/control/credit/latency change',
                      'MU TX tag bit 0 = constant wire (no constant-load flop; LEC safe form, 11-05)',
                      'opt-in TXI per-lane TX ingress stages (DIE-HEAD-84 11-07; default 0 = no added cycle)',
                      'MU landing slot index wsi/rsi = (NS>1) ? ws/rs : 0 (no X array index; LEC safe form, 11-09)',
                      'opt-in RXH RX head rank before ri / ml_wd (HEAD-PLAN-R4 NF15f 11-17; default 0 = no added cycle)',
                      'TXI lanes: late push select on count_r / wp_r (HEAD-TYPES-OPUS 11-18; TXI 0 = original statements; no added cycle)'],added_cycles=0,
             physical='new head provider; no inherited physical view or signoff')
 # RNE-PAIR-COPY (HEAD-EAST-REPLAN 11-24): each RX lane's SRAM/meta read pointers take the pair partner's nonempty flag
 # from a lane-local duplicate register (same D, same partner reset); zero added cycles.
 import importlib.util as _iu
 _sp=_iu.spec_from_file_location('head_lep_rne_pair_copy',ROOT/'tools/s81_head/head_lep_rne_pair_copy.py');_m=_iu.module_from_spec(_sp);_sp.loader.exec_module(_m)
 core=_m.apply(core)
 record['changes'].append('RNE-PAIR-COPY: lane-local duplicate of the pair partner nonempty flag for RX SRAM/meta read pointers (HEAD-EAST-REPLAN 11-24; no added cycle)')
 header='`timescale 1ns/1ps\n// Generated by tools/s81_head/head_lep_nr_sources.py; do not edit.\n'
 return header+core+'\n\n'+idx+'\n\n'+mem+'\n\n'+land+'\n\n'+show+'\n\n'+txi+'\n'+RXH_LEAVES+'\n',record

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--build-macro',action='store_true');ap.add_argument('--out',type=Path,default=ROOT/'rtl/dsrom_sys/s81_head/generated/ot_s81hd_lep_nr.sv');ap.add_argument('--record',type=Path,required=True);ap.add_argument('--check',action='store_true');a=ap.parse_args()
 if a.build_macro:
  import sys
  sys.path.insert(0,str(ROOT/'tools/mem_compiler'))
  import sram_gen,build_aligned_v2 as A
  out=ROOT/'physical/asap7_memory_macros_v2'
  for words,bits in [(128,256),(32,128)]:
   spec=sram_gen.SramSpec(name=f'ot_sram_1r1w_{words}x{bits}_m1_r0c0',words=words,bits=bits,mux=1,banks=1,ports='1r1w',spare_rows=0,spare_cols=0)
   with A.patched(sram_gen,macro_outline=A.aligned_outline,write_lef=A.aligned_write_lef,GENERATOR_VERSION=f"{sram_gen.GENERATOR_VERSION}+{A.ALIGN_VERSION}"):
    sheet=sram_gen.compile_macro(spec,out)
   area=sheet['area'];A.finish(out,spec.name,None,(area['macro_width_um'],area['macro_height_um']),{'kind':'sram','spec':{k:getattr(spec,k) for k in ('name','words','bits','mux','banks','ports','spare_rows','spare_cols')},'head_new_shape':True})
 text,record=derive(ROOT)
 if a.check:
  if a.out.read_text()!=text:raise SystemExit('STALE head LEP derived source')
 else:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(text)
 a.record.parent.mkdir(parents=True,exist_ok=True);a.record.write_text(json.dumps(record,indent=2)+'\n')
 print('HEAD_LEP_NR_SOURCES PASS; original masters unchanged; added cycles0')
