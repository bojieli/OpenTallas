"""Exact output/edge/address/status classification, distinct from wrapper status.

Readback latency 26+4*slice is a measured pilot observation, not native phase or
station result latency. No new stn_ages calibration is inferred from it.
"""
import hashlib,json,pathlib,re
import numpy as np
from replay import ROOT,W,SRC,SHA,sha
rows=[]
for nu in (1,4):
  for d in sorted((W/f'nu{nu}').iterdir()):
    layer=int(d.name[1]);mode=d.name.split('_')[1];mut='_'.join(d.name.split('_')[2:])
    out=(d/'bench.out').read_text();assert 'Traceback' not in out and 'RTL_EXEC_BEGIN' in out
    logs=list(d.glob('*.log'));events=list(d.glob('*.ev'))
    assert len(logs)==len(events)==1 and logs[0].stat().st_size and events[0].stat().st_size
    assert SHA[nu] in out and 'BENCH_RC' in out
    log={}
    for line in logs[0].read_text().splitlines():
      t,k,v=line.split();log.setdefault(k,[]).append((int(t),int(v,16)))
    low=json.loads((d/'lowering.json').read_text())
    with np.load(ROOT/f'fx_qk/L{layer}_mat_{mode}_tp8.npz') as z:g=z['gold_y'].astype(np.float32).view(np.uint32)
    address_gold={}
    for s,amap in low['expected_vm'].items():
      base=min(int(a) for a in amap)
      for addr,row in amap.items():
        for l in range(16):address_gold[(int(s)<<12)+int(addr)-base+l]=int(g[row+l])
    commands=[]
    for line in events[0].read_text().splitlines():
      t,p,v=line.split();v=int(v,16)
      if p=='0' and v&15==3 and (v>>4)&511==(501 if mode=='gu' else 500):commands.append((int(t),(v>>112)&15))
    expected_edges={}
    for t,s in commands:
      for j in range(32 if mode=='gu' else 16):expected_edges[(s,j)]=t+26+4*s+j
    seen={};edge_bad=[];bad=[];observations=[]
    for t,w in log.get('S0DD',[]):
      mask=(w>>537)&255;assert mask==255
      addr0=(w>>345)&0xffffff;s=addr0>>12;j=(addr0&4095)//8
      if expected_edges.get((s,j))!=t:edge_bad.append(dict(edge=t,expected=expected_edges.get((s,j)),slice=s,packet=j))
      for lane in range(8):
        a=(w>>(345+24*lane))&0xffffff;v=(w>>(89+32*lane))&0xffffffff
        assert a not in seen, ('duplicate output address',a)
        seen[a]=v
        observations.append(dict(edge=t,address=a,observed=hex(v),expected=hex(address_gold[a]) if a in address_gold else None,equal=address_gold.get(a)==v))
        if address_gold.get(a)!=v:bad.append(dict(address=a,got=hex(v),expected=hex(address_gold[a]) if a in address_gold else None))
    missing=sorted(set(address_gold)-set(seen));extra=sorted(set(seen)-set(address_gold))
    (d/'word_address_comparisons.json').write_text(json.dumps(observations,indent=1)+'\n')
    schedule=[]
    for line in events[0].read_text().splitlines():
      t,p,v=line.split();schedule.append((int(t),int(p),int(v,16)))
    stn=[t for t,p,v in schedule if p==0 and v&15==5]
    rs=[t for t,p,v in schedule if 2<=p<=25 and v]
    setup=[t for t,p,v in schedule if p==41]
    breakdown=dict(actual_command_entry_first=min(stn),actual_command_entry_last=max(stn),
      actual_cluster_input_first=min(rs),actual_cluster_input_last=max(rs),
      readback_command_entry_first=min(t for t,s in commands),readback_command_entry_last=max(t for t,s in commands),
      actual_readback_output_first=log['S0DD'][0][0],actual_readback_output_last=log['S0DD'][-1][0],
      stream_table_setup_first=min(setup),stream_table_setup_last=max(setup),stream_table_setup_events=len(setup),
      actual_command_to_last_station_result_span=None,
      actual_station_result_visibility='internal VM write not logged in existing fixed binary',
      actual_command_to_last_readback_output_span=log['S0DD'][-1][0]-min(stn),
      operation_latency_qualified=False)
    (d/'schedule_breakdown.json').write_text(json.dumps(breakdown,indent=2)+'\n')
    statuses={k:hex(v[0][1]) for k,v in log.items() if k.endswith('ST')}
    faults={k:(v[0][1]>>63)&127 for k,v in log.items() if k.endswith('ST')}
    aggregate=log['S0AG'][0][1];busy=(aggregate>>9)&1
    positive=mut=='positive'
    if positive:
      assert ' PASS ' in out and 'BENCH_RC 0' in out
      assert not (bad or missing or extra or edge_bad or any(faults.values()) or aggregate),d
      assert len(seen)==len(g)
    else:
      assert ' FAIL ' in out and 'BENCH_RC 1' in out,d
      assert bad or missing or extra or edge_bad or any(faults.values()) or busy,d
      if mut=='nearshift':assert any(faults.values()),d
      if mut=='kc2':assert busy or missing,d
      if mut in ('sbase1','predrain','scale_before_tree'):assert bad,d
    rows.append(dict(nu=nu,layer=layer,mode=mode,mutant=mut,verdict='PASS' if positive else 'CAUSAL_FAIL',
      fixture_words=len(g),observed_words=len(seen),equal_words=len(seen)-len(bad),data_mismatch_count=len(bad),
      first_mismatches=bad[:12],missing_addresses=missing[:20],extra_addresses=extra[:20],
      edge_checks=len(log.get('S0DD',[])),edge_mismatches=edge_bad[:20],
      readback_edge_basis='measured pilot command entry +26+4*slice+packet; not native station phase',
      schedule_breakdown=breakdown,
      faults=faults,aggregate=hex(aggregate),stn_busy=busy,terminal_status=statuses,
      first_output_edge=log['S0DD'][0][0],last_output_edge=log['S0DD'][-1][0],
      raw_log_sha256=sha(logs[0]),event_sha256=sha(events[0]),resources=json.loads((d/'resources.json').read_text())))
assert len(rows)==18,len(rows)
pairs=[]
for a in [r for r in rows if r['nu']==1]:
  b=next(r for r in rows if r['nu']==4 and all(r[k]==a[k] for k in ('layer','mode','mutant')))
  assert a['raw_log_sha256']==b['raw_log_sha256'] and a['event_sha256']==b['event_sha256'],(a,b)
  pairs.append({k:a[k] for k in ('layer','mode','mutant','raw_log_sha256','event_sha256')})
(W/'classification.json').write_text(json.dumps(dict(cases=rows,complete_trace_pairs=pairs,
  positive_isa_words=sum(r['fixture_words'] for r in rows if r['mutant']=='positive')) ,indent=2)+'\n')
print('CLASSIFICATION_PASS',len(rows),'cases',len(pairs),'complete NU1/NU4 pairs')
