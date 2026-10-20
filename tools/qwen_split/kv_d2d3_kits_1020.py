#!/usr/bin/env python3
"""KV-D2D3 2026-10-20: native-census successor kits of the CLOSED KV D2D sfm2 views.

  qkd_d2d_static_r7w_sfm3  ordinary master qkd_d2d_static_sfm3       (from qkd_d2d_static_r7w_sfm2, CLOSED 1c6c02ed7)
  qkd_d2d_static_ovl_sfm3  MU overlap master qkd_d2d_static_ovl_sfm3 (from qkd_d2d_static_ovl_sfm2, CLOSED a71ab049e)

Why: the mandatory pre-gate native census (tools/ref_tile/native_census.py, main 042aa171b) on the routed sfm2 synthesis
netlists FAILS (72 roots > 32 each, max 152; results/rtl/kv_d2d3_1020/README.md).  The sfm3 masters
(rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_sfm3.sv) fix every class with register boundaries, 0 cycles, same ports.
Geometry, outline, pin plan, clock recipe and reset landing are the CLOSED sfm2 kits' (p288 2x2 lattice slots), only the
top / source list / benches / provenance change.  Then run tools/ref_tile/ref_tile.py gen on each spec.
    python3 tools/qwen_split/kv_d2d3_kits_1020.py
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RT = ROOT / 'physical/ref_tile'
KITS = [('qkd_d2d_static_r7w_sfm3', 'qkd_d2d_static_r7w_sfm2', 'qkd_d2d_static_sfm3', 0, '1c6c02ed7'),
        ('qkd_d2d_static_ovl_sfm3', 'qkd_d2d_static_ovl_sfm2', 'qkd_d2d_static_ovl_sfm3', 1, 'a71ab049e')]
SFM3 = 'rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_sfm3.sv'
WHY = ("native census (tools/ref_tile/native_census.py, main 042aa171b) on the routed {base} synthesis netlist FAILS: "
       "72 roots > 32, max 152 (STATUS header check folded into 156 capture bits; calendar image write decode 64 x 64 / "
       "128 / 256 pins; epoch_begin copies 48-57; cal_seg copy 36)")
FIX = ("KV-D2D3 native-census successor of {base}: registered one-hot calendar image write strobes + data copies (readers "
       "use the image D side, exact), per-group registered STATUS header copies (13 groups), 17 epoch_begin copies, 5 "
       "cal_seg pin copies per calendar; 0 cycles, same ports / outline / pins / macros / clock recipe as the CLOSED {base}.")


def benches(kit, ovl, base_benches):
    o = 'OVLM=1 ' if ovl else ''
    w = f'results/closure_witness/{kit}/'
    out = []
    for b in base_benches:
        b = json.loads(json.dumps(b).replace('qkd_d2d_static_r7w_sfm2', kit).replace('qkd_d2d_static_ovl_sfm2', kit))
        c = b['cmd']
        if 'run_kv_d2d_sfm_miter.sh' in c or 'run_kv_d2d_sfm_guard.sh' in c:
            b['cmd'] = 'SFM3=1 ' + c
        if 'run_d2d_dies.sh' in c:
            b['cmd'] = c.replace('KSF=2 ', 'KSF=3 ')
        out.append(b)
    out += [
        {"name": "sfm3_mutfo8_image_q", "cmd": f"SFM3=1 {o}SRAMV=2 FEG=0 MUTFO=8 bash rtl/test/qwen_split/run_kv_d2d_sfm_miter.sh {{RUN}}/bench/m8",
         "expect": "fail", "fail_regex": "^SFO_MITER_FAIL mismatches$", "fail_witness": w + "sfm3_mutfo8_image_q.log",
         "threads": 4, "peak_ram_gb": 12},
        {"name": "sfm3_mutfo9_hdr_copy_hold", "cmd": f"SFM3=1 {o}SRAMV=2 FEG=1 RANDINIT=1 SEED=3 MUTFO=9 bash rtl/test/qwen_split/run_kv_d2d_sfm_miter.sh {{RUN}}/bench/m9",
         "expect": "fail", "fail_regex": "^SFO_MITER_FAIL FO_COPY_MISMATCH$", "fail_witness": w + "sfm3_mutfo9_hdr_copy_hold.log",
         "threads": 4, "peak_ram_gb": 12},
        {"name": "sfm3_mutfo1_seg1_selfhold", "cmd": f"SFM3=1 {o}SRAMV=2 FEG=1 RANDINIT=1 SEED=3 MUTFO=1 bash rtl/test/qwen_split/run_kv_d2d_sfm_miter.sh {{RUN}}/bench/m1",
         "expect": "fail", "fail_regex": "^SFO_MITER_FAIL FO_COPY_MISMATCH$", "fail_witness": w + "sfm3_mutfo1_seg1_selfhold.log",
         "threads": 4, "peak_ram_gb": 12},
    ]
    return out


def main():
    for kit, base, top, ovl, closed in KITS:
        src, dst = RT / base, RT / kit
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir()
        for f in ('local_reset_capture.tcl', 'assigned_pins.tcl', 'pin_geometry_plan.json'):
            shutil.copy(src / f, dst / f)
        d = json.loads((src / 'spec.json').read_text())
        d['name'], d['top'] = kit, top
        srcs = list(d['sources'])
        i = srcs.index('rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_sfm.sv')
        srcs.insert(i + 1, SFM3)
        d['sources'] = srcs
        d['io_tcl'] = f'physical/ref_tile/{kit}/assigned_pins.tcl'
        d['pin_hook_before_flops'] = [f'physical/ref_tile/{kit}/local_reset_capture.tcl']
        d['structural_change'] = FIX.format(base=f'{base} ({closed})')
        d['reroute_reason'] = {"kind": "rtl_change", "params": {"TXDP": "0x03030416", "SAFE_RC": 1, "SRAMV": 2, "FEG": 1,
                                                                 "top": top},
                               "source": "KV-D2D3 lane (LEAD4-KV brief 10-20): " + WHY.format(base=f'{base}-{closed}'),
                               "cell": top, "fix": d['structural_change']}
        j = d['job']
        j['owner'], j['branch'], j['tag'] = 'Claude:KV-D2D3 10-20', 'claude/kv-d2d3-1020', 'sfm3'
        j['purpose'] = (f"KV-die static D2D link end {top} (TXDP_K 0x03030416, NTX3, SAFE_RC1, SRAMV 2, FEG 1): native-census "
                        f"successor of the CLOSED {base} view (same ports/outline/pins/macros). PHY on face N.")
        j['benches'] = benches(kit, ovl, j['benches'])
        j['views_to'] = f'physical/ref_tile/{kit}/views'
        j['record_to'] = f'results/rtl/ref_tile/{kit}'
        (dst / 'spec.json').write_text(json.dumps(d, indent=1) + '\n')
        print(kit, top, len(j['benches']), 'benches')


if __name__ == '__main__':
    main()
