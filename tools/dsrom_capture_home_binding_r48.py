"""Source geometry census before capture cuts. Rectangle gaps are not routes."""
import gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_capture_home_binding_r48_20261002/inputs'
def load(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def gap(a,b):
    return max(b[0]-a[2],a[0]-b[2],0)+max(b[1]-a[3],a[1]-b[3],0)
def model():
    origins=load(BASE/'source_origins.json')
    for name,record in origins.items():
        if hashlib.sha256((BASE/name).read_bytes()).hexdigest()!=record['sha256']:raise ValueError('geometry/source snapshot changed '+name)
    field=load(BASE/'field.json.gz');services=load(BASE/'services.json.gz');banks=load(BASE/'capture_cells.json');clock=load(BASE/'clock_contract.json')
    assert len(field)==2048 and {i['local_pair'] for i in field}==set(range(2048))
    assert banks['row_to_root']=='(row %256)//2' and banks['all768_identical_row_to_root']
    dest={x['name']:x['bbox_DBU'] for x in services if x['name'] in ('HUB_VM','HUB_SU_VECTOR','PROSPECTIVE_COMMON_CONTROLLER_CUT')}
    roots=[]
    for r in range(64):
        rows=[x for x in field if x['source_root']==r];assert len(rows)==32
        boxes=[x['bbox_DBU'] for x in rows];bounds=[min(x[0] for x in boxes),min(x[1] for x in boxes),max(x[2] for x in boxes),max(x[3] for x in boxes)]
        roots.append(dict(source_root=r,source_pair_ids=[x['local_pair'] for x in rows],producer_frame_envelope_DBU=bounds,producer_frame_not_root_pin=True,capture_bank_home=None,root_output_pin=None,sink_seat_home=None,local_selector_home=None,stall_feedback_home=None,minimum_frame_to_reserved_service_gap_DBU={n:min(gap(b,x) for b in boxes) for n,x in dest.items()},routed_distance=None,physical_delay_ps=None,consumer_deadline=None))
    sources=[BASE/'field.json.gz',BASE/'services.json.gz',BASE/'bands.json.gz',BASE/'capture_cells.json',BASE/'clock_contract.json']
    return dict(schema='DSROM_CAPTURE_HOME_BINDING_R48',verdict='BLOCKED_ACTUAL_CAPTURE_SINK_CONTROL_PIN_HOMES_AND_DEADLINES',candidate='DS4096-TP4-S58-PAR2-NP2048',source_pins={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},geometry_scope='one shard parent template; 64 roots, 32 complete pairs per root; no per-stage/rank placement extrapolation',root_envelopes=roots,reserved_service_boxes=dest,raw_record_bits=69,total_capture_seats=576,ordered_scalar_rows_unchanged=True,rootmap_unchanged=True,nominal_balanced_tree_used=False,registered_stage_cuts_selected=False,source_clock_contract=clock['target_clock'],physical_clock_reset_PG_ingress=banks['source_clock_reset_PG_ingress'],actual_accepted_origin=clock['wholeprogram_accepted_I66_origin'],actual_consumer_deadline=None,CDC_implementation=None,CDC_latency_edges=None,coordinate_units='DBU in source files; rectangle lower bound only; no inferred routed length',parent_private_design=dict(source_snapshot_sha256=None,context_bits=169,request_bits=186,reply_bits=239,context_not_raw_record_alias=True,feedback_only_BUFx4_count=82454,parent_reported_feedback_only_body_um2=8415.25324,feedback_only_body_um2=82454*.10206,parent_report_minus_cell_product_um2=8415.25324-82454*.10206,typed_feedback_cone_reproduced=False,payload_forward_branch_feedback_cells_charged=False,forward_hold_screen=None,clock_reset_PG_routes_SS_capture_join=None),physical_admitted=False,new_RTL_or_build=False,owners=dict(Kepler='provider lease visibility reverse-credit and source ABI; no rootcapture cut implementation',Maxwell_Archimedes='physical homes pins route/clock feedback and typed hold cost',Hubble='actual accepted origin and required consumer deadline'),missing_provider_fields=['per-stage/rank/shard root-output pin and bank/sink/selector/control bounding boxes','actual consumer/control pin and clock/reset/PG ingress','positive routed forward/selector/stall-feedback paths incl OBS and PDN/via exclusions','stream1.2GHz to SU0.9GHz CDC ownership accepted/visible edges','private169bit context layout source hash and per-field identity widths','required first/last consumer edges from actual program'])
if __name__=='__main__':print(json.dumps(model(),sort_keys=True,indent=2))
