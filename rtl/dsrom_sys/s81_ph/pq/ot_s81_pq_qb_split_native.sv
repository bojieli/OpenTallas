`timescale 1ns/1ps
module ot_s81_pq_qb_head_native (
 input wire clk,rst_n,consume,input wire[9:0] aqi_d,
 input wire[15:0] h_b0,h_b1,input wire[1:0] hw_sv,
 input wire[1023:0] rd_data,input wire[39:0] erd_data,input wire[3:0] bfault,
 output reg[8:0] w0,w1,output reg wv,
 output reg[15:0] i0,i1,output reg[1:0] gates,output reg consume_1,
 output reg[255:0] hq0,hq1,output reg[9:0] he0,he1,output wire fault
);
    wire [0:0] rst_l;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr
        (.clk(clk), .rst_n_in(rst_n), .rst_n(rst_l));
    reg [9:0] aqi;
    always @(posedge clk or negedge rst_l[0]) begin
        if (!rst_l[0]) begin aqi <= 0; w0 <= 0; w1 <= 0; wv <= 0; end
        else begin
            aqi <= aqi_d;
            w0 <= (aqi[0] ? 9'd192 : 9'd0) + {1'b0, aqi[8:1]};
            w1 <= (aqi[0] ? 9'd192 : 9'd0) + {1'b0, aqi[8:1]} + 9'd1;
            wv <= aqi[9];
        end
    end
    always @(posedge clk or negedge rst_l[0])
        if (!rst_l[0]) begin i0 <= 0; i1 <= 0; gates <= 0; consume_1 <= 0; end
        else begin i0 <= h_b0; i1 <= h_b1; gates <= hw_sv; consume_1 <= consume; end
    wire [1:0] bank0 = {i0[3], i0[0]}, bank1 = {i1[3], i1[0]};
    wire [6:0] row0 = {i0[8:4], i0[2:1]}, row1 = {i1[8:4], i1[2:1]};
    wire [255:0] rd [0:3];
    wire [9:0] erd [0:3];
    reg [1:0] selected0, selected1, g2;
    reg fault_pin;
    always @(posedge clk or negedge rst_l[0]) begin
        if (!rst_l[0]) begin selected0 <= 0; selected1 <= 0; g2 <= 0; fault_pin <= 0; end
        else begin selected0 <= bank0; selected1 <= bank1; g2 <= gates & {2{consume_1}}; fault_pin <= |bfault; end
    end
    assign fault = fault_pin;
    always @(posedge clk) begin
        hq0 <= g2[0] ? rd[selected0] : 256'd0;
`ifdef OT_S81_PQ_QB_HEAD_MUT
        // Wrong logical read index: q1 consumes q0's bank as well as its row.
        hq1 <= g2[1] ? rd[selected0] : 256'd0;
`else
        hq1 <= g2[1] ? rd[selected1] : 256'd0;
`endif
        he0 <= g2[0] ? erd[selected0] : 10'd0;
        he1 <= g2[1] ? erd[selected1] : 10'd0;
    end
    generate for(genvar k=0;k<4;k=k+1) begin:g_data
      assign rd[k]=rd_data[256*k +: 256];assign erd[k]=erd_data[10*k +: 10];
    end endgenerate
`ifndef SYNTHESIS
    always @(posedge clk) if(rst_l[0]) begin
      if(consume_1&&gates[0]&&i0>=384) $fatal(1,"QB q0 index beyond production storage");
      if(consume_1&&gates[1]&&i1>=384) $fatal(1,"QB q1 index beyond production storage");
      if(aqi[9]&&(aqi[8:1]>=192||aqi[1])) $fatal(1,"QB write pair outside legal loader protocol");
    end
`endif
endmodule
module ot_s81_pq_qb_bank_native #(parameter integer B=0) (
 input wire clk,rst_n,input wire[8:0] w0,w1,input wire wv,
 input wire[511:0] aq_q,input wire[19:0] aq_e,input wire[9:0] aq_p,
 input wire[15:0] i0,i1,input wire[1:0] gates,input wire consume_1,
 output wire[255:0] rd,output reg[9:0] erd,output wire fault
);
    wire [0:0] rst_l;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr
        (.clk(clk), .rst_n_in(rst_n), .rst_n(rst_l));
    wire[1:0] bank0={i0[3],i0[0]},bank1={i1[3],i1[0]};
    wire[6:0] row0={i0[8:4],i0[2:1]},row1={i1[8:4],i1[2:1]};
        wire a = wv && {w0[3],w0[0]} == 2'(B);
        wire z = wv && {w1[3],w1[0]} == 2'(B);
        wire we = a || z;
        wire [8:0] wi = a ? w0 : w1;
        wire [6:0] wa = {wi[8:4],wi[2:1]};
        wire [255:0] wd = a ? aq_q[255:0] : aq_q[511:256];
        wire [9:0] ew = a ? aq_e[9:0] : aq_e[19:10];
        wire r0 = consume_1 && gates[0] && bank0 == 2'(B);
        wire r1 = consume_1 && gates[1] && bank1 == 2'(B);
        wire re = r0 || r1;
`ifdef OT_S81_PQ_QB_BANK_MUT_K
        wire [6:0] ra = B==`OT_S81_PQ_QB_BANK_MUT_K ? 7'd0 : (r0 ? row0 : row1);
`elsif OT_S81_PQ_QB_MUT_ROW
        wire [6:0] ra = row0;
`else
        wire [6:0] ra = r0 ? row0 : row1;
`endif
`ifdef OT_PQ_BENCH_TELEMETRY
        reg [95:0] rows_read;
        always @(posedge clk or negedge rst_l[0])
            if (!rst_l[0]) rows_read <= 0;
            else if (re && ra < 96) rows_read[ra] <= 1'b1;
`endif
        ot_sram_1r1w_128x256_m1_r2c2 u_mem (
            .clk(clk), .r_ce_in(re), .r_addr_in(ra), .rd_out(rd),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wd), .w_mask_in({256{1'b1}}),
            .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
        reg [9:0] exponent [0:95];
        reg [4:0] parity [0:95];
        reg [95:0] written;
        reg [4:0] expected;
        reg checked, sticky;
`ifdef OT_PQ_AQ_SIDE_PARITY
        wire [4:0] wp = a ? aq_p[4:0] : aq_p[9:5];
`else
        wire [4:0] wp = {^ew, ^wd[255:192], ^wd[191:128], ^wd[127:64], ^wd[63:0]};
`endif
        wire [4:0] rp = {^erd, ^rd[255:192], ^rd[191:128], ^rd[127:64], ^rd[63:0]};
        always @(posedge clk or negedge rst_l[0]) begin
            if (!rst_l[0]) begin written <= 0; checked <= 0; sticky <= 0; end
            else begin
                if (we && wa < 96) begin exponent[wa] <= ew; parity[wa] <= wp; written[wa] <= 1'b1; end
                `ifdef OT_S81_PQ_QB_BANK_MUT_K
                if (re && ra < 96) begin erd <= exponent[ra]; expected <= parity[ra]; end
`elsif OT_S81_PQ_QB_MUT_ROW
                if (re && ra < 96) begin erd <= exponent[ra]; expected <= parity[ra]; end
`else
                // Select the original two row values after local metadata reads.
                // This removes bank-selection decode from the address-mux tree,
                // while preserving the exact selected row and capture edge.
                if (re && (r0 ? row0 < 96 : row1 < 96)) begin erd <= r0 ? exponent[row0] : exponent[row1]; expected <= r0 ? parity[row0] : parity[row1]; end
`endif
                checked <= re && (r0 ? (row0 < 96 && written[row0]) : (row1 < 96 && written[row1]));
                if (checked && expected != rp) sticky <= 1'b1;
                if (re && (r0 ? (row0 >= 96 || !written[row0]) : (row1 >= 96 || !written[row1]))) sticky <= 1'b1;
            end
        end
        assign fault = sticky;
`ifndef SYNTHESIS
        always @(posedge clk) if (rst_l[0]) begin
            if (we && wa >= 96) $fatal(1, "QB write beyond production storage");
            if (a && z) $fatal(1, "QB writes collide in one bank");
            if (r0 && r1) $fatal(1, "QB reads collide in one bank");
            if (re && (ra >= 96 || !written[ra])) $fatal(1, "QB read before loaded");
            if (we && re && wa == ra) $fatal(1, "QB read during write violates have protocol");
        end
`endif
endmodule
// Fixed physical master B=0; complete wire identity, no state or epoch added.
module ot_s81_pq_qb_bank0_native (
 input wire clk,rst_n,input wire[8:0] w0,w1,input wire wv,
 input wire[511:0] aq_q,input wire[19:0] aq_e,input wire[9:0] aq_p,
 input wire[15:0] i0,i1,input wire[1:0] gates,input wire consume_1,
 output wire[255:0] rd,output wire[9:0] erd,output wire fault
);
 ot_s81_pq_qb_bank_native #(.B(0)) u_native (.clk(clk),.rst_n(rst_n),.w0(w0),.w1(w1),.wv(wv),.aq_q(aq_q),.aq_e(aq_e),.aq_p(aq_p),.i0(i0),.i1(i1),.gates(gates),.consume_1(consume_1),.rd(rd),.erd(erd),.fault(fault));
endmodule

// Fixed physical master B=1; complete wire identity, no state or epoch added.
module ot_s81_pq_qb_bank1_native (
 input wire clk,rst_n,input wire[8:0] w0,w1,input wire wv,
 input wire[511:0] aq_q,input wire[19:0] aq_e,input wire[9:0] aq_p,
 input wire[15:0] i0,i1,input wire[1:0] gates,input wire consume_1,
 output wire[255:0] rd,output wire[9:0] erd,output wire fault
);
 ot_s81_pq_qb_bank_native #(.B(1)) u_native (.clk(clk),.rst_n(rst_n),.w0(w0),.w1(w1),.wv(wv),.aq_q(aq_q),.aq_e(aq_e),.aq_p(aq_p),.i0(i0),.i1(i1),.gates(gates),.consume_1(consume_1),.rd(rd),.erd(erd),.fault(fault));
endmodule

// Fixed physical master B=2; complete wire identity, no state or epoch added.
module ot_s81_pq_qb_bank2_native (
 input wire clk,rst_n,input wire[8:0] w0,w1,input wire wv,
 input wire[511:0] aq_q,input wire[19:0] aq_e,input wire[9:0] aq_p,
 input wire[15:0] i0,i1,input wire[1:0] gates,input wire consume_1,
 output wire[255:0] rd,output wire[9:0] erd,output wire fault
);
 ot_s81_pq_qb_bank_native #(.B(2)) u_native (.clk(clk),.rst_n(rst_n),.w0(w0),.w1(w1),.wv(wv),.aq_q(aq_q),.aq_e(aq_e),.aq_p(aq_p),.i0(i0),.i1(i1),.gates(gates),.consume_1(consume_1),.rd(rd),.erd(erd),.fault(fault));
endmodule

// Fixed physical master B=3; complete wire identity, no state or epoch added.
module ot_s81_pq_qb_bank3_native (
 input wire clk,rst_n,input wire[8:0] w0,w1,input wire wv,
 input wire[511:0] aq_q,input wire[19:0] aq_e,input wire[9:0] aq_p,
 input wire[15:0] i0,i1,input wire[1:0] gates,input wire consume_1,
 output wire[255:0] rd,output wire[9:0] erd,output wire fault
);
 ot_s81_pq_qb_bank_native #(.B(3)) u_native (.clk(clk),.rst_n(rst_n),.w0(w0),.w1(w1),.wv(wv),.aq_q(aq_q),.aq_e(aq_e),.aq_p(aq_p),.i0(i0),.i1(i1),.gates(gates),.consume_1(consume_1),.rd(rd),.erd(erd),.fault(fault));
endmodule

module ot_s81_pq_qb_split_native (
 input wire clk,rst_n,consume,input wire[3:0] clk_bank,
 input wire[9:0] aqi_d,input wire[511:0] aq_q,input wire[19:0] aq_e,input wire[9:0] aq_p,
 input wire[15:0] h_b0,h_b1,input wire[1:0] hw_sv,
 output wire[255:0] hq0,hq1,output wire[9:0] he0,he1,output wire fault
);
 wire[1023:0] rd;wire[39:0] erd;wire[3:0] bfault;
 wire[8:0] w0,w1;wire wv;wire[15:0] i0,i1;wire[1:0] gates;wire consume_1;
 ot_s81_pq_qb_head_native u_head (.clk(clk),.rst_n(rst_n),.consume(consume),.aqi_d(aqi_d),
   .h_b0(h_b0),.h_b1(h_b1),.hw_sv(hw_sv),.rd_data(rd),.erd_data(erd),.bfault(bfault),
   .w0(w0),.w1(w1),.wv(wv),.i0(i0),.i1(i1),.gates(gates),.consume_1(consume_1),
   .hq0(hq0),.hq1(hq1),.he0(he0),.he1(he1),.fault(fault));
 ot_s81_pq_qb_bank0_native u_bank0 (.clk(clk_bank[0]),.rst_n(rst_n),.w0(w0),.w1(w1),.wv(wv),
     .aq_q(aq_q),.aq_e(aq_e),.aq_p(aq_p),.i0(i0),.i1(i1),.gates(gates),.consume_1(consume_1),
     .rd(rd[0 +: 256]),.erd(erd[0 +: 10]),.fault(bfault[0]));
 ot_s81_pq_qb_bank1_native u_bank1 (.clk(clk_bank[1]),.rst_n(rst_n),.w0(w0),.w1(w1),.wv(wv),
     .aq_q(aq_q),.aq_e(aq_e),.aq_p(aq_p),.i0(i0),.i1(i1),.gates(gates),.consume_1(consume_1),
     .rd(rd[256 +: 256]),.erd(erd[10 +: 10]),.fault(bfault[1]));
 ot_s81_pq_qb_bank2_native u_bank2 (.clk(clk_bank[2]),.rst_n(rst_n),.w0(w0),.w1(w1),.wv(wv),
     .aq_q(aq_q),.aq_e(aq_e),.aq_p(aq_p),.i0(i0),.i1(i1),.gates(gates),.consume_1(consume_1),
     .rd(rd[512 +: 256]),.erd(erd[20 +: 10]),.fault(bfault[2]));
 ot_s81_pq_qb_bank3_native u_bank3 (.clk(clk_bank[3]),.rst_n(rst_n),.w0(w0),.w1(w1),.wv(wv),
     .aq_q(aq_q),.aq_e(aq_e),.aq_p(aq_p),.i0(i0),.i1(i1),.gates(gates),.consume_1(consume_1),
     .rd(rd[768 +: 256]),.erd(erd[30 +: 10]),.fault(bfault[3]));
endmodule
