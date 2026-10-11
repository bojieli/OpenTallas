`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hgi_coll_rgx_snk (hgi-1010/c 2026-10-10): the die-side write path of the hardware COLL.ROW_GATHER sink in hfd_coll.
// ot_hgi_coll_ep rg_w (DEL lanes, each one 512-bit flit = 2 sectors at O address: VM word address when rg_w_vm, else HBM
// byte address) ->
//   VM space   a client of the VM's shared W2 wide-write group (ot_hgi_vm_lanearb, lead decision (a) 2026-10-10): lane b
//              writes bank b, {v, sector 15, data 256, word mask 8}; LQ credits a lane (returned by the VM at acceptance);
//              one done a lane per write.  Up to 2 x DEL sectors a cycle: a flit goes when both its banks are free this
//              cycle and hold a credit (lane order priority), else its rg_w lane waits.  The group is requested (c_req)
//              while flits are pending or writes / credits are outstanding (burst ownership: every credit home, every
//              done landed before release).  A VM address that is not sector aligned faults (sticky).
//   HBM space  two write clients (one sector in flight each, flit sector 0 on client 0, sector 1 on client 1), die nets
//              t_hgi_rgxw{0,1} {data 256, strb 32, addr 37, v} 326 b -> the loader's ot_hgi_hbm_wr_server on its own
//              ot_hfd_loader_kport lane; f_hgi_rgxa{0,1} 1 b = the lane's write acknowledgement.
// Every die / group output leaves a flop.  MUT (bench): 1 the second sector of a VM flit goes to bank + 2 (wrong row):
// must FAIL; 2 the HBM client acks before the lane write is acknowledged (counts the request): must FAIL.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_coll_rgx_snk #(
    parameter integer DEL = 4,
    parameter integer FW  = 512,
    parameter integer LQ  = 8,
    parameter integer MUT = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire [DEL-1:0]     rg_w_v,
    input  wire [DEL*40-1:0]  rg_w_addr,
    input  wire               rg_w_vm,
    input  wire [DEL*FW-1:0]  rg_w_data,
    output wire [DEL-1:0]     rg_w_rdy,        // the ep pops its head flit at this edge (VM: taken now; HBM: acked)
    // W2 group client (ot_hgi_vm_lanearb c_*)
    output reg                c_req,
    input  wire               c_gnt,
    output reg  [32*280-1:0]  c_q,
    input  wire [31:0]        c_cr,
    input  wire [31:0]        c_rsp,
    // HBM write lanes (die)
    output reg  [2*326-1:0]   xw,
    input  wire [1:0]         xwa,
    output reg                fault
);
    localparam integer CW = $clog2(LQ + 1);
    reg [CW-1:0] cr [0:31];
    reg [9:0] outst;                       // VM writes sent, done not yet back
    reg [CW+5:0] crs;                      // credits home (sum)
    // ---- VM path: per cycle, the flits whose two banks are free and credited
    reg [DEL-1:0] acc_v; reg [31:0] used; reg [31:0] take_b; reg [14:0] sec_b [0:31]; reg [255:0] dat_b [0:31];
    reg mis;
    always @* begin
        acc_v = '0; used = 32'd0; take_b = 32'd0; mis = 1'b0;
        for (integer b = 0; b < 32; b = b + 1) begin sec_b[b] = 15'd0; dat_b[b] = 256'd0; end
        for (integer l = 0; l < DEL; l = l + 1) begin : vl
            reg [14:0] s0, s1; reg [4:0] b0, b1;
            s0 = rg_w_addr[l*40 + 3 +: 15]; s1 = s0 + 15'd1;
            b0 = s0[4:0]; b1 = (MUT == 1) ? s0[4:0] + 5'd2 : s1[4:0];
            if (rg_w_v[l] && rg_w_vm && rg_w_addr[l*40 +: 3] != 3'd0) mis = 1'b1;
            if (rg_w_v[l] && rg_w_vm && c_gnt && rg_w_addr[l*40 +: 3] == 3'd0 && !used[b0] && !used[b1] &&
                cr[b0] != '0 && cr[b1] != '0) begin
                acc_v[l] = 1'b1; used[b0] = 1'b1; used[b1] = 1'b1; take_b[b0] = 1'b1; take_b[b1] = 1'b1;
                sec_b[b0] = s0; dat_b[b0] = rg_w_data[l*FW +: 256];
                sec_b[b1] = s1; dat_b[b1] = rg_w_data[l*FW + 256 +: 256];
            end
        end
    end
    // ---- HBM path: one flit at a time over the two clients (sector 0 on client 0, sector 1 on client 1)
    reg h_busy; reg [1:0] h_wait; reg [DEL-1:0] h_lane_oh;
    reg [$clog2(DEL > 1 ? DEL : 2)-1:0] h_pick; reg h_any;
    always @* begin
        h_any = 1'b0; h_pick = '0;
        for (integer l = DEL - 1; l >= 0; l = l - 1) if (rg_w_v[l] && !rg_w_vm) begin h_any = 1'b1; h_pick = l[$clog2(DEL > 1 ? DEL : 2)-1:0]; end
    end
    reg [DEL-1:0] h_rdy;
    assign rg_w_rdy = acc_v | h_rdy;
    integer b, l;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (b = 0; b < 32; b = b + 1) cr[b] <= CW'(LQ);
            c_req <= 1'b0; c_q <= '0; h_rdy <= '0; outst <= 10'd0; fault <= 1'b0; crs <= (CW+6)'(32 * LQ);
            xw <= '0; h_busy <= 1'b0; h_wait <= 2'd0;
        end else begin : seq
            integer nd, nc, ns;
            if (mis) fault <= 1'b1;
            // VM group lanes (registered): a taken bank's lane carries its sector
            nd = 0; nc = 0; ns = 0;
            for (b = 0; b < 32; b = b + 1) begin
                c_q[b*280 + 279] <= take_b[b];
                if (take_b[b]) c_q[b*280 +: 279] <= {sec_b[b], dat_b[b], 8'hFF};
                cr[b] <= cr[b] - CW'(take_b[b]) + CW'(c_cr[b]);
                if (c_rsp[b]) nd = nd + 1;
                if (c_cr[b]) nc = nc + 1;
                if (take_b[b]) ns = ns + 1;
            end
            outst <= outst + 10'(ns) - 10'(nd);
            crs <= crs - (CW+6)'(ns) + (CW+6)'(nc);
            h_rdy <= '0;
            // ownership: hold while anything is pending, in flight or not home
            c_req <= (|(rg_w_v & {DEL{rg_w_vm}})) || outst != 10'd0 || ns != 0 || crs != (CW+6)'(32 * LQ) || (c_req && !c_gnt);
            // HBM writes
            xw[0] <= 1'b0; xw[326] <= 1'b0;
            if (!h_busy && h_any && h_rdy == '0) begin : hs
                reg [36:0] a0;
                a0 = rg_w_addr[h_pick*40 +: 37];
                xw[0 +: 326]   <= {rg_w_data[h_pick*FW +: 256], 32'hFFFFFFFF, a0, 1'b1};
                xw[326 +: 326] <= {rg_w_data[h_pick*FW + 256 +: 256], 32'hFFFFFFFF, a0 + 37'd32, 1'b1};
                h_busy <= 1'b1; h_wait <= 2'b11; h_lane_oh <= DEL'(1) << h_pick;
                if (a0[4:0] != 5'd0) fault <= 1'b1;
            end else if (h_busy) begin
                if (MUT == 2) h_wait <= 2'b00;
                else h_wait <= h_wait & ~xwa;
                if ((MUT == 2) || (h_wait & ~xwa) == 2'b00) begin h_busy <= 1'b0; h_rdy <= h_lane_oh; end
            end
        end
    end
endmodule

`default_nettype wire
