`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 DMA row mover (hgi-adapters, 2026-10-09): the peer of ot_hgi_dma_record's move / fence ports (and of the FUSED
// adapter's gain load).  Glue on EXISTING ports: HBM through one lane of the loader's kport (ot_hfd_loader_kport:
// 37-bit byte address, 256-b sectors, strobes, one transaction outstanding), VM through one hfd_hgi_vm packet client
// (ot_hgi_vm_unit: {v, we, byte address 32, wdata 256, mask 32, tag 16} / {v, tag 16, we, rdata 256}).
// Move word (227 b, LSB first): {src space 2, src fmt 3, src base 40, src stride 32, src istride 16, dst space 2,
//   dst fmt 3, dst base 40, dst stride 32, dst istride 16, m 20, n 21}.  Element (o, i), o < m, i < n, row-major:
//   HBM byte  base + o stride + i istride esize      (esize: FP32 / U32 4, BF16 2, FP8E4M3 / INT8 1)
//   VM word   base + o stride + i istride
// LOAD (HBM -> VM FP32 / U32; hgi_sim decode_fmt): FP32 / U32 the word; BF16 the half << 16; INT8 the integer as FP32
//   (exact); FP8E4M3 the E4M3 value (NaN code 0x7F / 0xFF -> 0x7FC00000).  VM -> VM moves copy the word.
// STORE (VM FP32 / U32 -> HBM; hgi_sim encode_fmt): FP32 / U32 the word; BF16 = to_bf16 (RNE, hdc_golden); FP8E4M3 =
//   to_fp8 (RNE in the value's binade, subnormal quantum 2^-9, saturating at 448) then its code.
// One element a cycle while the source sector is cached and the destination sector buffer is open; a sector read
// misses or a destination sector change costs one round trip on its port (the kport is the boot-path rate: one sector
// per round trip; the PS stream fork is the fast path, a later successor).  The record retires on done = every write
// of the move acknowledged; fence_done = no write outstanding (the mover is serial, so 1 edge when idle).
// Faults: an element not naturally aligned (spec 6.10: 32-byte HBM bases, whole elements), a FP4 / UE8M0 format, a src / dst space other than HBM / VM, a kport fault -> mv_fault (sticky).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_dma_mover #(
    parameter integer MUT_RNE = 0         // mutant: BF16 store truncates (no round to nearest even)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          mv_v,
    output wire          mv_rdy,
    input  wire [226:0]  mv,
    output reg           mv_done,
    output reg           mv_fault,
    input  wire          fence_v,
    output wire          fence_rdy,
    output reg           fence_done,
    // kport lane (HBM)
    output reg           k_req_v,
    input  wire          k_req_rdy,
    output reg           k_req_we,
    output reg  [36:0]   k_req_addr,
    output reg  [255:0]  k_req_wdata,
    output reg  [31:0]   k_req_wstrb,
    output wire [15:0]   k_req_tag,
    input  wire          k_rsp_v,
    output wire          k_rsp_rdy,
    input  wire          k_rsp_we,
    input  wire [255:0]  k_rsp_data,
    input  wire          k_fault,
    // VM packet client
    output reg  [337:0]  vmq,
    input  wire [273:0]  vmr
);
    assign k_req_tag = 16'h4D56;
    assign k_rsp_rdy = 1'b1;
    // ---- command
    reg busy;
    reg [1:0] ssp, dsp; reg [2:0] sf, df; reg [39:0] sb, db; reg [31:0] sst, dst; reg [15:0] sis, dis;
    reg [19:0] mm; reg [20:0] nn;
    assign mv_rdy = !busy && !mv_fault;
    assign fence_rdy = !busy;
    wire [2:0] s_es = (sf == 3'd0 || sf == 3'd5) ? 3'd4 : (sf == 3'd1) ? 3'd2 : 3'd1;
    wire [2:0] d_es = (dsp == 2'd0) ? ((df == 3'd0 || df == 3'd5) ? 3'd4 : (df == 3'd1) ? 3'd2 : 3'd1) : 3'd4;
    // ---- element walk (incremental addresses, bytes)
    reg [19:0] o; reg [20:0] i;
    reg [41:0] srow, sa, drow, da;            // byte addresses (VM: word x 4)
    // ---- source sector cache / destination sector buffer
    reg        sc_ok; reg [36:0] sc_sec; reg [255:0] sc_dat;
    reg        db_dirty; reg [36:0] db_sec; reg [255:0] db_dat; reg [31:0] db_strb;
    reg [2:0]  ph;                            // 0 element, 1 read wait, 2 write wait, 3 final flush wait, 4 done
    reg        rd_pend, wr_pend;
    wire [36:0] s_sec = sa[41:5], d_sec = da[41:5];
    wire [4:0]  s_off = sa[4:0], d_off = da[4:0];
    // ---- element extract + convert
    wire [31:0] raw32 = sc_dat[{s_off[4:2], 5'd0} +: 32];
    wire [15:0] raw16 = sc_dat[{s_off[4:1], 4'd0} +: 16];
    wire [7:0]  raw8  = sc_dat[{s_off, 3'd0} +: 8];
    function automatic [31:0] i8_f(input [7:0] c);               // INT8 -> binary32 (exact)
        reg [7:0] a; reg [2:0] p; integer k;
        begin
            a = c[7] ? (~c + 8'd1) : c; p = 3'd0;
            for (k = 0; k < 8; k = k + 1) if (a[k]) p = k[2:0];
            i8_f = (a == 8'd0) ? 32'd0 : {c[7], 8'd127 + {5'd0, p}, ({15'd0, a} << (5'd23 - {2'd0, p})) & 23'h7FFFFF};
        end
    endfunction
    function automatic [31:0] e4m3_f(input [7:0] c);             // FP8 E4M3 -> binary32 (exact; NaN code -> qNaN)
        reg [3:0] e; reg [2:0] m; reg [1:0] p;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 4'hF && m == 3'h7) e4m3_f = 32'h7FC00000;
            else if (e == 4'd0) begin                             // subnormal m / 8 x 2^-6
                if (m == 3'd0) e4m3_f = {c[7], 31'd0};
                else begin
                    p = m[2] ? 2'd2 : m[1] ? 2'd1 : 2'd0;              // msb of m
                    e4m3_f = {c[7], 8'd127 - 8'd9 + {6'd0, p}, ({20'd0, m} << (5'd23 - {3'd0, p})) & 23'h7FFFFF};
                end
            end else e4m3_f = {c[7], 8'd120 + {4'd0, e}, m, 20'd0};
        end
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
            if (ex == 8'hFF) to_e4m3 = {x[31], 7'h7E};          // inf -> saturate (to_fp8 min(., 448)); NaN not expected
            else if (ex >= 8'd136) to_e4m3 = {x[31], 7'h7E};    // >= 512: saturate to 448 (code 0x7E)
            else begin
                // quantum exponent: max(e - 3, -9) with e = ex - 127 (normal binade, subnormals share -6)
                mant = (ex == 8'd0) ? 24'd0 : {1'b1, x[22:0]};
                sh = (ex >= 8'd121) ? 20 : (20 + 121 - ex);        // keep 3 fraction bits in the binade (>= 2^-6) or fewer
                if (sh > 24) begin q = 25'd0; end
                else begin
                    q = {1'b0, mant} >> sh;
                    // RNE on the dropped bits
                    if (sh > 0 && mant[sh - 1] && ((mant & ((24'd1 << (sh - 1)) - 24'd1)) != 0 || q[0])) q = q + 25'd1;
                end
                // q counts quanta: normal binade ex >= 121: q in [8, 16] (16 = carry into the next binade)
                if (ex >= 8'd121) begin
                    e4 = ex - 8'd120; mq = q[4] ? 4'd8 : q[3:0];
                    if (q[4]) e4 = e4 + 5'd1;
                    code = (e4 > 5'd15) ? 8'h7F : {e4[3:0], mq[2:0]};
                end else code = {1'b0, 4'd0, q[2:0]} + (q[3] ? 8'd8 : 8'd0);   // subnormal (q = 8: the 2^-6 normal)
                if (code > 8'h7E) code = 8'h7E;                    // > 448 after rounding: saturate
                to_e4m3 = (code == 8'd0) ? 8'd0 : {x[31], code[6:0]};
            end
        end
    endfunction
    reg [31:0] dec;                                             // the element as a VM word (LOAD) / FP32 (STORE src)
    always @* begin
        if (ssp == 2'd1) dec = raw32;                          // VM source: the word
        else case (sf)
            3'd1: dec = {raw16, 16'd0};
            3'd2: dec = e4m3_f(raw8);
            3'd4: dec = i8_f(raw8);
            default: dec = raw32;
        endcase
    end
    reg [31:0] enc; reg [3:0] enc_n;                            // bytes of the destination element
    always @* begin
        if (dsp == 2'd1) begin enc = dec; enc_n = 4'd4; end
        else case (df)
            3'd1: begin enc = {16'd0, to_bf16(dec)}; enc_n = 4'd2; end
            3'd2: begin enc = {24'd0, to_e4m3(dec)}; enc_n = 4'd1; end
            default: begin enc = dec; enc_n = 4'd4; end
        endcase
    end
    wire [255:0] put_dat = {224'd0, enc} << {d_off, 3'd0};
    wire [31:0]  put_strb = ((enc_n == 4'd4) ? 32'hF : (enc_n == 4'd2) ? 32'h3 : 32'h1) << d_off;
    wire [255:0] put_mask = ((enc_n == 4'd4) ? {224'd0, 32'hFFFFFFFF} : (enc_n == 4'd2) ? {240'd0, 16'hFFFF} :
                             {248'd0, 8'hFF}) << {d_off, 3'd0};
    wire last_elem = (o == mm - 20'd1) && (i == nn - 21'd1);
    // ---- VM / kport response capture
    reg [273:0] vr; always @(posedge clk) vr <= vmr;
    reg kv_r, kwe_r; reg [255:0] kd_r; reg kf_r;
    always @(posedge clk) begin kv_r <= k_rsp_v; kwe_r <= k_rsp_we; kd_r <= k_rsp_data; kf_r <= k_fault; end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; mv_done <= 1'b0; mv_fault <= 1'b0; fence_done <= 1'b0; k_req_v <= 1'b0; vmq <= 338'd0;
            sc_ok <= 1'b0; db_dirty <= 1'b0; ph <= 3'd0; rd_pend <= 1'b0; wr_pend <= 1'b0; o <= 0; i <= 0;
            k_req_we <= 1'b0; k_req_addr <= 0; k_req_wdata <= 0; k_req_wstrb <= 0;
        end else begin
            mv_done <= 1'b0; fence_done <= 1'b0; vmq[337] <= 1'b0;
            if (k_req_v && k_req_rdy) k_req_v <= 1'b0;
            if (fence_v && fence_rdy) fence_done <= 1'b1;
            if (kf_r) mv_fault <= 1'b1;
            if (mv_v && mv_rdy) begin
                {nn, mm, dis, dst, db, df, dsp, sis, sst, sb, sf, ssp} <= mv;
                busy <= 1'b1; o <= 0; i <= 0; sc_ok <= 1'b0; db_dirty <= 1'b0; ph <= 3'd0;
                srow <= (mv[1:0] == 2'd1) ? {mv[44:5], 2'b00} : {2'd0, mv[44:5]};
                sa   <= (mv[1:0] == 2'd1) ? {mv[44:5], 2'b00} : {2'd0, mv[44:5]};
                drow <= (mv[94:93] == 2'd1) ? {mv[137:98], 2'b00} : {2'd0, mv[137:98]};
                da   <= (mv[94:93] == 2'd1) ? {mv[137:98], 2'b00} : {2'd0, mv[137:98]};
                if ((mv[1:0] > 2'd1) || (mv[94:93] > 2'd1) || mv[4:2] == 3'd3 || mv[4:2] == 3'd6 || mv[97:95] == 3'd3 ||
                    mv[97:95] == 3'd6 || mv[97:95] == 3'd4 || mv[205:186] == 20'd0 || mv[226:206] == 21'd0) begin
                    mv_fault <= 1'b1; busy <= 1'b0;
                end
            end
            if (busy && !mv_fault) case (ph)
                3'd0: begin
                    if ((s_es == 3'd4 && sa[1:0] != 2'd0) || (s_es == 3'd2 && sa[0]) ||
                        (d_es == 3'd4 && da[1:0] != 2'd0) || (d_es == 3'd2 && da[0])) begin
                        mv_fault <= 1'b1; busy <= 1'b0;                          // an element not naturally aligned
                    end else if (!sc_ok || sc_sec != s_sec) begin                     // source sector miss: read it
                        if (ssp == 2'd0) begin k_req_v <= 1'b1; k_req_we <= 1'b0; k_req_addr <= {s_sec[31:0], 5'd0}; end
                        else vmq <= {1'b1, 1'b0, s_sec[26:0], 5'd0, 256'd0, 32'd0, 16'h4D52};
                        ph <= 3'd1;
                    end else if (db_dirty && db_sec != d_sec) begin          // destination sector change: flush
                        if (dsp == 2'd0) begin k_req_v <= 1'b1; k_req_we <= 1'b1; k_req_addr <= {db_sec[31:0], 5'd0};
                                               k_req_wdata <= db_dat; k_req_wstrb <= db_strb; end
                        else vmq <= {1'b1, 1'b1, db_sec[26:0], 5'd0, db_dat, db_strb, 16'h4D57};
                        ph <= 3'd2;
                    end else begin                                            // the element
                        db_sec <= d_sec; db_dirty <= 1'b1;
                        db_dat <= ((db_dirty ? db_dat : 256'd0) & ~put_mask) | put_dat;
                        db_strb <= (db_dirty ? db_strb : 32'd0) | put_strb;
                        if (last_elem) ph <= 3'd3;
                        else if (i == nn - 21'd1) begin
                            i <= 0; o <= o + 20'd1;
                            srow <= srow + ((ssp == 2'd1) ? {8'd0, sst, 2'b00} : {10'd0, sst});
                            sa   <= srow + ((ssp == 2'd1) ? {8'd0, sst, 2'b00} : {10'd0, sst});
                            drow <= drow + ((dsp == 2'd1) ? {8'd0, dst, 2'b00} : {10'd0, dst});
                            da   <= drow + ((dsp == 2'd1) ? {8'd0, dst, 2'b00} : {10'd0, dst});
                        end else begin
                            i <= i + 21'd1;
                            sa <= sa + ({26'd0, sis} * s_es);
                            da <= da + ({26'd0, dis} * ((dsp == 2'd1) ? 3'd4 : d_es));
                        end
                    end
                end
                3'd1: begin                                                    // read response
                    if (ssp == 2'd0 && kv_r && !kwe_r) begin sc_dat <= kd_r; sc_sec <= s_sec; sc_ok <= 1'b1; ph <= 3'd0; end
                    if (ssp == 2'd1 && vr[273] && !vr[256]) begin sc_dat <= vr[255:0]; sc_sec <= s_sec; sc_ok <= 1'b1; ph <= 3'd0; end
                end
                3'd2, 3'd4: begin                                              // write acknowledgement
                    if ((dsp == 2'd0 && kv_r && kwe_r) || (dsp == 2'd1 && vr[273] && vr[256])) begin
                        db_dirty <= 1'b0;
                        if (ph == 3'd4) begin busy <= 1'b0; mv_done <= 1'b1; end
                        ph <= (ph == 3'd4) ? 3'd0 : 3'd0;
                    end
                end
                3'd3: begin                                                    // final flush
                    if (dsp == 2'd0) begin k_req_v <= 1'b1; k_req_we <= 1'b1; k_req_addr <= {db_sec[31:0], 5'd0};
                                           k_req_wdata <= db_dat; k_req_wstrb <= db_strb; end
                    else vmq <= {1'b1, 1'b1, db_sec[26:0], 5'd0, db_dat, db_strb, 16'h4D57};
                    ph <= 3'd4;
                end
                default: ph <= 3'd0;
            endcase
        end
    end
endmodule
`default_nettype wire
