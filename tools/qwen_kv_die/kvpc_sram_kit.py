#!/usr/bin/env python3
"""KV-PC 2026-10-19 SAFE redesign: the PC / PC_H kit specs of the OT_KV_PC_SRAM tile, derived from the committed rl1
specs (tools/ref_tile/specs/qkd_kvs_pc{,_h}_rl1.json: same ports, faces, pin ranges, clocks, recipe) with
  * the tile file qkd_kvs_tiles_hroot_ff_k_mu_ds_rl_sr.sv + the SRAM / clone RTL + the native bank blackbox;
  * 23 native ot_sram_1r1w2c_32x64_m1 banks in five abutted N-S stacks (pins W/E only), two columns:
      col A x=43.2: front 5 (u_front, W side: the PHY read path pi -> port -> ECC -> front), return 5, tag queue 2;
      col B x=172.8: embedding CDC down 6, up 5 (E side: es / er faces);
    stacks 23.5 um apart, >= 21 um from every pin face, 97.6 um between the columns;
  * the eight HBM storage roots (pc__front_hbm_data / pc__return_hbm_data) declared as clocks of the hclk family
    (they clock only bank write ports now);
  * reset_relay_split max_loads 32 (ot_rst_copies: the kept hr_qv / hgo_qv families of the scheduler);
  * the SAFE unit benches (tools/qwen_kv_die/kvpc_sram_bench.py) with mutants and committed witnesses.
    python3 tools/qwen_kv_die/kvpc_sram_kit.py [--tag sr1] [--variant a|b]     (writes tools/ref_tile/specs/<kit>.json)
Variant b (fallback, gated in parallel): same RTL and outline, the CDC stacks in a centre column (x=129.6) instead of
x=172.8 (104 um std-cell region along the dense E face: er / her / hes / land_er / land_es).  The outline stays the die
frame: every face is pin-bound (N i_next 780 b + o_next 299 b + o_grp 295 b at ~6 / um over 267 um; E 5 x ~260 b over 288
um), so util (macros + std ~26k of 78k um2) cannot reach 40 % without a die-level pin re-assignment (MU-DIE-KV)."""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / 'tools/ref_tile/specs'
VIEW = 'physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1'
BB = VIEW + '/ot_sram_1r1w2c_32x64_m1_bb.v'
RL_TILE = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ds_rl.sv'
SR_TILE = 'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ds_rl_sr.sv'
NEW_RTL = ['rtl/qwen_sys/static_kv_20261014/qkd_kvpc_sram_1019.sv',
           'rtl/qwen_sys/static_kv_20261014/qkd_kvpc_sram_clones_1019.sv', BB]
MH, PITCH = 17.304, 17.328       # bank height; abutted N-S pitch (height + 0.024: pins stay on the 0.048 M4 track)
P = 'u_pc.u_pce.u_path.'
# (stack, instance glob of bank k, banks, column x, base y)
STACKS = [
    ('front', '*u_front.u_mem.g_b?{k}?.u_m', 5, 43.2, 23.76),
    ('return', '*u_return.u_mem.g_b?{k}?.u_m', 5, 43.2, 133.92),
    ('tq', '*u_sched.u_tq.u_{eo}', 2, 43.2, 241.92),
    ('cdc_down', '*u_ecdc.down.u_mem.g_b?{k}?.u_m', 6, 172.8, 23.76),
    ('cdc_up', '*u_ecdc.up.u_mem.g_b?{k}?.u_m', 5, 172.8, 151.2),
]
WIT = WIT_SR1 = 'results/rtl/qwen_kv_die/kvpc_sram_1019'
WIT_SR3 = 'results/rtl/qwen_kv_die/kvpc_sram_sr3_1019'   # KV-PC2 sr3+ receipts (Verilator 5.050, @96723d23b / tile @66c85f895)
UNITS = [('front', (1, 4, 5)), ('return', (1, 2)), ('cdc', (1, 2)), ('tq', (1,)), ('sched', (1,)), ('ctrl', (1, 2)),
         ('path', (2,))]


def macros(variant='a'):
    out = []
    for name, glob, n, x, y in STACKS:
        if variant == 'b' and x > 100:
            x = 129.6            # fallback: CDC stacks in the centre column (E std-cell region 104 um for the E faces)
        for k in range(n):
            inst = glob.format(k=k, eo='eo'[k % 2])
            out.append(dict(view=VIEW, count=1, inst=inst, at=[x, round(y + k * PITCH, 3)], orient='R0',
                            at_exact=k > 0, stack=name))
    return out


def benches(tile, hfx=False):
    WIT = WIT_SR3 if hfx else WIT_SR1
    sh = ('PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH python3 tools/qwen_kv_die/kvpc_sram_bench.py '
          '--unit {u} --mut {m} --threads 4 --out {{RUN}}/bench/kvpc_{u}_m{m}')
    b = []
    for u, muts in UNITS:
        tag = f'KVPC_{u.upper()}'
        b.append(dict(name=f'kvpc_{u}', cmd=sh.format(u=u, m=0), expect='pass', threads=4, peak_ram_gb=8,
                      needs=['verilator'], pass_regex=rf'^{tag} PASS .* errors=0 .*mut=0',
                      pass_witness=f'{WIT}/{u}_m0.log'))
        for m in muts:
            b.append(dict(name=f'kvpc_{u}_mut{m}', cmd=sh.format(u=u, m=m), expect='fail', threads=4, peak_ram_gb=8,
                          needs=['verilator'], pass_regex=rf'^{tag} PASS ', fail_regex=rf'^{tag} FAIL .* mut={m}',
                          fail_witness=f'{WIT}/{u}_m{m}.log'))
    b.append(dict(name=f'kvpc_tile_{tile}', cmd=sh.format(u='tile', m=0).replace('--unit tile', f'--unit tile --tile {tile}')
                  .replace('kvpc_tile_m0', f'kvpc_tile_{tile}_m0'), expect='pass', threads=4, peak_ram_gb=16,
                  needs=['verilator'], pass_regex=r'^KVPC_TILE PASS .* errors=0 mut=0',
                  pass_witness=f'{WIT}/tile_{tile}_m0.log'))
    if hfx:
        b.append(dict(name=f'kvpc_tile_{tile}_mut4', cmd=sh.format(u='tile', m=4).replace('--unit tile', f'--unit tile --tile {tile}')
                      .replace('kvpc_tile_m4', f'kvpc_tile_{tile}_m4'), expect='fail', threads=4, peak_ram_gb=16,
                      needs=['verilator'], pass_regex=r'^KVPC_TILE PASS ', fail_regex=r'^KVPC_TILE FAIL .* mut=4',
                      fail_witness=f'{WIT}/tile_{tile}_m4.log'))
    return b


def derive(tile, tag, variant):
    src = json.loads((SPECS / f'qkd_kvs_{tile}_rl1.json').read_text())
    s = copy.deepcopy(src)
    kit = f'qkd_kvs_{tile}_{tag}'
    s['name'] = kit
    s['sources'] = [SR_TILE if f == RL_TILE else f for f in s['sources']] + NEW_RTL
    s['macros'] = macros(variant)
    if tag in ('sr1', 'sr2', 'sr2b'):
        s['sdc_extra'] = list(s.get('sdc_extra', [])) + [f'physical/qkd_kvs_kits/qkd_kvs_pc_{tag}_store.sdc']
    else:
        # KV-PC2 (sr3+): the banks write on hck (front) / hck->ck (return ring): no storage-root clocks at all; the
        # eight pc__front_hbm_data / pc__return_hbm_data inputs are unused (kept for the die binding)
        s['pins']['S'] = list(s['pins']['S']) + ['pc__hfx']
        s['fill_reason'] = dict(pin_bound=(
            'The die frame sets the outline, not the area: every face is pin-bound (gate qkd_kvs_pc_h_sr1 15:39: N 1547 '
            'pins over 260.9/267.8 um = 5.9/um, E 1422 over 292.2/300.2, W 675 over 291.0/300.2; 92-97 % of every edge '
            'occupied at the ~6 pins/um face limit).  Moving 9216 storage FF into 23 SRAM banks cut the std-cell area, so '
            'fill fell below 35 %; shrinking needs a die-level pin re-assignment (MU-DIE-KV), not a tile change.'))
    s['reset_relay_split'] = dict(max_loads=32)
    ov = dict(s.get('orfs_vars', {}))
    ov['OT_RST_COPIES_WIDE'] = '1'      # kept copy families that select wide words / flop-array reads (item 3)
    s['orfs_vars'] = ov
    why = ('KV-PC SAFE 10-19 (one failed route = structural redesign; terminal gate 1248d0585 PC WARN / PC_H FAIL): the '
           'five runtime-indexed flop arrays (front 32x297 = 9216 FF on 4 storage roots, tag queue 64x34, return ring 8x288, '
           'embedding CDC FIFOs 8x349 / 8x258) are 23 native 32x64 dual-clock SRAM banks (kv_pc_sram_gen / '
           'qkd_kvpc_sram_1019.sv; 0 added edges); the 2405 / 2051 / 854-load pointer roots are gone; scheduler hr_q / hgo '
           'are kept copy families split <= 32 loads (ot_rst_copies); storage roots are hclk-family clocks of the bank '
           'write ports.')
    if tag not in ('sr1', 'sr2', 'sr2b'):
        why = ('KV-PC2 10-19 (structurally safe successor of sr1 / sr2): ' + why.replace(
            'storage roots are hclk-family clocks of the bank write ports.',
            'front banks write AND read on hck (the landing / pointer clock: no storage-root clocks, no same-phase '
            'claim); return-ring banks write on hck, read on ck behind per-slot toggle 2-flop synchronisers; embedding '
            'FIFOs are Gray-pointer async FIFOs; the three dropped sticky faults (chain / es_merge / embr) leave '
            'registered on pc__hfx[2:0] for the health plane.'))
    s['structural_change'] = why
    s['purpose'] = why
    s['safe_design_checklist'] = f'see physical/ref_tile/{kit}/README.md'
    j = s['job']
    j['owner'] = 'Claude:KV-PC' if tag in ('sr1', 'sr2', 'sr2b') else 'Claude:KV-PC2'
    j['branch'] = 'claude/kv-pc-1019' if tag in ('sr1', 'sr2', 'sr2b') else 'claude/kv-pc2-1019'
    j['tag'] = tag
    j['purpose'] = why
    j['benches'] = benches(tile, hfx=tag not in ('sr1', 'sr2', 'sr2b'))
    j['extra_paths'] = sorted(set(j.get('extra_paths', [])) | {VIEW, WIT, WIT_SR3, 'rtl', 'tools/qwen_kv_die'})
    j['views_to'] = f'physical/ref_tile/{kit}/views'
    j['record_to'] = f'results/rtl/ref_tile/{kit}'
    kb = s.get('kits_b', {})
    kb['rtl'] = SR_TILE
    return kit, s


def store_sdc(tag):
    ports = [f'pc__front_hbm_data[{i}]' for i in range(4)] + [f'pc__return_hbm_data[{i}]' for i in range(4)]
    L = ['# KV-PC SAFE 10-19 (generated by tools/qwen_kv_die/kvpc_sram_kit.py): the eight HBM storage roots clock only the',
         '# write ports of the native SRAM banks (front: pc__front_hbm_data[k], return ring: pc__return_hbm_data[k]).  The die',
         '# delivers each at the hclk period and phase (qkd_kv_hbm_elastic_front_mc: "every root at the same phase"), so they',
         '# are clocks of the hclk family: same period / waveform / uncertainty, propagated with hclk; no exception.',
         'set ot_st_prop 0',
         'catch {set ot_st_prop [get_property [get_clocks core_clk] is_propagated]}']
    for i, p in enumerate(ports):
        n = ('hfd' if 'front' in p else 'hrd') + str(i % 4)
        L.append(f'catch {{unset_input_delay [get_ports {{{p}}}]}}')
        L.append(f'create_clock -name {n} -period 1024.000 [get_ports {{{p}}}]')
        L.append(f'set_clock_uncertainty -setup 60 [get_clocks {n}]')
        L.append(f'set_clock_uncertainty -hold 25 [get_clocks {n}]')
        L.append(f'if {{$ot_st_prop}} {{ set_propagated_clock [get_clocks {n}] }}')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='sr1')
    ap.add_argument('--variant', default='a', choices=('a', 'b'))
    a = ap.parse_args()
    if a.tag in ('sr1', 'sr2', 'sr2b'):
        (ROOT / f'physical/qkd_kvs_kits/qkd_kvs_pc_{a.tag}_store.sdc').write_text(store_sdc(a.tag))
    for tile in ('pc', 'pc_h'):
        kit, s = derive(tile, a.tag, a.variant)
        for m in s['macros']:
            m.pop('stack')
        (SPECS / f'{kit}.json').write_text(json.dumps(s, indent=1) + '\n')
        print(f'kvpc_sram_kit: wrote tools/ref_tile/specs/{kit}.json ({len(s["macros"])} banks)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
