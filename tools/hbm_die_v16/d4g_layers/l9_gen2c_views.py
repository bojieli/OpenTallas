#!/usr/bin/env python3
"""DIE-HBM-LEAD/VIEWS 10-19: GEN2c contract post-layer L9 -- bind the views CLOSED since GEN2.

    l9_gen2c_views.py IN_contract.json[.gz] OUT_contract.json --report R.json [--no-cx] [--no-idx-pair]

Runs on the POST-LANDING contract (GEN2 net/contract.json, or GEN2b's after l7_wire); exit != 0 on any problem.

(A) Views that bind by themselves (tools/hbm_die_v15/v16_views.py real_view: same master, LEF pins == contract ports, spec
    params agree) need no netlist change, only their view directory in the worktree (GEN2c sparse set): recorded in the
    report table, not edited here.
(B) Netlist rebinds done here:
  cx  cxdl_<q><g> (x16) ot_hbm_su_static_cxport_dl and cxrc_<q> (x4) ot_hbm_su_static_cxport_rc are the two-root
      compositions of ot_hbm_su_static_cxport_split.sv; each is replaced by its two one-root halves (HH-1 10-18 23:45:
      the cxport parent is SOFT, the halves are the CLOSED views hbm_su_cx_{dlq,dls,rcq,rcs}_1018):
        <n>_s = ..._dl_s / ..._rc_s (clk_s, stream)   <n>_q = ..._dl_q / ..._rc_q (clk_q, serial)
      Every wrapper port is wired 1:1 to one half's port of the same width (parsed from the wrapper RTL), so every edge,
      clock/reset binding, open output and gap reference of the parent moves to that half unchanged; the wrapper's
      internal nets become seam edges <n>__seam_<net> (stream->serial 3:4 seam: die STA owns them with the epoch
      multicycle >= 3 quanta, as S81 x34).  The contract keeps 'split_parents' (parent -> port -> [[child, port], ...]) so
      path checks written against the parent (d4g_functional_bind) resolve through it.
  idx hb_idx__ctl ot_hbm_idx_rootctl_static -> ot_hbm_idx_rootctl_static_am and hb_argmax ot_hbm_argmax_static_sw_vm ->
      ot_hbm_argmax_static_sw_vm_r2 #(TP 192) as a PAIR (results/arch/hbm_argmax_r2_bind_1017/d4g_bind_idxam.json; COORD
      0ix die_sources supersede 330b0d6c5): rootctl clocks clk_program/_mem/clk_sel/clk_topk/clk_pair -> one clk (the
      die clock on clk_program); argmax_rr[2055:0] -> argmax_m[263:0]; hb_argmax.vm_rr 2,056 -> 264 b.  The relay tree
      on argmax_rr (4 lanes of 624) keeps lane 0 only: its stations carry argmax_m[263:0] (input fill = the word repeated,
      as the relay layer fills a short lane) and the other lanes' stations, edges and clock bindings are removed.
      Compiler: ARGMAX record timeline r2 (requests +1, writes +6, done +7; tools/hbm_argmax_static_vectors.py r2).
(C) Not bound (stay SYNTH / parent-internal), listed in the report with the reason.
"""
import argparse, collections, copy, gzip, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools' / 'hbm_die_v15'))
import full_die_v16 as F  # noqa: E402

REGION = 'd4g_gen2c_l9'
CX_SRC = 'rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport_split.sv'
CX = {'ot_hbm_su_static_cxport_dl': 'dl', 'ot_hbm_su_static_cxport_rc': 'rc'}
CLK_DOMAIN = {'clk_s': 'stream', 'clk_q': 'serial'}
AM = dict(ctl_master='ot_hbm_idx_rootctl_static_am', ctl_source='rtl/hbm_accel/index/quad_1017/ot_hbm_idx_rootctl_static_am.sv',
          ctl_deps=['rtl/hbm_accel/index/ot_hbm_idx_vm_share_static_am.sv', 'rtl/hbm_accel/index/ot_hbm_idx_vm_share_static.sv',
                    'rtl/hbm_accel/index/ot_hbm_idx_calendar_static.sv', 'rtl/hbm_accel/index/ot_hbm_idx_topk_static.sv',
                    'rtl/hbm_accel/generic/idx/ot_hgi_idx_tk2.sv', 'rtl/lib/ot_rst_relay.sv'],
          am_master='ot_hbm_argmax_static_sw_vm_r2', am_source='rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm_r2.sv')
OLD_CTL_CLOCKS = ('clk_program', 'clk_program_mem', 'clk_sel', 'clk_topk', 'clk_pair')

# report table: what GEN2c binds and how (A auto via real_view, B rebind here, C not bound + why)
TABLE = [
    ('A', 'ot_hbm_su_static_sfustore_hw', 'sfus_<q> x4', 'physical/ref_tile/hbm_su_sfustore_hw_1018/views/ot_hbm_su_static_sfustore_hw', 'CLOSED f391448a1, native PASS 71.7/64.4'),
    ('A', 'ot_hbm_svc_stack_fault', 'sfault_<q> x4', 'physical/ref_tile/hdie_svc_stack_fault/views/ot_hbm_svc_stack_fault', 'CLOSED 014a636f2 (reset-sync fix 5f7d151bc = worktree RTL)'),
    ('A', 'ot_hgi_coll_gq_land', 'hcollgl_<q> x4', 'physical/ref_tile/hcoll_gq_land_1018/views/ot_hgi_coll_gq_land', 'n1 record 40936f159 merged (fault FACE register: land_fault +1 edge only); native own-R PASS launch 137.5 / capture 93.7'),
    ('A', 'ot_hbm_fault_leaf (pv4, pv5)', 'fl/fr x16', 'physical/ref_tile/hdie_fault_leaf_n{4,5}_s8_r1/views/ot_hbm_fault_leaf', 'Codex native PASS, source = worktree'),
    ('A', 'ot_hbm_fault_leaf_n8_s0', 'fs_<q> x4', 'physical/ref_tile/hdie_fault_leaf_w_n8_s0/views/ot_hbm_fault_leaf_n8_s0', 'Codex native PASS'),
    ('A', 'ot_hbm_host_cfg_leaf_ne2 / _se2', 'hleaf_NE/SE', 'physical/ref_tile/hdie_host_cfg_leaf_{ne,se}_r2/views/*', 'Codex native PASS'),
    ('A', 'ot_hbm_idx_query_static', 'hb_idx__q_<q> x4', 'physical/ref_tile/hidx_q_r4/views/ot_hbm_idx_query_static', 'Codex native PASS'),
    ('A', 'ot_hbm_idx_xq_node_static (pv0 w297, pv1 w594)', 'hb_idx__xq_S/N/xqr', 'physical/ref_tile/hidx_xq_node_w{297,594}/views/ot_hbm_idx_xq_node_static', 'native PASS; source = closed (main), differs from GEN2 3ca snapshot'),
    ('A', 'ot_hbm_pc_refresh_cfg', 'refcfg_<q> x4', 'physical/ref_tile/hbm_refcfg_q_1018/views/ot_hbm_pc_refresh_cfg', 'native PASS; source = closed (main)'),
    ('A', 'ot_hbm_svc_wbw_copy', 'wbc_<q> x4', 'physical/ref_tile/hdie_svc_wbw_copy/views/ot_hbm_svc_wbw_copy', 'Codex native PASS'),
    ('A', 'ot_hgi_coll_inj_idx_join_rg', 'cij_<q> x4', 'physical/ref_tile/hcoll_inj_idx_join_rg_1017/views/ot_hgi_coll_inj_idx_join_rg', 'Codex native PASS'),
    ('A', 'ot_hgi_sfu_lg_pair_tap_leaf / _term', 'sfu_/hc_<q><k> x32', 'physical/ref_tile/hbm_{sfu,hc}_lg_pair_tap_leaf*_1017/views/*', 'native PASS; main RTL adds LOCAL_SPLIT (default 0 = identical)'),
    ('A', 'hbfd_rrl_sync / hbfd_rrl_hop', 'reset forest (F1 layer)', 'physical/ref_tile/hbfd_rrl_{sync,hop}/views/*', 'CLOSED c5ebcd5ca / 2a92d027a; bound when the forest layer adds the instances'),
    ('B', 'ot_hbm_su_static_cxport_dl -> dl_s + dl_q', 'cxdl_<q><g> x16 -> 32', 'physical/ref_tile/hbm_su_cx_dl{s,q}_1018/views/*', 'CLOSED 246b50404 / 05e11cc8e; own-R native FAIL (dl_q capture 393 on the 1,065 seam pins = die-STA epoch multicycle; dl_s capture 308.9 on del_obase, 231 pins) -> die STA decides'),
    ('B', 'ot_hbm_su_static_cxport_rc -> rc_s + rc_q', 'cxrc_<q> x4 -> 8', 'physical/ref_tile/hbm_su_cx_rc{s,q}_1018/views/*', 'CLOSED eabfa196e / 89a824801; own-R native FAIL (rc_s launch 343.8 / capture 501; rc_q capture 496.6) -> die STA decides'),
    ('B', 'idx PAIR ot_hbm_idx_rootctl_static_am + ot_hbm_argmax_static_sw_vm_r2 #(TP 192)', 'hb_idx__ctl + hb_argmax', 'physical/ref_tile/hidx_rootctl_am_1018/views/* + hbm_argmax_swvm_r2_1017/views/*', 'rootctl_am CLOSED r4 5187b22f9 (record branch, merged here) but own-R native FAIL launch 478 on 2,012 pins; argmax_r2 CLOSED r3 fc7263bbd native PASS; grants idx_ctl 300x260 -> 475.2x259.2 (grown W, host_N is E)'),
    ('C', 'ot_hbm_su_static_cxport_ij -> ij_s + ij_q', 'cxij_<q>', '-', 'halves not CLOSED (kits gating, claude/hbm-cxij-1018); stays SYNTH unsplit'),
    ('C', 'ot_hbm_idx_vm_share2_leaf_r (share2r)', 'hb_idx__nwsh / hcollrs', 'physical/ref_tile/hidx_share2r_leaf_1018/views/ot_hbm_idx_vm_share2_leaf_r', 'r3 CLOSED (8960ed57a) but own-R native FAIL capture 215.1 on 4 b_rq pins; wires-only rebind also needs hb_quant_NW RL 7->9, NW relay removal and calendar +1 (SHARE2 steps 2-4)'),
    ('C', 'ot_hgi_coll_kq_share2_leaf (kqs)', 'hcollks_<q> -> 16 leaves', 'physical/ref_tile/hcoll_kqs_leaf_1018/views/ot_hgi_coll_kq_share2_leaf', 'CLOSED + native PASS, but wires-only rebind changes COLL kq write latency +2 and host_status NF 141->153 (compiler) -- not in this brief; next layer'),
    ('C', 'ot_hgi_qdq_transport_ctl_r3', 'inside hb_quant_NW (soft host_split)', 'physical/ref_tile/hgi_qdq_tsplit_ctl_r3/views/ot_hgi_qdq_transport_ctl_r3 (record codex/closure-record-hgi_qdq_tsplit_ctl_r3-ctlr3-14e6fe3a2)', 'child of hb_quant_NW: needs the host_split_r2 die expansion (+XR straps, new slots) and program_leaf is not CLOSED'),
    ('C', 'ot_hgi_coll_ring_ag_ctln', 'inside the COLL quadrant parents', 'physical/ref_tile/hcoll_ring_ag_ctln_1018/views/ot_hgi_coll_ring_ag_ctln', 'not a die instance: bound by the hcoll q2/q3 parent kits'),
]


def load(p):
    return json.loads(gzip.open(p).read() if str(p).endswith('.gz') else Path(p).read_text())


def parse_wrapper(master):
    """the composition module in CX_SRC: children [(inst, child_master, {param: expr}, {child_port: net})]"""
    t = (ROOT / CX_SRC).read_text()
    t = re.sub(r'//[^\n]*', '', t)
    m = re.search(r'\bmodule\s+' + master + r'\b(.*?)\bendmodule', t, re.S)
    if not m:
        raise SystemExit(f'l9: {master} not in {CX_SRC}')
    body = m.group(1)
    kids = []
    for km in re.finditer(r'\b(ot_hbm_su_static_cxport_\w+)\s*#\((.*?)\)\s*(u_\w+)\s*\((.*?)\);', body, re.S):
        cm, pars, inst, conns = km.groups()
        params = dict(re.findall(r'\.(\w+)\s*\(\s*(\w+)\s*\)', pars))
        cmap = dict(re.findall(r'\.(\w+)\s*\(\s*(\w+)\s*\)', conns))
        kids.append((inst, cm, params, cmap))
    return kids


def remap_ref(ref, mp):
    """ref [inst, port, lo, hi] (or [inst, port, bits]) -> list of remapped refs"""
    k = (ref[0], ref[1])
    if k not in mp:
        return [ref]
    return [[c, cp] + list(ref[2:]) for c, cp in mp[k]]


def split_cx(c, rtl, problems, rep):
    I = c['instances']
    split = {}
    for n in sorted(n for n, i in I.items() if i['master'] in CX):
        P = I[n]; kind = CX[P['master']]
        kids = parse_wrapper(P['master'])
        if len(kids) != 2:
            problems.append(f'{n}: wrapper {P["master"]} has {len(kids)} children'); continue
        new = {}; port_map = collections.defaultdict(list); nets = collections.defaultdict(lambda: dict(drv=None, loads=[]))
        for ui, cm, pexpr, cmap in kids:
            cn = f'{n}_{ui[2:]}'           # u_s -> <n>_s, u_q -> <n>_q
            params = {}
            for k, v in pexpr.items():
                if v in P['params']:
                    params[k] = P['params'][v]
                elif re.fullmatch(r'\d+', v):
                    params[k] = int(v)
                elif v == 'MUT':
                    continue                  # MUT default 0 (bench only)
                else:
                    problems.append(f'{cn}: param {k}({v}) not resolvable')
            ports = rtl.ports(cm, CX_SRC, params)
            for cp, pd in ports.items():
                net = cmap.get(cp)
                if net is None:
                    problems.append(f'{cn}.{cp} unconnected in the wrapper'); continue
                if net in P['ports']:
                    if P['ports'][net]['bits'] != pd['bits'] or P['ports'][net]['direction'] != pd['direction']:
                        problems.append(f'{cn}.{cp} {pd} != parent {net} {P["ports"][net]}')
                    port_map[(n, net)].append([cn, cp])
                else:
                    nn = nets[net]
                    if pd['direction'] == 'output':
                        if nn['drv']:
                            problems.append(f'{n}: net {net} has two drivers')
                        nn['drv'] = (cn, cp, pd['bits'])
                    else:
                        nn['loads'].append((cn, cp, pd['bits']))
            new[cn] = dict(master=cm, source=CX_SRC, params=params, slot=None, owner='HBM-SU6/HH-1', region=REGION,
                           note=f'{REGION}: one-root half {ui[2:]} of {n} ({P["master"]}); abut with its pair (seam faces equal ranges)',
                           replaces_v15=None, rtl_deps=[], ports=ports, split_of=n)
        for p, pd in P['ports'].items():
            ch = port_map.get((n, p), [])
            if not ch:
                problems.append(f'{n}.{p} reaches no child')
            if pd['direction'] == 'output' and len(ch) != 1:
                problems.append(f'{n}.{p} output driven by {len(ch)} children')
        seams = []
        for net, nn in sorted(nets.items()):
            if not nn['drv'] or not nn['loads']:
                problems.append(f'{n}: seam net {net} drv {nn["drv"]} loads {nn["loads"]}'); continue
            dc, dp, w = nn['drv']
            clk = next(cp for cp in new[dc]['ports'] if cp in CLK_DOMAIN)
            for (lc, lp, lw) in nn['loads']:
                if lw != w:
                    problems.append(f'{n}: seam {net} width {w} -> {lc}.{lp} {lw}')
                seams.append(dict(name=f'{n}__seam_{net}', bits=w, source=[dc, dp, 0, w], sink=[lc, lp, 0, w],
                                  clock=CLK_DOMAIN[clk], ready_or_credit=False,
                                  allowed_exception='seam_3to4_epoch_multicycle_3q',
                                  basis=f'{REGION}: {P["master"]} wrapper net {net} (cxport_split.sv; die STA epoch multicycle >= 3 quanta)',
                                  region=REGION))
        del I[n]; I.update(new)
        c['edges'].extend(seams)
        split[n] = dict(master=P['master'], children={k: v['master'] for k, v in new.items()},
                        ports={p: v for (pn, p), v in port_map.items() if pn == n})
        rep['cx'].append(dict(parent=n, master=P['master'], children=sorted(new), seams=len(seams),
                              seam_bits=sum(e['bits'] for e in seams)))
    if not split:
        return
    mp = {(pn, p): v for pn, s in split.items() for p, v in s['ports'].items()}
    out = []
    for e in c['edges']:
        srcs = remap_ref(e['source'], mp); snks = remap_ref(e['sink'], mp)
        if len(srcs) != 1:
            problems.append(f'edge {e["name"]}: source maps to {len(srcs)} children')
        for k, s in enumerate(snks):
            x = dict(e, source=srcs[0], sink=s)
            if len(snks) > 1:
                x['name'] = f'{e["name"]}__{s[0]}'
            out.append(x)
    c['edges'] = out
    crs = []
    for x in c['clock_resets']:
        k = (x['instance'], x['port'])
        if k in mp:
            for cn, cp in mp[k]:
                crs.append(dict(x, instance=cn, port=cp, note=f'{REGION}: {k[0]}.{k[1]} -> half {cn}'))
        else:
            crs.append(x)
    c['clock_resets'] = crs
    straps = []
    for s in c['straps']:
        k = (s['inst'], s['port'])
        if k in mp:
            for cn, cp in mp[k]:
                straps.append(dict(s, inst=cn, port=cp, master=I[cn]['master']))
        else:
            straps.append(s)
    c['straps'] = straps
    c['open_outputs'] = [r for o in c['open_outputs'] for r in remap_ref(o, mp)]
    c['exposed_inputs'] = [r for o in c.get('exposed_inputs', []) for r in (remap_ref(o, mp) if isinstance(o, list) else [o])]
    for d in c['die_pins']:
        k = (d.get('instance'), d.get('port'))
        if k in mp:
            if len(mp[k]) != 1:
                problems.append(f'die pin {d["name"]} on a fan-out parent port')
            d['instance'], d['port'] = mp[k][0]
    for g in c.get('gaps', []):
        if isinstance(g.get('affects'), list):
            g['affects'] = [r for a in g['affects'] for r in (remap_ref(a, mp) if isinstance(a, list) else [a])]
    c.setdefault('split_parents', {}).update(split)


def idx_pair(c, rtl, problems, rep):
    I = c['instances']
    ctl, am = I.get('hb_idx__ctl'), I.get('hb_argmax')
    if not ctl or not am:
        problems.append('idx pair: hb_idx__ctl / hb_argmax missing'); return
    if ctl['master'] != 'ot_hbm_idx_rootctl_static' or am['master'] != 'ot_hbm_argmax_static_sw_vm':
        problems.append(f'idx pair: unexpected masters {ctl["master"]} / {am["master"]}'); return
    nports = rtl.ports(AM['ctl_master'], AM['ctl_source'], {})
    old = ctl['ports']
    for p, pd in old.items():
        if p in OLD_CTL_CLOCKS or p == 'argmax_rr':
            continue
        if nports.get(p) != pd:
            problems.append(f'idx pair: hb_idx__ctl.{p} {pd} -> {nports.get(p)}')
    extra = sorted(set(nports) - set(old) - {'clk', 'argmax_m'})
    if extra:
        problems.append(f'idx pair: rootctl_am new ports {extra}')
    aports = rtl.ports(AM['am_master'], AM['am_source'], {'TP': 192})
    for p, pd in am['ports'].items():
        if p != 'vm_rr' and aports.get(p) != pd:
            problems.append(f'idx pair: hb_argmax.{p} {pd} -> {aports.get(p)}')
    W = nports['argmax_m']['bits']
    if aports['vm_rr']['bits'] != W:
        problems.append(f'idx pair: vm_rr {aports["vm_rr"]["bits"]} != argmax_m {W}')
    # clocks: one clk = the die clock on clk_program
    crs, have = [], False
    for x in c['clock_resets']:
        if x['instance'] == 'hb_idx__ctl' and x['port'] in OLD_CTL_CLOCKS:
            if x['port'] == 'clk_program':
                crs.append(dict(x, port='clk', bits=1, note=f'{REGION}: rootctl_am one clk (was clk_program; 7 equal stream clocks merged)'))
                have = True
            continue
        crs.append(x)
    if not have:
        problems.append('idx pair: no clk_program clock binding on hb_idx__ctl')
    c['clock_resets'] = crs
    for e in c['edges']:
        if e['sink'][0] == 'hb_idx__ctl' and e['sink'][1] in OLD_CTL_CLOCKS:
            problems.append(f'idx pair: edge {e["name"]} drives a removed clock port')
    # argmax word: relay lanes from argmax_rr to vm_rr
    E = c['edges']
    drv = [e for e in E if e['source'][:2] == ['hb_idx__ctl', 'argmax_rr']]
    direct = [e for e in drv if e['sink'][:2] == ['hb_argmax', 'vm_rr']]
    removed_inst, removed_edges = set(), set()
    new_edges = []
    if direct:
        removed_edges |= {e['name'] for e in drv}
        new_edges.append(dict(direct[0], name='argmax_m__l9', bits=W, source=['hb_idx__ctl', 'argmax_m', 0, W],
                              sink=['hb_argmax', 'vm_rr', 0, W], basis=f'{REGION}: idx pair argmax_m -> vm_rr', region=REGION))
    else:
        out_of = collections.defaultdict(list)
        for e in E:
            out_of[e['source'][0]].append(e)
        lanes = {}
        for e in drv:
            st = e['sink'][0]
            if not re.match(r'rf\d+_s\d+_l\d+$', st):
                problems.append(f'idx pair: argmax_rr feeds non-relay {st}'); continue
            lane = st.rsplit('_', 1)[1]
            chain, cur = [st], st
            while True:
                nxt = [x for x in out_of[cur] if x['source'][1] == 'o']
                tgt = {x['sink'][0] for x in nxt}
                if tgt == {'hb_argmax'}:
                    break
                if len(tgt) != 1:
                    problems.append(f'idx pair: relay {cur} fans to {sorted(tgt)}'); break
                cur = tgt.pop(); chain.append(cur)
            lanes[lane] = chain
        keep = 'l0' if 'l0' in lanes else sorted(lanes)[0]
        kchain = lanes[keep]
        kin = I[kchain[0]]['ports']['i']['bits']
        if kin < W:
            problems.append(f'idx pair: lane {keep} width {kin} < {W}')
        for lane, ch in lanes.items():
            if lane != keep:
                removed_inst |= set(ch)
        for e in E:
            if e in drv or e['source'][0] in removed_inst or e['sink'][0] in removed_inst:
                removed_edges.add(e['name'])
            elif e['source'][0] == kchain[-1] and e['sink'][:2] == ['hb_argmax', 'vm_rr']:
                removed_edges.add(e['name'])
        tmpl = next(e for e in drv if e['sink'][0] == kchain[0])
        lo = 0; k = 0
        while lo < kin:      # input fill: the word repeated (as the relay layer fills a short lane)
            w = min(W, kin - lo)
            new_edges.append(dict(tmpl, name=f'{tmpl["name"].rsplit("_", 1)[0]}_am{k}', bits=w,
                                  source=['hb_idx__ctl', 'argmax_m', 0, w], sink=[kchain[0], 'i', lo, lo + w],
                                  basis=f'{REGION}: idx pair argmax_m into kept relay lane {keep}' + (' (fill)' if lo else ''),
                                  region=REGION))
            lo += w; k += 1
        ld = next(e for e in E if e['source'][0] == kchain[-1] and e['sink'][:2] == ['hb_argmax', 'vm_rr'])
        new_edges.append(dict(ld, name=f'{ld["name"]}__am', bits=W, source=[kchain[-1], 'o', 0, W],
                              sink=['hb_argmax', 'vm_rr', 0, W], region=REGION))
        rep['idx']['relay_lanes'] = {k2: v for k2, v in lanes.items()}
        rep['idx']['kept_lane'] = keep
    c['edges'] = [e for e in E if e['name'] not in removed_edges] + new_edges
    c['clock_resets'] = [x for x in c['clock_resets'] if x['instance'] not in removed_inst]
    for n in removed_inst:
        del I[n]
    if any(s['inst'] in removed_inst for s in c['straps']):
        problems.append('idx pair: straps on removed relay stations')
    ctl.update(master=AM['ctl_master'], source=AM['ctl_source'], rtl_deps=AM['ctl_deps'], params={}, ports=nports,
               region=REGION, note=f'{REGION}: idx PAIR rebind (d4g_bind_idxam.json): rootctl_am r4, one clk, argmax_m 264 b')
    am.update(master=AM['am_master'], source=AM['am_source'], params={'TP': 192}, ports=aports, region=REGION,
              note=f'{REGION}: idx PAIR rebind: ot_hbm_argmax_static_sw_vm_r2 (CLOSED r3-3ba44f68e), vm_rr 264 b')
    for sp in c.get('soft_parents', []):
        if 'hb_idx__ctl' in sp.get('children', {}):
            sp['children']['hb_idx__ctl'] = AM['ctl_master']
    rep['idx'].update(removed_relays=sorted(removed_inst), removed_edges=len(removed_edges), new_edges=len(new_edges),
                      argmax_bits=W)


RLY = re.compile(r'^hbfd_rly_(\d+)_(EW|WE|NS|SN)$')
SITE = re.compile(r'lane row (\S+) (\d+)/(\d+) (EW|WE|NS|SN); site \(([-\d.]+), ([-\d.]+)\) um')
STEP = {'SN': (0, 130.0), 'NS': (0, -130.0), 'WE': (130.0, 0), 'EW': (-130.0, 0)}


def equal_age_pads(c, problems, rep, scope=None):
    """EQUAL AGE per consumer port (root-clocked relay paths only).  The relay layer (relay_layer_d4f.py) packs a
    port's bits into several buses by bundle (sucore_<q>.red_tag[7:0] rides 'red_tag+red_x', red_tag[31:8] rides
    'red_sv+red_tag') and pads each bus tree to its own sinks, never across trees that meet at one consumer port: on
    GEN2 cxrc_SW/NW red_tag arrived 10 / 9 stages (red_x 10, red_sv 9).  For every consumer port whose bits arrive
    with unequal relay stage counts, the shorter trees get root-clocked pad stations (same relay master as their last
    station, same clock/reset) between their last station and THIS consumer instance (every port of it the tree
    feeds, so the co-travelling bits of other ports keep their mutual age).  Paths through landings are skipped
    (landed latency = the land plan's K/E)."""
    I = c['instances']
    for it in range(4):
        drv = {}
        for e in c['edges']:
            si, sp, slo, shi = e['source']; ki, kp, klo, khi = e['sink']
            for b in range(khi - klo):
                drv[(ki, kp, klo + b)] = (si, sp, slo + b)
        todo = {}
        sinks = collections.defaultdict(set)
        for (ki, kp, kb) in drv:
            if not I.get(ki, {}).get('master', '').startswith('hbfd'):
                sinks[(ki, kp)].add(kb)
        for (ki, kp), bits in sorted(sinks.items()):
            groups = collections.defaultdict(dict)    # producer port -> {bit: (stages, last station)}
            landed = set()
            for b in bits:
                cur, n, last = (ki, kp, b), 0, None
                while True:
                    d = drv.get(cur)
                    if d is None:
                        break
                    si, sp, sb = d; m = I[si]['master']
                    if m.startswith('hbfd') and sp in ('o', 'b'):
                        if not RLY.match(m):
                            landed.add(b)
                        if last is None:
                            last = si
                        n += 1
                        w = I[si]['ports']['i' if sp == 'o' else 'a']['bits']
                        cur = (si, 'i' if sp == 'o' else 'a', sb % w); continue
                    break
                if n and d is not None and b not in landed:
                    groups[(d[0], d[1])][b] = (n, last)
            # one producer WORD (same producer port -> same consumer port) must arrive at one age; bits of different
            # producers merged into one consumer port (fault ORs, status vectors) are separate words
            for src, per in sorted(groups.items()):
                counts = {v[0] for v in per.values()}
                if len(counts) < 2:
                    continue
                tgt = max(counts)
                if scope is not None and (ki, kp) not in scope:
                    # not a compiled functional path: report only (latency of these words is not ours to move here)
                    if it == 0:
                        rep['equal_age_unpadded'].append(dict(sink=f'{ki}.{kp}', producer=f'{src[0]}.{src[1]}',
                                                              stages=sorted(counts)))
                    continue
                for b, (n, last) in per.items():
                    if n < tgt:
                        k = (last, ki)
                        if todo.get(k, tgt - n) != tgt - n:
                            problems.append(f'equal age: tree end {last} -> {ki} needs two pad depths')
                        todo[k] = tgt - n
                rep['equal_age'].append(dict(sink=f'{ki}.{kp}', producer=f'{src[0]}.{src[1]}', stages=sorted(counts),
                                             padded_to=tgt, short_trees=sorted({v[1] for v in per.values() if v[0] < tgt})))
        if not todo:
            return
        for (last, ki), d in sorted(todo.items()):
            L = I[last]; m = L['master']; mm = RLY.match(m)
            if not mm:
                problems.append(f'equal age: {last} is not a root-clocked relay ({m})'); continue
            W = L['ports']['i']['bits']
            sm = SITE.search(L.get('note') or '')
            if not sm:
                problems.append(f'equal age: {last} has no lane-row site'); continue
            flow = sm.group(4); x, y = float(sm.group(5)), float(sm.group(6))
            prev = last
            stem = re.sub(r'_s\d+_l(\d+)$', r'_kq\g<1>', last)
            crs = [x_ for x_ in c['clock_resets'] if x_['instance'] == last]
            for j in range(d):
                pn = f'{stem}_{ki}_p{j}'
                if pn in I:
                    problems.append(f'equal age: {pn} exists'); break
                x += STEP[flow][0]; y += STEP[flow][1]
                I[pn] = dict(copy.deepcopy(L), region=REGION,
                             note=f'{REGION}: equal-age pad {j + 1}/{d} of {last} toward {ki}; lane row {pn} 0/1 {flow}; '
                                  f'site ({x:.1f}, {y:.1f}) um')
                c['edges'].append(dict(name=f'{pn}__t', bits=W, source=[prev, 'o', 0, W], sink=[pn, 'i', 0, W],
                                       clock=crs[0]['domain'] if crs else 'stream', ready_or_credit=False,
                                       allowed_exception=None, basis=f'{REGION}: equal-age pad chain', region=REGION))
                for x_ in crs:
                    c['clock_resets'].append(dict(x_, instance=pn, note=f'{REGION}: equal-age pad (as {last})'))
                prev = pn
            for e in c['edges']:
                if e['source'][0] == last and e['sink'][0] == ki:
                    e['source'] = [prev] + e['source'][1:]
                    e['basis'] = (e.get('basis') or '') + f' | {REGION}: via equal-age pad(s) {d}'
            rep['pads'].append(dict(after=last, to=ki, pads=d, master=m))
    problems.append('equal age: not converged in 4 passes')


GAP_EVIDENCE = {
    'G-CIL-INJ': 'RELEASE_TREE H.STA.WIRE.1 (SU<->COLL inject cic/cxij/cij wired on GEN2; l7_wire INJ_RET 9 / B39_NOOP 1; '
                 'GEN2b slice bench 4/4 PASS, 4 mutants FAIL)',
    'G-SMVM-XCMD': 'RELEASE_TREE H.STA.WIRE.3 (static x-load issuer xl_<q>_ctl + xcal + xq -> sm on the die, own calendar)',
    'G-CIL-RC': 'RELEASE_TREE H.STA.WIRE.5 (RC bound); red_tag equal age restored by the l9 pads (was 9/10 stages SW/NW)',
}


def sync_gaps(c, rep):
    """as l7_wire: a gap whose compiled functional paths ALL pass bit-exactly (d4g_functional_bind, fork stations followed,
    split parents resolved) is closed (kept, status 'closed' + closed_by with the evidence)."""
    sys.path.insert(0, str(ROOT / 'tools' / 'hbm_die_v16'))
    import d4g_functional_bind as FB
    res = FB.check(c, FB.spec()) + FB.check_params(c, FB.param_rules())
    st = collections.defaultdict(list)
    for r in res:
        st[r['gap']].append(r['status'])
    for g in c.get('gaps', []):
        s = st.get(g['id'])
        if s and all(x == 'PASS' for x in s) and g.get('status') != 'closed':
            g['status'] = 'closed'
            g['closed_by'] = (f'{REGION}: tools/hbm_die_v16/d4g_functional_bind.py -- all {len(s)} compiled producer->consumer '
                              f'paths/slot rules of this gap bound bit-exactly in this contract; ' + GAP_EVIDENCE.get(g['id'], ''))
            rep['closed_gaps'].append(dict(id=g['id'], paths=len(s), evidence=GAP_EVIDENCE.get(g['id'], '')))
    rep['functional_fail'] = sum(1 for r in res if r['status'] != 'PASS')


def validate(c, problems, dup_ok=frozenset()):
    I = c['instances']
    seen = collections.defaultdict(int)
    for e in c['edges']:
        for end in ('source', 'sink'):
            i, p, lo, hi = e[end]
            if i not in I:
                if i not in ('die',):
                    problems.append(f'edge {e["name"]} {end} {i} missing'); continue
                continue
            pd = I[i]['ports'].get(p)
            if pd is None or hi > pd['bits'] or lo < 0:
                problems.append(f'edge {e["name"]} {end} {i}.{p}[{lo}:{hi}] vs {pd}')
        i, p, lo, hi = e['sink']
        for b in range(lo, hi):
            seen[(i, p, b)] += 1
    dup = [k for k, v in seen.items() if v > 1]
    if dup:
        problems.append(f'{len(dup)} input bits driven twice, e.g. {dup[:3]}')
    for x in c['clock_resets']:
        if x['instance'] not in I or x['port'] not in I[x['instance']]['ports']:
            problems.append(f'clock/reset binding {x["instance"]}.{x["port"]} dangling')
    names = collections.Counter(e['name'] for e in c['edges'])
    d = [n for n, k in names.items() if k > 1 and n not in dup_ok]
    if d:
        problems.append(f'{len(d)} duplicate edge names, e.g. {d[:3]}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('contract'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    ap.add_argument('--no-cx', action='store_true'); ap.add_argument('--no-idx-pair', action='store_true')
    ap.add_argument('--no-pads', action='store_true')
    a = ap.parse_args()
    c = load(a.contract)
    rtl = F.Rtl(); problems = []
    rep = dict(schema='opentallas.hbm_d4g_l9_gen2c_views.v1', input=str(a.contract), cx=[], idx={}, equal_age=[], equal_age_unpadded=[], pads=[], closed_gaps=[],
               table=[dict(cls=t[0], master=t[1], instances=t[2], view=t[3], note=t[4]) for t in TABLE])
    n0 = len(c['instances'])
    dup_before = frozenset(k for k, v in collections.Counter(e['name'] for e in c['edges']).items() if v > 1)
    if not a.no_cx:
        split_cx(c, rtl, problems, rep)
    if not a.no_idx_pair:
        idx_pair(c, rtl, problems, rep)
    if not a.no_pads:
        sys.path.insert(0, str(ROOT / 'tools' / 'hbm_die_v16'))
        import d4g_functional_bind as FB
        scope = {(x['dst'][0], x['dst'][1]) for x in FB.resolve_split(c, FB.spec())}
        equal_age_pads(c, problems, rep, scope)
    validate(c, problems, dup_before)
    sync_gaps(c, rep)
    c['masters'] = dict(sorted(collections.Counter(i['master'] for i in c['instances'].values()).items()))
    s = c.get('summary', {})
    s.update(instances=len(c['instances']), masters=len(c['masters']), edges=len(c['edges']),
             edge_bits=sum(e['bits'] for e in c['edges']), clock_reset_ports=len(c['clock_resets']))
    c.setdefault('notes', [])
    if isinstance(c['notes'], list):
        c['notes'].append(f'{REGION}: GEN2c closed-view rebinds (cx halves {len(rep["cx"])}, idx pair {"yes" if rep["idx"] else "no"})')
    rep.update(instances_before=n0, instances_after=len(c['instances']), problems=problems,
               verdict='PASS' if not problems else 'FAIL')
    Path(a.report).write_text(json.dumps(rep, indent=1))
    for p in problems[:40]:
        print('PROBLEM', p)
    print(f'L9_GEN2C_VIEWS {rep["verdict"]} inst {n0} -> {len(c["instances"])} cx_split {len(rep["cx"])} '
          f'idx_pair {bool(rep["idx"])} problems {len(problems)}')
    if problems:
        sys.exit(1)
    op = Path(a.out)
    if str(op).endswith('.gz'):
        with gzip.open(op, 'wt') as f:
            json.dump(c, f)
    else:
        op.write_text(json.dumps(c))


if __name__ == '__main__':
    main()
