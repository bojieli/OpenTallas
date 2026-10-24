#!/usr/bin/env python3
"""KV plan v3.7-cores (KV-P6-CORES 10-23, COORD 10-23 19:36 RULED (3)): v3.6 die_plan.json -> v3.7 with
partition_types.<t>.hard_cores[] for every planned L1 core of l1_cores_v31.json (cap 400k std cells per run).

  hg*/hgi*  16 head_eighth cores (head<h>_e<e> = lanes g_t_{2e,2e+1} lane8+stin+stk, + g_front_{e/2} for even e,
            + u_kt for e0; max 383k cells, e0) in a 4 x 4 grid: head A = left 2 columns, head B = right 2 columns,
            e = 2*row + column-in-head (row 0 at the bottom); + the qkd_ectlk core (190k) in the top band under the
            N o_ectl windows (types that hold ectl).
  pv*       16 pv_pair cores (pvg<g>_p<k> = u_g<g>_b{2k,2k+1}, 2 x pv_slice_t 172.8^2, 388k) + every group join
            ot_qwen_tp8_pv_join_t (REUSE-CLOSED, 172.8^2 LEF) as its own core: one column per group g0..g3,
            pairs bottom-up, join on top; the top band (> 1071 um) stays free for the relays / vports / N windows.
  pc*       4 kvs_pc cores (kvpc0..3, 390.9 x 358.5 as built, 140k; kvpc0 = kvs_pc_h head form where present) 2 x 2
            in the upper half; the lower half keeps the hslices + E/W windows.
  hub_C     qkd_ahub core (397k, rework; outline = closed qkd_ahub_static_dw 734.4 x 540) top-left and the
            REUSE-CLOSED qkd_kvs_ctl core (475.2^2 LEF) bottom-right.
  hub_Wi    the 22 measured qkd_host_rt cluster children (gen_cluster.py, max 97k) shelf-packed (control density
            1 cell/um2 -> outline area = cells / 0.75 fill).
Planned cores (no hardened view yet) carry outline + origin only; pins come from the top-down pin tool (lef pending).
REUSE-CLOSED cores carry lef/lib (physical/ref_tile record views) + pins_file (LEF pin centres, cores/) and
track_offset_um [0.108, 0.012] (platform tracks: M5 x phase 0.012 mod 0.048, M3 0.009 mod 0.036, M4 y 0.012).
Every outline / origin is on the 8.64-um lattice; cores keep >= 17.28 um from the type faces.
usage: post_v37c.py die_plan_v36.json > die_plan.json"""
import json, math, re, sys

G = 8.64
OFF = [0.108, 0.012]
VIEWS = {
    'ot_qwen_tp8_pv_join_t': dict(
        lef='physical/ref_tile/qkd_pv_join/views/ot_qwen_tp8_pv_join_t/ot_qwen_tp8_pv_join_t.lef',
        lib='physical/ref_tile/qkd_pv_join/views/ot_qwen_tp8_pv_join_t/ot_qwen_tp8_pv_join_t_tt.lib',
        pins_file='cores/pv_join_pins.json', outline=[172.8, 172.8],
        src='REUSE-CLOSED qkd_pv_join-r4-COMMIT-708845e84 (record 32614b386); later closed runs rstpin_r5 / sfe_r6 '
            'have the same 172.8 outline (CORE-KS lefcmp decides the master)'),
    'qkd_kvs_ctl': dict(
        lef='physical/ref_tile/qkd_kvs_ctl/views/qkd_kvs_ctl/qkd_kvs_ctl.lef',
        lib='physical/ref_tile/qkd_kvs_ctl/views/qkd_kvs_ctl/qkd_kvs_ctl_tt.lib',
        pins_file='cores/kvs_ctl_pins.json', outline=[475.2, 475.2],
        src='REUSE-CLOSED qkd_kvs_ctl_mu2-mu2-9105d74ed (record d20111be0, TT +24.38 / FF +8.88 ps)'),
}
HOST_CORES = {   # l1_cores_v31.py (measured hier std cells; x8 adp)
    'qkd_hr_phy_adp': (6924, 8), 'qkd_hr_phy_pad': (13017, 1), 'qkd_hr_core_prompt': (40025, 1),
    'qkd_hr_core_rx': (49650, 1), 'qkd_hr_core_tx': (54742, 1), 'qkd_hr_core_guard': (47616, 1),
    'qkd_hr_core_queue': (43301, 1), 'qkd_hr_core_order': (79710, 1), 'qkd_hr_core_peer': (71728, 1),
    'qkd_hr_host_qm': (4249, 1), 'qkd_hr_ingest_eng': (97410, 1), 'qkd_hr_cdc_pc': (76242, 1),
    'qkd_hr_cdc_ch': (76392, 1), 'qkd_hr_cdc_hi': (37795, 1), 'qkd_hr_cdc_ci': (35764, 1)}


def L(v):
    return round(round(v / G) * G, 6)


def Lup(v):
    return round(math.ceil(v / G - 1e-9) * G, 6)


def core(inst, module, x, y, w, h, note, reuse=None):
    c = dict(inst=inst, module=module, origin_um=[L(x), L(y)], outline_um=[round(w, 6), round(h, 6)], orient='R0')
    if reuse:
        v = VIEWS[reuse]
        c.update(track_offset_um=list(OFF), pins_file=v['pins_file'], lef=v['lef'], lib=v['lib'])
        note = f"{note}; {v['src']}; placed at origin + {OFF} (platform-track build, COORD 10-23 08:36)"
    else:
        note = f'{note}; PLANNED core: lef/lib/pins pending (top-down pin tool, then CORE-KS harden)'
    c['note'] = note
    return c


def hg(tn, t):
    W, H = t['outline_um']
    mods = {c['inst']: c['module'] for c in t['contents']}
    heads = sorted({m.group(1) for i in mods for m in [re.match(r'(head\d)__', i)] if m})
    assert len(heads) == 2, (tn, heads)
    cw = ch = 33 * G                 # 285.12: e0 leaves 58.1k um2 (2 lane8 + 2 stin/stk + front + ktree) = 71 % fill
    gx, gy, m = 4 * G, 4 * G, 2 * G
    out = []
    for hi, hd in enumerate(heads):
        for e in range(8):
            r, ci = e // 2, e % 2
            col = 2 * hi + ci
            mem = [f'{hd}__g_t_{2 * e}', f'{hd}__g_t_{2 * e + 1}'] + ([f'{hd}__g_front_{e // 2}'] if e % 2 == 0 else []) \
                + ([f'{hd}__u_kt'] if e == 0 else [])
            out.append(core(f'{hd}_e{e}', f'kv3_head_eighth_e{e}', m + col * (cw + gx), m + r * (ch + gy), cw, ch,
                            f"head_eighth: {' + '.join(mem)}"))
    if 'ectl' in mods:
        ew, eh = 102 * G, 25 * G     # 881.28 x 216 = 190k um2 (qkd_ectlk 189.7k cells, control density 1.0)
        out.append(core('ectl', 'qkd_ectlk', m, H - m - eh, ew, eh, 'qkd_ectlk leaf core under the N o_ectl windows'))
    return out


def pv(tn, t):
    W, H = t['outline_um']
    mods = {c['inst']: c['module'] for c in t['contents']}
    pw, ph, jw = 44 * G, 22 * G, 20 * G   # pair 380.16 x 190.08 (2 x 172.8^2 slices), join 172.8
    m, gx, gy = 4 * G, 12 * G, 3 * G
    out = []
    for g in range(4):
        x = m + g * (pw + gx)
        for k in range(4):
            out.append(core(f'pvg{g}_p{k}', 'kv3_pv_pair', x, m + k * (ph + gy), pw, ph,
                            f'pv_pair: pv__u_g{g}_b{2 * k} + pv__u_g{g}_b{2 * k + 1} (ot_qwen_tp8_pv_slice_t x2)'))
        j = f'pv__u_g{g}_j'
        if mods.get(j) == 'ot_qwen_tp8_pv_join_t':
            out.append(core(j, 'ot_qwen_tp8_pv_join_t', x + (pw - jw) / 2, m + 4 * (ph + gy), jw, jw,
                            f'pv group {g} join', reuse='ot_qwen_tp8_pv_join_t'))
    return out


def pc(tn, t):
    W, H = t['outline_um']
    mods = {c['inst']: c['module'] for c in t['contents']}
    cw, ch = 46 * G, 42 * G          # 397.44 x 362.88 (as built 390.936 x 358.536)
    mx, gx = 10 * G, 8 * G
    out = []
    for i in range(4):
        k = f'kvpc{i}'
        if k not in mods:
            continue
        r, c = i // 2, i % 2
        out.append(core(k, mods[k], mx + c * (cw + gx), H - 2 * G - (2 - r) * ch - (1 - r) * 3 * G, cw, ch,
                        f'{mods[k]} leaf core'))
    return out


def hub_c(tn, t):
    W, H = t['outline_um']
    out = [core('ahub', 'qkd_ahub', 10 * G, H - 10 * G - 62.5 * G, 85 * G, 62.5 * G,
                'qkd_ahub (rework, AP_OFS/FR_OFS table-driven) 397k cells; outline = closed qkd_ahub_static_dw '
                '734.4 x 540')]
    v = VIEWS['qkd_kvs_ctl']['outline']
    out.append(core('kvs_ctl', 'qkd_kvs_ctl', W - 10 * G - v[0], 10 * G, v[0], v[1], 'qkd_kvs_ctl leaf core',
                    reuse='qkd_kvs_ctl'))
    return out


def hub_wi(tn, t):
    W, H = t['outline_um']
    items = []
    for ch_, (cells, n) in HOST_CORES.items():
        a = cells / 0.75
        s = Lup(math.sqrt(a))
        w, h = s, Lup(a / s)
        for i in range(n):
            items.append((h, w, f'host__{ch_}' + (f'_{i}' if n > 1 else ''), ch_, cells))
    items.sort(key=lambda r: (-r[0], r[2]))
    x0, y = 10 * G, 10 * G
    x, rowh, out = x0, 0, []
    for h, w, inst, mod, cells in items:
        if x + w > W - 10 * G:
            x, y, rowh = x0, y + rowh + 2 * G, 0
        out.append(core(inst, mod, x, y, w, h, f'qkd_host_rt cluster child {mod} ({cells} cells hier, measured)'))
        x, rowh = x + w + 2 * G, max(rowh, h)
    assert y + rowh <= H - 10 * G, (tn, y + rowh)
    return out


def main():
    P = json.load(open(sys.argv[1]))
    n = 0
    for tn, t in P['partition_types'].items():
        f = (hg if re.match(r'kv3_hgi?(_|$)', tn) else pv if re.match(r'kv3_pv(_|$)', tn) else
             pc if re.match(r'kv3_pc(_|$)', tn) else hub_c if tn == 'kv3_hub_C' else
             hub_wi if tn == 'kv3_hub_Wi' else None)
        if f:
            t['hard_cores'] = f(tn, t)
            n += len(t['hard_cores'])
    P['note'] += (f' | v3.7-cores (KV-P6-CORES 10-23): hard_cores[] for every L1 core (post_v37c.py; {n} entries over '
                  'the types; reuse-closed pv_join / kvs_ctl with LEF + pins + track_offset, the rest planned)')
    json.dump(P, sys.stdout, indent=1)


if __name__ == '__main__':
    main()
