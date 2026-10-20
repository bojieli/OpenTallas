// ---- qkd_kvpc_s_calendar: KV-PC5 native32 successor of qkd_controller_hbm_calendar (rtl/qwen_sys/static_kv_20261014/qkd_controller_hbm_calendar.sv) ----
// Same ports, same edges, same register state (image, seen, sealed, active_*, wait/left/burst, outputs, fault, idle).
// Native census f1 (tile pc sr7): the calendar's comb controls fanned out to 33..74 mapped pins (image write decodes,
// fire[k], go_q copies, the go-load select).  Every such control is now a LOOKAHEAD kept copy family: the copy registers
// f(next state) on the same hck edge as the state it is derived from, so copy(t) == f(state(t)) exactly (async reset rn:
// reset value == f(reset state) == 0).  Each copy drives one <=16-bit slice directly (no ot_rst_split re-pointing):
//   wv/pa  image write enable + address per (half, 8-bit slice) and the seen bits: we_q && !sealed && !live && addr[4]==h
//   fc     fire[k] for the event OR (4 x ~11 command bits) and the mask / static-read / fire count
//   fe/le  fire[k] && !go_q, live[k] && !go_q for the left/burst and wait (2 x 8 b) updates (the original "else" branch)
//   gk/ga  go_ok = go_q && sealed && !live && !we_q for the per-entry go load (left+burst, wait 2 x 8 b) and active_* / owner / idle
//   i84b   kept copy of image[k][84] (written with it, from its own data copy d20c): it selects half of the 19 row bits
// The go pin feeds 5 gates (go_q + 2 go_ok D gates + 2 !go gates), each gate <= 32 copy D pins; rnx = rn copies (same D,
// same edge) make those gates distinct so synthesis cannot re-share them.  rn stays the reset family (rst_copies).
module qkd_kvpc_s_calendar #(parameter integer N=16, ROW0=64, MUT=0)(
 input wire hck,rst_n,
 input wire cfg_we,input wire [4:0] cfg_addr,input wire [63:0] cfg_data,
 input wire seal,go,input wire [15:0] epoch,input wire [5:0] layer,
 output reg static_cmd_owner,output reg [42:0] static_cmd,
 output reg reserved_rd,reserved_static_col,reserved_write_col,
 output reg [15:0] static_epoch,output wire expected_raw_valid,
 output reg fault,output reg idle
);
 initial if(N!=16)$fatal(1,"qkd_kvpc_s_calendar: the native32 copy families assume N == 16");
 (* keep, ot_rst_split *) reg [39:0] rn__qv;   // KV-PC5: 40 kept copies of rn (async reset of ~1100 flops)
 wire rn = rn__qv[0];
 always @(posedge hck)rn__qv <= {40{rst_n}};
 (* keep *) reg [3:0] rnx;                      // KV-PC5: rn copies that only make the go gates distinct
 always @(posedge hck)rnx <= {4{rst_n}};
 reg we_q,seal_q,go_q;reg [63:0] data_q;
 reg [15:0] epoch_q;reg [5:0] layer_q;
 always @(posedge hck)begin data_q<=cfg_data;epoch_q<=epoch;layer_q<=layer;end
 reg [127:0] image[0:N-1];reg [N-1:0] low_seen,high_seen;
 reg sealed;reg [15:0] active_epoch;reg [18:0] active_row;
 reg [15:0] wait_q[0:N-1];reg [9:0] left_q[0:N-1];reg [3:0] burst_q[0:N-1];
 // lookahead copy families (see header)
 (* keep *) reg [17:0] wv;            // [h*9 + s]: s 0..7 image byte slices, s 8 seen bit
 (* keep *) reg [17*4+3:0] pa;        // addr[3:0] per wv copy
 (* keep *) reg [5*N-1:0] fc;         // [k*5 + 0..3]: event cmd bits [10:0] [21:11] [32:22] [42:33]; +4 mask-static-count
 (* keep *) reg [3*N-1:0] fe;         // [k*3 + 0/1/2]: left+burst / wait[7:0] / wait[15:8]
 (* keep *) reg [2*N-1:0] le;         // [k*2 + 0/1]: live && !go_q, wait[7:0] / wait[15:8]
 (* keep *) reg [3*N-1:0] gk;         // [k*3 + 0/1/2]: go load left+burst / wait[7:0] / wait[15:8]
 (* keep *) reg [N-1:0] i84b;         // copy of image[k][84]
 (* keep *) reg d20c;                 // copy of data_q[20] (feeds only i84b)
 (* keep *) reg [2:0] ga;             // go load active_epoch / active_row / owner+idle
 wire live_any = |{left_q[15]!=0,left_q[14]!=0,left_q[13]!=0,left_q[12]!=0,left_q[11]!=0,left_q[10]!=0,left_q[9]!=0,
                   left_q[8]!=0,left_q[7]!=0,left_q[6]!=0,left_q[5]!=0,left_q[4]!=0,left_q[3]!=0,left_q[2]!=0,
                   left_q[1]!=0,left_q[0]!=0};
 reg [42:0] event_cmd;reg [2:0] event_mask;
 reg static_read;integer fires,i;
 reg [42:0] cmd_k;
 always @*begin
 event_cmd=0;event_mask=0;static_read=0;fires=0;
 for(integer k=0;k<N;k=k+1)begin
  cmd_k = image[k][80:38];
  if(image[k][84])cmd_k[10:1]=active_row[9:0];
  if(i84b[k])cmd_k[19:11]=active_row[18:10];
  if(fc[k*5+0])event_cmd[10:0]=event_cmd[10:0] | cmd_k[10:0];
  if(fc[k*5+1])event_cmd[21:11]=event_cmd[21:11] | cmd_k[21:11];
  if(fc[k*5+2])event_cmd[32:22]=event_cmd[32:22] | cmd_k[32:22];
  if(fc[k*5+3])event_cmd[42:33]=event_cmd[42:33] | cmd_k[42:33];
  if(fc[k*5+4])begin fires=fires+1;event_mask=event_mask | image[k][83:81];static_read=static_read|image[k][85];end
 end
 end
 // next entry state (the original update, branch selects from the copies)
 reg [16*N-1:0] wait_nx;reg [10*N-1:0] left_nx;reg [4*N-1:0] burst_nx;
 reg [N-1:0] fire_nx,live_nx;reg [16*N-1:0] wl,wf,wd;
 always @*begin
 for(integer k=0;k<N;k=k+1)begin
  left_nx[k*10 +: 10] = gk[k*3] ? image[k][25:16] : (fe[k*3] ? left_q[k]-10'd1 : left_q[k]);
  burst_nx[k*4 +: 4] = gk[k*3] ? 4'd0 : (fe[k*3] ? ((burst_q[k]==image[k][29:26]) ? 4'd0 : burst_q[k]+4'd1) : burst_q[k]);
  wl[k*16 +: 16] = image[k][15:0]+16'(MUT==1);
  wf[k*16 +: 16] = (burst_q[k]==image[k][29:26]) ? ((MUT==2)?16'd0:{8'b0,image[k][37:30]}) : 16'd0;
  wd[k*16 +: 16] = wait_q[k]-16'd1;
  wait_nx[k*16+0 +: 8] = gk[k*3+1] ? wl[k*16+0 +: 8] : fe[k*3+1] ? wf[k*16+0 +: 8] : le[k*2] ? wd[k*16+0 +: 8] : wait_q[k][7:0];
  wait_nx[k*16+8 +: 8] = gk[k*3+2] ? wl[k*16+8 +: 8] : fe[k*3+2] ? wf[k*16+8 +: 8] : le[k*2+1] ? wd[k*16+8 +: 8] : wait_q[k][15:8];
  live_nx[k] = left_nx[k*10 +: 10]!=0;
  fire_nx[k] = live_nx[k] && (wait_nx[k*16 +: 16]==0);
 end
 end
 wire allseen = (&low_seen)&&(&high_seen);
 wire sealed_nx = sealed | (seal_q && allseen && !live_any);
 wire pre_nx = sealed_nx && !(|live_nx) && !cfg_we;
 wire gok_a = go && pre_nx && rnx[0], gok_b = go && pre_nx && rnx[1];
 wire ng_f = !go && rnx[2], ng_l = !go && rnx[3];
 wire wv_g = cfg_we && !sealed_nx && !(|live_nx);
 wire raw,unused_put;wire [15:0] unused_epoch;
 // Compiler accounts original controller pin-to-raw offset exactly. This leaf
 // feeds the reservation pins, so its own two pin edges precede this pipe.
 qkd_static_kv_return_calendar raw_calendar(.pll_hbm(hck),.hrst(rn),
 .reserved_rd(reserved_rd),.reserved_static_read(reserved_static_col&&static_read_q),
 .reservation_epoch(static_epoch),.expected_raw_valid(raw),.compiled_hbm_put(unused_put),.expected_return_epoch(unused_epoch));
 assign expected_raw_valid=raw;
 reg static_read_q;
 // image: written only by the wv/pa copies (no reset, as the original; wv is 0 while rn is low)
 always @(posedge hck)
 for(integer k=0;k<N;k=k+1)for(integer h=0;h<2;h=h+1)for(integer s=0;s<8;s=s+1)
  if(wv[h*9+s] && pa[(h*9+s)*4 +: 4]==4'(k))begin
   image[k][h*64+s*8 +: 8]<=data_q[s*8 +: 8];
   if(h==1 && s==2)i84b[k]<=d20c;              // image[k][84] = image[k][64+20]
  end
 always @(posedge hck)d20c<=cfg_data[20];
 always @(posedge hck)pa<={18{cfg_addr[3:0]}};
 always @(posedge hck or negedge rn)
 if(!rn)begin
 we_q<=0;seal_q<=0;go_q<=0;
 wv<=0;fc<=0;fe<=0;le<=0;gk<=0;ga<=0;
 low_seen<=0;high_seen<=0;sealed<=0;active_epoch<=0;active_row<=0;
 static_cmd_owner<=0;static_cmd<=0;reserved_rd<=0;reserved_static_col<=0;reserved_write_col<=0;
 static_epoch<=0;static_read_q<=0;fault<=0;idle<=1;
 for(i=0;i<N;i=i+1)begin wait_q[i]<=0;left_q[i]<=0;burst_q[i]<=0;end
 end else begin
 we_q<=cfg_we;seal_q<=seal;go_q<=go;
 wv<={{9{wv_g && cfg_addr[4]}},{9{wv_g && !cfg_addr[4]}}};
 for(i=0;i<N;i=i+1)begin
  fc[i*5 +: 5]<={5{fire_nx[i]}};
  fe[i*3 +: 3]<={3{fire_nx[i] && ng_f}};
  le[i*2 +: 2]<={2{live_nx[i] && ng_l}};
  gk[i*3 +: 3]<={3{(i<8)?gok_a:gok_b}};
  wait_q[i]<=wait_nx[i*16 +: 16];left_q[i]<=left_nx[i*10 +: 10];burst_q[i]<=burst_nx[i*4 +: 4];
 end
 ga<={gok_b,gok_b,gok_a};
 static_cmd<=event_cmd;reserved_rd<=event_mask[0];reserved_static_col<=event_mask[1];reserved_write_col<=event_mask[2];
 static_epoch<=active_epoch;static_read_q<=static_read;idle<=!live_any && !ga[2];
 if(fires>1 || (event_mask!=0 && (event_mask&(event_mask-1))!=0))fault<=1;
 if(we_q && (sealed || live_any))fault<=1;
 for(i=0;i<N;i=i+1)begin
  if(wv[8] && pa[8*4 +: 4]==4'(i))low_seen[i]<=1;
  if(wv[17] && pa[17*4 +: 4]==4'(i))high_seen[i]<=1;
 end
 if(seal_q)begin if(allseen&&!live_any)sealed<=1;else fault<=1;end
 if(go_q && (!sealed || live_any || we_q))fault<=1;
 if(ga[0])active_epoch<=epoch_q;
 if(ga[1])active_row<=19'(ROW0)+{13'b0,layer_q};
 if(ga[2])static_cmd_owner<=1;
 end
endmodule
