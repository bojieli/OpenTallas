#!/usr/bin/env python3
"""Place one gross hook proposal; preserve separate bank and VM lease fences."""
import argparse,hashlib,json,re
from fractions import Fraction
from pathlib import Path
import dsrom_capture_identity_slot_join as I
import dsrom_capture_consumer_admission as A
import dsrom_capture_selected_bank_escape as E
from dsrom_capture_publication_credit import identity
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_capture_completion_hook_slot_20261003'

def callback_order(e):
    # Enrolled callbacks only: fixtures do not establish an actual deadline.
    if not e.get('enrolled') or not e.get('origin_id'):raise ValueError('accepted origin required')
    if e.get('clock_domain')!='native_single_clk':raise ValueError('CDC cannot inherit native edge proof')
    keys=('VM_visible','captured_credit','packet_retired','F','later_GU0_accept','SU_front_accept','SU_read','observed_Xtag','VM_lease_release')
    if any(e.get(k) is None for k in keys):raise ValueError('complete accepted callbacks')
    expected=identity(e.get('owned_context',{}))
    if set(e.get('callback_contexts',{}))!=set(keys) or any(identity(e['callback_contexts'][k])!=expected for k in keys):raise ValueError('full169 callback lineage')
    v={k:Fraction(e[k]) for k in keys}
    if not v['VM_visible']<v['captured_credit']<v['F'] or not v['packet_retired']<v['F']:raise ValueError('positive credit and pre-F publication')
    if v['later_GU0_accept']<v['F']+1 or v['SU_front_accept']<v['later_GU0_accept']+6:raise ValueError('registered source FSM fence')
    if v['SU_read']<v['SU_front_accept'] or v['observed_Xtag']!=v['SU_read']+2:raise ValueError('native accepted read/R+2 tag')
    if v['VM_lease_release']<v['observed_Xtag']:raise ValueError('old VM version still owned')
    if e.get('bank_waits_for_SU_read'):raise ValueError('bank lease must not depend on SU read')
    return True

def build():
    raw=(BASE/'inputs/composition.json').read_bytes();origin=json.loads((BASE/'inputs/origin.json').read_text())
    if hashlib.sha256(raw).hexdigest()!=origin['sha256']:raise ValueError('composition drift')
    n=json.loads(raw);hook=n['constructive_deadline']['hook_allowedcell_floor'];identity=I.build();d,_=I.H.H.inputs();facts=d['capture.json']['source_cell_facts']
    counts=dict(hook['cell_counts']);buf='BUFx4_ASAP7_75t_R';counts[buf]+=2 #local CLK and RESETN fanout; upstream extra, not free
    strip=identity['identity_strip_bbox_DBU'];prior=identity['source_cell_proposal'];x=max(c['bbox_DBU'][2] for c in prior);y=strip[1]
    start=x;cells=[]
    for master,count in sorted(counts.items()):
        width=round(float(re.search(r'SIZE\s+([\d.]+)',d['cell_LEF.json'][master])[1])*1000)
        for index in range(count):
            cells.append(dict(proposed_instance=f'hook.{master}.{index}',master=master,orientation='R0',bbox_DBU=[x,y,x+width,y+270],actual_RTL_instance=None,role=('feedback' if index<4 else 'local_CLK' if index==4 else 'local_RESETN') if master==buf else 'gross_hook_control'));x+=width
    if any(E.overlap(c['bbox_DBU'],p['bbox_DBU']) for c in cells for p in prior):raise ValueError('identity collision')
    body=sum((c['bbox_DBU'][2]-c['bbox_DBU'][0])*270 for c in cells)/1e6
    # A distinct 50% reservation stays inside the existing strip; no old cells borrowed.
    reserve=[start,y,start+2*(x-start),y+270]
    if reserve[2]>strip[2]:raise ValueError('hook tail overflow')
    repair=ROOT/'results/uarch/dsrom_capture_clock_branch_reallocation_20261003'
    for shard in (0,1):
        import gzip
        sites=json.loads(gzip.decompress((repair/f'shard{shard}_sites.json.gz').read_bytes()))
        if any(E.overlap(reserve,p['bbox_DBU']) for p in sites):raise ValueError('relocated clock site collision')
    lane=A.inputs()['lane.sv.gz']
    for text in ('assign rd_re = {4{mr_v}}','m_v <= mr_v; x_v <= m_v','x_a <= rd_q[31:0]'):
        if text not in lane:raise ValueError('source SU read/tag path changed')
    return dict(schema='DS_GROSS_COMPLETION_HOOK_NAMED_SLOT_V1',candidate='DS4096-TP4-S58-PAR2-NP2048',composition_origin=origin,
        selected_clock_bank=n['clock_bank'],clock_repair_commit='53dfdf1c9d2bdc4d6a88a24fd785529b1ffad75d',annex_charge_mm2=0,
        gross_hook_cells=cells,gross_hook_body_um2=hook['body_um2'],additional_local_clock_reset_BUF=2,
        placed_body_um2=body,reserve50pct_mm2=2*body/1e6,reservation_bbox_DBU=reserve,
        source_identity_cells_untouched=True,selected_correction_buffers_untouched=True,one_proposed_hook_home=dict(stage=0,rank=0,physical_shard=0,region='existing identity-strip tail'),
        all_stage_or_remote_owner_hook_replication_selected=False,
        new_clock_input_pin=E.transform(E.shapes(d['cell_LEF.json'][buf],'A')[0],next(c for c in cells if c['role']=='local_CLK')),
        new_reset_input_pin=E.transform(E.shapes(d['cell_LEF.json'][buf],'A')[0],next(c for c in cells if c['role']=='local_RESETN')),
        SSFF_ASR_CLK_loads=hook['SSFF_new_CLK_pin_fF'],SSFF_ASR_RESET_loads=hook['SSFF_new_RESETN_pin_fF'],
        upstream_new_BUF_input_load_fF={corner:facts[buf][corner]['pins']['A']['cap_fF'] for corner in ('SS','FF')},
        relative_native_fences=n['constructive_deadline']['fences'],relative_bound='VMvisible < positive captured credit < effective-idle preedge F; later GU0 >=F+1; adjacent SUfront >=F+7',
        bank_rearm_not_waiting_for_SU_read=True,VM_address_version_lease_through_all_accepted_reads_and_observed_Rplus2=True,
        native_lane_source_sha256=hashlib.sha256(lane.encode()).hexdigest(),context_bits=169,user_bits=32,
        actual_current_PHW10_origin=None,actual_callback_journal=None,actual_first_last_read=None,actual_max_VM_versions=None,
        C=None,physical_station_register_count=None,CDC_latency=None,
        full169_comparator_counters_ingress_fault_logic_not_in_gross_hook=True,
        full_control_PG_escape_and_clock_reset_routes_qualified=False,samecell_feedback_lower_bound_not_FF_closure=True,
        SU_guard_selected=False,original_native_hook_implemented=False,added_cycles=None,token_delta=None,
        physical_fit=False,contextual_PR_admitted=False,remaining_gate='Bind named hook pins to qualified upstream clock/reset and full-context retirement owner; enroll current PHW10 F/read/tag callbacks, then choose finite C/stations from accepted service and actual routes.',new_jobs=[])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=BASE/'model.json');a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),sort_keys=True,indent=2)+'\n')
