`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 DMA row mover, F6 full-rate version (hgi-takeover 2026-10-09; hgi-e2e F6: the element-serial mover ran one
// element every 4 edges plus a lane round trip per sector: +113k cycles on Qwen L0, +26k on DS L0).
// Same ports / ABI / semantics as hgi-adapters' mover (the peer of ot_hgi_dma_record's move / fence ports):
// Move word (227 b, LSB first): {src space 2, src fmt 3, src base 40, src stride 32, src istride 16, dst space 2,
//   dst fmt 3, dst base 40, dst stride 32, dst istride 16, m 20, n 21}.  Element (o, i), o < m, i < n, row-major:
//   HBM byte  base + o stride + i istride esize      (esize: FP32 / U32 4, BF16 2, FP8E4M3 / INT8 1)
//   VM word   base + o stride + i istride
// LOAD (HBM -> VM): FP32 / U32 the word; BF16 the half << 16; INT8 the integer as FP32 (exact); FP8E4M3 the E4M3 value
//   (NaN code -> 0x7FC00000).  VM -> VM copies the word.  STORE (VM -> HBM): FP32 / U32 the word; BF16 = to_bf16 (RNE);
//   FP8E4M3 = to_fp8 (RNE, saturating at 448) then its code.  Faults: an element not naturally aligned, FP4 / UE8M0, a
//   space other than HBM / VM, a lane fault.  done = every write of the move acknowledged; fence_done when idle.
//
// SECTOR ENGINE (every move whose element strides are 1 on both sides -- rows of contiguous elements; the strided rest
// runs on the element-serial engine ot_hgi_dma_mover_serial, unchanged):
//   R  reader (hgi-1010/c 2026-10-10, HC weight prefetch: lead + hbm-phys svc_dma_hc_sizing): a row is cut into CHUNKS of
//      up to 8 source sectors ending on an 8-sector boundary or the row end.  HBM source: a chunk is ONE native burst on the
//      kport read lane of its stack (r_req_*, lanes 0..3 = stacks 0..3, len 1..8, tag = its first landing slot; the lane
//      answers in order, up to the kport's NO requests outstanding a lane), so every stack the move touches streams at the
//      svc's in-flight limit.  VM source: a chunk is one sector, one VM packet read (4 in flight, in order).  Each chunk
//      allocates its landing slots at issue and pushes a descriptor {elements, first byte, destination sector / byte,
//      row end} into the chunk FIFO (64), in issue order.
//      STRIPE4 (source HBM, base bits [39:37] = 1, spec 6.4): row o reads stack (base[36:35] + o) mod 4 at the local byte
//      address base[34:0] + o x stride: four reader slots (slot k = rows k, k + 4, ..., all on one stack) issue chunks in
//      rotation, so one move keeps the four stacks busy (an HC weight row = 4 quarter rows, one a stack, stride 0).  Rows
//      and their destinations must start 32 B aligned (whole destination sectors a chunk: chunks of different rows never
//      share a destination sector), the destination must be VM; else the move faults.  Other codes than 0 / 1 fault.
//   L  landing: one response sector a cycle (a registered rotating grant over the four read lanes, rsp_rdy) is written
//      into its slot (tag + beat) of the 256-sector landing RAM (ot_sram_1r1w_256x256, slot valid bits in flops);
//   U  unpack (registered): the head chunk's descriptor, up to 8 elements a cycle from the head slot (when it has
//      landed) -- as many as are left in that sector, in the chunk and in the destination sector -- with each lane's
//      destination byte offset and a flush mark at a destination sector end / row end;
//   D  decode (registered): source format -> binary32 (or the raw word on a VM source);
//   E  encode + merge (registered): -> the destination format, merged into the destination sector buffer with byte
//      strobes; a flush pushes the sector into a 4-deep write queue;
//   W  writer: the write queue drains first on its port (VM client / HBM lane), reads use the rest.
// Rate: one destination sector a cycle in the pipe (FP32 / U32 source: 32 B a cycle); an HBM source stack streams at the
// kport's in-flight limit (NO x 4 sectors a round trip), a STRIPE4 move at four times that.  Exactness = the serial
// engine's arithmetic, per element.
// MUT (bench): 1 BF16 store truncates (no RNE; both engines); 2 the sector engine drops a row's last partial sector;
//   3 a burst's beats all land in its first slot (beat ignored); 4 STRIPE4 reads / writes every row on stack base[36:35].
// B2 (el1011-hbm-b2-cp, per-quadrant HBM die, B2_CONVENTION): B2 = 1 makes this instance quadrant QID, the owner of HBM
//   stack QID.  A STRIPE4 move (sent to all four quadrants) runs only the reader slot whose rows live on stack QID (the
//   other slots are never activated: no HBM request, no VM access, not counted; done when the own rows land; no own row
//   -> done at once).  A linear move whose HBM side starts on another stack is refused at the command station, a request
//   to another stack later in a move (a row crossing the stack) faults before it issues, and so does any request of the
//   serial engine's kport lane off stack QID (fail-closed, mv_fault).  HBM lanes other than QID are constant 0 and their
//   inputs ignored.  The serial engine has no STRIPE4 addressing: a strided move with a STRIPE4 side is refused.
//   B2 = 0: unchanged.  MUT_B2 (bench): 1 the slot of stack QID + 1 is served on lane QID (rows off by one), 2 stack
//   QID's lane is driven on output lane QID + 1 (wrong lane).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_b2_dma_mv #(
    parameter integer MUT_SEAM = 0,
    parameter integer MUT_RNE = 0,        // mutant: BF16 store truncates (no round to nearest even)
    parameter integer MUT = 0,
    parameter integer KOUT = 64,          // HBM writes in flight (the per-stack lanes)
    parameter integer VR2 = 0,            // 1: VM-source sectors on the VM's DMA wide READ group (vr2q / vr2r), else the packet client
    parameter integer SVR2 = -1,          // the SECTOR engine's VM-source reads on the read group (-1: = VR2).  hbm-fq/dma 10-11 audit:
                                          //   with KVW = 1 set 0 (the sector engine reads through the packet client; the read group's
                                          //   32-lane response capture / 32-way drain belong to the KV engine only)
    parameter integer KVW = 0,            // 1 (needs VR2 = 1): the KV write-back engine ot_hgi_dma_kvw takes every raw VM -> HBM row
                                          // copy (KVWB_DS / FP32 / U32 STORE of whole sectors, linear destination), 64 B a cycle
    parameter integer PX = 0,             // hbm-fq/mvf 10-11 (route mover_el 89c140d31 post-CTS -435 ps wq_h -> rsa[1][41]: the
                                          // write-queue head-lane mux -> iss_kw -> reader pick -> r_k-muxed 42-b chunk add in one
                                          // cycle; sel_s -> vmq 338-b output mux): 1 = registered write-queue head lane, every slot's
                                          // next source / destination / row values precomputed in R0 (the issue is a select),
                                          // registered vmq output (+1 cycle on VM packet requests)
                                          // 2 (hbm-fq/mvf 10-11, route px2a-75a1aed59 TT -143: r_rsp_we pin -> l_take -> 4-way
                                          // 256-b AND-OR -> lt_* 12-17 levels behind the pin; sbase/sstb -> rsa / dbase/dstb -> rdd
                                          // 42-b (3-operand) adds at go_f 26-29 levels; sstw -> s_nc settle add; u_ser.sa self-loop):
                                          // = PX 1 + read-response pin flops (raw capture, the lane pick one cycle later, +1 cycle
                                          // on the landing), every slot's row start and next-row start computed straight from
                                          // base + m x stride (m <= 8) as carry-save + three 14-b chunks with registered carries on
                                          // the existing go_f / go_q2 / go_q3 setup edges (no extra command cycle), serial engine
                                          // next addresses precomputed (SXP: +1 cycle a command)
    parameter integer B2 = 0,             // 1: per-quadrant instance (B2 die): serves HBM stack QID only (see the header)
    parameter integer QID = 0,            // B2: this quadrant = its HBM stack (0..3)
    parameter integer MUT_B2 = 0          // B2 bench mutant: 1 rows of stack QID + 1 on lane QID; 2 lane QID driven on lane QID + 1
) (
    output wire [264:0] land_write,
    output wire [63:0] land_read,
    output wire [6:0] source_format,
    input wire [306:0] decoded,
    output wire ser_mv_v,
    output wire [226:0] ser_mv,
    input wire ser_mv_rdy,
    input wire ser_mv_done,
    input wire ser_mv_fault,
    input wire ser_fence_rdy,
    input wire ser_k_req_v,
    output wire ser_k_req_rdy,
    input wire ser_k_req_we,
    input wire [36:0] ser_k_req_addr,
    input wire [255:0] ser_k_req_wdata,
    input wire [31:0] ser_k_req_wstrb,
    input wire [15:0] ser_k_req_tag,
    output wire ser_k_rsp_v,
    input wire ser_k_rsp_rdy,
    output wire ser_k_rsp_we,
    output wire [255:0] ser_k_rsp_data,
    output wire ser_k_fault,
    output wire [273:0] ser_vmr,
    input wire kv_c_rdy, kv_idle_w, kv_creq, kv_src, kv_done,
    input wire [31:0] kv_req_v, input wire [3:0] kv_wv, kv_wo,
    input wire [147:0] kv_wa, input wire [1023:0] kv_wd,
    output reg kc_v, output reg [14:0] kc_vs, kc_vst,
    output reg [31:0] kc_ds, kc_dst, output reg [17:0] kc_ns, output reg [19:0] kc_m,
    output wire kc_gnt, output wire [191:0] credit_source,
    output wire [3:0] kc_wrdy,
    input wire [1:0] qid, output wire vm_serial_owner,
    input  wire          clk,
    input  wire          rst_n,
    input  wire          mv_v,
    output wire          mv_rdy,
    input  wire [226:0]  mv,
    output reg           mv_done,
    output reg           mv_fault,
    output reg           mv_src,      // pulse: every source sector of the move has been read and landed (posted
                                      // STORE / KVWB retire here; the VM / HBM source may be overwritten from now on)
    input  wire          fence_v,
    output wire          fence_rdy,
    output reg           fence_done,
    // kport lane (HBM)
    output wire          k_req_v,
    input  wire          k_req_rdy,
    output wire          k_req_we,
    output wire [36:0]   k_req_addr,
    output wire [255:0]  k_req_wdata,
    output wire [31:0]   k_req_wstrb,
    output wire [15:0]   k_req_tag,
    input  wire          k_rsp_v,
    output wire          k_rsp_rdy,
    input  wire          k_rsp_we,
    input  wire [255:0]  k_rsp_data,
    input  wire          k_fault,
    // HBM lanes (hgi-1010/c): kport lane of stack l.  Reads: bursts {addr 37, len 1..8, tag 16 = the first landing slot},
    // answered in request order (rsp_tag = the request's tag, rsp_last on its last sector); rsp_rdy = this lane's
    // registered landing grant.  Writes (STORE): one full sector a request, many outstanding; rsp_we = its acknowledgement
    // (always accepted)
    output wire [3:0]     r_req_v,
    input  wire [3:0]     r_req_rdy,
    output wire [4*37-1:0] r_req_addr,
    output wire [4*4-1:0] r_req_len,
    output wire [4*16-1:0] r_req_tag,
    output wire [3:0]     r_req_we,                     // a write (STORE to HBM): one full sector, acknowledged by rsp_we
    output wire [4*256-1:0] r_req_wdata,
    output wire [4*32-1:0] r_req_wstrb,
    input  wire [3:0]     r_rsp_v,
    input  wire [3:0]     r_rsp_we,
    output wire [3:0]     r_rsp_rdy,
    input  wire [4*16-1:0] r_rsp_tag,
    input  wire [3:0]     r_rsp_last,
    input  wire [4*256-1:0] r_rsp_data,
    // VM wide READ group 2 = DMA (VR2 = 1; b's ot_hgi_vm_die contract): up {c_req, 32 lanes x {v, sector 15}}; down
    // {c_gnt, credits 32, 32 lanes x {v, data 256}}; lane b serves sectors s[4:0] = b, in order a lane, LQ credits a lane;
    // c_req is held until every credit is home (burst ownership).  The mover keeps one sector in flight a lane.
    output wire [512:0]  vr2q,
    input wire [32:0] vr2r_ctrl,
    // VM packet client
    output wire [337:0]  vmq,
    input  wire [273:0]  vmr,
    // VM WIDE WRITE PORT lane (hgi-takeover 2026-10-10, coordinator decision): the sector engine writes its VM
    // destination sectors here, one a cycle, never back-pressured, {v, sector 15, wdata 256, word mask 8}; wl_done
    // returns when the write is in the macro (ot_hgi_vm_unit wq / wq_done)
    output reg  [279:0]  wl,
    input  wire          wl_done
);
    wire command_valid, command_ready;
    wire [226:0] command_data;
    ot_hgi_b2_dma_cmd_pin u_cmd_pin(.clk(clk), .rst_n(rst_n), .in_v(mv_v), .in_data(mv), .in_ready(mv_rdy),
       .out_v(command_valid), .out_data(command_data), .out_ready(command_ready));
    // SVR2=0: sector engine receives group grant/credits only; data pins belong to closed hold leaves.
    wire [8256:0] vr2r = {vr2r_ctrl,8224'd0};
    // ---- per-stack lanes as the engines see them (ir_*); B2: only lane QID reaches the ports (output lane OL)
    localparam integer OL = (MUT_B2 == 2) ? ((QID + 1) % 4) : QID;
    wire [3:0] ir_req_v, ir_req_we, ir_req_rdy, ir_rsp_v, ir_rsp_we, ir_rsp_rdy, ir_rsp_last;
    wire [4*37-1:0] ir_req_addr; wire [4*4-1:0] ir_req_len; wire [4*16-1:0] ir_req_tag, ir_rsp_tag;
    wire [4*256-1:0] ir_req_wdata, ir_rsp_data; wire [4*32-1:0] ir_req_wstrb;
    if (B2 == 0) begin : g_lane
        assign r_req_v = ir_req_v; assign r_req_we = ir_req_we; assign r_req_addr = ir_req_addr; assign r_req_len = ir_req_len;
        assign r_req_tag = ir_req_tag; assign r_req_wdata = ir_req_wdata; assign r_req_wstrb = ir_req_wstrb;
        assign r_rsp_rdy = ir_rsp_rdy;
        assign ir_req_rdy = r_req_rdy; assign ir_rsp_v = r_rsp_v; assign ir_rsp_we = r_rsp_we; assign ir_rsp_tag = r_rsp_tag;
        assign ir_rsp_last = r_rsp_last; assign ir_rsp_data = r_rsp_data;
    end else begin : g_lane_b2
        reg [1:0] rnq; reg [361:0] rh, rt;
        reg rb_ready, rb_valid;
        wire rb_push = ir_req_v[QID] && rb_ready;
        wire rb_pop = rb_valid && r_req_rdy[OL];
        wire [361:0] rb_in_good = {ir_req_we[QID],ir_req_addr[QID*37 +: 37]+(37'(qid_q)<<35),
           ir_req_len[QID*4 +: 4],ir_req_tag[QID*16 +: 16],ir_req_wdata[QID*256 +: 256],ir_req_wstrb[QID*32 +: 32],16'd0};
        wire [361:0] rb_in = rb_in_good ^ ((MUT_SEAM == 4 && ir_req_we[QID]) ? (362'd1 << 48) : 362'd0);
        always @(posedge clk or negedge rn) begin
           if (!rn) begin rnq <= 0; rb_ready <= 1; rb_valid <= 0; end
           else begin
             rb_ready <= (rnq + {1'b0,rb_push} - {1'b0,rb_pop}) < 2;
             rb_valid <= (rnq + {1'b0,rb_push} - {1'b0,rb_pop}) != 0;
             case ({rb_push,rb_pop})
              2'b10: begin if (rnq == 0) rh <= rb_in; else rt <= rb_in; rnq <= rnq + 1'b1; end
              2'b01: begin rh <= rt; rnq <= rnq - 1'b1; end
              2'b11: begin if (rnq == 1) rh <= rb_in; else begin rh <= rt; rt <= rb_in; end end
              default: begin end
             endcase
           end
        end
        for (genvar l = 0; l < 4; l = l + 1) begin : ln
            if (l == OL) begin : o
                assign r_req_v[l] = rb_valid; assign r_req_we[l] = rh[361];
                assign r_req_addr[l*37 +: 37] = rh[360:324]; assign r_req_len[l*4 +: 4] = rh[323:320];
                assign r_req_tag[l*16 +: 16] = rh[319:304]; assign r_req_wdata[l*256 +: 256] = rh[303:48];
                assign r_req_wstrb[l*32 +: 32] = rh[47:16]; assign r_rsp_rdy[l] = 1'b1; // B2 owns ONE lane: raw pin capture accepts one beat each clock; no lane arbitration.
            end else begin : z
                assign r_req_v[l] = 1'b0; assign r_req_we[l] = 1'b0; assign r_req_addr[l*37 +: 37] = 37'd0; assign r_req_len[l*4 +: 4] = 4'd0;
                assign r_req_tag[l*16 +: 16] = 16'd0; assign r_req_wdata[l*256 +: 256] = 256'd0; assign r_req_wstrb[l*32 +: 32] = 32'd0;
                assign r_rsp_rdy[l] = 1'b0;
            end
            if (l == QID) begin : i
                assign ir_req_rdy[l] = rb_ready; assign ir_rsp_v[l] = r_rsp_v[OL]; assign ir_rsp_we[l] = r_rsp_we[OL];
                assign ir_rsp_tag[l*16 +: 16] = r_rsp_tag[OL*16 +: 16]; assign ir_rsp_last[l] = r_rsp_last[OL];
                assign ir_rsp_data[l*256 +: 256] = r_rsp_data[OL*256 +: 256];
            end else begin : iz
                assign ir_req_rdy[l] = 1'b0; assign ir_rsp_v[l] = 1'b0; assign ir_rsp_we[l] = 1'b0; assign ir_rsp_tag[l*16 +: 16] = 16'd0;
                assign ir_rsp_last[l] = 1'b0; assign ir_rsp_data[l*256 +: 256] = 256'd0;
            end
        end
    end
    // B2: a request on an internal lane other than QID (never issued: its lane is cut off) faults (backstop)
    wire b2_lx = B2 != 0 && |(ir_req_v & ~(4'd1 << QID));
    // the sector engine's port registers (the serial engine has its own; sel_s picks)
    wire f_kv = 1'b0, f_kwe = 1'b0; wire [36:0] f_ka = 37'd0; wire [255:0] f_kd = 256'd0; wire [31:0] f_ks = 32'd0; reg [337:0] f_vmq;
    // hgi-1010/c: the sector engine's HBM reads and writes use the per-stack lanes (r_*); kport lane 2 is the serial engine's
    assign k_req_tag = 16'h4D56;
    assign k_rsp_rdy = 1'b1;
    // ================================================================ dispatch: sector engine or serial engine
    // registered reset (async assert, release two edges after rst_n): the port reset no longer reaches the D / recovery
    // pins of the whole mover (route 00007e219 IO paths rst_n -> f_vmq / u_ser.i)
    reg [1:0] rq; always @(posedge clk or negedge rst_n) if (!rst_n) rq <= 2'b00; else rq <= {rq[0], 1'b1};
    wire rn = rq[1];
    // registered boundary (submit lint: input -> register <= 16 levels): a command station, pin flops on the lane and
    // VM responses (+1 cycle each), and the lane request issues only from an empty request register (k_req_rdy only
    // clears it)
    reg cv_q; reg [226:0] cm_q;
    reg kr_v, kr_we; reg [255:0] kr_d; reg [273:0] vr_q;
    reg wld_q; always @(posedge clk) wld_q <= wl_done;     // wide-port done pin flop (hgi-1010/c: wl_done -> wr_in was 17 levels)
    always @(posedge clk or negedge rn)
        if (!rn) begin kr_v <= 1'b0; vr_q[273] <= 1'b0; end
        else begin kr_v <= k_rsp_v; vr_q[273] <= vmr_local[273]; end
    always @(posedge clk) vr_q[272:0] <= vmr_local[272:0];
    always @(posedge clk) begin kr_we <= k_rsp_we; kr_d <= k_rsp_data; end
    wire fast_cmd = (cm_q[92:77] == 16'd1) && (cm_q[185:170] == 16'd1);     // src istride 1 and dst istride 1
    // hbm-fq/dma (KVW = 1): a raw VM -> HBM row copy goes to the KV write-back engine: VM source, HBM linear destination,
    // FP32 / U32 on both sides, istrides 1, VM rows of whole sectors (base, stride, n multiples of 8 words), 32 B aligned
    // destination rows; any other move waits for that engine to be idle (its posted writes drained)
    localparam integer SV = (SVR2 >= 0) ? SVR2 : VR2;   // the sector engine uses the read group
    wire kv_ok = KVW != 0 && VR2 != 0 && fast_cmd && cm_q[1:0] == 2'd1 && cm_q[94:93] == 2'd0 && cm_q[137:135] == 3'd0 &&
                 (cm_q[4:2] == 3'd0 || cm_q[4:2] == 3'd5) && (cm_q[97:95] == 3'd0 || cm_q[97:95] == 3'd5) &&
                 cm_q[7:5] == 3'd0 && cm_q[47:45] == 3'd0 && cm_q[208:206] == 3'd0 && cm_q[102:98] == 5'd0 &&
                 cm_q[142:138] == 5'd0 && cm_q[205:186] != 20'd0 && cm_q[226:206] != 21'd0;

    reg kc_pending, kv_idle_q;
    always @(posedge clk or negedge rn) if (!rn) kv_idle_q <= 1'b1; else kv_idle_q <= kv_idle_w;
    wire kv_idle = (KVW != 0) ? kv_idle_q && !kc_pending && !kc_v : 1'b1;
    reg [1:0] qid_q; always @(posedge clk) qid_q <= (MUT_SEAM == 6) ? qid + 2'd1 : qid;
    wire [273:0] vmr_local = vmr; // already owned and registered by the packet-face leaf
    // B2: refused at the command station (fail-closed, no request): a linear HBM side starting on another stack (the KV
    // engine streams a move on its row-0 stack), a strided move with a STRIPE4 side (the serial engine addresses linearly)
    wire b2_bad = B2 != 0 && ((cm_q[1:0] == 2'd0 && cm_q[44:42] == 3'd0 && cm_q[41:40] != 2'(QID)) ||
                              (cm_q[94:93] == 2'd0 && cm_q[137:135] == 3'd0 && cm_q[134:133] != 2'(QID)) ||
                              (!fast_cmd && ((cm_q[1:0] == 2'd0 && cm_q[44:42] != 3'd0) || (cm_q[94:93] == 2'd0 && cm_q[137:135] != 3'd0))));
    wire b2_flt = cv_q && b2_bad;
    wire kv_take = cv_q && kv_ok && (!kc_v || kv_c_rdy) && !b2_bad;               // into the KV engine's descriptor FIFO
    wire cv_go = cv_q && !kv_ok && kv_idle && !b2_bad;                 // to the sector / serial engines
    reg  busy_f; reg src_sent;
    wire ko_ld;                                                         // the lane output register takes a request                                                        // the sector engine owns the ports
    reg  sel_s;                                                         // the serial engine owns the ports
    wire s_mv_rdy, s_mv_done, s_mv_fault, s_fence_rdy, s_fence_done;
    wire s_kv, s_kwe; wire [36:0] s_ka;
    wire b2_kx;                                                         // B2: the serial engine's lane request is off stack QID
    wire [255:0] s_kd; wire [31:0] s_ks; wire [15:0] s_kt; wire s_krr;
    reg  f_fault;
    assign command_ready = !busy_f && !cv_q && !sel_s && s_mv_rdy && !f_fault;
    wire pin_s_kv, pin_s_kwe, s_pin_ready; wire [36:0] pin_s_ka;
    wire [255:0] pin_s_kd; wire [31:0] pin_s_ks; wire [15:0] pin_s_kt;
    wire [341:0] serial_head;
    ot_hgi_b2_dma_cmd_pin #(.W(342)) u_serial_kpin(.clk(clk), .rst_n(rn), .in_v(pin_s_kv),
      .in_data({pin_s_kwe,pin_s_ka,pin_s_kd,pin_s_ks,pin_s_kt}), .in_ready(s_pin_ready),
      .out_v(s_kv), .out_data(serial_head), .out_ready(ko_ld && sel_s && !b2_kx));
    assign {s_kwe,s_ka,s_kd,s_ks,s_kt}=serial_head;
    reg ser_go;
    always @(posedge clk or negedge rn) if (!rn) ser_go<=0; else ser_go<=cv_go && !fast_cmd && cm_q[94:93] != 2'd0;
    assign ser_mv_v = ser_go;
    assign ser_mv = cm_q;
    assign s_mv_rdy = ser_mv_rdy;
    assign s_mv_done = ser_mv_done;
    assign s_mv_fault = ser_mv_fault;
    assign s_fence_rdy = ser_fence_rdy;
    assign pin_s_kv = ser_k_req_v;
    assign ser_k_req_rdy = s_pin_ready;
    assign pin_s_kwe = ser_k_req_we;
    assign pin_s_ka = ser_k_req_addr;
    assign pin_s_kd = ser_k_req_wdata;
    assign pin_s_ks = ser_k_req_wstrb;
    assign pin_s_kt = ser_k_req_tag;
    assign ser_k_rsp_v = kr_v && sel_s;
    assign s_krr = ser_k_rsp_rdy;
    assign ser_k_rsp_we = kr_we;
    assign ser_k_rsp_data = kr_d;
    // Register the fault seam at the MV face; external fault never crosses the tile combinationally.
    reg ser_k_fault_q;
    always @(posedge clk or negedge rn)
        if (!rn) ser_k_fault_q <= 1'b0;
        else ser_k_fault_q <= (k_fault && sel_s) || b2_kx;
    assign ser_k_fault = ser_k_fault_q;
    assign vm_serial_owner = sel_s;
    assign ser_vmr = sel_s ? vr_q : 274'd0;
    reg fence_pending;
    wire fence_available = !busy_f && s_mv_rdy && s_fence_rdy && kv_idle && !cv_q && !command_valid;
    assign fence_rdy = !fence_pending;
    always @(posedge clk or negedge rn) begin
       if (!rn) fence_pending <= 0;
       else begin
          if (fence_v && fence_rdy) fence_pending <= 1;
          if (fence_pending && fence_available) fence_pending <= 0;
       end
    end
    // ================================================================ sector engine
    function automatic [2:0] esz(input [2:0] f);
        esz = (f == 3'd0 || f == 3'd5) ? 3'd4 : (f == 3'd1) ? 3'd2 : 3'd1;
    endfunction
    function automatic [15:0] to_bf16(input [31:0] x);           // RNE (hdc_golden to_bf16), NaN kept quiet
        reg [31:0] r;
        begin
            if (x[30:23] == 8'hFF && x[22:0] != 0) to_bf16 = {x[31:16]} | 16'h0040;
            else if (MUT_RNE) to_bf16 = x[31:16];
            else begin r = x + 32'h7FFF + {31'd0, x[16]}; to_bf16 = r[31:16]; end
        end
    endfunction
    function automatic [7:0] to_e4m3(input [31:0] x);            // to_fp8 (RNE, binade quantum, saturate 448) -> code
        reg [7:0] ex; reg [23:0] mant; integer sh; reg [24:0] q; reg [7:0] code; reg [4:0] e4; reg [3:0] mq;
        begin
            ex = x[30:23];
            if (ex == 8'hFF) to_e4m3 = {x[31], 7'h7E};
            else if (ex >= 8'd136) to_e4m3 = {x[31], 7'h7E};
            else begin
                mant = (ex == 8'd0) ? 24'd0 : {1'b1, x[22:0]};
                sh = (ex >= 8'd121) ? 20 : (20 + 121 - ex);
                if (sh > 24) begin q = 25'd0; end
                else begin
                    q = {1'b0, mant} >> sh;
                    if (sh > 0 && mant[sh - 1] && ((mant & ((24'd1 << (sh - 1)) - 24'd1)) != 0 || q[0])) q = q + 25'd1;
                end
                if (ex >= 8'd121) begin
                    e4 = ex - 8'd120; mq = q[4] ? 4'd8 : q[3:0];
                    if (q[4]) e4 = e4 + 5'd1;
                    code = (e4 > 5'd15) ? 8'h7F : {e4[3:0], mq[2:0]};
                end else code = {1'b0, 4'd0, q[2:0]} + (q[3] ? 8'd8 : 8'd0);
                if (code > 8'h7E) code = 8'h7E;
                to_e4m3 = (code == 8'd0) ? 8'd0 : {x[31], code[6:0]};
            end
        end
    endfunction
    // ---- command
    reg        go_f;
    reg [1:0]  ssp, dsp; reg [2:0] sf, df; reg [31:0] sst, dst; reg [33:0] sstb, dstb; reg [19:0] mm; reg [20:0] nn;   // sstb / dstb: row strides in bytes
    reg [2:0]  ses, des;                                    // element bytes (VM: 4)
    reg [1:0]  sl2, dl2;                                    // log2 of the element bytes: every size product is a shift
    reg [23:0] nnb;                                         // row bytes on the source side = nn << sl2
    reg [41:0] sbase, dbase;                                // byte addresses (VM: word x 4)
    // ---- reader: up to four slots (STRIPE4: slot k = rows k, k + 4, ...; else slot 0 = every row)
    reg        stp, stpd;                                   // STRIPE4 source / destination
    // PX3 (idle1012, route px3a-344de5a43 TT -86: stp/stpd -> m -> 8-way x-shift select -> carry-save -> 14-b add, 27-30
    // levels): the base + m x stride addends (a1, a2, carry-in) of every slot are REGISTERED on the command-accept edge,
    // decoded from cm_q (same edge as sstb / dstb / stp / stpd), so the go_f / go_q2 / go_q3 chunk adds start from flops
    // (carry-save 2 levels + 14-b add); the row step (4 under STRIPE4, else 1) is its own flop (no stp fanout).
    reg [41:0] op_a1 [0:3][0:3], op_a2 [0:3][0:3]; reg op_ci [0:3][0:3]; reg [19:0] ro_inc;
    reg [1:0]  s0, d0;                                      // STRIPE4: row 0's source / destination stack
    reg [41:0] sstw, dstw;                                  // a slot's row step (STRIPE4: 4 strides)
    reg [3:0]  ract;                                        // slot active (rows left to issue)
    reg [19:0] ro [0:3];                                    // slot's row index
    reg [41:0] rsa [0:3], rnsa [0:3];                       // next chunk's source byte (STRIPE4: stack-local), next row's start
    reg [41:0] rdd [0:3], rndd [0:3];                       // next chunk's destination byte, next row's start
    reg [23:0] rrl [0:3];                                   // source bytes left in the slot's row
    reg [1:0]  rrr;                                         // rotation
    wire       r_done = ract == 4'd0;                       // every chunk issued
    // ---- read lanes (one a stack): request registers, landing grant, beat counters
    reg [3:0] lq_v; reg [36:0] lq_a [0:3]; reg [3:0] lq_n [0:3]; reg [7:0] lq_t [0:3];
    reg [3:0] lq_we; reg [255:0] lq_d [0:3]; reg [31:0] lq_s [0:3];
    reg  [1:0] wq_hl;                                       // PX: the write queue head's lane, registered
    wire [1:0] w_l = (B2 != 0) ? 2'(QID) : wq_head[319:318]; // the write queue head's stack (its lane)
    // ---- VM read group (VR2): per lane a sector in flight, its landing slot, the held response, the credits
    localparam integer GLQ = 32;
    reg [31:0] g_busy, g_hv; reg [7:0] g_slot [0:31]; reg [255:0] g_d [0:31]; reg [5:0] g_cr [0:31]; reg [4:0] g_rr;
    // pin flops (registered boundary: route lint 98f8152b3 counted 96 levels from c_gnt through the reader issue)
    reg g_gnt; reg [31:0] g_crp; reg [512:0] s_vr2q;
    // Registered source seam; masking/OR is captured in the independent group face.
    assign vr2q = s_vr2q;
    always @(posedge clk or negedge rn) if (!rn) begin g_gnt <= 1'b0; g_crp <= 32'd0; end
                                        else begin g_gnt <= vr2r[8256]; g_crp <= vr2r[8255:8224]; end
    reg g_dv; reg [4:0] g_di;                               // the held response drained into the landing RAM this cycle
    always @* begin g_dv = 1'b0; g_di = 5'd0;
        for (integer t = 31; t >= 0; t = t - 1) if (g_hv[5'(g_rr + 5'(t))]) begin g_dv = 1'b1; g_di = 5'(g_rr + 5'(t)); end end
    reg g_home; always @* begin g_home = 1'b1; for (integer b = 0; b < 32; b = b + 1) if (g_cr[b] != 6'(GLQ)) g_home = 1'b0; end
    reg [3:0] lg; reg [1:0] lgi; reg [2:0] lbc [0:3];
    // ---- chunk FIFO (issue order) and the staged head descriptor {slot 2, rend, dp 6, dsec 37, sp 5, elements 9}
    localparam integer CF = 64;
    reg [6:0] cf_n; wire [59:0] cf_head; wire cf_hv, cf_ovf; reg cd_v; reg [59:0] cd;   // + {slot 2} at [59:58]
    // ---- unpack state (the current chunk)
    // (route 51ae5ce55: the elements left in the head source sector (s_room) and in the destination sector (d_room) are
    //  registers that count down)
    reg u_cv; reg [8:0] u_left; reg [4:0] u_sp; reg [36:0] u_dsec; reg [5:0] u_dp; reg u_rend; reg [5:0] s_room, d_room;
    // ---- landing RAM (slots allocated at issue in order, filled in any order, consumed in order)
    localparam integer SFD = 256;
    localparam integer SB = 8;
    reg [SB-1:0] sf_h, sf_a, v_ptr; reg [8:0] sf_n; reg [SFD-1:0] lv;
    reg lw_v; reg [SB-1:0] lw_a; reg [255:0] lw_d;          // landing write stage
    // ---- port in-flight accounting
    reg [7:0] k_in; reg [2:0] v_in; reg [7:0] v_kind;      // lane 2 (writes) / VM client (reads), kinds oldest at [0]
    reg [8:0] rd_in;                                        // source sectors issued, not landed
    // ---- write queue
    wire [324:0] wq_head; wire wq_hv, wq_ovf; reg [4:0] wq_n;   // 16: the 8-stage pipe
    reg [8:0] wr_in;                                          // writes issued, not acknowledged
    // ---- pipeline registers
    // hgi-1010/c (route f628d5015: sf_h -> p1_sec, the 64-entry landing read under the unpack enable, 18 levels): p1 keeps
    // the slot address, the PR stage reads the slot from that register (+1 cycle); the reader stops 2 slots short of
    // full, so a popped slot is not rewritten before PR has read it
    reg        p1_v; reg [3:0] p1_k; reg [SB-1:0] p1_h; reg [4:0] p1_sp; reg [5:0] p1_dp; reg [36:0] p1_dsec; reg p1_fl;
    // extract (px) and convert (p2) are separate stages; encode (pe) and byte placement (p3) are separate stages
    // (route 51ae5ce55: p2_w / des -> p3_d, 31 levels: the encoders and the variable placement in one cycle)
    reg        p2_v; reg [3:0] p2_k; reg [255:0] p2_w; reg [5:0] p2_dp; reg [36:0] p2_dsec; reg p2_fl;
    reg        pe_v; reg [7:0] pe_lv; reg [255:0] pe_e; reg [5:0] pe_dp; reg [36:0] pe_dsec; reg pe_fl, pe_keep;
    reg        p3_v; reg [255:0] p3_d; reg [31:0] p3_s; reg [36:0] p3_dsec; reg p3_fl, p3_keep;
    // hgi-1010/c (route bf6565982 TT -107 / -168, SS -570: dl2 / pe_dp -> p3_d, 23-25 levels = per-element variable
    // placement): PACK (pe -> pk, registered: the k encoded elements contiguous from byte 0, by dl2) then SHIFT (pk -> p3:
    // one 32-byte barrel shift by pe_dp and the byte mask with it).  +1 cycle in the pipe.
    reg        pk_v; reg [255:0] pk_d; reg [31:0] pk_s; reg [5:0] pk_dp; reg [36:0] pk_dsec; reg pk_fl, pk_keep;
    reg [255:0] db_dat [0:3]; reg [31:0] db_strb [0:3]; reg [3:0] db_dirty;   // a merge buffer a reader slot (rows interleave)
    reg [1:0] p1_sl, p2_sl, pa_sl, pe_sl, pk_sl, p3_sl, u_sl;
    // ---- source sector issue
    wire src_hbm = (ssp == 2'd0), dst_hbm = (dsp == 2'd0);
    // ---- unpack decision (combinational on registered state)
    reg [3:0] u_k; reg u_fl; reg u_pop; reg u_go; reg u_end;
    always @* begin : unp
        reg [5:0] l8, m1;
        l8 = (u_left > 9'd8) ? 6'd8 : {2'd0, u_left[3:0]};            // elements left in the chunk, at most 8
        m1 = (s_room < d_room) ? s_room : d_room;
        u_k = 4'((l8 < m1) ? l8 : m1);
        u_end = u_left <= 9'({5'd0, u_k});                             // the chunk ends with this step
        u_go = busy_f && u_cv && go_q3 && lv[sf_h] && wq_room;
        u_fl = ({2'd0, u_k} == d_room) || (u_end && u_rend);          // the destination sector is full / row end
        u_pop = ({2'd0, u_k} == s_room) || u_end;                     // the source sector is used up / chunk end
    end
    // ---- reader: each slot's next chunk (combinational on registered slot state)
    reg [3:0] c_ok; reg [8:0] c_bv [0:3]; reg [36:0] c_ea [0:3]; reg [3:0] c_ns [0:3]; reg [8:0] c_by [0:3]; reg [3:0] c_rend; reg [3:0] c_bad;
    reg [36:0] c_ds [0:3];                                  // the chunk's first destination sector (STRIPE4: its stack)
    always @* begin : chk
        for (integer k = 0; k < 4; k = k + 1) begin : ck
            reg [3:0] lm; reg [8:0] bav; reg [1:0] st;
            lm = src_hbm ? (4'd8 - {1'b0, rsa[k][7:5]}) : 4'd1;       // sectors to the 8-sector boundary (VM: one)
            bav = {lm, 5'd0} - {4'd0, rsa[k][4:0]};
            c_bv[k] = bav;
            c_by[k] = ({15'd0, bav} < rrl[k]) ? bav : rrl[k][8:0];
            c_rend[k] = {15'd0, bav} >= rrl[k];
            c_ns[k] = 4'(({4'd0, rsa[k][4:0]} + c_by[k] + 9'd31) >> 5);
            st = (MUT == 4) ? s0 : (B2 != 0 && MUT_B2 == 1) ? 2'(QID) : s0 + 2'(k);
            c_ea[k] = stp ? {st, rsa[k][34:0]} : rsa[k][36:0];
            c_bad[k] = (stp && rsa[k][41:35] != 7'd0) || (stpd && rdd[k][41:35] != 7'd0) ||  // STRIPE4: beyond the stack-local space
                       (B2 != 0 && src_hbm && !stp && rsa[k][41:35] != 7'(QID));              // B2: a linear read off stack QID
            c_ds[k] = stpd ? {5'd0, (MUT == 4) ? d0 : (B2 != 0 && MUT_B2 == 1) ? 2'(QID) : 2'(d0 + 2'(k)), rdd[k][34:5]} : rdd[k][41:5];
            // the slot's own readiness (the parts that change only with the slot's state or the read group's lane state)
            c_ok[k] = ract[k] && (src_hbm || SV == 0 || (!g_busy[rsa[k][9:5]] && g_cr[rsa[k][9:5]] != 6'd0));
        end
    end
    // hbm-fq/dma 2026-10-11 (textbook audit class 5, route e666b2c25 TT -616.7 ps on rsa[2][9] -> rdd[2][35], 1,784 ps
    // arrival: the lane-indexed busy / credit lookup, the 4-slot rotating pick and the r_k-selected chunk add in one cycle):
    // the reader decision is PIPELINED.  R0 registers each slot's next chunk (q_*) and its readiness; R1 picks among the
    // registered slots.  A slot that issued in the previous cycle is masked (its q_* predate the issue), and so is any slot
    // on the read-group lane issued in the previous cycle (its busy / credit predate it); the kport lane, the write issue
    // and the packet client's count stay live (one register compare each).  +1 cycle per chunk on one slot.
    reg [3:0] q_ok, q_rend, q_bad; reg [36:0] q_ea [0:3]; reg [3:0] q_ns [0:3]; reg [8:0] q_by [0:3]; reg [36:0] q_ds [0:3];
    reg [4:0] q_ln [0:3]; reg l_v; reg [1:0] l_k; reg [4:0] l_ln;
    // PX: each slot's next values on issue (valid under the same mask as q_*: a slot that issued last cycle is not picked)
    wire [41:0] q_san [0:3]; reg [23:0] q_rln [0:3]; reg [19:0] q_ron [0:3]; reg [3:0] q_rlst;
    // Split the 37-bit next-chunk increment: parallel digit increments in R0,
    // registered carry, two-input high select in R1. Same chunk decision cycle.
    reg [13:0] sa_inc_lo [0:3]; reg [22:0] sa_inc_hi0 [0:3], sa_inc_hi1 [0:3]; reg [3:0] sa_inc_c;
    for (genvar si=0; si<4; si=si+1) begin : g_sa_increment
       wire [36:0] chunk_addr = src_hbm ? {3'd0,rsa[si][41:8]} : rsa[si][41:5];
       wire [36:0] addr_next = {sa_inc_c[si] ? sa_inc_hi1[si] : sa_inc_hi0[si],sa_inc_lo[si]};
       always @(posedge clk) begin
          sa_inc_lo[si] <= chunk_addr[13:0] + 14'd1;
          sa_inc_c[si] <= &chunk_addr[13:0];
          sa_inc_hi0[si] <= chunk_addr[36:14]; sa_inc_hi1[si] <= chunk_addr[36:14] + 23'd1;
       end
       assign q_san[si] = src_hbm ? {addr_next[33:0],8'd0} : {addr_next[36:0],5'd0};
    end
    // hbm-fq/mvf 10-11 r2 (route px1a 01a78566e TT -208 / SS -713: rsa / ssp -> q_san / q_ddn 26-31 levels = the c_by chain
    // (src_hbm -> lm -> bav -> compare rrl -> mux) in series with a 42-b add; sstw -> q_nsn / rsa -> rnsa = bare 42-b adds):
    // * q_san is only consumed when the chunk does NOT end the row (!q_rend), where c_by = bav, so rsa + c_by =
    //   (rsa[41:5] + lm) << 5 = HBM ? {rsa[41:8] + 1, 8'b0} : {rsa[41:5] + 1, 5'b0}: two incrementers off the register.
    // * q_ddn = rdd + ((bav >> sl2) << dl2) (< 2^12): a 13-b low add with its carry registered; the high part is rdd[41:13]
    //   or its registered increment, selected at issue by the carry (rdd[k] is unchanged since R0 sampled it: same mask
    //   as every q_*).  q_nsn / q_ndn (row-step adds): 21-b halves, carry registered, both high sums registered.
    reg [12:0] q_dlo [0:3]; reg [3:0] q_dc; reg [41:13] q_dh1 [0:3];
    reg [20:0] q_nlo [0:3], q_nh0 [0:3], q_nh1 [0:3], q_mlo [0:3], q_mh0 [0:3], q_mh1 [0:3]; reg [3:0] q_nc, q_mc;
    wire [41:0] q_ddn [0:3], q_nsn [0:3], q_ndn [0:3];
    genvar g;
    for (g = 0; g < 4; g = g + 1) begin : g_qsel
        assign q_ddn[g] = {q_dc[g] ? q_dh1[g] : rdd[g][41:13], q_dlo[g]};
        assign q_nsn[g] = {q_nc[g] ? q_nh1[g] : q_nh0[g], q_nlo[g]};
        assign q_ndn[g] = {q_mc[g] ? q_mh1[g] : q_mh0[g], q_mlo[g]};
    end
    // PX 2 set-up operands (registered base / stride / stp / stpd only): value v of slot k = base + A + B + cin, as
    // carry-save S = base ^ A ^ B, K = maj(base, A, B) << 1; v 0 rsa (m = k), 1 rnsa (m = k + step), 2 rdd, 3 rndd
    // (step 4 when STRIPE4 on either side, as sstw / dstw; 7 x = 8 x + ~x + 1)
    reg [41:0] cs_s [0:3][0:3], cs_k [0:3][0:3]; reg cs_i [0:3][0:3]; reg [1:0] cs_c [0:3][0:3];
    always @* begin : csa
        reg [41:0] b, x, a1, a2; reg ci; integer m;
        for (integer v = 0; v < 4; v = v + 1) for (integer k = 0; k < 4; k = k + 1) begin
            cs_s[v][k] = op_a1[v][k]; cs_k[v][k] = op_a2[v][k]; cs_i[v][k] = op_ci[v][k];
        end
    end
    always @(posedge clk) if (cv_go && fast_cmd) begin : csa_op     // the addends, registered with the command fields
        reg [41:0] x, a1, a2, b; reg ci, st4; integer m;
        st4 = (cm_q[1:0] == 2'd0 && cm_q[44:42] == 3'd1) || (cm_q[94:93] == 2'd0 && cm_q[137:135] == 3'd1);
        ro_inc <= st4 ? 20'd4 : 20'd1;
        for (integer v = 0; v < 4; v = v + 1) for (integer k = 0; k < 4; k = k + 1) begin
            x = (v < 2) ? {8'd0, ((cm_q[1:0] == 2'd1) ? {cm_q[76:45], 2'b00} : {2'd0, cm_q[76:45]})}
                        : {8'd0, ((cm_q[94:93] == 2'd1) ? {cm_q[169:138], 2'b00} : {2'd0, cm_q[169:138]})};
            m = (v == 0 || v == 2) ? k : st4 ? k + 4 : k + 1;
            ci = 1'b0;
            case (m)
                0: begin a1 = 42'd0;    a2 = 42'd0; end
                1: begin a1 = x;        a2 = 42'd0; end
                2: begin a1 = x << 1;   a2 = 42'd0; end
                3: begin a1 = x << 1;   a2 = x; end
                4: begin a1 = x << 2;   a2 = 42'd0; end
                5: begin a1 = x << 2;   a2 = x; end
                6: begin a1 = x << 2;   a2 = x << 1; end
                default: begin a1 = x << 3; a2 = ~x; ci = 1'b1; end
            endcase
            // Capture the carry-save operands on the existing command edge.
            if(v<2)begin
                b=(cm_q[1:0]==2'd1)?{cm_q[44:5],2'b00}:{2'd0,cm_q[44:5]};
                if(cm_q[1:0]==2'd0 && cm_q[44:42]==3'd1)b={7'd0,cm_q[39:5]};
            end else begin
                b=(cm_q[94:93]==2'd1)?{cm_q[137:98],2'b00}:{2'd0,cm_q[137:98]};
                if(cm_q[94:93]==2'd0 && cm_q[137:135]==3'd1)b={7'd0,cm_q[132:98]};
            end
            op_a1[v][k] <= b ^ a1 ^ a2;
            op_a2[v][k] <= ((b & a1) | (b & a2) | (a1 & a2)) << 1;
            op_ci[v][k] <= ci;
        end
    end
    always @(posedge clk) begin
        for (integer k = 0; k < 4; k = k + 1) begin : r0
            reg [41:0] w; reg [19:0] rn1;
            q_ok[k] <= c_ok[k]; q_rend[k] <= c_rend[k]; q_bad[k] <= c_bad[k]; q_ea[k] <= c_ea[k]; q_ns[k] <= c_ns[k];
            q_by[k] <= c_by[k]; q_ds[k] <= c_ds[k]; q_ln[k] <= rsa[k][9:5];
            w = {33'd0, c_bv[k] >> sl2}; rn1 = ro[k] + ro_inc;

            q_rln[k] <= rrl[k] - {15'd0, c_bv[k]};                                     // exact when !c_rend
            {q_dc[k], q_dlo[k]} <= {1'b0, rdd[k][12:0]} + {1'b0, 13'(w << dl2)}; q_dh1[k] <= rdd[k][41:13] + 29'd1;
            {q_nc[k], q_nlo[k]} <= {1'b0, rnsa[k][20:0]} + {1'b0, sstw[20:0]};
            q_nh0[k] <= rnsa[k][41:21] + sstw[41:21]; q_nh1[k] <= rnsa[k][41:21] + sstw[41:21] + 21'd1;
            {q_mc[k], q_mlo[k]} <= {1'b0, rndd[k][20:0]} + {1'b0, dstw[20:0]};
            q_mh0[k] <= rndd[k][41:21] + dstw[41:21]; q_mh1[k] <= rndd[k][41:21] + dstw[41:21] + 21'd1;
            q_ron[k] <= rn1; q_rlst[k] <= rn1 >= mm;
        end
        l_k <= r_k; l_ln <= rsa[r_k][9:5];
    end
    reg go_q5;                                                         // R0 holds the set-up slots
    always @(posedge clk or negedge rn) if (!rn) begin l_v <= 1'b0; go_q5 <= 1'b0; end
                                        else begin l_v <= r_go; go_q5 <= go_q4 && busy_f && !go_f; end
    reg r_go; reg [1:0] r_k; reg [3:0] r_ok;
    always @* begin : rpick
        for (integer k = 0; k < 4; k = k + 1)
            r_ok[k] = q_ok[k] && !(l_v && l_k == 2'(k)) && !(B2 != 0 && q_bad[k]) &&   // B2: a bad chunk never issues
                      (src_hbm ? !lq_v[q_ea[k][36:35]] && !(iss_kw && w_l == q_ea[k][36:35]) :
                       (SV != 0) ? g_gnt && !(l_v && l_ln == q_ln[k]) : v_in < 3'd4);
        r_go = 1'b0; r_k = 2'd0;
        for (integer t = 3; t >= 0; t = t - 1) if (r_ok[2'(rrr + 2'(t))]) begin r_go = 1'b1; r_k = 2'(rrr + 2'(t)); end
        r_go = r_go && busy_f && go_q5 && !f_fault && sf_n <= 9'(SFD - 10) && cf_n < 7'(CF - 2);
    end
    reg [3:0] s_nc, s_mc;                                              // PX: settle-edge low-half carries
    reg go_q3;                                                         // one more setup edge: the row-end registers settle
    reg go_q4;                                                         // the reader slots are set up
    reg go_q2;                                                         // the command fields are settled
    // the write queue (16) must hold the flushes the pipe may still produce (p1, px, p2, pe, p3 + this one)
    // slots reserved = queued + flushes in the pipe, kept as a register (a popcount over the 8 stages sat in u_go)
    reg [4:0] wq_res;
    wire wq_room = wq_res < 5'd15;
    // The landing/decode leaf is independent. Keep every read reservation
    // charged across its five in-flight stages, including the return pin edge.
    reg [4:0] land_pending;
    assign land_write={lw_v,lw_a,lw_d};
    assign land_read={p1_v,p1_h,p1_k,p1_sp,p1_dp,p1_dsec,p1_fl,p1_sl};
    assign source_format={ssp,sf,sl2};
    // ---- encode, two stages (hgi-1010/c, route f628d5015: p2_w -> pe_e 20 levels = E4M3 variable shift + sticky + round +
    //      code assembly in one edge).  ENC A (p2 -> pa): BF16 complete (one 32-bit add); E4M3 to the pre-round quotient,
    //      its round-up bit and the exponent class.  ENC B (pa -> pe): E4M3 round add + code.  +1 cycle in the pipe.
    reg [255:0] enc_a; reg [8*25-1:0] ea_q; reg [7:0] ea_inc, ea_big, ea_sat, ea_sign; reg [8*8-1:0] ea_ex;
    always @* begin
        enc_a = 256'd0; ea_q = '0; ea_inc = 8'd0; ea_big = 8'd0; ea_sat = 8'd0; ea_sign = 8'd0; ea_ex = '0;
        for (integer j = 0; j < 8; j = j + 1) begin : en
            reg [31:0] x; reg [7:0] ex; reg [23:0] mant; integer sh; reg [24:0] q;
            x = p2_w[32*j +: 32];
            if (dsp == 2'd1 || df == 3'd0 || df == 3'd5) enc_a[32*j +: 32] = x;
            else if (df == 3'd1) enc_a[32*j +: 32] = {16'd0, to_bf16(x)};
            else begin
                ex = x[30:23]; ea_ex[8*j +: 8] = ex; ea_sign[j] = x[31];
                ea_sat[j] = (ex == 8'hFF) || (ex >= 8'd136);
                ea_big[j] = ex >= 8'd121;
                mant = (ex == 8'd0) ? 24'd0 : {1'b1, x[22:0]};
                sh = (ex >= 8'd121) ? 20 : (20 + 121 - ex);
                if (sh > 24) q = 25'd0;
                else begin
                    q = {1'b0, mant} >> sh;
                    ea_inc[j] = sh > 0 && mant[sh - 1] && ((mant & ((24'd1 << (sh - 1)) - 24'd1)) != 0 || q[0]);
                end
                ea_q[25*j +: 25] = q;
            end
        end
    end
    reg        pa_v; reg [3:0] pa_k; reg [255:0] pa_e; reg [8*25-1:0] pa_q; reg [7:0] pa_inc, pa_big, pa_sat, pa_sign;
    reg [8*8-1:0] pa_ex; reg [5:0] pa_dp; reg [36:0] pa_dsec; reg pa_fl, pa_e4;
    reg [255:0] enc_e;
    always @* begin
        enc_e = pa_e;
        if (pa_e4) for (integer j = 0; j < 8; j = j + 1) begin : eb
            reg [24:0] q; reg [7:0] code; reg [4:0] e4; reg [3:0] mq;
            q = pa_q[25*j +: 25] + {24'd0, pa_inc[j]};
            if (pa_big[j]) begin
                e4 = 5'(pa_ex[8*j +: 8] - 8'd120); mq = q[4] ? 4'd8 : q[3:0];
                if (q[4]) e4 = e4 + 5'd1;
                code = (e4 > 5'd15) ? 8'h7F : {e4[3:0], mq[2:0]};
            end else code = {1'b0, 4'd0, q[2:0]} + (q[3] ? 8'd8 : 8'd0);
            if (code > 8'h7E) code = 8'h7E;
            enc_e[32*j +: 32] = {24'd0, pa_sat[j] ? {pa_sign[j], 7'h7E} : (code == 8'd0) ? 8'd0 : {pa_sign[j], code[6:0]}};
        end
    end
    // ---- place (pe -> p3): lane j at byte dp + j << dl2 of the destination sector
    // pack: element j of the k at byte j << dl2 (contiguous from byte 0)
    reg [255:0] pack_d; reg [31:0] pack_s;
    always @* begin
        pack_d = 256'd0; pack_s = 32'd0;
        for (integer j = 0; j < 8; j = j + 1) if (pe_lv[j]) begin
            if (dl2 == 2'd2) begin pack_d[32*j +: 32] = pe_e[32*j +: 32]; pack_s[4*j +: 4] = 4'hF; end
            else if (dl2 == 2'd1) begin pack_d[16*j +: 16] = pe_e[32*j +: 16]; pack_s[2*j +: 2] = 2'b11; end
            else begin pack_d[8*j +: 8] = pe_e[32*j +: 8]; pack_s[j] = 1'b1; end
        end
    end
    // shift: the packed elements to the destination byte offset (a run never crosses the sector: d_room bounds k)
    wire [255:0] put_d = pk_d << {pk_dp[4:0], 3'd0};
    wire [31:0]  put_s = pk_s << pk_dp[4:0];
    // Datapath payloads have no reset net and no reset-derived enable. Only valid bits reset.
    always @(posedge clk) if (iss_vr) f_vmq[336:0] <= {1'b0,rsa[r_k][31:5],5'd0,256'd0,32'd0,16'h4D52};
    always @(posedge clk) if (iss_vw) begin
       reg [7:0] mask_words;
       for (integer t=0;t<8;t=t+1) mask_words[t] = &wq_head[256+4*t +: 4];
       wl[278:0] <= {wq_head[302:288] ^ ((MUT_SEAM == 5) ? 15'd1 : 15'd0),wq_head[255:0],mask_words};
    end
    // Native memory queues with two registered head entries. Their credits include pipe reservations.
    // Keep the flush reservation charged at p3; enqueue the registered bank on the next edge.
    // A same-bank update on that edge occurs after the FIFO samples the previous assembled payload.
    reg wq_pending_push;reg [1:0] wq_pending_slot;reg [36:0] wq_pending_dest;
    always @(posedge clk or negedge rn)
      if(!rn)wq_pending_push<=0;else wq_pending_push<=p3_v&&p3_fl&&p3_keep;
    always @(posedge clk)if(p3_v&&p3_fl&&p3_keep)begin wq_pending_slot<=p3_sl;wq_pending_dest<=p3_dsec;end
    wire [324:0] wq_push_data = {wq_pending_dest,db_strb[wq_pending_slot],db_dat[wq_pending_slot]};
    ot_hgi_b2_dma_fifo #(.W(325), .DEPTH(16), .MACRO(0), .ESL(32)) u_wq_mem(.clk(clk), .rst_n(rn),
       .push(wq_pending_push), .wdata(wq_push_data), .pop(iss_kw || iss_vw), .hv(wq_hv), .head(wq_head), .ovf(wq_ovf));
    wire [59:0] cf_push_data = {r_k,q_rend[r_k],1'b0,rdd[r_k][4:0],q_ds[r_k],rsa[r_k][4:0],9'(q_by[r_k] >> sl2)};
    ot_hgi_b2_dma_fifo #(.W(60), .DEPTH(64), .MACRO(3)) u_cf_mem(.clk(clk), .rst_n(rn),
       .push(r_go), .wdata(cf_push_data), .pop(cf_hv && (!cd_v || (cd_v && (!u_cv || (u_go && u_end))))), .hv(cf_hv), .head(cf_head), .ovf(cf_ovf));
    // ---- port issue selection
    reg iss_kw, iss_kr, iss_vw, iss_vr;
    always @* begin
        iss_kw = 1'b0; iss_kr = 1'b0; iss_vw = 1'b0; iss_vr = 1'b0;
        if (busy_f && go_q3 && !f_fault) begin
            if (wq_hv && dst_hbm && !lq_v[w_l] && wr_in < 9'(KOUT) && (B2 == 0 || w_l == 2'(QID))) iss_kw = 1'b1;   // a full sector to its stack's lane
            if (wq_hv && !dst_hbm) iss_vw = 1'b1;                      // the wide port: no client slot
        end
        iss_vr = r_go && !src_hbm && SV == 0; iss_kr = r_go && src_hbm;
    end
    // ---- response routing (in order per port)
    wire k_rv = kr_v && busy_f, v_rv = vr_q[273] && busy_f;
    wire k_wr_ack = k_rv;                                               // lane 2 carries the sector engine's writes only
    wire v_rd_land = v_rv && !v_kind[0], v_wr_ack = v_rv && v_kind[0];
    // ---- read lanes: requests, the registered landing grant (one sector a cycle), the landing RAM
    wire [3:0] l_take = ir_rsp_v & ((B2 != 0) ? 4'b1111 : lg) & ~ir_rsp_we;               // read sectors on the landing grant
    wire [3:0] w_ack = ir_rsp_v & ir_rsp_we & l_wo;                // write acknowledgements (taken on a lane with writes in flight)
    // Two requests of credit absorb the registered ready round trip. Register
    // every KV write at the input face before selecting the HBM lane payload.
    // The core retires only after HBM acknowledgements, so its idle cannot rise
    // while a request remains in this station or the downstream lane station.
    wire [3:0] kv_pin_v;
    wire [147:0] kv_pin_a;
    wire [1023:0] kv_pin_d;
    for (genvar kp = 0; kp < 4; kp = kp + 1) begin : g_kv_pin
      if (KVW != 0 && (B2 == 0 || kp == QID)) begin : used
        wire [292:0] request_head;
        ot_hgi_b2_dma_cmd_pin #(.W(293)) u_pin(.clk(clk), .rst_n(rn),
          .in_v(kv_wv[kp]), .in_data({kv_wa[kp*37 +: 37],kv_wd[kp*256 +: 256]}),
          .in_ready(kc_wrdy[kp]), .out_v(kv_pin_v[kp]), .out_data(request_head),
          .out_ready(!kv_idle && ir_req_rdy[kp]));
        assign {kv_pin_a[kp*37 +: 37],kv_pin_d[kp*256 +: 256]} = request_head;
      end else begin : unused
        assign kc_wrdy[kp] = 1'b0;
        assign kv_pin_v[kp] = 1'b0;
        assign kv_pin_a[kp*37 +: 37] = 37'd0;
        assign kv_pin_d[kp*256 +: 256] = 256'd0;
      end
    end
    genvar gl;
    for (gl = 0; gl < 4; gl = gl + 1) begin : g_rl
        // KVW: the KV engine's write requests share the lane (the engines never run together)
        // (selected by the KV engine's registered busy, not by its valid: registered outputs + one mux)
        assign ir_req_v[gl] = kv_idle ? lq_v[gl] : kv_pin_v[gl];
        assign ir_req_addr[gl*37 +: 37] = kv_idle ? lq_a[gl] : kv_pin_a[gl*37 +: 37];
        assign ir_req_len[gl*4 +: 4] = kv_idle ? lq_n[gl] : 4'd1;
        assign ir_req_tag[gl*16 +: 16] = {8'h52, kv_idle ? lq_t[gl] : 8'd0};
        assign ir_req_we[gl] = kv_idle ? lq_we[gl] : 1'b1;
        assign ir_req_wdata[gl*256 +: 256] = kv_idle ? lq_d[gl] : kv_pin_d[gl*256 +: 256];
        assign ir_req_wstrb[gl*32 +: 32] = kv_idle ? lq_s[gl] : 32'hFFFF_FFFF;
    end
    reg [3:0] l_wo;                                        // lanes with writes in flight (their responses are all write acks)
    // ---- KV write-back engine (hbm-fq/dma, KVW = 1)

    // Descriptor pin station: stable registered payload until the closed core takes it.
    always @(posedge clk or negedge rn) begin
       if (!rn) begin kc_v <= 0; kc_pending <= 0; end
       else begin
          if (kc_v && kv_c_rdy) kc_v <= 0;
          if (!kv_idle_w) kc_pending <= 0;
          if (kv_take) begin
             kc_v <= 1; kc_pending <= 1;
             kc_vs <= cm_q[22:8]; kc_vst <= cm_q[62:48];
             kc_ds <= cm_q[134:103]; kc_dst <= {5'd0,cm_q[169:143]};
             kc_ns <= cm_q[226:209]; kc_m <= cm_q[205:186];
          end
       end
    end
    assign kc_gnt = g_gnt;
    for (genvar gc = 0; gc < 32; gc = gc + 1) begin : g_credit_source
       assign credit_source[gc*6 +: 6] = g_cr[gc]; // registered counter source; output pin capture is in Kface
    end
    assign kb_we = 1'b0; assign kb_re = 1'b0; assign kb_wa = 8'd0; assign kb_ra = 8'd0; assign kb_wd = 256'd0;
    reg [5:0] l_wn [0:3];
    reg [3:0] w_acc_q, w_ack_q;                            // write accepted / acknowledged a lane (pin flops of the handshakes)
    always @* for (integer l = 0; l < 4; l = l + 1) l_wo[l] = l_wn[l] != 6'd0 || w_acc_q[l];
    assign ir_rsp_rdy = lg | l_wo | kv_wo;
    // the taken sector is registered first (the grant is one-hot: an AND-OR pick), its slot computed from the register
    // (registered boundary: r_rsp_v -> lt_i -> tag[lt_i] + beat -> lw_a was 49 levels)
    reg lt_v; reg [7:0] lt_tag; reg [2:0] lt_bt; reg [255:0] lt_d;
    // PX 2: the taken read sector is first captured raw per lane (pin flops: take = v & grant & !we, no logic before the
    // data / tag / last flops); the one-hot lane pick and the beat count run from those registers (+1 cycle on the landing)
    wire [3:0] lk_take; wire [4*8-1:0] lk_tag; wire [3:0] lk_last; wire [4*256-1:0] lk_data;
    if (PX >= 2) begin : g_rpf
        reg [3:0] tk_q; reg [3:0] tl_q; reg [4*8-1:0] tt_q; reg [4*256-1:0] td_q;
        always @(posedge clk or negedge rn) if (!rn) tk_q <= 4'd0; else tk_q <= l_take;
        always @(posedge clk) begin
            tl_q <= ir_rsp_last; td_q <= ir_rsp_data;
            for (integer l = 0; l < 4; l = l + 1) tt_q[l*8 +: 8] <= ir_rsp_tag[l*16 +: 8];
        end
        assign lk_take = tk_q; assign lk_tag = tt_q; assign lk_last = tl_q; assign lk_data = td_q;
    end else begin : g_rnopf
        assign lk_take = l_take; assign lk_last = ir_rsp_last; assign lk_data = ir_rsp_data;
        for (genvar l = 0; l < 4; l = l + 1) begin : g_t assign lk_tag[l*8 +: 8] = ir_rsp_tag[l*16 +: 8]; end
    end
    always @(posedge clk) begin : ltk
        reg [7:0] tg; reg [2:0] bt; reg [255:0] dd;
        tg = 8'd0; bt = 3'd0; dd = 256'd0;
        for (integer l = 0; l < 4; l = l + 1) if (lk_take[l]) begin
            tg = tg | lk_tag[l*8 +: 8]; bt = bt | lbc[l]; dd = dd | lk_data[l*256 +: 256];
        end
        lt_tag <= tg; lt_bt <= bt; lt_d <= dd;
    end
    always @(posedge clk or negedge rn) if (!rn) lt_v <= 1'b0; else lt_v <= |lk_take;
    // KVW: bank 0 of the KV engine's buffer (the sector engine is idle while it runs; its enables pick the port)
    // (textbook audit 10-11: the KV engine owns both its buffer banks, OWN_B0 1: no shared macro port across the split)
    wire kb_we, kb_re; wire [7:0] kb_wa, kb_ra; wire [255:0] kb_wd;
    always @(posedge clk) begin : lwd
        lw_a <= lt_v ? lt_tag + ((MUT == 3) ? 8'd0 : {5'd0, lt_bt}) : (SV != 0) ? g_slot[g_di] : v_ptr;
        lw_d <= lt_v ? lt_d : (SV != 0) ? g_d[g_di] : vr_q[255:0];
        for (integer b = 0; b < 32; b = b + 1) if (SV != 0 && vr2r[b*257 + 256]) g_d[b] <= vr2r[b*257 +: 256];   // the lane's response (pin flop)
    end
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            busy_f <= 1'b0; sel_s <= 1'b0; go_f <= 1'b0; go_q2 <= 1'b0; f_fault <= 1'b0;
            mv_done <= 1'b0; mv_fault <= 1'b0; fence_done <= 1'b0; f_vmq[337] <= 1'b0; wl[279] <= 1'b0; mv_src <= 1'b0; src_sent <= 1'b0;
            k_in <= 8'd0; v_in <= 3'd0; v_kind <= 8'd0; rd_in <= 9'd0; wr_in <= 9'd0;
            sf_h <= '0; sf_a <= '0; v_ptr <= '0; sf_n <= 9'd0; lv <= '0; lw_v <= 1'b0; lq_v <= 4'd0; lg <= 4'd0; lgi <= 2'd0; ract <= 4'd0; rrr <= 2'd0;
            cf_n <= 7'd0; cd_v <= 1'b0; u_cv <= 1'b0; go_q4 <= 1'b0; stp <= 1'b0; stpd <= 1'b0;
            g_busy <= 32'd0; g_hv <= 32'd0; g_rr <= 5'd0; s_vr2q <= '0; for (integer b = 0; b < 32; b = b + 1) g_cr[b] <= 6'(GLQ);
            w_acc_q <= 4'd0; w_ack_q <= 4'd0; for (integer l = 0; l < 4; l = l + 1) l_wn[l] <= 6'd0;
            for (integer l = 0; l < 4; l = l + 1) lbc[l] <= 3'd0;
            wq_n <= 5'd0; wq_hl <= 2'd0; wq_res <= 5'd0; go_q3 <= 1'b0;
            p1_v <= 1'b0; land_pending <= 0; p2_v <= 1'b0; pa_v <= 1'b0; pe_v <= 1'b0; pk_v <= 1'b0; p3_v <= 1'b0; db_dirty <= 4'd0;
        end else begin
            mv_done <= 1'b0; fence_done <= 1'b0; mv_src <= 1'b0;
            if (fence_pending && fence_available) fence_done <= 1'b1;
            // ---- the serial engine's completion and ports
            if (s_mv_done) begin mv_done <= 1'b1; mv_src <= 1'b1; sel_s <= 1'b0; end   // serial engine: source = done
            if (s_mv_fault) mv_fault <= 1'b1;
            cv_q <= cv_q && !kv_take && !cv_go && !b2_flt;            // held while the KV engine is busy / full
            if (wq_ovf || cf_ovf || (B2 != 0 && (b2_flt || b2_lx || b2_kx))) begin mv_fault <= 1'b1; f_fault <= 1'b1; end
            if (command_valid && command_ready) begin cv_q <= 1'b1; cm_q <= command_data; end
            if (kv_src) mv_src <= 1'b1;
            if (kv_done) mv_done <= 1'b1;
            if (k_fault && !kv_idle) begin mv_fault <= 1'b1; f_fault <= 1'b1; end
            if (cv_go && !fast_cmd && cm_q[94:93] == 2'd0) begin mv_fault <= 1'b1; f_fault <= 1'b1; end   // strided HBM writes: partial sectors
            else if (cv_go && !fast_cmd) sel_s <= 1'b1;
            // ---- accept a sector-engine command
            go_f <= 1'b0; go_q2 <= go_f | (go_q2 && busy_f);           // go_q2: the command fields have settled (level while busy)
            go_q3 <= go_q2 && busy_f && !go_f;                         // go_q3: the row registers have settled
            go_q4 <= go_q3 && busy_f && !go_f;                         // go_q4: the reader slots' next-row registers have settled
            if (cv_go && fast_cmd) begin
                busy_f <= 1'b1; go_f <= 1'b1;
                ssp <= cm_q[1:0]; sf <= cm_q[4:2]; sst <= cm_q[76:45]; dsp <= cm_q[94:93]; df <= cm_q[97:95]; dst <= cm_q[169:138];
                sstb <= (cm_q[1:0] == 2'd1) ? {cm_q[76:45], 2'b00} : {2'd0, cm_q[76:45]};
                dstb <= (cm_q[94:93] == 2'd1) ? {cm_q[169:138], 2'b00} : {2'd0, cm_q[169:138]};
                mm <= cm_q[205:186]; nn <= cm_q[226:206];
                ses <= (cm_q[1:0] == 2'd1) ? 3'd4 : esz(cm_q[4:2]); des <= (cm_q[94:93] == 2'd1) ? 3'd4 : esz(cm_q[97:95]);
                sl2 <= (cm_q[1:0] == 2'd1) ? 2'd2 : l2(esz(cm_q[4:2])); dl2 <= (cm_q[94:93] == 2'd1) ? 2'd2 : l2(esz(cm_q[97:95]));
                nnb <= {3'd0, cm_q[226:206]} << ((cm_q[1:0] == 2'd1) ? 2'd2 : l2(esz(cm_q[4:2])));
                sbase <= (cm_q[1:0] == 2'd1) ? {cm_q[44:5], 2'b00} : {2'd0, cm_q[44:5]};
                dbase <= (cm_q[94:93] == 2'd1) ? {cm_q[137:98], 2'b00} : {2'd0, cm_q[137:98]};
                if ((cm_q[1:0] > 2'd1) || (cm_q[94:93] > 2'd1) || cm_q[4:2] == 3'd3 || cm_q[4:2] == 3'd6 || cm_q[97:95] == 3'd3 ||
                    cm_q[97:95] == 3'd6 || cm_q[97:95] == 3'd4 || cm_q[205:186] == 20'd0 || cm_q[226:206] == 21'd0 ||
                    (cm_q[1:0] == 2'd0 && cm_q[44:42] > 3'd1) ||                       // HBM source: stripe code 0 / 1 only
                    (cm_q[1:0] == 2'd0 && cm_q[44:42] == 3'd1 &&                       // STRIPE4 source: 32 B row starts, VM destination
                     (cm_q[9:5] != 5'd0 || cm_q[49:45] != 5'd0 || cm_q[94:93] != 2'd1 || cm_q[100:98] != 3'd0 || cm_q[140:138] != 3'd0)) ||
                    (cm_q[94:93] == 2'd0 && cm_q[137:135] > 3'd1) ||                   // HBM destination: stripe code 0 / 1 only
                    (cm_q[94:93] == 2'd0 && cm_q[137:135] == 3'd1 && cm_q[1:0] == 2'd0) ||   // STRIPE4 destination: VM source
                    // HBM destination (STORE): whole sectors only (the kport writes full sectors): row start, stride and row
                    // bytes multiples of 32
                    (cm_q[94:93] == 2'd0 && (cm_q[102:98] != 5'd0 || cm_q[142:138] != 5'd0 ||
                     ((cm_q[226:206] << l2(esz(cm_q[97:95]))) & 21'h1F) != 21'd0))) begin
                    f_fault <= 1'b1; mv_fault <= 1'b1; busy_f <= 1'b0;
                end
                // STRIPE4: the base is stack-local (bits [34:0]), row 0's stack is base[36:35]
                stp <= cm_q[1:0] == 2'd0 && cm_q[44:42] == 3'd1; s0 <= cm_q[41:40];
                if (cm_q[1:0] == 2'd0 && cm_q[44:42] == 3'd1) sbase <= {7'd0, cm_q[39:5]};
                stpd <= cm_q[94:93] == 2'd0 && cm_q[137:135] == 3'd1; d0 <= cm_q[134:133];
                if (cm_q[94:93] == 2'd0 && cm_q[137:135] == 3'd1) dbase <= {7'd0, cm_q[132:98]};
            end
            if (go_f) src_sent <= 1'b0;
            if (busy_f && go_q4 && !f_fault && r_done && rd_in == 9'd0 && !src_sent) begin mv_src <= 1'b1; src_sent <= 1'b1; end
            if (go_f) begin
                // reader slots: slot k starts at row k (STRIPE4: rows k, k + 4, ...; else slot 0 takes every row)
                db_dirty <= 4'd0; u_cv <= 1'b0; rrr <= 2'd0; v_ptr <= sf_a;
                sstw <= (stp || stpd) ? {6'd0, sstb, 2'b00} : {8'd0, sstb}; dstw <= (stp || stpd) ? {6'd0, dstb, 2'b00} : {8'd0, dstb};
                if (PX < 2) begin
                    rsa[0] <= sbase; rsa[1] <= sbase + {8'd0, sstb}; rsa[2] <= sbase + {7'd0, sstb, 1'b0};
                    rsa[3] <= sbase + {7'd0, sstb, 1'b0} + {8'd0, sstb};
                    rdd[0] <= dbase; rdd[1] <= dbase + {8'd0, dstb}; rdd[2] <= dbase + {7'd0, dstb, 1'b0};
                    rdd[3] <= dbase + {7'd0, dstb, 1'b0} + {8'd0, dstb};
                end
                for (integer k = 0; k < 4; k = k + 1) begin
                    ro[k] <= 20'(k); rrl[k] <= nnb;
                    ract[k] <= (k == 0 || stp || stpd) && 20'(k) < mm &&     // B2: STRIPE4 runs only the slot on stack QID
                               (B2 == 0 || !(stp || stpd) || 2'((stp ? s0 : d0) + 2'(k)) == 2'(QID + ((MUT_B2 == 1) ? 1 : 0)));
                end
                // natural alignment of every row start (elements are contiguous within a row)
                if ((ses == 3'd4 && (sbase[1:0] != 2'd0 || sstb[1:0] != 2'd0)) || (ses == 3'd2 && (sbase[0] || sstb[0])) ||
                    (des == 3'd4 && (dbase[1:0] != 2'd0 || dstb[1:0] != 2'd0)) || (des == 3'd2 && (dbase[0] || dstb[0]))) begin
                    f_fault <= 1'b1; mv_fault <= 1'b1; busy_f <= 1'b0;
                end
            end
            if (PX >= 2) begin                     // base + m x stride: carry-save, 14-b chunks on go_f / go_q2 / go_q3
                for (integer k = 0; k < 4; k = k + 1) begin
                    if (go_f) begin
                        {cs_c[0][k][0], rsa[k][13:0]}  <= {1'b0, cs_s[0][k][13:0]} + {1'b0, cs_k[0][k][13:0]} + 15'(cs_i[0][k]);
                        {cs_c[1][k][0], rnsa[k][13:0]} <= {1'b0, cs_s[1][k][13:0]} + {1'b0, cs_k[1][k][13:0]} + 15'(cs_i[1][k]);
                        {cs_c[2][k][0], rdd[k][13:0]}  <= {1'b0, cs_s[2][k][13:0]} + {1'b0, cs_k[2][k][13:0]} + 15'(cs_i[2][k]);
                        {cs_c[3][k][0], rndd[k][13:0]} <= {1'b0, cs_s[3][k][13:0]} + {1'b0, cs_k[3][k][13:0]} + 15'(cs_i[3][k]);
                    end
                    if (go_q2 && !go_q3) begin
                        {cs_c[0][k][1], rsa[k][27:14]}  <= {1'b0, cs_s[0][k][27:14]} + {1'b0, cs_k[0][k][27:14]} + 15'(cs_c[0][k][0]);
                        {cs_c[1][k][1], rnsa[k][27:14]} <= {1'b0, cs_s[1][k][27:14]} + {1'b0, cs_k[1][k][27:14]} + 15'(cs_c[1][k][0]);
                        {cs_c[2][k][1], rdd[k][27:14]}  <= {1'b0, cs_s[2][k][27:14]} + {1'b0, cs_k[2][k][27:14]} + 15'(cs_c[2][k][0]);
                        {cs_c[3][k][1], rndd[k][27:14]} <= {1'b0, cs_s[3][k][27:14]} + {1'b0, cs_k[3][k][27:14]} + 15'(cs_c[3][k][0]);
                    end
                    if (go_q3 && !go_q4) begin
                        rsa[k][41:28]  <= cs_s[0][k][41:28] + cs_k[0][k][41:28] + 14'(cs_c[0][k][1]);
                        rnsa[k][41:28] <= cs_s[1][k][41:28] + cs_k[1][k][41:28] + 14'(cs_c[1][k][1]);
                        rdd[k][41:28]  <= cs_s[2][k][41:28] + cs_k[2][k][41:28] + 14'(cs_c[2][k][1]);
                        rndd[k][41:28] <= cs_s[3][k][41:28] + cs_k[3][k][41:28] + 14'(cs_c[3][k][1]);
                    end
                end
            end else if (PX != 0) begin                                        // two settle edges: 21-b halves, carry kept
                if (go_q2 && !go_q3) for (integer k = 0; k < 4; k = k + 1) begin
                    {s_nc[k], rnsa[k][20:0]} <= {1'b0, rsa[k][20:0]} + {1'b0, sstw[20:0]};
                    {s_mc[k], rndd[k][20:0]} <= {1'b0, rdd[k][20:0]} + {1'b0, dstw[20:0]};
                end
                if (go_q3 && !go_q4) for (integer k = 0; k < 4; k = k + 1) begin
                    rnsa[k][41:21] <= rsa[k][41:21] + sstw[41:21] + {20'd0, s_nc[k]};
                    rndd[k][41:21] <= rdd[k][41:21] + dstw[41:21] + {20'd0, s_mc[k]};
                end
            end else if (go_q2 && !go_q3) for (integer k = 0; k < 4; k = k + 1) begin   // the settle edge: each slot's next row
                rnsa[k] <= rsa[k] + sstw; rndd[k] <= rdd[k] + dstw;
            end
            // ---- issue: lane / client requests
            f_vmq[337] <= 1'b0;
            begin : issue
                reg kpush, kkind, vpush, vkind;
                kpush = 1'b0; kkind = 1'b0; vpush = 1'b0; vkind = 1'b0;
                // lane requests enter a 2-entry skid (its head drives k_req; k_req_rdy only pops it)
                if (iss_kw) begin
                    lq_v[w_l] <= 1'b1; lq_we[w_l] <= 1'b1; lq_a[w_l] <= {wq_head[319:288], 5'd0}; lq_n[w_l] <= 4'd1;
                    lq_d[w_l] <= wq_head[255:0]; lq_s[w_l] <= wq_head[287:256]; lq_t[w_l] <= 8'd0;
                end
                wl[279] <= 1'b0;
                if (iss_vw) begin : wide
                    reg [7:0] wm; integer t;
                    for (t = 0; t < 8; t = t + 1) wm[t] = &wq_head[256+4*t +: 4];
                    wl[279] <= 1'b1;
                end
                if (iss_vr) begin
                    f_vmq[337] <= 1'b1; vpush = 1'b1;
                end
                // write queue pop
                // read lane requests leave their registers when the lane takes them
                for (integer l = 0; l < 4; l = l + 1) begin
                    if (lq_v[l] && ir_req_rdy[l]) lq_v[l] <= 1'b0;
                    w_acc_q[l] <= lq_v[l] && ir_req_rdy[l] && lq_we[l]; w_ack_q[l] <= w_ack[l];
                    l_wn[l] <= l_wn[l] + 6'(w_acc_q[l] ? 1 : 0) - 6'(w_ack_q[l] ? 1 : 0);
                end
                // reader: the chunk of slot r_k -> its lane request (HBM) / VM read, its descriptor, its landing slots
                if (r_go) begin : radv
                    reg [41:0] w;
                    sf_a <= sf_a + 8'(q_ns[r_k]);
                    if (src_hbm) begin
                        lq_v[q_ea[r_k][36:35]] <= 1'b1; lq_we[q_ea[r_k][36:35]] <= 1'b0; lq_a[q_ea[r_k][36:35]] <= {q_ea[r_k][36:5], 5'd0};
                        lq_n[q_ea[r_k][36:35]] <= q_ns[r_k]; lq_t[q_ea[r_k][36:35]] <= sf_a;
                    end
                    if (q_bad[r_k]) begin f_fault <= 1'b1; mv_fault <= 1'b1; end
                    rrr <= r_k + 2'd1;
                    if (PX != 0) begin
                        for (integer k = 0; k < 4; k = k + 1) if (r_k == 2'(k)) begin   // a select of precomputed values
                            if (q_rend[k]) begin
                                if (q_rlst[k]) ract[k] <= 1'b0;
                                ro[k] <= q_ron[k]; rrl[k] <= nnb;
                                rsa[k] <= rnsa[k]; rnsa[k] <= q_nsn[k]; rdd[k] <= rndd[k]; rndd[k] <= q_ndn[k];
                            end else begin
                                rsa[k] <= q_san[k]; rrl[k] <= q_rln[k]; rdd[k] <= q_ddn[k];
                            end
                        end
                    end else if (q_rend[r_k]) begin                                       // the slot's next row (precomputed)
                        if (ro[r_k] + ro_inc >= mm) ract[r_k] <= 1'b0;
                        ro[r_k] <= ro[r_k] + ro_inc; rrl[r_k] <= nnb;
                        rsa[r_k] <= rnsa[r_k]; rnsa[r_k] <= rnsa[r_k] + sstw; rdd[r_k] <= rndd[r_k]; rndd[r_k] <= rndd[r_k] + dstw;
                    end else begin
                        rsa[r_k] <= rsa[r_k] + {33'd0, q_by[r_k]}; rrl[r_k] <= rrl[r_k] - {15'd0, q_by[r_k]};
                        w = {33'd0, q_by[r_k] >> sl2}; rdd[r_k] <= rdd[r_k] + (w << dl2);
                    end
                end
                // in-flight accounting (kind shift registers: push at the tail, pop at the head)
                k_in <= k_in + {7'd0, kpush} - {7'd0, k_rv};
                v_in <= v_in + {2'd0, vpush} - {2'd0, v_rv};
                begin : vk
                    reg [7:0] t; t = v_kind;
                    if (v_rv) t = t >> 1;
                    if (vpush) t[v_in - {2'd0, v_rv}] = vkind;
                    v_kind <= t;
                end
                begin : rdc                                    // PX3: one candidate per slot, picked after the add
                    reg [8:0] cn, cc [0:3];
                    cn = rd_in - {8'd0, lw_v};
                    for (integer k = 0; k < 4; k = k + 1) cc[k] = cn + {5'd0, q_ns[k]};
                    rd_in <= r_go ? cc[r_k] : cn;
                end
                wr_in <= wr_in + {8'd0, iss_kw | iss_vw} - {8'd0, v_wr_ack | (wld_q & busy_f & !dst_hbm)}
                         - {6'd0, 3'(w_ack_q[0]) + 3'(w_ack_q[1]) + 3'(w_ack_q[2]) + 3'(w_ack_q[3])};
            end
            if (k_fault && busy_f) begin f_fault <= 1'b1; mv_fault <= 1'b1; end
            // B2: a chunk read / a sector write off stack QID (a linear row crossing the stack): fault, never issued
            if (B2 != 0 && busy_f && ((go_q5 && |(q_ok & q_bad)) || (go_q3 && wq_n != 5'd0 && dst_hbm && w_l != 2'(QID)))) begin
                f_fault <= 1'b1; mv_fault <= 1'b1;
            end
            // ---- landing
            // ---- landing: a lane's response sector (registered grant) or the VM read, into its slot of the landing RAM
            begin : land
                reg pop_; reg [1:0] nx; reg nf;
                pop_ = u_go && u_pop;
                lw_v <= lt_v || v_rd_land || (SV != 0 && g_dv);
                // VM read group: responses held a lane, drained one a cycle; credits; burst ownership
                for (integer b = 0; b < 32; b = b + 1) begin
                    if (SV != 0 && vr2r[b*257 + 256] && kv_idle) g_hv[b] <= 1'b1;     // KVW: the KV engine's responses are its own
                    g_cr[b] <= g_cr[b] + 6'(g_crp[b]) - 6'((r_go && !src_hbm && SV != 0 && rsa[r_k][9:5] == 5'(b)) ? 1 : 0)
                               - 6'(kv_req_v[b]);                // the KV engine's requests (hbm-fq/dma)
                end
                if (SV != 0 && g_dv) begin g_hv[g_di] <= 1'b0; g_busy[g_di] <= 1'b0; g_rr <= g_di + 5'd1; end
                s_vr2q[511:0] <= '0;
                if (r_go && !src_hbm && SV != 0) begin
                    g_busy[rsa[r_k][9:5]] <= 1'b1; g_slot[rsa[r_k][9:5]] <= sf_a;
                    s_vr2q[rsa[r_k][9:5]*16 +: 16] <= {1'b1, rsa[r_k][19:5]};
                end
                s_vr2q[512] <= VR2 != 0 && ((SV != 0 && busy_f && !src_hbm && go_q4 && !r_done) || g_busy != 32'd0 || !g_home);
                if (v_rd_land) v_ptr <= v_ptr + 8'd1;
                for (integer l = 0; l < 4; l = l + 1) if (lk_take[l]) lbc[l] <= lk_last[l] ? 3'd0 : lbc[l] + 3'd1;
                // next grant: rotating from the lane after the current grant, among the lanes with a sector waiting
                nf = 1'b0; nx = 2'd0;
                for (integer t = 4; t >= 1; t = t - 1) begin : gp
                    reg [1:0] c; c = 2'(lgi + 2'(t));
                    if (ir_rsp_v[c] && !ir_rsp_we[c]) begin nf = 1'b1; nx = c; end
                end
                lg <= nf ? (4'd1 << nx) : 4'd0; if (nf) lgi <= nx;
                if (lw_v) lv[lw_a] <= 1'b1;
                if (pop_) begin lv[sf_h] <= 1'b0; sf_h <= sf_h + 8'd1; end
                begin : sfc                                    // PX3: one candidate per slot, picked after the add
                    reg [8:0] cn, cc [0:3];
                    cn = sf_n - {8'd0, pop_};
                    for (integer k = 0; k < 4; k = k + 1) cc[k] = cn + {5'd0, q_ns[k]};
                    sf_n <= r_go ? cc[r_k] : cn;
                end
            end
            // ---- unpack (stage U -> p1): the current chunk; the staged descriptor becomes current at the chunk end
            p1_v <= 1'b0;
            begin : unpk
                reg take_cd;
                take_cd = cd_v && (!u_cv || (u_go && u_end));
                if (u_go) begin
                    p1_v <= 1'b1; p1_k <= u_k; p1_h <= sf_h; p1_sp <= u_sp; p1_dp <= u_dp; p1_dsec <= u_dsec;
                    p1_fl <= u_fl; p1_sl <= u_sl;
                    if (u_end) u_cv <= 1'b0;
                    else begin
                        u_left <= u_left - {5'd0, u_k};
                        u_sp <= u_sp + (5'(u_k) << sl2);
                        s_room <= u_pop ? (6'd32 >> sl2) : s_room - {2'd0, u_k};
                        if (u_fl) begin u_dsec <= u_dsec + 37'd1; u_dp <= 6'd0; d_room <= 6'd32 >> dl2; end
                        else begin u_dp <= u_dp + (6'(u_k) << dl2); d_room <= d_room - {2'd0, u_k}; end
                    end
                end
                if (take_cd) begin
                    u_cv <= 1'b1; u_left <= cd[8:0]; u_sp <= cd[13:9]; u_dsec <= cd[50:14]; u_dp <= cd[56:51]; u_rend <= cd[57]; u_sl <= cd[59:58];
                    s_room <= room(cd[13:9], sl2); d_room <= room(cd[55:51], dl2);
                end
                if (cf_hv && (!cd_v || take_cd)) begin cd <= cf_head; cd_v <= 1'b1; end
                else if (take_cd) cd_v <= 1'b0;
                cf_n <= cf_n + {6'd0, r_go} - {6'd0, cf_hv && (!cd_v || take_cd)};
            end
            // ---- extract (p1 -> px), convert (px -> p2), encode (p2 -> pe), place (pe -> p3), merge (p3)
            land_pending <= {land_pending[3:0],p1_v};
            p2_v <= decoded[306];
            if(decoded[306])begin
              {p2_k,p2_dp,p2_dsec,p2_fl,p2_sl,p2_w} <= decoded[305:0];
            end
            pa_v <= p2_v;
            if (p2_v) begin
                pa_k <= p2_k; pa_e <= enc_a; pa_q <= ea_q; pa_inc <= ea_inc; pa_big <= ea_big; pa_sat <= ea_sat; pa_sign <= ea_sign;
                pa_ex <= ea_ex; pa_dp <= p2_dp; pa_dsec <= p2_dsec; pa_fl <= p2_fl; pa_sl <= p2_sl; pa_e4 <= !(dsp == 2'd1 || df == 3'd0 || df == 3'd5 || df == 3'd1);
            end
            pe_v <= pa_v;
            if (pa_v) begin
                pe_e <= enc_e; pe_dp <= pa_dp; pe_dsec <= pa_dsec; pe_fl <= pa_fl; pe_sl <= pa_sl;
                for (integer q = 0; q < 8; q = q + 1) pe_lv[q] <= q < pa_k;
                pe_keep <= !(MUT == 2 && pa_dp + (6'(pa_k) << dl2) != 6'd32);
            end
            pk_v <= pe_v;
            if (pe_v) begin pk_d <= pack_d; pk_s <= pack_s; pk_dp <= pe_dp; pk_dsec <= pe_dsec; pk_fl <= pe_fl; pk_keep <= pe_keep; pk_sl <= pe_sl; end
            p3_v <= pk_v;
            if (pk_v) begin p3_d <= put_d; p3_s <= put_s; p3_dsec <= pk_dsec; p3_fl <= pk_fl; p3_keep <= pk_keep; p3_sl <= pk_sl; end
            if (p3_v) begin
                // Final assembly lands in the existing bank even on flush, before pending enqueue.
                db_dat[p3_sl] <= ((db_dirty[p3_sl] ? db_dat[p3_sl] : 256'd0) & ~mk(p3_s)) | p3_d;
                db_strb[p3_sl] <= (db_dirty[p3_sl] ? db_strb[p3_sl] : 32'd0) | p3_s;
                db_dirty[p3_sl] <= !p3_fl;
            end
            wq_n <= wq_n + {4'd0, p3_v && p3_fl && p3_keep} - {4'd0, iss_kw | iss_vw};
            wq_res <= wq_res + {4'd0, u_go && u_fl} - {4'd0, iss_kw | iss_vw} - {4'd0, p3_v && p3_fl && !p3_keep};
            // ---- completion: everything unpacked, the pipe empty, the queue drained and every write acknowledged
            if (busy_f && go_q4 && !f_fault && r_done && !u_cv && !cd_v && cf_n == 7'd0 && !lw_v && lq_v == 4'd0 && !p1_v && land_pending == 0 && !p2_v && !pa_v && !pe_v && !pk_v && !p3_v && wq_n == 5'd0 && wr_in == 9'd0 &&
                !(iss_kw | iss_vw) && rd_in == 9'd0 && sf_n == 9'd0) begin
                busy_f <= 1'b0; mv_done <= 1'b1;
            end
            if (f_fault && busy_f && k_in == 8'd0 && v_in == 3'd0 && rd_in == 9'd0 && lq_v == 4'd0) busy_f <= 1'b0;
        end
    end
    function automatic [1:0] l2(input [2:0] e);
        l2 = (e == 3'd4) ? 2'd2 : (e == 3'd2) ? 2'd1 : 2'd0;
    endfunction
    function automatic [5:0] room(input [4:0] off, input [1:0] lgs);  // elements from byte off to the sector end
        room = (6'd32 - {1'b0, off}) >> lgs;
    endfunction
    function automatic [255:0] mk(input [31:0] s);
        integer t; begin mk = 256'd0; for (t = 0; t < 32; t = t + 1) if (s[t]) mk[8*t +: 8] = 8'hFF; end
    endfunction
    // ---- port muxing with the serial engine (it drives the ports while it owns them)
    // The output slot refills only while empty. Raw receiver ready reaches the valid flop only,
    // never the serial FIFO payload mux (failed route: k_req_rdy -> out_data, -584 ps).
    // A consumed request creates one refill edge; serial throughput is measured in the exact gate.
    assign ko_ld = !ko_v;
    assign b2_kx = B2 != 0 && sel_s && s_kv && s_ka[36:35] != 2'(QID);
    // hgi-1010/c: the lane request leaves an OUTPUT REGISTER (route bf6565982: sel_s / kq_h -> k_req_wdata / k_req_addr
    // through the engine mux to the pins, -352 ps): the register loads the selected engine's request whenever it is
    // empty or the lane takes its content (bubble-free); an engine's request counts as taken when the register loads it
    reg ko_v, ko_we; reg [36:0] ko_a; reg [255:0] ko_d; reg [31:0] ko_s;
    always @(posedge clk or negedge rn)
        if (!rn) ko_v <= 1'b0;
        else if (ko_v && k_req_rdy) ko_v <= 1'b0;
        else if (ko_ld) begin
            ko_v <= sel_s ? s_kv && !b2_kx : f_kv;                      // B2: an off-stack request is never issued
            ko_we <= sel_s ? s_kwe : f_kwe; ko_a <= (sel_s ? s_ka : f_ka) + (37'(qid_q) << 35);
            ko_d <= sel_s ? s_kd : f_kd; ko_s <= sel_s ? s_ks : f_ks;
        end
    assign k_req_v = ko_v; assign k_req_we = ko_we; assign k_req_addr = ko_a; assign k_req_wdata = ko_d; assign k_req_wstrb = ko_s;
    assign vmq = f_vmq; // fast-engine registered producer; owner mux lives in independent packet face
    wire unused_ok = &{1'b0, s_kt, s_krr, s_fence_done};
`ifndef SYNTHESIS
    // a refused move names itself (bench / e2e debugging)
    always @(posedge clk) if (rn && cv_go && (fast_cmd ? 1'b1 : cm_q[94:93] == 2'd0)) begin : flt
        reg x; x = (cm_q[94:93] == 2'd0) && (!fast_cmd || cm_q[102:98] != 5'd0 || cm_q[142:138] != 5'd0 ||
                    ((cm_q[226:206] << l2(esz(cm_q[97:95]))) & 21'h1F) != 21'd0);
        if (x) $display("MOVER refuses a partial-sector HBM write: src sp %0d fmt %0d dst base %h stride %0d fmt %0d m %0d n %0d istride %0d/%0d",
                        cm_q[1:0], cm_q[4:2], cm_q[137:98], cm_q[169:138], cm_q[97:95], cm_q[205:186], cm_q[226:206], cm_q[92:77], cm_q[185:170]);
    end
`endif
endmodule
`default_nettype wire

// Two-entry input pin station: payload, valid and ready are all registered at the face.
module ot_hgi_b2_dma_cmd_pin #(parameter integer W=227)(
 input wire clk, rst_n, in_v, input wire [W-1:0] in_data, output reg in_ready,
 output reg out_v, output reg [W-1:0] out_data, input wire out_ready
);
 reg [1:0] count; reg [W-1:0] tail;
 wire push = in_v && in_ready, pop = out_v && out_ready;
 wire [1:0] count_next = count + {1'b0,push} - {1'b0,pop};
 always @(posedge clk or negedge rst_n) begin
   if (!rst_n) begin count<=0; in_ready<=1; out_v<=0; end
   else begin
     count<=count_next; in_ready<=count_next<2; out_v<=count_next!=0;
     case ({push,pop})
       2'b10: begin if (count==0) out_data<=in_data; else tail<=in_data; end
       2'b01: out_data<=tail;
       2'b11: begin if (count==1) out_data<=in_data; else begin out_data<=tail; tail<=in_data; end end
       default: begin end
     endcase
   end
 end
endmodule
