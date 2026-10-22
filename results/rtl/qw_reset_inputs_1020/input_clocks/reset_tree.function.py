def _reset_tree(v, m):
    """tp8 reset tree (owner 2026-10-13 release gate; plan results/arch/qwen_tp8_1013/reset_tree_plan.json): every bus of
    class 'reset' longer than RELAY_REACH_UM pin to pin (bounding box of the pin centroids, as pinreg_audit.py) becomes a
    registered tree of 1-bit repeaters (RST_REP: clk + d on W, q0 on E, q1 on N; 1 input flop + 2 registered outputs,
    2 cycles), every site LEGALISED on the GX / GY lattice against the final placement (after the relays) with RST_GAP_UM
    clearance, every net (one driver + its sinks) <= RST_OK_UM.  Each tree is clocked by the clock net of its sinks
    (clk_core_<q>, clk_hbm_<q>, the KV core clock): assertion and release are synchronous to the leaf domain.  EQUAL
    DEPTH per domain (bus name less the quadrant suffix): the slack of every tree edge is padded by a pad chain beside
    the child (RST_PAD cells of 10 cycles + plain repeaters), so every sink of a domain leaves reset in the same cycle.
    Power-on only: 0 cycles per token.  Raises on any reset net left over the reach."""
    if _os_r.environ.get('OT_RELAY_SKIP') == '1':
        return
    import os as _os
    by = {i.name: i for i in m['insts']}
    pos = _pin_pos(v, m)
    from qwen_split.reset_sync_contract import clock_inputs
    ckof = clock_inputs(m)
    nets, ck_of_bus, idx_of = [], {}, {}
    for idx, (bid, cl, bits, eps) in enumerate(m['buses']):
        if cl != 'reset' or len(eps) < 2:
            continue
        pts = [pos(*e) for e in eps]
        if _hp(pts) <= RELAY_REACH_UM:
            continue
        if bits != 1:
            raise ValueError(f'reset tree: {bid} is {bits} b')
        d = next((j for j, e in enumerate(eps) if re.match(r'rso|hrst$|crst$', e[1].lstrip('*'))), 0)
        sinks = [(e[0], e[1], pts[j]) for j, e in enumerate(eps) if j != d]
        # the clock of the sinks: the clock net on the sink instance (a CDC leaf has two: h_* pins ride hclk)
        vote = {}
        for i, p, _ in sinks:
            c = ckof.get(i, [])
            if len(c) > 1:
                hb = p.lstrip('*').startswith('h')
                c = [q for q in c if q[1].lstrip('*').startswith('h') == hb] or c
            if c:
                vote[c[0][0]] = vote.get(c[0][0], 0) + 1
        if not vote:
            raise ValueError(f'reset tree: {bid} sinks carry no clock net')
        ck_of_bus[bid] = max(sorted(vote), key=lambda k: vote[k])
        idx_of[bid] = idx
        nets.append(dict(bid=bid, dom=re.sub(r'_(?:[WE][SN]|c)$', '', bid), drv=(eps[d][0], eps[d][1], pts[d]), sinks=sinks,
                         domain=by[sinks[0][0]].domain))
    rec = dict(reach_um=RELAY_REACH_UM, long_reset_nets=len(nets), repeaters=0, pad_cells=0, nets=0, max_net_um=0.0)
    m['tp8_reset_tree'] = rec
    if not nets:
        return rec
    rects = [(i.x, i.y, i.x + i.w, i.y + i.h) for i in m['insts']]
    if _os.environ.get('OT_RESET_DUMP'):
        import json as _json
        _json.dump(dict(nets=nets, rects=rects, W=m['die']['w'], H=m['die']['h'], gx=v.GX, gy=v.GY), open(_os.environ['OT_RESET_DUMP'], 'w'))
    cells, wires, per, errors = _rst_tree_build(nets, rects, m['die']['w'], m['die']['h'], v.GX, v.GY)
    if errors:
        rec.update(errors=errors, per_net=dict(per))
    _reset_reach_gate(errors, rec)
    if errors:
        # diagnosis only (OT_RESET_GATE=diag): the nets with an unbuildable sink / driver stay single long nets and are reported; Q-COMPUTE-DIE
        # 10-16: every OTHER reset net still gets its tree (r2h2: 3 unreachable pins on rst_spine / rst_io dropped the whole
        # tree, so rst_field reached 1,584 sinks as one 47.5 mm net and die STA read -3.96 us on it)
        if _os.environ.get('OT_RESET_PARTIAL', '1') == '0':
            return rec
        bad = {e['net'] for e in errors}
        cells = [c for c in cells if c[4] not in bad]
        wires = [w for w in wires if w[1] not in bad]
        nets = [n for n in nets if n['bid'] not in bad]
        per = {k: r for k, r in per.items() if k not in bad}
        idx_of = {k: j for k, j in idx_of.items() if k not in bad}
        ck_of_bus = {k: c for k, c in ck_of_bus.items() if k not in bad}
        rec['partial_unbuilt_nets'] = sorted(bad)
        if not nets:
            return rec
    # Q-RSTGEN7 10-19 (RELEASE_TREE Q.STA.GEN.7; tools/qwen_split/reset_sync_contract.py): reset release into a foreign
    # clock.  (c) a sink on a clock DOMAIN not mesochronous with its tree, without its own synchroniser (link-PHY rst_n: dv2f15codex io_ucie
    # -220.9 ps stream -> ucie) gets its LAST tree hop re-clocked onto its own clock (qfd_rst_rep = 2-flop synchroniser
    # of the level in the receiving domain); (b) a tile whose rst_n feeds only its own 2-flop reset synchroniser
    # (qfd_d2d_static / qfd_sys_face, RTL-proved) is a synchroniser input (d2d_rom early tap -100.7 ps).  Both become
    # declared synchroniser endpoints (case/reset_sync.sdc, die STA false path with the structural reason); same depth.
    rsync = dict(reclock={}, endpoints=[], errors=[])
    if _os.environ.get('OT_SPLIT_RST_SYNC', '1') != '0':
        from qwen_split import reset_sync_contract as _RS
        _repo = Path(__file__).resolve().parents[1]
        _ok = _RS.rtl_check(_repo)
        _rep_ok = _RS.rep_check(_repo) if (_repo / _RS.REP_SYNC['qfd_rst_rep']).exists() else (False, 'RTL missing')
        _meso = _RS.mesochronous(m)    # SerDes FDI roots mesochronous with the core (clock_contract.py); ucie 6:5 is not
        # QW-G5NOROOT 10-20: a forwarded package clock (ckb_rom pll_ck -> the d2d link hop-0 stations) is its own domain:
        # the rst_d2d leaf into those stations' en is re-clocked onto it (2-flop synchroniser), not a timed release
        _fwdc = _RS.fwd_clocks(m)
        rsync = _RS.plan(cells, wires, ck_of_bus, ckof, {i.name: i.master for i in m['insts']}, _ok, _meso, fwd=_fwdc)
        if rsync['reclock'] and not _rep_ok[0]:
            rsync['errors'].append(dict(error=f'qfd_rst_rep is not a 2-flop synchroniser: {_rep_ok[1]}'))
        _rclk = {c[0]: rsync['reclock'].get(c[0], ck_of_bus[c[4]]) for c in cells}
        rsync['untreated'] = _RS.audit(wires, _rclk, ckof, {i.name: i.master for i in m['insts']}, rsync['endpoints'], _meso,
                                       fwd=_fwdc)
        rsync['mesochronous'] = sorted(_meso)
        rsync['forwarded_clocks'] = sorted(_fwdc)
        if rsync['untreated']:
            rsync['errors'].append(dict(error='untreated reset release hops', hops=rsync['untreated'][:8]))
        rsync['rtl_check'] = {k: list(r) for k, r in _ok.items()}
        rsync['rep_check'] = list(_rep_ok)
        rec['reset_sync'] = dict(reclock=rsync['reclock'], endpoints=len(rsync['endpoints']), errors=rsync['errors'],
                                 by_class={c: sum(1 for e in rsync['endpoints'] if e['cls'] == c)
                                           for c in sorted({e['cls'] for e in rsync['endpoints']})})
        if rsync['errors']:
            raise ValueError(f"reset tree: reset synchroniser plan failed: {rsync['errors'][:4]}")
    m['reset_sync'] = rsync
    dom_inst = {n['bid']: n['domain'] for n in nets}
    ck_add = {}
    for nm, mst, x, y, bid, _ in cells:
        m['insts'].append(v.Inst(nm, mst, x, y, RST_W, RST_H, kind='reset_rep', region='reset_tree', domain=dom_inst[bid]))
        ck_add.setdefault(rsync['reclock'].get(nm, ck_of_bus[bid]), []).append((nm, 'clk'))
    # DIE-QWEN-GEN16 (Q-CB16RST 10-19): a repeater whose output drops on a cluster's regional reset pin (qfd_c_b16_dv
    # rst_c<c>r<r>) is the LAST hop of that drop: it is clocked from the cluster's own root (re-filed with the cluster),
    # so the 16 drops of an instance leave the die tree on the cluster's clock, all at the tree's equal depth (same edge)
    _rn = {c[0] for c in cells}
    _ckf = m.setdefault('ck_follow', {})
    for w_ in wires:
        eps_ = w_[-1]
        drv = next((i for i, p in eps_ if i in _rn and p in ('q0', 'q1')), None)
        tgt = next((i for i, p in eps_ if re.fullmatch(r'rst_c\d+r\d+', p.lstrip('*'))), None)
        if drv and tgt:
            _ckf.setdefault((drv, 'clk'), tgt)
    drop = set(idx_of.values())
    B = [b for j, b in enumerate(m['buses']) if j not in drop]
    B = [(bid, cl, bits, eps + ck_add.pop(bid)) if bid in ck_add else (bid, cl, bits, eps) for bid, cl, bits, eps in B]
    assert not ck_add, sorted(ck_add)
    m['buses'] = B + [(nm, 'reset', 1, eps) for nm, _, eps in wires]
    base = v.masters

    def masters(model, k=1, port_bits=None):
        o = base(model, k, port_bits)
        for mn, pad in ((RST_REP, 0), (RST_PAD, 8)):
            M = v.Master(mn, RST_W, RST_H, 3, f'reset tree repeater (ot_qwen_rst_rep PAD={pad}): 1 input flop + {pad} pad '
                         f'flops + 2 registered outputs, standard cells M1-M3, clk + d on W, q0 on E, q1 on N')
            if RST_CLOSED:              # the closed view's own pin centres (bind_real swaps in its LEF)
                M.face('clk', 1, 'W', 'M4', 3.132)
                M.face('d', 1, 'W', 'M4', 3.228)
                M.face('q0', 1, 'E', 'M4', 3.228)
                M.face('q1', 1, 'N', 'M5', 6.972)
            else:
                M.face('clk', 1, 'W', 'M4', RST_H * 0.3)
                M.face('d', 1, 'W', 'M4', RST_H * 0.7)
                M.face('q0', 1, 'E', 'M4', RST_H / 2)
                M.face('q1', 1, 'N', 'M5', RST_W / 2)
            o[mn] = M
        return o
    v.masters = masters
    # the release rule on the emitted pins (the audit's measure), every reset-class net of the die
    pos = _pin_pos(v, m)
    over, mx = [], 0.0
    for bid, cl, bits, eps in m['buses']:
        if cl != 'reset' or len(eps) < 2:
            continue
        L_ = _hp([pos(*e) for e in eps])
        if bid in per or '__t' in bid:
            mx = max(mx, L_)
        if L_ > (RST_OK_UM if '__t' in bid else RELAY_REACH_UM):
            over.append((bid, round(L_, 1)))
    deps = {}
    for bid, r in per.items():
        deps.setdefault(r['dom'], set()).update(r['depth_cycles'])
    # legalisation: distance (Manhattan, um) from each requested point (lattice cell centre for a trunk node, sink
    # centroid for a leaf, the node it pads / fans out for a pad or auxiliary cell) to the legal site taken
    moved = sorted(c[5] for c in cells)
    rec.update(repeaters=sum(r['repeaters'] for r in per.values()), pad_rep=sum(r['pad_rep'] for r in per.values()),
               pad_p8=sum(r['pad_p8'] for r in per.values()), cells=len(cells), nets=len(wires), max_net_um=round(mx, 1),
               depth_cycles={d_: sorted(s) for d_, s in deps.items()}, max_depth_cycles=max(max(s) for s in deps.values()),
               pads='pad chains beside the child of each slack edge: qfd_rst_rep_p8 (10 cycles) + qfd_rst_rep (2 cycles)',
               masters=[RST_REP, RST_PAD], frame_um=[RST_W, RST_H], gap_um=RST_GAP_UM, lattice_um=RST_PITCH_UM,
               clock_of={b_: ck_of_bus[b_] for b_ in sorted(ck_of_bus)}, per_net=per, over=over,
               legalised=dict(sites=len(moved), moved_over_1um=sum(1 for q in moved if q > 1.0), median_um=moved[len(moved) // 2],
                              p90_um=moved[len(moved) * 9 // 10], max_um=moved[-1]),
               cycles_per_token=0)
    if any(len(s) != 1 for s in deps.values()):
        raise ValueError(f'reset tree: unequal leaf depth {rec["depth_cycles"]}')
    if over and _os.environ.get('OT_RESET_GATE') not in ('warn', 'diag'):
        raise ValueError(f'reset tree: {len(over)} reset nets over the reach: {over[:8]}')
    return rec
