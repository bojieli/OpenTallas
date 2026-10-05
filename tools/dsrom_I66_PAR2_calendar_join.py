#!/usr/bin/env python3
"""Join observed native I66 events to the common PAR2 site/root ownership.
Whole-product calendar insertion point, not a physical or fullscheduler proof.
"""
import argparse,collections,gzip,hashlib,json
from pathlib import Path
import dsrom_I66_standalone_calibration as S
OUT=S.ROOT/'results/uarch/dsrom_I66_PAR2_calendar_join_20261002'

def site_owner(site):
    if not 0<=site<4096:raise ValueError('global site outside compiled field')
    return dict(shard=site//2048,local_site=site%2048)

def root_owner(root):
    if not 0<=root<128:raise ValueError('root outside native field')
    return dict(shard=root//64,local_root=root%64)

def build(events,node,phase):
    identity=dict(stage=0,rank=0,phase=10,key_word=2149580800,reset_era=0)
    for x in events:
        if any(x[k]!=v for k,v in identity.items()):raise ValueError('wrong phase/era/owner')
    case=S.load(S.A/'prediction_r2/prediction.json')['case']
    assert node['node']==case['node']=='L0.I66' and node['address_bound']
    selected=next(x for x in node['phase_choices'] if x['expert']==case['EID'])
    assert selected['phase']==10 and selected['source_key_word']==identity['key_word']
    assert phase['phase_binding']['phase']==selected['phase']
    matrix=phase['matrix'];plans=matrix['plans']
    active={p[1] for p in plans};row_home={}
    cfg_source=(OUT/'inputs/phase_cfg_source.py.txt').read_text()
    assert 'cfg[slot]=(2*row|' in cfg_source
    assert 'cfg[17+slot]=2*row+1 if 2*row+1<m[\'rows\'] else 0x8000' in cfg_source
    for seg,g,first,n,stride,start,w in plans:
        assert seg==0 and matrix['segments']==[[0,5120]]
        for i in range(n):
            superrow=first+i*stride
            # Original host return tree has 8192 leaves and six binary levels.
            root=(2*g)>>6
            assert site_owner(g)['shard']==root_owner(root)['shard']
            for row in [2*superrow,2*superrow+1]:
                if row>=matrix['rows']:continue
                assert row not in row_home,'multiple ownership/reassociated K grain'
                row_home[row]=root
    assert set(row_home)==set(range(576))
    per=collections.defaultdict(lambda:collections.Counter())
    cadence=collections.defaultdict(collections.Counter)
    edges=collections.defaultdict(list);roots={};writes={};visible={};cross_K=0
    pair_kinds={'cfg_ROM_read_accept','cfg_element_write_accept','main_CE_accept','macro_read_accept','bank_capture','lane_consumer_sample','active_pair_go_accept','pair_partial'}
    for e in events:
        k=e['kind'];edges[k].append(e['edge'])
        if k in pair_kinds:
            own=site_owner(e['a']);per[own['shard']][k]+=1;cadence[(own['shard'],k)][e['edge']]+=1
            if k=='main_CE_accept' and e['a'] not in active:raise ValueError('CE at nonowned site')
            if k=='pair_partial':
                row=(e['c']>>13)&65535
                if row_home[row]!=(2*e['a'])>>6:raise ValueError('partial routed outside original tree')
        elif k=='root_row_accept':
            row=e['b'];root=e['a']
            if root!=row_home[row] or row in roots:raise ValueError('root owner/duplicate')
            roots[row]=e;per[root_owner(root)['shard']][k]+=1;cadence[(root_owner(root)['shard'],k)][e['edge']]+=1
        elif k=='VM_write_accept':
            row=e['b']-398720
            if row in writes or e['a']!=row_home[row]:raise ValueError('writer identity')
            writes[row]=e;per[root_owner(e['a'])['shard']][k]+=1;cadence[(root_owner(e['a'])['shard'],k)][e['edge']]+=1
        elif k=='final_destination_visible':
            row=e['a']-398720
            if row in visible:raise ValueError('duplicate visibility')
            visible[row]=e
    assert set(roots)==set(writes)==set(visible)==set(range(576))
    for row in roots:
        assert writes[row]['edge']==roots[row]['edge']+1
        assert visible[row]['edge']==writes[row]['edge']
        assert roots[row]['c']==writes[row]['c']==visible[row]['c']==0x45a00000
    assert [edges[k][0] for k in ['op_accept','phase_accept','spine_idle','phase_retire']]==[10,15,421,422]
    assert max(edges['root_row_accept'])==419 and max(edges['VM_write_accept'])==420
    return dict(schema='opentallas.dsrom.I66.PAR2.observed-ownership-calendar.v1',candidate='DS4096-TP4-S58-PAR2-NP2048',identity=identity,selected_node='L0.I66',selected_expert=0,compiled=dict(logical_sites=4096,shards=2,sites_per_shard=2048,roots=128,roots_per_shard=64,NBF=724,PHW=10,BST=17),phase_coverage='one actual I66 expert0/rank0/position1 consumer cone; not other1148calls or fulltoken',runtime=dict(overall='PASS',native_op_origin=10,last_root=419,last_VM_visibility=420,spine_idle=421,adapter_idle=422,observed_stable_debt_drain=462,drain462_is_not_kernel_latency=True),per_source_shard={str(k):dict(v) for k,v in sorted(per.items())},per_shard_accepted_cadence={f'{shard}:{kind}':dict(peak_transactions_per_native_edge=max(v.values()),edge_counts={str(t):c for t,c in sorted(v.items())}) for (shard,kind),v in sorted(cadence.items())},configuration_native_read_rate_bits_per_edge_per_shard=2048*48,native_event_edges={k:dict(count=len(v),first=min(v),last=max(v)) for k,v in sorted(edges.items())},ordered_K_grain=dict(segments=matrix['segments'],rows=576,rows_owned_once=True,paired_leaf_to_root_shard_crossings=cross_K,rule='root=(2*global_pair)>>6; original binary reductions retained; no inter-shard K reassociation'),physical_deadlines=dict(last_cfg_capture_to_field_GO_edges=1,CE_to_bank_capture_edges=2,bank_capture_to_lane_edges=1,root_to_VM_visible_edges=1,source_idle_to_adapter_idle_edges=1),boundary_widths=dict(cfg_word_bits=48,cfg_words_per_pair=25,FP4_activation_payload_bits=548,FP4_activation_valid_bits=1,root_wire_bits_per_port=69,writer_wire_bits_per_port=63,VM_address_bits=19,AW=30),ownership_contract=dict(configuration='both2048-site shards load25words per pair inclinactive/padded sites; no active-only credit',activation='one native64FP32read/AQ stream broadcast to both shards; physical broadcast transport must be priced',root='source roots0..63 shard0 and64..127 shard1; root arrivals need real delivery to common logical VM sink',VM_sink_physical_home=None,provider_clock_or_wire_delay=None,fullprogram_I66_origin=None,coll_busy_release=None),physical_admission=False,fullscheduler_admission=False,no_loss_proof=False,unbound=['physical cfgROM/clock delivery','activation broadcast wire/crossing','root gather to physical destination/write visibility','whole-program scheduler/I66 origin and coll_busy release','otherexperts/positions/fulltoken'],ECC_roles_removed=True,new_global_capture_pool_bits=0,new_ACK_protocol=False)

def insert_at(model,accepted_op_edge):
    """Conditional placement at an actually known whole-program native op edge.
    Caller must provide a same-domain accepted origin, not an offered timestamp.
    This places the measured CONE trace; unbound physical costs remain None.
    """
    shift=accepted_op_edge-model['runtime']['native_op_origin']
    return dict(source_domain='native simulation clk/gclk edges',accepted_op_edge=accepted_op_edge,conditional_native_edges={k:model['runtime'][k]+shift for k in ['last_root','last_VM_visibility','spine_idle','adapter_idle']},physical_cfg_activation_root_added_edges=None,coll_busy_release=None,fullscheduler_or_provider_admission=False)

def generate(out):
    inputs=OUT/'inputs';node=S.load(inputs/'I66_node_binding.json');phase=S.load(inputs/'I66_phase_ownership.json')
    S.verify();model=build(S.events('r2_PASS'),node,phase)
    model['input_sha256']={str(p.relative_to(S.ROOT)):S.sha(p) for p in sorted(inputs.iterdir()) if p.is_file()}
    model['runtime_record_sha256']=S.sha(S.A/'r2_PASS/record.json')
    model['runtime_journal_raw_sha256']=S.sha_raw(S.A/'r2_PASS/actual.jsonl.gz')
    out.write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
    return model

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.out)
