"""Source-fixed SAFE2 pipeline costs, separate from measured external die lanes.

This is a planning receipt, not a replacement for the post-forwarding netlist
table or an adopted token calendar. Missing external lanes stay unknown.
"""


def plan_receipt(m, stacks, order):
    rs = m.get('relay_stages') or {}
    chain = list(reversed(order))
    rows, missing = [], set()

    def path(bids):
        unknown = [b for b in bids if b not in rs]
        missing.update(unknown)
        return dict(buses=bids, relay_edges=None if unknown else sum(rs[b] for b in bids))

    for stack in stacks:
        for depth, group in enumerate(chain):
            ctl = [f'ks_kvs_hroot_{stack}__o_ch0'] + [
                f'ks_slg_{stack}_{g}__o_dn' for g in chain[:depth]]
            gather = [f'ks_slg_{stack}_{g}__o_ctl' for g in chain[:depth + 1]]
            rows.append(dict(instance=f'slg_{stack}_{group}', depth=depth,
                             control=path(ctl), gather=path(gather),
                             control_face_edges=depth + 1, gather_face_edges=depth,
                             est_face_edges=1, reset_release_edges=dict(core=2, hbm=2)))
    return dict(schema='opentallas.kv_grp_safe2_plan.v1', groups=rows,
                missing_external_buses=sorted(missing),
                external_age_basis='generator relay stages before forwarded/landed replacement',
                source_age_basis='qkd_kvs_grp_s2 icq_o/icq_leaf, iuq and estq posedge ck flops',
                qualified=False,
                remaining='Recompose actual forwarded/landed lane ages and boot/first-use/status calendars; '
                          'native child timing and parent clock-pair checks remain required')
