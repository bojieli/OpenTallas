#!/usr/bin/env python3
"""KV-PROMPT4 (10-18): local reset relays for the HOST cluster child qkd_hr_core_prompt.

Gate p3 (KV-TILES-D, b9f83635a) measured host_rst_n driving 4,924 async-reset pins across the whole tile (u_pkg 1,504,
u_csr 908, u_host 645 + its rst_n_i 1,496, u_axi 547, records 671, u_program 358, u_program_rx 210, u_prompt 76, u_hc 8).
Coordinator decision (4): feed host_rst_n (and so rst_n_i) through local ot_rst_relay trees.

Every host_rst_n consumer inside the child gets its own relay at its rst_n pin (one wrapper per member type: the same
ports and parameters, ot_rst_relay #(REGIONS 1, SYNC 2, TREE 1) between the pin and the member's rst_n, as the
NATIVE-FIX3/kvhr tx/rx wrappers).  The relay flop is placed with its member, so the tile-wide net now feeds 9 x 3 relay
flops and each member resets from a local tree.  Assert stays asynchronous and immediate; release is 3 ck edges later,
UNIFORMLY for every consumer in the child (members stay mutually aligned).  Members are unchanged files.

Two members sit below qkd_host_control_prompt_observed (u_prompt) and qkd_host_fullcontrol_observed (u_pkg, u_csr,
u_host); for those, this script writes renamed copies (<m>_rr) whose only edits are the module name and the member
instance types.  The direct members are switched in the generated child with gen_cluster.py --wrap-only, and the flat
reference of the composition gate takes the same substitution (bench/flat_wraps.json).

QKD_HR_PR_RR_MUTANT (bench only): every relay in these wrappers bypassed (raw pin = member reset).

KV-RELAYGEN (10-19, SAFE-DESIGN item 3, audit results/arch/safe_audit_1019/kv.md): a member whose gate measured more than
RR_MAX reset loads gets REGIONS = ceil(1.1 x loads / RR_MAX) KEPT relay copies (RR_LOADS, measured on gate p6: one relay
flop drove 1,508 / 960 / 671 / 647 flops).  The copies are identical registers (same D / clock / async clear); the member
still takes copy 0 at its rst_n pin and synthesis (physical/common_flow/ot_rst_split.tcl, kit "reset_relay_split") re-points
the member's reset loads over the copies, <= RR_MAX each, grouped by hierarchy so every copy serves one region.  Release
timing is unchanged (+3 edges, all copies equal).  Members with <= RR_MAX loads keep REGIONS 1 (byte-identical wrapper).

usage: gen_prompt_rr.py [--check]      (writes rtl/qwen_sys/host_cluster_20261017/prompt_rr/*.sv)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'rtl/qwen_sys/host_cluster_20261017/prompt_rr'

# member type -> (source file, clock port)
WRAP = {
    'qkd_host_axi_packet': ('rtl/qwen_sys/host_20261013/qkd_host_axi_packet.sv', 'ck'),
    'qkd_host_program_loader_target': ('rtl/qwen_sys/host_20261013/qkd_host_program_loader_target.sv', 'ck'),
    'qkd_host_program_rx_target': ('rtl/qwen_sys/host_integrated_20261014/qkd_host_program_rx_target.sv', 'ck'),
    'qkd_host_record_port': ('rtl/qwen_sys/context_transport_20261014/qkd_host_record_port.sv', 'ck'),
    'qkd_host_hc_station': ('rtl/qwen_sys/host_20261013/qkd_host_hc_station.sv', 'ck'),
    'qkd_host_ctl_service_pins': ('rtl/qwen_sys/host_20261013/qkd_host_ctl_service_pins.sv', 'ck'),
    'qkd_host_csr_service_pins': ('rtl/qwen_sys/host_20261013/qkd_host_csr_service_pins.sv', 'clk'),
    'qkd_host_if_pins_observed': ('rtl/qwen_sys/host_integrated_20261014/qkd_host_if_pins_observed.sv', 'clk'),
    'qkd_host_prompt_capture_pins': ('rtl/physical/ot_qkd_host_prompt_capture_pins.sv', 'ck'),
}
# HKV-PROMPT6 (10-19): the relay wrapper's inner member is the bit/cycle-exact timing fork of gen_prompt_pd.py
INNER = {
    'qkd_host_prompt_capture_pins': 'qkd_host_prompt_capture_pins_pd',
    'qkd_host_if_pins_observed': 'qkd_host_if_pins_observed_pd',
}
# KV-RELAYGEN: measured reset loads per member type (gate p6 textbook high_fanout, 58693d40b) -> relay copies
RR_MAX = 256
RR_LOADS = {
    'qkd_host_ctl_service_pins': 1508,     # u_control.u_pkg
    'qkd_host_csr_service_pins': 960,      # u_control.u_csr
    'qkd_host_record_port': 671,           # u_records
    'qkd_host_if_pins_observed': 647,      # u_control.u_host
}


def regions(mod):
    n = RR_LOADS.get(mod, 0)
    return max(1, -(-n * 11 // (10 * RR_MAX))) if n > RR_MAX else 1


# renamed copies: (module, source, {member type -> wrapper type})
COPY = [
    ('qkd_host_fullcontrol_observed', 'rtl/qwen_sys/host_integrated_20261014/qkd_host_fullcontrol_observed.sv',
     ['qkd_host_ctl_service_pins', 'qkd_host_csr_service_pins', 'qkd_host_if_pins_observed']),
    ('qkd_host_control_prompt_observed', 'rtl/qwen_sys/host_integrated_20261014/qkd_host_control_prompt_observed.sv',
     ['qkd_host_fullcontrol_observed', 'qkd_host_prompt_capture_pins']),
]
# the direct members of qkd_hr_core_prompt (gen_cluster --wrap-only + bench/flat_wraps.json)
DIRECT = ['qkd_host_control_prompt_observed', 'qkd_host_hc_station', 'qkd_host_axi_packet',
          'qkd_host_program_loader_target', 'qkd_host_program_rx_target', 'qkd_host_record_port']


def strip_comments(t):
    t = re.sub(r'/\*.*?\*/', ' ', t, flags=re.S)
    return re.sub(r'//[^\n]*', '', t)


def split_top(s):
    """split on commas outside () [] {}"""
    out, d, cur = [], 0, ''
    for ch in s:
        if ch in '([{':
            d += 1
        elif ch in ')]}':
            d -= 1
        if ch == ',' and d == 0:
            out.append(cur)
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


def matching(t, i):
    """index of the ')' matching '(' at t[i]"""
    d = 0
    for j in range(i, len(t)):
        if t[j] == '(':
            d += 1
        elif t[j] == ')':
            d -= 1
            if d == 0:
                return j
    raise SystemExit('unbalanced')


def header(src, mod):
    t = strip_comments((ROOT / src).read_text())
    m = re.search(r'\bmodule\s+' + mod + r'\b\s*', t)
    i = m.end()
    params = ''
    if t[i] == '#':
        p0 = t.index('(', i)
        p1 = matching(t, p0)
        params = t[p0 + 1:p1]
        i = p1 + 1
    q0 = t.index('(', i)
    q1 = matching(t, q0)
    return params, t[q0 + 1:q1]


def param_names(params):
    names = []
    for it in split_top(params):
        it = it.strip()
        if not it:
            continue
        m = re.match(r'(?:parameter\s+)?(?:integer\s+|int\s+|logic\s+|bit\s+)?(?:signed\s+)?(?:\[[^\]]*\]\s*)?(\w+)\s*=', it)
        if not m:
            raise SystemExit(f'param parse: {it!r}')
        names.append(m.group(1))
    return params, names


def ports(plist):
    """[(dir, range_text, name)]; ANSI lists with continuation names"""
    out, cur_dir, cur_rng = [], None, ''
    for it in split_top(plist):
        it = ' '.join(it.split())
        if not it:
            continue
        m = re.match(r'(input|output|inout)\b\s*(.*)$', it)
        if m:
            cur_dir, rest = m.group(1), m.group(2)
            rest = re.sub(r'^(wire|reg|logic)\b\s*', '', rest)
            rest = re.sub(r'^signed\b\s*', '', rest)
            r = re.match(r'((?:\[[^\]]*\]\s*)*)(\w+)$', rest)
            if not r:
                raise SystemExit(f'port parse: {it!r}')
            cur_rng, name = r.group(1).strip(), r.group(2)
        else:
            if not re.fullmatch(r'\w+', it):
                raise SystemExit(f'port parse: {it!r}')
            name = it
        out.append((cur_dir, cur_rng, name))
    return out


def wrapper(mod, src, ck):
    params, plist = header(src, mod)
    params, pn = param_names(params)
    ps = ports(plist)
    names = [p[2] for p in ps]
    assert 'rst_n' in names and ck in names, (mod, names[:6])
    ptxt = (' #(\n  ' + ',\n  '.join(' '.join(x.split()) for x in split_top(params) if x.strip()) + '\n)') if pn else ''
    decl = ',\n '.join(f'{d} wire {r + " " if r else ""}{n}' for d, r, n in ps)
    pass_p = ('#(' + ','.join(f'.{n}({n})' for n in pn) + ')') if pn else ''
    conns = ',\n  '.join(f'.{n}({"rst_q" if n == "rst_n" else n})' for n in names)
    # body localparams that the member's ANSI port ranges use (declared after the header, as in the member itself)
    body = strip_comments((ROOT / src).read_text())
    lps = re.findall(r'\blocalparam\s+(?:integer\s+)?(\w+)\s*=\s*([^;]+);', body)
    used, rng = [], ' '.join(r for _, r, _ in ps)
    for nm, ex in lps:
        if re.search(r'\b' + nm + r'\b', rng) or any(re.search(r'\b' + nm + r'\b', e) for _, e in used):
            used.append((nm, ex))
    inner = INNER.get(mod, mod)
    inner_note = (f'\n// HKV-PROMPT6: inner member {inner} (tools/qwen_kv_die/host_cluster/gen_prompt_pd.py, same function).'
                  if inner != mod else '')
    lp = ''.join(f' localparam integer {nm}={" ".join(ex.split())};\n' for nm, ex in used)
    nr = regions(mod)
    if nr == 1:
        relay = f' ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst_relay(.clk({ck}),.rst_n_in(rst_n),.rst_n(rst_q));'
    else:
        relay = (f' // KV-RELAYGEN: {nr} KEPT identical relay copies (gate p6: {RR_LOADS[mod]} reset loads); synthesis\n'
                 f' // (physical/common_flow/ot_rst_split.tcl) spreads the member reset loads over them, <= {RR_MAX} a copy.\n'
                 f' wire [{nr - 1}:0] rst_c;\n'
                 f' ot_rst_relay #(.REGIONS({nr}),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst_relay(.clk({ck}),.rst_n_in(rst_n),.rst_n(rst_c));\n'
                 f' assign rst_q = rst_c[0];')
    return f"""`timescale 1ns/1ps
// GENERATED by tools/qwen_kv_die/host_cluster/gen_prompt_rr.py (KV-PROMPT4 10-18) -- do not edit.
// {mod} behind a local reset relay at its rst_n pin (HOST cluster child qkd_hr_core_prompt, coordinator decision 4:
// gate p3 host_rst_n drove 4,924 async-reset pins tile-wide).  The pin drives only ot_rst_relay (2 sync flops + 1 kept
// relay flop) placed with this member; the relay output is the member's reset.  Assert asynchronous and immediate,
// RELEASE 3 {ck} edges after the pin, as every other host_rst_n consumer of the child.  {src} is unchanged.{inner_note}
// QKD_HR_PR_RR_MUTANT (bench only): relay bypassed.
module {mod}_rr{ptxt}(
 {decl}
);
{lp} wire rst_q;
`ifdef QKD_HR_PR_RR_MUTANT
 assign rst_q = rst_n;
`else
{relay}
`endif
 {inner} {pass_p} u_m(
  {conns});
endmodule
"""


def copy(mod, src, members):
    t = (ROOT / src).read_text()
    u, n = re.subn(r'(\bmodule\s+)' + mod + r'\b', r'\g<1>' + mod + '_rr', t, count=1)
    assert n == 1, mod
    for m in members:
        u, k = re.subn(r'(^|[\s;)])' + m + r'(?=\s*(?:#\s*\(|[A-Za-z_\\]))', lambda x: x.group(1) + m + '_rr', u, flags=re.M)
        assert k >= 1, (mod, m, k)
    hdr = (f'// GENERATED by tools/qwen_kv_die/host_cluster/gen_prompt_rr.py (KV-PROMPT4 10-18) -- do not edit.\n'
           f'// {src} renamed {mod}_rr with member instance types {", ".join(members)} -> <type>_rr (local reset relay\n'
           f'// wrappers); every other byte unchanged.\n')
    return hdr + u


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {}
    for mod, (src, ck) in WRAP.items():
        files[OUT / f'{mod}_rr.sv'] = wrapper(mod, src, ck)
    for mod, src, members in COPY:
        files[OUT / f'{mod}_rr.sv'] = copy(mod, src, members)
    bad = 0
    for f, txt in files.items():
        if '--check' in sys.argv:
            if not f.exists() or f.read_text() != txt:
                print(f'STALE {f.relative_to(ROOT)}')
                bad += 1
        else:
            f.write_text(txt)
            print(f'wrote {f.relative_to(ROOT)}')
    print('wraps for gen_cluster --wrap-only / flat_wraps.json:', ' '.join(f'{m}={m}_rr' for m in DIRECT))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
