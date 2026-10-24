#!/usr/bin/env python3
"""KV-P7-HUB 10-23: attention-stack (astk) hard cores for kv3_hub_Eo / kv3_hub_Wo (GEOM-REVIEW7 20:18 FAIL FIX (1)).

The G3 kit-rtl probes of hub_Eo (399k synth / 415k placed: over the 400k cap with no hard cores) and hub_Wo (287k / 294k)
showed the astk logic GPL-scattered into clumps and 1-mm FF columns far from the windows it serves.  Each astk instance
(<q> = EN / ES on hub_Eo, WN / WS on hub_Wo) becomes ONE planned hard core:

    astk_<q> = astk_<q>__g_phys_fault_u_fault (qkd_astk_fault_join) + astk_<q>__u_strip_u_strip_g_zn_0..3__u_zn
               (qkd_astk_zn_head_p + 3 x qkd_astk_zn) + astk_<q>__u_strip_u_strip_u_ctl (qkd_astk_ctl_s)

module kv3_astk_<q> (one module per instance: the four stacks differ only in their ZC / ST quadrant constants; CORE-KS
may merge them into one master with a 2-bit strap).  Outline = as-built synth std area (cores/astk_synth_v38h.json:
hierarchical Yosys + ABC on the BINDER3 kv39 kit RTL, ASAP7 RVT TT, flop FIFOs as the as-built astk kits
(SYNTH_MEMORY_MAX_BITS 32768)) / FILL, square-ish on the 8.64-um lattice.  Site: the core abuts (through a face band)
the N (q = *N) or S (q = *S) windows it talks to (qo 572 out / xo 267 + zo 138 + fault in = 978 of its ~1.4k boundary
bits); N/S band BAND_NS, E/W band toward the hub's outer face BAND_EW (ft inlets on that face pass between the core and the
face).  hub_Wo is the x-mirror of hub_Eo (its windows are mirrored), so its cores are mirrored too.  Outline, buses,
ft_slots, lanes and ports are untouched; only partition_types.{kv3_hub_Eo,kv3_hub_Wo}.hard_cores is written.

Pins (--gen RTL_DIR, top-down, as core_pins_v37p.py: boundary bits of the bound partition netlist kv39
rtl/<type>_part.sv, face = best facing to partners, even spread on M4 (E/W) / M5 (N/S) plan tracks) go to
cores/kv3_astk_<q>_pins.json; the cores' connectivity is merged into core_conns.json (entries of the two types only).
usage: post_v38h.py die_plan.json PLAN_DIR [--gen RTL_DIR] > die_plan.json"""
import json
import math
import re
import sys
from pathlib import Path

G = 8.64
FILL = 0.55          # std-cell utilisation of a hardened astk core (as-built astk kits PD 0.6; FIFO flops dense)
BAND_NS = 3 * G      # 25.92 um >= 22: face-register band between the core and its N/S windows
BAND_EW = 6 * G      # 51.84 um: E (hub_Eo) / W (hub_Wo) face band + escape channel for the ft inlets beside the corner
TYPES = {'kv3_hub_Eo': ('EN', 'ES'), 'kv3_hub_Wo': ('WN', 'WS')}
MIRROR = {'kv3_hub_Eo': False, 'kv3_hub_Wo': True}


def members(t, q):
    pre = f'astk_{q}__'
    return [c['inst'] for c in t['contents'] if c['inst'].startswith(pre)]


def lat(v):
    return round(math.ceil(v / G - 1e-9) * G, 6)


def cores_for(tn, t, syn):
    W, H = t['outline_um']
    out = []
    for q in TYPES[tn]:
        mem = members(t, q)
        assert len(mem) == 6, (tn, q, mem)
        s = syn[q]
        area = s['std_area_um2'] / FILL
        cw = lat(math.sqrt(area))
        ch = lat(area / cw)
        x = W - BAND_EW - cw
        if MIRROR[tn]:
            x = W - x - cw
        y = H - BAND_NS - ch if q.endswith('N') else BAND_NS
        x = round(round(x / G) * G, 6)
        y = round(round(y / G) * G, 6)
        out.append(dict(
            inst=f'astk_{q}', module=f'kv3_astk_{q}', origin_um=[x, y], outline_um=[cw, ch], orient='R0',
            track_offset_um=[0.0, 0.0], pins_file=f'cores/kv3_astk_{q}_pins.json',
            note=(f"astk_core: {' + '.join(mem)}; PLANNED core (KV-P7-HUB v3.8h): {s['cells']} cells / "
                  f"{s['std_area_um2']:.0f} um2 std as-built synth (cores/astk_synth_v38h.json) at fill {FILL}; "
                  f"N/S band {BAND_NS:.2f}, outer-face band {BAND_EW:.2f}; lef/lib pending (CORE-KS harden)")))
    return out


def gen_pins(plan, rtl, out):
    """top-down pins for the astk cores only (core_pins_v37p machinery, member grouping = 'astk_core:' note)."""
    import core_pins_v37p as CP
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/die_plan'))
    import check as C
    import schema as S
    keep = set(TYPES)
    sub = json.loads(json.dumps(plan))
    for tn, t in sub['partition_types'].items():
        if tn not in keep:
            t.pop('hard_cores', None)
        for hc in t.get('hard_cores', []):
            hc.pop('pins_file', None)          # planned: the pin tool assigns them (a pins_file marks a closed view)
    orig_members, orig_rel = CP.members, CP.rel

    def members(t, hc):
        m = re.match(r'astk_core: ([^;]+)', hc.get('note', ''))
        if m:
            pre = [x.strip() for x in m.group(1).split('+')]
            return [c['inst'] for c in t['contents'] if c['inst'] in pre], pre
        return orig_members(t, hc)

    def rel(inst, pre, hc):
        if hc['module'].startswith('kv3_astk_'):
            return re.sub(r'^astk_[EW][NS]__', '', inst).replace('__', '_')
        return orig_rel(inst, pre, hc)
    CP.members, CP.rel = members, rel
    CP.SWAP = {}
    og = CP.Net.graph

    def graph(self):
        # clock / reset nets join every station of the partition: without this filter the station-chain fixpoint in
        # core_pins_v37p spreads every bus to every pin group (all partners = all 60 hub buses)
        g = og(self)
        return {k: v for k, v in g.items() if not any(CP.CLKRST.match(e[1]) for e in v)}
    CP.Net.graph = graph
    CP.apply_layout = lambda types: {}     # v3.7p core moves are already in the plan
    CP.C, CP.S, CP.SP = C, S, S.Plan(sub)
    tmp = Path(out) / '_v38h_tmp'
    tmp.mkdir(parents=True, exist_ok=True)
    pj = tmp / 'plan.json'
    pj.write_text(json.dumps(sub))
    argv = sys.argv
    sys.argv = ['core_pins_v37p.py', str(pj), rtl, str(tmp)]
    try:
        CP.main()
    finally:
        sys.argv = argv
    od = Path(out)
    for f in (tmp / 'cores').glob('kv3_astk_*_pins.json'):
        (od / 'cores' / f.name).write_text(f.read_text())
    new = json.loads((tmp / 'core_conns.json').read_text())
    cc = json.loads((od / 'core_conns.json').read_text())
    for tn in keep:
        cc[tn] = new.get(tn, {})
    (od / 'core_conns.json').write_text(json.dumps(cc, separators=(',', ':'), sort_keys=True))
    patch = json.loads((tmp / 'cores' / 'core_patch_v37p.json').read_text())
    for f in tmp.rglob('*'):
        if f.is_file():
            f.unlink()
    for d in sorted(tmp.rglob('*'), reverse=True):
        d.rmdir()
    tmp.rmdir()
    return {tn: patch.get(tn, {}) for tn in keep}


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    rtl = sys.argv[sys.argv.index('--gen') + 1] if '--gen' in sys.argv else None
    if rtl:
        a.remove(rtl)
    plan, pdir = json.load(open(a[0])), Path(a[1])
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    syn = json.loads((pdir / 'cores' / 'astk_synth_v38h.json').read_text())['cores']
    n = 0
    for tn in TYPES:
        t = plan['partition_types'][tn]
        assert not t.get('hard_cores'), (tn, 'post_v38h composes after post_v37p: hub_Eo/Wo had no hard cores')
        t['hard_cores'] = cores_for(tn, t, syn)
        n += len(t['hard_cores'])
    if rtl:
        patch = gen_pins(plan, rtl, pdir)
        for tn, cs in patch.items():
            hs = {h['inst']: h for h in plan['partition_types'][tn]['hard_cores']}
            for ci, pt in cs.items():
                if pt.get('orient', 'R0') != 'R0':
                    hs[ci]['orient'] = pt['orient']
        (pdir / 'cores' / 'core_patch_v38h.json').write_text(json.dumps(patch, indent=1, sort_keys=True))
    pf = pdir / 'cores' / 'core_patch_v38h.json'
    if not rtl and pf.exists():
        for tn, cs in json.loads(pf.read_text()).items():
            hs = {h['inst']: h for h in plan['partition_types'][tn]['hard_cores']}
            for ci, pt in cs.items():
                hs[ci]['orient'] = pt.get('orient', 'R0')
    plan['note'] = plan.get('note', '') + (f' | v3.8h (KV-P7-HUB 10-23): {n} astk hard cores on hub_Eo/Wo (post_v38h.py, '
                                           'as-built synth outline, top-down pins)')
    sys.stderr.write(f'post_v38h: {n} astk cores\n')
    json.dump(plan, sys.stdout, indent=1)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
