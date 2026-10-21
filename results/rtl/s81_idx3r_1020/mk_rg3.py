import sys, re
src = open(sys.argv[1]).read()
lines = src.split('\n')
# body of module dsdv_idx_rg2 only (line 44 .. first endmodule)
start = next(i for i, l in enumerate(lines) if l.startswith('module dsdv_idx_rg2 #('))
end = next(i for i, l in enumerate(lines) if i > start and l.startswith('endmodule'))
body = '\n'.join(lines[start:end + 1])

def rep(old, new, cnt=1):
    global body
    n = body.count(old)
    if n != cnt:
        raise SystemExit('pattern count %d != %d: %r' % (n, cnt, old[:80]))
    body = body.replace(old, new)

def rep_between(a, b, new):
    """replace text from the line holding a (inclusive) to the line holding b (exclusive)"""
    global body
    i = body.index(a); i = body.rindex('\n', 0, i) + 1
    j = body.index(b, i); j = body.rindex('\n', 0, j) + 1
    body = body[:i] + new + body[j:]

rep('module dsdv_idx_rg2 #(', 'module dsdv_idx_rg3 #(')
rep('    parameter integer DQ = 8,           // controller request buffer entries a PC (dsfd_ctrl_rg2 DQ, <= 8)\n',
    '    parameter integer DQR = 24,         // outstanding requests a PC lane: dsfd_ctrl_rg3 RFD (reader landing FIFO)\n')
rep('''    input  wire [681:0]  rqi0,
    output reg  [681:0]  rqo0,
    input  wire [561:0]  rdi0,
    output reg  [561:0]  rdo0,
    input  wire [681:0]  rqi1,
    output reg  [681:0]  rqo1,
    input  wire [561:0]  rdi1,
    output reg  [561:0]  rdo1,
''', '''    output reg  [183:0]  rqo,           // 4 x 46-b request lanes, u = 2 r + q: {tag10, len 4, addr 30, sl, v}
    input  wire [1087:0] rri,           // 4 x 272-b response lanes, u = 2 r + q: {data 256, tag10, beat 4, pop, v}
''')
rep('''    initial if (IQD > 1024 || SQD > 1024 || LFD > 1024 || DQ > 8) $fatal(1, "dsdv_idx_rg2: queue / owner sizes");''',
    '''    initial if (IQD > 1024 || SQD > 1024 || LFD > 1024 || DQR > 31 || DQR < 1) $fatal(1, "dsdv_idx_rg3: queue / budget sizes");
    localparam integer OW = 6;          // own_n width (DQR <= 31)''')

# ---------------- pin registers
rep_between('    reg [1:0][681:0] rqr;', '    // ================================================================== frame parser (query chain)', '''    reg [3:0][271:0] rrr;                           // response lanes at the pin
    always @(posedge ck or negedge rl[0])
        if (!rl[0]) begin qr[0] <= 1'b0; sr[0] <= 1'b0; end
        else begin qr[0] <= qi[0]; sr[0] <= si[0]; end
    always @(posedge ck or negedge rl[1])
        if (!rl[1]) begin rrr[0][1:0] <= 2'd0; rrr[1][1:0] <= 2'd0; rrr[2][1:0] <= 2'd0; rrr[3][1:0] <= 2'd0; end
        else begin
            rrr[0][1:0] <= rri[1:0]; rrr[1][1:0] <= rri[273:272]; rrr[2][1:0] <= rri[545:544]; rrr[3][1:0] <= rri[817:816];
        end
    always @(posedge ck) begin
        qr[512:1] <= qi[512:1]; sr[275:1] <= si[275:1];
        rrr[0][271:2] <= rri[271:2]; rrr[1][271:2] <= rri[543:274]; rrr[2][271:2] <= rri[815:546]; rrr[3][271:2] <= rri[1087:818];
    end
    // pin copies: pop (budget counter + copies), query valid (payload counters)
    (* keep = "true" *) reg [3:0]  rkc;
    (* keep = "true" *) reg [1:0]  qvk;
    always @(posedge ck) begin
        rkc <= {rri[817], rri[545], rri[273], rri[1]};
        qvk <= {2{qi[0]}};
    end
    wire [3:0] rk_in = {rrr[3][1], rrr[2][1], rrr[1][1], rrr[0][1]};   // a request left the controller's landing FIFO
    wire [3:0] rv_in = {rrr[3][0], rrr[2][0], rrr[1][0], rrr[0][0]};
    wire [3:0][16:0] rt;
    wire [3:0][3:0]  rb;
    wire [3:0][255:0] rdd;
    genvar gu;
    generate for (gu = 0; gu < 4; gu = gu + 1) begin : g_rdw
        assign rt[gu]  = {2'b11, rrr[gu][15:6], 5'd0};   // the controller's reader-tag range: {11, tag10, 00000}
        assign rb[gu]  = rrr[gu][5:2];
        assign rdd[gu] = rrr[gu][271:16];
    end endgenerate
    // every lane response is this reader's (the controller's tag demux); MUT 5: responses of tag bit 0 of cell lost
    wire [3:0] mine;
    generate for (gu = 0; gu < 4; gu = gu + 1) begin : g_mine
        assign mine[gu] = rv_in[gu] && !(MUT == 5 && rt[gu][7]);
    end endgenerate

''')

# ---------------- issuers / budget (replace owner FIFOs and rq/rd pass-through)
rep('''    (* keep = "true" *) reg [3:0] ivk0, ivk1, ivk2, ivk3, ivk4;   // i_v copies [copy][u]
    (* keep = "true" *) reg [3:0] cnk0, cnk1, cnk2, cnk3, cnk4;   // own_n < DQ copies''',
'''    (* keep = "true" *) reg [3:0] ivk0, ivk3, ivk4;   // i_v copies [copy][u]
    (* keep = "true" *) reg [3:0] cnk0, cnk3, cnk4;   // own_n < DQR copies''')
rep('''    reg  [3:0][7:0]     own;                        // owner bits (1 = this reader), circular
    reg  [3:0][7:0]     owp, orp;                   // write / read pointers (one-hot)
    reg  [3:0][4:0]     own_n;
    // issue: this reader's request leaves (no slice request this edge, controller room); one copy a consumer group
    wire [3:0] is0 = ivk0 & cnk0 & {~avc[3][0], ~avc[2][0], ~avc[1][0], ~avc[0][0]};   // rq valid, own_n
    wire [3:0] is1 = ivk1 & cnk1 & {~avc[3][1], ~avc[2][1], ~avc[1][1], ~avc[0][1]};   // owner write pointer
    wire [3:0] is2 = ivk2 & cnk2 & {~avc[3][2], ~avc[2][2], ~avc[1][2], ~avc[0][2]};   // owner entry writes
    wire [3:0] is3 = ivk3 & cnk3 & {~avc[3][3], ~avc[2][3], ~avc[1][3], ~avc[0][3]};   // issuer advance (k, count)
    wire [3:0] is4 = ivk4 & cnk4 & {~avc[3][4], ~avc[2][4], ~avc[1][4], ~avc[0][4]};   // head read pointers''',
'''    reg  [3:0][OW-1:0]  own_n;                      // requests issued on the lane and not yet popped at the controller
    // issue: a request leaves on its own lane (no slice word to share the lane with: the controller merges the lanes
    // into its PCs in the static reader slots), within the budget; one copy a consumer group.  MUT 2: budget ignored.
    wire [3:0] cb0 = (MUT == 2) ? 4'hF : cnk0, cb3 = (MUT == 2) ? 4'hF : cnk3, cb4 = (MUT == 2) ? 4'hF : cnk4;
    wire [3:0] is0 = ivk0 & cb0;                    // rq valid, own_n
    wire [3:0] is3 = ivk3 & cb3;                    // issuer advance (k, count)
    wire [3:0] is4 = ivk4 & cb4;                    // head read pointers''')
rep('''            ivk0 <= nz & ~is0; ivk1 <= nz & ~is1; ivk2 <= nz & ~is2; ivk3 <= nz & ~is3; ivk4 <= nz & ~is4;''',
    '''            ivk0 <= nz & ~is0; ivk3 <= nz & ~is3; ivk4 <= nz & ~is4;''')
rep('''        if (!rl[4]) begin ivk0 <= 4'd0; ivk1 <= 4'd0; ivk2 <= 4'd0; ivk3 <= 4'd0; ivk4 <= 4'd0; end''',
    '''        if (!rl[4]) begin ivk0 <= 4'd0; ivk3 <= 4'd0; ivk4 <= 4'd0; end''')
rep_between('        // owner FIFO (8 entries, circular, one-hot pointers): a push is the slice\'s request or this reader\'s',
            '    // ================================================================== slot table (per parity q, shared by A and B)',
'''        // budget: own_n = issued - popped (the pop returns on the response lane, after the fixed round trip, so own_n
        // >= the controller landing FIFO's occupancy for this lane: the FIFO can never overflow)
        always @(posedge ck or negedge rl[9 + gu])
            if (!rl[9 + gu]) own_n[gu] <= '0;
            else own_n[gu] <= own_n[gu] + (is0[gu] ? OW'(1) : OW'(0)) - (rkc[gu] ? OW'(1) : OW'(0));
        always @(posedge ck or negedge rl[13 + gu / 2])
            if (!rl[13 + gu / 2]) begin cnk0[gu] <= 1'b1; cnk3[gu] <= 1'b1; cnk4[gu] <= 1'b1; end
            else begin : g_cn
                reg [OW-1:0] nx;
                nx = own_n[gu] + (is0[gu] ? OW'(1) : OW'(0)) - (rk_in[gu] ? OW'(1) : OW'(0));
                cnk0[gu] <= nx < OW'(DQR); cnk3[gu] <= nx < OW'(DQR); cnk4[gu] <= nx < OW'(DQR);
            end
    end endgenerate
    // request lanes out: {tag10, len, addr, sl, v}; sl = the reader's window (job active: header -> window done),
    // the compiled reader slot calendar of the controller (svc_rs never issues on the pair's PCs inside it)
    (* keep = "true" *) reg [3:0] slk;
    always @(posedge ck or negedge rl[15])
        if (!rl[15]) slk <= 4'd0; else slk <= {4{act}};
    always @(posedge ck or negedge rl[15])
        if (!rl[15]) begin rqo[0] <= 1'b0; rqo[46] <= 1'b0; rqo[92] <= 1'b0; rqo[138] <= 1'b0; end
        else begin rqo[0] <= is0[0]; rqo[46] <= is0[1]; rqo[92] <= is0[2]; rqo[138] <= is0[3]; end
    always @(posedge ck) for (u = 0; u < 4; u = u + 1) begin
        rqo[46 * u + 1] <= slk[u];
        rqo[46 * u + 2 +: 44] <= {i_t[u][14:5], i_l[u], i_a[u]};
    end

''')
# fault checks
rep('''                if (rk_in[u] && own_n[u] == 0) fw[1] <= 1'b1;                      // rk with no request
                if (own_n[u] > 5'd8) fw[1] <= 1'b1;                                // owner FIFO overflow''',
    '''                if (rk_in[u] && own_n[u] == 0) fw[1] <= 1'b1;                      // pop with no request
                if (own_n[u] > OW'(DQR)) fw[1] <= 1'b1;                            // budget overflow''')
hdr = open(sys.argv[3]).read()
out = hdr + body + '\n'
open(sys.argv[2], 'w').write(out)
# sanity: no leftover inline names
for w in ['rqr', 'rdr', 'avc', 'avs', 'avk', 'rdo', 'rqi', 'rdi', 'own_h', 'owp', 'is1', 'is2']:
    if re.search(r'\b' + w + r'\b', body): print('LEFTOVER', w, [m.start() for m in re.finditer(r'\b'+w+r'\b', body)][:3])
