"""Phase-wide exclusion for proposed default-off intercepted ROM scalar slot0.
Pure accepted-journal checker. No copied ingress/RTL implementation or provider
qualification is supplied. Source port0 is not a native root-row alias.
"""
import argparse
import hashlib
import json
from pathlib import Path
import dsrom_I66_capture_owner as O
import dsrom_I66_consumer_deadline as D
import dsrom_I66_widened_visible_callback as V

ROOT=Path(__file__).resolve().parents[1]


def source_plan():
    source=D.source_model()
    return dict(scope='PROPOSED_SLOT0_PHASE_EXCLUSION_CHECK_NOT_ACTUAL_ADMISSION',
        source_sha256=V.source_plan()['source_sha256'],
        Nash_successor='6f2c3b8f143fb6cecc5534b6cb9abbbd29166efb',
        proposed_write='dut.u_tile.rom_we[0], rom_waddr[0+:AW30], rom_wdata[0+:32]',
        port0_is_intercepted_ingress_not_native_root_id=True,
        ingress_default_off=True,implemented_copied_ingress=False,
        mux_owner_and_exclusion_cost=None,
        necessary_native_ROM_exclusion='slot0 substitution does not silence native slots1..127; prove no writes into the lease or explicitly price suppression/interception',
        lease_origin='actual acquired owner epoch, not borrowed cone retirement422',
        unchanged_formatter='row + pos*ops + obase; source fmt/pw62/pw63/rsplit, supplied BF16, error0 and VM19 bounds',
        writer_families=list(V.WRITERS),
        exclusion='every source edge from phase lease through last associated consumer read/Xtag; any other writer to a leased address rejected, including equal bits',
        scalar_source_credit='actual visible then positive captured feedback; does not free phase address lease',
        phase_address_lease='held until all576 associated consumers observed and tags matched; no timed release or promise',
        generation_rearm='separate source/route/packetACK owner fences still required; not proved by this address-lease checker',
        consumer='actual source xs_rd_re/src0/address/old data -> observed vx/cwx Xtag atR+2; accepted consumer owner, not current PC',
        consumer_source_nodes=[dict(producer=x['producer_node'],consumers=x['first_static_consumer']) for x in source['obligations']],
        scope_clock='native_core_clk only; no inferred physical3:4CDC conversion',
        current_enrollment='current PHW10 binary/source/program/field + compiled intercepted-ingress callback closure and accepted journal must qualify separately',
        actual_consumer_deadline=None,C=None,stations=None,RTL_GO=False,new_jobs=False)


def check(lease,samples,credit_min_delay):
    V.uint(credit_min_delay,32)
    if not credit_min_delay or lease['clock']!='native_core_clk':
        raise ValueError('positive qualified native credit feedback required')
    ctx=lease['context'];O.identity(ctx)
    first=V.uint(lease['start_edge'],64);last=V.uint(lease['release_edge'],64)
    if last<=first:
        raise ValueError('source phase lifetime')
    # Sparse snapshots cannot prove absence of competing writes.
    if len(samples)!=last-first+1 or any(V.uint(s['edge'],64)!=first+i for i,s in enumerate(samples)):
        raise ValueError('every phase source edge must be sampled')
    records=lease['records']
    if len(records)!=576 or [r['row'] for r in records]!=list(range(576)):
        raise ValueError('complete source row identities')
    desc=lease['descriptor']
    for name,width in [('fmt',2),('rsplit',16),('pw62',1),('pw63',1),('obase',30),('ops',30)]:
        V.uint(desc[name],width)
    formatted=[O.source_formatter(r,desc) for r in records]
    if len({a for a,d in formatted})!=576:
        raise ValueError('source formatter address alias')
    frame={a:(r,data) for r,(a,data) in enumerate(formatted)}
    expected=next((o for o in D.source_model()['obligations'] if o['producer_node']=='L0.I'+str(ctx['pc'])),None)
    if expected is None:
        # Existing archived node spelling is source-owned; do not invent it.
        expected=next((o for o in D.source_model()['obligations'] if int(o['producer_node'].split('I')[-1])==ctx['pc']),None)
    if expected is None:
        raise ValueError('unknown accepted producer PC')
    choice=next((p for p in expected['phase_choices'] if p['expert']==ctx['expert']),None)
    if choice is None or any(ctx[k]!=choice[v] for k,v in [('stage','stage'),('phase','phase'),('key_word','source_key_word')]):
        raise ValueError('source expert/stage/phase/key association')
    if set(frame)!=set(range(*expected['output_VM_elements'])):
        raise ValueError('source output/consumer footprint mismatch')
    consumer_pc=int(expected['first_static_consumer'][0]['consumer_node'].split('I')[-1])
    consumer_operands={p['operand'] for p in expected['first_static_consumer']}
    pubs={};reads={};credits={};tags={};read_refs=[];next_pub=0
    for s in samples:
        edge=s['edge']
        if (s['clock']!='native_core_clk' or s['context']!=ctx or O.identity(s['context'])!=O.identity(ctx) or
            s['reset_accepted'] is not True or s['healthy'] is not True):
            raise ValueError('source clock/context/healthy epoch')
        if s['sampled_writer_classes']!=list(V.WRITERS):
            raise ValueError('complete writer family sampling')
        params=s['parameters']
        if any(V.uint(params.get(k),32)!=v for k,v in {'X_ROM':1,'ROM_PHW':10,'ROM_R':128,'SUN':256,'ROM_FBW':1632}.items()):
            raise ValueError('current PHW10 source geometry')
        publication=s['ingress']
        own=None
        if publication is not None:
            row=V.uint(publication['row'],16)
            if row!=next_pub or V.uint(publication['physical_shard'],1)!=((row%256)//2)//64:
                raise ValueError('ordered intercepted source identity')
            address,data=formatted[row]
            own=(address,data);next_pub+=1
        target=[]
        for w in s['writes']:
            if w['kind'] not in V.WRITERS:
                raise ValueError('unknown writer')
            full=V.uint(w['address'],30);data=V.uint(w['data'],32);V.uint(w['port'],16)
            resolved=full%(2**19)
            if resolved in frame:
                if own is None or (full,data)!=own or w['kind']!='rom' or w['port']!=0:
                    raise ValueError('phase address lease violated by competing writer')
                target.append(w)
        for kind in ('xa','xb'):
            for port in {w['port'] for w in s['writes'] if w['kind']==kind}:
                if (kind=='xa' and port!=0) or (kind=='xb' and not 0<=port<4):
                    raise ValueError('external port index')
                addresses=[w['address'] for w in s['writes'] if w['kind']==kind and w['port']==port]
                base=min(addresses)//16*16
                if len(addresses)!=16 or sorted(addresses)!=list(range(base,base+16)):
                    raise ValueError('complete unmasked512 write sample required')
        if own is not None:
            if len(target)!=1 or s['post_stage']!='postNBA' or V.uint(s['post_edge'],64)!=edge or V.uint(s['post_VM'].get(str(own[0])),32)!=own[1]:
                raise ValueError('actual accepted slot0/postNBA witness missing')
            # Recorded publication happens after preedge reads at this edge.
            pubs[publication['row']]=edge
        for read in s['reads']:
            if V.uint(read['src'],2)!=0:
                continue
            address=V.uint(read['address'],30)
            if address%(2**19) not in frame:
                continue
            row,data=frame[address%(2**19)]
            if address not in frame or row in reads or row not in pubs or pubs[row]>=edge or V.uint(read['data'],32)!=data:
                raise ValueError('consumer read before owned visibility/alias/duplicate/data mismatch')
            c=read['consumer_context']
            for name,width in [('rank',2),('generation',32),('user',32),('xversion',32),('pc',14),('seq',8)]:
                V.uint(c[name],width)
            if c['pc']!=consumer_pc or any(c[k]!=ctx[k] for k in ('rank','generation','user','xversion')):
                raise ValueError('accepted consumer owner differs from source obligation')
            if 'abcd'[V.uint(read['port'],10)%4] not in consumer_operands:
                raise ValueError('source consumer operand mismatch')
            reads[row]=edge;read_refs.append((row,edge,c))
        for tag in s['X_tags']:
            if tag['valid'] is not True or tag['fault'] is not False:
                raise ValueError('invalid actual Xtag')
            key=(edge,V.uint(tag['rank'],2))
            if key in tags:
                raise ValueError('duplicate actual Xtag')
            tags[key]=tag
        for row in s['credit_returns']:
            V.uint(row,16)
            if row in credits or row not in pubs or edge<pubs[row]+credit_min_delay:
                raise ValueError('early/duplicate/unowned visibility credit')
            credits[row]=edge
    if set(pubs)!=set(range(576)) or set(reads)!=set(pubs) or set(credits)!=set(pubs):
        raise ValueError('phase lease cannot release before all publication/consumer/credit debts')
    for row,edge,c in read_refs:
        tag=tags.get((edge+2,c['rank']))
        if tag is None or any(type(tag.get(k)) is not int or tag[k]!=c[k] for k in ('rank','generation','user','xversion','pc','seq')):
            raise ValueError('observed read-aligned Xtag/context missing')
    if last<=max(max(reads.values())+2,max(credits.values())):
        raise ValueError('phase release before final read tag/credit captured fence')
    return dict(verdict='PASS_SUPPLIED_PHASE_EXCLUSION_AND_CONSUMER_ASSOCIATION_ONLY',
        rows=576,first_consumer_read=min(reads.values()),last_consumer_read=max(reads.values()),
        address_lease_release=last,generation_rearm_proved=False,packet_delivery_ACK_proved=False,ingress_source_implementation_qualified=False,
        actual_current_program_enrolled=False,finite_physical_service_bound=None,fulltoken=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.write_text(json.dumps(source_plan(),indent=2,sort_keys=True)+'\n')
