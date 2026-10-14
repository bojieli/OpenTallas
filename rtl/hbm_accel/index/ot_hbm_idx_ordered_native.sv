`default_nettype none
// Wires-only composition around byte-identical CLOSED native selector/scorers.
// The collector owns registered candidate publication and event join. The
// existing selector still quantises the query and computes exact top-k.
module ot_hbm_idx_ordered_native #(
    parameter integer MUT=0
)(
    input wire ck,rst,
    input wire [89:0] fs,
    input wire [1047:0] qb,
    output wire qbr,
    input wire [344:0] kin,
    output wire [2283:0] qo,
    input wire [2439:0] si,
    output wire [3:0] sc,
    output wire [611:0] to,
    input wire toc,
    output wire [71:0] co,
    input wire coc,
    output wire [1:0] ev,
    output wire co_quarter_last
);
    wire [89:0] topk_fs={fs[89],1'b0,fs[87:0]};
    wire [1:0] selector_ev;
    hfd_idx_sel_native_qend selector(
        .ck(ck),.rst(rst),.fs(topk_fs),.qb(qb),.qbr(qbr),.kin(kin),
        .qo(qo),.si(si),.sc(sc),.to(to),.toc(toc),.co(),.coc(1'b0),
        .ev(selector_ev),.co_quarter_last());
    ot_hbm_idx_ordered_candidate #(.MUT(MUT)) collector(
        .ck(ck),.rst(rst),.fs(fs),.si(si),.selector_ev(selector_ev),
        .co(co),.coc(coc),.ev(ev),.co_quarter_last(co_quarter_last));
endmodule
`default_nettype wire
