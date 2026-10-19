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

usage: gen_peer_rr.py [--check]      (writes rtl/qwen_sys/host_cluster_20261017/peer_rr/*_rr.sv)
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
    ptxt = (' #(\n  ' + ',\n  '.join(' '.join(x.split()) for x in G.split_top(params) if x.strip()) + '\n)') if pn else ''
    decl = ',\n '.join(f'{d} wire {r + " " if r else ""}{n}' for d, r, n in ps)
    pass_p = ('#(' + ','.join(f'.{n}({n})' for n in pn) + ')') if pn else ''
    conns = ',\n  '.join(f'.{n}({n + "_q" if n in rsts else n})' for n in names)
    lps = re.findall(r'\blocalparam\s+(?:integer\s+)?(\w+)\s*=\s*([^;]+);', body)
    used, rng = [], ' '.join(r for _, r, _ in ps)
    for nm, ex in lps:
        if re.search(r'\b' + nm + r'\b', rng) or any(re.search(r'\b' + nm + r'\b', e) for _, e in used):
            used.append((nm, ex))
    lp = ''.join(f' localparam integer {nm}={" ".join(ex.split())};\n' for nm, ex in used)
    rel = ''.join(f' wire {r}_q;\n' for r in rsts)
    mut = ''.join(f' assign {r}_q = {r};\n' for r in rsts)
    rly = ''.join(f' ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst_relay_{r}(.clk({ck}),.rst_n_in({r}),'
                  f'.rst_n({r}_q));\n' for r in rsts)
    return f"""`timescale 1ns/1ps
// GENERATED by tools/qwen_kv_die/host_cluster/gen_peer_rr.py (KV-HROOT-PEER 10-18) -- do not edit.
// {mod} behind local reset relays at its reset pin(s) {", ".join(rsts)} (HOST cluster child qkd_hr_core_peer: gate
// ca25bcce7 por_n drove 5,341 and host_rst_n 3,419 async-reset flops from the ports).  Each pin drives only an
// ot_rst_relay (2 sync flops + 1 kept relay flop) placed with this member; the relay output is the member's reset.
// Assert asynchronous and immediate, RELEASE 3 {ck} edges after the pin, as every reset consumer of the child.
// {src} is unchanged.  QKD_HR_PE_RR_MUTANT (bench only): relays bypassed.
module {mod}_rr{ptxt}(
 {decl}
);
{lp}{rel}`ifdef QKD_HR_PE_RR_MUTANT
{mut}`else
{rly}`endif
 {mod} {pass_p} u_m(
  {conns});
endmodule
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bad = 0
    for mod, (src, ck, rsts) in WRAP.items():
        f, txt = OUT / f'{mod}_rr.sv', wrapper(mod, src, ck, rsts)
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
