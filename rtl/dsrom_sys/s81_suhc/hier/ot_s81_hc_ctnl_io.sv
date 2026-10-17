// ot_s81_hc_ctnl_l2io (HC-COLUMN 10-16): ot_s81_hc_ctnl_l2 with IO_ROOT 1 -- the lane-2 tile's ~1.3k boundary registers
// (fdx / fv / write-back / request pin capture flops and the hpr / hrq read registers) on a second clock entry clk_io.
// Native repair of ctnl_l2 np2 (launch 222.8 / capture 208.7 ps: an overloaded 60.7 ps core-tree leaf under the hrq
// launch flops and route hold-ECO HB2 pairs on 42 fdx captures).  Same logic, same edges; the parent ties clk_io to clk.
module ot_s81_hc_ctnl_l2io #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, RLY = 2, PIN_STAGE = 1, CHAIN_STEP = 6
) (
    input  wire                  clk,
    input  wire                  clk_io,              // second entry of the same clock: the boundary-register tree
    input  wire                  rst_in,
    input  wire [7:0]            tid,
    input  wire [1:0]            bank,
    input  wire [1:0]            lane,
    input  wire                  last,
    input  wire [S_RD+4:0]       fv,
    input  wire [FXW-1:0]        fdx,
    input  wire                  wb_v, wb_en, wb_hs,  // hc_post write back (ctpl flops)
    input  wire [15:0]           wb_ob,
    input  wire [63:0]           wb_d,                // group lq's 4 hc_post outputs, BF16
    input  wire [16*S_RT-1:0]    rq_q,                // return pin flops (ctr): row field
    input  wire                  hs_run,
    input  wire [15:0]           hs_c,
    output reg  [63:0]           hpr,                 // hc_post row read, group lq (zero unless this bank)
    output reg  [64*S_RT-1:0]    hrq,                 // return h row reads, group lq (zero unless this bank)
    input  wire [31:0]           cy_in,               // octet carry (lane 0)
    input  wire [31:0]           acc_in,              // chain: previous lane's adder output
    input  wire [31:0]           sqn_in,              // chain: next lane's square
    output wire [31:0]           sq_out,
    output wire [31:0]           acc_out,
    output reg  [31:0]           cy_out,              // registered acc_out (the octet carry at lane 2)
    output wire [15:0]           yb,
    output reg                   flt
);
    localparam integer O_D=72+16*S_RD, P_BITS=352, FXW=O_D+S_RD*P_BITS,
                       FULL_FXW=O_D+S_RD*512;

    // Constant bit maps: HLOAD64-bit lane words, GAIN32-bit lane words, shared pre128.
    function automatic integer lane_payload_width(input integer ln);
        begin case(ln) 0:lane_payload_width=256; 1:lane_payload_width=288;
              2:lane_payload_width=352; default:lane_payload_width=288; endcase end
    endfunction
    function automatic integer lane_payload_needed(input integer ln,input integer bitno);
        integer g;
        begin
            lane_payload_needed=(bitno<128) ||
                (bitno>=64*ln && bitno<64*ln+64) ||
                (bitno>=64*(ln+4) && bitno<64*(ln+4)+64);
            for(g=0;g<4;g=g+1)
                if(bitno>=32*(ln+4*g) && bitno<32*(ln+4*g)+32)
                    lane_payload_needed=1;
        end
    endfunction
    function automatic integer lane_payload_rank(input integer ln,input integer bitno);
        integer b;
        begin lane_payload_rank=0;
            for(b=0;b<bitno;b=b+1) lane_payload_rank=lane_payload_rank+lane_payload_needed(ln,b);
        end
    endfunction
    function automatic integer lane_payload_index(input integer ln,input integer packedbit);
        integer b,c;
        begin lane_payload_index=0;c=0;
            for(b=0;b<512;b=b+1) if(lane_payload_needed(ln,b)) begin
                if(c==packedbit) lane_payload_index=b;
                c=c+1;
            end
        end
    endfunction
    wire [FULL_FXW-1:0] fdx_full;
    assign fdx_full[O_D-1:0]=fdx[O_D-1:0];
    for(genvar rp=0;rp<S_RD;rp=rp+1) begin : g_read_port
        for(genvar b=0;b<512;b=b+1) begin : g_expand
            if(lane_payload_needed(2,b)) begin : g_keep
                localparam integer PBIT=lane_payload_rank(2,b);
                assign fdx_full[O_D+rp*512+b]=fdx[O_D+rp*P_BITS+PBIT];
            end else begin : g_unused
                assign fdx_full[O_D+rp*512+b]=1'b0;
            end
        end
    end
    ot_s81_hc_ctnl #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),
        .ML(ML),.AL(AL),.RLY(RLY),.PIN_STAGE(PIN_STAGE),.CHAIN_STEP(CHAIN_STEP),.FIXED_LANE(2),.IO_ROOT(1)) u_core
        (.fdx(fdx_full),.clk_io(clk_io),.*);
`ifndef SYNTHESIS
    always @(posedge clk) if(rst_in && lane!=2'd2) $error("fixed HC lane2 identity mismatch");
`endif
endmodule
