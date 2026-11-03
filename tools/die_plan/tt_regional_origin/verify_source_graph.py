#!/usr/bin/env python3
"""Independent local structural checks on a native elaborated TT regional wrapper.

Unchanged core/receiver interfaces are native library black boxes. The origin and
one-bit raw relay are real process-lowered source. This does not prove those
black-box functions, map physical clocks, or replace global G0C/LEC/KEEP checks.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path


def verify(graph,model):
    modules=graph['modules'];top=modules['qfd_qc_tt_ctlm_part_bound'];cells=top['cells']
    def equal(actual,expected,what):
        if actual!=expected:raise ValueError(what)
    clk=top['ports']['clk']['bits']
    origin=cells['u_cland_origin'];h=modules[origin['type']];op=origin['connections']
    params=h['parameter_default_values']
    equal([int(params[k],2) for k in ('ENABLE','PADW','REGIONS')],[1,1,4],'Actual origin specialization differs')
    equal(op['clk'],clk,'Origin clock changed')
    equal(op['p_start'],top['ports']['cland_tstart_in']['bits'],'External START sampling input changed')
    parent=cells['u_rrl_85']['connections']['q'];central=cells['u_rrl_87']['connections']
    equal(central['clk'],clk,'Central raw clock changed');equal(central['d'],parent,'Central raw parent changed')
    equal(op['rst_raw_n'],central['q'],'Retained SF/S0 raw leaf changed')
    raw_module=modules['ot_dp_rrelay'];raw_cells=list(raw_module['cells'].values())
    if len(raw_cells)!=1 or raw_cells[0]['type']!='$dff':raise ValueError('Raw copy is not the actual one-bit DFF mechanism')
    raw_cell=raw_cells[0]
    equal(int(raw_cell['parameters']['WIDTH'],2),1,'Raw width changed')
    equal(int(raw_cell['parameters']['CLK_POLARITY'],2),1,'Raw edge changed')
    for p,q in [('CLK','clk'),('D','d'),('Q','q')]:equal(raw_cell['connections'][p],raw_module['ports'][q]['bits'],'Raw relay mechanism changed at '+p)
    raw=[]
    for r in range(4):
        name=f'g_tt_raw_regions.g_region[{r}].u_raw_copy';c=cells[name]
        equal(c['type'],'ot_dp_rrelay','Unqualified raw copy type')
        equal(c['connections']['d'],parent,'Regional raw copy changed parent')
        equal(c['connections']['clk'],clk,'Regional raw copy clock changed')
        raw+=c['connections']['q']
    equal(op['rst_region_raw_n'],raw,'Regional raw order changed')
    if len(set(raw))!=4:raise ValueError('Regional raw state copies were merged')
    if any(c['type'] not in ('$dff','$mux','$shiftx','$logic_not') for c in h['cells'].values()):
        raise ValueError('Unclassified helper logic/state outside the actual proved source mechanism')
    flops=[(n,c) for n,c in h['cells'].items() if c['type']=='$dff']
    equal(len(flops),14,'Regional origin FF count differs')
    expected_signals={'g_on.sf':0,'g_on.s0':1}
    for r in range(4):
        for st in ('s1','s2','pd'):expected_signals[f'g_on.g_region[{r}].{st}']=1
    source_states=[];state_bits=set();state_cells=set()
    for name,polarity in expected_signals.items():
        bits=h['netnames'][name]['bits'];found=[(n,c) for n,c in flops if c['connections']['Q']==bits]
        if len(found)!=1:raise ValueError('Missing or merged actual source state '+name)
        n,c=found[0]
        if tuple(bits) in state_bits or n in state_cells:raise ValueError('Source state aliases another declared FF')
        state_bits.add(tuple(bits));state_cells.add(n)
        equal(int(c['parameters']['WIDTH'],2),1,'Source width changed: '+name)
        equal(int(c['parameters']['CLK_POLARITY'],2),polarity,'Source edge changed: '+name)
        equal(c['connections']['CLK'],h['ports']['clk']['bits'],'Source root clock changed: '+name)
        source_states.append(dict(rtl_signal='u_bound.u_cland_origin.'+name,actual_native_process_ff=n,edge='posedge' if polarity else 'negedge'))
    expected_start=collections.defaultdict(set);expected_d=collections.defaultdict(set);expected_raw=collections.defaultdict(set);receivers=[]
    for region in model['qualified_regions']:
        r=region['region']
        for full in region['receivers']:
            name=full.removeprefix('u_bound.');c=cells[name];p=c['connections']
            equal(p['clk'],clk,'Receiver clock changed: '+name)
            if c['type']=='ot_dp_clk_landing_cas':
                equal(p['rst_n'],[op['start_r'][r]],'Reader regional START changed: '+name)
                bus=name.removeprefix('u_cland_')
                equal(p['fclk'],top['ports']['fclk_in_'+bus]['bits'],'Reader forwarded clock changed: '+name)
                equal(p['t_rst_n'],top['ports']['cland_fstart_in_'+bus]['bits'],'Reader sender START contract changed: '+name)
                equal(p['d'],top['ports'][bus]['bits'],'Reader input payload/epoch changed: '+name)
                expected_start[r].add((name,'rst_n'))
            elif c['type']=='ot_dp_landing_relay':
                equal(p['d'],[op['start_d_r'][r]],'Forwarded regional D changed: '+name)
                equal(p['rst_raw_n'],[raw[r]],'Forwarded regional raw reset changed: '+name)
                expected_d[r].add((name,'d'));expected_raw[r].add((name,'rst_raw_n'))
            else:raise ValueError('Unsupported regional receiver type '+c['type'])
            receivers.append(dict(instance=name,type=c['type'],region=r))
    equal(len(receivers),37,'Missing exact receiver coverage')
    def fanout(bit):
        return {(n,p) for n,c in cells.items() for p,bits in c['connections'].items()
                if c.get('port_directions',{}).get(p)=='input' and bit in bits}
    for r in range(4):
        equal(fanout(op['start_r'][r]),expected_start[r],'Unpriced regional START consumers')
        equal(fanout(op['start_d_r'][r]),expected_d[r],'Unpriced regional D consumers')
        equal(fanout(raw[r]),expected_raw[r]|{('u_cland_origin','rst_region_raw_n')},'Unpriced regional raw consumers')
    return dict(schema='opentallas.tt_native_regional_source_structure.v1',status='PASS_LOCAL_NATIVE_STRUCTURE',
                physical_qualified=False,whole_part_lec_credit=False,global_g0c_credit=False,
                origin_ff=14,origin_posedge_ff=13,origin_negedge_ff=1,old_origin_ff=5,
                extra_raw_leaves=4,net_ff_added=13,cycles_added=0,receivers=receivers,actual_source_states=source_states,
                checked=['actual selected core/receiver interface elaboration','all37receiver clock/START/D/raw joins and exact output consumer sets','reader external forwardedclock/START/payload unchanged','four distinct one-bit sameD/sameCLK raw copies from actual85; central87 retained','all14real origin sourceFF identities/widths/edges'],
                unproved=['unchanged blackbox core/receiver functions','whole-part nativeLEC145','global reset/count/source/landslots verifier integration','mapped KEEP/ABI and physical clock-name/phase/path assignment','native placement/row legality and all parent/corner gates'])


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('graph','model','out'):ap.add_argument('--'+k,type=Path,required=True)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--proved-helper',type=Path,required=True)
    a=ap.parse_args()
    if not a.source.read_bytes().endswith(a.proved_helper.read_bytes()):
        raise ValueError('Actual native source helper differs from the proved helper')
    r=verify(json.loads(a.graph.read_text()),json.loads(a.model.read_text()))
    r['proved_helper_sha256']=hashlib.sha256(a.proved_helper.read_bytes()).hexdigest()
    r['actual_native_source_sha256']=hashlib.sha256(a.source.read_bytes()).hexdigest()
    r['graph_sha256']=hashlib.sha256(a.graph.read_bytes()).hexdigest();r['model_sha256']=hashlib.sha256(a.model.read_bytes()).hexdigest()
    a.out.write_text(json.dumps(r,indent=1)+'\n');print('TT_NATIVE_SOURCE_GRAPH',r['status'],'receivers',len(r['receivers']),'netFF',r['net_ff_added'])
