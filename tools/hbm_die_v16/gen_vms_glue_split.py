#!/usr/bin/env python3
"""STEWARD-HBMd/GLUE 2026-10-23 (coordinator tile review 10-23 #1: hfd_hgi_vms_glue_{sw,nw}_t = 648 x 1555 um, 21.4k
pins, ONE 100 x 150 um logic blob at 6% fill, one 107,776-sink clock root, TT insertion 979 ps, FF hold -60..-79 after
36-40k hold cells): SPLIT PER FACE of the g7 VM hub-glue tile into hardened children along the glue's OWN registered
seams.  Plan + numbers: lanes/STEWARD-HBM.md "[STEWARD-HBMd/GLUE 01:25] PLAN".
Writes rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_glue_split.sv:
  hfd_vmg_rs_t            ring stop child (ot_vms_rstop_lt + its own port stages): ONE master for all 8 stops of the
                          die (dir strap 0 = CW / 1 = CCW, sid strap); owns the ring faces of its direction and its
                          bank eject / egress faces (xq or xq2, xq_done or xq2_done, eg).
  hfd_vmg_hub_<k>_t       hub child (ot_vms_hub_lt + ot_vms_rcl_lt + ot_vms_status_static + the core seam relays
                          pi / ri (outputs) and cco / rce / ring-fault landings); owns the client, schedule-control,
                          bank request / response / status faces.  k = sw (NC 2), e (NC 0, sid strap), nw (NC 0, flt).
  hfd_hgi_vms_glue_<k>_s  ZERO-LOGIC soft parent (wiring only) with EXACTLY the port list of hfd_hgi_vms_glue_<k>_t
                          (gen_vms_glue_tiles.py): the die binds it as a split parent; no neighbour interface changes.
Cycle-exact by construction (no edge changes anywhere): every flop of the g7 tile exists in exactly one child with the
same D-input function; the only duplicates are the eg pin flop (one per stop, same input, same edge), the sid strap
relays and the reset landing + forest (one per child, same assertion / release timing: ot_vms_rst_forest leaves are
uniform).  Seams (child <-> child) are the existing flop -> flop relays of hfd_vms_glue_core_lt: pi0/pi1 and ri0/ri1
(HUB output flops -> stop stage A), cco / rce (stop output flops -> HUB landings cco*_r / rce*_r), stop fault flop ->
HUB rf_r, wko / ack_o (stop flops) -> the other stop's stage A.  Proof: vms_glue_split_equiv.py (lockstep _s vs the g7
tile _t and vs the contract ref _t_ref, every output bit every edge, periodic resets).
Parameter MUT (bench only, default 0): 1 ring-stop flit mutant (both stops, = tile MUT 1), 4 / 6 / 7 hub mutants
(= tile MUT 4 / 6 / 7), 5 pi / rce seam relays bypassed (= tile MUT 5), 9 split mutant: HUB drives the CW pi seam from
the hub directly and the replay takes the CW rce seam unlanded (seam relays pi0_r / rce0_r missing: contract break, must FAIL).
    gen_vms_glue_split.py [--check]
"""
import sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import gen_vms_glue_tiles as G  # noqa: E402

OUT = G.D / 'hfd_hgi_vms_glue_split.sv'
LANE = G.LANE
RS_UPPER = "8'b00111100"   # plan A lane bands; the NW instance is the MX of plan A (= plan B), UPPER is placement only
RS_NLS = 36
STOP_P = [('xq', 'output', 276), ('xq_done', 'input', 1), ('eg', 'input', 276)]


def rs_ports():
    p = [('clk', 'input', 1), ('rst_n', 'input', 1), ('sid', 'input', 2), ('dir', 'input', 1),
         ('tx_enable', 'input', 1), ('tx_source', 'input', 3)]
    p += [(f'l_in_l{b}', 'input', LANE) for b in range(8)] + [('l_in_h', 'input', 16)]
    p += [(f'l_out_l{b}', 'output', LANE) for b in range(8)] + [('l_out_h', 'output', 16)]
    for b in range(8):
        p += [(f'b{b}_{n}', d, wd) for n, d, wd in STOP_P]
    p += [('pi', 'input', 290), ('ri', 'input', 266), ('rce', 'output', 288), ('cco', 'output', 264),
          ('wko', 'output', 3), ('wki', 'input', 3), ('ack_o', 'output', 1), ('ack_i', 'input', 1),
          ('mirror_busy', 'output', 1), ('ring_fault', 'output', 1), ('fault_h', 'output', 1)]
    return p


def rs():
    L = ['module hfd_vmg_rs_t #(parameter integer MUT=0) (', G.decl(rs_ports()), ');']
    L.append('    // reset landing + forest (g6 timing: assertion +2, release +5 edges after the port), own copy per child')
    L.append('    reg rst_l0;')
    L.append('    always @(posedge clk) rst_l0 <= rst_n;')
    L.append(f'    wire [{RS_NLS - 1}:0] rl;')
    L.append(f'    ot_vms_rst_forest #(.NL({RS_NLS})) u_rst(.clk(clk),.rst_l0(rst_l0),.rl(rl));')
    last = G.chain(L, 'sid', 2, G.DC, 'sid_g')
    L.append(f'    wire [1:0] sid_c = {last};')
    L.append('    wire [2223:0] l_in = ' + G.cat(['l_in_h'] + [f'l_in_l{b}' for b in reversed(range(8))]) + ';')
    L.append('    wire [2223:0] l_out;')
    L += [f'    assign l_out_l{b} = l_out[{b * LANE + LANE - 1}:{b * LANE}];' for b in range(8)]
    L.append('    assign l_out_h = l_out[2223:2208];')
    # bank-side port stages (same depths as the g7 tile: xq DB, xq_done DD, eg DEPTH eg)
    L.append('    wire [2207:0] xq_c, xq_p;')
    last = G.chain(L, 'xq_c', 2208, G.bank_depth('xq'), 'bk_xq')
    L.append(f'    assign xq_p = {last};')
    L += [f'    assign b{b}_xq = xq_p[{b * 276 + 275}:{b * 276}];' for b in range(8)]
    L.append('    wire [7:0] xq_done_p = ' + G.cat([f'b{b}_xq_done' for b in reversed(range(8))]) + ';')
    last = G.chain(L, 'xq_done_p', 8, G.bank_depth('xq_done'), 'bk_xq_done')
    L.append(f'    wire [7:0] xq_done_c = {last};')
    L.append('    wire [2207:0] eg_p = ' + G.cat([f'b{b}_eg' for b in reversed(range(8))]) + ';')
    last = G.chain(L, 'eg_p', 2208, G.bank_depth('eg'), 'bk_eg')
    L.append(f'    wire [2207:0] eg_c = {last};')
    L.append('    wire mb_c, fl_c;')
    L.append('    ot_vms_rstop_lt #(.COMMIT_DELAY(%d),.MUT((MUT == 1) ? 1 : 0),.UPPER(%s),.NLS(%d)) u_stop(' % (G.COMMIT_DELAY, RS_UPPER, RS_NLS))
    L.append('        .clk(clk),.rl(rl),.sid(sid_c),.dir(dir),.tx_enable(tx_enable),.tx_source(tx_source),')
    L.append('        .l_in(l_in),.l_out(l_out),.pi(pi),.eg(eg_c),.xq(xq_c),.xq_done(xq_done_c),')
    L.append('        .rce(rce),.ri(ri),.wko(wko),.wki(wki),.cco(cco),')
    L.append('        .ack_o(ack_o),.ack_i(ack_i),.mirror_busy(mb_c),.fault(fl_c));')
    L.append('    assign fault_h = fl_c;   // stop fault flop -> HUB rf_r (status), register to register')
    last = G.chain(L, 'mb_c', 1, G.DC, 'mirror_busy_g')
    L.append(f'    assign mirror_busy = {last};')
    last = G.chain(L, 'fl_c', 1, G.DC, 'ring_fault_g')
    L.append(f'    assign ring_fault = {last};')
    L.append('endmodule')
    return '\n'.join(L) + '\n'


def hub_ports(k, c):
    p = [('clk', 'input', 1), ('rst_n', 'input', 1)]
    if c['sid'] == 'strap':
        p.append(('sid', 'input', 2))
    p += G.common(c)
    p += [(n, d, wd) for n, d, wd in G.RINGC if n in G.CLIENT_CTL]
    for b in range(8):
        p += [(f'b{b}_{n}', d, wd) for n, d, wd, _ in G.bankp(c) if n in ('pq', 'pr', 'status', 'flt')]
    p += [('hub_status', 'output', 3), ('vmstat', 'output', 19), ('ring_fault', 'output', 1)]
    p += [('pi0', 'output', 290), ('pi1', 'output', 290), ('ri0', 'output', 266), ('ri1', 'output', 266),
          ('cco0', 'input', 264), ('cco1', 'input', 264), ('rce0', 'input', 288), ('rce1', 'input', 288),
          ('fault0', 'input', 1), ('fault1', 'input', 1)]
    return p


def hub(k, c):
    nc = c['nc']; cw = G.cw_of(nc)
    L = [f'module hfd_vmg_hub_{k}_t #(parameter integer MUT=0) (', G.decl(hub_ports(k, c)), ');']
    L.append(f'    localparam integer NC={nc}, CW={cw}, NLH=3+14*(NC+1), NL=NLH+4;')
    L.append('    localparam integer RMUT=(MUT == 4) ? 4 : (MUT == 5) ? 5 : (MUT == 6) ? 6 : (MUT == 7) ? 7 : 0;')
    L.append('    reg rst_l0;')
    L.append('    always @(posedge clk) rst_l0 <= rst_n;')
    L.append('    wire [NL-1:0] rl;')
    L.append('    ot_vms_rst_forest #(.NL(NL)) u_rst(.clk(clk),.rst_l0(rst_l0),.rl(rl));')
    for n, d, wd, f in G.bankp(c):
        if n not in ('pq', 'pr', 'status', 'flt'):
            continue
        dep = G.bank_depth(n)
        L.append(f'    wire [{8 * wd - 1}:0] {f}_p, {f}_c;')
        if d == 'input':
            L.append(f'    assign {f}_p = ' + G.cat([f'b{b}_{n}' for b in reversed(range(8))]) + ';')
            last = G.chain(L, f'{f}_p', 8 * wd, dep, f)
            L.append(f'    assign {f}_c = {last};')
        else:
            last = G.chain(L, f'{f}_c', 8 * wd, dep, f)
            L.append(f'    assign {f}_p = {last};')
            L += [f'    assign b{b}_{n} = {f}_p[{b * wd + wd - 1}:{b * wd}];' for b in range(8)]
    for nm, wd in G.client_ins(c):
        last = G.chain(L, nm, wd, G.DC, f'{nm}_g')
        L.append(f'    wire {G.w(wd)}{nm}_c = {last};')
    for nm, wd in [(n, wd) for n, wd in G.client_outs(c) if n not in ('mirror_busy', 'ring_fault')]:
        L.append(f'    wire {G.w(wd)}{nm}_c;')
        last = G.chain(L, f'{nm}_c', wd, G.DC, f'{nm}_g')
        L.append(f'    assign {nm} = {last};')
    st = 'bank_status_c'
    if c['flt']:
        L.append('    // NW: the wq2-merge leaves (vmm_NWb) sticky flt -> bank status bit 17 (as hfd_hgi_vms_static_NW_glue)')
        L.append('    wire [143:0] bank_status_m;')
        L += [f'    assign bank_status_m[{b * 18 + 17}:{b * 18}] = {{bank_status_c[{b * 18 + 17}] | bk_flt_c[{b}], '
              f'bank_status_c[{b * 18 + 16}:{b * 18}]}};' for b in range(8)]
        st = 'bank_status_m'
    sid = 'sid_c' if c['sid'] == 'strap' else c['sid']
    # hfd_vms_glue_core_lt minus the two ring stops (they are the RS children): the same wiring and seam relays
    L.append('    wire [(NC+1)*338-1:0] hcq;')
    L.append('    wire [(NC+1)*274-1:0] hcr;')
    L.append('    wire [337:0] hq;')
    L.append('    wire [273:0] hr=hcr[NC*274+:274];')
    if nc:
        L.append('    assign hcq={hq,cq_c}; assign cr_c=hcr[NC*274-1:0];')
    else:
        L.append('    assign hcq=hq;')
    L.append('    wire [289:0] pi0_h,pi1_h;')
    L.append('    wire [265:0] ri0_h,ri1_h;')
    L.append('    wire rfault2;')
    L.append('    // seam relays (the core_lt g4 relays): pi / ri leave from these flops, cco / rce / stop faults land on them')
    L.append('    reg [289:0] pi0_r,pi1_r; reg [265:0] ri0_r,ri1_r; reg [263:0] cco0_r,cco1_r; reg [287:0] rce0_r,rce1_r; reg [2:0] rf_r;')
    L.append('    always @(posedge clk) begin')
    L.append('        pi0_r<=pi0_h; pi1_r<=pi1_h; ri0_r<=ri0_h; ri1_r<=ri1_h; cco0_r<=cco0; cco1_r<=cco1; rce0_r<=rce0; rce1_r<=rce1;')
    L.append('        rf_r<={rfault2,fault1,fault0};')
    L.append('    end')
    L.append('    assign pi0=(RMUT == 5 || MUT == 9) ? pi0_h : pi0_r;')
    L.append('    assign pi1=(RMUT == 5) ? pi1_h : pi1_r;')
    L.append('    assign ri0=ri0_r; assign ri1=ri1_r;')
    L.append('    wire [287:0] rce0_s=(RMUT == 5 || MUT == 9) ? rce0 : rce0_r, rce1_s=(RMUT == 5) ? rce1 : rce1_r;')
    L.append('    wire [2:0] hub_status_w;')
    L.append('    assign hub_status_c=hub_status_w;')
    L.append('    ot_vms_hub_lt #(.NC(NC),.CW(CW),.MUT(RMUT),.NLH(NLH)) u_hub(')
    L.append(f'        .clk(clk),.rl(rl[0+:NLH]),.sid({sid}),.cq(hcq),.cr(hcr),')
    L.append('        .client_seq(client_seq_c),.response_enable(response_enable_c),.response_seq(response_seq_c),')
    L.append('        .bank_enable(bank_enable_c),.bank_client(bank_client_c),')
    L.append('        .cw_enable(hub_ring_enable_c[0]),.cw_client(hub_ring_client_c[0+:CW]),')
    L.append('        .ccw_enable(hub_ring_enable_c[1]),.ccw_client(hub_ring_client_c[CW+:CW]),')
    L.append('        .pq(bk_pq_c),.pr(bk_pr_c),.cwi(pi0_h),.cci(pi1_h),.cco0(cco0_r),.cco1(cco1_r),.status(hub_status_w));')
    L.append(f'    ot_vms_rcl_lt u_replay(.clk(clk),.rl(rl[NLH+:3]),.sid({sid}),')
    L.append('        .rx_enable(replay_enable_c),.rx_source(replay_source_c),.rce0(rce0_s),.rce1(rce1_s),')
    L.append('        .hq(hq),.hr(hr),.ri0(ri0_h),.ri1(ri1_h),.fault(rfault2));')
    L.append(f'    ot_vms_status_static u_status(.clk(clk),.rst_n(rl[NLH+3]),')
    L.append(f'        .bank_status({st}),.hub_status(hub_status_w),.ring_fault(|rf_r),.vmstat(vmstat_c));')
    last = G.chain(L, 'rfault2', 1, G.DC, 'ring_fault_g')
    L.append(f'    assign ring_fault = {last};')
    L.append('endmodule')
    return '\n'.join(L) + '\n'


def parent(k, c):
    p = G.ports(k, c)
    L = [f'module hfd_hgi_vms_glue_{k}_s #(parameter integer MUT=0) (', G.decl(p), ');']
    L.append('    // zero-logic soft parent: wiring of the RS (CW, CCW) and HUB children only')
    sid = 'sid' if c['sid'] == 'strap' else c['sid']
    L.append('    wire [289:0] pi0,pi1; wire [265:0] ri0,ri1; wire [263:0] cco0,cco1; wire [287:0] rce0,rce1;')
    L.append('    wire [2:0] wk01,wk10; wire ack01,ack10, f0,f1;')
    for i, (rn, ring_in, ring_out, xq, done) in enumerate((('u_rs_cw', 'cw_in', 'cw_out', 'xq', 'xq_done'),
                                                         ('u_rs_ccw', 'ccw_in', 'ccw_out', 'xq2', 'xq2_done'))):
        conn = ['.clk(clk)', '.rst_n(rst_n)', f'.sid({sid})', f".dir(1'b{i})",
                f'.tx_enable(ring_tx_enable[{i}])', f'.tx_source(ring_tx_source[{3 * i + 2}:{3 * i}])']
        conn += [f'.l_in_l{b}({ring_in}_l{b})' for b in range(8)] + [f'.l_in_h({ring_in}_h)']
        conn += [f'.l_out_l{b}({ring_out}_l{b})' for b in range(8)] + [f'.l_out_h({ring_out}_h)']
        for b in range(8):
            conn += [f'.b{b}_xq(b{b}_{xq})', f'.b{b}_xq_done(b{b}_{done})', f'.b{b}_eg(b{b}_eg)']
        conn += [f'.pi(pi{i})', f'.ri(ri{i})', f'.rce(rce{i})', f'.cco(cco{i})',
                 f'.wko({"wk01" if i == 0 else "wk10"})', f'.wki({"wk10" if i == 0 else "wk01"})',
                 f'.ack_o({"ack01" if i == 0 else "ack10"})', f'.ack_i({"ack10" if i == 0 else "ack01"})',
                 f'.mirror_busy(mirror_busy[{i}])', f'.ring_fault(ring_fault[{i}])', f'.fault_h(f{i})']
        L.append(f'    hfd_vmg_rs_t #(.MUT((MUT == 1) ? 1 : 0)) {rn} (\n        ' + ',\n        '.join(conn) + ');')
    conn = ['.clk(clk)', '.rst_n(rst_n)'] + (['.sid(sid)'] if c['sid'] == 'strap' else [])
    conn += [f'.{nm}({nm})' for nm, _, _ in G.common(c)]
    conn += [f'.{n}({n})' for n in G.CLIENT_CTL]
    for b in range(8):
        conn += [f'.b{b}_{n}(b{b}_{n})' for n, _, _, _ in G.bankp(c) if n in ('pq', 'pr', 'status', 'flt')]
    conn += ['.hub_status(hub_status)', '.vmstat(vmstat)', '.ring_fault(ring_fault[2])',
             '.pi0(pi0)', '.pi1(pi1)', '.ri0(ri0)', '.ri1(ri1)', '.cco0(cco0)', '.cco1(cco1)', '.rce0(rce0)',
             '.rce1(rce1)', '.fault0(f0)', '.fault1(f1)']
    L.append(f'    hfd_vmg_hub_{k}_t #(.MUT((MUT == 1) ? 0 : MUT)) u_hub (\n        ' + ',\n        '.join(conn) + ');')
    L.append('endmodule')
    return '\n'.join(L) + '\n'


def build():
    hdr = ['`timescale 1ns/1ps', '`default_nettype none',
           '// GENERATED by tools/hbm_die_v16/gen_vms_glue_split.py (do not edit): VM hub-glue split per face (RS + HUB',
           '// children under a zero-logic soft parent with the g7 tile port list).'] + \
          ['// ' + x for x in __doc__.strip().split('\n')[:-1]]
    body = [rs()] + [hub(k, c) for k, c in G.M.items()] + [parent(k, c) for k, c in G.M.items()]
    return '\n'.join(hdr) + '\n' + '\n'.join(body) + '`default_nettype wire\n'


def main():
    t = build()
    if '--check' in sys.argv:
        ok = OUT.exists() and OUT.read_text() == t
        print('gen_vms_glue_split', 'UP-TO-DATE' if ok else 'STALE', OUT.relative_to(G.ROOT))
        return 0 if ok else 1
    OUT.write_text(t)
    print('wrote', OUT.relative_to(G.ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
