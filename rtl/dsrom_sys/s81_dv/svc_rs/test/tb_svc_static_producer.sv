`timescale 1ns/1ps
// Actual outer decoder/memories. Consumer below is PROTOCOL ONLY, with real
// calendar and real H8 expander; no arithmetic or numerical-engine claim.
module tb_svc_static_producer;
 reg clk=0;always #0.5 clk=~clk;reg rst_n=0,qv=0;reg[511:0]q=0;
 integer phase_case=0,mut=0,errors=0,cycle=0,origin=-1,gphase=-1;
 integer qc=0,kc=0,pc=0,lastq=-1,lastk=-1,lastp=-1,qerr=0,phaseerr=0;
 wire[31:0]fc;
 dsdv_svc_att #(.H(8)) u(.clk(clk),.rst_n(rst_n),.sid(4'd3),.tile(4'd0),.gd(8'd0),.pvs(8'd0),.root(1'b0),
  .q_v(qv),.q_d(q),.hw_v(1'b0),.hw_d(291'd0),.qrq(),.qrk(2'd0),.qwd(2'd0),.qrv(2'd0),.qr_data(512'd0),.qr_tag(34'd0),.qr_beat(8'd0),
  .l_v(),.l_d(),.pv_ov(),.pv_od(),.sm_st(),.sm_kind(),.sm_jid(),.sm_rv(),.sm_rp(),.sm_rj(),.sm_rd(),
  .go_o(),.tjob_o(),.done(),.tagj(),.hcr(),.hack(),.fault(),.fault_code(fc),.pio_o(),.pvo_o(),.jc_o(),.st_o(),.hb_o());
 always @(posedge clk)if(rst_n)begin
  cycle++;
  if(u.go)begin origin=cycle;gphase=!u.u_eng.slot;end
  if(u.eq_v&&u.eq_ready)begin
   if(lastq>=0&&cycle-lastq!=2)phaseerr++;
   if(!u.u_eng.slot)phaseerr++;
   if(cycle-origin!=2+gphase+2*qc)phaseerr++;
   for(integer w=0;w<32;w++)if(u.eq_w[16*w+:16]!==16'(4096+32*qc+w))qerr++;
   $display("Q case%0d idx%0d cycle%0d relative%0d slot%0b",phase_case,qc,cycle,cycle-origin,u.u_eng.slot);
   qc++;lastq=cycle;
  end
  if(u.ekv_v)begin if(lastk>=0&&cycle-lastk!=1)phaseerr++;kc++;lastk=cycle;end
  if(u.ep_v)begin
   if(lastp>=0&&cycle-lastp!=2)phaseerr++;
   if(u.u_eng.slot)phaseerr++;
   if(cycle-origin!=64+(1^gphase)+2*pc)phaseerr++;
   for(integer w=0;w<64;w++)if(u.ep_w[16*w+:16]!==16'(8192+64*pc+w))qerr++;
   $display("P case%0d idx%0d cycle%0d relative%0d slot%0b",phase_case,pc,cycle,cycle-origin,u.u_eng.slot);
   pc++;lastp=cycle;
  end
 end
 task automatic word(input[511:0]w);@(negedge clk);qv=1;q=w;endtask
 task automatic gap;@(negedge clk);qv=0;q=0;repeat(4)@(negedge clk);endtask
 function automatic[511:0]hdr(input integer typ,input integer len);reg[511:0]h;h=0;h[511:508]=4'(typ);h[503]=1;h[491:480]=12'(len);return h;endfunction
 initial begin
  reg[511:0]h;integer nominal_bad;integer seen[0:1];
  void'($value$plusargs("mut=%d",mut));
  for(integer p=0;p<2;p++)begin
   phase_case=p;rst_n=0;qv=0;repeat(4)@(negedge clk);rst_n=1;
   qc=0;kc=0;pc=0;lastq=-1;lastp=-1;lastk=-1;qerr=0;phaseerr=0;origin=-1;
   h=hdr(12,0);h[32]=1;word(h);gap();
   h=hdr(2,0);h[98:89]=32;word(h);gap();
   h=hdr(7,2);h[19:10]=32;word(h);
   for(integer j=0;j<2;j++)begin h=0;for(integer r=0;r<16;r++)h[32*r+:32]=32'(80+r+256*j);word(h);end gap();
   repeat(36)@(negedge clk);
   word(hdr(6,32));for(integer r=0;r<32;r++)begin h=0;h[9:0]=10'(r);h[30:10]=21'(80+(r%16)+256*(r/16));h[34+:128]=128'h010101;h[290+:16]=16'h3c00;word(h);end gap();
   word(hdr(1,128));for(integer j=0;j<128;j++)begin h=0;for(integer w=0;w<32;w++)h[16*w+:16]=16'(4096+32*(j/16)+w);word(h);end gap();
   word(hdr(5,8));for(integer j=0;j<8;j++)begin h=0;for(integer w=0;w<32;w++)h[16*w+:16]=16'(8192+32*j+w);word(h);end gap();
   repeat(p)@(negedge clk);
   h=hdr(13,0);h[15:0]=64;h[31:16]=200;word(h);gap();repeat(260)@(negedge clk);
   seen[p]=gphase;
   nominal_bad=(qc!=8||kc!=8||pc!=4||qerr!=0||phaseerr!=0||fc!=0||u.u_eng.af!=0||u.u_eng.pouts!=8);
   $display("PRODUCER case%0d go_phase%0d Q%0d KV%0d P%0d qerr%0d phaseerr%0d fc%08x af%0d expandedP%0d",p,gphase,qc,kc,pc,qerr,phaseerr,fc,u.u_eng.af,u.u_eng.pouts);
   if(mut==0)begin if(nominal_bad)errors++;end
   else if(qc==8||qerr==0||!fc[12])errors++;
  end
  if(seen[0]==seen[1])begin $display("GO phase coverage FAILED");errors++;end
  if(errors==0)$display("STATIC_PRODUCER PASS mut=%0d",mut);else $fatal(1,"STATIC_PRODUCER FAIL mut=%0d errors=%0d",mut,errors);
  $finish;
 end
endmodule
module ot_s81_svc_attn_s #(
    parameter integer SRX=0, parameter [1023:0] SRXT=0, parameter integer H = 16,          // heads per die
    parameter integer D = 512,         // head_dim
    parameter integer TD = 64,         // tile width (dims per q.k beat / rows per p.v block)
    parameter integer NL = 4,          // row lanes (rows per cycle)
    parameter integer TROWS = 640,     // staging buffer rows
    parameter integer SC_CRED = 64,     // score-beat credits; 0 = static scores (SVC-PV3): no credit, sc_cr ignored --
                                        //   the consumer takes every beat the cycle it is produced (valid-only)
    parameter integer PV_CRED = 64,    // pv-beat credits; 0 = static P.V (SVC-PV2): no credit, pv_cr ignored -- the
                                       //   consumer's buffer and drain are compiled and fault-checked there
    parameter bit SRAM_MACRO = 0,      // ASAP7 packed-row staging macro boundary
    parameter integer PWORDS = 1,      // probability words per p handshake (1 or 2)
    parameter integer ILV = 0,         // 1: position-interleaved verify mode (see the controller)
    parameter integer REPL = 0,        // 1 (needs ILV = 1): per-tile copies of the transposer read/write indices,
                                       //   the E-register q.k/p.v select and registered pad flags, and a 2-entry
                                       //   p-word input FIFO so q_ready/p_ready come from registers only;
                                       // 2: as 1, plus one register stage between every issue/fill decision and
                                       //   its per-tile copies and the staging read (q.k and p.v beats both enter
                                       //   the E register one cycle later; guards one cycle longer)
    parameter integer PHYS = 0,        // 1: physical characterisation only (transposers/merges stubbed)
    parameter integer NSTAGE = 1,      // 2 (needs ILV = 1): two staging buffers, the front job writes and reads
                                       //   one while the back job fills from the other (per-position row lists)
    parameter integer FPL = 3,         // binary32 add latency (7: 1.2 GHz streaming domain)
    parameter integer FML = 3,         // tile product latency
    parameter integer NBANKP = 0,      // stationary banks; 0 = as built (3 / 4 with PWORDS 2, +1 with ILV).  The
                                       // bank lifetime grows with the skew (6 FPL): at FPL 7 more banks keep p.v
                                       // at one beat per cycle (see the W11 stream record)
    parameter integer TILE_S = 0,      // 1: the head-group tile ot_hdc_v41x_attn_tile_s (same cycles; hardens
                                       //    hierarchically, rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv)
    parameter integer FPLX = 0,        // >0: FP32 add latency of the lane trees and block merges (default FPL)
    parameter integer F12 = 0,         // 1: every FP32 add is the 1.2 GHz f12 unit (LAT 4: ot_hdc_fp32_add_f12_l4,
                                       //    registered operands; LAT 5: ot_hdc_fp32_add_f12_l5x, operand mux in front)
    parameter integer TRX = 0,         // 1 (REPL >= 1): transposers with per-element one-hot read selects and per-row
                                       //    one-hot write enables (ot_hdc_v41x_attn_tr_x; same cycles)
    parameter integer MFAN = 0,        // 1: the block merges with per-head control copies (ot_hdc_v41x_attn_merge_x;
                                       //    +1 cycle on p.v results only)
    parameter integer NARROW = 0,      // 1: block counters (load / fill / issue / filled / count) BKW bits wide, not
                                       //    16 (values never exceed NBLKMAX; same values and cycles for T <= TROWS):
                                       //    shortens the controller's compare/increment loops for 1.2 GHz
    // SVC4 (LEAD2-S81, 10-19): landed engine.  TEXT 1 = the NT tiles are NOT instantiated here: tile t's input bundle
    // leaves on tx_i[t] and its output bundle returns on tx_o[t] (the landed parent dsdv_svc_attw_f_lp puts every tile
    // in its own clock region with LANDED crossings both ways).  TLX = edges the tile round trip takes beyond TLAT (the
    // compiler re-schedule: tags / lane trees wait TLX more); TXD = register stages on the returning bundle inside this
    // module (the flat lockstep reference of a landed parent: TXD = TLX; a landed build: TXD = 0).  Defaults = as built.
    parameter integer TEXT = 0,
    parameter integer TLX = 0,
    parameter integer TXD = 0,
    // ATTN1 (DRIVE-S81-ATTN1, 10-20, opt-in): NTP = PHYSICAL engine tiles (0 = NT = NL * D / TD, as built).  NTP < NT
    // (needs D = TD, i.e. S = 1, and NT % NTP == 0) time-multiplexes V = NT / NTP virtual tiles on each physical tile:
    // physical tile p runs virtual tiles p V + k in sub-beat k (k = 0 .. V - 1, consecutive cycles), so the controller
    // issues one beat (q.k or p.v) every V cycles, every stationary-bank guard grows by V (the sub-beats read up to V
    // cycles after the old E register), and the tile outputs are re-assembled into the NT-tile beat (lane values,
    // merges, sc_* / pv_* ABI and the merge order unchanged: bit-exact, only the cycles move).  Tile input +1 register
    // (the sub-beat shift chain), tile output re-assembly +V: tags wait TLAT + TLX + V + 1.
    parameter integer NTP = 0,
    parameter integer NMUT = 0,        // ATTN1 bench negative controls (V > 1 only): 1 = sub-beat re-assembly order
                                       //   reversed, 2 = issue slot free one cycle early (V - 1), 3 = no guard growth
    // derived (do not override): tile bundle widths, same formulas as the NBANK / BW localparams below
    parameter integer TX_NB = (NBANKP > 0) ? NBANKP : (((PWORDS >= 2) ? 4 : 3) + ((ILV != 0) ? 1 : 0)),
    parameter integer TX_BW = (TX_NB > 4) ? $clog2(TX_NB) : 2,
    parameter integer TXI = 1 + 1 + TX_BW + 8 + PWORDS*TD*16 + 1 + 1 + TX_BW + TD*18,  // {ib, ibank, iv, ld_w2v, ld_w, ld_grp, ld_bank, ld_mode, ld_v}
    parameter integer TXO = 1 + H*32 + H,                                               // {oflt, oy, ov}
    parameter integer TX_NT = (NTP > 0) ? NTP : NL*(D/TD)                               // tile bundles (physical tiles)
) (
    input  wire                   clk,
    input  wire                   rst_n,
    // job
    input  wire                   job_v,
    input  wire [15:0]            job_t,
    output wire                   job_ready,
    // q
    input  wire                   q_v,
    input  wire [D*16-1:0]        q_w,
    output wire                   q_ready,
    // kv rows
    input  wire                   kv_v,
    input  wire [NL-1:0]          kv_m,
    input  wire [NL*(D/32)*265-1:0] kv_w,
    output wire                   kv_ready,
    // scores
    output reg                    sc_v,
    output reg  [15:0]            sc_row,
    output reg  [NL-1:0]          sc_m,
    output reg  [NL*H*32-1:0]     sc_y,
    output reg  [NL*H-1:0]        sc_f,
    input  wire                   sc_cr,
    // probabilities
    input  wire                   p_v,
    input  wire [PWORDS*TD*16-1:0] p_w,
    output wire                   p_ready,
    // pv
    output reg                    pv_v,
    output reg  [7:0]             pv_c,
    output reg  [NL*(D/TD)*H*32-1:0] pv_y,
    output reg  [NL*(D/TD)*H-1:0] pv_f,
    input  wire                   pv_cr,
    // bench visibility
    output wire                   qk_iss,
    output wire                   pv_iss,
    // SVC4 landed engine (TEXT 1): tile bundles; unused (tx_i 0, tx_o ignored) when TEXT 0
    output wire [TX_NT*TXI-1:0] tx_i,
    input  wire [TX_NT*TXO-1:0] tx_o
);

wire slot;
ot_s81_svc_rt2_load_calendar cal(.clk(clk),.rst_n(rst_n),.load_slot(slot));
integer nq,nkv,pulse,pidx,pouts;
reg[1:0]skn;reg skr,skw;reg[1023:0]sk[0:1];
wire pop=skn!=0&&slot&&nq>=8;
wire push=p_v&&p_ready;
assign job_ready=1;assign q_ready=slot&&nq<8;assign kv_ready=1;assign p_ready=skn!=2;
assign qk_iss=0;assign pv_iss=0;assign tx_i=0;
wire ov,om;wire[1023:0]ow;wire[7:0]og;wire af;
ot_s81c_h8_rt2_load ex(.clk(clk),.rst_n(rst_n),.ld_v((q_v&&q_ready)||pop),.ld_mode(pop),.ld_bank(3'd0),.ld_grp(pop?8'(2*pidx):8'(nq)),.ld_w(pop?sk[skr]:1024'(q_w)),.ld_w2v(pop),.out_v(ov),.out_mode(om),.out_bank(),.out_grp(og),.out_w(ow),.out_w2v(),.fault(af));
always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin nq<=0;nkv<=0;pulse<=0;pidx<=0;pouts<=0;skn<=0;skr<=0;skw<=0;pv_v<=0;pv_c<=0;end
 else begin
  if(q_v&&q_ready)nq<=nq+1;
  if(kv_v)nkv<=nkv+1;
  if(push)begin sk[skw]<=p_w;skw<=!skw;end
  if(pop)begin skr<=!skr;pidx<=pidx+1;end
  case({push,pop})2'b10:skn<=skn+1;2'b01:skn<=skn-1;default:;endcase
  if(ov&&om)begin
   pouts<=pouts+1;
   for(integer r=0;r<4;r++)for(integer h=0;h<8;h++)if(ow[16*(16*r+h)+:16]!==16'(8192+16*og+8*r+h))$fatal(1,"expanded P payload mismatch grp%0d row%0d h%0d got%h",og,r,h,ow[16*(16*r+h)+:16]);
  end
  if(job_v)pulse<=1;else if(pulse!=0)pulse<=pulse+1;
  pv_v<=pulse>=100&&pulse<108;pv_c<=8'(pulse-100);
 end
end
always_comb begin sc_v=0;sc_row=0;sc_m=0;sc_y=0;sc_f=0;pv_y=0;pv_f=0;end
endmodule
