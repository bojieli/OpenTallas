#!/usr/bin/env python3
"""Read-only analytical accounting; no EDA or simulation."""
import collections, gzip, hashlib, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
SRC=HERE.parent/'attn_graph_audit_1019'
cells={}; pins={}; drivers=collections.defaultdict(list); inputs=collections.defaultdict(list)
for line in gzip.open(SRC/'graph.tsv.gz','rt'):
    a=line.rstrip().split('\t')
    if a[0]=='CELL': cells[a[1]]=a[2]
    if a[0]=='PIN' and a[3]=='SIGNAL':
        pins[a[1]]=a
        if a[2]=='OUTPUT': drivers[a[4]].append(a[1])
        elif a[2]=='INPUT': inputs[a[1].split('/')[0]].append(a[1])
def back(pin, cuts):
    todo=[pin]; seen=set(); frontier=set(); comb=set()
    while todo:
        p=todo.pop()
        if p in seen: continue
        seen.add(p)
        if p in cuts: frontier.add(p); continue
        if p not in pins: frontier.add(p); continue
        a=pins[p]; c=p.split('/')[0]
        if a[2]=='INPUT':
            ds=drivers[a[4]]
            if not ds: frontier.add('PORT:'+a[4])
            todo+=ds
        elif 'DFF' in cells[c] or cells[c].startswith('TIE'): frontier.add(p)
        else: comb.add(c); todo+=inputs[c]
    return dict(frontier=sorted(frontier), frontier_count=len(frontier), comb_cells=len(comb),
      frontier_master_counts=dict(collections.Counter(cells.get(p.split('/')[0],'CUT_OR_PORT') for p in sorted(frontier))))
frontiers=dict(first_to_c2168=back('c2168/Y',set()),second_to_c2343=back('c2343/Y',{'c2168/Y'}),third_to_capture=back('cpo216_ff/D',{'c2343/Y'}))
(HERE/'frontiers.json').write_text(json.dumps(frontiers,indent=2)+'\n')
L=2
plain=L*(216+517+535); reset=L*(1+1+2)
model=dict(verdict='ANALYTICAL_HOLD_NOT_SOURCE_READY', audit_commit='548178937', source_sha256='ac6af21580867b0e1224c7cf7e6476309d5b036cd2ba558ad5014737fbfeddde',
 graph_sha256=hashlib.sha256((SRC/'graph.tsv.gz').read_bytes()).hexdigest(),
 cuts=['c2168/Y','c2343/Y'], critical_path_segment_surrogates_ps=[515.38,816.26-515.38+101.06,1294.07-816.26+101.06],
 critical_path_segment_surrogates_are_closure=False,
 L=L, transport=dict(metadata_bits=216, q_bundle_bits=518, exported_prg_bits=537,
 transport_ff=plain+reset, plain_ff=plain, resettable_valid_ff=reset,
 transport_clock_pins=plain+reset, transport_area_floor_um2=plain*1.080*.270+reset*1.404*.270,
 extra_reset_copies=None, predicate_ff=None, combinational_area=None, total_ff=None,total_area=None,
 clock_capacitance=None, reset_capacitance=None, dynamic_power=None),
 schedule=dict(per_request_added_edges=L, per_request_added_ns=L/1.2,
 serial_token_added_edges='L * exact number of dependent ATTN admissions',
 scenario_32_admissions_added_edges=32*L, scenario_32_admissions_added_ns=32*L/1.2,
 scenario_257280_baseline_rate_loss_percent=100*(32*L)/(257280+32*L),
 scenario_4_users_added_work_edges=4*32*L, actual_mu_wall_delta=None,
 no_overlap_service_initiation_interval='old interval + L', actual_throughput=None),
 unresolved=['full source predicate cutset','old-state feedback ownership','all side-cone timing','ready snapshot versus live readiness',
 'continuous fault veto and exact fault observation contract','CAL_PIPE cohort and boot capability',
 'compiler actual request count and Q/result/TX/STATUS/health calendar','native FF and reset clockcap and driver copies',
 '521 unused inputs and 107 constant output ABI','PG contacts and clock matching'])
(HERE/'model.json').write_text(json.dumps(model,indent=2)+'\n')
print(json.dumps(dict(transport_ff=plain+reset,transport_area_floor_um2=model['transport']['transport_area_floor_um2'],segment_surrogates_ps=model['critical_path_segment_surrogates_ps'])))
