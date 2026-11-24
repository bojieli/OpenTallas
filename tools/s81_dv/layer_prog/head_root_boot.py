"""Consume the actual HEAD ROOT88 source witness without inventing mission dates."""
import hashlib,json,re
from pathlib import Path

# HEAD W6 coherent source bundle (HEAD-R18, COORD ruling 11-24), built by
# results/token_pass/head_w6_compiler_1124/make_bundle.py from the live W6 plan b3507e628de6, the W6 sidecar with the
# lep0N_w status-network fix and the START tree re-sited on the W6 type raw exports.  Was l48uo f140216c (11-07).
# A later event needs its own reviewed source selection; this bundle is not physically admitted.
PINS={
 'source_plan.json':'b3507e628de66025925b5e381ad18d6efd5bde9e5a98b826a7d52815a5840381',
 'source_sidecar.json':'ba968452ea5ae279da4ba59efbfbf026d7abac9a80729c30770f3119547411ac',
 'start_stages.json':'b0970ff4a93ecc1a7aa92302e17dd06b89acfb7560def25cc14c982956aae649',
 'start_stages.sv':'8ac30434ad222d125771e4f5891376064f5bf0a5a5c72acca9bcac1178923b5f',
 'root88_report.json':'ab60927a80ad8e2974bfa5b76f109a05844ab2872861722af93fff52d03f756d',
 'boot88_account.json':'332d8fcadaf6faa04b7a0c75b1567381c6f620927a021e4c788aa6d3b3fc23a2'}
MANIFEST_SHA256='793d69f1300dbc46525e200b6a6474bf72f3db76fa782dd8260aa37f3d14231d'
# The l48ui n4 links as the W6 sidecar carries them: (added_cycles, count-aligned sched_lat).  Since l48uo the plan
# latency equals sidecar sched_lat; the d links carry +2 added and sched_lat 4.
N4_LINK_ADDED_CYCLES={'coll_WN1_u__1':4,'coll_WN2_u__3':4,'coll_WN1_d__0':2,'coll_WN2_d__0':2}
N4_LINK_SCHED_LAT={'coll_WN1_u__1':4,'coll_WN2_u__3':4,'coll_WN1_d__0':4,'coll_WN2_d__0':4}
# Recomputed W6 boot account (make_bundle.py, 10-30 accountant arithmetic).  The sidecar boot_budget still states the
# l48uo values 110/382/5861; the witness uses the recomputed bounds.
SOURCE_BOUNDS=dict(root_start_upper_cycle=113,part_start_max_cycle=365,control_ready_or_fault_upper_cycle=5851)


def read_witness(selection,root):
    if selection.get('schema')!='opentallas.head.root88_source_selection.v1':raise ValueError('explicit current HEAD ROOT88 source selection required')
    bundle=Path(root)/selection['bundle_root'];raw={}
    manifest_path=bundle/'current_source_manifest.json'
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest()!=MANIFEST_SHA256:
        raise ValueError('current HEAD coherent source manifest differs')
    manifest=json.loads(manifest_path.read_text())
    if manifest.get('schema')!='opentallas.head_current_source.w6.v1' or manifest.get('frozen')is not False or manifest.get('physical_admission')is not False:
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
    for obj,values in [(report,dict(root_settle_cycles=88,raw_relative_span=72,guard_cycles=4,delta_boot_cycles=24,added_steady_cycles=0)),
        (account,dict(root_settle_cycles=88,previous_settle_cycles=64,delta_boot_cycles=24,added_steady_cycles=0,root_raw_release_cycle=24,root_start_upper_cycle=113,part_start_max_cycle=365,status_ready_or_fault_at_glue_upper_cycle=5851))]:
        if any(type(obj.get(k))is not int or obj[k]!=v for k,v in values.items()):raise ValueError('ROOT88 actual boot cycle accounting differs')
    for port,cycles in N4_LINK_ADDED_CYCLES.items():
        row=next((p for p in side['ports'] if p['port']==port),None)
        if row is None or row['added_cycles']!=cycles or side['count_aligned']['ports'][port]['sched_lat']!=N4_LINK_SCHED_LAT[port]:
            raise ValueError('HEAD sidecar lacks the n4 +1 data cycle: '+port)
    budget=side['collector']['boot_budget']
    if budget['root_settle_cycles']!=88 or budget['data_cycles_added']!=0:
        raise ValueError('enriched HEAD metadata boot cost differs')
    # These are source bounds under stated clocks and CA windows. They never
    # establish a success event or provide an external producer/mission date.
    if any(budget.get(k)is not None for k in ('native_pma_phy_ready_cycle','actual_external_host_event_cycle','actual_mission_cycle')):
        raise ValueError('source-only HEAD bound unexpectedly advertises a physical date')
    if account['physical_clock_phase_qualified']is not False or account['actual_external_host_event_cycle']is not None or account['actual_physical_full_array_boot_receipt']is not None:
        raise ValueError('source-only HEAD accounting is not a global physical witness')
    return dict(schema='opentallas.head.root88_compiler_boot.v1',status='SOURCE_WITNESS_ONLY',plan_event='w6',
        n4_link_added_cycles=dict(N4_LINK_ADDED_CYCLES),n4_link_sched_lat=dict(N4_LINK_SCHED_LAT),n4_data_cycles_added_per_link=1,
        source_plan_sha256=PINS['source_plan.json'],source_witness_sha256=dict(PINS),
        root=expected,root_settle_cycles=88,previous_settle_cycles=64,delta_boot_cycles=24,
        delta_from_original64_boot_cycles=24,added_steady_cycles=0,
        source_bounds=dict(SOURCE_BOUNDS),
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
