#!/usr/bin/env python3
"""TOK-FUNC-QW stage xdie: RUNROOT/xdie/out/<cfg>.summary + <cfg>/run.log -> RUNROOT/xdie/result.json.
usage: stage_xdie.collect.py RUNROOT RUN_RC"""
import json, os, re, sys

root, rc = sys.argv[1], int(sys.argv[2])
S = f'{root}/xdie'; O = f'{S}/out'
try:
    commit = open(f'{root}/src/ASM_COMMIT').read().strip()
except OSError:
    commit = None
POS = ('cur_pair', 'cur_bound_image', 'cur_bound_image_t8192', 'cur_bound_image_sfm3', 'cur_pair_t8192', 'cur_pair_phy9',
       'cur_pair_l0', 'cur_shift_only_sd0', 'cur_kseam_d22bu_route_r')
runs, mutants, logs = {}, {}, ['xdie/run.log', 'xdie/out/SUMMARY.txt', 'xdie/out/law_check.log']
for fn in sorted(os.listdir(O)) if os.path.isdir(O) else []:
    if not fn.endswith('.summary'):
        continue
    name = fn[:-8]
    txt = open(f'{O}/{fn}').read()
    m = re.search(rf'^({re.escape(name)}) expect=(\S+) got=(\S+) -> (\S+)', txt, re.M)
    if not m:
        runs[name] = dict(status='NO_RESULT'); continue
    _, exp, got, ok = m.groups()
    r = dict(expect=exp, got=got, ok=ok == 'OK')
    e = re.search(r'XQ_E (.*)', txt)
    if e:
        r['E'] = {k: int(v) for k, v in (kv.split('=') for kv in e.group(1).split())}
    c = re.search(r'XQ_CFG (.*)', txt)
    if c:
        r['cfg'] = c.group(1).strip()
        for k in ('X', 'period', 'layers', 'PHY'):
            mm = re.search(rf'\b{k}=(-?\d+)', r['cfg'])
            if mm:
                r[k] = int(mm.group(1))
    ib = re.search(r'IMAGE_BIND .*', txt)
    if ib:
        r['image_bind'] = ib.group(0)
    p = re.search(r'XQ_PASS (.*)', txt)
    if p:
        r['pass_line'] = p.group(1).strip()
    errs = re.findall(r'XQ_(?:FAIL|CAUSE|ERR)[^\n]*', txt)
    if errs:
        r['fail_lines'] = errs[:3]
    runs[name] = r
    logs += [f'xdie/out/{name}/run.log', f'xdie/out/{name}/cal.log']
    if exp in ('FAIL', 'BUILD_FAIL'):
        mutants[name] = 'FAIL as required' if r['ok'] else f'UNEXPECTED got={got}'

def E(cfg):
    return runs.get(cfg, {}).get('E', {})

cycles = {}
for cfg in ('cur_bound_image', 'cur_pair'):
    e = E(cfg)
    if e:
        cycles = dict(source_config=cfg,
                      C2K_cmd=e.get('C2K_cmd_issue_to_land'), C2K_q31=e.get('C2K_q31_issue_to_land'),
                      C2K_q_first_issue_to_last_land=e.get('C2K_q_first_issue_to_last_land'),
                      K2C_r31=e.get('K2C_r31_issue_to_land'), K2C_status=e.get('K2C_status_issue_to_land'),
                      KVN_k3=e.get('KVN_k3_issue_to_land'),
                      roundtrip_cmd_to_r31=e.get('roundtrip_cmd_issue_to_r31_land'),
                      kv_service_cmd_land_to_r31_issue=e.get('kv_service_cmd_land_to_r31_issue'),
                      compute_done_after_r31=e.get('compute_done_after_r31_land'),
                      X_per_layer=runs[cfg].get('X'), period_per_layer=runs[cfg].get('period'),
                      layers=runs[cfg].get('layers'))
        if None not in (cycles['C2K_q31'], cycles['K2C_r31']):
            cycles['exposed_d2d_per_layer'] = cycles['C2K_q31'] + cycles['K2C_r31']
        if cycles['period_per_layer']:
            cycles['decode_layers_L1_35_total'] = cycles['period_per_layer'] * 35
        break
for cfg, key in (('cur_pair_phy9', 'phy9'), ('cur_pair_l0', 'L0'), ('cur_kseam_d22bu_route_r', 'd22bu_route_r')):
    e = E(cfg)
    if e:
        cycles[f'{key}_roundtrip_cmd_to_r31'] = e.get('roundtrip_cmd_issue_to_r31_land')
        cycles[f'{key}_exposed_d2d'] = (e.get('C2K_q31_issue_to_land') or 0) + (e.get('K2C_r31_issue_to_land') or 0)
        cycles[f'{key}_X'] = runs[cfg].get('X'); cycles[f'{key}_period'] = runs[cfg].get('period')
law = None
try:
    law = json.load(open(f'{O}/law_check/image_bind.json'))
except (OSError, ValueError):
    pass
pos_ok = all(runs.get(c, {}).get('got') == 'PASS' and runs[c].get('ok') for c in POS)
mut_ok = bool(mutants) and all(v == 'FAIL as required' for v in mutants.values())
verdict = 'PASS' if (pos_ok and mut_ok and rc == 0) else 'FAIL'
res = {
    'stage': 'xdie',
    'grade': 'RTL-functional (source assembly)',
    'src_commit': commit,
    'verdict': verdict,
    'golden': ('tb_xdie_qwen_exchange per-layer golden: 35 decode layers x (CMD + 32 Q beats compute->KV, 4 KVN words, '
               '32 RESULT beats + STATUS KV->compute), every 548-b record word bit-exact vs the bench reference AND every '
               'landing on its compiled cycle, identical measurements every layer, no fault in either D2D master / '
               'native59 / kvs_attn_fl r17 / pvfin; pvfin beat0 age = PV + max(P0,P1,R) + 17 law'),
    'pair_image': {'file': 'rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu_ew595_r16.svh',
                   'law_compile_equals_image_seg0_and_txdp': None if law is None else law.get('all_equal_to_law'),
                   'note': 'cur_bound_image* runs bind the image seg-0 calendars + TXDP_C/K into both masters (xdie_image_cal.py)'},
    'seam_plan': 'XQ_CUR C 2,2,2,3,2,2 / K 11,11,9,9,9,9,9 = die stages the ew595_r16 image was compiled for (g5r2b/g5r3 '
                 'compute netlisted seam, K22 pair-image KV seam); GEN9 d22bu as-built K 13,13,9,9,9,11,11 in cur_kseam_d22bu_*',
    'cycles': cycles,
    'mutants': mutants,
    'runs': runs,
    'users': '1 (bench is single-user: native59 NU 1 as the die binds; the 4-user OVL pair is a separate stage)',
    'stand_ins': ['UCIe PHY = physical/qwen_kv_die_phy ot_qkvd_ucie_x64_phy_model (LAT 5; 9 in *_phy9) -- off-chip leg, allowed',
                  'die seam relays = bench register chains (xq_dly) at the XQ_CUR lane ages, not the GEN relay cells',
                  'outer-pin stimuli: native59 dd / sys_face slot pulses, KV i_ctl (programme go/issue/run) and boot cfg, '
                  'PV pair beat streams + rz into qkd_pv_fin_s are bench-driven at their compiled ages (the neighbouring '
                  'compute slices / sys_face / KV PV tiles are not in this vehicle)',
                  'calendar sequencers (qfd/qkd_d2d_cal_seq replaying the image) not instantiated: the bench writes the '
                  'calendar entries through cfg_* (cur_bound_image*: exactly the image seg-0 words + TXDP)'],
    'die_netlist_hook': 'not wired: at closure replace u_c/u_k/u_kattn RTL with the GEN carves (stage_xdie.sh header)',
    'overlay': [l.split() for l in open(f'{S}/overlay.txt').read().splitlines()] if os.path.exists(f'{S}/overlay.txt') else [],
    'run_rc': rc,
    'logs': logs,
}
json.dump(res, open(f'{S}/result.json', 'w'), indent=1)
print(json.dumps({k: res[k] for k in ('verdict', 'cycles', 'mutants')}, indent=1))
print('runs:', {k: (v.get('expect'), v.get('got')) for k, v in runs.items()})
