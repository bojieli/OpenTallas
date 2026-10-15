"""Real engine13 PQ host boot/program/calendar encoder for c9 + PHW10.

This encodes source RTL interfaces. It does not grant physical phase, canonical
operand content, or die qualification. Existing engine identities0..12 remain.
"""
from program import encode_program
from pq_descriptors import encode_descriptors
from pq_calendar import compile_events,viamap

PQ_ENGINE=13
HOST_PQ_CSR=0x12

def host_word(opcode,word):
    if type(word)is not int or not 0<=word<1<<35:raise ValueError('actual PW payload35 required')
    return opcode|((word&((1<<28)-1))<<32)|((word>>28)<<96)

def compile_stage(rows,descriptors,events,stage,phase,base=0):
    if type(base)is not int or not 0<=base<4096:raise ValueError('calendar base12')
    pq=[r for r in rows if r['engine']==PQ_ENGINE]
    if not pq:raise ValueError('actual PQ engine13 row required')
    desc_words=encode_descriptors(descriptors,phase_width=10)
    for r in pq:
        if r['arg']>=len(descriptors):raise ValueError('missing actual descriptor')
        d=descriptors[r['arg']]
        if r['native_tag']!=d['native_tag'] or r['pin_to_pin']!=d['observed_end_edges']+2:
            raise ValueError('PHW10 PINREG endpoint: done is observed-END duration plus2 registered launch/input-capture edges')
    words=compile_events(events,pq,action_bits=75,pq_engine=PQ_ENGINE)
    if base+len(words)>4096:raise ValueError('actual paired calendar ROM capacity')
    issuer=encode_program(rows,stage,phase)
    # Host packets occupy fixed stream edges >=8 apart: slower than the
    # four-serial-edge host dequeue plus actual fixed alternating mailbox.
    packets=[];cycle=16
    def emit(op,w):
        nonlocal cycle
        packets.append(dict(host_stream_cycle=cycle,cls=0,data=host_word(op,w)))
        cycle+=8
    emit(0x11,len(rows))
    for w in issuer['writes']:emit(0x10,w['word'])
    emit(HOST_PQ_CSR,(6<<25)|((len(words)-1)<<12)|base)
    for w in desc_words:emit(HOST_PQ_CSR,w)
    # NDesc64 scan + endpoint pin capture + FIFO/mailbox crossing and
    # skew-independent boot margin. These edges are initialization only.
    cycle+=200
    emit(HOST_PQ_CSR,5<<25)
    arm=cycle+200
    padded=[0]*base+words
    return dict(schema='opentallas.s81.pq-engine13-c9.v1',engine=PQ_ENGINE,
                issuer=issuer,descriptor_words=desc_words,calendar_words=words,
                calendar_action_viamap=viamap([w&((1<<72)-1)for w in padded]),
                calendar_time_viamap=viamap([w>>72 for w in padded]),
                host_packets=packets,earliest_job_host_stream_cycle=arm,
                clock_ratio_stream_to_serial='4:3 frequency',
                memory=dict(existing_descriptor_rows=64,existing_descriptor_bits=117,
                            existing_calendar_macros=2,calendar_macro_shape='4096x72',
                            new_rom_macros=0,new_sram_macros=0),
                dispatch_eligible=False,qualified=False,
                blockers=['physical phase/transport and native whole-program validation required'])
