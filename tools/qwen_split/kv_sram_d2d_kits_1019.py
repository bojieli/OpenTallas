#!/usr/bin/env python3
"""KV-SRAM-D2D 2026-10-19: write the four right-sized-storage KV D2D kit specs from the safe fan-out kits.

  qkd_d2d_static_r7w_sfm   ordinary master qkd_d2d_static_sfm,      SRAMV 1 (d2d p192 64x137), two-column geometry
  qkd_d2d_static_ovl_sfm   MU overlap master qkd_d2d_static_ovl_sfm, SRAMV 1, two-column geometry
  qkd_d2d_static_r7w_sfm2  PARALLEL FALLBACK: SRAMV 2 (d2d p288 64x137, taller pin face), the s1 2x2 lattice slots
  qkd_d2d_static_ovl_sfm2  PARALLEL FALLBACK of the OVL kit, same

Outline (475.2 x 280.8), pin faces and every existing pin location are those of the reviewed s1 / sf kits except the S
face, which is re-spread in its existing order with the 17 rx_zero17 pins inserted after the last rx_payload bit (full
face, 0.192 / 0.240 um = 4 / 5 M5 tracks).  Then run tools/ref_tile/ref_tile.py gen on each spec.
    python3 tools/qwen_split/kv_sram_d2d_kits_1019.py
"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RT = ROOT / 'physical/ref_tile'
MV = 'physical/asap7_memory_macros_v2'
OLD = 'ot_sram_1r1w_64x512_m1_r2c2'
MAC = {1: 'd2d_sram_1r1w_64x137_m1_r2c2_p192', 2: 'd2d_sram_1r1w_64x137_m1_r2c2_p288'}
# macro origins (43.2 lattice).  p192 57.912 x 45.672: two columns (x 86.4 / 345.6), rows y 86.4 / 172.8: every pin face
# (W / E) opens onto >= 86 um of standard-cell area.  p288 57.912 x 67.512: the s1 / sf lattice slots.
GEO = {1: [(86.4, 86.4), (345.6, 86.4), (86.4, 172.8), (345.6, 172.8)],
       2: [(43.2, 43.2), (259.2, 43.2), (43.2, 172.8), (259.2, 172.8)]}
KITS = [('qkd_d2d_static_r7w_sfm', 'qkd_d2d_static_r7w_sf', 'qkd_d2d_static_sfm', 1, 0),
        ('qkd_d2d_static_ovl_sfm', 'qkd_d2d_static_ovl_sf', 'qkd_d2d_static_ovl_sfm', 1, 1),
        ('qkd_d2d_static_r7w_sfm2', 'qkd_d2d_static_r7w_sf', 'qkd_d2d_static_sfm', 2, 0),
        ('qkd_d2d_static_ovl_sfm2', 'qkd_d2d_static_ovl_sf', 'qkd_d2d_static_ovl_sfm', 2, 1)]
TXDP_GREP = "grep -q \"QKD_D2D_TXDP = 32'h03030416\" {RUN}/bench/%s/cal/txdp.svh"
H = 280.8
FILL_REASON = ("pin-bound perimeter: 5,072 functional pins on full faces (gate pin demand S 2,308-2,312 pins over 470.8/475.2 um, "
   "N 1,170 over 470.8, W 1,251 over 276.3/280.8, E 333-339 over 276.3: 98-99% of every edge; S 4.9 pins/um, W 4.5/um, "
   "at the 4-5 M5-track pitch of the reviewed sf plan); the outline cannot shrink without exceeding the pin pitch. "
   "Right-sizing the slot store (64x512 -> 64x137, KV-SRAM-D2D) removed ~37k um2 of macro, so fill fell 45% -> 12-16% at "
   "the same pin-limited outline (KV-D2D-COLLECT 10-19).")
PIN_RE = re.compile(r'^place_pin -pin_name \{(\S+)\} -layer (\S+) -location \{([\d.]+) ([\d.]+)\} -pin_size \{(\S+) (\S+)\}$')


def respread_s(lines):
    """S face (y ~ 0, M5): keep order, insert rx_zero17[0..16] after the last rx_payload bit, spread on 0.048 tracks."""
    s, other = [], []
    for ln in lines:
        m = PIN_RE.match(ln)
        if m and float(m.group(4)) < 1.0:
            s.append(m)
        else:
            other.append(ln)
    s.sort(key=lambda m: float(m.group(3)))
    names = [m.group(1) for m in s]
    last = max(i for i, n in enumerate(names) if n.startswith('rx_payload['))
    y, layer, pw, ph = s[0].group(4), s[0].group(2), s[0].group(5), s[0].group(6)
    names = names[:last + 1] + [f'rx_zero17[{i}]' for i in range(17)] + names[last + 1:]
    x0, x1 = float(s[0].group(3)), float(s[-1].group(3))
    n = len(names)
    tracks = round((x1 - x0) / 0.048)
    out = []
    for k, nm in enumerate(names):
        x = x0 + round(k * tracks / (n - 1)) * 0.048
        out.append(f'place_pin -pin_name {{{nm}}} -layer {layer} -location {{{x:.6f} {y}}} -pin_size {{{pw} {ph}}}')
    xs = [x0 + round(k * tracks / (n - 1)) * 0.048 for k in range(n)]
    gaps = sorted(set(round(b - a, 3) for a, b in zip(xs, xs[1:])))
    return other, out, {'pins': n, 'span': x1 - x0, 'pins_per_um': n / (x1 - x0), 'gaps_um': gaps}


def benches(kit, sramv, ovl):
    o = 'OVLM=1 ' if ovl else ''
    v = f'SRAMV={sramv} '
    w = f'results/closure_witness/{kit}/'
    tag = f'ovlm={ovl} randinit=0 seed=0 mutfo=0 sramv={sramv}'
    b = [
        {"name": "leaf_eq", "cmd": f"{v}bash rtl/test/qwen_split/run_d2d_sram_leaf_eq.sh {{RUN}}/bench/le", "expect": "pass",
         "pass_regex": f"^LEAF_EQ_PASS sramv={sramv} ", "threads": 2, "peak_ram_gb": 4},
        {"name": "leaf_mutw_col136", "cmd": f"{v}MUTW=1 bash rtl/test/qwen_split/run_d2d_sram_leaf_eq.sh {{RUN}}/bench/lm",
         "expect": "fail", "fail_regex": "^LEAF_EQ_FAIL mismatches$", "fail_witness": w + "leaf_mutw_col136.log",
         "threads": 2, "peak_ram_gb": 4},
        {"name": "sfm_miter_feg0", "cmd": f"{o}{v}FEG=0 bash rtl/test/qwen_split/run_kv_d2d_sfm_miter.sh {{RUN}}/bench/s0",
         "expect": "pass", "pass_regex": f"^SFO_MITER_PASS {tag} feg=0", "threads": 4, "peak_ram_gb": 12},
        {"name": "sfm_miter_feg1", "cmd": f"{o}{v}FEG=1 bash rtl/test/qwen_split/run_kv_d2d_sfm_miter.sh {{RUN}}/bench/s1",
         "expect": "pass", "pass_regex": f"^SFO_MITER_PASS {tag} feg=1", "threads": 4, "peak_ram_gb": 12},
        {"name": "sfm_miter_randinit", "cmd": f"{o}{v}FEG=1 RANDINIT=1 SEED=13 bash rtl/test/qwen_split/run_kv_d2d_sfm_miter.sh {{RUN}}/bench/sr",
         "expect": "pass", "pass_regex": f"^SFO_MITER_PASS ovlm={ovl} randinit=1 seed=13 mutfo=0 sramv={sramv} feg=1",
         "threads": 4, "peak_ram_gb": 12},
        {"name": "sfm_mutfo2_bypass_select", "cmd": f"{o}{v}FEG=0 MUTFO=2 bash rtl/test/qwen_split/run_kv_d2d_sfm_miter.sh {{RUN}}/bench/m2",
         "expect": "fail", "fail_regex": "^SFO_MITER_FAIL mismatches$", "fail_witness": w + "sfm_mutfo2_bypass_select.log",
         "threads": 4, "peak_ram_gb": 12},
        {"name": "sfm_mutfo6_crc_late", "cmd": f"{o}{v}FEG=0 MUTFO=6 bash rtl/test/qwen_split/run_kv_d2d_sfm_miter.sh {{RUN}}/bench/m6",
         "expect": "fail", "fail_regex": "^SFO_MITER_FAIL mismatches$", "fail_witness": w + "sfm_mutfo6_crc_late.log",
         "threads": 4, "peak_ram_gb": 12},
        {"name": "sfm_mutfo7_z17_bit19", "cmd": f"{o}{v}FEG=0 MUTFO=7 bash rtl/test/qwen_split/run_kv_d2d_sfm_miter.sh {{RUN}}/bench/m7",
         "expect": "fail", "fail_regex": "^SFO_MITER_FAIL Z17 cycle", "fail_witness": w + "sfm_mutfo7_z17_bit19.log",
         "threads": 4, "peak_ram_gb": 12},
        {"name": "sfm_guard", "cmd": f"{o}bash rtl/test/qwen_split/run_kv_d2d_sfm_guard.sh {{RUN}}/bench/g0", "expect": "pass",
         "pass_regex": "^GUARD_PASS mutfo=0", "threads": 4, "peak_ram_gb": 12},
        {"name": "sfm_guard_mutfo5_off", "cmd": f"{o}MUTFO=5 bash rtl/test/qwen_split/run_kv_d2d_sfm_guard.sh {{RUN}}/bench/g5",
         "expect": "fail", "fail_regex": "^GUARD_FAIL A ", "fail_witness": w + "sfm_guard_mutfo5_off.log",
         "threads": 4, "peak_ram_gb": 12},
        {"name": "d2d_dies_ksfm", "cmd": f"KSF=2 {v}KRC=1 {o}KDLY=19 bash rtl/test/qwen_split/run_d2d_dies.sh {{RUN}}/bench/d0 0 && "
         + TXDP_GREP % 'd0', "expect": "pass", "pass_regex": "^D2D_DIES_PASS", "threads": 1, "peak_ram_gb": 8},
        {"name": "d2d_dies_ksfm_mut_slot", "cmd": f"KSF=2 {v}KRC=1 {o}KDLY=19 bash rtl/test/qwen_split/run_d2d_dies.sh {{RUN}}/bench/dm 1",
         "expect": "fail", "fail_regex": "^D2D_DIES_FAIL$", "fail_witness": w + "d2d_dies_ksfm_mut_slot.log",
         "threads": 1, "peak_ram_gb": 8},
    ]
    if not ovl:
        b.append({"name": "d2d_ksfm_lock", "cmd": f"KSF=2 {v}KRC=1 LOCK=1 KDLY=19 bash rtl/test/qwen_split/run_d2d_dies.sh {{RUN}}/bench/l0 0 && "
                  + TXDP_GREP % 'l0', "expect": "pass", "pass_regex": "^D2D_LOCK edges \\d+ mismatches 0 ", "threads": 1,
                  "peak_ram_gb": 8})
    else:
        b.append({"name": "d2d_ovl_ksfm_omut1_user", "cmd": f"KSF=2 {v}KRC=1 OVLM=1 OMUT=1 KDLY=19 bash rtl/test/qwen_split/run_d2d_dies.sh {{RUN}}/bench/o1 0",
                  "expect": "fail", "fail_regex": "^D2D_DIES_FAIL$", "fail_witness": w + "d2d_ovl_ksfm_omut1_user.log",
                  "threads": 1, "peak_ram_gb": 8})
    return b


def main():
    for kit, base, top, sramv, ovl in KITS:
        src, dst = RT / base, RT / kit
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir()
        for f in ('local_reset_capture.tcl',):
            shutil.copy(src / f, dst / f)
        # pins
        lines = (src / 'assigned_pins.tcl').read_text().splitlines()
        head = [ln for ln in lines if ln.startswith('#')]
        other, s_new, s_stat = respread_s([ln for ln in lines if not ln.startswith('#')])
        (dst / 'assigned_pins.tcl').write_text('\n'.join(
            ['# Safe full-face exact pins (s1 / sf plan); KV-SRAM-D2D 10-19: S face re-spread in order with rx_zero17[16:0] '
             'after rx_payload (0.192 / 0.240 um).'] + head[1:] + other + s_new) + '\n')
        plan = json.loads((src / 'pin_geometry_plan.json').read_text())
        plan['S'] = {'pins': s_stat['pins'], 'span': s_stat['span'], 'pins_per_um': s_stat['pins_per_um']}
        (dst / 'pin_geometry_plan.json').write_text(json.dumps(plan, indent=1) + '\n')
        # spec
        d = json.loads((src / 'spec.json').read_text())
        d['name'], d['top'] = kit, top
        srcs = [s for s in d['sources'] if OLD not in s]
        i = srcs.index('rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies_sfo.sv')
        srcs.insert(i + 1, 'rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_sfm.sv')
        srcs.append(f'{MV}/{MAC[sramv]}/{MAC[sramv]}_bb.v')
        d['sources'] = srcs
        d['params'] = {**d['params'], 'SRAMV': sramv, 'FEG': 1}
        d['macros'] = [{'view': f'{MV}/{MAC[sramv]}', 'count': 1, 'at': list(xy)} for xy in GEO[sramv]]
        s = d['pins']['S']
        s.insert(s.index('rx_payload') + 1, 'rx_zero17')
        d['io_tcl'] = f'physical/ref_tile/{kit}/assigned_pins.tcl'
        d['pin_hook_before_flops'] = [f'physical/ref_tile/{kit}/local_reset_capture.tcl']
        fb = sramv == 2
        what = (f"right-sized slot store {MAC[sramv]} x4 (64x137 = the stored width; W/E 229 pins at "
                f"{'0.288 um = 3.49' if fb else '0.192 um = 5.23'}/um, was 64x512 at 10.2/um), registered RX CRC, 5-b recovery "
                "counter, first-epoch guard (FEG 1), Z17 sideband rx_zero17")
        d['structural_change'] = ((f"PARALLEL FALLBACK of {kit[:-1]} (taller p288 pin face, s1 2x2 lattice slots). " if fb else "")
                                  + f"KV-SRAM-D2D successor of {base}: {what}; same outline / pin faces (S re-spread +17 pins).")
        d['reroute_reason'] = {"kind": "rtl_change", "params": {"TXDP": "0x03030416", "SAFE_RC": 1, "SRAMV": sramv, "FEG": 1,
                                                                 "top": top},
                               "source": "KV-SRAM-D2D lane (LEAD2-KV brief 10-19): Codex HOLD 12:48 macro face 10.2 pins/um > 6; "
                                         "sf/sfb gates reg-reg -16.1/-23.4/-95.5/-100.7 ps",
                               "cell": top, "fix": d['structural_change']}
        d.pop('safe_checklist', None)
        # KV-D2D-COLLECT 10-19: the 17:01 CTS gates FAILed only 'fill' (12-16%): the outline is set by the full pin faces
        d['fill_reason'] = {'pin_bound': FILL_REASON}
        j = d['job']
        j['owner'], j['branch'], j['tag'] = 'Claude:KV-SRAM-D2D 10-19', 'claude/kv-sram-d2d-1019', kit.split('_')[-1]
        j['purpose'] = (f"KV-die static D2D link end {top} (TXDP_K 0x03030416, NTX3, SAFE_RC1, SRAMV {sramv}, FEG 1): {what}. "
                        "PHY on face N.")
        j['extra_paths'] = [p for p in j['extra_paths'] if OLD not in p] + [f'{MV}/{OLD}', f'{MV}/{MAC[1]}', f'{MV}/{MAC[2]}']
        j['benches'] = benches(kit, sramv, ovl)
        j['views_to'] = f'physical/ref_tile/{kit}/views'
        j['record_to'] = f'results/rtl/ref_tile/{kit}'
        (dst / 'spec.json').write_text(json.dumps(d, indent=1) + '\n')
        print(kit, top, MAC[sramv], s_stat)


if __name__ == '__main__':
    main()
