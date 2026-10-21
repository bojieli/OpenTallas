#!/usr/bin/env python3
# HBM-KIND8: KIND1/KIND2 lane leaf kits. rg = region-form single clock ck (main); r5 = r4 roots (fallback).
import json, pathlib, copy, shutil
QC = pathlib.Path('/home/ubuntu/wt/hbm-qcore8-1020/physical/ref_tile/hbm_su_qcore_r13_1020')  # HBM-QCORE9 r13 canonicalize (Codex FP6)
WT = pathlib.Path('/home/ubuntu/wt/hbm-kind8-1020')
A = 'rtl/hbm_accel/generic/adapters/static_su/arithmetic/'
def mk(kind, form, name, side=None):
    base = json.load(open(WT / f'physical/ref_tile/hbm_su_static_kind{kind}_l4_r4_1016/spec.json'))
    s = copy.deepcopy(base); s['name'] = name
    r4top = f'ot_hbm_su_static_kind{kind}_lat4_leaf1_r4_physical'
    top = f'ot_hbm_su_static_kind{kind}_lat4_leaf1_{form}_physical'
    s['top'] = top
    s['sources'] = [x.replace(r4top, top) for x in base['sources']]
    K8 = A + 'k8/'
    s['sources'] = s['sources'][:-1] + [K8 + f for f in ('ot_hdc_fp32_mul_lat_k8.sv', 'ot_hdc_fastfp_lat_k8.sv', 'ot_hdc_v41x_exp_k8.sv',
                                                    'ot_hbm_su_static_ins_k8.sv', 'ot_hdc_v41x_ins_k8.sv', 'ot_hbm_su_static_lane_k8.sv', 'ot_hbm_su_static_lane_pinreg_k8.sv', 'ot_hdc_v41x_fdiv_k8.sv', 'ot_k9_fam.sv')] + ['rtl/hdc/ot_hdc_fp32_add_n32.sv'] + s['sources'][-1:]
    s['defines'] = list(base['defines']) + ['OT_FP_DATA_NORST']
    if form != 'rg': s['reset_landing'] = {'enable': True, 'stages': 2, 'clock': 'clk'}
    s['route']['io_hold_margin_ns'] = 0.03
    # HBM-KIND9: FP adds = Codex FP6 ot_hdc_fp32_add_n32; its kept copy families need the HBM-QCORE9 copy-alias + splitter
    # canonicalize (kit-scoped SYNTH_CANONICALIZE_TCL, unchanged except the kit path) and the splitter at 32 loads
    s['orfs_vars'] = {'SYNTH_CANONICALIZE_TCL': f'physical/ref_tile/{name}/synth_canonicalize.tcl'}
    s['reset_relay_split'] = {'max_loads': 32}
    s['job']['extra_paths'] = [f'physical/ref_tile/{name}/copy_aliases.py', f'physical/ref_tile/{name}/synth_canonicalize.tcl']
    s['route']['peak_ram_gb'] = 48 if kind == 1 else 96
    if form == 'rg':
        for k in ('clock', 'clock_ports', 'clock_data_paths', 'clock_relationship', 'clock_entry_domains'):
            s.pop(k, None)
        s['clock_port'] = 'ck'; s['route'].pop('signoff_period_ps', None)
        ck = s['pin_ranges']['clk']
        for k in [k for k in s['pin_ranges'] if k.startswith('clk')]: s['pin_ranges'].pop(k)
        s['pins']['W'] = ['ck'] + [p for p in s['pins']['W'] if not p.startswith('clk')]
        s['pin_ranges']['ck'] = ck
        if side:  # shrink square KIND1 to util ~0.5 (r4 gate util 0.437 at 233.28)
            f = side / s['outline']['w']
            s['outline'] = {'w': side, 'h': side}
            for k, v in s['pin_ranges'].items(): s['pin_ranges'][k] = [round(v[0] * f, 3), round(v[1] * f, 3)]
            s['pin_ranges']['ck'] = [round(side / 2 - 0.048, 3), round(side / 2 + 0.048, 3)]
    sc = (f"HBM-KIND9 10-20 {form}: FP adds = Codex FP6 ot_hdc_fp32_add_n32 LAT 3 (bit-exact, HBM-QCORE9 canonicalize); HBM-KIND8 " + ("REGION-FORM single clock ck (pgrg region pattern: every lane clock = the region root; "
          "no cross-root seams inside the lane), " if form == 'rg' else "r4 regional roots kept (fallback), ")
          + "io_hold_margin 0.03; pre-gate native census + safe-design checklist in README. Base: " + base['structural_change'][:300])
    s['structural_change'] = sc
    EX = ' '.join(A + 'k8/' + f for f in ('ot_hbm_su_static_ins_k8.sv', 'ot_hdc_v41x_ins_k8.sv', 'ot_hbm_su_static_lane_pinreg_k8.sv', 'ot_hbm_su_static_lane_k8.sv', 'ot_hdc_fastfp_lat_k8.sv',
                                          'ot_hdc_fp32_mul_lat_k8.sv', 'ot_hdc_v41x_exp_k8.sv', 'ot_hdc_v41x_fdiv_k8.sv', 'ot_k9_fam.sv')) + ' rtl/hdc/ot_hdc_fp32_add_n32.sv'
    for b in s['job']['benches']:
        b['cmd'] = b['cmd'].replace(r4top, top).replace('SU_PINREG=1 ', f"SU_PINREG=1 SU_LANE_NORST=1 SU_LANE_EXTRA='{EX}' ")
    s['job'].update({'owner': 'Claude:HBM-KIND9', 'branch': 'claude/hbm-kind8-1020', 'tag': form,
                     'purpose': sc, 'auto_merge': False})
    d = WT / 'physical/ref_tile' / name; d.mkdir(parents=True, exist_ok=True)
    shutil.copy(QC / 'copy_aliases.py', d / 'copy_aliases.py')
    (d / 'synth_canonicalize.tcl').write_text((QC / 'synth_canonicalize.tcl').read_text().replace(
        'physical/ref_tile/hbm_su_qcore_r13_1020/copy_aliases.py', f'physical/ref_tile/{name}/copy_aliases.py').replace(
        '# hbm_su_qcore_r13_1020 kit-scoped', f'# {name} kit-scoped (copied by HBM-KIND9 from hbm_su_qcore_r13_1020)'))
    (d / 'spec.json').write_text(json.dumps(s, indent=1) + '\n'); print(name, s['outline'], top)
mk(1, 'rg', 'hbm_su_static_kind1_rg_1020', side=216.0)
mk(2, 'rg', 'hbm_su_static_kind2_rg_1020')
mk(1, 'r5', 'hbm_su_static_kind1_r5_1020')
mk(2, 'r5', 'hbm_su_static_kind2_r5_1020')
