// One physically selected embedding bank + static expansion leaf. The compiler
// routes token to owner/bank and supplies its fixed base; no demand arbitration.
// Table geometry: owner=token/32320, bank=(token%32320*320)/4096,
// base=(token%32320*320)%4096. A compiler may split a crossing row across banks;
// this one-bank composition rejects those commands instead of wrapping them.
module ot_s81_embedding_bank #(
    parameter string VIAMAP="",
    parameter integer OWNER=0, BANK=0, MUTANT=0
)(
    input wire clk,rst_n,start,
    input wire [16:0] token,
    input wire [12:0] base,
    input wire [13:0] vm_base,
    input wire [511:0] header,
    output wire busy,done,fault,vm_v,
    output wire [13:0] vm_row,
    output wire [511:0] vm_d,
    output wire hop_v,hop_last,
    output wire [511:0] hop_d
);
    wire rv,rb,ef;
    wire [8:0] ri;
    wire [511:0] rd;
    reg command_fault;
    wire [25:0] source_word=26'(token%32320)*26'd320;
    always @(posedge clk) begin
        if(!rst_n) command_fault<=0;
        else if(start && (token>=129280 || token/32320!=OWNER || source_word/4096!=BANK ||
            base!={1'b0,source_word[11:0]} || base>3776)) command_fault<=1;
    end
    assign fault=ef|command_fault;
    ot_dsrom_embed_row_reader #(.WORDS(320),.VIAMAP(VIAMAP),.ENABLE(1)) reader(
        .clk(clk),.rst_n(rst_n),.start(start),.base(base),.o_v(rv),.o_idx(ri),.o_d(rd),.busy(rb));
    ot_s81_embed_expand #(.MUTANT(MUTANT)) expand(
        .clk(clk),.rst_n(rst_n),.start(start),.header(header),.vm_base(vm_base),
        .rom_v(rv),.rom_idx(ri),.rom_d(rd),.busy(busy),.done(done),.fault(ef),
        .vm_v(vm_v),.vm_row(vm_row),.vm_d(vm_d),.hop_v(hop_v),.hop_last(hop_last),.hop_d(hop_d));
endmodule
