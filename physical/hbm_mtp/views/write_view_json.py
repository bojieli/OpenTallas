#!/usr/bin/env python3
"""mtp-lead 2026-10-09: view.json (opentallas.hbm_die_view.v1) for the two HBM MTP master views exported from the
INSTALLED (post-ECO) databases of their CLOSED closure-loop jobs."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
V = ROOT / 'physical/hbm_accel_die_views'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def inputs(d):
    out = {}
    for line in (d / 'input_sha256.txt').read_text().splitlines():
        h, p = line.split()
        out[Path(p).name] = h
    return out


COMMON = dict(export=dict(tool='physical/hbm_mtp/views/run_export.sh + mk_export.py (openroad/orfs:asap7lock)',
                          sdc='6_final.sdc of the installed database (the timing models carry the block SDC; sign-off '
                              'numbers below are the loop corner_sta with its post-SDCs)',
                          libraries='ASAP7 RVT + LVT/SLVT twins (ECO / LVT cells present)'),
              port_check='port_check.json: abstract LEF pins == routed 6_final.v top ports, bit for bit')

VIEWS = {
    'mtp_hgi': dict(
        master='hgi_mtp_native', kind='mtp_hgi', status='closed',
        job='hgi_mtp_native-n14-lvt-5b9670b6d-tc-hm10', record_commit='db5a8e9a7', merged='ae380d24e',
        host='ot-epyc4',
        base='/srv/opentallas-scratch/claude/closure-loop/hgi_mtp_native-n14-lvt-5b9670b6d-tc-hm10/cl/eco/pass1/orfs/'
             'results/asap7/opentallas_hgi_mtp_native_asap7_mtp_hgi_mtp_native_n14_lvt_5b9670b6d_tc_hm10/base',
        eco='installed 2026-10-10T22:29:56-07:00 (post-route hold ECO cl/eco/pass1, +2,758 cells); exported from the '
            'installed 6_final.odb (the db the CLOSED corner_sta timed)',
        signoff=dict(tt_setup_ps=39.14, ff_hold_ps=8.80, ss_sensitivity_ps=-244.03, drc=0),
        die_binding=dict(
            variant='R25GQN (main d98cc3409 N14 DROP: dedicated MTP <-> router / coll nets removed; the MTP kernels '
                    'compile onto standard records)',
            status='VIEW READY; ports = the N14 contract (no router / coll groups)',
            ports='716 pin bits = clk, rst_n, f_cmdproc 197 in, t_cmdproc 517 out (port_check.json MATCH)',
            size_note='view 286.56 x 200.88 (unchanged footprint)'),
        note='N14 re-close at main 5b9670b6d (h deleted the tied XSEL / union logic, 6499df7c8); supersedes the '
             'nreg-a-lvt eaea6da41 view (853 pins incl. router / coll MTP groups). hm0 sibling also CLOSED '
             '(TT +42.63 / FF +4.29, record 4cc345c28).'),
    'mtp_hfd': dict(
        master='hfd_mtp_x_stop', kind='mtp_hfd', status='closed',
        job='hfd-mtp-x-stop-nreg-hm10-7bebe74b7-tc', record_commit='867da6c5f', merged='0c6d1d0c4',
        host='ot-epyc2',
        base='/srv/opentallas-data/claude/closure-loop/hfd-mtp-x-stop-nreg-hm10-7bebe74b7-tc/routes/'
             'hfd_mtp_x_stop_nreg_hm10_7bebe74b7_tc/work/orfs/results/asap7/'
             'opentallas_hfd_mtp_x_stop_asap7_mtp_hfd_mtp_x_stop_nreg_hm10_7bebe74b7_tc/base',
        eco='installed 2026-10-09T16:40:32-07:00 (post-route hold ECO cl/eco); exported from the installed '
            '6_final.odb (sha256 696aef85ea0b..., the db the CLOSED corner_sta timed)',
        signoff=dict(tt_setup_ps=17.39, ff_hold_ps=8.65, ss_sensitivity_ps=-283.20, drc=0),
        die_binding=dict(
            variant='r25m / r25i (MTP_SLOT 466.56 x 200.88, slot master "hfd_mtp")',
            status='SIZE MATCH, PIN MISMATCH by design: `hbm_die_views.py --variant r25m check --master hfd_mtp` -> '
                   'macro name hfd_mtp_x_stop != hfd_mtp; 1,319 generated pins missing / 1,358 view pins extra. The '
                   'generator\'s hfd_mtp is a placeholder with MTP_HUB_LINKS bus pins (126/320/657/64/64/78/8); the '
                   'closed block has its own MD-7 port set. Binding = MD-7 die integration: slot master -> '
                   'hfd_mtp_x_stop with the view\'s pins (spine_slot_masters + a ports.json from this LEF) and the '
                   'peer ECO pins (cmdproc_s t/f_mtp, su_red, router, coll)',
            ports='1,358 pin bits (port_check.json)'),
        note='ADOPTED HBM die MTP master (drive-0849 round 6).'),
}

for d, v in VIEWS.items():
    out = V / d
    m = v['master']
    files = [f'{m}.lef', f'{m}_ss.lib', f'{m}_ff.lib', f'{m}_tt.lib']
    rec = dict(schema='opentallas.hbm_die_view.v1', master=m, kind=v['kind'], status=v['status'],
               lef=f'{m}.lef', lib=dict(ss=f'{m}_ss.lib', ff=f'{m}_ff.lib', tt=f'{m}_tt.lib'),
               files_sha256={f: sha(out / f) for f in files},
               check=json.loads((out / 'port_check.json').read_text()) | dict(scope='LEF vs routed netlist ports'),
               size_um=json.loads((out / 'port_check.json').read_text())['size_um'],
               source=dict(job=v['job'], host=v['host'], installed_base=v['base'], record_commit=v['record_commit'],
                           merged_main=v['merged'], installed_inputs_sha256=inputs(out), eco=v['eco']),
               signoff_833=v['signoff'], die_binding=v['die_binding'], note=v['note'], **COMMON)
    (out / 'view.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(d, m, rec['size_um'], rec['check']['verdict'])
