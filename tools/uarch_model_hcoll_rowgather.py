"""Pre-RTL complete Engram ROW_GATHER transport/assembly model.

Source and consumer are real two-macro row stores from0d07ffe3e. Exact link
profile is the proved logical102edgeFEC+8edgeCDC profile1b3f1c2bb, not PMA512
qualification. Source SRAM load/service latency is supplied separately.
"""
import collections,json,pathlib
class ScheduleFault(ValueError):pass

def compile_calendar(receipt,layer=1,profile_rx_base=614,two_rate=False):
    rows=[x for x in receipt['rows'] if x['layer']==layer]
    assert [x['list_index'] for x in rows]==list(range(24))
    first=0 if layer==1 else 8;consumer=first+8
    assert set(x['rank'] for x in rows)==set(range(first,consumer))
    def acceptance(j):
        w=(613*j)//487
        return 511+(17*w)//16 if two_rate else 498+w
    def publication(j):
        w=(613*(j+1)+486)//487-1
        return 702+(17*w)//16 if two_rate else profile_rx_base+w
    events={};hops=[];requests=[];packets=[];writes=[];used=[{} for _ in range(8)]
    def reserve(unit,c,identity):
        key=(unit,c)
        if key in events and events[key]!=identity:raise ScheduleFault((key,events[key],identity))
        events[key]=identity
    for row in rows:
        home=row['rank']-first;rid=row['list_index']
        for pair in range(5):
            identity=rid*5+pair
            for start in range(486,100000):
                mark=dict(events);oldh=len(hops);oldw=len(writes);undo=[]
                try:
                    # RAW+3, packetizer input capture+1/output+1, qslots+1.
                    req=[(start-7,2*pair),(start-6,2*pair+1)] if pair<4 else [(start-6,8)]
                    for c,sector in req:
                        if c<479:raise ScheduleFault('read before staged source ready')
                        reserve(f'home{home}.read',c,(rid,sector))
                    capture=start;source=0
                    for link in range(home,8):
                        reserve(f'n{link}.qsrc{source}',capture,identity)
                        reserve(f'n{link}.qsink0',capture+1,identity)
                        reserve(f'n{link}.bridge0',capture+3,identity)
                        write=capture+5
                        j=max(0,((write+11-(511 if two_rate else 498))*487*(16 if two_rate else 1))//(613*(17 if two_rate else 1))-2)
                        if used[link]:j=max(j,max(used[link])+1)
                        while acceptance(j)<write+11:j+=1
                        accept=acceptance(j);read=accept-7
                        k=(613*(j+1)+486)//487-1;receive=publication(j)
                        seq=len(used[link]);slot=seq%64
                        if seq>=65536:raise ScheduleFault('sequence overflow')
                        if seq>=64:
                            old=next(e for e in reversed(hops) if e['link']==link and e['seq']==seq-64)
                            if write<old['read']+4:raise ScheduleFault('replay64 overwrite')
                        reserve(f'l{link}.write',write,identity);reserve(f'l{link}.read',read,identity)
                        reserve(f'n{link+1}.rxface',receive+1,identity)
                        used[link][j]=seq;undo.append((link,j))
                        hops.append(dict(index=identity,home=home,row=rid,pair=pair,link=link,seq=seq,slot=slot,capture=capture,write=write,read=read,accept=accept,ordinal=j,receive=receive))
                        capture=receive+3;source=3
                    reserve('consumer.qsrc3',capture,identity);reserve('consumer.qsink3',capture+1,identity)
                    # qslot outputC+2, assembler inputC+3, outputC+4,
                    # actual consumer row-store samples lowerC+5/upperC+6.
                    for w,sector in [(capture+5,2*pair)]+([] if pair==4 else [(capture+6,2*pair+1)]):
                        reserve('consumer.write',w,(rid,sector));writes.append(dict(cycle=w,row=rid,sector=sector))
                    requests.extend(dict(home=home,row=rid,sector=sector,cycle=c) for c,sector in req)
                    packets.append(dict(index=identity,home=home,row=rid,pair=pair,source_capture=start,consumer_capture=capture+3))
                    break
                except ScheduleFault:
                    events=mark
                    for link,j in undo:del used[link][j]
                    del hops[oldh:];del writes[oldw:]
            else:raise ScheduleFault('no finite resource-safe source schedule')
    assert len(writes)==216 and len({(x['row'],x['sector']) for x in writes})==216
    finalwrite=max(x['cycle'] for x in writes)
    # Actualconsumer commit+1; scale read first, then eight code sectors.
    decode=[dict(cycle=finalwrite+2+row*9+s,row=row,sector=([8]+list(range(8)))[s]) for row in range(24) for s in range(9)]
    done=decode[-1]['cycle']+4
    last_rx=max(x['receive'] for x in hops)
    stop=2877 if two_rate else 2658
    if any((613*(e['ordinal']+1)+486)//487-1>=2048 for e in hops):raise ScheduleFault('payload requiresword beyond2048wordepoch')
    if done>=stop:raise ScheduleFault(f'operation extends past compiled finite window:done{done} stop{stop}')
    result=dict(status='PRE_RTL_CALENDAR_RESOURCE_PASS; logical FEC profile only',layer=layer,home_ranks=list(range(first,consumer)),consumer_rank=consumer,rows=24,bytes_per_row=288,sectors=216,packets=120,links=8,requests=requests,packets_calendar=packets,hops=hops,consumer_writes=writes,consumer_reads=decode,last_packet_publication=last_rx,last_consumer_write=finalwrite,done=done,finite_read_last=2871 if two_rate else 2656,finite_window_headroom=stop-1-done,two_rate=two_rate,reserved_resources=len(events),profile=dict(tx=6,rx=2,accept_base=511 if two_rate else 498,rx_publication_base=702 if two_rate else profile_rx_base,word_bits=487,frame_bits=613,fec_age=151 if two_rate else 102,internal_cdc_age_fec=8,window_words=2048,core_period_ticks=16,fec_period_ticks=17 if two_rate else 16,qualification='ExacteventmodelpendingactualRTLproof' if two_rate else 'Provedsameclocklogicalbaseline'),physical='Source-pinned candidate8neighborchain. PMA512, actual clocks/pads and resulting latency are not qualified.')
    return result

def model():
    return dict(kind='actual8home_row_gather_to1consumer',input_bytes=24*288,payload_packets=120,source_homes=8,consumer_count=1,source_rows_per_home=3,macs_per_cycle=0,source_memory_read_bytes_per_cycle=32,consumer_memory_write_bytes_per_cycle=32,source_sram_instances=16,consumer_sram_instances=2,macro='ot_sram_1r1w_128x256_m1_r2c2',macro_bits_total=18*128*256,payload_boundary_bits=545,native_frame_bits=612,inband_frame_bits=613,transport_word_bits=487,endpoints=16,replay_macros=64,links=8,programme_width=256,programme_payload_bits=238,programme_operations_per_macro_word=2,programme_banks_per_node=19,programme_cycles_per_node=2432,programme_instances=9,programme_native_macros=171,programme_macro_bits=171*64*512,programme_execution='nativeSRAMtypedextension; unchangedG25Anormativeprogrammejoinnotclaimed',packetizer_max_clock_sinks=1800,depacketizer_max_clock_sinks=2100,source_packetizer_capacity=1,consumer_assembler_capacity=1,consumer_writes_per_full_packet=2,normal_flow='fixed compiler reservations, no ready/credits',clock_target_ps=833.334,area_um2=None,floorplan_fit=None,corridor_capacity=None,physical_status='unqualified; requires actual native hard views/clock/geometry and PMA512 join')
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('receipt',type=pathlib.Path);p.add_argument('out',type=pathlib.Path);p.add_argument('--two-rate',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    v=json.loads(a.receipt.read_text())
    for layer in [1,14]:
        cal=compile_calendar(v,layer,two_rate=a.two_rate);(a.out/f'layer{layer}.json').write_text(json.dumps(cal,indent=2)+'\n');print(layer,cal['done'],cal['finite_window_headroom'])
    (a.out/'model.json').write_text(json.dumps(model(),indent=2)+'\n')
