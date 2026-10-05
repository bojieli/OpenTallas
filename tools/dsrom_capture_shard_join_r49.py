"""Two physical PAR2 dies; source owner census, not selected capture cuts."""
import collections,gzip,hashlib,json
from pathlib import Path
from dsrom_capture_home_binding_r48 import model as predecessor
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'results/uarch/dsrom_capture_shard_join_r49_20261002/inputs/selected_matrix_plans.jsonl.gz'
PLAN_SHA='c45db23a51501a0694a8bc523724287448a86364fa2368f93a7e68db3f950034'
def source_ownership(matrix):
    if (matrix['compiled_NP'],matrix['K'],matrix['rows'],matrix['segments'])!=(4096,5120,576,[[0,5120]]):raise ValueError('source dimensions')
    rows={}
    for seg,g,first,n,stride,start,w in matrix['plans']:
        if seg!=0 or not 0<=g<4096:raise ValueError('source segment/site')
        for j in range(n):
            for row in (2*(first+j*stride),2*(first+j*stride)+1):
                if row>=576:continue
                if row in rows:raise ValueError('duplicate owner')
                rows[row]=g//32
    if rows!={r:(r%256)//2 for r in range(576)}:raise ValueError('source row/root ownership differs')
    return rows

def identity(row,stage,rank,physical_shard):
    if type(row)is not int or not 0<=row<576:raise ValueError('row bound')
    root=(row%256)//2;shard=root//64
    if physical_shard!=shard or not 0<=stage<64 or not 0<=rank<4:raise ValueError('physicalshard not stage/rank alias')
    return dict(row=row,stage=stage,rank=rank,physical_shard=shard,logical_root=root,local_root=root%64)

def model():
    if hashlib.sha256(DATA.read_bytes()).hexdigest()!=PLAN_SHA:raise ValueError('source plans changed')
    count=0
    with gzip.open(DATA,'rt') as f:
        for line in f:source_ownership(json.loads(line)['matrix']);count+=1
    if count!=768:raise ValueError('all384 W1/W3 sources required')
    parent=predecessor();shards=[]
    for s,seats,height in [(0,320,172.8),(1,256,138.24)]:
        rows=[identity(r,0,0,s) for r in range(576) if ((r%256)//2)//64==s]
        depths=collections.Counter(r['local_root'] for r in rows);assert len(rows)==seats
        roots=[dict(x,physical_shard=s,logical_root=x['source_root']+s*64,local_root=x['source_root'],island_home=None,gather_request_route=None,request_ACK_route=None,return_route=None) for x in parent['root_envelopes']]
        shards.append(dict(physical_shard=s,physical_die_identity=None,global_roots=[64*s,64*s+63],local_roots=[0,63],seats=seats,depths_by_local_root=dict(sorted(depths.items())),ordered_owned_rows=rows,producer_frame_template=roots,raw69_slot=dict(width_um=204.93,height_um=height,utilization=.5,reserved_um2=204.93*height,raw_feedback_BUFs=2*seats*69,feedback_in_raw_width=True,physical_home=None,control_read_clock_PG_included=False),stream_clock_ps=1000/1.2,capture_pin_home=None,local_selector_pin_home=None,local_stall_feedback_pin_home=None))
    return dict(schema='DSROM_TWO_PHYSICAL_SHARD_CAPTURE_JOIN_R49',source_plan_sha256=PLAN_SHA,verified_source_matrices=count,physical_PAR2_die_count=2,logical_root_count=128,total_seats=576,shards=shards,logical_phase_lease_count=1,context_bits=170,request_bits=187,reply_bits=240,physical_shard_bits=1,physical_shard_separate_from_stage6_rank2=True,ordered_global_output_rows=list(range(576)),no_combinational_read_tree_across_dies=True,offdie_service=dict(request_route=None,request_ACK_bits=None,request_ACK_route=None,return_gather_home=None,return_route=None,gather_sink_seat_capacity=None,one_context_lease=True,read_sink_seat_reserved_before_issue_required=True,consumer_clock_ps=1000/.9,stream_serial_CDC=None,first_last_accepted_consumer_edges=None,service_latency_cycles=None),feedback=dict(raw_BUFs=2*576*69,control_BUFs=2*1483,total_BUFs=82454,source_BUF_area_um2=.10206,total_body_um2=82454*.10206,total_raw_slot_reservation_um2=sum(s['raw69_slot']['reserved_um2'] for s in shards),baseline_old_raw_slot_reservation_um2=152.766*(172.8+138.24),slot_delta_um2=(204.93-152.766)*(172.8+138.24),control_clock_PG_routes_not_in_raw_slots=True,raw_feedback_not_charged_again_to_forward_payload=True,forward_hold_screen=None,typed_feedback_prototype_source_sha256=None),extra_context_state_bits_per_outstanding_token=1,finite_token_capacity=None,extra_total_context_state_bits=None,registered_stage_cuts_selected=False,physical_admitted=False,RTL_or_build=False,predecessor_r48_one_template_scope_superseded=True)
if __name__=='__main__':print(json.dumps(model(),sort_keys=True,indent=2))
