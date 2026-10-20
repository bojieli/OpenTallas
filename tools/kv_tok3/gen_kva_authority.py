#!/usr/bin/env python3
"""KV-TOK3 10-19: cut-generic observation-authority + source-fault fixture generator for KV attention vehicles.

Generalises the exact-G7 pair  trace_frontiers.py (codex/kv-token-authority-source-1019 25641b1c6)  +  generate.py /
g7_fault_bind.svh (codex/kv-token-authority-monitor-1019 e003b6794 / c54345a6b)  from the one archived G7 WSQK cut to ANY
cut produced by kva_vehicle.sh (WSQK.., P0/P1 pair vehicles), so the GEN9 boot-word vehicles carry the startup repair.
Verification only: reads <top>.sv + kva_grp_map.svh + kva_ports.svh of a cut, never edits them, drives nothing.

Paths (same semantics as G7): index 0 = TX valid (KVA_TXV), 1 = sequencer request (KVA_SEQ_PRG_REQ_V),
2..2+NG-1 = K request of landing group g (kva_kreq[g]), 2+NG..2+2NG-1 = V request of group g (kva_vreq[g]).
Each observer bit is traced back through the cut's relay stations (qkd_rlys*/qkd_rlysh*/qkd_landsh*; plain `assign`
aliases add no capture) to the producer's port net; the producer type fixes the actual source qualifier and reset:
  qkd_kvs_attn        TX : kvs_attn.u_attn.ctl.g_txl.tx_v_l   SEQ: kvs_attn.u_attn.g_prg.prg_rv   reset u_attn.rst_n
  qkd_ectl3_kiss_st   K  : <i>.u_a.u_k.req_valid               reset <i>.u_a.u_k.rn
  qkd_pv16_vport_b    V  : <i>.vq<j>_valid                     reset <i>.rn
Any other producer type, a multi-clock path, a disconnected hop or a missing observer REFUSES (exit 2): the vehicle then
has no verdict rather than an unrepaired one.
Fault probes (continuous after the producer's own reset is captured low): every kva_ectl_f / kva_vport_f instance
(.fault), every KVA_STK_F strip net and the stack's e-read owner fault net n_astk_<S>__er_fault, each initialised by the
rst_n of the instance driving it.
Outputs in --out: kva_auth_defs.svh, authority.svh, kva_fault_bind.svh, authority_manifest.json.
"""
import argparse, hashlib, json, pathlib, re, sys

RELAY = ('qkd_rlys', 'qkd_rlysh', 'qkd_landsh')


def fail(msg):
    raise SystemExit('AUTHORITY_GENERATE_FAIL ' + msg)


def parse_cut(text):
    width = {n: int(h) + 1 for h, n in re.findall(r'(?:wire|input wire|output wire)\s+\[(\d+):0\]\s+(\w+)', text)}

    def bits(e):
        e = e.strip()
        if e.startswith('{'):
            return sum([bits(x) for x in e[1:-1].split(',')], [])
        m = re.fullmatch(r'(\w+)\[(\d+)(?::(\d+))?\]', e)
        if m:
            n, h, l = m.groups()
            return [(n, i) for i in range(int(h), int(l if l is not None else h) - 1, -1)]
        if re.fullmatch(r"\d+'[bdh][0-9a-fA-F_]+", e):
            return [('CONST', e)] * int(e.split("'")[0])
        return [(e, i) for i in range(width.get(e, 1) - 1, -1, -1)]

    dr, inst, by_port = {}, {}, {}
    for ln, l in enumerate(text.splitlines(), 1):
        m = re.match(r'\s*(\w+)\s+(?:#\(.*\)\s+)?(\w+)\s+\((.*)\);', l)
        if m:
            typ, n, body = m.groups()
            ports = dict(re.findall(r'\.(\w+)\(([^()]*)\)', body))
            inst[n] = {'type': typ, 'ports': ports, 'line': ln}
            if not typ.startswith(RELAY):   # producer lookup by connected BIT (bus ports such as .prg(n_ks_prg[536:0]))
                for p, v in ports.items():
                    for bt in bits(v):
                        by_port.setdefault(bt, []).append((n, p))
            if typ.startswith(RELAY) and 'a' in ports and 'b' in ports:
                aa, bb = bits(ports['a']), bits(ports['b'])
                if len(aa) != len(bb):
                    fail(f'relay width mismatch {n}')
                for a, b in zip(aa, bb):
                    if b in dr:
                        fail(f'multiple relay drivers {b}')
                    dr[b] = {'a': a, 'name': n, 'type': typ, 'clock': ports.get('ck', ports.get('ic', 'UNKNOWN')).strip(), 'line': ln}
            continue
        m = re.match(r'\s*assign (\w+(?:\[\d+(?::\d+)?\])?) = ([^;]+);', l)
        if m:
            for b, a in zip(bits(m[1]), bits(m[2])):
                if b in dr:
                    fail(f'multiple drivers {b}')
                dr[b] = {'a': a, 'name': 'assign', 'type': 'assign', 'line': ln}
    return width, bits, dr, inst, by_port


def trace(dr, n, b=0):
    cur, out = (n, b), []
    while cur in dr:
        d = dr[cur]
        out.append(dict(d, out=list(cur)))
        cur = tuple(d['a'])
        if len(out) > 400:
            fail(f'relay loop at {n}')
    return {'end': list(cur), 'path': out}


def first_bit(expr):
    e = expr.strip()
    if e.startswith('{'):
        e = e[1:-1].split(',')[0].strip()
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cut-dir', type=pathlib.Path, required=True)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    a = ap.parse_args()
    sl = a.cut_dir
    top = json.loads((sl / 'slice.json').read_text())['top']
    cut = (sl / f'{top}.sv').read_text()
    gm = (sl / 'kva_grp_map.svh').read_text()
    pm = (sl / 'kva_ports.svh').read_text()
    width, bits, dr, inst, by_port = parse_cut(cut)

    m = re.search(r'`define KVA_TXV o_(\w+)', pm) or fail('no KVA_TXV')
    tx = m[1]
    m = re.search(r'`define KVA_SEQ_PRG_REQ_V dut\.(\w+)\[0\]', gm) or fail('no KVA_SEQ_PRG_REQ_V')
    seq = m[1]
    ng = int((re.search(r'KVA_NG = (\d+)', gm) or fail('no KVA_NG'))[1])
    kreq = dict((int(g), n) for g, n in re.findall(r'assign kva_kreq\[(\d+)\] = o_(\w+);', gm))
    vreq = dict((int(g), n) for g, n in re.findall(r'assign kva_vreq\[(\d+)\] = o_(\w+);', gm))
    if sorted(kreq) != list(range(ng)) or sorted(vreq) != list(range(ng)):
        fail(f'kreq/vreq observers do not cover 0..{ng - 1}')
    obs = [('TX', tx), ('SEQ', seq)] + [(f'K{g}', kreq[g]) for g in range(ng)] + [(f'V{g}', vreq[g]) for g in range(ng)]
    N = len(obs)

    sv = [f'// GENERATED by gen_kva_authority.py (KV-TOK3) from {sl}/{top}.sv -- verification only, drives nothing.',
          '`ifndef KVA_AUTH_DUT', '`define KVA_AUTH_DUT dut', '`endif',
          '// KVA_AUTH_ADMIT must be actual source command acceptance at its sampling edge.',
          f'wire [{N - 1}:0] kva_authority_known;', f'wire [31:0] kva_authority_errors [0:{N - 1}];',
          'integer kva_authority_admission_errors = 0;']
    paths, body = [], []
    for i, (role, net) in enumerate(obs):
        t = trace(dr, net, 0)
        hops = [x for x in t['path'] if x['type'] != 'assign']
        if any(not x['type'].startswith(RELAY) for x in hops):
            fail(f'{role} {net}: unsupported primitive')
        chain = list(reversed(hops))
        if not chain:
            fail(f'{role} {net}: no registered hop')
        clocks = {first_bit(x['clock']) for x in chain}
        if len(clocks) != 1:
            fail(f'{role} {net}: multi-clock path {sorted(clocks)}')
        clk = clocks.pop()
        end = t['end']
        ref = f'{end[0]}[{end[1]}]'
        drivers = by_port.get(tuple(end), [])
        if role in ('TX', 'SEQ'):
            want = [(n, p) for n, p in drivers if n == 'kvs_attn']
            if len(want) != 1 or inst['kvs_attn']['type'] != 'qkd_kvs_attn':
                fail(f'{role} {net}: endpoint {ref} not one kvs_attn port ({drivers})')
            prod = 'kvs_attn'
            reset = 'kvs_attn.u_attn.rst_n'
            source = 'kvs_attn.u_attn.' + ('ctl.g_txl.tx_v_l' if role == 'TX' else 'g_prg.prg_rv')
        elif role[0] == 'K':
            want = [(n, p) for n, p in drivers if inst[n]['type'] == 'qkd_ectl3_kiss_st' and p == 'req_valid']
            if len(want) != 1:
                fail(f'{role} {net}: endpoint {ref} not one ECTL req_valid ({drivers})')
            prod = want[0][0]
            reset, source = prod + '.u_a.u_k.rn', prod + '.u_a.u_k.req_valid'
        else:
            want = [(n, p) for n, p in drivers if inst[n]['type'] == 'qkd_pv16_vport_b' and re.fullmatch(r'vq[01]_valid', p)]
            if len(want) != 1:
                fail(f'{role} {net}: endpoint {ref} not one V port vq*_valid ({drivers})')
            prod = want[0][0]
            reset, source = prod + '.rn', prod + '.' + want[0][1]
        cur = end
        for x in chain:
            if list(x['a']) != list(cur):
                fail(f'{role} {net}: disconnected hop {x["name"]}')
            cur = x['out']
        if cur != [net, 0]:
            fail(f'{role} {net}: wrong terminal {cur}')
        if i == 0:
            adm_clk = clk
        hop = '{' + ','.join(f'`KVA_AUTH_DUT.{x["out"][0]}[{x["out"][1]}]' for x in reversed(chain)) + '}'
        body += [f'kva_authority_path #(.DEPTH({len(chain)}), .ID({i})) kva_auth_{i} (',
                 f' .clk(`KVA_AUTH_DUT.{clk}), .source_rst_n(`KVA_AUTH_DUT.{reset}),',
                 f' .source_valid(`KVA_AUTH_DUT.{source}), .source_alias(`KVA_AUTH_DUT.{ref}),',
                 f' .hop_q({hop}), .known(kva_authority_known[{i}]), .errors(kva_authority_errors[{i}]) );']
        paths.append(dict(index=i, role=role, observer=net, producer=prod, source=source, effective_reset=reset, clock=clk,
                          depth=len(chain), assign_aliases=len(t['path']) - len(hops), end=end))
    sv += [f'always @(posedge `KVA_AUTH_DUT.{adm_clk}) begin',
           '  if ($isunknown(`KVA_AUTH_ADMIT)) begin',
           '    kva_authority_admission_errors = kva_authority_admission_errors + 1;',
           '    $display("AUTHORITY_FAIL unknown authoritative admission");', '  end',
           f"  if (`KVA_AUTH_ADMIT === 1'b1 && kva_authority_known !== {{{N}{{1'b1}}}}) begin",
           '    kva_authority_admission_errors = kva_authority_admission_errors + 1;',
           '    $display("AUTHORITY_FAIL admission before all frontiers");', '  end', 'end'] + body

    # ---- source fault probes ----
    probes = []
    for wire in ('kva_ectl_f', 'kva_vport_f'):
        m = re.search(r'wire \[\d+:0\] %s = \{([^}]*)\};' % wire, gm) or fail(f'no {wire}')
        for e in reversed([x.strip() for x in m[1].split(',')]):
            mm = re.fullmatch(r'dut\.(\w+)\.fault', e) or fail(f'{wire}: {e}')
            n = mm[1]
            if n not in inst or 'rst_n' not in inst[n]['ports']:
                fail(f'{wire}: {n} has no rst_n')
            probes.append((n, f'dut.{n}.fault', inst[n]['ports']['rst_n'].strip(), first_bit(inst[n]['ports'].get('ck', ''))))
    m = re.search(r'`define KVA_STK_F \{([^}]*)\}', gm) or fail('no KVA_STK_F')
    stk_nets = [re.fullmatch(r'dut\.(\w+)\[0\]', x.strip())[1] for x in reversed(m[1].split(','))]
    nets = []
    for s in stk_nets:
        nets.append((s, 'af'))
        er = s.replace('__af_s', '__er_fault')
        if er != s and er in width:
            nets.append((er, 'fault'))
    for s, port in nets:
        drv = [(n, p) for n, p in by_port.get((s, 0), []) if p == port]
        if len(drv) != 1:
            fail(f'fault net {s}: not one .{port} driver ({drv})')
        n = drv[0][0]
        if 'rst_n' not in inst[n]['ports']:
            fail(f'fault net {s}: driver {n} has no rst_n')
        probes.append((n, f'dut.{s}[0]', inst[n]['ports']['rst_n'].strip(), first_bit(inst[n]['ports'].get('ck', ''))))
    fb = ['// GENERATED by gen_kva_authority.py (KV-TOK3): source-derived continuous fault checks. No trace_on, A0 or active mask.']
    for i, (n, probe, rst, ck) in enumerate(probes):
        if not ck:
            fail(f'fault probe {n}: no clock')
        fb += [f'reg kva_fault_init_{i}=0, kva_fault_seen_{i}=0;',
               f"always @(posedge dut.{ck}) if (dut.{rst} === 1'b0) kva_fault_init_{i} <= 1;",
               f"always @(negedge dut.{ck}) if (kva_fault_init_{i} && !kva_fault_seen_{i} && {probe} !== 1'b0) begin",
               f' kva_fault_seen_{i}=1; smoke_err("actual source fault {n} after initialization");',
               f' $display("KVA_SOURCE_FAULT cyc=%0d probe={probe} value=%b",cyc,{probe});',
               ' if(kva_fs < 0) kva_fs=cyc;', 'end']
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'authority.svh').write_text('\n'.join(sv) + '\n')
    # path count / V base are needed by the driver BEFORE authority.svh is included (macros are textual)
    (a.out / 'kva_auth_defs.svh').write_text(f'// GENERATED by gen_kva_authority.py (KV-TOK3)\n`define KVA_AUTH_N {N}\n`define KVA_AUTH_VBASE {2 + ng}\n')
    (a.out / 'kva_fault_bind.svh').write_text('\n'.join(fb) + '\n')
    (a.out / 'authority_manifest.json').write_text(json.dumps(dict(
        cut=str(sl / f'{top}.sv'), cut_sha256=hashlib.sha256(cut.encode()).hexdigest(), top=top, ng=ng, paths=paths,
        captures=sum(p['depth'] for p in paths),
        fault_probes=[dict(index=i, instance=n, probe=p, reset=r, clock=c) for i, (n, p, r, c) in enumerate(probes)]), indent=1) + '\n')
    print(f'AUTHORITY_GENERATE_PASS top={top} paths={N} captures={sum(p["depth"] for p in paths)} '
          f'depths={[p["depth"] for p in paths]} fault_probes={len(probes)}')


if __name__ == '__main__':
    main()
