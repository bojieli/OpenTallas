#!/usr/bin/env python3
"""KV-HROOT-PEER (10-18): local reset relays for the HOST cluster child qkd_hr_core_peer.

Gate ca25bcce7 (kv-cdc2-peer, --cts): reset port por_n drove 5,341 async-reset flops (coordinator, rank-0 codec through
por_n&&pll_locked, root mux, ctrl packet) and host_rst_n 3,419 (peer link, ctrl packet), straight from the ports
(in->reg recovery -46.9 ps; most of the ~12.9k failing CTS-repair endpoints were these recovery arcs).

Every reset pin of every member of the child gets its own ot_rst_relay #(REGIONS 1, SYNC 2, TREE 1) inside a
wrapper with the member's ports and parameters (one wrapper per member type, as gen_prompt_rr.py / the NATIVE-FIX3
tx/rx wrappers).  The relay flops are placed with their member, so each port net feeds only 3-flop relays and each
member resets from a local, flop-driven tree.  Assert stays asynchronous and immediate; release is 3 ck edges later,
UNIFORMLY for both resets and every member of the child, so the members stay mutually aligned and the ctrl packet's
por_n-domain state still sees host reset (rst_n used as data) relative to its own por_n exactly as before.  host_rst_n
consumers of tx / rx / prompt already release +3 (same contract); the child's por_n release moves +3 against the
guard / prompt por_n consumers (POR, the cluster boots long after it).

The root mux wrapper wraps the restructured copy qkd_host_peer_root_mux_pl (peer_rr/, hand-written: cycle-exact one-hot
TX round robin + one registered cycle on the local rank-0 RX path; its own bench rtl/test/qwen_host/hr_peer_pl_1018).
The wraps are applied to the generated child with gen_cluster.py --wrap-only and to the flat reference of the
composition gate through bench/flat_wraps.json.

QKD_HR_PE_RR_MUTANT (bench only): every relay of these wrappers bypassed (raw pin = member reset).

KV-PEER5 r5 (REFILL-1330 10-19, SAFE-AUDIT-KV: r4 checklist fails 3/4/7):
 (a) RESET RELAY COPIES: each relay is ot_rst_relay #(REGIONS K) whose K identical kept outputs <r>_qv carry the
     attribute ot_rst_split; physical/common_flow/ot_rst_split.tcl (synthesis, OT_RST_SPLIT=1) spreads the member's
     async-reset flops over the K copies (<= ~200 loads each; r4: 5,165 / 2,165 / 1,260 / 893 on one relay flop).
     Function unchanged: the copies are the same register (release +3 edges, assert immediate, as before).
 (b) INPUT STAGES (STAGE): listed member inputs pass one plain register (no reset) inside the wrapper before the member
     (+1 edge on those inputs; same as the sender driving them one edge later).  r4 gate classes cut:
     engine_result_v pin flop -> coordinator lifecycle selected-terminal compare -> lifecycle_fault / terminal_* (-146.8
     / -133.2) and local_service_epoch pin flop -> rank codec status compare -> tx word -> root mux (-97.0 / -84.2).
     Bench: rtl/test/qwen_host/hr_peer_stage_1019 (wrapper vs the member with the same relay and the inputs delayed
     one edge in the bench, every output every edge); QKD_HR_PE_STAGE_MUTANT bypasses the stages (must FAIL).
 (c) the root mux wrapper's inner member is qkd_host_peer_root_mux_pl2 (registered one-hot TX grant + RX/TX slices).

usage: gen_peer_rr.py [--check]      (writes rtl/qwen_sys/host_cluster_20261017/peer_rr/*_rr.sv and the stage benches)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_prompt_rr as G  # noqa: E402  (strip_comments, split_top, matching, ports)

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'rtl/qwen_sys/host_cluster_20261017/peer_rr'
HI = 'rtl/qwen_sys/host_integrated_20261014/'
# member type -> (source file, clock port, reset ports)
WRAP = {
    'qkd_host_tp8_coordinator': (HI + 'qkd_host_tp8_coordinator.sv', 'ck_codec', ['por_n']),
    'qkd_host_peer_rank_codec': (HI + 'qkd_host_peer_rank_codec.sv', 'ck', ['por_n']),
    'qkd_host_ctrl_token_service_packet_collected': (HI + 'qkd_host_ctrl_token_service_packet_collected.sv', 'ck',
                                                     ['por_n', 'rst_n']),
    'qkd_host_peer_link': (HI + 'qkd_host_peer_link.sv', 'ck', ['rst_n']),
    'qkd_host_peer_root_mux_pl': ('rtl/qwen_sys/host_cluster_20261017/peer_rr/qkd_host_peer_root_mux_pl.sv', 'ck', ['por_n']),
}
# HKV-PROMPT6 (10-19): the relay wrapper's inner member is the bit/cycle-exact timing fork of gen_peer_pd.py
# KV-PEER5 (10-19): the root mux wrapper's inner member is _pl2 (same ports as _pl / the source)
INNER = {'qkd_host_ctrl_token_service_packet_collected': 'qkd_host_ctrl_token_service_packet_collected_pd',
         'qkd_host_peer_root_mux_pl': 'qkd_host_peer_root_mux_pl2'}
# KV-PEER5: relay copies per reset pin, sized from the PRE-optimisation async loads the synthesis hook counts
# (r5 canonicalize, ot_rst_split.tcl; they run 1.3-4x the final-netlist count), <= ~235 a copy
COPIES = {
    ('qkd_host_tp8_coordinator', 'por_n'): 28,                          # 6,532 pre-opt (r4 netlist 5,165)
    ('qkd_host_peer_rank_codec', 'por_n'): 16,                          # 3,624 (893)
    ('qkd_host_ctrl_token_service_packet_collected', 'rst_n'): 12,      # 2,732 (2,165)
    ('qkd_host_ctrl_token_service_packet_collected', 'por_n'): 1,       # 58
    ('qkd_host_peer_link', 'rst_n'): 7,                                 # 1,596 (1,260)
    ('qkd_host_peer_root_mux_pl', 'por_n'): 3,                          # 536
}
# KV-PEER5: member inputs registered one edge in the wrapper (see (b) above)
STAGE = {
    'qkd_host_tp8_coordinator': ['engine_result_v', 'engine_result_tag', 'engine_result_gen', 'engine_result_done',
                                 'engine_result_fault', 'engine_result_cause', 'engine_result_token',
                                 'engine_result_value', 'engine_result_cycles'],
    'qkd_host_peer_rank_codec': ['service_ready', 'native_ready', 'service_epoch', 'drained', 'context_owned',
                                 'links_drained', 'link_reset_seen', 'retrained', 'program_ready', 'program_epoch',
                                 'program_digest'],
}
BENCH = ROOT / 'rtl/test/qwen_host/hr_peer_stage_1019'
# flat member type -> wrapper type (gen_cluster --wrap-only + bench/flat_wraps.json)
WRAPS = {
    'qkd_host_tp8_coordinator': 'qkd_host_tp8_coordinator_rr',
    'qkd_host_peer_rank_codec': 'qkd_host_peer_rank_codec_rr',
    'qkd_host_ctrl_token_service_packet_collected': 'qkd_host_ctrl_token_service_packet_collected_rr',
    'qkd_host_peer_link': 'qkd_host_peer_link_rr',
    'qkd_host_peer_root_mux': 'qkd_host_peer_root_mux_pl_rr',
}


def header(src, mod):
    t = G.strip_comments((ROOT / src).read_text())
    t = re.sub(r'\bparameter\s*\[', 'parameter [', t)
    m = re.search(r'\bmodule\s+' + mod + r'\b\s*', t)
    i = m.end()
    params = ''
    if t[i] == '#':
        p0 = t.index('(', i)
        p1 = G.matching(t, p0)
        params = t[p0 + 1:p1]
        i = p1 + 1
    q0 = t.index('(', i)
    q1 = G.matching(t, q0)
    return t, params, t[q0 + 1:q1]


def param_names(params):
    names, cur_kind = [], ''
    for it in G.split_top(params):
        it = ' '.join(it.split())
        if not it:
            continue
        m = re.match(r'(?:parameter\s+)?(?:integer\s+|int\s+|logic\s+|bit\s+)?(?:signed\s+)?(?:\[[^\]]*\]\s*)?(\w+)\s*=', it)
        if not m:
            raise SystemExit(f'param parse: {it!r}')
        names.append(m.group(1))
    return names


def wrapper(mod, src, ck, rsts):
    body, params, plist = header(src, mod)
    pn = param_names(params)
    ps = G.ports(plist)
    names = [p[2] for p in ps]
    assert ck in names and all(r in names for r in rsts), (mod, names[:8])
    stage = STAGE.get(mod, [])
    pdir = {n: (d, r) for d, r, n in ps}
    assert all(pdir.get(s, ('',))[0] == 'input' for s in stage), (mod, stage)
    ptxt = (' #(\n  ' + ',\n  '.join(' '.join(x.split()) for x in G.split_top(params) if x.strip()) + '\n)') if pn else ''
    decl = ',\n '.join(f'{d} wire {r + " " if r else ""}{n}' for d, r, n in ps)
    pass_p = ('#(' + ','.join(f'.{n}({n})' for n in pn) + ')') if pn else ''
    conns = ',\n  '.join(f'.{n}({n + "_q" if n in rsts else (n + "_s" if n in stage else n)})' for n in names)
    lps = re.findall(r'\blocalparam\s+(?:integer\s+)?(\w+)\s*=\s*([^;]+);', body)
    used, rng = [], ' '.join(r for _, r, _ in ps)
    for nm, ex in lps:
        if re.search(r'\b' + nm + r'\b', rng) or any(re.search(r'\b' + nm + r'\b', e) for _, e in used):
            used.append((nm, ex))
    lp = ''.join(f' localparam integer {nm}={" ".join(ex.split())};\n' for nm, ex in used)
    inner = INNER.get(mod, mod)
    inner_note = (f'\n// inner member {inner} (same ports; see its header / generator).' if inner != mod else '')
    kk = {r: COPIES.get((mod, r), 1) for r in rsts}
    rel = ''.join(f' (* keep, ot_rst_split *) wire [{kk[r] - 1}:0] {r}_qv;\n wire {r}_q = {r}_qv[0];\n' for r in rsts)
    mut = ''.join(f' assign {r}_qv = {{{kk[r]}{{{r}}}}};\n' for r in rsts)
    rly = ''.join(f' ot_rst_relay #(.REGIONS({kk[r]}),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst_relay_{r}(.clk({ck}),.rst_n_in({r}),'
                  f'.rst_n({r}_qv));\n' for r in rsts)
    stg = ''
    if stage:
        stg = (f' // KV-PEER5 input stage: one plain register per listed input (no reset), +1 {ck} edge\n' +
               ''.join(f' reg {pdir[s][1] + " " if pdir[s][1] else ""}{s}_r;\n wire {pdir[s][1] + " " if pdir[s][1] else ""}{s}_s;\n'
                       for s in stage) +
               f' always @(posedge {ck}) begin\n' + ''.join(f'  {s}_r <= {s};\n' for s in stage) + ' end\n'
               '`ifdef QKD_HR_PE_STAGE_MUTANT\n' + ''.join(f' assign {s}_s = {s};\n' for s in stage) + '`else\n' +
               ''.join(f' assign {s}_s = {s}_r;\n' for s in stage) + '`endif\n')
    copies = ', '.join(f'{r} x{kk[r]}' for r in rsts)
    return f"""`timescale 1ns/1ps
// GENERATED by tools/qwen_kv_die/host_cluster/gen_peer_rr.py (KV-HROOT-PEER 10-18, KV-PEER5 r5 10-19) -- do not edit.
// {mod} behind local reset relays at its reset pin(s) {", ".join(rsts)}.  Each pin drives only an ot_rst_relay
// (2 sync flops + K kept relay copies, {copies}) placed with this member; the copies <r>_qv (attribute ot_rst_split) are
// the member's reset, spread over its flops at synthesis by physical/common_flow/ot_rst_split.tcl (<= ~200 loads a copy).
// Assert asynchronous and immediate, RELEASE 3 {ck} edges after the pin, as every reset consumer of the child.
// {src} is unchanged.  QKD_HR_PE_RR_MUTANT (bench only): relays bypassed.{inner_note}
""" + (f"// Input stage (+1 {ck} edge): {', '.join(stage)}.  QKD_HR_PE_STAGE_MUTANT (bench only): stage bypassed.\n" if stage else '') + f"""module {mod}_rr{ptxt}(
 {decl}
);
{lp}{rel}`ifdef QKD_HR_PE_RR_MUTANT
{mut}`else
{rly}`endif
{stg} {inner} {pass_p} u_m(
  {conns});
endmodule
"""


def stage_bench(mod, src, ck, rsts):
    """lock-step bench: {mod}_rr vs the unchanged {mod} with the same relay (REGIONS 1) and the staged inputs delayed
    one edge in the bench; random inputs, valid-like 1-bit inputs sparse, async reset pulses; every output every edge."""
    body, params, plist = header(src, mod)
    ps = G.ports(plist)
    stage = STAGE[mod]
    clks = [n for d, r, n in ps if d == 'input' and re.fullmatch(r'ck\w*|clk', n)]
    ins = [(r, n) for d, r, n in ps if d == 'input' and n not in clks and n not in rsts]
    outs = [(r, n) for d, r, n in ps if d == 'output']
    def w(r):
        if not r:
            return 1
        m = re.fullmatch(r'\[(\d+):(\d+)\]', r.replace(' ', ''))
        assert m, (mod, r)
        return abs(int(m.group(1)) - int(m.group(2))) + 1
    tb = f'tb_{mod}_stage'
    L = [f"`timescale 1ns/1ps",
         f"// GENERATED by tools/qwen_kv_die/host_cluster/gen_peer_rr.py (KV-PEER5 10-19) -- do not edit.",
         f"// {mod}_rr (relay copies + input stage) vs the unchanged {mod} with the same ot_rst_relay and the inputs",
         f"// {', '.join(stage)} delayed one edge here.  Every output compared after every edge (4-state !==).",
         f"module {tb};",
         " parameter integer NCYC=200000, SEED=1019;",
         " reg ck=0; reg rst=0; always #5 ck=~ck;"]
    for r, n in ins:
        L.append(f" reg {r + ' ' if r else ''}{n}=0;")
    for r, n in outs:
        L.append(f" wire {r + ' ' if r else ''}a_{n}, b_{n};")
    L.append(' wire ref_rst;')
    L.append(f' ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_ref_relay(.clk(ck),.rst_n_in(rst),.rst_n(ref_rst));')
    for s in stage:
        r = dict((n, rr) for rr, n in ins)[s]
        L.append(f" reg {r + ' ' if r else ''}{s}_d; always @(posedge ck) {s}_d <= {s};")
    def conn(pref, ref):
        c = [f'.{n}(ck)' for n in clks] + [f'.{n}({"ref_rst" if ref else "rst"})' for n in rsts]
        c += [f'.{n}({n + "_d" if (ref and n in stage) else n})' for _, n in ins]
        c += [f'.{n}({pref}_{n})' for _, n in outs]
        return ','.join(c)
    L.append(f" {mod} ua({conn('a', True)});")
    L.append(f" {mod}_rr ub({conn('b', False)});")
    va = ','.join(f'a_{n}' for _, n in outs)
    vb = ','.join(f'b_{n}' for _, n in outs)
    L.append(f" wire [{sum(w(r) for r, _ in outs) - 1}:0] va={{{va}}}, vb={{{vb}}};")
    L.append(" integer seed, cyc, mism=0, first=-1, resets=0, act=0;")
    L.append(" initial begin")
    L.append("  seed=SEED; rst=0; repeat(3) @(posedge ck); #1 rst=1;")
    L.append("  for(cyc=0;cyc<NCYC;cyc=cyc+1) begin")
    L.append("   @(negedge ck); if(va!==vb) begin mism=mism+1; if(first<0) first=cyc; end")
    L.append("   if(va!=0) act=act+1;")
    L.append("   @(posedge ck); #1;")
    L.append("   if(($random(seed)&511)==0) begin rst=0; resets=resets+1; #1 rst=1; end")
    for r, n in ins:
        wd = w(r)
        if wd == 1:
            L.append(f"   {n} = (($random(seed)&7)==0);")
        else:
            L.append(f"   {n} = {{{','.join(['$random(seed)'] * ((wd + 31) // 32))}}};")
    L.append("  end")
    L.append(f'  $display("HR_PEER_STAGE {mod} seed=%0d cycles=%0d resets=%0d active_cycles=%0d mismatches=%0d first=%0d %s",'
             '   SEED,NCYC,resets,act,mism,first,(mism==0&&resets>=100&&act>=NCYC/2)?"PASS":"FAIL");')
    L.append("  $finish;")
    L.append(" end")
    L.append("endmodule")
    return tb, '\n'.join(L) + '\n'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    BENCH.mkdir(parents=True, exist_ok=True)
    bad = 0
    files = []
    for mod, (src, ck, rsts) in WRAP.items():
        files.append((OUT / f'{mod}_rr.sv', wrapper(mod, src, ck, rsts)))
        if mod in STAGE:
            tb, txt = stage_bench(mod, src, ck, rsts)
            files.append((BENCH / f'{tb}.sv', txt))
    for f, txt in files:
        if '--check' in sys.argv:
            if not f.exists() or f.read_text() != txt:
                print(f'STALE {f.relative_to(ROOT)}')
                bad += 1
        else:
            f.write_text(txt)
            print(f'wrote {f.relative_to(ROOT)}')
    print('wraps for gen_cluster --wrap-only / flat_wraps.json:', ' '.join(f'--wrap {m}={w}' for m, w in WRAPS.items()))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
