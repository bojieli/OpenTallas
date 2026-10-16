`timescale 1ns/1ps
`default_nettype none
// HGI-1 quant unit (FUSED.QDQ_*) as one die block body (hgi-takeover 2026-10-09): the normative record bus
// (ot_hgi_quant_record) -> the qualified VM transport (ot_hgi_quant_vm_transport, which owns the 23-edge decode core)
// -> the VM packet client.  Die-side protocol: the VM fast path -- up to 4 requests outstanding (the transport counts
// them), in-order responses; the request needs no ready (the VM station queues 4) and the response no back-pressure.
// Return = {fault, done, ready}.
// tput-gate-1010 (2026-10-10, AGENTS.md throughput qualification): WIDE = 1 adds ot_hgi_quant_wide on a VM lane group
// (lane b <-> bank b; ot_hgi_vm_unit RP / W2 layout, the FUSED lgE slot in hb_quant): a record whose shape is on the
// fast path (QDQ header legal, A / O VM FP32-word, inner stride 1, 8-word aligned bases / strides, inside VM, disjoint or
// identical regions) runs there at one 32-element beat a cycle; every other record goes to the packet transport
// unchanged (its rules and faults).  WIDE = 0 is byte-identical in behaviour to the previous unit (+0 edges).  WIDE = 1
// adds a 3-edge steering station in front (eligibility: the span multiplies are registered before the compares).
module ot_hgi_quant_unit #(
    parameter integer SERIAL_SHAPE = 0,
    parameter integer MUT = 0,         // bench: transport MUTANT (4 = responses paired with the newest request)
    parameter integer WIDE = 0,
    parameter integer WLQ = 16,        // lane credits (WIDE)
    parameter integer WMUT = 0,        // bench: ot_hgi_quant_wide MUT; 3 = every record forced to the packet path
    parameter integer WNB = 16, WOD = 32
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [682:0]  rec,           // {n_O, n_A, desc_O, desc_A, header, valid}
    output reg  [2:0]    ret,           // {fault, done, ready}
    output reg  [337:0]  vmq,           // {v, req 337}
    input  wire [273:0]  vmr,           // {v, rsp 273}
    // VM lane group (WIDE = 1; tie the inputs 0 / gnt 1 otherwise)
    output wire [32*16-1:0]  wrq,
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr,
    output wire [32*280-1:0] wwq,
    input  wire [31:0]       wwq_cr,
    input  wire [31:0]       wwq_done,
    output wire              rg_req,
    input  wire              rg_gnt,
    output wire              wg_req,
    input  wire              wg_gnt
);
    wire [1408:0] cmd;
    wire nfault, ready, done, fault, drained, req_v, rsp_r;
    wire [336:0] req;
    ot_hgi_quant_record u_rec (.clk(clk), .rst_n(rst_n), .rec(rec), .cmd(cmd), .nfault(nfault));
    // the die station queues the request: every staged request is taken the next cycle
    wire take = req_v;
    generate if (!WIDE) begin : g_packet
        ot_hgi_quant_vm_transport #(.ENABLE(1), .MUTANT(MUT), .SERIAL_SHAPE(SERIAL_SHAPE)) u_tr (.clk(clk), .rst_n(rst_n), .cmd(cmd), .ready(ready), .done(done),
            .fault(fault), .drained(drained), .req_v(req_v), .req_r(take), .req(req), .rsp_v(vmr[273]), .rsp_r(rsp_r),
            .rsp(vmr[272:0]), .provider_fault(1'b0));
        assign wrq = '0; assign wwq = '0; assign rg_req = 1'b0; assign wg_req = 1'b0;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin vmq <= 338'd0; ret <= 3'd0; end
            else begin
                vmq <= {take, req};
                ret <= {fault | nfault, done, ready & drained};
            end
    end else begin : g_wide
        // ---- steering station: S1 capture, S2 spans, S3 compares -> wide go | packet cmd
        reg [2:0] st; reg [1408:0] c;
        wire [127:0] h = c[128:1];
        wire [255:0] a = c[385 +: 256], o = c[1153 +: 256];
        wire [5:0] op = h[123:118];
        wire [19:0] an = a[67:48], am = a[87:68], on = o[67:48], om = o[87:68];
        wire [31:0] ars = a[119:88], ors = o[119:88];
        wire [39:0] ab = a[47:8], ob = o[47:8];
        reg fld_q, fast_q, same_q; reg [63:0] aend_q, oend_q;
        wire fld = h[127:124] == 4 && op >= 4 && op <= 6 && h[99:93] == 7'b0010001 && !h[92] &&
                   (op != 6 || h[71:64] == 16) && a[1:0] == 1 && o[1:0] == 1 && a[4:2] == 0 && (o[4:2] == 0 || o[4:2] == 1) &&
                   !o[5] && am != 0 && am == om && an != 0 && an == on && (op == 6 ? an[3:0] == 0 : an[4:0] == 0);
        wire fast = !a[5] && a[135:120] <= 16'd1 && o[135:120] <= 16'd1 && ab[2:0] == 0 && ob[2:0] == 0 && an[2:0] == 0 &&
                    (am == 20'd1 || (ars[2:0] == 0 && ors[2:0] == 0 && ars >= {12'd0, an} && ors >= {12'd0, on}));
        wire elig = fld_q && fast_q && aend_q < 64'd262144 && oend_q < 64'd262144 &&
                    ((aend_q < {24'd0, ob}) || (oend_q < {24'd0, ab}) || (same_q && ab == ob)) && WMUT != 3;
        wire t_ready, t_done, t_fault, t_drained;
        reg t_go;
        wire w_idle, w_done, w_fault;
        reg w_go;
        ot_hgi_quant_vm_transport #(.ENABLE(1), .MUTANT(MUT), .SERIAL_SHAPE(SERIAL_SHAPE)) u_tr (.clk(clk), .rst_n(rst_n),
            .cmd({c[1408:1], t_go}), .ready(t_ready), .done(t_done), .fault(t_fault), .drained(t_drained), .req_v(req_v),
            .req_r(take), .req(req), .rsp_v(vmr[273]), .rsp_r(rsp_r), .rsp(vmr[272:0]), .provider_fault(1'b0));
        ot_hgi_quant_wide #(.NB(WNB), .OD(WOD), .LQ(WLQ), .MUT(WMUT == 3 ? 0 : WMUT)) u_w (.clk(clk), .rst_n(rst_n),
            .go(w_go), .cmd(c), .idle(w_idle), .done(w_done), .fault(w_fault), .wrq(wrq), .wrq_cr(wrq_cr), .wrr(wrr),
            .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done), .rg_req(rg_req), .rg_gnt(rg_gnt), .wg_req(wg_req), .wg_gnt(wg_gnt));
        // st: 0 idle | 1 captured | 2 spans | 3 compares + launch | 4 running
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                st <= 0; c <= '0; t_go <= 0; w_go <= 0; fld_q <= 0; fast_q <= 0; same_q <= 0; aend_q <= 0; oend_q <= 0;
                vmq <= 338'd0; ret <= 3'd0;
            end else begin
                t_go <= 0; w_go <= 0;
                vmq <= {take, req};
                case (st)
                    0: if (cmd[0]) begin c <= cmd; st <= 1; end
                    1: begin
                        fld_q <= fld; fast_q <= fast; same_q <= ars == ors;
                        aend_q <= {24'd0, ab} + (64'(am) - 64'd1) * 64'(ars) + 64'(an) - 64'd1;
                        oend_q <= {24'd0, ob} + (64'(om) - 64'd1) * 64'(ors) + 64'(on) - 64'd1;
                        st <= 2;
                    end
                    2: begin if (elig) w_go <= 1; else t_go <= 1; st <= 3; end
                    3: st <= 4;
                    4: if (w_idle && t_ready && t_drained && !w_go && !t_go) st <= 0;
                    default: st <= 0;
                endcase
                ret <= {t_fault | w_fault | nfault, t_done | w_done, st == 0 && !cmd[0] && w_idle && t_ready && t_drained};
            end
        // the transport takes its command while ready (it is idle whenever the station is)
    end endgenerate
endmodule
`default_nettype wire
