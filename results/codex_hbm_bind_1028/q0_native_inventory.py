"""Inventory the actual two COL/ring mothers and GQ sources; never delete slots.
Usage: q0_native_inventory.py TOP HUB_GRAPH ELAB_SOURCES PLAN SOURCE_ROOT OUT
"""
from pathlib import Path
import hashlib,json,re,sys
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools/hbm_b2'));sys.path.insert(0,str(root/'tools/die_plan'))
from b2_top import Die,parse_expr
from bind_elab import module_body
top,graph,sources,plan,srcroot,out=map(Path,sys.argv[1:])
d=Die(top,{})
g=json.loads(graph.read_text());p=json.loads(plan.read_text());selected=json.loads(sources.read_text())
def local_source(path):
    text=str(path)
    marker=next(m for m in ('/physical/','/rtl/','/results/') if m in text)
    return srcroot/(marker.lstrip('/')+text.split(marker,1)[1])
records=[]
for side,qid in [('NW',2),('NE',3)]:
    mother='hb_coll_'+side;mc=d.insts[mother]
    actual=next(c['module'] for c in g['cells'] if c['path']==mother)
    expected='ot_hfd_coll_q_hard_v8g_body' + ('_s' if side=='NE' else '')
    fs=[local_source(f) for f in selected['lib'] if module_body(local_source(f),actual)]
    assert len(fs)==1,(mother,fs)
    body=module_body(fs[0],actual)
    assert len(re.findall(r'\b'+re.escape(expected)+r'\s*#',body))==1,(mother,fs[0],expected,body[-250:])
    inner=module_body(fs[0],expected)
    assert len(re.findall(r'\bot_hgi_coll_ring_ag\s*#\([^;]*?\)\s+u_ring\s*\(',inner,re.S))==1
    assert parse_expr(mc['conns']['qid'],d.widths)==[('c',2,qid)]
    issue='hcollgi_'+side;ic=d.insts[issue]
    assert ic['master']=='ot_hgi_coll_gq_issue'
    assert mc['conns']['ra_lp_data']==issue+'__ra_lp_data[255:0]'
    row=next(c for c in g['cells'] if c['path']==issue)
    assert row['plan_instance']=='u_hcollgi_Q__q1'
    forbidden={'u_hcollgi_Q__q0','u_hb_coll_Q_ring_ag__q0'}
    q0=[c for c in g['cells'] if c['partition']==side+'_hub' and c['plan_instance'] in forbidden]
    assert not q0
    assert not any(name.startswith('hcollgi_'+s) for name in d.insts for s in ('SW','SE'))
    records.append(dict(hub=side+'_hub',mother=mother,module=actual,raw_module=mc['master'],native_qid=qid,
                        body_module=expected,ring_path=mother+'.u_body.u_ring',ring_instances=1,
                        selected_source=str(fs[0]),source_sha256=hashlib.sha256(fs[0].read_bytes()).hexdigest(),
                        gq_issue=issue,gq_plan_instance=row['plan_instance'],
                        actual_ring_lp_data=mc['conns']['ra_lp_data'],q0_mapped_native_cells=q0,
                        q0_named_producer_or_consumer_count=0))
rec=dict(schema='opentallas.hbm.q0_native_inventory.v1',source=str(top),
         source_sha256=hashlib.sha256(top.read_bytes()).hexdigest(),hubs=records,
         actual_ring_instances=2,actual_gq_issue_instances=2,
         status='SOURCE_UNREALIZED_Q0_SLOTS_NO_PLAN_MUTATION',
         limitations=['The current unsplit COL mothers still need exact physical cut bindings.',
                      'Parent must preserve unrelated FT stations/clock/reset and recalculate plan gates before freeing lots.',
                      'No equivalence, timing or deletion approval is inferred from this source occurrence inventory.'])
out.write_text(json.dumps(rec,indent=2)+'\n');print('native COL ring 2 / GQ issue 2; q0 mapped producer-consumer occurrence 0; no slots deleted')
