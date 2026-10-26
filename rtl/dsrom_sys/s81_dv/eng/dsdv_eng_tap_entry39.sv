`timescale 1ns/1ps
// The first Engram tap receives the native PCBASE=0 address format:
// request {tag[6:0], sector[25:0], pc[4:0], valid}. The 30-bit sector
// interface used by downstream taps has four absent address bits [35:32].
// This is a real 39-bit entry ABI. No clock or data/control edge changes.
module dsdv_eng_tap_entry39 (
    input wire ck, input wire rst_n, input wire [3:0] sid,
    input wire [38:0] rci, output wire [42:0] rco,
    input wire [267:0] pci, output wire [267:0] pco,
    input wire [91:0] rqi, output wire [91:0] rqo,
    input wire [543:0] rri, output wire [543:0] rro, output wire fault
);
    wire [42:0] entry_request = {rci[38:32], 4'd0, rci[31:0]};
    dsdv_eng_tap_c #(.WEST(0)) u_t (
        .ck(ck), .rst_n(rst_n), .sid(sid), .rci(entry_request), .rco(rco),
        .pci(pci), .pco(pco), .rqi(rqi), .rqo(rqo),
        .rri(rri), .rro(rro), .fault(fault));
endmodule
