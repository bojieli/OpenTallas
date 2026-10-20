#!/usr/bin/env python3
"""Bind VM error flags into each quadrant fault root; preserve existing synchronisers.

vmstat[18]=hub protocol/address/ack or bank protocol fault, [17]=hub mask
fault, [16]=bank uncorrectable ECC. Lower16 corrected-error count is unchanged.
Static host ingress has no vmstat input: only the registered fault tree reaches
host_status.die_fault -> host_cp_rxs.fault and block_ready -> ingress admission.
Successful execution gains zero cycles. Error visibility follows existing stream
status pipeline, two-edge leaf and three-edge host join, plus planned die relays.
"""
import argparse,copy,gzip,json
from pathlib import Path

QS=('SW','SE','NW','NE')

def load(path):
    return json.load(gzip.open(path,'rt') if str(path).endswith('.gz') else open(path))

def apply(contract):
    c=copy.deepcopy(contract);I=c['instances'];E=c['edges'];changes=[]
    def clock(instance):
        # Unfolded SE/NE glue clocks its status producer on clk_hub. Folded tiles expose clk.
        port='clk' if 'clk' in I[instance]['ports'] else 'clk_hub'
        matches=[x['source'] for x in c['clock_resets'] if x['instance']==instance and x['port']==port]
        if len(matches)!=1:raise ValueError('missing/ambiguous primary clock '+instance)
        return matches[0]
    for q in QS:
        src='hb_vms_'+q;dst='fr_'+q;v=I[src];f=I[dst]
        assert v['ports']['vmstat']==dict(direction='output',bits=19)
        assert f['master']=='ot_hbm_fault_leaf'
        if clock(src)!=clock(dst):raise ValueError('VM flags need explicit CDC design: '+q)
        old_n=f['params']['N'];mask=f['params']['SYNC_MASK'];edge_name='l16_vm_fault_'+q
        prior=[e for e in E if e['name']==edge_name]
        if prior:
            assert len(prior)==1 and prior[0]['source']==[src,'vmstat',16,19]
            assert prior[0]['sink']==[dst,'in',old_n-3,old_n]
            changes.append(dict(quadrant=q,already_bound=True,new_n=old_n,sync_mask=mask));continue
        assert 0<old_n<=61 and f['ports']['in']['bits']==old_n
        incoming=[e for e in E if e['sink'][:2]==[dst,'in']]
        used={b for e in incoming for b in range(e['sink'][2],e['sink'][3])}
        assert used==set(range(old_n)), (dst,'preexisting input not fully bound')
        f['params']['N']=old_n+3;f['ports']['in']['bits']=old_n+3
        # Append high bits: existing SYNC_MASK and existing source->sink offsets unchanged.
        assert f['params']['SYNC_MASK']==mask
        f['note']=(f.get('note') or '')+' | l16_vm_fault: stream VM fatal flags[18:16] appended, old SYNC_MASK preserved'
        E.append(dict(name=edge_name,bits=3,source=[src,'vmstat',16,19],sink=[dst,'in',old_n,old_n+3],
            clock='stream',ready_or_credit=False,allowed_exception=None,region='l16_vm_fault',
            basis='VM protocol/mask/bank uncorrectable-ECC flags must reach host fault tree; CE count remains separate'))
        changes.append(dict(quadrant=q,old_n=old_n,new_n=old_n+3,sync_mask=mask,clock=clock(src),
            source=[src,'vmstat',16,19],sink=[dst,'in',old_n,old_n+3]))
    host_fault=[e for e in E if e['source'][:2]==['host_status','die_fault']]
    admission=[e for e in E if e['source'][:2]==['host_status','block_ready']]
    assert any(e['sink'][:2]==['host_cp_rxs','fault'] for e in host_fault)
    assert any(e['sink'][:2]==['host_cp_ingress','block_ready'] for e in admission)
    for q in QS:
        assert any(e['source'][:2]==['fr_'+q,'fault'] and e['sink'][:2]==['host_status','a_fault'] for e in E)
    if 'summary' in c:
        c['summary']['edges']=len(E);c['summary']['edge_bits']=sum(e['bits'] for e in E)
    c.setdefault('notes',[]).append('L16: VM fatal flags[18:16] enter regional fault roots; static host has no vmstat input. No execution latency change.')
    return c,dict(layer='l16_vm_fault',changes=changes,clock_domain='same primary stream clock, no extra sync',
        old_sync_masks_preserved=True,successful_execution_added_cycles=0,
        error_visibility='VM status pipeline +2 leaf edges +3 host-join edges + planned die relays',
        host_fault_edges=host_fault,host_admission_edges=admission,
        physical_obligation='fr parameter variants N14/N13 require source-bound synthesis/physical qualification before binding old hard views')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('inp');ap.add_argument('out');ap.add_argument('--report',required=True);a=ap.parse_args()
    c,r=apply(load(a.inp));Path(a.report).write_text(json.dumps(r,indent=1)+'\n')
    if a.out.endswith('.gz'):
        with gzip.open(a.out,'wt') as f:json.dump(c,f)
    else:Path(a.out).write_text(json.dumps(c)+'\n')
    print('L16_OK',len(r['changes']),'quadrants; VM fatal flags connected; old synchronisers preserved')

if __name__=='__main__':main()
