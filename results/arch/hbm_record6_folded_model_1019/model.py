#!/usr/bin/env python3
"""Small integer/symbolic schedule. MODEL, not RTL or FP32 qualification."""
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
INV = json.loads((HERE/'inventory_exact.json').read_text())
MUTANT = os.environ.get('R6_MODEL_MUTANT','')

def digest(x):
    return hashlib.sha256(repr(x).encode()).hexdigest()

def chunk(c, swap=False):
    words = [('square', 8*c+k) for k in range(8)]
    if swap:
        words[1], words[2] = words[2], words[1]
    # canonical zero first operand; actual squaring finite/nonnegative fixture.
    acc = ('canonical_zero', words[0])
    for w in words[1:]:
        acc = ('add', acc, w)
    return acc

def tree(base, size):
    if size == 1:
        return chunk(base) if base < 160 else ('zero_chunk', base)
    return ('add', tree(base, size//2), tree(base+size//2, size//2))

def blocks(lo, hi):
    out=[]
    while lo < hi:
        n=1
        while lo % (2*n) == 0 and lo+2*n <= hi:
            n*=2
        out.append((lo,n)); lo+=n
    return out

def schedule(nl, period, lane_age=29, global_adders=1):
    ops=[]; fragments={}; stations={}; emits=[]
    def add(name, a, b, resource, earliest, available):
        t=max(earliest,a[0],b[0],available.get(resource,0))
        if MUTANT=='early_feedback': t-=1
        assert t>=max(earliest,a[0],b[0],available.get(resource,0)), 'EARLY_FEEDBACK'
        # Conservative non-overlap reservation: even independent operations
        # occupy the entire recurrence interval, not pipeline issue-rate one.
        available[resource]=t+nl
        expr=('add',a[1],b[1])
        ops.append(dict(name=name, resource=resource, start=t, done=t+nl,
                        result=digest(expr),
                        operands=[digest(a[1]),digest(b[1])]))
        return (t+nl,expr)
    for g in range(4):
        emit=32+period*g; cap=emit+lane_age+1
        emits.append(dict(group=g,emit=emit,first_capture=cap))
        avail={}
        for q in range(4):
            row=next(x for x in INV['groups'] if x['group']==g and x['quarter']==q)
            base=(row['roles']['A']['first']-46336)//8
            count=16 if q in (0,2) else 4
            leaves={}
            for k in range(count):
                c=base+k; r=f'q{q}.station{k}'
                acc=(cap,('canonical_zero',('square',8*c)))
                for j in range(1,8):
                    src=3-j if MUTANT=='word_order' and c==0 and j in (1,2) else j
                    acc=add(f'g{g}.chunk{c}.word{j}',acc,
                        (cap,('square',8*c+src)),r,cap,avail)
                leaves[(c,1)]=acc
            for b,n in blocks(base,base+count):
                def fold(b,n):
                    if n==1: return leaves[(b,1)]
                    a=fold(b,n//2); z=fold(b+n//2,n//2)
                    if MUTANT=='join_pairing' and b==0 and n==2: a,z=z,a
                    # Same physical left-most station reused after its chunk.
                    return add(f'g{g}.q{q}.subtree{b}:{b+n}',a,z,
                               f'q{q}.station{b-base}',cap,avail)
                result=fold(b,n)
                assert result[1] == tree(b,n), 'ORDERED_CANONICAL_FRAGMENT'
                fragments[(b,n)]=(result[0]+1,result[1]) # registered export
            stations[(g,q)]=dict(count=count,last=max(avail.values()))
        assert max(avail.values())+1 <= 32+period*(g+1)+lane_age+1
    assert len(fragments)==26
    # Immutable canonical padding subtrees. No live operand replaced by zero.
    fragments[(160,32)]=(0,tree(160,32))
    fragments[(192,64)]=(0,tree(192,64))
    pending=dict(fragments); global_available={}; global_count=0
    while (0,256) not in pending:
        candidates=[]
        for (b,n),a in pending.items():
            if b%(2*n)==0 and (b+n,n) in pending:
                z=pending[(b+n,n)]
                candidates.append((max(a[0],z[0]),n,b))
        assert candidates
        ready,n,b=min(candidates)
        a=pending.pop((b,n)); z=pending.pop((b+n,n))
        resource=min((f'global{i}' for i in range(global_adders)),
                     key=lambda r:(global_available.get(r,0),r))
        result=add(f'global{b}:{b+2*n}',a,z,resource,ready,global_available)
        pending[(b,2*n)]=result; global_count+=1
    root=pending[(0,256)]
    assert root[1] == tree(0,256) and global_count==27
    # Every resource is exclusive through its reserved interval.
    for r in {o['resource'] for o in ops}:
        rows=sorted((o['start'],o['done']) for o in ops if o['resource']==r)
        assert all(a[1]<=b[0] for a,b in zip(rows,rows[1:]))
    # One real held result per local station is sufficient: no result may be
    # overwritten before its local parent's two-stage selector starts.
    producers={o['result']:o for o in ops}
    lifetime_checks=0
    for op in ops:
        if op['resource'].startswith('global'): continue # fixed export entries
        for operand in op['operands']:
            if operand not in producers: continue # actual captured input word
            src=producers[operand]
            assert src['done']<=op['start']
            assert not any(x['resource']==src['resource'] and
                src['done']<x['done']<=op['start'] for x in ops), 'OVERWRITTEN_LOCAL_CHILD'
            lifetime_checks+=1
    # 1120 chunk additions; 134 local fragment-tree adds; 27 global joins.
    assert sum('.word' in o['name'] for o in ops)==1120
    assert len(ops)==1281
    # Index range, group and exact ordered expression assertions are the oracle.
    assert len({w for c in range(160) for w in range(8*c,8*c+8)})==1280
    assert chunk(0,swap=True)!=chunk(0)
    assert ('add',tree(0,128),tree(128,128))==root[1]
    assert ('add',tree(128,128),tree(0,128))!=root[1]
    assert tree(0,128)!=root[1] # omitted second half is rejected
    scalar_vm=root[0]+1+22+32+2+2+20
    return dict(nl=nl,group_period=period,global_adders=global_adders,lane_age_illustration=lane_age,
        groups=emits,stations=[dict(group=g,quarter=q,**v) for (g,q),v in stations.items()],
        fragment_count=26,local_additions=134,global_additions=27,
        held_local_result_lifetime_checks=lifetime_checks,
        total_additions=len(ops),root_serial=root[0],
        R_native_done_serial_illustration=scalar_vm,
        R_native_done_stream_illustration=scalar_vm*4/3,
        extra_stream_over_original182_18=scalar_vm*4/3-182.18,
        whole_expression_sha256=digest(root[1]),operations=ops)

def four_adder_schedule(nl=9, period=112, lane_age=29):
    """Four total adders; genuine four 8-word operand stations, 64 emits.

    All global joins deliberately wait for local arithmetic to finish, then
    reuse q0's adder. This is a legal conservative calendar, not an optimum.
    """
    avail={f'q{q}':0 for q in range(4)}; fragments={}; ops=[]; emits=[]
    def add(a,b,r,name):
        t=max(a[0],b[0],avail[r]); avail[r]=t+nl
        ops.append(dict(name=name,resource=r,start=t,done=t+nl))
        return (t+nl,('add',a[1],b[1]))
    for g in range(4):
        for q in range(4):
            row=next(x for x in INV['groups'] if x['group']==g and x['quarter']==q)
            base=(row['roles']['A']['first']-46336)//8
            count=16 if q in (0,2) else 4
            for b,n in blocks(base,base+count):
                stack=[]
                for c in range(b,b+n):
                    k=c-base; emit=32+(16*g+k)*period; cap=emit+lane_age+1
                    emits.append(dict(group=g,quarter=q,chunk=c,emit=emit))
                    assert avail[f'q{q}']<=cap
                    acc=(cap,('canonical_zero',('square',8*c)))
                    for j in range(1,8):
                        acc=add(acc,(cap,('square',8*c+j)),f'q{q}',f'chunk{c}.word{j}')
                    entry=(c,1,acc)
                    while stack and stack[-1][1]==entry[1]:
                        left=stack.pop(); assert left[0]+left[1]==entry[0]
                        acc=add(left[2],entry[2],f'q{q}',f'local{left[0]}:{entry[0]+entry[1]}')
                        entry=(left[0],2*entry[1],acc)
                    stack.append(entry)
                assert len(stack)==1 and stack[0][:2]==(b,n)
                fragments[(b,n)]=(stack[0][2][0]+1,stack[0][2][1])
    fragments[(160,32)]=(0,tree(160,32)); fragments[(192,64)]=(0,tree(192,64))
    last_local=max(avail.values()); avail['q0']=last_local
    pending=dict(fragments)
    while (0,256) not in pending:
        ready,n,b=min((max(a[0],pending[(b+n,n)][0]),n,b)
            for (b,n),a in pending.items() if b%(2*n)==0 and (b+n,n) in pending)
        a=pending.pop((b,n)); z=pending.pop((b+n,n))
        pending[(b,2*n)]=add(a,z,'q0',f'global{b}:{b+2*n}')
    root=pending[(0,256)]
    assert root[1]==tree(0,256) and len(ops)==1281
    assert len({e['emit'] for e in emits})==64
    for r in avail:
        rows=sorted((o['start'],o['done']) for o in ops if o['resource']==r)
        assert all(a[1]<=b[0] for a,b in zip(rows,rows[1:]))
    return dict(nl=nl,emit_period=period,actual_emit_slots=64,total_adders=4,
        root_serial=root[0],R_native_done_serial_illustration=root[0]+79,
        R_native_done_stream_illustration=(root[0]+79)*4/3,
        extra_stream_over_original182_18=(root[0]+79)*4/3-182.18,
        whole_expression_sha256=digest(root[1]),emits=emits,operations=ops,
        source_change='NEW per-chunk lane-liveness lowering; whole-group capture prohibited')

result=dict(scope='MODEL ONLY; no numerical, RTL, physical or token PASS',
    source_commit='1dad69123',
    source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                   [HERE/'source_add_lat.sv',HERE/'source_pretree.sv',HERE/'inventory_exact.json']},
    selected=schedule(9,112),four_global_adders=schedule(9,112,global_adders=4),
    four_total_adders=four_adder_schedule(),
    optimistic_source_node_only=schedule(7,80),
    native_fill=dict(sectors=160,banks=24,last_command=7,last_commit=28,
                     first_emit=32,prefetch_assumed=False),
    storage=dict(retained_full512_input_payload_valid_FF=512*33,
        active_compute_stations=40,words_per_station=8,
        actual_station_operand_bits=8*32,
        extra_accumulator_output_FF=40*33,
        local_select_pipeline_FF=40*2*2*33,
        fragment_bank_bits=26*56,
        global_select_pipeline_FF=2*2*56,
        static_operator_schedule_state_FF_upper=40*24+64,
        tag_and_fragment_fault_FF_upper=128,
        native_adder_LAT6_register_bits=499,
        existing_node_OPR_and_mode_bits=72,
        arithmetic_nodes=41,
        arithmetic_pipeline_FF=41*571,
        scheduler_command_store_capacity_total=7111,
        scheduler_command_store_physical_slots=8192,
        scheduler_command_store_per_bank=128,
        new_SRAM_macros=0,
        operator_register_classification='ROOT confirmed true private operator operands admissible; no coherent memory sharding'),
    unqualified=['actual source A profile and NL feedback/selection capture edges',
        'actual independent operand ports/state/control source and fragment bank implementation',
        'native arithmetic cell mapping/mux/decode/control/reset copies and clock',
        'producer native sector visibility and physical placement',
        'qcore new root operand and real SRAM RF binding/route L/host H',
        'all boundaries/region relay latency and actual native SRAM access timing',
        'packed command lowering/dictionary/index/store bank capacity',
        'dependent record reschedule/SU reservation and complete token simulation'])
storage=result['storage']
storage['all_explicit_FF_reservation_before_fanout_copies']=sum(storage[k] for k in (
    'retained_full512_input_payload_valid_FF','extra_accumulator_output_FF',
    'local_select_pipeline_FF','fragment_bank_bits','global_select_pipeline_FF',
    'static_operator_schedule_state_FF_upper','tag_and_fragment_fault_FF_upper',
    'arithmetic_pipeline_FF'))
ff=storage['all_explicit_FF_reservation_before_fanout_copies']
storage['reference_DFF_area_um2']=ff*.2916
storage['reference_DFF_TT_CLK_fF']=ff*.474736
(HERE/'model.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:{x:v for x,v in result[k].items() if x not in ('operations','stations','emits')}
                  for k in ('selected','four_global_adders','four_total_adders','optimistic_source_node_only')},indent=2))
print(json.dumps(storage,indent=2))
