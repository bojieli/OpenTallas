"""Consume the actual HEAD ROOT88 source witness without inventing mission dates."""
import hashlib,json,re
from pathlib import Path

# Owner-supplied coherent current source bundle. A later event needs its own
# reviewed source selection; this bundle is explicitly not physically admitted.
PINS={
 'source_plan.json':'655784af46096873ba3235578fbc045d24a567ec614aedc4ad16b4cb11e12d2f',
 'source_sidecar.json':'02dececead4ad7facaac03791bcdd63dcb593637ee23cfda73c52ab8925f2044',
 'start_stages_src25q.json':'268dbd422ba708b36ff9eec33c47b76898b2ec3502eddafa1a0cb98fd8fd40b3',
 'start_stages.sv':'47d93bb26b712a8a859d596fe273bc7f0af39d38a847993435b4971f7ec071da',
 'root88_report.json':'6576ac58311ad8cc9550ab037f5fab8e6303a3232955060d2dddf55b7f18750d',
 'boot88_account.json':'096ec946d40120485b9e12ed68ff664605fb273f278255162b2db355b24d335d'}


def read_witness(selection,root):
    if selection.get('schema')!='opentallas.head.root88_source_selection.v1':raise ValueError('explicit current HEAD ROOT88 source selection required')
    bundle=Path(root)/selection['bundle_root'];raw={}
    manifest_path=bundle/'current_source_manifest.json'
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest()!='011c8ca00f9742eaf1c4369fe801d471bb2d61ecc12929d9a038031177d4859b':
        raise ValueError('current HEAD coherent source manifest differs')
    manifest=json.loads(manifest_path.read_text())
    if manifest.get('schema')!='opentallas.head_current_source.legal88.v1' or manifest.get('frozen')is not False or manifest.get('physical_admission')is not False:
        raise ValueError('actual HEAD bundle source-only qualification differs')
    for key,wanted in PINS.items():
        data=(bundle/key).read_bytes()
        if manifest['files'].get(key)!=wanted or hashlib.sha256(data).hexdigest()!=wanted:
            raise ValueError('current HEAD ROOT88 source identity differs: '+key)
        raw[key]=data.decode()
    side=json.loads(raw['source_sidecar.json'])
    stages=json.loads(raw['start_stages_src25q.json']);report=json.loads(raw['root88_report.json']);account=json.loads(raw['boot88_account.json'])
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
    budget=side['collector']['boot_budget']
    if budget['root_settle_cycles']!=88 or budget['delta_boot_cycles']!=14 or budget['data_cycles_added']!=0:
        raise ValueError('enriched HEAD metadata boot cost differs')
    # These are source bounds under stated clocks and CA windows. They never
    # establish a success event or provide an external producer/mission date.
    if any(budget.get(k)is not None for k in ('native_pma_phy_ready_cycle','actual_external_host_event_cycle','actual_mission_cycle')):
        raise ValueError('source-only HEAD bound unexpectedly advertises a physical date')
    if account['physical_clock_phase_qualified']is not False or account['actual_external_host_event_cycle']is not None or account['actual_physical_full_array_boot_receipt']is not None:
        raise ValueError('source-only HEAD accounting is not a global physical witness')
    return dict(schema='opentallas.head.root88_compiler_boot.v1',status='SOURCE_WITNESS_ONLY',
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
