`timescale 1ns/1fs
// Actual registered fusion endpoint; cached source operands/expected only.
module tb_hbm_accel_su_fused_norm #(
 parameter integer N=256,D=1280,HC=0,RD=0,QUANT=1,RW=9,BW=9
);
 localparam integer NV=(D+N-1)/N, NX=(HC?4:1)*D, NB=D/32;
 reg clk=0;
 always #0.416666667 clk=~clk;
    reg [31:0]  xm [0:NX-1];
    reg [31:0]  wm [0:D-1];
    reg [31:0]  cfg [0:5];
    reg [31:0]  csm [0:(RD ? RD : 2)-1];
    reg [31:0]  ey [0:D-1];
    reg [31:0]  er [0:D-1];
    reg [255:0] eqc [0:NB-1];
    reg [15:0]  eqe [0:NB-1];
    reg [511:0] eqy [0:NB-1];
    initial begin
        $readmemh("x.mem", xm);
        $readmemh("w.mem", wm);
        $readmemh("cfg.mem", cfg);
        $readmemh("ey.mem", ey);
        if (RD > 0) begin $readmemh("cs.mem", csm); $readmemh("er.mem", er); end
        if (QUANT) begin $readmemh("eqc.mem", eqc); $readmemh("eqe.mem", eqe); $readmemh("eqy.mem", eqy); end
    end

    reg rst_n = 1'b0, go = 1'b0, in_v = 1'b0, wl_v = 1'b0;
    reg [7:0] wl_i = 0;
    reg [N*32-1:0] wl_d;
    reg [(HC ? 4 : 1)*N*32-1:0] in_x;
    wire y_v, q_v, ro_v, fault;
    wire [7:0] y_i, q_i;
    wire [N*32-1:0] y, ro;
    wire [(QUANT ? N/32 : 1)*256-1:0] q_codes;
    wire [(QUANT ? N/32 : 1)*10-1:0] q_e;
    wire [(QUANT ? N/32 : 1)*512-1:0] q_y;
    reg  [(RD ? RD/2 : 1)*32-1:0] cos_t, sin_t;
    integer i, j, k;
    initial begin
        cos_t = 0; sin_t = 0;
        #0.1;
        for (i = 0; i < RD / 2; i = i + 1) begin
            cos_t[i * 32 +: 32] = csm[i];
            sin_t[i * 32 +: 32] = csm[RD / 2 + i];
        end
    end

    wire cmd_ready, gain_ready, in_ready, busy, done;
    wire [15:0] reserve_events; wire [31:0] completion_id;
    wire [4*N*32-1:0] operands = {{(4*N*32-(HC?4:1)*N*32){1'b0}},in_x};
    ot_hbm_accel_su_fused_stream #(.ENABLE(1),.KIND(HC?0:(RD?2:1)),
        .N(N),.D(D),.RD(RD),.LM(6),.LA(5),.BCAST(7),.RET(8),.RW(RW),.BW(BW)) dut (
        .clk(clk),.rst_n(rst_n),.cmd_valid(go),.cmd_id(32'h1048575),
        .reserve_grant(1'b1),.reserve_events(reserve_events),.cmd_ready(cmd_ready),
        .busy(busy),.done(done),.completion_id(completion_id),
        .comb(512'd0),.post_pre({cfg[3],cfg[2],cfg[1],cfg[0]}),.n_f(cfg[4]),.eps(cfg[5]),.lim(32'd0),
        .cos_t(cos_t),.sin_t(sin_t),.gain_valid(wl_v),.gain_index(wl_i),.gain_data(wl_d),.gain_ready(gain_ready),
        .in_valid(in_v),.in_ready(in_ready),.operands(operands),.sink_ready(1'b1),
        .y_valid(y_v),.ro_valid(ro_v),.q_valid(q_v),.y_index(y_i),.q_index(q_i),
        .y_data(y),.ro_data(ro),.q_codes(q_codes),.q_exp(q_e),.q_bf16(q_y),.fault(fault));
    integer cyc=0,go_cyc=-1,cold_cyc=-1,iss=0,load=0;
    integer ey_err=0,er_err=0,eq_err=0,ny=0,nq=0,nr=0;
    integer y_last=-1,ro_last=-1,q_last=-1,ro_cnt=0;
    reg sent_cmd=0;
    // Cold gain reads are inside the measured interval. Operand availability
    // and actual engine readiness drive acceptance, not a timestamp offset.
    always @(negedge clk) begin
        if(cyc==3) rst_n=1;
        wl_v=0; go=0; in_v=0;
        if(rst_n && load<NV && gain_ready) begin
            wl_v=1; wl_i=load;
            for(j=0;j<N;j=j+1) wl_d[j*32+:32]=(load*N+j<D)?wm[load*N+j]:0;
        end else if(!sent_cmd && load==NV && cmd_ready) go=1;
        if(sent_cmd && iss<NV && in_ready) begin
            in_v=1;
            for(k=0;k<(HC?4:1);k=k+1)
                for(j=0;j<N;j=j+1)
                    in_x[(k*N+j)*32+:32]=(iss*N+j<D)?xm[k*D+iss*N+j]:0;
        end
        if(done) begin
            $display("FUSED_END cold=%0d cmd=%0d end=%0d checked_y=%0d checked_r=%0d checked_q=%0d ey=%0d er=%0d eq=%0d fault=%0d id=%0d",cold_cyc,go_cyc,cyc,ny,nr,nq,ey_err,er_err,eq_err,fault,completion_id);
            if(ey_err==0 && er_err==0 && eq_err==0 && ny==D && (RD==0 || nr==D) && nq==NB && !fault && completion_id==32'h1048575) $display("PASS");
            else $fatal(1,"fusion endpoint cached mismatch");
            $finish;
        end
        if(fault) $fatal(1,"fusion endpoint fault (lease retained)");
    end
    always @(posedge clk) begin
        cyc<=cyc+1;
        if(wl_v && gain_ready) begin
            if(cold_cyc<0) cold_cyc<=cyc;
            load<=load+1;
            $display("FUSED_EVENT gain_load cycle=%0d index=%0d time_ns=%0t",cyc,wl_i,$realtime);
        end
        if(go && cmd_ready) begin
            go_cyc<=cyc; sent_cmd<=1;
            $display("FUSED_EVENT command cycle=%0d reserve=%0d time_ns=%0t",cyc,reserve_events,$realtime);
        end
        if(in_v && in_ready) begin
            iss<=iss+1;
            $display("FUSED_EVENT input cycle=%0d index=%0d time_ns=%0t",cyc,iss,$realtime);
        end
        if(y_v) $display("FUSED_EVENT landing_y cycle=%0d index=%0d time_ns=%0t",cyc,y_i,$realtime);
        if(ro_v) $display("FUSED_EVENT landing_ro cycle=%0d time_ns=%0t",cyc,$realtime);
        if(q_v) $display("FUSED_EVENT landing_q cycle=%0d index=%0d time_ns=%0t",cyc,q_i,$realtime);
        if (y_v) begin
            y_last <= cyc - go_cyc;
            for (j = 0; j < N; j = j + 1)
                if (y_i * N + j < D) begin
                    ny = ny + 1;
                    if (y[j * 32 +: 32] !== ey[y_i * N + j]) begin
                        if (ey_err < 5) $display("Y mismatch el %0d got %08x want %08x", y_i * N + j, y[j * 32 +: 32],
                                                 ey[y_i * N + j]);
                        ey_err = ey_err + 1;
                    end
                end
        end
        if (ro_v) begin
            ro_last <= cyc - go_cyc;
            for (j = 0; j < N; j = j + 1)
                if (ro_cnt * N + j < D) begin
                    nr = nr + 1;
                    if (ro[j * 32 +: 32] !== er[ro_cnt * N + j]) begin
                        if (er_err < 5) $display("R mismatch el %0d got %08x want %08x", ro_cnt * N + j, ro[j * 32 +: 32],
                                                 er[ro_cnt * N + j]);
                        er_err = er_err + 1;
                    end
                end
            ro_cnt = ro_cnt + 1;
        end
        if (q_v) begin
            q_last <= cyc - go_cyc;
            for (k = 0; k < (QUANT ? N / 32 : 0); k = k + 1)
                if (q_i * (N / 32) + k < NB) begin
                    nq = nq + 1;
                    if (q_codes[k * 256 +: 256] !== eqc[q_i * (N / 32) + k] ||
                        q_e[k * 10 +: 10] !== eqe[q_i * (N / 32) + k][9:0] ||
                        q_y[k * 512 +: 512] !== eqy[q_i * (N / 32) + k]) begin
                        if (eq_err < 5) $display("Q mismatch block %0d e %0d want %0d", q_i * (N / 32) + k,
                                                 $signed(q_e[k * 10 +: 10]), $signed(eqe[q_i * (N / 32) + k][9:0]));
                        eq_err = eq_err + 1;
                    end
                end
        end
    end
endmodule
