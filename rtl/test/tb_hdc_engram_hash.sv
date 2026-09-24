`timescale 1ns/1ps
// Streams golden vectors ("first cid row0 .. rowN-1", hex, one token position
// per line; see tools/rtl_hdc_v41_engram_campaign.py) through
// ot_hdc_engram_hash with random input bubbles and checks every column's row
// address, in order, bit for bit.  Clocked from outside (Verilator harness) or
// by the HDC_SELF_CLOCK wrapper (Icarus).
module tb_hdc_engram_hash (input wire clk);
    import ot_hdc_engram_tables_pkg::*;
    localparam integer MAXV = 1 << 16;
    localparam integer NC = ENG_LAYERS * ENG_COLS;
    localparam integer OW = ENG_ROW_W * NC;
    reg               vfirst [0:MAXV-1];
    reg [ENG_ID_W-1:0] vcid  [0:MAXV-1];
    reg [OW-1:0]      vrow   [0:MAXV-1];
    integer nvec = 0, fd, rc, i, c;
    reg [31:0] fld;

    reg rst_n = 1'b0;
    reg in_valid = 1'b0, in_first = 1'b0;
    reg [ENG_ID_W-1:0] in_cid = 0;
    wire out_valid;
    wire [OW-1:0] out_row;
    ot_hdc_engram_hash dut (.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_first(in_first),
                            .in_cid(in_cid), .out_valid(out_valid), .out_row(out_row));

    initial begin : load
        reg [8*512-1:0] path;
        reg [OW-1:0] row;
        if (!$value$plusargs("VEC=%s", path)) path = "engram_vectors.txt";
        fd = $fopen(path, "r");
        if (fd == 0) begin $display("cannot open vectors"); $finish; end
        rc = 1;
        while (rc > 0 && nvec < MAXV) begin
            rc = $fscanf(fd, "%h", fld);
            if (rc > 0) begin
                vfirst[nvec] = fld[0];
                rc = $fscanf(fd, "%h", fld);
                vcid[nvec] = fld[ENG_ID_W-1:0];
                row = {OW{1'b0}};
                for (c = 0; c < NC; c = c + 1) begin
                    rc = $fscanf(fd, "%h", fld);
                    row[ENG_ROW_W*c +: ENG_ROW_W] = fld[ENG_ROW_W-1:0];
                end
                vrow[nvec] = row;
                nvec = nvec + 1;
            end
        end
        $fclose(fd);
    end

    integer cyc = 0, sent = 0, got = 0, errors = 0, idle = 0;
    reg [31:0] seed = 32'h0BAD_5EED;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        seed = seed ^ (seed << 13); seed = seed ^ (seed >> 17); seed = seed ^ (seed << 5);
        if (rst_n && sent < nvec && seed[2:0] != 3'd0) begin
            in_valid <= 1'b1; in_first <= vfirst[sent]; in_cid <= vcid[sent];
            sent <= sent + 1;
        end else begin
            in_valid <= 1'b0; in_first <= seed[5]; in_cid <= seed[16:5];   // idle inputs are noise
        end
        if (rst_n && out_valid) begin
            if (got >= nvec || out_row !== vrow[got]) begin
                if (errors < 5) begin
                    $display("MISMATCH position=%0d", got);
                    for (c = 0; c < NC; c = c + 1)
                        if (out_row[ENG_ROW_W*c +: ENG_ROW_W] !== vrow[got][ENG_ROW_W*c +: ENG_ROW_W])
                            $display("  column %0d got %0d expect %0d", c, out_row[ENG_ROW_W*c +: ENG_ROW_W],
                                     vrow[got][ENG_ROW_W*c +: ENG_ROW_W]);
                end
                errors = errors + 1;
            end
            got = got + 1;
        end
        idle = (rst_n && sent >= nvec) ? idle + 1 : 0;
        if (idle > 40 || cyc > 4 * MAXV + 1000) begin
            $display("ENGRAM vectors=%0d checked=%0d errors=%0d cycles=%0d", nvec, got, errors, cyc);
            if (errors == 0 && got == nvec && nvec > 0) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
endmodule

`ifdef HDC_SELF_CLOCK
module tb_hdc_engram_hash_clk;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    tb_hdc_engram_hash u (.clk(clk));
endmodule
`endif
