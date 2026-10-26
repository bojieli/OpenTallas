#!/usr/bin/env python3
"""STW-S81c-DIE-FRAME 10-22: S81 frame (col_h9 / col_h10) VECTOR-LANDED successor kits.

Measured cause of the fs1/fs1x/fs1w/fs1e GPL non-convergence (h9 3_3 ovf 0.40 after 7 h, h10 16.6-21 % overflowed GCells):
lp.py landed every region crossing of the scalar-netted frame ONE BIT AT A TIME (col_h9 3,017 rings, col_h10 3,143).  Each
1-bit ring / read pair costs ~38 flops and 20 ring -> read wires (bank 4 + epoch 12 + valid 4), and all of them relax
onto the two region-boundary rows, which are bf rows (bf_col W + front roots + bf_col E: 25 / 56 um channels, M7-blocked)
-> 13.2k wires across y 2160 vs 3.6k one row up (tools: framecut.py in the lane), 148k frame flops, roots 47k / 70k / 31k.

Fix (lp.py opt-in landing_vector_group): the 3,017 crossings share only 31-34 (source region, destination region, source
child, reader set) groups; each group becomes ONE vector landing (same D 4 / E = K 2, +3 edges per net, same reset-leaf age:
per-bit LANDING-CONTRACT and every net's schedule unchanged).  Landing flops 78.4k -> 18.1k (h9), reset forest 6.6k -> 0.65k.

  frame_vg_kit.py --master col_h9 --tag vg  --base-kit s81frame_col_h9_rf3rlfs1x            FB: same regions as rf3r
  frame_vg_kit.py --master col_h9 --tag vgc --base-kit ... --cuts 1170,2250                MAIN: regions re-cut by rows
                                                                                             (3 element rows per region,
                                                                                             boundaries off the bf rows)
Writes: lp spec results/arch/s81_dv_1016/frame_l4_cluster/compiler/<tag>/<master>_spec.json, LP RTL + bench + record in
rtl/dsrom_sys/s81_dv/frame_lp/<tag>/, the schedule (frame_schedule.py) beside the record, kit RTL
rtl/dsrom_sys/s81_dv/frame_lp/kit/<master>_l4_lp_kit_<tag>.sv (hard-child #() stripped + rst_n 2-stage landing + xo relay
reset on xk = the rf3r transforms of tools/s81_dv/frame_kit.py), the bench twin <tag>/<master>_l4_lp_rf3r.sv, and the
ref_tile spec tools/ref_tile/specs_s81frame/<name>.json (base kit geometry, pins, outline, clocks, forwarded metadata kept).
Same frame ports (ck_r0..2, x/xk/xo/xok/ret/lk/rst_n), same pin ranges, same outline as the base kit.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/s81_dv'), str(ROOT / 'tools/landed_parent')]
import frame_kit as FK  # noqa: E402
import lp  # noqa: E402

REC = 'results/arch/s81_dv_1016/frame_l4_cluster/compiler'
LPDIR = 'rtl/dsrom_sys/s81_dv/frame_lp'
ROM = 'ot_rom_4096x72_m8'


def lef_size(view):
    n = view.split('/')[-1]
    t = (ROOT / view / f'{n}.lef').read_text()
    m = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', t)
    return float(m.group(1)), float(m.group(2))


def inst_y(kit_spec, lp_spec, iters=60):
    """y per lp instance: hard children / macros at their kit centre; soft relays relaxed to their netlist neighbours."""
    y = {}
    for c in kit_spec['children'] + kit_spec['macros']:
        w, h = lef_size(c['view'])
        y[c['inst'].split('.')[0]] = c['at'][1] + h / 2
    P = lp.Parent(lp_spec)
    nets = collections.defaultdict(set)
    for ins in P.insts:
        for pin, ex in ins['conns'].items():
            if pin in (lp_spec.get('clock_pins') or []):
                continue
            for n in lp.idents(ex):
                nets[n].add(ins['inst'])
    nb = collections.defaultdict(list)
    for ks in nets.values():
        if len(ks) <= 40:
            for a in ks:
                nb[a] += [b for b in ks if b != a]
    soft = [i['inst'] for i in P.insts if i['inst'] not in y]
    for s in soft:
        y[s] = kit_spec['outline']['h'] / 2
    for _ in range(iters):
        for s in soft:
            ys = [y[b] for b in nb[s]]
            if ys:
                y[s] = sum(ys) / len(ys)
    return y, P


def audit_compare(spec, ref_spec, ref_rtl):
    """lp region audit of the vector-landed RTL vs the bound rf3r RTL: PASS iff the vector RTL has NO fail the bound RTL
    lacks (the only fails are the forwarded-domain port reads of x / xk, by design: u_xo* on xk[k], crs4 u_cf)."""
    S = lp.load(spec)
    A = lp.audit(S, (ROOT / S['out_dir'] / f"{S['top']}_lp.sv").read_text())
    B = lp.audit(lp.load(ref_spec), (ROOT / ref_rtl).read_text())
    new = sorted(set(A['fails']) - set(B['fails']))
    print(f"LP_AUDIT vector landings={A.get('landings')} reset_hops={A.get('reset_hops')} fails={len(A['fails'])}; "
          f"rf3r landings={B.get('landings')} fails={len(B['fails'])}; NEW fails={len(new)}")
    for f in new[:20]:
        print('NEW', f)
    unl = ROOT / S['out_dir'] / '_unland_probe.sv'
    lp.gen(S, mut_unland=True, rtl_out=unl)
    U = lp.audit(S, unl.read_text())
    unl.unlink()
    caught = any('UNLANDED' in f and f not in A['fails'] for f in U['fails'])
    print('LP_AUDIT unland mutant', 'CAUGHT' if caught else 'MISSED')
    return 0 if not new and caught else 1


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--audit-compare':
        raise SystemExit(audit_compare(*sys.argv[2:5]))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--master', required=True, choices=['col_h9', 'col_h10'])
    ap.add_argument('--tag', required=True)
    ap.add_argument('--base-kit', required=True, help='physical/ref_tile/<base>/spec.json geometry source')
    ap.add_argument('--lp-spec', help='rf3r lp spec (default compiler/rf3r/<master>_spec.json)')
    ap.add_argument('--cuts', help='y1,y2: re-cut the 3 regions at these frame y (um) by instance centre')
    ap.add_argument('--name', help='kit name (default s81frame_<master>_<tag>)')
    ap.add_argument('--why', default='')
    a = ap.parse_args()
    m, tag = a.master, a.tag
    name = a.name or f's81frame_{m}_{tag}'
    base = json.loads((ROOT / 'physical/ref_tile' / a.base_kit / 'spec.json').read_text())
    lps = json.loads((ROOT / (a.lp_spec or f'{REC}/rf3r/{m}_spec.json')).read_text())
    lps['landing_vector_group'] = True
    lps['out_dir'] = f'{LPDIR}/{tag}'
    lps['record_dir'] = f'{REC}/{tag}'
    if a.cuts:
        c1, c2 = map(float, a.cuts.split(','))
        lps['_spec_path'] = 'x'
        y, P = inst_y(base, lps)
        reg = collections.defaultdict(list)
        for i, v in y.items():
            reg['r%d' % ((v > c1) + (v > c2))].append(i)
        core = {'u_cf', 'u_xo0', 'u_xo1', 'u_xo2', 'u_xo3'}
        for i in core:
            if i in y and i not in reg['r0']:
                raise SystemExit(f'{i} (core: x / xk ports) falls outside r0 with cuts {a.cuts}')
        hard = {c['inst'].split('.')[0]: c for c in base['children'] + base['macros']}
        for r in lps['regions']:
            r['insts'] = sorted(reg[r['name']])
            ks = [hard[i] for i in r['insts'] if i in hard]
            ar = [(lef_size(k['view']), k['at']) for k in ks]
            tot = sum(w * h for (w, h), _ in ar)
            r['centre'] = [round(sum((x + w / 2) * w * h for (w, h), (x, _) in ar) / tot, 1),
                           round(sum((yy + h / 2) * w * h for (w, h), (_, yy) in ar) / tot, 1)]
        lps.pop('_spec_path', None)
    sd = ROOT / REC / tag
    sd.mkdir(parents=True, exist_ok=True)
    sp = sd / f'{m}_spec.json'
    sp.write_text(json.dumps(lps, indent=1) + '\n')
    lp.gen(lp.load(str(sp)))
    rec = json.loads((sd / f'{m}_l4_lp_record.json').read_text())
    # schedule (the frame bench plan set and the compiler calendar): per-net crossings do not depend on grouping
    out = subprocess.run([sys.executable, str(ROOT / 'tools/s81_dv/frame_schedule.py'), str(sp), '--out',
                          str(sd / f'{m}_schedule.json')], capture_output=True, text=True, cwd=ROOT)
    if out.returncode:
        raise SystemExit(out.stderr[-2000:])
    print(out.stdout.strip())
    # kit RTL: hard-child #() stripped (frame_kit.kit_rtl), then the rf3r variant (rst_n landing + xk reset sync)
    lpsv = ROOT / LPDIR / tag / f'{m}_l4_lp.sv'
    t = lpsv.read_text()
    hard_m = {c['view'].split('/')[-1] for c in base['children'] + base['macros']} | {'ot_v41_bf_col', 'dsfd_bf_col'}
    # PATH-S81/F2 10-25: the stripped overrides are the hardened config of each view -> recorded in the kit sidecar
    t2, n, hparams, hsites = FK.HP.strip_hard(t, hard_m, str(lpsv.relative_to(ROOT)))
    t2 = re.sub(r'\bparameter\s+string\s+', 'parameter ', t2)
    kit0 = f'{LPDIR}/kit/{m}_l4_lp_kit_{tag}0.sv'
    (ROOT / kit0).write_text(f'// GENERATED by tools/s81_dv/frame_vg_kit.py from {lpsv.relative_to(ROOT)} (sha256 '
                             f'{hashlib.sha256(t.encode()).hexdigest()}): hard-child #() overrides removed ({n} sites)\n' + t2)
    kit = f'{LPDIR}/kit/{m}_l4_lp_kit_{tag}.sv'
    FK.variant_rtl(m, kit0, kit, 0, True)
    FK.HP.write_sidecar(ROOT / FK.HP.sidecar_path(kit), hparams, hsites, lpsv.relative_to(ROOT), t)
    twin = f'{LPDIR}/{tag}/{m}_l4_lp_rf3r.sv'
    FK.variant_rtl(m, f'{LPDIR}/{tag}/{m}_l4_lp.sv', twin, 0, True)
    (ROOT / kit0).unlink()
    # ref_tile spec: base kit geometry / pins / clocks, new sources + record + ROM roots + benches
    s = json.loads(json.dumps(base))
    s['name'] = name
    old_kit = next(f for f in s['sources'] if '/kit/' in f and f.endswith('.sv') and '_l4_lp_kit' in f)
    s['sources'] = [kit if f == old_kit else f for f in s['sources']]
    s['landed_record'] = f'{REC}/{tag}/{m}_l4_lp_record.json'
    s['frame']['lp_rtl'] = str(lpsv.relative_to(ROOT))
    s['frame']['lp_rtl_sha256'] = hashlib.sha256(t.encode()).hexdigest()
    s['frame']['landing'] = dict(vector_group=True, landings=len(rec['landings']), flops=rec['flops'],
                                 bits=sum(L['width'] for L in rec['landings']))
    kt = (ROOT / kit).read_text()
    roms = dict(re.findall(rf'\b{ROM}\s+(u_c\w+)\s*\(.*?\.clk\((ck_r\d)\)', kt))
    insts = [x['inst'] for x in s['macros'] if Path(x['view']).name == ROM]
    if set(roms) != set(insts):
        raise SystemExit(f'ROM instances in kit RTL {len(roms)} != spec macros {len(insts)}')
    s['soft_root_macro_bindings'] = {i: dict(master=ROM, clock_pin='clk', root=roms[i]) for i in sorted(insts)}
    s['structural_change'] = s.get('structural_change', '') + (
        f' | {name} (STW-S81c-DIE-FRAME 10-22): VECTOR LANDINGS (lp landing_vector_group): '
        f"{rec['audit'].get('landings', len(rec['landings']))} vector ring/read pairs carry the "
        f"{sum(L['width'] for L in rec['landings'])} crossing bits (was one 1-bit ring per bit: 3,017 h9 / 3,143 h10, "
        f"~38 flops + 20 ring->read wires each, piled on the bf-row region boundaries = the GPL routability failure); "
        f"landing flops {rec['flops']['landing']}, reset forest {rec['flops']['reset']}; per-net D/E/K, +3 edges and reset "
        f"age unchanged" + (f'; regions re-cut at y {a.cuts} (3 element rows each, boundaries off the bf rows)' if a.cuts else
                           '; regions = rf3r') + (f'; {a.why}' if a.why else ''))
    s['reroute_reason'] = dict(kind='structural_change', reason=(
        f'{a.base_kit}: GPL 3_3 routability non-convergence from 3k one-bit landings on the bf-row region boundaries -> '
        f'vector landings (same ports, pins, outline, clocks)' + (f', regions re-cut {a.cuts}' if a.cuts else '')))
    s.pop('slot_change_request', None)
    j = s['job']
    j['owner'] = 'Claude:STW-S81c-DIE-FRAME'
    j['branch'] = 'claude/s81c-frame-1022'
    j['tag'] = tag
    j['purpose'] = f'S81 {m} landed frame cluster -- {tag}: vector landings' + (' + row re-cut' if a.cuts else '')
    j['views_to'] = f'physical/ref_tile/{name}/views'
    j['record_to'] = f'results/rtl/ref_tile/{name}'
    j['extra_paths'] = sorted(set(j.get('extra_paths', [])) | {f'{REC}/{tag}', f'{LPDIR}/{tag}'})
    benches = FK.frame_benches(m, name.replace(f'_{tag}', '_rf3r'), kit0.replace(f'_kit_{tag}0.sv', '_kit.sv'), kit)
    sched = f'{REC}/{tag}/{m}_schedule.json'
    for b in benches:
        b['cmd'] = b['cmd'].replace(f'FRAME_LP_SV=rtl/dsrom_sys/s81_dv/frame_lp/{m}_l4_lp_rf3r.sv',
                                    f'FRAME_LP_SV={twin} FRAME_SCHED={sched}')
        if b['name'] == 'reset_crossing_audit_mutant_rf3':
            b['cmd'] = f'python3 tools/s81_dv/frame_reset_audit.py {LPDIR}/kit/{m}_l4_lp_kit_rf3.sv'
    lpb = f'{LPDIR}/{tag}/{m}_l4_lp_bench.sh'
    # lockstep landed vs the flat parent (+3 edges per landed net) with mutants 1 (landing 0 bypassed), 2 (read K+1),
    # 4 (u_e0 reset run 400 long); the generated script's own exit also folds in the lp region audit, whose only fails are
    # the PRE-EXISTING port x / xk forwarded-domain reads (u_xo* on xk, crs4 u_cf), identical on the bound rf3r RTL
    # (lp_audit_vs_rf3r below proves the fail set is unchanged), so the verdict here is read from the MUT lines.
    # (no lp lockstep bench: lp.py's own tb binds the ROM bb model, which has no INSTANCE parameter, so it cannot build
    # for a ROM frame; the frame plan/each benches + 3 mutants above are the lockstep proof of the vector-landed RTL)
    benches.append(dict(name='lp_audit_vs_rf3r', expect='pass', threads=1, peak_ram_gb=4,
                        cmd=(f'python3 tools/s81_dv/frame_vg_kit.py --audit-compare {REC}/{tag}/{m}_spec.json '
                             f'{REC}/rf3r/{m}_spec.json {LPDIR}/{m}_l4_lp.sv')))
    j['benches'] = benches
    o = ROOT / 'tools/ref_tile/specs_s81frame' / f'{name}.json'
    o.parent.mkdir(parents=True, exist_ok=True)
    o.write_text(json.dumps(s, indent=1) + '\n')
    print(f'{name}: landings {len(rec["landings"])} flops {rec["flops"]} audit {rec["audit"]["ok"]} '
          f'{rec["audit"].get("fails", [])[:1]}; spec {o.relative_to(ROOT)}; kit RTL {kit}; twin {twin}')


if __name__ == '__main__':
    main()
