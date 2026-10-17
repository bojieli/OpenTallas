#!/usr/bin/env python3
"""Per-class bit-weighted relay stages of the selected HBM die plan -> an eval.json option for layout_ds_cost_1016.py
(H-DIE 10-16; ROOT RELAY-SCHEMA 10-16: reads opentallas.die_relay_stages.v1, fails closed).

    relay_class_price.py PLAN_STAGES.json[.gz] OUT_eval.json [--compiled-out SCHED.json] [--override BUS_ID=N ...]
    relay_class_price.py --legacy-relay-pass RELAY_PASS.json OUT_eval.json      (diagnostic only, logged)

PLAN_STAGES = the die plan's per-bus table (tools/hbm_die_v15/relay_stages_export.py; env OT_DIE_RELAY_STAGES_HBM
when the positional is '-').  Class value = width-weighted mean stages over the plan buses of its (origin master.port
-> sink master.port) pair; SM_X = max(vms.rr->ctlw) + max(ctlw.xw_data->smh) (equal-age broadcast: max).  A class
pair with no bus in the plan is an ERROR (no default 0).  --compiled-out writes the table this pricing used
(role compiled_schedule) for tools/die_relay_check.py.
"""
import argparse, collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import die_relay_stages as DRS  # noqa: E402

BASE_EVAL = str(HERE.parents[1] / 'results/arch/hbm_die_v15/core4_sfu2_b3624/eval.json')
QS = ['NE', 'NW', 'SE', 'SW']
# class -> list of legs; a leg = ('mean'|'max', [(origin master.port, sink master.port), ...] alternatives -> max)
CLASSES = dict(
    SM_HBM=[('mean', [('ot_hbm_svc_pc_ctrl_leaf.kr_data', 'ot_hbm_svc_vm_kshare.c_kr_data')]),
            ('mean', [('ot_hbm_svc_vm_kshare.g_kr_data', 'ot_hbm_svc_sm_group.kr_data')]),
            ('mean', [('ot_hbm_svc_sm_group.sm_packet', 'ot_hbm_accel_smh_attn.packet')])],
    SM_X=[('mean', [(f'hfd_hgi_vms_static_{Q}.rr', 'ot_hgi_sm_xload_cl2_ctlw.rr') for Q in QS]),
          ('max', [('ot_hgi_sm_xload_cl2_ctlw.xw_data', 'ot_hbm_accel_smh_attn.xw_data')])],
    SM_OUT=[('mean', [('ot_hbm_accel_smh_attn.rdata', 'ot_hbm_sm_vm_wr_q_t.rdata')])],
    HBM_VM=[('mean', [('ot_hbm_svc_vm_kshare.fill_data', 'ot_hbm_svc_vmdel_lane.fill_data_i')])],
    VM_HBM=[('mean', [('ot_hbm_svc_wb_kport.w_k_wdata', 'ot_hbm_svc_vm_kshare.w_k_wdata')])],
    HC_ENG=[('mean', [('ot_hbm_hc_q_static.x_wave', 'ot_hbm_hc_eng_static.x_wave')])],
    SFU_CORE=[('mean', [('ot_hgi_sfu_core_split.local_wq', 'ot_hgi_sfu_lg_pair_leaf.c_wq')])],
    LG_HC=[('mean', [('ot_hbm_hc_q_static.lg_wq', 'ot_hgi_sfu_lg_pair_leaf.c_wq')])],
    COLL_EP=[('mean', [('ot_hfd_coll_q2_static_host_v4.tx_pin_flit', 'hfd_ep_static.tx_frame')])],
    VM_RING=[('mean', [('hfd_hgi_vms_static_SW.ccw_out', 'hfd_hgi_vms_static_NW.ccw_in')])],
    LG_SU=[('mean', [('ot_hbm_vm_lg_static_bank.near_wq', f'hfd_hgi_vms_static_{Q}.wq') for Q in QS])])


class ClassPriceError(ValueError):
    pass


def class_stages(table):
    """-> ({class: stages}, {bus id: [classes]}); every leg alternative must have >= 1 plan bus (fail closed)"""
    vals, used = {}, collections.defaultdict(list)
    for cls, legs in CLASSES.items():
        tot = 0.0
        for how, alts in legs:
            best = None
            for o, s in alts:
                om, op = o.split('.', 1); sm, sp = s.split('.', 1)
                m = table.match(src_master=om, src_port=op, dst_master=sm, dst_port=sp)
                if not m:
                    raise ClassPriceError(f'class {cls}: no bus {o} -> {s} in die plan {table.doc["plan"]["id"]} '
                                          '(fail closed; fix the class map or the plan export)')
                for b in m:
                    used[b['id']].append(cls)
                w = sum(b['width'] for b in m)
                v = sum(b['width'] * b['stages'] for b in m) / w if how == 'mean' else max(b['stages'] for b in m)
                best = v if best is None else max(best, v)
            tot += best
        vals[cls] = tot
    return vals, used


def legacy_class_stages(d):
    def q(o, s, default=0.0):
        r = [x for x in d['end_to_end'] if x['origin'] == o and x['sinks'] == s]
        return r[0]['total_mean'] if r else default

    def qmax(o, s):
        r = [x for x in d['end_to_end'] if x['origin'] == o and x['sinks'] == s]
        return r[0]['total_max'] if r else 0.0
    out = {}
    for cls, legs in CLASSES.items():
        out[cls] = sum(max((q if how == 'mean' else qmax)(o, s) for o, s in alts) for how, alts in legs)
    return out


def price(vals, base_eval=BASE_EVAL):
    b = json.loads(Path(base_eval).read_text())
    A = json.loads(json.dumps(b))
    for k, v in vals.items():
        A['per_class'][k]['stages_bw'] = v
    A['per_class']['SU_CORE']['stages_bw'] = b['per_class']['SU_CORE']['stages_bw'] * 480 / 450   # partitioned programme, issue-ahead
    return A


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('plan', help="die plan die_relay_stages file ('-' = env OT_DIE_RELAY_STAGES_HBM)")
    ap.add_argument('out'); ap.add_argument('--compiled-out'); ap.add_argument('--base-eval', default=BASE_EVAL)
    ap.add_argument('--override', action='append', default=[], metavar='BUS_ID=N',
                    help='DIAGNOSTIC ONLY: replace one bus stage count (logged, recorded; die_relay_check fails it)')
    ap.add_argument('--legacy-relay-pass', action='store_true',
                    help='DIAGNOSTIC ONLY: price from an old die_relay_pass end_to_end file (no schema, no check)')
    a = ap.parse_args(argv)
    if a.legacy_relay_pass:
        print('relay_class_price: DIAGNOSTIC --legacy-relay-pass: not a die_relay_stages plan; result cannot be '
              'checked against a die run', file=sys.stderr)
        vals = legacy_class_stages(json.loads(Path(a.plan).read_text()))
        A = price(vals, a.base_eval)
        A['relay_stage_source'] = dict(kind='legacy_relay_pass', path=a.plan)
    else:
        p = DRS.plan_path('hbm', None if a.plan == '-' else a.plan)
        doc = DRS.load(p)
        if doc['design'] != 'hbm':
            raise SystemExit(f'relay_class_price: {p} is design {doc["design"]}, not hbm')
        ov = DRS.parse_overrides(a.override)
        sched = DRS.compiled(doc, 'tools/hbm_die_v15/relay_class_price.py', loaded_from=p, overrides=ov)
        vals, used = class_stages(DRS.Table(sched, str(p)))
        sched['compiled']['used_by'] = {k: sorted(set(v)) for k, v in used.items()}
        A = price(vals, a.base_eval)
        A['relay_stage_source'] = dict(kind=DRS.SCHEMA, path=str(p), plan=doc['plan']['id'], digest=doc['digest'],
                                       overrides=sched['compiled']['overrides'])
        if a.compiled_out:
            DRS.write(a.compiled_out, sched)
    json.dump(A, open(a.out, 'w'))
    print({k: round(v, 2) for k, v in vals.items()})


if __name__ == '__main__':
    main()
