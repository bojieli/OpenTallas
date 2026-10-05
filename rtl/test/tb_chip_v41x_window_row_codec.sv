`timescale 1ns/1ps
module tb_chip_v41x_window_row_codec;
    reg [4223:0] row;
    reg [20:0] position;
    reg [29:0] region_base_sector, region_sector_count;
    reg [4:0] sector_index;
    reg [8:0] element_index;
    wire [29:0] sector_address;
    wire [255:0] sector_data;
    wire [31:0] sector_strobe, element_fp32;
    wire address_fault, element_fault;
    ot_chip_v41x_window_row_codec dut(.*);
    integer fin, fout, rc, n;
    reg [1023:0] infile, outfile;
    initial begin
        if (!$value$plusargs("IN=%s", infile) || !$value$plusargs("OUT=%s", outfile))
            $fatal(1, "IN and OUT paths required");
        fin = $fopen(infile, "r"); fout = $fopen(outfile, "w");
        if (!fin || !fout) $fatal(1, "file open failed");
        n = 0;
        while (!$feof(fin)) begin
            rc = $fscanf(fin, "%h %d %d %d %d %d\n", row, position,
                         region_base_sector, region_sector_count, sector_index, element_index);
            if (rc == 6) begin
                #1;
                $fdisplay(fout, "%h %h %h %b %h %b", sector_address,
                          sector_data, sector_strobe, address_fault,
                          element_fp32, element_fault);
                n = n + 1;
            end else if (!$feof(fin)) $fatal(1, "malformed vector %0d", n);
        end
        $fclose(fin); $fclose(fout);
        $display("vectors=%0d", n);
        $finish;
    end
endmodule
