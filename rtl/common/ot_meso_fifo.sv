// Option C candidate. Safe 3FF fallback; no raw/phase-qualified pointer bypass.
// Independent clock phase permitted. Gray pointer/control arcs require generated
// max-delay/bus-skew bounds; data stays stable until genuine consumer credit.
// Coarse clock-count drift monitor is fail-closed, NOT an analog phase detector.
module ot_meso_fifo #(
    parameter integer W=512,
    parameter integer DEPTH=4,
    parameter bit ENABLE=0,
    parameter integer SYNC_STAGES=3,
    parameter integer HOLD=8,
    parameter integer DRIFT_LIMIT=2
)(
    input wire wclk, wrst_n, w_v,
    output wire w_rdy,
    input wire [W-1:0] w_d,
    input wire rclk, rrst_n, r_rdy,
    output wire r_v,
    output wire [W-1:0] r_d,
    output wire w_live, r_live, w_fault, r_fault
);
    localparam integer AW=$clog2(DEPTH), PW=AW+1, CW=8, HW=$clog2(HOLD+1);
    initial begin
        if (DEPTH<4 || (DEPTH&(DEPTH-1))!=0 || SYNC_STAGES!=3 || HOLD<8)
            $error("ot_meso_fifo requires D>=4 power of 2, SYNC_STAGES=3, HOLD>=8");
        if (DRIFT_LIMIT<2 || DRIFT_LIMIT>32) $error("invalid drift limit");
    end
    generate if (!ENABLE) begin: disabled
        assign w_rdy=0; assign r_v=0; assign r_d=0;
        assign w_live=0; assign r_live=0; assign w_fault=0; assign r_fault=0;
    end else begin: active
        localparam [1:0] DOWN=0, WAIT=1, RUN=3;
        reg [W-1:0] mem[0:DEPTH-1];
        reg [PW-1:0] wp=0, rp=0, wg=0, rg=0;
        reg [1:0] ws=DOWN, rs=DOWN;
        reg [HW-1:0] wh=HW'(HOLD), rh=HW'(HOLD);
        reg wf=0, rf=0;
        reg [CW-1:0] wc=0, rc=0, wcg=0, rcg=0;
        reg [CW-1:0] w_anchor=0, r_anchor=0;
        (* async_reg="true" *) reg [PW-1:0] wg_r[0:SYNC_STAGES-1], rg_w[0:SYNC_STAGES-1];
        (* async_reg="true" *) reg [CW-1:0] wcg_r[0:SYNC_STAGES-1], rcg_w[0:SYNC_STAGES-1];
        (* async_reg="true" *) reg [1:0] ws_r[0:SYNC_STAGES-1], rs_w[0:SYNC_STAGES-1];
        (* async_reg="true" *) reg wf_r[0:SYNC_STAGES-1], rf_w[0:SYNC_STAGES-1];
        reg ov=0; reg [W-1:0] od;
        function automatic [PW-1:0] pbin(input [PW-1:0] g);
            integer j; begin pbin[PW-1]=g[PW-1]; for(j=PW-2;j>=0;j=j-1) pbin[j]=pbin[j+1]^g[j]; end
        endfunction
        function automatic [CW-1:0] cbin(input [CW-1:0] g);
            integer j; begin cbin[CW-1]=g[CW-1]; for(j=CW-2;j>=0;j=j-1) cbin[j]=cbin[j+1]^g[j]; end
        endfunction
        wire [PW-1:0] peer_rp=pbin(rg_w[SYNC_STAGES-1]), peer_wp=pbin(wg_r[SYNC_STAGES-1]);
        wire [PW-1:0] used=wp-peer_rp, avail=peer_wp-rp;
        wire signed [CW-1:0] w_drift=$signed(wc-cbin(rcg_w[SYNC_STAGES-1])-w_anchor);
        wire signed [CW-1:0] r_drift=$signed(rc-cbin(wcg_r[SYNC_STAGES-1])-r_anchor);
        wire w_bad=(ws==RUN) && rs_w[SYNC_STAGES-1]==RUN && ((w_drift>CW'(DRIFT_LIMIT))||(w_drift< -CW'(DRIFT_LIMIT))||(used>PW'(DEPTH)));
        wire r_bad=(rs==RUN) && ws_r[SYNC_STAGES-1]==RUN && ((r_drift>CW'(DRIFT_LIMIT))||(r_drift< -CW'(DRIFT_LIMIT))||(avail>PW'(DEPTH)));
        assign w_live=ENABLE && wrst_n && ws==RUN && rs_w[SYNC_STAGES-1]==RUN && !wf && !rf_w[SYNC_STAGES-1] && !w_bad;
        assign r_live=ENABLE && rrst_n && rs==RUN && ws_r[SYNC_STAGES-1]==RUN && !rf && !wf_r[SYNC_STAGES-1] && !r_bad;
        assign w_rdy=w_live && used<PW'(DEPTH);
        assign r_v=r_live && ov;
        assign r_d=od;
        assign w_fault=wf; assign r_fault=rf;
        wire pop=r_v && r_rdy;
        wire [PW-1:0] rp_next=rp+{{(PW-1){1'b0}},pop};

        always @(posedge wclk) begin
            if (!wrst_n) begin
                for(integer j=0;j<SYNC_STAGES;j=j+1) begin rg_w[j]<=0;rcg_w[j]<=0;rs_w[j]<=DOWN;rf_w[j]<=0;end
            end else begin
                rg_w[0]<=rg;rcg_w[0]<=rcg;rs_w[0]<=rs;rf_w[0]<=rf;
                for(integer j=1;j<SYNC_STAGES;j=j+1) begin rg_w[j]<=rg_w[j-1];rcg_w[j]<=rcg_w[j-1];rs_w[j]<=rs_w[j-1];rf_w[j]<=rf_w[j-1];end
            end
            if (!wrst_n) begin ws<=DOWN;wh<=HW'(HOLD);wp<=0;wg<=0;wc<=0;wcg<=0;wf<=0;w_anchor<=0;end
            else begin
                wc<=wc+1'b1;wcg<=((wc+1'b1)>>1)^(wc+1'b1);
                if(w_bad || rf_w[SYNC_STAGES-1]) wf<=1;
                case(ws)
                    DOWN: begin wp<=0;wg<=0;if(wh!=0)wh<=wh-1'b1;else if(rs_w[SYNC_STAGES-1]!=RUN)ws<=WAIT;end
                    WAIT: if(rs_w[SYNC_STAGES-1]!=DOWN)begin ws<=RUN;w_anchor<=wc-cbin(rcg_w[SYNC_STAGES-1]);end
                    RUN: if(rs_w[SYNC_STAGES-1]==DOWN)begin ws<=DOWN;wh<=HW'(HOLD);wp<=0;wg<=0;end
                default:begin ws<=DOWN;wf<=1;end
                endcase
                if(w_v && w_rdy)begin mem[wp[AW-1:0]]<=w_d;wp<=wp+1'b1;wg<=((wp+1'b1)>>1)^(wp+1'b1);end
            end
        end
        always @(posedge rclk) begin
            if (!rrst_n) begin
                for(integer j=0;j<SYNC_STAGES;j=j+1) begin wg_r[j]<=0;wcg_r[j]<=0;ws_r[j]<=DOWN;wf_r[j]<=0;end
            end else begin
                wg_r[0]<=wg;wcg_r[0]<=wcg;ws_r[0]<=ws;wf_r[0]<=wf;
                for(integer j=1;j<SYNC_STAGES;j=j+1) begin wg_r[j]<=wg_r[j-1];wcg_r[j]<=wcg_r[j-1];ws_r[j]<=ws_r[j-1];wf_r[j]<=wf_r[j-1];end
            end
            if(!rrst_n)begin rs<=DOWN;rh<=HW'(HOLD);rp<=0;rg<=0;rc<=0;rcg<=0;rf<=0;ov<=0;r_anchor<=0;end
            else begin
                rc<=rc+1'b1;rcg<=((rc+1'b1)>>1)^(rc+1'b1);
                if(r_bad || wf_r[SYNC_STAGES-1])rf<=1;
                case(rs)
                    DOWN:begin rp<=0;rg<=0;ov<=0;if(rh!=0)rh<=rh-1'b1;else if(ws_r[SYNC_STAGES-1]!=RUN)rs<=WAIT;end
                    WAIT:if(ws_r[SYNC_STAGES-1]!=DOWN)begin rs<=RUN;r_anchor<=rc-cbin(wcg_r[SYNC_STAGES-1]);end
                    RUN:if(ws_r[SYNC_STAGES-1]==DOWN)begin rs<=DOWN;rh<=HW'(HOLD);rp<=0;rg<=0;ov<=0;end
                default:begin rs<=DOWN;rf<=1;ov<=0;end
                endcase
                if(r_live)begin
                    if(pop)begin rp<=rp_next;rg<=(rp_next>>1)^rp_next;end
                    if(!ov || pop)begin
                        if(peer_wp!=rp_next)begin od<=mem[rp_next[AW-1:0]];ov<=1;end
                        else ov<=0;
                    end
                end else ov<=0;
            end
        end
    end endgenerate
endmodule
