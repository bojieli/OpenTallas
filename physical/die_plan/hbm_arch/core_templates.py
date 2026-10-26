#!/usr/bin/env python3
"""TYPE-REDUCE-2/HBM 2026-10-25: one pin template per (RTL master, outline) for the B2n HBM die plan, ID constants
as declared strap_* input pins (OWNER option B, 10-25 07:01).

Why: B2n pins every hard-core instance toward its own neighbours (cores/<module>__<WxH>__<type>_<inst>.json, one
table per instance), and three split masters bake an ID into per-replica piece modules (sfu lane map_lane_j, su
lane_exp lane_lane_id, su lanes4 lane0..3_lane_id).  autopilot ownership.py keys a core design by (RTL master,
outline, pin-table sha), so every table is a separate hardened design.  Commercial practice: a few tile templates
replicated many times -> one fixed pin table per template in the core frame, instances reuse it (whole-instance
orient R0/MX/MY/R180 allowed by the schema; R0 kept unless a mirror cuts the total displacement by >= 20 %).

Deterministic + idempotent: reads the BASE plan from git (BASE_SHA:physical/die_plan/hbm_arch/B2n/...), writes
  B2n/die_plan.json (hard_cores[].module / pins_file / orient / track_offset_um / straps / note),
  B2n/core_conns.json (pin bus keys renamed where a template renames cut pins),
  B2n/cores_tmpl/<module>__<WxH>[__<class>].json (the templates; per-instance tables of untouched cores stay),
  rtl/hbm_accel/cores_split/<dir>/<top>_strap.sv (strap wrapper: ID input ports renamed strap_<port>),
  results/type_reduce2_hbm_1025/{groups.json,displacements.tsv}.

Groups:
  * canonical split masters (physical/die_plan/hbm/cores/harden/canonical_ports_split.json) at one B2n outline;
    members with different NON-ID constants (bankq lanes3 lg*_fst chain-first flags, tied_at_parent data ties) stay
    in separate classes -- they are different netlists, never straps;
  * one non-split module at one outline with several tables.
Excluded (PATH-HBM): partition type 'root' (TKM root + 32 tiles, hc_root tails / hcp_sys share the root partition;
the PATH lead owns its no-ID common/terminal TKM templates) -- recorded in the census only.
Displacement of a pin = |old placed position - new placed position| (Manhattan, core box frame); every pin moved
> REACH um is listed (it needs a relay stage or a re-place of the core).
"""
import collections
import copy
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
PREL = 'physical/die_plan/hbm_arch/B2n'
PDIR = os.path.join(ROOT, PREL)
CANON = 'physical/die_plan/hbm/cores/harden/canonical_ports_split.json'
RES = os.path.join(ROOT, 'results/type_reduce2_hbm_1025')
BASE_SHA = '190ebb428e3f1b43763161d39f9013d77c3e9b0b'      # origin/main 2026-10-25 19:5x (B2n = 871717c83)
REACH = 405.0
ORIENTS = ('R0', 'MX', 'MY', 'R180')
MIRROR_GAIN = 0.20
NEWDIR = 'cores_tmpl'
EXCLUDE_TYPES = {'root'}
# owner option B: ID-only ports of the split masters -> strap_<port> (tools/die_plan/parent_id_straps.py whitelist)
# groups merged by face class only (base: one table for the whole group either stretched a pin past REACH or turned
# ports away from their partners in G0C core_faces -- measured on BASE_SHA by this script without the split)
FACE_SPLIT = {'hfd_ep_static', 'hfd_vms_bank_native_q0_faces', 'ot_hbm_hc_bankq_ft_static__lanes6_7_bank',
              'ot_hbm_hc_bankq_static__lanes6_7_bank', 'ot_hbm_svc_sm_group_rel_id', 'ot_hbm_svc_sm_xcal_rel_t',
              'ot_hbm_svc_vm_kshare_splitstrap', 'ot_hgi_sm_xload_cl2_bfqg', 'pg_lane_exp', 'pg_pretree', 'sfu_lane',
              'ot_hbm_svc_pc_ctrl_leaf_cfg_h9b', 'ot_hbm_svc_vmdel_lane_n', 'ot_hgi_sm_xload_cl2_bdring',
              'ot_hgi_sm_xload_xq_pegress', 'bankq_lanes3', 'ot_hbm_xp_aq_tree13_fmt'}
ID_PORTS = {'map_lane_j', 'lane_lane_id', 'lane0_lane_id', 'lane1_lane_id', 'lane2_lane_id', 'lane3_lane_id'}


def git_show(path):
    return subprocess.check_output(['git', '-C', ROOT, 'show', f'{BASE_SHA}:{path}'])


def opt(o, w, h, x, y):
    if o in ('MY', 'R180'):
        x = w - x
    if o in ('MX', 'R180'):
        y = h - y
    return x, y


def split_bit(n):
    m = re.fullmatch(r'(.*)\[(\d+)\]', n)
    return (m.group(1), int(m.group(2))) if m else (n, None)


def neutral(base):
    return re.sub(r'(?<=_)\d+(?=_)', 'N', base)


def renamer(cut_pins, ports):
    """cut pin -> canonical master port name where the cut pin IS one whole port; else a position-neutral name built
    from the canonical ports it carries (sorted, '__'-joined; e.g. bank0_read_addr__lane0_rd_addr), so the same pin
    of every replica gets the same name; a cut pin with no census mapping keeps a lane-neutral cut name
    (HBM-CORES owns the bit map of the concatenated pins)"""
    pw = {p[0]: p[2] for p in ports}
    users = collections.Counter(cn for m in cut_pins.values() for cn in m)
    whole = {b for b, m in cut_pins.items() if len(m) == 1 and all(users[cn] == 1 and pw.get(cn) == w
                                                                    for cn, w in m.items())}
    # a cut name without position digits is already replica-neutral: kept as is
    cand = {b: ('__'.join(sorted(m)) if (m and neutral(b) != b) else neutral(b)) for b, m in cut_pins.items()
            if b not in whole}
    dup = collections.Counter(cand.values())
    for b in list(cand):
        if dup[cand[b]] > 1:                 # several cut pins carry the same ports: keep the cut suffix to split them
            cand[b] = cand[b] + '__' + neutral(b)

    def base(b):
        if b in whole:
            (cn, _w), = cut_pins[b].items()
            return cn
        return cand.get(b, neutral(b))

    def rn(name):
        b, i = split_bit(name)
        if b in whole:
            (cn, w), = cut_pins[b].items()
            if pw.get(cn) == 1 and w == 1:
                return cn
            return f'{cn}[{i if i is not None else 0}]'
        return base(b) + (f'[{i}]' if i is not None else '')
    return rn, base


def strap_name(port):
    return 'strap_' + port


def main():
    plan = json.loads(git_show(f'{PREL}/die_plan.json'))
    conns = json.loads(git_show(f'{PREL}/core_conns.json'))
    canon = json.loads(git_show(CANON))['types']
    T = plan['partition_types']
    ninst = collections.Counter(p['type'] for p in plan['partitions'])
    piece = {}
    for cn, c in canon.items():
        for tid, v in c['type_ids'].items():
            mod, _wh = re.match(r'(.*)__([\d.]+x[\d.]+)$', tid).groups()
            piece[mod] = (cn, v)
    groups = collections.defaultdict(list)
    for tn in sorted(T):
        if tn in EXCLUDE_TYPES:
            continue
        for i, hc in enumerate(T[tn].get('hard_cores') or []):
            m = hc['module']
            wh = 'x'.join(f'{v:g}' for v in hc['outline_um'])
            if m in piece:
                cn, v = piece[m]
                if cn.startswith('tkm'):
                    continue
                st = v.get('straps', {}) or {}
                ids = {k: x for k, x in st.items() if k in ID_PORTS}
                non_id = {k: x for k, x in st.items() if k not in ID_PORTS}
                cls = hashlib.sha1(json.dumps([non_id, v.get('tied_at_parent') or {}, v.get('open_at_parent') or {}],
                                              sort_keys=True).encode()).hexdigest()[:6]
                rn, rb = renamer(v['cut_pins'], canon[cn]['ports'])
                groups[(cn, wh, cls)].append(dict(type=tn, idx=i, hc=hc, rn=rn, rb=rb, ids=ids, non_id=non_id))
            else:
                groups[(m, wh, '')].append(dict(type=tn, idx=i, hc=hc, rn=(lambda n: n), rb=(lambda b: b), ids={},
                                                non_id={}))
    # face classes: a template may only merge instances whose every port sits on the same core face (the face
    # that points at its partners); instances whose neighbours lie on other sides stay separate templates
    # (a fixed table there would turn ports away from their partners -> G0C core_faces)
    fgroups = {}
    for g, mem in groups.items():
        if g[0] not in FACE_SPLIT:
            fgroups[g] = mem
            continue
        w, h = mem[0]['hc']['outline_um']
        cls_of = {}
        for e in mem:
            P = json.loads(git_show(f"{PREL}/{e['hc']['pins_file']}"))
            P = P['pins'] if isinstance(P, dict) else P
            sig = collections.Counter()
            for p in P:
                x, y = float(p['x']), float(p['y'])
                f = min((x, 'W'), (w - x, 'E'), (y, 'S'), (h - y, 'N'))[1]
                sig[(split_bit(e['rn'](p['name']))[0], f)] += 1
            dom = {}
            for (b, f), n in sig.items():                 # each bus's dominant face
                if n > dom.get(b, ('', 0))[1]:
                    dom[b] = (f, n)
            cls_of.setdefault(json.dumps(sorted((b, f) for b, (f, _n) in dom.items())), []).append(e)
        for j, (_k, ms) in enumerate(sorted(cls_of.items(), key=lambda kv: -len(kv[1]))):
            fgroups[(g[0], g[1], g[2] + (f'f{j}' if len(cls_of) > 1 else ''))] = ms
    groups = fgroups
    os.makedirs(os.path.join(PDIR, NEWDIR), exist_ok=True)
    os.makedirs(RES, exist_ok=True)
    out, disp_rows, wrappers = {}, [], {}
    for g in sorted(groups):
        mem = groups[g]
        cn, wh, cls = g
        is_canon = cn in canon
        if not any(e['ids'] for e in mem) and (len(mem) == 1 or (len({e['hc']['module'] for e in mem}) == 1 and
                                                                  len({e['hc']['pins_file'] for e in mem}) == 1)):
            continue                                              # one entry, no ID: already one design
        tabs = []
        for e in mem:
            P = json.loads(git_show(f"{PREL}/{e['hc']['pins_file']}"))
            P = P['pins'] if isinstance(P, dict) else P
            own = {e['rn'](p['name']): (p['layer'], float(p['x']), float(p['y'])) for p in P}
            if len(own) != len(P):
                tabs = None
                break
            tabs.append(own)
        if tabs is None:
            print(f'SKIP {g}: canonical rename collides')
            out['|'.join(g)] = dict(skipped='canonical rename collides', members=len(mem))
            continue
        shas = {hashlib.sha1(json.dumps(sorted(t.items())).encode()).hexdigest() for t in tabs}
        has_ids = any(e['ids'] for e in mem)
        if (len(shas) == 1 and len({json.dumps(e['ids'], sort_keys=True) for e in mem}) <= 1
                and sum(1 for gg in groups if gg[:2] == g[:2] and gg[2][:6] == g[2][:6]) == 1):
            continue                                              # one table, one ID value: already one design
        if len(shas) == 1 and not has_ids and len({e['hc']['module'] for e in mem}) == 1:
            continue                                              # already one design
        if len({frozenset(t) for t in tabs}) != 1:
            print(f'SKIP {g}: members keep different pin name sets after the canonical rename')
            out['|'.join(g)] = dict(skipped='pin name sets differ after canonical rename', members=len(mem))
            continue
        w, h = mem[0]['hc']['outline_um']
        offs = {tuple(e['hc'].get('track_offset_um', [0.0, 0.0])) for e in mem}
        # placed (core box frame incl. track offset) old positions
        placed = []
        for e, t in zip(mem, tabs):
            ox, oy = e['hc'].get('track_offset_um', [0.0, 0.0])
            placed.append({n: (x + ox, y + oy) for n, (_l, x, y) in t.items()})
        best = None
        uniq = {}
        for k, t in enumerate(tabs):
            uniq.setdefault(hashlib.sha1(json.dumps(sorted(t.items())).encode()).hexdigest(), k)
        for _sha, k in sorted(uniq.items()):
            off = mem[k]['hc'].get('track_offset_um', [0.0, 0.0])
            tot, choice = 0.0, []
            for pm in placed:
                res = {}
                for o in ORIENTS:
                    d = []
                    for n, (X, Y) in pm.items():
                        _l, cx, cy = tabs[k][n]
                        tx, ty = opt(o, w, h, cx, cy)
                        d.append((abs(X - tx - off[0]) + abs(Y - ty - off[1]), n))
                    res[o] = (sum(x for x, _ in d), d)
                o = 'R0'
                alt = min(ORIENTS, key=lambda q: res[q][0])
                if res[alt][0] < (1 - MIRROR_GAIN) * res['R0'][0]:
                    o = alt
                tot += res[o][0]
                choice.append((o, res[o][1]))
            if best is None or tot < best[0]:
                best = (tot, k, choice)
        tot, k, choice = best
        tabk = tabs[k]
        if any(x > REACH for _o, d in choice for x, _ in d) and all(o == 'R0' for o, _ in choice):
            # consensus template: per pin the lower median (x, y) of the members' old positions (each a real member
            # coordinate, so it stays on that layer's track lattice); a pin whose median spot is taken keeps the
            # best member's position.  Minimises the summed displacement per pin instead of copying one slot.
            off = mem[k]['hc'].get('track_offset_um', [0.0, 0.0])
            med = {}
            for n, (l, _x, _y) in tabk.items():
                xs = sorted(pm[n][0] - off[0] for pm in placed)
                ys = sorted(pm[n][1] - off[1] for pm in placed)
                med[n] = (l, round(xs[(len(xs) - 1) // 2], 4), round(ys[(len(ys) - 1) // 2], 4))
            cnt = collections.Counter(med.values())
            cons = {n: (v if cnt[v] == 1 else tabk[n]) for n, v in med.items()}
            if len(set(cons.values())) == len(cons):
                cch = [('R0', [(abs(X - cons[n][1] - off[0]) + abs(Y - cons[n][2] - off[1]), n)
                               for n, (X, Y) in pm.items()]) for pm in placed]
                cfar = sum(1 for _o, d in cch for x, _ in d if x > REACH)
                ofar = sum(1 for _o, d in choice for x, _ in d if x > REACH)
                if cfar < ofar:
                    tabk, choice, tot = cons, cch, sum(x for _o, d in cch for x, _ in d)
                    print(f"  consensus template {'|'.join(g)}: pins >{REACH:g} {ofar} -> {cfar}")
        nfar = [sum(1 for x, _ in d if x > REACH) for _o, d in choice]
        if sum(nfar):
            # one fixed table would stretch connections past the reach: NOT applied (needs a relay stage per far
            # pin in the latency table, or a re-place of the parent so every instance sees the same neighbours)
            for e, (o, d), nf in zip(mem, choice, nfar):
                for x, n in sorted([x for x in d if x[0] > REACH], reverse=True):
                    disp_rows.append((e['type'], e['hc']['inst'], '|'.join(g), n, round(x, 1), 'DEFERRED-not-applied'))
            out['|'.join(g)] = dict(deferred='pins > 405 um', members=len(mem), tables_before=len(shas),
                                    pins_over_405=sum(nfar), insts_over_405=sum(1 for x in nfar if x),
                                    template_from=f"{mem[k]['type']}/{mem[k]['hc']['inst']}")
            print(f"DEFER {'|'.join(g)}: {len(mem)} entries, {len(shas)} tables; pins >{REACH:g}: {sum(nfar)}")
            if not has_ids:
                continue
            # cause (2) alone: the ID still becomes a strap, so the replicas that already share one slot table become
            # one design (one template per distinct table, 0 um displacement); the cause (3) merge stays deferred
            subs = []
            for j, (sha, k0) in enumerate(sorted(uniq.items(), key=lambda kv: kv[1])):
                sub = [i for i, t in enumerate(tabs) if hashlib.sha1(json.dumps(sorted(t.items())).encode()).hexdigest() == sha]
                ox, oy = mem[sub[0]]['hc'].get('track_offset_um', [0.0, 0.0])
                ch = [('R0', [(abs(placed[i][n][0] - x - ox) + abs(placed[i][n][1] - y - oy), n)
                              for n, (_l, x, y) in tabs[sub[0]].items()]) for i in sub]
                subs.append((sub, tabs[sub[0]], ch, f'__t{j}'))
        else:
            subs = [(list(range(len(mem))), tabk, choice, '')]
        for sub, tabk, choice, sfx in subs:
            smem = [mem[i] for i in sub]
            tmpl = dict(tabk)
            toff = list((smem[0] if sfx else mem[k])['hc'].get('track_offset_um', [0.0, 0.0]))
            module = mem[0]['hc']['module']
            straps = {}
            if is_canon:
                top = canon[cn]['top']
                pw = {p[0]: p[2] for p in canon[cn]['ports']}
                id_ports = sorted({s for e in mem for s in e['ids']})
                if id_ports:
                    module = top + '_strap'
                    wrappers[module] = (cn, id_ports)
                    straps = {strap_name(s): pw[s] for s in id_ports}
                    clk = sorted((v for n, v in tmpl.items() if 'clk' in n), key=lambda v: (v[2], v[1]))[0]
                    # strap pins go on free lattice slots of the existing pin rows (same layer + y), the clock pin's
                    # row first, then the rows nearest it; the slot lattice = the row's own smallest pin gap
                    rows_ = collections.defaultdict(list)
                    for l, x, y in tmpl.values():
                        rows_[(l, round(y, 4))].append(x)
                    need = sum(straps.values())
                    picked = []
                    for (l, y) in sorted(rows_, key=lambda r: (r[0] != clk[0], abs(r[1] - clk[2]), r)):
                        xs = sorted(rows_[(l, y)])
                        gaps = [round(q - p, 4) for p, q in zip(xs, xs[1:]) if q - p > 1e-6]
                        if not gaps:
                            continue
                        pitch = min(gaps)
                        x0 = xs[0] - pitch * int(xs[0] / pitch)
                        occ = {round((x - x0) / pitch) for x in xs}
                        cand = sorted((k for k in range(int((w - x0) / pitch) + 1)
                                       if k not in occ and pitch <= x0 + k * pitch <= w - pitch),
                                      key=lambda k: (abs(x0 + k * pitch - clk[1]), k))
                        for k_ in cand[:need - len(picked)]:
                            picked.append((l, round(x0 + k_ * pitch, 4), y))
                        if len(picked) >= need:
                            break
                    if len(picked) < need:
                        raise SystemExit(f'{g}: only {len(picked)} free row slots < {need}')
                    slots = iter(sorted(picked, key=lambda p: (p[0] != clk[0], abs(p[2] - clk[2]), p[1])))
                    for s_, wdt in straps.items():
                        for b_ in range(wdt):
                            tmpl[f'{s_}[{b_}]' if wdt > 1 else s_] = next(slots)
            stem = f"{module}__{wh}" + (f"__{cls}" if cls and sum(1 for gg in groups if gg[:2] == g[:2]) > 1 else '') + sfx
            rel = f'{NEWDIR}/{stem}.json'
            rows = [dict(name=n, layer=l, x=round(x, 4), y=round(y, 4)) for n, (l, x, y) in sorted(tmpl.items())]
            open(os.path.join(PDIR, rel), 'w').write(json.dumps(rows, indent=0) + '\n')
            gd = dict(master=cn, outline=wh, cls=cls, module=module, pins_file=rel, members=[], straps=straps,
                      tables_before=len(shas), template_from=f"{(smem[0] if sfx else mem[k])['type']}/{(smem[0] if sfx else mem[k])['hc']['inst']}",
                      total_disp_um=round(tot, 1))
            for e, (o, d) in zip(smem, choice):
                ent = T[e['type']]['hard_cores'][e['idx']]
                far = sorted([x for x in d if x[0] > REACH], reverse=True)
                ds = sorted(x for x, _ in d)
                gd['members'].append(dict(type=e['type'], inst=ent['inst'], old_module=ent['module'],
                                          old_pins=ent['pins_file'], orient=o, replicas=ninst[e['type']],
                                          p50=round(ds[len(ds) // 2], 2), p90=round(ds[int(len(ds) * 0.9)], 2),
                                          max=round(ds[-1], 2), n_over_405=len(far)))
                for x, n in far:
                    disp_rows.append((e['type'], ent['inst'], '|'.join(g), n, round(x, 1), 'APPLIED'))
                old_mod, old_pf = ent['module'], ent['pins_file']
                if straps:
                    ent['module'] = module           # strap master; other groups keep their (netlist-identical) piece module
                ent['pins_file'] = rel
                ent['track_offset_um'] = list(toff)
                if o != 'R0':
                    ent['orient'] = o
                if e['ids']:
                    ent['straps'] = [dict(port=strap_name(s), width=len(v), value=f"{len(v)}'b{v}")
                                     for s, v in sorted(e['ids'].items())]
                ent['note'] = (f"TYPE-REDUCE-2/HBM 10-25: one pin template per (master, outline) ({rel}), orient {o}"
                               + (f"; ID straps {[strap_name(s) for s in sorted(e['ids'])]} tied at the parent "
                                  "(owner option B)" if e['ids'] else '')
                               + f"; was {old_mod} {old_pf} | " + ent.get('note', ''))
                # core_conns keys = core pin bus names (renamed with the template)
                cc = conns.get(e['type'], {}).get(ent['inst'])
                if cc is not None and is_canon:
                    new = {}
                    for b, v in cc.items():
                        nb = e['rb'](b)
                        if nb in new and new[nb] != v:
                            new[nb] = sorted(set(new[nb]) | set(v))
                        else:
                            new[nb] = v
                    conns[e['type']][ent['inst']] = new
            out['|'.join(g) + sfx] = gd
            print(f"{'|'.join(g)}: {len(smem)} entries, {len(shas)} tables -> 1 ({module}), straps {sorted(straps)}, "
                  f"total disp {sum(sum(x for x, _ in d) for _o, d in choice):.0f} um, pins >{REACH:g}: {sum(m['n_over_405'] for m in gd['members'])}")
    # strap wrappers: the master with each ID input renamed strap_<port> (no logic)
    for wm, (cn, id_ports) in sorted(wrappers.items()):
        c = canon[cn]
        d = os.path.join(ROOT, os.path.dirname(c['file']))
        lines = [f"// GENERATED by physical/die_plan/hbm_arch/core_templates.py (TYPE-REDUCE-2/HBM 2026-10-25). Do not edit.",
                 f"// One hardened design for every replica of {c['top']}: the ID-only inputs {', '.join(id_ports)} are",
                 "// declared strap_* input pins (OWNER option B 10-25 07:01): tied at the parent with TIEHI/TIELO,",
                 "// set_false_path -from in the kit SDC, no pin register, no case analysis.",
                 "`timescale 1ns/1ps", "`default_nettype none", f"module {wm} ("]
        decl = []
        for n, dr, wdt, lsb in c['ports']:
            nn = strap_name(n) if n in id_ports else n
            rng = f'[{wdt - 1 + lsb}:{lsb}] ' if wdt > 1 or lsb else ''
            decl.append(f"    {dr} wire {rng}{nn}")
        lines.append(',\n'.join(decl))
        lines.append(');')
        conn = [f"        .{n}({strap_name(n) if n in id_ports else n})" for n, _d, _w, _l in c['ports']]
        lines += [f"    {c['top']} u_core (", ',\n'.join(conn), '    );', 'endmodule', '`default_nettype wire', '']
        open(os.path.join(d, wm + '.sv'), 'w').write('\n'.join(lines))
    plan['note'] = plan.get('note', '') + (' | TYPE-REDUCE-2/HBM 2026-10-25: one pin template per (RTL master, outline), '
                                           'ID straps option B (physical/die_plan/hbm_arch/core_templates.py).')
    json.dump(plan, open(os.path.join(PDIR, 'die_plan.json'), 'w'), indent=0)
    json.dump(conns, open(os.path.join(PDIR, 'core_conns.json'), 'w'), indent=0)
    for fn in ('die_plan.json', 'core_conns.json'):       # base files end with a newline
        open(os.path.join(PDIR, fn), 'a').write('\n')
    json.dump(dict(base=BASE_SHA, groups=out), open(os.path.join(RES, 'groups.json'), 'w'), indent=1)
    with open(os.path.join(RES, 'displacements.tsv'), 'w') as f:
        f.write('type\tinst\tgroup\tpin\tdisp_um\tstatus\n')
        for r in disp_rows:
            f.write('\t'.join(map(str, r)) + '\n')
    print('pins >405 um (applied):', sum(1 for r in disp_rows if r[-1] == 'APPLIED'), 'deferred:', sum(1 for r in disp_rows if r[-1] != 'APPLIED'), 'wrappers:', sorted(wrappers))


if __name__ == '__main__':
    main()
