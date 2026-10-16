`define OT_QFD_VM_PARTITIONED_CLOCKS
module gold(input wire clk,rst_n,input wire[239:0]write_ck,input wire[0:0]gm,input wire[19:0]f_r0,input wire[79:0]f_m,input wire[2559:0]f_d,input wire[191:0]su_k,input wire[63:0]su_hit,input wire[15:0]su_hs,input wire[19:0]m_row,input wire[15:0]m_mb,input wire[511:0]m_data,input wire[5:0]pl_w,input wire[119:0]pl_row,input wire[95:0]pl_mb,input wire[3071:0]pl_data,input wire[3:0]ge,input wire[79:0]qrows,input wire[63:0]qmasks,input wire[2047:0]qdatas,output wire[63:0]o_bw_we,output wire[511:0]o_bw_line,output wire[1023:0]o_bw_mask,output wire[32767:0]o_bw_data,output wire[191:0]o_bw_src,output wire[15:0]o_ws_we,output wire[159:0]o_ws_line,output wire[255:0]o_ws_mask,output wire[8191:0]o_ws_data);
localparam NRB=64,NRBS=16,LAW=8,LAWS=10,RW=20,LNRB=6,LNRBS=4,NB=6,NQ=4,SQD=1,PAR_RB=1,WRITE_LEAVES=0,WRITE_CLOCKS=1;
genvar g;
wire[19:0]q_row[0:3];wire[15:0]q_mask[0:3];wire[511:0]q_data[0:3];
genvar z; generate for(z=0;z<4;z=z+1)begin assign q_row[z]=qrows[z*20+:20];assign q_mask[z]=qmasks[z*16+:16];assign q_data[z]=qdatas[z*512+:512];end endgenerate
    reg  [NRB-1:0]      bw_we;
    reg  [NRB*LAW-1:0]  bw_line;
    reg  [NRB*16-1:0]   bw_mask;
    reg  [NRB*512-1:0]  bw_data;
    reg  [NRB*3-1:0]    bw_src;
    generate for (g = 0; g < NRB; g = g + 1) begin : g_bw
        wire [2:0] kk = su_k[g*3 +: 3];
        wire [RW-1:0] srow = f_r0 + kk;
        reg  [2:0] src;          // 0 none, 1 su, 2 mx, 3 rd, 4 seq, 5 merge
        // the one granted skid entry of this bank (grants are distinct mod NRBS, so distinct mod NRB): AND-OR select
        reg  [2:0]    es;
        reg  [RW-1:0] er;
        reg  [15:0]   em;
        reg  [511:0]  ed;
        // PAR_RB: the lane row of this bank (lanes are distinct mod NRBS, so at most one matches): AND-OR select
        reg  [NB-1:0] lh;
        reg  [RW-1:0] lr;
        reg  [15:0]   lm;
        reg  [511:0]  ld;
        integer li;
        always @(*) begin
            lh = 0; lr = m_row; lm = m_mb; ld = m_data;
            if (PAR_RB != 0) begin
                lr = 0; lm = 0; ld = 0;
                for (li = 0; li < NB; li = li + 1) if (pl_w[li] && pl_row[RW*li +: LNRB] == g) begin
                    lh[li] = 1'b1; lr = lr | pl_row[RW*li +: RW]; lm = lm | pl_mb[16*li +: 16]; ld = ld | pl_data[512*li +: 512];
                end
            end
        end
        integer ee;
        always @(*) begin
            es = 3'd0; er = {RW{1'b0}}; em = 16'd0; ed = 512'd0;
            for (ee = 0; ee < NQ; ee = ee + 1)
                if (ge[ee] && q_row[ee][LNRB-1:0] == g) begin
                    es = es | ((ee / SQD == 3) ? 6 : ee / SQD + 2); er = er | q_row[ee]; em = em | q_mask[ee]; ed = ed | q_data[ee];
                end
            src = 3'd0;
            if (su_hit[g]) src = 3'd1;
            else if (es != 3'd0) src = es;
            else if (gm && m_row[LNRB-1:0] == g) src = 3'd5;
            else if (|lh) src = 3'd5;
        end
        always @(posedge clk or negedge rst_n) if (!rst_n) bw_we[g] <= 1'b0; else bw_we[g] <= (src != 0);
        always @(posedge clk) begin
            bw_src[g*3 +: 3] <= src;
            case (src)
                3'd1: begin bw_line[g*LAW +: LAW] <= srow[LNRB +: LAW]; bw_mask[g*16 +: 16] <= f_m[kk*16 +: 16];
                            bw_data[g*512 +: 512] <= f_d[kk*512 +: 512]; end
                3'd2, 3'd3, 3'd4, 3'd6: begin bw_line[g*LAW +: LAW] <= er[LNRB +: LAW]; bw_mask[g*16 +: 16] <= em;
                            bw_data[g*512 +: 512] <= ed; end
                default: begin bw_line[g*LAW +: LAW] <= lr[LNRB +: LAW]; bw_mask[g*16 +: 16] <= lm;
                            bw_data[g*512 +: 512] <= ld; end
            endcase
        end
    end endgenerate
    // per-bank write registers of the SU replica copies (NRBS banks, beside them)
    reg  [NRBS-1:0]      ws_we;
    reg  [NRBS*LAWS-1:0] ws_line;
    reg  [NRBS*16-1:0]   ws_mask;
    reg  [NRBS*512-1:0]  ws_data;
    generate for (g = 0; g < NRBS; g = g + 1) begin : g_ws
        wire [LNRBS-1:0] kk = g[LNRBS-1:0] - f_r0[LNRBS-1:0];
        wire [RW-1:0] srow = f_r0 + kk;
        reg  [2:0] src;
        reg           es;
        reg  [RW-1:0] er;
        reg  [15:0]   em;
        reg  [511:0]  ed;
        reg  [NB-1:0] lh;
        reg  [RW-1:0] lr;
        reg  [15:0]   lm;
        reg  [511:0]  ld;
        integer li;
        always @(*) begin
            lh = 0; lr = m_row; lm = m_mb; ld = m_data;
            if (PAR_RB != 0) begin
                lr = 0; lm = 0; ld = 0;
                for (li = 0; li < NB; li = li + 1) if (pl_w[li] && pl_row[RW*li +: LNRBS] == g) begin
                    lh[li] = 1'b1; lr = lr | pl_row[RW*li +: RW]; lm = lm | pl_mb[16*li +: 16]; ld = ld | pl_data[512*li +: 512];
                end
            end
        end
        integer ee;
        always @(*) begin
            es = 1'b0; er = {RW{1'b0}}; em = 16'd0; ed = 512'd0;
            for (ee = 0; ee < NQ; ee = ee + 1)
                if (ge[ee] && q_row[ee][LNRBS-1:0] == g) begin
                    es = 1'b1; er = er | q_row[ee]; em = em | q_mask[ee]; ed = ed | q_data[ee];
                end
            src = 3'd0;
            if (su_hs[g]) src = 3'd1;
            else if (es) src = 3'd2;
            else if (gm && m_row[LNRBS-1:0] == g) src = 3'd5;
            else if (|lh) src = 3'd5;
        end
        always @(posedge clk or negedge rst_n) if (!rst_n) ws_we[g] <= 1'b0; else ws_we[g] <= (src != 0);
        always @(posedge clk) begin
            case (src)
                3'd1: begin ws_line[g*LAWS +: LAWS] <= srow[LNRBS +: LAWS]; ws_mask[g*16 +: 16] <= f_m[kk*16 +: 16];
                            ws_data[g*512 +: 512] <= f_d[kk*512 +: 512]; end
                3'd2: begin ws_line[g*LAWS +: LAWS] <= er[LNRBS +: LAWS]; ws_mask[g*16 +: 16] <= em;
                            ws_data[g*512 +: 512] <= ed; end
                default: begin ws_line[g*LAWS +: LAWS] <= lr[LNRBS +: LAWS]; ws_mask[g*16 +: 16] <= lm;
                            ws_data[g*512 +: 512] <= ld; end
            endcase
        end
    end endgenerate

assign o_bw_we=bw_we;
assign o_bw_line=bw_line;
assign o_bw_mask=bw_mask;
assign o_bw_data=bw_data;
assign o_bw_src=bw_src;
assign o_ws_we=ws_we;
assign o_ws_line=ws_line;
assign o_ws_mask=ws_mask;
assign o_ws_data=ws_data;
endmodule
module dut(input wire clk,rst_n,input wire[239:0]write_ck,input wire[0:0]gm,input wire[19:0]f_r0,input wire[79:0]f_m,input wire[2559:0]f_d,input wire[191:0]su_k,input wire[63:0]su_hit,input wire[15:0]su_hs,input wire[19:0]m_row,input wire[15:0]m_mb,input wire[511:0]m_data,input wire[5:0]pl_w,input wire[119:0]pl_row,input wire[95:0]pl_mb,input wire[3071:0]pl_data,input wire[3:0]ge,input wire[79:0]qrows,input wire[63:0]qmasks,input wire[2047:0]qdatas,output wire[63:0]o_bw_we,output wire[511:0]o_bw_line,output wire[1023:0]o_bw_mask,output wire[32767:0]o_bw_data,output wire[191:0]o_bw_src,output wire[15:0]o_ws_we,output wire[159:0]o_ws_line,output wire[255:0]o_ws_mask,output wire[8191:0]o_ws_data);
localparam NRB=64,NRBS=16,LAW=8,LAWS=10,RW=20,LNRB=6,LNRBS=4,NB=6,NQ=4,SQD=1,PAR_RB=1,WRITE_LEAVES=1,WRITE_CLOCKS=1;
genvar g;
wire[19:0]q_row[0:3];wire[15:0]q_mask[0:3];wire[511:0]q_data[0:3];
genvar z; generate for(z=0;z<4;z=z+1)begin assign q_row[z]=qrows[z*20+:20];assign q_mask[z]=qmasks[z*16+:16];assign q_data[z]=qdatas[z*512+:512];end endgenerate
    reg  [NRB-1:0]      bw_we;
    reg  [NRB*LAW-1:0]  bw_line;
    reg  [NRB*16-1:0]   bw_mask;
    reg  [NRB*512-1:0]  bw_data;
    reg  [NRB*3-1:0]    bw_src;
    generate for (g = 0; g < NRB; g = g + 1) begin : g_bw
        wire [2:0] kk = su_k[g*3 +: 3];
        wire [RW-1:0] srow = f_r0 + kk;
        reg  [2:0] src;          // 0 none, 1 su, 2 mx, 3 rd, 4 seq, 5 merge
        // the one granted skid entry of this bank (grants are distinct mod NRBS, so distinct mod NRB): AND-OR select
        reg  [2:0]    es;
        reg  [RW-1:0] er;
        reg  [15:0]   em;
        reg  [511:0]  ed;
        // PAR_RB: the lane row of this bank (lanes are distinct mod NRBS, so at most one matches): AND-OR select
        reg  [NB-1:0] lh;
        reg  [RW-1:0] lr;
        reg  [15:0]   lm;
        reg  [511:0]  ld;
        integer li;
        always @(*) begin
            lh = 0; lr = m_row; lm = m_mb; ld = m_data;
            if (PAR_RB != 0) begin
                lr = 0; lm = 0; ld = 0;
                for (li = 0; li < NB; li = li + 1) if (pl_w[li] && pl_row[RW*li +: LNRB] == g) begin
                    lh[li] = 1'b1; lr = lr | pl_row[RW*li +: RW]; lm = lm | pl_mb[16*li +: 16]; ld = ld | pl_data[512*li +: 512];
                end
            end
        end
        integer ee;
        always @(*) begin
            es = 3'd0; er = {RW{1'b0}}; em = 16'd0; ed = 512'd0;
            for (ee = 0; ee < NQ; ee = ee + 1)
                if (ge[ee] && q_row[ee][LNRB-1:0] == g) begin
                    es = es | ((ee / SQD == 3) ? 6 : ee / SQD + 2); er = er | q_row[ee]; em = em | q_mask[ee]; ed = ed | q_data[ee];
                end
            src = 3'd0;
            if (su_hit[g]) src = 3'd1;
            else if (es != 3'd0) src = es;
            else if (gm && m_row[LNRB-1:0] == g) src = 3'd5;
            else if (|lh) src = 3'd5;
        end
        if (WRITE_LEAVES != 0) begin : g_write_leaf
            reg [LAW-1:0] next_line;
            reg [15:0] next_mask;
            reg [511:0] next_data;
            always @* begin
            case (src)
                3'd1: begin next_line = srow[LNRB +: LAW]; next_mask = f_m[kk*16 +: 16];
                            next_data = f_d[kk*512 +: 512]; end
                3'd2, 3'd3, 3'd4, 3'd6: begin next_line = er[LNRB +: LAW]; next_mask = em;
                            next_data = ed; end
                default: begin next_line = lr[LNRB +: LAW]; next_mask = lm;
                            next_data = ld; end
            endcase
            end
            wire [2:0] owned_ck;
`ifdef OT_QFD_VM_PARTITIONED_CLOCKS
            assign owned_ck = (WRITE_CLOCKS != 0) ? write_ck[(g)*3 +: 3] : {3{clk}};
`else
            assign owned_ck = {3{clk}};
            initial if (WRITE_CLOCKS != 0) $fatal(1,"WRITE_CLOCKS requires PARTITIONED_CLOCKS");
`endif
            ot_qfd_vm_write_register_t #(.CW(LAW+19)) u_write (
                .ck(owned_ck),.rst_n(rst_n),.we(src != 0),.data(next_data),.ctrl({src,next_line,next_mask}),
                .qwe(bw_we[g]),.qdata(bw_data[g*512 +: 512]),.qctrl({bw_src[g*3 +: 3],bw_line[g*LAW +: LAW],bw_mask[g*16 +: 16]}));
        end else begin : g_original
        always @(posedge clk or negedge rst_n) if (!rst_n) bw_we[g] <= 1'b0; else bw_we[g] <= (src != 0);
        always @(posedge clk) begin
            bw_src[g*3 +: 3] <= src;
            case (src)
                3'd1: begin bw_line[g*LAW +: LAW] <= srow[LNRB +: LAW]; bw_mask[g*16 +: 16] <= f_m[kk*16 +: 16];
                            bw_data[g*512 +: 512] <= f_d[kk*512 +: 512]; end
                3'd2, 3'd3, 3'd4, 3'd6: begin bw_line[g*LAW +: LAW] <= er[LNRB +: LAW]; bw_mask[g*16 +: 16] <= em;
                            bw_data[g*512 +: 512] <= ed; end
                default: begin bw_line[g*LAW +: LAW] <= lr[LNRB +: LAW]; bw_mask[g*16 +: 16] <= lm;
                            bw_data[g*512 +: 512] <= ld; end
            endcase
        end
        end
    end endgenerate
    // per-bank write registers of the SU replica copies (NRBS banks, beside them)
    reg  [NRBS-1:0]      ws_we;
    reg  [NRBS*LAWS-1:0] ws_line;
    reg  [NRBS*16-1:0]   ws_mask;
    reg  [NRBS*512-1:0]  ws_data;
    generate for (g = 0; g < NRBS; g = g + 1) begin : g_ws
        wire [LNRBS-1:0] kk = g[LNRBS-1:0] - f_r0[LNRBS-1:0];
        wire [RW-1:0] srow = f_r0 + kk;
        reg  [2:0] src;
        reg           es;
        reg  [RW-1:0] er;
        reg  [15:0]   em;
        reg  [511:0]  ed;
        reg  [NB-1:0] lh;
        reg  [RW-1:0] lr;
        reg  [15:0]   lm;
        reg  [511:0]  ld;
        integer li;
        always @(*) begin
            lh = 0; lr = m_row; lm = m_mb; ld = m_data;
            if (PAR_RB != 0) begin
                lr = 0; lm = 0; ld = 0;
                for (li = 0; li < NB; li = li + 1) if (pl_w[li] && pl_row[RW*li +: LNRBS] == g) begin
                    lh[li] = 1'b1; lr = lr | pl_row[RW*li +: RW]; lm = lm | pl_mb[16*li +: 16]; ld = ld | pl_data[512*li +: 512];
                end
            end
        end
        integer ee;
        always @(*) begin
            es = 1'b0; er = {RW{1'b0}}; em = 16'd0; ed = 512'd0;
            for (ee = 0; ee < NQ; ee = ee + 1)
                if (ge[ee] && q_row[ee][LNRBS-1:0] == g) begin
                    es = 1'b1; er = er | q_row[ee]; em = em | q_mask[ee]; ed = ed | q_data[ee];
                end
            src = 3'd0;
            if (su_hs[g]) src = 3'd1;
            else if (es) src = 3'd2;
            else if (gm && m_row[LNRBS-1:0] == g) src = 3'd5;
            else if (|lh) src = 3'd5;
        end
        if (WRITE_LEAVES != 0) begin : g_write_leaf
            reg [LAWS-1:0] next_line;
            reg [15:0] next_mask;
            reg [511:0] next_data;
            always @* begin
            case (src)
                3'd1: begin next_line = srow[LNRBS +: LAWS]; next_mask = f_m[kk*16 +: 16];
                            next_data = f_d[kk*512 +: 512]; end
                3'd2: begin next_line = er[LNRBS +: LAWS]; next_mask = em;
                            next_data = ed; end
                default: begin next_line = lr[LNRBS +: LAWS]; next_mask = lm;
                            next_data = ld; end
            endcase
            end
            wire [2:0] owned_ck;
`ifdef OT_QFD_VM_PARTITIONED_CLOCKS
            assign owned_ck = (WRITE_CLOCKS != 0) ? write_ck[(NRB+g)*3 +: 3] : {3{clk}};
`else
            assign owned_ck = {3{clk}};
            initial if (WRITE_CLOCKS != 0) $fatal(1,"WRITE_CLOCKS requires PARTITIONED_CLOCKS");
`endif
            ot_qfd_vm_write_register_t #(.CW(LAWS+16)) u_write (
                .ck(owned_ck),.rst_n(rst_n),.we(src != 0),.data(next_data),.ctrl({next_line,next_mask}),
                .qwe(ws_we[g]),.qdata(ws_data[g*512 +: 512]),.qctrl({ws_line[g*LAWS +: LAWS],ws_mask[g*16 +: 16]}));
        end else begin : g_original
        always @(posedge clk or negedge rst_n) if (!rst_n) ws_we[g] <= 1'b0; else ws_we[g] <= (src != 0);
        always @(posedge clk) begin
            case (src)
                3'd1: begin ws_line[g*LAWS +: LAWS] <= srow[LNRBS +: LAWS]; ws_mask[g*16 +: 16] <= f_m[kk*16 +: 16];
                            ws_data[g*512 +: 512] <= f_d[kk*512 +: 512]; end
                3'd2: begin ws_line[g*LAWS +: LAWS] <= er[LNRBS +: LAWS]; ws_mask[g*16 +: 16] <= em;
                            ws_data[g*512 +: 512] <= ed; end
                default: begin ws_line[g*LAWS +: LAWS] <= lr[LNRBS +: LAWS]; ws_mask[g*16 +: 16] <= lm;
                            ws_data[g*512 +: 512] <= ld; end
            endcase
        end
        end
    end endgenerate

assign o_bw_we=bw_we;
assign o_bw_line=bw_line;
assign o_bw_mask=bw_mask;
assign o_bw_data=bw_data;
assign o_bw_src=bw_src;
assign o_ws_we=ws_we;
assign o_ws_line=ws_line;
assign o_ws_mask=ws_mask;
assign o_ws_data=ws_data;
endmodule
module ot_qfd_vm_write_register_t #(parameter integer CW=27)(
 input wire [2:0] ck,input wire rst_n,we,input wire [511:0] data,
 input wire [CW-1:0] ctrl,output wire qwe,output wire [511:0] qdata,
 output wire [CW-1:0] qctrl);
 qvm_data256_native u_lo(.clk(ck[0]),.d(data[255:0]),.q(qdata[255:0]));
 qvm_data256_native u_hi(.clk(ck[1]),.d(data[511:256]),.q(qdata[511:256]));
 ot_qfd_vm_write_control_t #(.W(CW)) u_control(.clk(ck[2]),.rst_n(rst_n),
     .we(we),.d(ctrl),.qwe(qwe),.q(qctrl));
endmodule
module ot_qfd_vm_write_control_t #(parameter integer W=27)(
 input wire clk,rst_n,we,input wire [W-1:0] d,
 output reg qwe,output reg [W-1:0] q);
 always @(posedge clk or negedge rst_n) if(!rst_n) qwe<=1'b0;else qwe<=we;
 always @(posedge clk) q<=d;
endmodule
module qvm_data256_native(input wire clk,input wire[255:0]d,output reg[255:0]q);
 always @(posedge clk)q<=d;
endmodule
