`timescale 1ns/1ps
// tb_dsfd_capt_status_x43_eq (S-VM-CAPT-X43RST 2026-10-16): the S leaf with the 2-flop local reset stage
// (dsfd_capt_status_x43_s, rsv -> rv -> state) against a FROZEN copy of the rsv-direct S leaf it replaces
// (dsfd_capt_status_x43_s_rsvref below = dsfd_capt_status_x43_s of main 61d167710, mutant ifdefs removed).  Both see
// the same ckv / rsv / pins; t_st is compared (4-state, !==) every half time unit from time 0, i.e. at and between
// every edge, so ANY change of the edge on which an output changes, or of the reset value, fails.
//   pins: the real dsfd_capt_status_x43_t on ck (f_sn random every stream cycle) in "proto" segments, random junk in
//   "junk" segments (exercises every fault-check branch); 40 segments, each: both resets asserted at a random time
//   (mid-epoch), held a random time, then released ALIGNED (just before a coincident epoch edge, the contract) or at a
//   random offset (slips; rsv may be released on any ckv phase).  Coverage counters must be nonzero.
//   -> TB_STX43EQ PASS checks <n> segments <s> aligned <a> fault_cycles <f> data_cycles <d>
//   -> TB_STX43EQ FAIL mismatches <m> ...
module dsfd_capt_status_x43_s_rsvref (
    input  wire [0:0]  ckv,
    input  wire [0:0]  rsv,
    input  wire [63:0] b0, b2, b3,
    input  wire [2:0]  bpar,
    input  wire        t_mark,
    output wire [63:0] t_st
);
    reg [1:0] sp; reg se; reg warm; reg mk; reg flt;
    reg [63:0] stq;
    reg [63:0] sh0, sh2, sh3; reg [2:0] bq;
    always @(posedge ckv[0]) begin sh0 <= b0; sh2 <= b2; sh3 <= b3; bq <= bpar; end
    wire [1:0] sn = (sp == 2'd2) ? 2'd0 : sp + 2'd1;
    always @(posedge ckv[0] or negedge rsv[0])
        if (!rsv[0]) begin sp <= 2'd2; se <= 1'b0; warm <= 1'b0; mk <= 1'b0; flt <= 1'b0; end
        else begin
            sp <= sn;
            mk <= t_mark;
            if (warm && mk != (sn == 2'd0)) flt <= 1'b1;
            case (sn)
                2'd0: begin se <= ~se; if (warm && bq[1] != se) flt <= 1'b1; end
                2'd1: begin warm <= 1'b1; if (warm && bq[2] != ~se) flt <= 1'b1; end
                default: if (warm && bq[0] != se) flt <= 1'b1;
            endcase
        end
    reg [63:0] rd;
    always @(*)
        case (sn)
            2'd0: rd = sh2;
            2'd1: rd = sh3;
            default: rd = sh0;
        endcase
    always @(posedge ckv[0] or negedge rsv[0])
        if (!rsv[0]) stq <= 64'd0;
        else if (warm) stq <= {rd[63:4], rd[3] | flt, rd[2:0]};
    assign t_st = stq;
endmodule

module tb_dsfd_capt_status_x43_eq;
    // die clocks as tb_dsfd_capt_status_x43: 1 unit = 1/2 VCO tick, ck period 6, ckv period 8, coincident at 24k + 3
    reg ck = 1'b0, ckv = 1'b0;
    initial forever begin #3 ck = 1'b1; #3 ck = 1'b0; end
    initial begin #3 forever begin ckv = 1'b1; #4 ckv = 1'b0; #4; end end
    reg rst = 1'b0, rsv = 1'b0, junk = 1'b0;
    reg [63:0] f_sn = 64'd0, j0 = 64'd0, j2 = 64'd0, j3 = 64'd0; reg [2:0] jp = 3'd0; reg jm = 1'b0;
    wire [63:0] b0, b2, b3; wire [2:0] bpar; wire t_mark;
    dsfd_capt_status_x43_t ut (.ck(ck), .rst(rst), .f_sn(f_sn), .b0(b0), .b2(b2), .b3(b3), .bpar(bpar), .t_mark(t_mark));
    wire [63:0] p0 = junk ? j0 : b0, p2 = junk ? j2 : b2, p3 = junk ? j3 : b3;
    wire [2:0]  pp = junk ? jp : bpar;
    wire        pm = junk ? jm : t_mark;
    wire [63:0] t_new, t_ref;
    dsfd_capt_status_x43_s        un (.ckv(ckv), .rsv(rsv), .b0(p0), .b2(p2), .b3(p3), .bpar(pp), .t_mark(pm), .t_st(t_new));
    dsfd_capt_status_x43_s_rsvref ur (.ckv(ckv), .rsv(rsv), .b0(p0), .b2(p2), .b3(p3), .bpar(pp), .t_mark(pm), .t_st(t_ref));
    always @(negedge ck) begin
        f_sn <= {$random, $random};
        j0 <= {$random, $random}; j2 <= {$random, $random}; j3 <= {$random, $random}; jp <= $random; jm <= $random;
    end
    integer bad = 0, checks = 0, fault_cycles = 0, data_cycles = 0, segs = 0, aligned = 0, k, d;
    initial begin
        #0.25;
        forever begin
            if (t_new !== t_ref) begin
                bad = bad + 1;
                if (bad < 6) $display("TB_STX43EQ MISMATCH t=%0t rsv=%b new %h ref %h", $realtime, rsv, t_new, t_ref);
            end
            checks = checks + 1;
            #0.5;
        end
    end
    always @(negedge ckv) if (rsv) begin
        if (t_ref[3]) fault_cycles = fault_cycles + 1;
        if (t_ref != 64'd0 && t_ref !== 64'bx) data_cycles = data_cycles + 1;
    end
    initial begin
        #98;                                   // first release just before the coincident edge at 99
        for (k = 0; k < 40; k = k + 1) begin
            junk = (k % 4 == 3);
            if (k % 3 != 2) begin              // ALIGNED: both released 1 unit before a coincident epoch edge
                rst = 1'b1; rsv = 1'b1; aligned = aligned + 1;
            end else begin                     // slipped: independent random release offsets (any phase)
                d = {$random} % 30; #(d) rst = 1'b1;
                d = {$random} % 30; #(d) rsv = 1'b1;
            end
            segs = segs + 1;
            #(24 * (20 + {$random} % 20) + {$random} % 24);
            // re-reset at a random (mid-epoch) time, held a random number of units
            d = {$random} % 2; if (d) begin rsv = 1'b0; #({$random} % 7) rst = 1'b0; end
            else begin rst = 1'b0; #({$random} % 7) rsv = 1'b0; end
            #(5 + {$random} % 50);
            // advance to 1 unit before the next coincident edge (24 m + 3)
            d = ($time - 2) % 24; #(24 - d);
        end
        #(24 * 20);
        if (bad == 0 && checks > 10000 && aligned > 20 && fault_cycles > 0 && data_cycles > 1000)
            $display("TB_STX43EQ PASS checks %0d segments %0d aligned %0d fault_cycles %0d data_cycles %0d",
                     checks, segs, aligned, fault_cycles, data_cycles);
        else
            $display("TB_STX43EQ FAIL mismatches %0d checks %0d segments %0d aligned %0d fault_cycles %0d data_cycles %0d",
                     bad, checks, segs, aligned, fault_cycles, data_cycles);
        $finish;
    end
endmodule
