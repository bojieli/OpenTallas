`timescale 1ns/1ps
// Shared integrity functions for the public-reference RTL.
//
// The bit/byte traversal is part of the ICD: packed records are consumed from
// byte 0 upward and each byte is presented most-significant bit first.  Keeping
// the functions in a package prevents individual blocks from quietly choosing
// different CRC conventions.
package ot_crc_pkg;
    function automatic [15:0] crc16_ccitt;
        // A fixed maximum argument keeps the package compatible with older
        // open simulators; data_w selects the covered low-order bytes.
        input integer data_w;
        input [4095:0] data;
        integer byte_i;
        integer bit_i;
        reg [15:0] c;
        reg fb;
        begin
            c = 16'hffff;
            for (byte_i = 0; byte_i < data_w/8; byte_i = byte_i + 1) begin
                for (bit_i = 7; bit_i >= 0; bit_i = bit_i - 1) begin
                    fb = c[15] ^ data[byte_i*8 + bit_i];
                    c = {c[14:0], 1'b0};
                    if (fb)
                        c = c ^ 16'h1021;
                end
            end
            crc16_ccitt = c;
        end
    endfunction

    function automatic [31:0] crc32c;
        input integer data_w;
        input [4095:0] data;
        integer byte_i;
        integer bit_i;
        reg [31:0] c;
        reg fb;
        begin
            c = 32'hffffffff;
            // Reflected Castagnoli implementation.  The first transmitted
            // byte is the low byte of the packed record.
            for (byte_i = 0; byte_i < data_w/8; byte_i = byte_i + 1) begin
                for (bit_i = 0; bit_i < 8; bit_i = bit_i + 1) begin
                    fb = c[0] ^ data[byte_i*8 + bit_i];
                    c = c >> 1;
                    if (fb)
                        c = c ^ 32'h82f63b78;
                end
            end
            crc32c = c ^ 32'hffffffff;
        end
    endfunction
endpackage
