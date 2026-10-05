#!/usr/bin/env python3
"""Deterministic whole-row HBROM layout, address codec and finite read calendar.

A storage group is four streams, each backed by two alternating 4096-row
macros. Four simultaneous words form one 1088-bit SM record. Padding is stored
and charged. This software layout is not a physical/RTL qualification.
"""
from __future__ import annotations
import argparse
import gzip
import json
from pathlib import Path


def ceildiv(a, b):
    return (a + b - 1) // b


def normalize_format(fmt):
    return {'mxfp4_packed': 'fp4', 'fp8_e4m3': 'fp8', 'f32': 'fp32'}.get(fmt, fmt)


def row_geometry(fmt, k, layout_mode="padded"):
    fmt = normalize_format(fmt)
    if fmt not in ('fp4', 'fp8', 'bf16') or k <= 0:
        raise ValueError('SM requires positive K and supported exact format')
    lanes = {'fp4': 8, 'fp8': 4, 'bf16': 64}[fmt]
    chunk = 8 if fmt == 'bf16' else 256
    chunks = ceildiv(k, chunk)
    groups = ceildiv(chunks, lanes)
    if layout_mode not in ('padded', 'compact'): raise ValueError('layout mode')
    # Native SM stack creates missing tree groups; no ROM zero bridge. Both
    # legacy mode names deliberately map to this one source-correct layout.
    physical_steps=list(range(8*groups))
    return dict(format=fmt, k=k, lanes=lanes, chunk_k=chunk, groups=groups,
                steps=8, records_per_row=len(physical_steps), words_per_row=4*len(physical_steps),
                issued_records_per_row=8*groups, physical_steps=physical_steps,
                layout_mode=layout_mode, padded_k=groups*lanes*chunk)


def code_coordinate(fmt, group, step, lane, within=0):
    """SM lane -> source K; caller zero fills coordinates beyond true K."""
    lanes = {'fp4': 8, 'fp8': 4, 'bf16': 64}[fmt]
    if not (0 <= lane < lanes and 0 <= step < 8):
        raise ValueError('lane/step bounds')
    if fmt == 'bf16':
        if within: raise ValueError('BF16 has one scalar per lane')
        return (group*lanes+lane)*8+step
    if not 0 <= within < 32: raise ValueError('block coordinate bounds')
    return (group*lanes+lane)*256+step*32+within


def encode_record(fmt, k, group, step, code, scale=None):
    """Compile four physical words from callbacks code(k), scale(k//32).

    BF16 callback supplies already rounded immutable BF16 bits, including wo_a
    expansion. Scale callback returns stored UE8M0 byte, never signed exponent.
    """
    fmt = normalize_format(fmt)
    words = [0]*4
    if fmt == 'bf16':
        for lane in range(64):
            pos=code_coordinate(fmt,group,step,lane)
            v=code(pos) if pos<k else 0
            if not 0<=v<65536: raise ValueError('BF16 code')
            words[lane//16] |= v << (16*(lane%16))
    else:
        if fmt not in ('fp4','fp8') or scale is None: raise ValueError('quantized scale required')
        lanes=8 if fmt=='fp4' else 4; width=4 if fmt=='fp4' else 8
        for lane in range(lanes):
            wi=lane//2 if fmt=='fp4' else lane
            base=136*(lane%2) if fmt=='fp4' else 0
            pos=code_coordinate(fmt,group,step,lane)
            for j in range(32):
                v=code(pos+j) if pos+j<k else 0
                if not 0<=v<(1<<width): raise ValueError('weight code')
                words[wi] |= v << (base+j*width)
            sc=scale(pos//32) if pos<k else 127
            if not 0<=sc<256: raise ValueError('scale code')
            words[wi] |= sc << (base+32*width)
    return words


def swizzle(fmt, words):
    """Four ROM words -> SM 1024 weight bits followed by eight scale bytes."""
    if len(words)!=4 or any(w<0 or w>>274 for w in words): raise ValueError('ROM word bounds')
    fmt=normalize_format(fmt); result=0
    for i,w in enumerate(words):
        if fmt=='fp4':
            result |= (w & ((1<<128)-1)) << (256*i)
            result |= ((w>>136)&((1<<128)-1)) << (256*i+128)
            result |= ((w>>128)&255) << (1024+16*i)
            result |= ((w>>264)&255) << (1032+16*i)
        elif fmt in ('fp8','bf16'):
            result |= (w&((1<<256)-1)) << (256*i)
            if fmt=='fp8': result |= ((w>>256)&255) << (1024+8*i)
        else: raise ValueError('unsupported SM format')
    return result


def summarize_storage_records(tensors, tp=1):
    """Cheap necessary capacity bound, before per-owner/group-tail allocation.

    Omits only allocation holes, never native SM lane padding. Passing this
    bound is not a fit verdict. Count inline quantized scales through records;
    separately listed source scale archives remain charged.
    """
    total=0; cache={}
    for tensor in tensors:
        fmt=normalize_format(tensor.get('format','raw'))
        k=int(tensor.get('k',tensor.get('K',0)) or 0)
        matrix=(fmt in ('fp4','fp8','bf16') and k>1 and not tensor.get('is_scale') and not tensor['name'].endswith('.scale'))
        if matrix:
            key=(fmt,k)
            if key not in cache: cache[key]=row_geometry(fmt,k)['records_per_row']
            records=int(tensor.get('rows') or 1)*cache[key]
        else: records=ceildiv(int(tensor['bytes']),128)
        total+=records*int(tensor.get('replicas_per_rank',1))*(tp if tensor.get('replicated',False) else 1)
    return dict(total_records=total,physical_words=4*total,
                excludes='per-group tail holes and per-matrix eight-record alignment',
                is_necessary_bound_only=True)


def allocate(tensors, tp, clusters_per_die, pairs_per_cluster, rows_per_macro=4096, emit_runs=True, layout_mode="padded", emit_summaries=True):
    """Allocate source records; clusters here are independent compute tiles.

    Every logical row belongs to exactly one rank/tile by cyclic assignment.
    Four-pair groups are filled sequentially; each matrix row stays in a group.
    Source scale tensors remain separately archived if present: inline scale
    replication and this conservative duplicate are both explicitly charged.
    """
    if min(tp,clusters_per_die,pairs_per_cluster,rows_per_macro)<=0 or pairs_per_cluster%4 or rows_per_macro%8:
        raise ValueError('positive geometry, four pairs per record group required')
    depth=2*rows_per_macro; groups=pairs_per_cluster//4
    cursors=[[0]*clusters_per_die for _ in range(tp)]
    runs=[]; summaries=[]; rotate=0; padding=0; useful=0
    for tensor in sorted(tensors,key=lambda t:t['name']):
        n=tensor['name']; fmt=normalize_format(tensor.get('format','raw'))
        nr=int(tensor.get('rows') or 1); k=int(tensor.get('k',tensor.get('K',0)) or 0)
        matrix=(fmt in ('fp4','fp8','bf16') and k>1 and not tensor.get('is_scale') and not n.endswith('.scale'))
        geom=row_geometry(fmt,k,layout_mode) if matrix else None
        if matrix:
            rpr=geom['records_per_row']; logical_rows=nr
        else:
            # Raw payload is packed densely in 128-byte records, including
            # scalar vectors and archived scales; one record is one unit.
            rpr=1; logical_rows=ceildiv(int(tensor['bytes']),128)
        if rpr>depth: raise ValueError(f'{n}: row exceeds physical storage group depth')
        replicas=int(tensor.get('replicas_per_rank',1)); replicated=tensor.get('replicated',False)
        stride=clusters_per_die if replicated else tp*clusters_per_die
        entries=[]
        for rank in range(tp):
            for tile in range(clusters_per_die):
                owner=tile if replicated else rank*clusters_per_die+tile
                # All executable matrices share source-row ownership. In particular,
                # gate/up rows and every selected/shared down output row meet at
                # the same rank/tile; raw archives may rotate for capacity.
                first=owner if matrix else (owner-rotate)%stride
                count=0 if first>=logical_rows else 1+(logical_rows-1-first)//stride
                if not count: continue
                for replica in range(replicas):
                    left=count; source=first
                    while left:
                        cur=cursors[rank][tile]
                        if matrix:
                            aligned=ceildiv(cur,8)*8; padding+=aligned-cur;cur=aligned
                        group,off=divmod(cur,depth)
                        room=(depth-off)//rpr
                        if not room:
                            padding+=depth-off; cur=(group+1)*depth; group+=1;off=0;room=depth//rpr
                        take=min(left,room)
                        if emit_runs:
                            run=dict(name=n,rank=rank,tile=tile,replica=replica,group=group,
                                     record_base=off,first_row=source,row_stride=stride,row_count=take,
                                     records_per_row=rpr,format=fmt if matrix else 'raw',k=k if matrix else 0,
                                     physical_steps=geom['physical_steps'] if geom else [0])
                            runs.append(run)
                        if emit_summaries: entries.append(dict(rank=rank,tile=tile,rows=take,records=take*rpr,group=group))
                        cursors[rank][tile]=cur+take*rpr;source+=take*stride;left-=take
        if emit_summaries: summaries.append(dict(name=n,geometry=geom,logical_rows=logical_rows,owners=entries))
        useful+=int(tensor['bytes'])*(tp if replicated else 1)*replicas
        if not matrix: rotate=(rotate+logical_rows)%stride
    peak=max(max(row) for row in cursors); fits=peak<=groups*depth
    return dict(schema='opentallas.hbrom.allocator.v1',fits=fits,tp=tp,tiles_per_die=clusters_per_die,
                pairs_per_tile=pairs_per_cluster,rows_per_macro=rows_per_macro,groups_per_tile=groups,
                layout_mode=layout_mode,required_pairs_per_tile=4*ceildiv(peak,depth),
                capacity_records_per_tile=groups*depth,used_record_highwaters=cursors,
                max_cluster_bytes=peak*128,capacity_bytes_per_rank=groups*depth*128*clusters_per_die,
                allocated_bytes_per_rank=max(sum(r) for r in cursors)*128,
                useful_bytes_per_rank=ceildiv(useful,tp),group_tail_padding_records=padding,
                tensors=summaries,runs=runs,mapping='aligned matrix row modulo rank/tile; 4-stream native SM records; physical group bounded',
                fit_is_not_physical_qualification=True)


def physical_address(run, source_row, group_step, stream, rows_per_macro=4096):
    delta=source_row-run['first_row']
    if delta<0 or delta%run['row_stride'] or delta//run['row_stride']>=run['row_count']:
        raise ValueError('row not owned by run')
    if not 0<=stream<4: raise ValueError('stream bounds')
    if group_step not in run['physical_steps']: raise ValueError('generated zero record has no ROM address')
    stored_step=run['physical_steps'].index(group_step)
    record=run['record_base']+(delta//run['row_stride'])*run['records_per_row']+stored_step
    if record>=2*rows_per_macro: raise ValueError('physical depth')
    return dict(rank=run['rank'],tile=run['tile'],macro=8*run['group']+2*stream+(record//8)%2,
                row=(record//16)*8+record%8)


def inverse_address(run, macro, row, rows_per_macro=4096):
    if not 0<=row<rows_per_macro or macro//8!=run['group']: raise ValueError('physical bounds')
    record=(row//8)*16+(macro%2)*8+row%8; delta=record-run['record_base']
    if not 0<=delta<run['row_count']*run['records_per_row']: raise ValueError('unowned address')
    unit,step=divmod(delta,run['records_per_row'])
    return dict(source_row=run['first_row']+unit*run['row_stride'],group_step=run['physical_steps'][step],stream=(macro%8)//2)


def selected_calendar(allocation, names, il=8):
    """Per-tile serialized selected tensor service, group-slot wave bubbles.

    Each cycle reads one record from four alternating-macro streams. Group-slot
    order interleaves independent eight-step chains. No credit for unused banks.
    This is no-stall service only; caller adds transport, finite-credit stalls,
    descriptor, activation and arithmetic drain latency.
    """
    selected=set(names); tiles={}; seen=set()
    for t in allocation['tensors']:
        if t['name'] not in selected: continue
        seen.add(t['name']); work={}
        for own in t['owners']:
            key=(own['rank'],own['tile']);work[key]=work.get(key,0)+own['rows']
        for key,rows in work.items():
            g=t['geometry']; cycles=ceildiv(rows*g['groups'],il)*il*8 if g else rows
            value=tiles.setdefault(key,dict(cycles=0,records=0,source_request_cycles_upper=0,matrices=[]))
            records=rows*g['records_per_row'] if g else rows
            # Only final partial IL wave can have odd record count. Each
            # of seven timestep boundaries may then need one macro-busy wait.
            # Storage-group boundaries can remove waits, so this is an upper bound.
            recurrence_stalls=7 if g and (rows*g['groups'])%2 else 0
            source_upper=records+recurrence_stalls
            value['cycles']+=max(cycles,source_upper);value['records']+=records
            value['source_request_cycles_upper']+=source_upper
            value['matrices'].append(dict(name=t['name'],rows=rows,cycles=max(cycles,source_upper),issue_cycles=cycles,
                                          records=records,source_request_cycles_upper=source_upper,
                                          macro_busy_stalls_upper=recurrence_stalls))
    if selected-seen: raise ValueError('unmapped selected tensors: '+str(sorted(selected-seen)))
    return dict(max_cycles=max((v['cycles'] for v in tiles.values()),default=0),
                tiles=[dict(rank=k[0],tile=k[1],**v) for k,v in sorted(tiles.items())],
                policy='selected tensors serialize per tile; group-slot exact 8-step waves; four streams per issued record',
                excludes='ready stalls, pool-select pipeline, descriptor, activation, drain and result transport')


def access_calendar(allocation, name, rank, tile, il=8):
    """Yield physical reads in native group-slot order, with explicit bubbles.

    Matrix record addresses use item parity for macro selection: all eight
    timesteps of one item occupy one macro. Adjacent group-slot items alternate
    macros, meeting the two-cycle capture service even when t is unchanged.
    """
    runs=[r for r in allocation['runs'] if r['name']==name and r['rank']==rank and r['tile']==tile]
    if not runs: return
    if any(r['format']=='raw' for r in runs): raise ValueError('raw provider is not an SM matrix')
    rows=sorted((r['first_row']+i*r['row_stride'],r) for r in runs for i in range(r['row_count']))
    groups=runs[0]['records_per_row']//8
    cycle=0
    for wave in range(0,len(rows)*groups,il):
        for step in range(8):
            for slot in range(il):
                item=wave+slot
                if item>=len(rows)*groups:
                    yield dict(cycle=cycle,bubble=True)
                else:
                    ri,group=divmod(item,groups);source_row,run=rows[ri]
                    addresses=[physical_address(run,source_row,8*group+step,s,allocation['rows_per_macro']) for s in range(4)]
                    yield dict(cycle=cycle,bubble=False,source_row=source_row,group=group,step=step,addresses=addresses)
                cycle+=1


def source_request_calendar(allocation, name, rank, tile, il=8):
    """Dense bulk-copy requests in issue order, with actual macro busy stalls.

    Bulk copy omits IL bubble slots. Odd final waves can revisit a macro at the
    next timestep immediately; req_ready must stall until its two-cycle read
    service permits capture. This generator prices that wait, without a lookup
    table or changing immutable addresses. Transport/staging credit stalls are
    separate additional constraints.
    """
    last={}; cycle=0; sequence=0
    for event in access_calendar(allocation,name,rank,tile,il):
        if event['bubble']: continue
        earliest=max([cycle]+[last.get(a['macro'],-2)+2 for a in event['addresses']])
        stalled=earliest-cycle
        yield dict(event,cycle=earliest,issue_cycle=event['cycle'],request_index=sequence,
                   macro_busy_stall_cycles=stalled)
        for a in event['addresses']: last[a['macro']]=earliest
        cycle=earliest+1;sequence+=1


def main():
    p=argparse.ArgumentParser();p.add_argument('--inventory',required=True);p.add_argument('--out',required=True)
    p.add_argument('--tp',type=int,default=4);p.add_argument('--tiles',type=int,required=True);p.add_argument('--pairs',type=int,required=True)
    a=p.parse_args();path=Path(a.inventory)
    with (gzip.open(path,'rt') if path.suffix=='.gz' else path.open()) as f: inv=json.load(f)
    result=allocate(inv['tensors'],a.tp,a.tiles,a.pairs)
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    with (gzip.open(out,'wt') if out.suffix=='.gz' else out.open('w')) as f: json.dump(result,f)

if __name__=='__main__':main()
