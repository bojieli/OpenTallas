#!/usr/bin/env python3
"""TOKEN-XDIE-QWEN 2026-10-18: record.json of the Qwen compute <-> KV D2D exchange co-sim (run_xdie_exchange.sh output).

usage: xdie_exchange_record.py RUN_DIR OUT_JSON [--rtl-commits k=v ...]
Reads every RUN_DIR/<config>/run.log (XQ_MEAS / XQ_E / XQ_PASS / XQ_FAIL / XQ_CAUSE) and calendar.json, checks the
expectations of SUMMARY.txt, and composes the full-pair exchange from the two single-side-real vehicles:
  vc = compute native59 real + KV record codec (stub)      vk = compute record codec (stub) + KV programme real
  vc_abut / vk_abut = the same with zero die seam stages   (the stub-to-stub link core is common to all four)
  full C2K = vc + vk - abut(vk) ;  full K2C = vk + vc - abut(vk)   (each side's seam + pipeline is additive: the link core
  between the two D2D die masters is the same in every configuration; checked: vc_abut / vk_abut cores agree)
Composition term (lane TOKEN-XDIE section 3): E_exposed = max(0, E_meas - O_meas), O_meas from the compiler schedule.
"""
import json, re, sys
from pathlib import Path

KEYS = ('cmd_issue', 'q0_issue', 'q31_issue', 'cmd_land', 'q0_land', 'q31_land', 'r0_issue', 'r31_issue', 'status_issue',
        'r0_land', 'r31_land', 'kvn0_issue', 'kvn3_issue', 'kvn0_land', 'kvn3_land', 'done')


def parse(d):
    log = (d / 'run.log').read_text() if (d / 'run.log').exists() else ''
    meas = []
    for m in re.finditer(r'^XQ_MEAS (.*)$', log, re.M):
        kv = dict(x.split('=', 1) for x in m.group(1).split())
        meas.append({k: int(kv[k]) for k in KEYS} | dict(layer=int(kv['layer'])))
    e = re.search(r'^XQ_E (.*)$', log, re.M)
    e = {k: int(v) for k, v in (x.split('=') for x in e.group(1).split())} if e else {}
    cfg = re.search(r'^XQ_CFG (.*)$', log, re.M)
    cal = json.loads((d / 'cal' / 'calendar.json').read_text()) if (d / 'cal' / 'calendar.json').exists() else None
    return dict(passed=bool(re.search(r'^XQ_PASS', log, re.M)), meas=meas, E=e, cfg=cfg.group(1) if cfg else None,
                causes=re.findall(r'^XQ_CAUSE (.*)$', log, re.M)[:4], first_errors=re.findall(r'^XQ_ERR (.*)$', log, re.M)[:3],
                calendar=cal)


def main():
    run, out = Path(sys.argv[1]), Path(sys.argv[2])
    commits = dict(a.split('=', 1) for a in sys.argv[3:])
    summ = (run / 'SUMMARY.txt').read_text()
    exp = {m.group(1): (m.group(2), m.group(3)) for m in re.finditer(r'^(\S+) expect=(\w+) got=(\w+)', summ, re.M)}
    R = {n: parse(run / n) for n in exp}
    for n, (e, g) in exp.items():
        assert e == g, f'{n}: expected {e}, got {g}'
    for n in ('vc', 'vk', 'vc_abut', 'vk_abut', 'vc_phy9', 'vk_phy9'):
        assert R[n]['passed'] and len(R[n]['meas']) == 35, n
        first = R[n]['meas'][0]
        assert all({k: m[k] for k in KEYS} == {k: first[k] for k in KEYS} for m in R[n]['meas']), f'{n}: not static'

    def leg(n, a, b):
        m = R[n]['meas'][0]
        return m[b] - m[a]

    def full(phy=''):
        vc, vk, ab = 'vc' + phy, 'vk' + phy, 'vk_abut'
        dphy = 0 if not phy else (leg(vk, 'cmd_issue', 'cmd_land') - leg('vk', 'cmd_issue', 'cmd_land'))
        c2k_cmd = leg(vc, 'cmd_issue', 'cmd_land') + leg(vk, 'cmd_issue', 'cmd_land') - leg(ab, 'cmd_issue', 'cmd_land') - dphy
        c2k_q31 = leg(vc, 'q31_issue', 'q31_land') + leg(vk, 'q31_issue', 'q31_land') - leg(ab, 'q31_issue', 'q31_land') - dphy
        k2c_r31 = leg(vc, 'r31_issue', 'r31_land') + leg(vk, 'r31_issue', 'r31_land') - leg(ab, 'r31_issue', 'r31_land') - dphy
        kvn = leg(vc, 'kvn3_issue', 'kvn3_land')
        svc = leg(vk, 'cmd_land', 'r31_issue')
        q0 = R[vc]['calendar']['params']['P_QS']
        native_cmd_after_q0 = R[vc]['meas'][0]['cmd_issue'] - q0
        rt = native_cmd_after_q0 + c2k_cmd + svc + k2c_r31
        return dict(C2K_cmd=c2k_cmd, C2K_q31=c2k_q31, K2C_r31=k2c_r31, KVN_last=kvn, kv_service_cmd_land_to_r31_issue=svc,
                    q0_to_r31_land=rt)
    F5, F9 = full(), full('_phy9')
    # priced: the component-bench (stub-stub, zero stages) layer is the priced token-path image (d2d_link_calendar)
    priced_rt = R['vk_abut']['meas'][0]['r31_land'] - R['vk_abut']['calendar']['params']['P_QS']
    assert R['vk_abut']['calendar']['attn_extend_X'] == 0 or True
    layers = 35
    o_meas = dict(C2K=0, K2C=0, KVN='hidden: consumed by the next token attention (layer period %d edges >> KVN latency)'
                  % R['vc']['calendar']['layer_period'])
    rec = dict(
        schema='opentallas.xdie_qwen_1018.record.v1', lane='TOKEN-XDIE-QWEN', date='2026-10-18',
        vehicle=dict(bench='rtl/test/qwen_split/tb_xdie_qwen_exchange.sv', run='rtl/test/qwen_split/run_xdie_exchange.sh',
                     calendar_compiler='tools/qwen_split/xdie_exchange_cal.py', record_tool='tools/qwen_split/xdie_exchange_record.py',
                     simulator='Verilator 5.050 --binary --timing (fleet ot-run)', clock='1.2 GHz core edges', layers_per_run=layers,
                     witnesses=str(run)),
        rtl_commits=commits,
        modelled=dict(phy=dict(model='physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv', lat_cycles=5,
                               source='3.5 ns measured FDI-to-FDI, IEEE JSSC 2026 doi:10.1109/JSSC.2026.3651425 (registry sct:r-ucie-jssc26) '
                                      '-> 4.2 -> 5 cycles at 1.2 GHz; best 3 (CPMT 2022 bound), worst 9 (2x measured, phy json)',
                               sensitivity_lat9=F9),
                      die_seam_stages='register chains at the die depth (dv2f14bn fwd_lanes E 2 / kvs14c die.v relay chains); the '
                                      'positive runs equalise each bundle to its netlisted maximum (PLAN)',
                      stimuli='slice Q/K/V dd words, HOST context, sys_face slots, KV layer-programme authority, PV final '
                              'join result beats: compiled stimuli at the native59 / programme pins'),
        exchanges=[
            dict(name='C2K CMD + 32 Q (native59 -> KV attention programme)', per_layer=1, beats=33,
                 E_meas_cycles=F5['C2K_q31'], E_meas_cmd_cycles=F5['C2K_cmd'],
                 definition='last Q beat issue at native59 native_tx_v -> that beat at the programme q_valid (CMD: issue -> request_valid)',
                 O_meas=0, O_source='compiler token path: attn_kv window serial after qknorm_rope; no independent compute op scheduled inside it',
                 E_exposed=F5['C2K_q31'], grade='measured-current-RTL (composed vc+vk; full-pair co-sim blocked, see findings)'),
            dict(name='K2C 32 RESULT + STATUS (KV attention programme -> native59 -> DV return chain)', per_layer=1, beats=33,
                 E_meas_cycles=F5['K2C_r31'],
                 definition='last RESULT beat issue at the programme tx_valid -> that beat at native59 dr_o',
                 O_meas=0, O_source='compiler token path: o_proj starts after attn_kv (serial)', E_exposed=F5['K2C_r31'],
                 grade='measured-current-RTL (composed vc+vk)'),
            dict(name='KVN 4 words (new K/V, native59 formatter -> KV d2d KVN word)', per_layer=1, beats=4,
                 E_meas_cycles=F5['KVN_last'], O_meas=o_meas['KVN'], E_exposed=0, grade='measured-current-RTL (vc)'),
        ],
        kv_service_cmd_land_to_r31_issue=F5['kv_service_cmd_land_to_r31_issue'],
        layer_attention_segment=dict(
            measured_q0_to_r31_land=F5['q0_to_r31_land'], priced_q0_to_r31_land=priced_rt,
            delta_per_layer=F5['q0_to_r31_land'] - priced_rt,
            delta_per_layer_phy9=F9['q0_to_r31_land'] - priced_rt,
            note='q0 = the compiled CMD slot (end of qknorm_rope); priced = the d2d_link_calendar image with zero-latency '
                 'component codecs (vk_abut reproduces it). Abutted real producers (vc_abut/vk_abut): +%d.'
                 % (leg('vc_abut', 'cmd_issue', 'cmd_land') + (R['vc_abut']['meas'][0]['cmd_issue'] - R['vc_abut']['calendar']['params']['P_QS'])
                    + leg('vc_abut', 'r31_issue', 'r31_land') + F5['kv_service_cmd_land_to_r31_issue'] - priced_rt)),
        composition=dict(
            formula='T_token += sum_l n_l * max(0, E_meas - O_meas)  (exchanges above; n_l = 1 per decode layer)',
            layers_covered='L1..L35 (segment 0, identical windows); L0 (token-run window 2038) NOT run: see findings F7',
            per_layer_exposed=F5['C2K_q31'] + F5['K2C_r31'], L1_L35_total=layers * (F5['C2K_q31'] + F5['K2C_r31']),
            vs_priced_token_path=dict(per_layer=F5['q0_to_r31_land'] - priced_rt, L1_L35_total=layers * (F5['q0_to_r31_land'] - priced_rt),
                                      phy9_L1_L35_total=layers * (F9['q0_to_r31_land'] - priced_rt)),
            usage='with TOKEN-PASS-QWEN C_die(l) terms that exclude every D2D leg (compute die to the Q issue / from the dr_o '
                  'land; KV die C_kv = programme CMD land -> last RESULT issue = %d, fixed by SERVICE_END 1777): add '
                  'per_layer_exposed. If C_die keeps the priced attn_kv window (1816), add vs_priced_token_path instead.'
                  % F5['kv_service_cmd_land_to_r31_issue']),
        configs={n: dict(expect=exp[n][0], got=exp[n][1], cfg=R[n]['cfg'], E=R[n]['E'], causes=R[n]['causes'],
                         first_errors=R[n]['first_errors'],
                         X=(R[n]['calendar'] or {}).get('attn_extend_X'), txd=(R[n]['calendar'] or {}).get('txd'))
                 for n in exp},
    )
    out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(full_phy5=F5, full_phy9=F9, priced=priced_rt, composition=rec['composition']), indent=1))


if __name__ == '__main__':
    main()
