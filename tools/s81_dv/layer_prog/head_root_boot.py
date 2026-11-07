"""Consume the actual HEAD ROOT88 source witness without inventing mission dates."""
import hashlib,json,re
from pathlib import Path

# HEAD l48uo coherent source bundle, built by
# results/token_pass/head_l48uo_compiler_1107/make_bundle.py from plan_of_record/l48uo.
# A later event needs its own reviewed source selection; this bundle is not physically admitted.
PINS={
 'source_plan.json':'f140216c876ba3186afdf3271f0f9b3ceadf63df95b5e0416a06af6dffcb54f6',
 'source_sidecar.json':'90d006a48f17adc6795bbf55e3077ff308bb6b417604167248051501cda25d77',
 'start_stages.json':'255b2b4e27a2c8b1bb202038cb89d021b4a7ff82a5afac3e52b45e84bbacb5eb',
 'start_stages.sv':'e9ed25cdd21dab157624adf049b27889d2774dfa530f0331c1595bdfa30c4002',
 'root88_report.json':'0aebf3ae714564846871c845cc64a9a39e623dfc43e68426b45e75af2922f21f',
 'boot88_account.json':'02acbd5e1065093b15c42ba437f25395f5b314a457da8186cc331bf40c3cc477'}
MANIFEST_SHA256='911ed1aea33fdf03e58c395603870647f62c0fd070849470006eb80dc1902347'
# The l48ui n4 event: +1 data cycle on these links, in the sidecar and not in plan latency.lanes.
N4_LINK_ADDED_CYCLES={'coll_WN1_u__1':4,'coll_WN2_u__3':4,'coll_WN1_d__0':2,'coll_WN2_d__0':2}


def read_witness(selection,root):
    if selection.get('schema')!='opentallas.head.root88_source_selection.v1':raise ValueError('explicit current HEAD ROOT88 source selection required')
    bundle=Path(root)/selection['bundle_root'];raw={}
    manifest_path=bundle/'current_source_manifest.json'
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest()!=MANIFEST_SHA256:
        raise ValueError('current HEAD coherent source manifest differs')
    manifest=json.loads(manifest_path.read_text())
    if manifest.get('schema')!='opentallas.head_current_source.l48uo.v1' or manifest.get('frozen')is not False or manifest.get('physical_admission')is not False:
        raise ValueError('actual HEAD bundle source-only qualification differs')
    for key,wanted in PINS.items():
        data=(bundle/key).read_bytes()
        if manifest['files'].get(key)!=wanted or hashlib.sha256(data).hexdigest()!=wanted:
            raise ValueError('current HEAD ROOT88 source identity differs: '+key)
        raw[key]=data.decode()
    side=json.loads(raw['source_sidecar.json'])
    stages=json.loads(raw['start_stages.json']);report=json.loads(raw['root88_report.json']);account=json.loads(raw['boot88_account.json'])
    if type(side['count_aligned']['root_settle_cycles'])is not int or side['count_aligned']['root_settle_cycles']!=88:
        raise ValueError('HEAD compiler rejects stale64/74 settle contract')
    roots=[s for s in stages['stages']if s.get('root')]
    if len(roots)!=1:raise ValueError('one actual HEAD root stage required')
    actual=roots[0]
    expected=dict(id='b0',region='st:h',module='ot_dp_landing_root',settle=88,clock_port='t_st_b0__clk',reset_port='wrst_sp3__rst_start_raw_22')
    if {k:actual.get(k)for k in expected}!=expected or stages['root_settle']!=88:raise ValueError('actual ROOT88 stage/clock/reset identity differs')
    if not re.search(r'ot_dp_landing_root\s+#\(\.SETTLE\(88\)\)\s+u_st_b0\s*\(\.clk\(t_st_b0__clk\),\s*\.rst_raw_n\(wrst_sp3__rst_start_raw_22\)',raw['start_stages.sv']):
        raise ValueError('actual emitted root SETTLE88/clock/reset differs')
    for obj,values in [(report,dict(root_settle_cycles=88,raw_relative_span=84,guard_cycles=4,delta_boot_cycles=14,added_steady_cycles=0)),
        (account,dict(root_settle_cycles=88,previous_settle_cycles=74,delta_boot_cycles=14,added_steady_cycles=0,root_raw_release_cycle=21,root_start_upper_cycle=110,part_start_max_cycle=382))]:
        if any(type(obj.get(k))is not int or obj[k]!=v for k,v in values.items()):raise ValueError('ROOT88 actual boot cycle accounting differs')
    for port,cycles in N4_LINK_ADDED_CYCLES.items():
        row=next((p for p in side['ports'] if p['port']==port),None)
        if row is None or row['added_cycles']!=cycles or side['count_aligned']['ports'][port]['sched_lat']!=cycles:
            raise ValueError('HEAD sidecar lacks the n4 +1 data cycle: '+port)
    budget=side['collector']['boot_budget']
    if budget['root_settle_cycles']!=88 or budget['delta_boot_cycles']!=14 or budget['data_cycles_added']!=0:
        raise ValueError('enriched HEAD metadata boot cost differs')
    # These are source bounds under stated clocks and CA windows. They never
    # establish a success event or provide an external producer/mission date.
    if any(budget.get(k)is not None for k in ('native_pma_phy_ready_cycle','actual_external_host_event_cycle','actual_mission_cycle')):
        raise ValueError('source-only HEAD bound unexpectedly advertises a physical date')
    if account['physical_clock_phase_qualified']is not False or account['actual_external_host_event_cycle']is not None or account['actual_physical_full_array_boot_receipt']is not None:
        raise ValueError('source-only HEAD accounting is not a global physical witness')
    return dict(schema='opentallas.head.root88_compiler_boot.v1',status='SOURCE_WITNESS_ONLY',plan_event='l48uo',
        n4_link_added_cycles=dict(N4_LINK_ADDED_CYCLES),n4_data_cycles_added_per_link=1,
        source_plan_sha256=PINS['source_plan.json'],source_witness_sha256=dict(PINS),
        root=expected,root_settle_cycles=88,previous_settle_cycles=74,delta_boot_cycles=14,
        delta_from_original64_boot_cycles=24,added_steady_cycles=0,
        source_bounds=dict(root_start_upper_cycle=110,part_start_max_cycle=382,control_ready_or_fault_upper_cycle=5861),
        bounds_scope='conditional generated START/CA/status network READY_OR_FAULT; native PMA/PHY/external HOST/mission excluded',
        physical_START_qualified=False,actual_physical_START_cycle=None,
        admission='actual registered root ready && !actual sticky fault && actual host boot_done',
        global_booking_qualified=False)


def pipeline_guard(bookings,root):
    selection=bookings.get('head_root88_witness')
    if not selection:return None,[dict(cause='current_HEAD_ROOT88_source_witness_missing')]
    try:witness=read_witness(selection,root)
    except (ValueError,KeyError,OSError,TypeError)as exc:
        return None,[dict(cause='current_HEAD_ROOT88_source_witness_unqualified',detail=str(exc))]
    gaps=[]
    if bookings.get('selected_HEAD_source_plan_sha256')!=witness['source_plan_sha256']:
        gaps.append(dict(cause='HEAD_ROOT88_not_bound_to_selected_source_plan'))
    # The actual current witness supplies no physical launch authority, even if
    # a caller fills in a number from a conditional timeout or source bound.
    gaps.append(dict(cause='HEAD_physical_START_HOST_PMA_authority_missing',
        actual_physical_START_cycle=None,root_ready_or_fault_bound_is_not_mission=True))
    return witness,gaps
