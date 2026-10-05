    // ---- network pipe to the tiles -------------------------------------------------------
    reg [NE-1:0]   q_v    [0:FILL_LAT-1];
    reg [10:0]     q_tile [0:FILL_LAT-1][0:NE-1];
    reg [6:0]      q_loc  [0:FILL_LAT-1][0:NE-1];
    reg [511:0]    q_data [0:FILL_LAT-1][0:NE-1];
    reg [511:0]    q_msk  [0:FILL_LAT-1][0:NE-1];
    reg [FILL_LAT+2:0] inflight;      // a slice write somewhere between here and its SRAM edge
    integer si, sj;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (si = 0; si < FILL_LAT; si = si + 1) q_v[si] <= 0;
            kvw_ce <= 0; inflight <= 0;
        end else begin
            q_v[0] <= e_v;
            for (si = 1; si < FILL_LAT; si = si + 1) q_v[si] <= q_v[si-1];
            inflight <= {inflight[FILL_LAT+1:0], |e_v};
            kvw_ce <= 0;
            for (sj = 0; sj < NE; sj = sj + 1)
                if (q_v[FILL_LAT-1][sj]) kvw_ce[q_tile[FILL_LAT-1][sj]] <= 1'b1;
        end
    end
    always @(posedge clk) begin
        for (sj = 0; sj < NE; sj = sj + 1) begin
            q_tile[0][sj] <= e_tile[sj]; q_loc[0][sj] <= e_loc[sj]; q_data[0][sj] <= e_data[sj]; q_msk[0][sj] <= e_msk[sj];
        end
        for (si = 1; si < FILL_LAT; si = si + 1)
            for (sj = 0; sj < NE; sj = sj + 1)
                if (q_v[si-1][sj]) begin
                    q_tile[si][sj] <= q_tile[si-1][sj]; q_loc[si][sj] <= q_loc[si-1][sj];
                    q_data[si][sj] <= q_data[si-1][sj]; q_msk[si][sj] <= q_msk[si-1][sj];
                end
        for (sj = 0; sj < NE; sj = sj + 1)
            if (q_v[FILL_LAT-1][sj]) begin
                kvw_addr[q_tile[FILL_LAT-1][sj]*7 +: 7] <= q_loc[FILL_LAT-1][sj];
                kvw_data[q_tile[FILL_LAT-1][sj]*512 +: 512] <= q_data[FILL_LAT-1][sj];
                kvw_mask[q_tile[FILL_LAT-1][sj]*512 +: 512] <= q_msk[FILL_LAT-1][sj];
            end
    end
    wire pipe_empty = (inflight == 0) && (e_v == 0);

