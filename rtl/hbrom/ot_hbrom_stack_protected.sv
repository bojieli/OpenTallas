`timescale 1ns/1ps
// Protected ownership/metadata only. FP32 adders and pending arithmetic values stay single.
module ot_hbrom_stack_protected #(parameter integer PROTECT=0,LEV=4,IL=8,TAGW=12,ALAT=7)(
 input wire clk,rst_n,iv,input wire [31:0] d,input wire ilast,
 input wire [$clog2(IL)-1:0] islot,input wire [TAGW-1:0] itag,
 output wire ov,output wire [31:0] y,output wire [TAGW-1:0] otag,output wire fault);
 generate if(!PROTECT) begin:g_original
  ot_hbm_accel_stack #(.LEV(LEV),.IL(IL),.TAGW(TAGW),.ALAT(ALAT)) u_original(.*);
 end else begin:g_protected
    reg ov_raw,fault_raw;reg [TAGW-1:0] otag_raw;reg [31:0] y_raw;
    localparam integer SW = $clog2(IL);
    localparam integer MW = SW + TAGW + 1;          // meta: last, slot, tag
    // ---- the stack's input register (level 0's look-ahead tap is the unregistered input) ----
    reg              iv_q, ilast_q;
    (* keep *) reg iv_q_b, ilast_q_b;
    (* keep *) reg [SW-1:0] islot_q_b;
    (* keep *) reg [TAGW-1:0] itag_q_b;
    wire [LEV-1:0] local_bad;
    wire input_bad = {iv_q,ilast_q,islot_q,itag_q}!={iv_q_b,ilast_q_b,islot_q_b,itag_q_b};
    always @(posedge clk or negedge rst_n) begin
      if(!rst_n) begin iv_q_b<=0;ilast_q_b<=0;islot_q_b<=0;itag_q_b<=0;end
      else begin iv_q_b<=iv;ilast_q_b<=ilast;islot_q_b<=islot;itag_q_b<=itag;end
    end
    reg [31:0]       d_q;
    reg [SW-1:0]     islot_q;
    reg [TAGW-1:0]   itag_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) iv_q <= 1'b0;
        else iv_q <= iv;
    always @(posedge clk) begin
      d_q <= d;
      if(!rst_n) begin ilast_q<=0;islot_q<=0;itag_q<=0;end
      else begin ilast_q <= ilast; islot_q <= islot; itag_q <= itag; end
    end
    wire [LEV:0]          lv_v, lv_ev;              // valid now / valid next cycle
    wire [LEV:0]          lv_last;
    wire [32*(LEV+1)-1:0] lv_d;
    wire [SW*(LEV+1)-1:0] lv_slot, lv_eslot;        // slot now / slot next cycle
    wire [TAGW*(LEV+1)-1:0] lv_tag;
    wire [LEV:0]          ret_v;
    wire [32*(LEV+1)-1:0] ret_d;
    wire [TAGW*(LEV+1)-1:0] ret_tag;
    wire [LEV:0]          lf;
    assign lv_v[0] = iv_q;
    assign lv_ev[0] = iv;
    assign lv_last[0] = ilast_q;
    assign lv_d[31:0] = d_q;
    assign lv_slot[SW-1:0] = islot_q;
    assign lv_eslot[SW-1:0] = islot;
    assign lv_tag[TAGW-1:0] = itag_q;
    genvar l;
        for (l = 0; l < LEV; l = l + 1) begin : g_lv
            reg [IL-1:0]  pend_v, seen;
            (* keep *) reg [IL-1:0] pend_v_b, seen_b;
            (* keep *) reg have_q_b, seen_q_b;
            wire wr_b = v_in && !last_in && !have_q_b;
            wire n_pend_b = upd ? wr_b : pend_v_b[es];
            wire n_seen_b = upd ? !last_in : seen_b[es];
            always @(posedge clk or negedge rst_n) begin
              if(!rst_n) begin pend_v_b<=0;seen_b<=0;have_q_b<=0;seen_q_b<=0;end
              else begin
                have_q_b<=n_pend_b;seen_q_b<=n_seen_b;
                if(v_in) begin
                  if(last_in) begin pend_v_b[s_in]<=0;seen_b[s_in]<=0;end
                  else if(have_q_b) begin pend_v_b[s_in]<=0;seen_b[s_in]<=1;end
                  else begin pend_v_b[s_in]<=1;seen_b[s_in]<=1;end
                end
              end
            end
            reg [31:0]    pend_d [0:IL-1];
            wire          v_in = lv_v[l];
            wire          last_in = lv_last[l];
            wire [31:0]   d_in = lv_d[32*l +: 32];
            wire [SW-1:0] s_in = lv_slot[SW*l +: SW];
            wire [SW-1:0] es = lv_eslot[SW*l +: SW];
            wire [TAGW-1:0] t_in = lv_tag[TAGW*l +: TAGW];
            // registered look-ahead of slot s_in's state (valid whenever v_in)
            reg           have_q, seen_q;
            reg  [31:0]   opa_q;
            wire          have = have_q;
            wire          lone = v_in && last_in && !have && !seen_q;
            wire          go   = v_in && !lone && (have || last_in);
            wire          wr   = v_in && !last_in && !have;          // this cycle parks d_in in slot s_in
            wire          upd  = v_in && (s_in == es);
            wire          n_pend = upd ? wr : pend_v[es];
            wire          n_seen = upd ? !last_in : seen[es];
            wire [31:0]   n_d    = (upd && wr) ? d_in : pend_d[es];
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    pend_v <= {IL{1'b0}};
                    seen <= {IL{1'b0}};
                    have_q <= 1'b0;
                    seen_q <= 1'b0;
                end else begin
                    have_q <= n_pend;
                    seen_q <= n_seen;
                    if (v_in) begin
                        if (last_in) begin
                            pend_v[s_in] <= 1'b0;
                            seen[s_in] <= 1'b0;
                        end else if (have) begin
                            pend_v[s_in] <= 1'b0;
                            seen[s_in] <= 1'b1;
                        end else begin
                            pend_v[s_in] <= 1'b1;
                            seen[s_in] <= 1'b1;
                        end
                    end
                end
            end
            always @(posedge clk) begin
                opa_q <= n_pend ? n_d : 32'd0;
                if (wr) pend_d[s_in] <= d_in;
            end
            wire [31:0] sum;
            ot_gpu_fadd #(.LAT(ALAT)) u_add (.clk(clk), .rst_n(rst_n), .v(go), .a(opa_q), .b(d_in), .y(sum), .fault(lf[l]));
            wire [ALAT:0] gv;
            ot_hdc_vline #(.D(ALAT)) u_gv (.clk(clk), .rst_n(rst_n), .v(go), .vd(gv));
            // meta delay line with every tap (the next level's look-ahead reads tap ALAT - 1)
            reg [MW-1:0] meta [1:ALAT];
            (* keep *) reg [MW-1:0] meta_b [1:ALAT];
            reg [ALAT:1] valid_b;
            wire [ALAT-1:0] meta_bad;
            genvar mi;
            for(mi=1;mi<=ALAT;mi=mi+1) begin:g_meta_check
              assign meta_bad[mi-1]=(meta[mi]!=meta_b[mi]);
            end
            assign local_bad[l] = (pend_v!=pend_v_b)||(seen!=seen_b)||(have_q!=have_q_b)||(seen_q!=seen_q_b)||(|meta_bad)||(gv[ALAT:1]!=valid_b);
            integer kb;
            always @(posedge clk or negedge rst_n) begin
              if(!rst_n) valid_b<=0;
              else valid_b<={valid_b[ALAT-1:1],go};
            end
            always @(posedge clk) begin
              if(!rst_n) for(kb=1;kb<=ALAT;kb=kb+1) meta_b[kb]<=0;
              else begin
                meta_b[1]<={last_in,s_in,t_in};
                for(kb=2;kb<=ALAT;kb=kb+1) meta_b[kb]<=meta_b[kb-1];
              end
            end
            integer k;
            always @(posedge clk) begin
                if(!rst_n) for(k=1;k<=ALAT;k=k+1) meta[k]<=0;
                else begin
                  meta[1] <= {last_in, s_in, t_in};
                  for (k = 2; k <= ALAT; k = k + 1) meta[k] <= meta[k-1];
                end
            end
            wire [MW-1:0] meta_q = meta[ALAT];
            wire [MW-1:0] meta_e = (ALAT >= 2) ? meta[ALAT-1] : {last_in, s_in, t_in};
            assign lv_v[l+1] = gv[ALAT];
            assign lv_ev[l+1] = gv[ALAT-1];
            assign lv_last[l+1] = meta_q[SW+TAGW];
            assign lv_slot[SW*(l+1) +: SW] = meta_q[SW+TAGW-1:TAGW];
            assign lv_eslot[SW*(l+1) +: SW] = meta_e[SW+TAGW-1:TAGW];
            assign lv_tag[TAGW*(l+1) +: TAGW] = meta_q[TAGW-1:0];
            assign lv_d[32*(l+1) +: 32] = sum;
            assign ret_v[l] = lone;
            assign ret_d[32*l +: 32] = d_in;
            assign ret_tag[TAGW*l +: TAGW] = t_in;
        end
    assign ret_v[LEV] = lv_v[LEV];
    assign ret_d[32*LEV +: 32] = lv_d[32*LEV +: 32];
    assign ret_tag[TAGW*LEV +: TAGW] = lv_tag[TAGW*LEV +: TAGW];
    assign lf[LEV] = 1'b0;
    integer kk, nret;
    reg [31:0] y_n;
    reg [TAGW-1:0] t_n;
    always @* begin
        nret = 0; y_n = 32'd0; t_n = {TAGW{1'b0}};
        for (kk = 0; kk <= LEV; kk = kk + 1)
            if (ret_v[kk]) begin
                nret = nret + 1;
                y_n = ret_d[32*kk +: 32];
                t_n = ret_tag[TAGW*kk +: TAGW];
            end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ov_raw <= 1'b0; y_raw <= 32'd0; otag_raw <= {TAGW{1'b0}}; fault_raw <= 1'b0;
        end else begin
            ov_raw <= |ret_v;
            y_raw <= y_n;
            otag_raw <= t_n;
            fault_raw <= fault_raw | (|lf) | (nret > 1);
        end
    end

    (* keep *) reg ov_b,fault_b,poison_a,poison_b;
    (* keep *) reg [TAGW-1:0] otag_b;
    wire output_bad=(ov_raw!=ov_b)||(otag_raw!=otag_b)||(fault_raw!=fault_b);
    wire mismatch=input_bad|(|local_bad)|output_bad;
    always @(posedge clk or negedge rst_n) begin
      if(!rst_n) begin ov_b<=0;otag_b<=0;fault_b<=0;end
      else begin ov_b<=|ret_v;otag_b<=t_n;fault_b<=fault_b|(|lf)|(nret>1);end
    end
    always @(posedge clk or negedge rst_n)
      if(!rst_n) poison_a<=0;else poison_a<=poison_a|poison_b|mismatch;
    always @(posedge clk or negedge rst_n)
      if(!rst_n) poison_b<=0;else poison_b<=poison_b|poison_a|mismatch;
    assign fault=fault_raw|fault_b|poison_a|poison_b|mismatch;
    assign ov=ov_raw&&!fault;assign otag=otag_raw;assign y=y_raw;
 end endgenerate
endmodule
