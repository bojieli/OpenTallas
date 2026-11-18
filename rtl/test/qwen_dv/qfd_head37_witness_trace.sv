// Simulation-only receiver-face probe. Instantiate beside the selected TT WTN.
// It observes the same accepted start/observation inputs; it never drives them.
`ifndef SYNTHESIS
module qfd_head37_witness_trace (
    input wire ck, rst_n,
    input wire [24:0] start,
    input wire [37:0] obs
);
    integer fd;
    longint unsigned edge_index = 0;
    string trace_path;
    initial begin
        if (!$value$plusargs("HEAD37_WITNESS_TRACE=%s", trace_path))
            $fatal(1, "actual HEAD37 witness trace path required");
        // The runner owns a newly created private output directory. Standard
        // SV fopen has no exclusive-create mode; refuse any existing file.
        fd = $fopen(trace_path, "r");
        if (fd) begin
            $fclose(fd);
            fd = 0;
            $fatal(1, "existing actual HEAD37 witness trace refused");
        end
        fd = $fopen(trace_path, "w");
        if (!fd) $fatal(1, "new actual HEAD37 witness trace required; existing file refused");
        $fdisplay(fd, "HEAD37_TRACE_V1 RECEIVER_FACE_PRE_NBA");
    end
    always @(posedge ck) begin
        if (rst_n) begin
            if (start[24] && start[21:16] == 37)
                $fdisplay(fd, "HEAD37_START %0d %0d %0d %0d", edge_index,
                          start[23:22], start[21:16], start[15:0]);
            if (obs[37] && obs[21:16] == 37)
                $fdisplay(fd, "HEAD37_OBS %0d %0d %0d %0d %0d %0d", edge_index,
                          obs[36:35], obs[34:31], obs[30:22], obs[21:16], obs[15:0]);
            $fflush(fd);
        end
        edge_index <= edge_index + 1;
    end
    final if (fd) $fclose(fd);
endmodule
`endif
