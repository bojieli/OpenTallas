#!/usr/bin/env python3
"""CLAUDE HBM-ABSTRACTS (svcidx): SEGMENT SPLIT of the r16g index-quarter master hfd_index_q (coordinator DECISION
2026-10-06: the 930 x 5530 um slot with ONE ck pin at its top-right corner measured 5.46-6.22 ns clock insertion and
758 ps skew post-CTS, so no IO budget can close it; split into ~1 mm bands, each a normal hardened block with its own
ck pin and registered faces, joined by registered pin-to-pin hops across the shared edges).

Writes
  split_spec.json                        -> python3 tools/hbm_die_split.py --spec ... (split/<band>/ports.json, split.json)
  rtl/split/hfd_index_q_b<k>.sv           one module per band (b0 bottom .. b5 top)
  rtl/split/hfd_index_q_seg.sv            the six bands joined, same ports as hfd_index_q (bench vehicle)
  split_stages.json                       per-band chain depths and the added-cycle ledger

Bands carry the INTERIM index-quarter function unchanged (attention rows -> two SU lanes; forwarded keys -> placeholder
t_vm): a0 (b0) and a1 (b2) -> lane 0, a2 (b3) and a3 (b5) -> lane 1, merge + t_su in b2; k (b0) -> CDC -> kf -> t_vm
(b5).  Every chain is ot_svc_vpipe; a chain stage at a band face is the face register (no logic between pin and flop).
Depths: hop <= HOP um (Manhattan, pin to pin), common/wire_stage_fence.tcl places the stages (anchored at the face pins).
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HOP = 350.0
W_UM, H_UM = 930.072, 5529.576
# band y0 (um, parent coordinates); a band ends 0.024 um below the next one
Y0 = [0.0, 970.08, 1940.16, 2900.16, 3870.24, 4700.16]
H = [round((Y0[i + 1] if i + 1 < len(Y0) else H_UM + 0.024) - Y0[i] - 0.024, 4) for i in range(len(Y0))]
NAMES = [f'hfd_index_q_b{i}' for i in range(len(Y0))]
TR = 0.192
# cross-bus first-pin x (um) on the shared edges
X_A0, X_A3, X_A2, X_CK, X_K = 100.032, 250.08, 400.128, 520.032, 600.0
PAR = {  # parent pin centroids (um, parent coordinates)
    'k': (130.4, 0.0), 'a0': (0.0, 674.9), 'a1': (0.0, 2068.1), 'a2': (0.0, 3461.3), 'a3': (0.0, 4854.5),
    't_su': (930.0, 2764.7), 't_vm': (930.0, 5479.7)}


# views agent 2026-10-07: hbm_idxq_b1_e8b5132fb_r18b SS -75.99 (a0i -> first a0 stage) / -75.70 (kin -> first kp stage),
# 13 levels of wire buffers between the input pin and the first chain register: +2 stages on both b1 chains
EXTRA = {'b1.kp': 2, 'b1.a0': 2}


def hops(d):
    return max(1, math.ceil(d / HOP))


def bus_c(x0, bits):
    return x0 + (bits - 1) * TR / 2


def plan():
    xk, xa0, xa3, xa2 = bus_c(X_K, 513), bus_c(X_A0, 529), bus_c(X_A3, 529), bus_c(X_A2, 529)
    st = {}
    # K: b0 chain (end anchored at the top face, starts after kf at the CDC FIFOs by the k pins)
    st['b0.kp'] = hops(abs(xk - PAR['k'][0]) + H[0])
    for i in (1, 2, 3, 4):                                   # pass-through: anchored both ends, hops = N - 1
        st[f'b{i}.kp'] = hops(H[i]) + 1
    st['b5.kp'] = hops(abs(PAR['t_vm'][0] - xk) + (PAR['t_vm'][1] - Y0[5]))     # anchored start, then vm at t_vm
    # a0: b0 (pin -> top face), b1 pass, b2 (bottom face -> FIFO -> lane register at t_su: 2 extra hops)
    st['b0.a0'] = hops(abs(xa0 - 0) + (H[0] - PAR['a0'][1])) + 1
    st['b1.a0'] = hops(H[1]) + 1
    tsu_y = PAR['t_su'][1] - Y0[2]
    st['b2.r0'] = max(1, hops(abs(930 - xa0) + tsu_y) - 1)
    st['b2.r1'] = max(1, hops(930 + abs(tsu_y - (PAR['a1'][1] - Y0[2]))) - 1)
    st['b2.r2'] = max(1, hops(abs(930 - xa2) + (H[2] - tsu_y)) - 1)
    st['b2.r3'] = max(1, hops(abs(930 - xa3) + (H[2] - tsu_y)) - 1)
    st['b3.a2'] = hops(xa2 + (PAR['a2'][1] - Y0[3])) + 1
    st['b3.a3'] = hops(H[3]) + 1
    st['b4.a3'] = hops(H[4]) + 1
    st['b5.a3'] = hops(xa3 + (PAR['a3'][1] - Y0[5])) + 1
    for k, e in EXTRA.items():                               # fail-fast extra stages (views agent, measured misses)
        st[k] += e
    return st


def spec():
    ck = lambda edge: [  # noqa: E731
        {"port": "ck", "bits": 1, "direction": "input", "edge": edge, "x0": X_CK, "role": "die clock leaf (new die net)"},
        {"port": "rst", "bits": 1, "direction": "input", "edge": edge, "x0": round(X_CK + 2 * TR, 4),
         "role": "die reset (same die net as hfd_index_q rst)"}]

    def bus(port, bits, d, edge, x0, role):
        return {"port": port, "bits": bits, "direction": d, "edge": edge, "x0": x0, "role": role}
    K = lambda d, e: bus('kin' if d == 'input' else 'kout', 513, d, e, X_K, 'key chain {data512, valid}')  # noqa: E731
    bands = [
        dict(name=NAMES[0], y0=Y0[0], h=H[0], ports=['k', 'a0'],
             new=ck('top') + [K('output', 'top'), bus('a0o', 529, 'output', 'top', X_A0, 'a0 row to b1')]),
        dict(name=NAMES[1], y0=Y0[1], h=H[1], ports=[],
             new=ck('bottom') + [K('input', 'bottom'), K('output', 'top'),
                                 bus('a0i', 529, 'input', 'bottom', X_A0, 'a0 row from b0'),
                                 bus('a0o', 529, 'output', 'top', X_A0, 'a0 row to b2')]),
        dict(name=NAMES[2], y0=Y0[2], h=H[2], ports=['a1', 't_su'],
             new=ck('bottom') + [K('input', 'bottom'), K('output', 'top'),
                                 bus('a0i', 529, 'input', 'bottom', X_A0, 'a0 row from b1'),
                                 bus('a3i', 529, 'input', 'top', X_A3, 'a3 row from b3'),
                                 bus('a2i', 529, 'input', 'top', X_A2, 'a2 row from b3')]),
        dict(name=NAMES[3], y0=Y0[3], h=H[3], ports=['a2'],
             new=ck('bottom') + [K('input', 'bottom'), K('output', 'top'),
                                 bus('a3o', 529, 'output', 'bottom', X_A3, 'a3 row to b2'),
                                 bus('a2o', 529, 'output', 'bottom', X_A2, 'a2 row to b2'),
                                 bus('a3i', 529, 'input', 'top', X_A3, 'a3 row from b4')]),
        dict(name=NAMES[4], y0=Y0[4], h=H[4], ports=[],
             new=ck('bottom') + [K('input', 'bottom'), K('output', 'top'),
                                 bus('a3o', 529, 'output', 'bottom', X_A3, 'a3 row to b3'),
                                 bus('a3i', 529, 'input', 'top', X_A3, 'a3 row from b5')]),
        dict(name=NAMES[5], y0=Y0[5], h=H[5], ports=['a3', 'ck', 'rst', 't_vm'],
             new=[K('input', 'bottom'), bus('a3o', 529, 'output', 'bottom', X_A3, 'a3 row to b4')]),
    ]
    cross = []
    for i in range(5):
        cross.append({"from": f"{NAMES[i]}.kout", "to": f"{NAMES[i+1]}.kin", "bits": 513, "carries": "key chain"})
    cross += [{"from": f"{NAMES[0]}.a0o", "to": f"{NAMES[1]}.a0i", "bits": 529, "carries": "hfd_index_q a0 row"},
              {"from": f"{NAMES[1]}.a0o", "to": f"{NAMES[2]}.a0i", "bits": 529, "carries": "hfd_index_q a0 row"},
              {"from": f"{NAMES[5]}.a3o", "to": f"{NAMES[4]}.a3i", "bits": 529, "carries": "hfd_index_q a3 row"},
              {"from": f"{NAMES[4]}.a3o", "to": f"{NAMES[3]}.a3i", "bits": 529, "carries": "hfd_index_q a3 row"},
              {"from": f"{NAMES[3]}.a3o", "to": f"{NAMES[2]}.a3i", "bits": 529, "carries": "hfd_index_q a3 row"},
              {"from": f"{NAMES[3]}.a2o", "to": f"{NAMES[2]}.a2i", "bits": 529, "carries": "hfd_index_q a2 row"}]
    return {"parent": "hfd_index_q", "out": "physical/hbm_accel_die_views/index_q/split",
            "note": ("index_q SEGMENT SPLIT (coordinator DECISION 2026-10-06; one-pin slot measured 5.46-6.22 ns "
                     "insertion / 758 ps skew): six bands b0 (bottom) .. b5 (top), each with its own ck / rst (b0-b4 new "
                     "die clock leaves on the bottom (b0: top) edge at x 520, b5 keeps the parent ck / rst); cross buses "
                     "abut on the shared edges (zero-length die nets): key chain kout -> kin up every boundary, a0 row "
                     "b0 -> b1 -> b2, a3 row b5 -> b4 -> b3 -> b2, a2 row b3 -> b2. Gap 0.024 um between bands."),
            "bands": bands, "cross": cross,
            "die_nets": [f"{n}.ck <- die clock leaf" for n in NAMES[:5]] +
                        [f"{n}.rst <- die reset (net of hfd_index_q.rst)" for n in NAMES[:5]]}


HDR = """`timescale 1ps/1fs
`default_nettype none
// GENERATED by physical/hbm_accel_die_views/index_q/gen_split.py (CLAUDE HBM-ABSTRACTS svcidx, segment split of the
// INTERIM index-quarter view hfd_index_q; NOT the indexer).  Every die input lands in a chain's first (face) register,
// every die output leaves a chain's last register or a pin register; each band synchronises its own reset.
"""


def rsync():
    # the synchroniser is named rst_s so the io_vclk SDC's reset-release multicycle (rst_mcp2: release reaches every
    # flop within 2 cycles; the die holds rst >= 3 cycles and sends no valid within 2 cycles of release) applies to
    # the band's own release net (s1_b5: rs2 -> u_a3 valid recovery -89 ps at 770 across the 830 um band)
    return ("  wire c = ck[0];\n  reg [1:0] rst_s;\n"
            "  always @(posedge c or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};\n"
            "  wire rn = rst_s[1];\n")


def rsync_regions(regions):
    # safe-hbm 2026-10-08 (REVIEW_20261008 C3, S-C3): hfd_index_q_b2 failed TT -192.9 on rst_s[1] -> u_r3.gn.rv[1]
    # (one synchroniser's release net across the band).  The synchroniser is replicated per region: every region
    # gets its own 2-flop rst_s from the raw rst pin (asynchronous assert, release 2 edges after rst rises exactly as
    # the shared one), placed beside the flops it releases.  0 cycles; every flop is released on the same edge.
    t = "  wire c = ck[0];\n"
    for r in regions:
        t += (f"  reg [1:0] rst_s_{r};\n"
              f"  always @(posedge c or negedge rst[0]) if (!rst[0]) rst_s_{r} <= 2'b00; else rst_s_{r} <= {{rst_s_{r}[0], 1'b1}};\n"
              f"  wire rn_{r} = rst_s_{r}[1];\n")
    return t


def pipe(name, w, n, vin, din, qv, q):
    return (f"  wire {qv}; wire [{w-1}:0] {q};\n"
            f"  ot_svc_vpipe #(.W({w}), .N({n})) {name} (.ck(c), .rst_n(rn), .v({vin}), .d({din}), .qv({qv}), .q({q}));\n")


def band_rtl(st):
    m = {}
    # ---- b0: keys (CDC) + a0
    m[NAMES[0]] = HDR + f"""module {NAMES[0]} (
    input wire [528:0] a0, input wire [0:0] ck, input wire [1025:0] k, input wire [0:0] rst,
    output wire [512:0] kout, output wire [528:0] a0o);
{rsync()}  // forwarded keys: capture on the forwarded clock's falling edge at the pin, two-clock FIFOs (8 deep), kf
  wire [511:0] kh [0:1]; wire [1:0] ke;
  genvar g;
  generate for (g = 0; g < 2; g = g + 1) begin : gk
    wire full_; wire [2:0] fr_;
    wire wck = ~k[1024+g];
    reg [511:0] kc;
    always @(posedge wck) kc <= k[g*512 +: 512];
    ot_hbm_accel_cdc_fifo #(.W(512), .AW(3)) u_x (.wclk(wck), .wrst_n(rst[0]), .we(1'b1),
      .wdata(kc), .full(full_), .rd_freed(fr_), .rclk(c), .rrst_n(rn), .re(1'b1), .rdata(kh[g]),
      .empty(ke[g]));
  end endgenerate
  // FIFO readouts registered at each FIFO before the XOR (margin rule; s2_b0: 8:1 read mux + XOR across the two
  // FIFOs -118 ps at 770): +1 key cycle
  reg kv0, kv; reg [511:0] kr0, kr1, kf;
  always @(posedge c or negedge rn) if (!rn) begin kv0 <= 1'b0; kv <= 1'b0; end else begin kv0 <= !ke[0] && !ke[1]; kv <= kv0; end
  always @(posedge c) begin kr0 <= kh[0]; kr1 <= kh[1]; kf <= kr0 ^ kr1; end
{pipe('u_kp', 512, st['b0.kp'], 'kv', 'kf', 'kpv', 'kpq')}  assign kout = {{kpq, kpv}};
{pipe('u_a0', 528, st['b0.a0'], 'a0[0]', 'a0[528:1]', 'a0v', 'a0q')}  assign a0o = {{a0q, a0v}};
endmodule
`default_nettype wire
"""
    # ---- b1, b4, b3: pass-throughs
    def passthru(name, buses, extra_ports='', body=''):
        ports = ['input wire [0:0] ck', 'input wire [0:0] rst', 'input wire [512:0] kin', 'output wire [512:0] kout']
        txt = ''
        for (pi, po, w, n, inst) in buses:
            ports += [f'input wire [{w}:0] {pi}', f'output wire [{w}:0] {po}']
            txt += pipe(inst, w, n, f'{pi}[0]', f'{pi}[{w}:1]', f'{inst}_v', f'{inst}_q') + \
                f"  assign {po} = {{{inst}_q, {inst}_v}};\n"
        return HDR + f"module {name} (\n    " + ',\n    '.join(ports + ([extra_ports] if extra_ports else [])) + \
            ");\n" + rsync() + pipe('u_kp', 512, st[f'b{name[-1]}.kp'], 'kin[0]', 'kin[512:1]', 'kpv', 'kpq') + \
            "  assign kout = {kpq, kpv};\n" + txt + body + "endmodule\n`default_nettype wire\n"
    m[NAMES[1]] = passthru(NAMES[1], [('a0i', 'a0o', 528, st['b1.a0'], 'u_a0')])
    m[NAMES[4]] = passthru(NAMES[4], [('a3i', 'a3o', 528, st['b4.a3'], 'u_a3')])
    m[NAMES[3]] = passthru(NAMES[3], [('a3i', 'a3o', 528, st['b3.a3'], 'u_a3')], 'input wire [528:0] a2,\n    output wire [528:0] a2o',
                           pipe('u_a2', 528, st['b3.a2'], 'a2[0]', 'a2[528:1]', 'a2v', 'a2q') + "  assign a2o = {a2q, a2v};\n")
    # ---- b2: rows -> FIFOs -> two lanes (t_su); key pass-through
    rows = [('a0i', st['b2.r0']), ('a1', st['b2.r1']), ('a2i', st['b2.r2']), ('a3i', st['b2.r3'])]
    body = "  wire [3:0] sv, ne; wire [527:0] sd [0:3], fd [0:3]; wire [1:0] lv; wire [527:0] ld [0:1];\n" \
           "  reg [1:0] last; wire [3:0] take;\n"
    for r, (p, n) in enumerate(rows):
        body += f"  ot_svc_vpipe #(.W(528), .N({n})) u_r{r} (.ck(c), .rst_n(rn_r{r}), .v({p}[0]), .d({p}[528:1]), .qv(sv[{r}]), .q(sd[{r}]));\n"
    body += """  wire [3:0] rn_f = {rn_r3, rn_r2, rn_r1, rn_r0};   // each row's FIFO shares its row's synchroniser
  wire [1:0] rn_l = {rn_l1, rn_l0};
  genvar g;
  generate for (g = 0; g < 4; g = g + 1) begin : gr
    wire rdy_;
    ot_svc_fifo #(.W(528), .AW(2), .AF(0)) u_f (.ck(c), .rst_n(rn_f[g]), .we(sv[g]), .wd(sd[g]), .rdy(rdy_),
      .re(take[g]), .rd(fd[g]), .ne(ne[g]));
  end endgenerate
  generate for (g = 0; g < 2; g = g + 1) begin : gl
    wire pick1 = ne[2*g+1] && (!ne[2*g] || last[g] == 1'b0);
    assign take[2*g] = ne[2*g] && !pick1;
    assign take[2*g+1] = pick1;
    // views agent (s4_b2 SS -90.21: FIFO read pointer -> 4:1 read mux -> lane pick mux -> d, 19 levels; d -> t_su
    // -17 over the wire): both FIFO heads and the pick are registered first (hq / pq), the pick mux runs the next
    // cycle, and the lane leaves through a 2-stage pin chain (u_o): +3 cycles on each t_su row, transaction-exact
    reg vq, pq, v; reg [527:0] hq0, hq1, d;
    wire rn = rn_l[g];
    always @(posedge c or negedge rn)
      if (!rn) begin vq <= 1'b0; v <= 1'b0; last[g] <= 1'b1; end
      else begin vq <= ne[2*g] || ne[2*g+1]; v <= vq; if (ne[2*g] || ne[2*g+1]) last[g] <= pick1; end
    always @(posedge c) begin hq0 <= fd[2*g]; hq1 <= fd[2*g+1]; pq <= pick1; d <= pq ? hq1 : hq0; end
    ot_svc_vpipe #(.W(528), .N(2)) u_o (.ck(c), .rst_n(rn), .v(v), .d(d), .qv(lv[g]), .q(ld[g]));
  end endgenerate
  assign t_su = {ld[1], lv[1], ld[0], lv[0]};
"""
    m[NAMES[2]] = HDR + f"""module {NAMES[2]} (
    input wire [528:0] a0i, input wire [528:0] a1, input wire [528:0] a2i, input wire [528:0] a3i,
    input wire [0:0] ck, input wire [0:0] rst, input wire [512:0] kin, output wire [512:0] kout,
    output wire [1057:0] t_su);
{rsync_regions(['kp', 'r0', 'r1', 'r2', 'r3', 'l0', 'l1'])}{pipe('u_kp', 512, st['b2.kp'], 'kin[0]', 'kin[512:1]', 'kpv', 'kpq').replace('.rst_n(rn)', '.rst_n(rn_kp)')}  assign kout = {{kpq, kpv}};
{body}endmodule
`default_nettype wire
"""
    # ---- b5: a3 + key end (vm at t_vm)
    m[NAMES[5]] = HDR + f"""module {NAMES[5]} (
    input wire [528:0] a3, input wire [0:0] ck, input wire [0:0] rst, input wire [512:0] kin,
    output wire [528:0] a3o, output wire [511:0] t_vm);
{rsync()}{pipe('u_kp', 512, st['b5.kp'], 'kin[0]', 'kin[512:1]', 'pv', 'pq')}  reg [511:0] vm;
  always @(posedge c) if (pv) vm <= pq;
  assign t_vm = vm;
{pipe('u_a3', 528, st['b5.a3'], 'a3[0]', 'a3[528:1]', 'a3v', 'a3q')}  assign a3o = {{a3q, a3v}};
endmodule
`default_nettype wire
"""
    seg = HDR + """module hfd_index_q_seg (     // the six bands joined (bench vehicle; same ports as hfd_index_q)
    input wire [528:0] a0, input wire [528:0] a1, input wire [528:0] a2, input wire [528:0] a3,
    input wire [0:0] ck, input wire [1025:0] k, input wire [0:0] rst,
    output wire [1057:0] t_su, output wire [511:0] t_vm);
  wire [512:0] k01, k12, k23, k34, k45; wire [528:0] a0_01, a0_12, a3_54, a3_43, a3_32, a2_32;
  hfd_index_q_b0 u_b0 (.a0(a0), .ck(ck), .k(k), .rst(rst), .kout(k01), .a0o(a0_01));
  hfd_index_q_b1 u_b1 (.ck(ck), .rst(rst), .kin(k01), .kout(k12), .a0i(a0_01), .a0o(a0_12));
  hfd_index_q_b2 u_b2 (.a0i(a0_12), .a1(a1), .a2i(a2_32), .a3i(a3_32), .ck(ck), .rst(rst), .kin(k12), .kout(k23), .t_su(t_su));
  hfd_index_q_b3 u_b3 (.ck(ck), .rst(rst), .kin(k23), .kout(k34), .a3i(a3_43), .a3o(a3_32), .a2(a2), .a2o(a2_32));
  hfd_index_q_b4 u_b4 (.ck(ck), .rst(rst), .kin(k34), .kout(k45), .a3i(a3_54), .a3o(a3_43));
  hfd_index_q_b5 u_b5 (.a3(a3), .ck(ck), .rst(rst), .kin(k45), .a3o(a3_54), .t_vm(t_vm));
endmodule
`default_nettype wire
"""
    return m, seg


def main():
    st = plan()
    (HERE / 'split_spec.json').write_text(json.dumps(spec(), indent=1) + '\n')
    d = HERE / 'rtl/split'
    d.mkdir(parents=True, exist_ok=True)
    m, seg = band_rtl(st)
    for n, t in m.items():
        (d / f'{n}.sv').write_text(t)
    (d / 'hfd_index_q_seg.sv').write_text(seg)
    # added-cycle ledger vs the one-slot MARGIN view (A_ST 8 + input reg + FIFO + lane = 11 regs per row; keys kf +
    # K_ST 16 + vm = 18): the split adds one zero-length face hop per band boundary crossed and re-sizes every chain
    # to its own distance
    L = 5   # FIFO + lane: was 2 (FIFO, lane d); views agent: + head/pick register + 2-stage t_su pin chain
    rows = {'a0': st['b0.a0'] + st['b1.a0'] + st['b2.r0'] + L, 'a1': st['b2.r1'] + L,
            'a2': st['b3.a2'] + st['b2.r2'] + L, 'a3': st['b5.a3'] + st['b4.a3'] + st['b3.a3'] + st['b2.r3'] + L}
    keys = 2 + st['b0.kp'] + sum(st[f'b{i}.kp'] for i in (1, 2, 3, 4)) + st['b5.kp'] + 1
    led = dict(hop_um=HOP, bands=dict(zip(NAMES, [dict(y0_um=y, h_um=h) for y, h in zip(Y0, H)])), stages=st,
               regs=dict(rows=rows, keys=keys), margin_view_regs=dict(rows=11, keys=18),
               added_cycles=dict(rows={r: v - 11 for r, v in rows.items()}, keys=keys - 18))
    (HERE / 'split_stages.json').write_text(json.dumps(led, indent=1) + '\n')
    print(json.dumps(led['added_cycles']), json.dumps(st))


if __name__ == '__main__':
    main()
