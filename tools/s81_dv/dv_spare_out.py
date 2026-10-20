#!/usr/bin/env python3
"""S81-DIECHAIN 10-19: declare PROVABLY role-unused output bits of the bound S81 die as spare outputs (die_port_bind pad rule,
TOK-S81-GAPS/SVCP: a pad declaration on an OUTPUT port names spare output bits -- "a role-unused face of a hardened-once
master, lane padding").  Only three classes, each with its own proof; everything else stays OUTPUT_OPEN / unread (a real gap).

  A  svc_rs faces (dsdv_svc_rs / _entry, 16 instances of one hardened master): the role ROM fixes which faces carry traffic
     -- dn_o on the child faces (tree.json `children` mask), up_o / ro on the parent face (`parent` 1 + face; 0 = entry host
     pins = no face), go_v/go_d and so_v/so_d on the faces the score-exchange embedding names (embed.json roles go / so != 0).
     A face that the role ROM never drives (a stream valid / P.V word / score on a non-tree face is a sticky fault at the
     receiver, never a delivery) is spare.  PROOF: every role-ACTIVE face must be wired to a die net; a role-active face that
     is open is reported as a GAP and NOT declared.
  B  lane quantisation: a link whose RTL payload (cov bits) is narrower than its relay master (b bits) enters hop 0 with
     bits [cov, b-1] tied 0 (declared station pads); the landing output bits [cov, b-1] carry those zeros -> spare.
  C  forwarded-clock taps: clock output ports (name starts with `ck`) of a master emitted as a full-width wire whose bit k is
     a per-lane forwarded clock; bits no die cell reads belong to lanes the plan does not build -> spare.
     C' slice ck_rt (`assign ck_rt = {8{clk}}` in ot_s81sl_slice, a pure copy of the slice root): the rt return lanes are
     inbound and forwarded by their source frames, so no die lane takes the slice's ck_rt -> whole port spare when unbound.
  D  band output bo of a C1 slice (ot_s81sl_slice HB = 0, also the u_sl of every lep wrapper, which takes the default HB 0):
     the RTL drives `assign bo = 513'd0` (C1 has no band port) -> whole port spare when unbound.  (HB = 1 slices keep
     their bo; any of its bits the die leaves unread stays a failure.)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

FACES = 'NESW'
RS_FACE_W = {'dn_o': 805, 'up_o': 16, 'ro': 514, 'go_v': 1, 'go_d': 2132, 'so_v': 1, 'so_d': 1076}
INST_RE = re.compile(r'^\s*(\w+)\s+(?:#\(.*?\)\s+)?(u_\w+|ld_\w+|st_\w+)\s+\((.*)\);', re.S)


def _ports(body):
    """.port(expr) pairs of one instance line (expr may hold braces / commas)"""
    out, i = {}, 0
    while True:
        j = body.find('.', i)
        if j < 0:
            return out
        k = body.find('(', j)
        name = body[j + 1:k].strip()
        depth, e = 0, k
        while True:
            c = body[e]
            depth += c == '('
            depth -= c == ')'
            if depth == 0:
                break
            e += 1
        out[name] = body[k + 1:e].strip()
        i = e + 1


def _segments(expr, decl):
    """[(lo, hi, net_or_None)] of a concat {a, b, ...} (MSB first), LSB-relative bit positions; None = constant"""
    ex = expr[1:-1] if expr.startswith('{') and expr.endswith('}') else expr
    parts = [p.strip() for p in ex.split(',')]
    segs, pos = [], 0
    for p in reversed(parts):
        m = re.fullmatch(r"(\d+)'d\d+", p)
        if m:
            w, net = int(m.group(1)), None
        else:
            m = re.fullmatch(r'(\w+)\[(\d+):(\d+)\]', p) or re.fullmatch(r'(\w+)\[(\d+)\]', p)
            if m:
                hi = int(m.group(2)); lo = int(m.group(3)) if m.lastindex == 3 else hi
                w, net = hi - lo + 1, m.group(1)
            else:
                w, net = decl.get(p, 1), p
        segs.append((pos, pos + w - 1, net))
        pos += w
    return segs


def declare(lines, pads, root):
    """mutates pads (instance -> {master, reason, ports}) with the spare output declarations; returns the record"""
    text = '\n'.join(lines)
    decl = {m.group(2): int(m.group(1)) + 1 for m in re.finditer(r'wire \[(\d+):0\] (\w+);', text)}
    insts = {}
    for ln in lines:
        m = INST_RE.match(ln)
        if m:
            insts[m.group(2)] = (m.group(1), _ports(m.group(3)))
    rec = dict(A_svc_rs_faces=[], B_lane_quantisation=[], C_forwarded_clock_taps=[], D_c1_band_out=[], gaps=[])
    base = Path(root) / 'results/arch/s81_dv_1016/svc_rs'
    tree = json.loads((base / 'tree.json').read_text())['slices']
    emb = json.loads((base / 'embed.json').read_text())['roles']

    def add(inst, master, reason, port, lo, hi, cls):
        e = pads.setdefault(inst, dict(master=master, reason=reason, ports={}))
        if e.get('reason') != reason:
            e['reason'] = e['reason'] + ' | ' + reason
        e['ports'].setdefault(port, []).append([lo, hi])
        rec[cls].append(dict(inst=inst, master=master, port=port, lo=lo, hi=hi, bits=hi - lo + 1))

    # ---- A: svc_rs role faces
    for inst, (mod, ps) in sorted(insts.items()):
        if mod not in ('dsdv_svc_rs', 'dsdv_svc_rs_entry'):
            continue
        sid = int(inst.split('_')[2])
        t, r = tree[str(sid)], emb[str(sid)]
        active = {'dn_o': {f for f in range(4) if t['children'] >> f & 1},
                  'up_o': {t['parent'] - 1} if t['parent'] else set(),
                  'ro': {t['parent'] - 1} if t['parent'] else set(),
                  'go_v': {f for f in range(4) if r['go'][f]}, 'go_d': {f for f in range(4) if r['go'][f]},
                  'so_v': {f for f in range(4) if r['so'][f]}, 'so_d': {f for f in range(4) if r['so'][f]}}
        for port, fw in RS_FACE_W.items():
            segs = _segments(ps[port], decl) if port in ps else [(0, 4 * fw - 1, None)]
            for f in range(4):
                lo, hi = f * fw, f * fw + fw - 1
                cover = [s for s in segs if s[0] <= hi and s[1] >= lo]
                wired = all(s[2] is not None and '_nc' not in s[2] for s in cover) and port in ps
                if f in active[port]:
                    if not wired:
                        rec['gaps'].append(dict(inst=inst, port=port, face=FACES[f], why='role-active face not wired'))
                elif not wired:
                    add(inst, mod, 'svc_rs role ROM (tree.json / embed.json): face never driven by this slice role -- '
                        'spare face of the hardened-once master', port, lo, hi, 'A_svc_rs_faces')
                else:
                    rec['gaps'].append(dict(inst=inst, port=port, face=FACES[f], why='role-inactive face wired (plan vs role ROM)'))
    # ---- B: lane quantisation landing outputs
    for st, e in list(pads.items()):
        if not (st.startswith('st_') and st.endswith('_0') and e.get('reason', '').startswith('lane quantisation')):
            continue
        nm = st[3:-2]
        ld = f'ld_{nm}'
        if ld not in insts:
            continue
        mst, ps = insts[ld]
        if not ps.get('o', '').startswith(f'w_{nm}_lnd'):
            continue
        for lo, hi in e['ports']['i']:
            add(ld, mst, f'lane quantisation: landing output bits [{lo}, {hi}] carry the zero pads tied at {st}.i', 'o', lo, hi,
                'B_lane_quantisation')
    # ---- C: forwarded-clock taps
    for inst, (mod, ps) in sorted(insts.items()):
        for port, ex in ps.items():
            if not port.startswith('ck') or ex != f'{inst}_{port}' or ex not in decl:
                continue
            w = decl[ex]
            used = set()
            for m in re.finditer(re.escape(ex) + r'(\[(\d+)\])?(?!\w)', text):
                if m.group(1):
                    used.add(int(m.group(2)))
            uses = len(re.findall(re.escape(ex) + r'(?![\w\[])', text))
            if uses > 2:          # declaration + port connection; a bare read uses every bit
                continue
            for k in range(w):
                if k not in used:
                    add(inst, mod, 'forwarded-clock tap of a lane the plan does not build', port, k, k, 'C_forwarded_clock_taps')
    # ---- C' / D: slice clock-copy and C1 band outputs (proof = the RTL text, checked here)
    sl = (Path(root) / 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv').read_text()
    ck_rt_copy = 'assign ck_rt = {8{clk}};' in sl
    c1_bo_zero = "assign bo = 513'd0;" in sl and re.search(r'parameter\s+integer\s+HB\s*=\s*0', sl) is not None
    for ln in lines:
        m = INST_RE.match(ln)
        if not m or not m.group(1).startswith('ot_s81sl_slice'):
            continue
        mod, inst, ps = m.group(1), m.group(2), _ports(m.group(3))
        hb = re.search(r'#\(.*?\.HB\((\d+)\)', ln)
        if ck_rt_copy and 'ck_rt' not in ps:
            add(inst, mod, 'slice ck_rt = {8{clk}} root copy; rt lanes are forwarded by their source frames', 'ck_rt', 0, 7,
                'C_forwarded_clock_taps')
        if c1_bo_zero and 'bo' not in ps and (mod != 'ot_s81sl_slice' or (hb and hb.group(1) == '0')):
            add(inst, mod, "C1 slice (HB 0): bo = 513'd0 in ot_s81sl_slice g_c1 (no band port)", 'bo', 0, 512, 'D_c1_band_out')
    rec['summary'] = {k: dict(entries=len(v), bits=sum(x.get('bits', 0) for x in v)) for k, v in rec.items() if k != 'gaps'}
    rec['summary']['gaps'] = len(rec['gaps'])
    return rec
