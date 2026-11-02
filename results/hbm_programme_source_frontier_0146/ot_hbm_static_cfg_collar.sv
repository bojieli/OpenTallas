module ot_hbm_static_cfg_collar #(
    parameter integer PAGE_W=12,    
    parameter integer NS=2,         
    parameter integer NPR=1,        
    parameter integer NREC=0,       
    parameter integer NGO=1,        
    parameter integer NB=2,         
    parameter integer NF=1,         
    parameter integer TAIL=4,
    parameter integer XSER=0,       
    parameter integer MUT=0,        
                                    
                                    
     
     
    parameter integer SPARSE_SU=0,
    parameter [319:0] SU_DICT_CAP={32'd1,32'd1,32'd1,32'd1,32'd1,32'd2,32'd13,32'd9,32'd10,32'd3},
    parameter integer AW=PAGE_W+11
)(
    input  wire clk, clk_in, rst_n,
    input  wire [7:0] tgt,
    input  wire cfg_v,
    input  wire [7:0] cfg_target,
    input  wire [11:0] cfg_addr,
    input  wire [255:0] cfg_data,
    input  wire desc_v,
    input  wire launch_v,
    input  wire [NB-1:0] c_busy,
    input  wire c_done,
    input  wire [NF-1:0] c_fault,
    output reg  [NS-1:0] pw_we,
    output reg  [AW-1:0] pw_addr,
    output reg  [255:0] pw_data,
    output reg  [NPR*256-1:0] prm,
    output reg  start_v,
    output reg  [NGO-1:0] go,
    output reg  [220:0] rec,
    output reg  ready, active, fault
);
    initial begin
        if (NS<1 || NS>4 || NPR<1 || NPR>1024 || NREC<0 || NREC>512 || NGO<1 || NGO>2 || PAGE_W<1 || AW>31)
            $fatal(1, "ot_hbm_static_cfg_collar: parameter out of range");
    end
    initial if (SPARSE_SU && (NS!=1 || PAGE_W!=12))
        $fatal(1, "SPARSE_SU requires the frozen SU bank16/row7 interface");
     
    function automatic su_bank_valid(input [15:0] bank);
        integer part, local_bank, column, cap;
        begin
            su_bank_valid=0;
            for(part=0;part<4;part=part+1) begin
                if(bank>=part*320 && bank<(part+1)*320) begin
                    local_bank=bank-part*320; column=local_bank/32;
                    cap=SU_DICT_CAP[32*column+:32];
                    su_bank_valid=(local_bank%32)<(4+((cap<=3)?3:13));
                end
            end
        end
    endfunction
    localparam integer SW = (NS>1) ? $clog2(NS) : 1;
    localparam integer RN = (NREC>0) ? NREC : 1;
    localparam integer RW = (NREC>1) ? $clog2(NREC+1) : 1;
     
     
     
     
     
     
     
     
     
     
     
     
     
     
    wire rst_c_n, rst_s_n;
    generate if (XSER == 0) begin : g_rst_same
        reg [1:0] rc;
        always @(posedge clk) rc <= {rc[0], rst_n};
        if (MUT == 8) begin : g_mut8    
            reg por_done = 1'b0;
            always @(posedge clk) if (rc[1] === 1'b1) por_done <= 1'b1;
            assign rst_c_n = rc[1] | por_done;
        end else begin : g_rc
            assign rst_c_n = rc[1];
        end
        assign rst_s_n = rc[1];
    end else begin : g_rst_sync
        reg [1:0] rc, rs;
        always @(posedge clk)    rc <= {rc[0], rst_n};
        always @(posedge clk_in) rs <= {rs[0], rc[1]};
        assign rst_c_n = rc[1];
        assign rst_s_n = (MUT == 5) ? 1'b1 : rs[1];
    end endgenerate
     
    reg cv, dv, lv, done_q, xfault;
    reg [7:0] ct, tg;
    reg [11:0] ca;
    reg [255:0] cd;
    reg [NB-1:0] busy_q;
    reg [NF-1:0] cf_q;
    always @(posedge clk) tg <= tgt;
    always @(posedge clk or negedge rst_c_n)
        if (!rst_c_n) begin done_q <= 0; busy_q <= 0; cf_q <= 0; end
        else begin done_q <= c_done; busy_q <= c_busy; cf_q <= c_fault; end
    generate if (XSER == 0) begin : g_same
         
        always @(posedge clk) begin ct <= cfg_target; ca <= cfg_addr; cd <= cfg_data; end
        always @(posedge clk or negedge rst_s_n)
            if (!rst_s_n) begin cv <= 0; dv <= 0; lv <= 0; xfault <= 0; end
            else begin cv <= cfg_v; dv <= desc_v; lv <= launch_v; xfault <= 0; end
    end else begin : g_xser
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
         
        reg pv_cv, pv_dv, pv_lv; reg [7:0] p_ct; reg [11:0] p_ca; reg [255:0] p_cd;
        reg [1:0] h_seq; reg h_cv, h_dv, h_lv; reg [7:0] h_ct; reg [11:0] h_ca; reg [255:0] h_cd;
        always @(posedge clk_in) begin p_ct <= cfg_target; p_ca <= cfg_addr; p_cd <= cfg_data; end
        always @(posedge clk_in or negedge rst_s_n)
            if (!rst_s_n) begin pv_cv <= 0; pv_dv <= 0; pv_lv <= 0; h_seq <= 0; h_cv <= 0; h_dv <= 0; h_lv <= 0; end
            else begin
                pv_cv <= cfg_v; pv_dv <= desc_v; pv_lv <= launch_v;
                if (pv_cv || pv_dv || pv_lv) begin
                     
                    h_seq <= (MUT == 6) ? h_seq + 1'b1 : {h_seq[0], ~h_seq[1]};
                    h_cv <= pv_cv; h_dv <= pv_dv; h_lv <= pv_lv;
                end
            end
         
         
         
        always @(posedge clk_in)
            if (pv_cv || pv_dv || pv_lv) begin h_ct <= p_ct; h_ca <= p_ca; h_cd <= p_cd; end
        reg [1:0] x1_seq, x2_seq, x3_seq;
        always @(posedge clk or negedge rst_c_n)
            if (!rst_c_n) begin x1_seq <= 0; x2_seq <= 0; x3_seq <= 0; end
            else begin x1_seq <= h_seq; x2_seq <= x1_seq; x3_seq <= x2_seq; end
         
        wire [1:0] q_new = (MUT == 7) ? x1_seq : x2_seq;
        wire [1:0] q_old = (MUT == 7) ? x2_seq : x3_seq;
        wire ev = q_new != q_old;
        wire [1:0] b_new = {q_new[1], q_new[1] ^ q_new[0]}, b_old = {q_old[1], q_old[1] ^ q_old[0]};
        always @(posedge clk) if (ev) begin ct <= h_ct; ca <= h_ca; cd <= h_cd; end
        always @(posedge clk or negedge rst_c_n)
            if (!rst_c_n) begin cv <= 0; dv <= 0; lv <= 0; xfault <= 0; end
            else begin
                cv <= ev && h_cv; dv <= ev && h_dv; lv <= ev && h_lv;
                xfault <= ev && (b_new - b_old) != 2'd1 && MUT != 4;
            end
    end endgenerate
     
    reg [SW-1:0] sel;
    reg [PAGE_W-1:0] page [0:NS-1];
    reg [AW:0] hwm [0:NS-1];
    reg [AW:0] need [0:NS-1];
    reg [AW-1:0] sparse_last;
    reg sparse_seen;
    wire [22:0] sparse_linear=23'(lin), sparse_previous=23'(sparse_last);
    wire sparse_address_ok=su_bank_valid(sparse_linear[22:7]) &&
        ((lin==0) || (sparse_seen && lin>sparse_last &&
          ((sparse_linear[22:7]==sparse_previous[22:7] && {1'b0,lin[6:0]}=={1'b0,sparse_last[6:0]}+8'd1) ||
           (sparse_linear[22:7]>sparse_previous[22:7] && lin[6:0]==0))));
    reg need_set, wait_mask, wait_done;
    reg [NPR-1:0] loaded;
    reg armed, run;
    reg [31:0] cnt;
    reg [RW-1:0] rptr;
    reg [7:0] tail;
    reg [31:0] r_off [0:RN-1];
    reg [RN-1:0] r_val;
    reg [1:0] r_go [0:RN-1];
    reg [220:0] r_pay [0:RN-1];
    wire hit = cv && ct == tg;
    wire dhit = dv && ct == tg;
    wire [AW:0] lin = {1'b0, page[sel], ca[10:0]};
    reg inst_ok;
    integer s;
    always @* begin
        inst_ok = need_set && (&loaded);
        if (SPARSE_SU && (!sparse_seen || need[0]==0)) inst_ok = 0;
        for (s = 0; s < NS; s = s + 1) if ((SPARSE_SU ? (hwm[s] != need[s]) : (hwm[s] < need[s])) && MUT != 2) inst_ok = 0;
    end
    wire recs_done = (NREC == 0) || (rptr >= NREC) || !r_val[rptr];
    wire [31:0] cur_off = r_off[(NREC == 0) ? 0 : rptr];
    wire [31:0] cmp_cnt = (MUT == 3) ? cnt + 1 : cnt;
    integer k;
    always @(posedge clk or negedge rst_c_n) begin
        if (!rst_c_n) begin
            pw_we <= 0; start_v <= 0; go <= 0; ready <= 0; active <= 0; fault <= 0;
            sel <= 0; need_set <= 0; wait_mask <= 0; wait_done <= 0; loaded <= 0; armed <= 0; run <= 0;
            cnt <= 0; rptr <= 0; tail <= 0; r_val <= 0; sparse_last <= 0; sparse_seen <= 0;
            for (k = 0; k < NS; k = k + 1) begin hwm[k] <= 0; need[k] <= 0; page[k] <= 0; end
        end else begin
            pw_we <= 0; start_v <= 0; go <= 0;
            if (|cf_q || xfault) fault <= 1;
             
            if (hit) begin
                armed <= 0;
                if (run) fault <= 1;
                else if (!ca[11]) begin
                    if (SPARSE_SU) begin
                        if (!sparse_address_ok || hwm[sel][AW]) fault <= 1;
                        else begin
                            pw_we[sel] <= 1; pw_addr <= lin[AW-1:0]; pw_data <= cd;
                            sparse_last <= lin[AW-1:0]; sparse_seen <= 1;
                            if(lin==0) begin
                                hwm[sel] <= 1; need_set <= 0; loaded <= 0;
                            end else hwm[sel] <= hwm[sel]+1'b1;
                        end
                    end else if (lin == hwm[sel] || MUT == 1) begin
                        if (hwm[sel][AW]) fault <= 1;
                        else begin pw_we[sel] <= 1; pw_addr <= lin[AW-1:0]; pw_data <= cd; hwm[sel] <= lin + 1'b1; end
                    end else if (lin == 0) begin
                        pw_we[sel] <= 1; pw_addr <= 0; pw_data <= cd; hwm[sel] <= 1;
                    end else fault <= 1;
                end else if (ca[11:10] == 2'b10) begin
                    if (ca[9:0] >= NPR) fault <= 1;
                    else begin prm[ca[9:0]*256 +: 256] <= cd; loaded[ca[9:0]] <= 1; end
                end else if (ca[11:9] == 3'b110) begin
                    if (ca[8:0] >= NREC) fault <= 1;
                    else begin
                        r_off[ca[8:0]] <= cd[31:0]; r_val[ca[8:0]] <= cd[32];
                        r_go[ca[8:0]] <= cd[34:33]; r_pay[ca[8:0]] <= cd[255:35];
                        if (NGO < 2 && cd[34]) fault <= 1;
                    end
                end else if (ca == 12'hE00) begin
                    if (cd[7:0] >= NS) fault <= 1;
                    else begin sel <= cd[SW-1:0]; page[cd[SW-1:0]] <= cd[8 +: PAGE_W]; end
                end else if (ca == 12'hE01) begin
                    for (k = 0; k < NS; k = k + 1) need[k] <= cd[k*32 +: AW+1];
                    wait_mask <= cd[128]; need_set <= 1;
                end else fault <= 1;
            end
            if (dhit) begin
                if (run || hit) fault <= 1; else armed <= 1;
            end
             
            if (lv && armed) begin
                armed <= 0;
                if (!(inst_ok && !fault && !run)) fault <= 1;
                else begin
                    start_v <= 1; run <= 1; cnt <= 0; rptr <= 0; tail <= TAIL[7:0];
                    wait_done <= wait_mask;
                end
            end
             
            if (run) begin
                cnt <= cnt + 1'b1;
                if (tail != 0 && !start_v) tail <= tail - 1'b1;
                if (done_q) wait_done <= 0;
                if (!recs_done) begin
                    if (cur_off == cmp_cnt) begin
                        go <= r_go[rptr][NGO-1:0]; rec <= r_pay[rptr]; rptr <= rptr + 1'b1; tail <= TAIL[7:0];
                    end else if (cur_off < cnt) fault <= 1;
                end else if (!start_v && tail == 0 && !(|busy_q) && !wait_done && go == 0) run <= 0;
            end
            active <= run || (lv && armed);
            ready <= armed && inst_ok && !fault && !run && !hit;
        end
    end
endmodule
