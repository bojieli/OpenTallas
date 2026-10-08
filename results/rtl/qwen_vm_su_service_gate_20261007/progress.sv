module source_progress(input wire clk,rst_n,retire,emit,accept,v_last_r,input wire[0:0]l_last,output reg[15:0]progress,progress_rows,output wire chased_out);
 wire[15:0]su_progress=progress,su_rows=progress_rows,me_progress=0;
 wire[1:0]d_unit=1;wire d_chase_rows=0;wire[15:0]d_chase_n=1;
    // Element chaining in vectors: retirement is in order, so the latest
    // instruction has written (vectors retired - vectors emitted before it).
    reg [15:0] n_emit, n_retire, first_mark;
    wire [15:0] done_n = n_retire - first_mark;
    //: rows: a row's last vector carries l_last; rows retire in order too
    reg [15:0] r_emit, r_retire, r_mark;
    wire [15:0] rdone_n = r_retire - r_mark;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            n_emit <= 0; n_retire <= 0; first_mark <= 0; progress <= 0;
            r_emit <= 0; r_retire <= 0; r_mark <= 0; progress_rows <= 0;
        end else begin
            n_emit <= n_emit + (emit ? 16'd1 : 16'd0);
            n_retire <= n_retire + (retire ? 16'd1 : 16'd0);
            r_emit <= r_emit + ((emit && v_last_r) ? 16'd1 : 16'd0);
            r_retire <= r_retire + ((retire && l_last[0]) ? 16'd1 : 16'd0);
            if (accept) begin
                first_mark <= n_emit; progress <= 0;
                r_mark <= r_emit; progress_rows <= 0;
            end else begin
                progress <= done_n[15] ? 16'd0 : done_n;
                progress_rows <= rdone_n[15] ? 16'd0 : rdone_n;
            end
        end
    end

    wire chased = ((d_unit == 2'd1) ? (d_chase_rows ? su_rows : su_progress) : me_progress) >= d_chase_n;
assign chased_out=chased;
endmodule
