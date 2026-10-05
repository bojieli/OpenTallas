"""New conditional E32 packet/control/level-ACK model; no hardware provider."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path('results/quality/w16_engram_rom_constructive_home_20261001')
DM=(1<<264)-1;TM=(1<<48)-1
def tag(e,c,l,b,lease):
    assert 0<=e<2**32 and 0<=c<24 and l in (0,1) and 0<=b<8 and 0<=lease<64
    return (e<<16)|(c<<11)|(l<<10)|(b<<7)|(1<<6)|lease
def response_encode(data,t):
    assert 0<=data<=DM and 0<=t<=TM
    return [(data&((1<<200)-1))|(t<<200), (data>>200)|(t<<200)|(1<<248)]
def request_encode(word,t):
    assert 0<=word<2**27 and 0<=t<=TM and ((t>>6)&1)
    body=word|((t&65535)<<27);epoch=t>>16
    return [((body>>(16*p))&65535)|(epoch<<16)|(p<<48)|(1<<50) for p in range(3)]
def request_decode(frags,epoch,expected_home):
    if len(frags)!=3:raise ValueError('exactly3 control fragments required')
    body=0
    for p,f in enumerate(frags):
        if not 0<=f<1<<51 or not (f>>50)&1:raise ValueError('request width/REQlevel')
        if ((f>>48)&3)!=p or ((f>>16)&0xffffffff)!=epoch:raise ValueError('phase/epoch')
        chunk=f&65535
        if p==2 and chunk>>11:raise ValueError('request padding')
        body|=chunk<<(16*p)
    word=body&((1<<27)-1);lo=body>>27;t=(epoch<<16)|lo
    col=(lo>>11)&31;layer=(lo>>10)&1;beat=(lo>>7)&7
    if col>=24 or not (lo>>6)&1 or beat!=(word&7):raise ValueError('request identity')
    home=4*(layer*24+col)+((word>>12)>>13)
    if home!=expected_home:raise ValueError('wrong home/shard')
    return word,t
class Hop:
    # EXACT sixresponsecontrol bits: RXphase2, senderFSM2, TXfragphase1, peerACKlevel1.
    # senderFSM IDLE/WAIT_ACK1/WAIT_ACK0 encodes reqlevel/creditlocking.
    def __init__(self,t):
        self.t=t;self.rxphase=0;self.sender=0;self.txphase=0;self.peer_ack=0
        self.first=None;self.word=None
    @property
    def reqlevel(self):return int(self.sender==1)
    def start(self,observed_ack,all_hops_drained,image_context_bound):
        if self.sender!=0 or observed_ack or not all_hops_drained or not image_context_bound:
            raise ValueError('not drained/ACK0/image-bound')
        self.sender=1
    def fragment(self,f):
        if self.sender!=1 or self.rxphase not in (0,1):raise ValueError('not accepting/held word')
        if not 0<=f<1<<256 or f>>249:raise ValueError('response padding')
        phase=(f>>248)&1;t=(f>>200)&TM;data=f&((1<<200)-1)
        if t!=self.t or not (t>>6)&1:raise ValueError('fullE32/tag mismatch')
        if self.rxphase==0:
            if phase:raise ValueError('second before first')
            self.first=data;self.rxphase=1
        else:
            if phase!=1 or data>>64:raise ValueError('duplicate phase/padding')
            self.word=self.first|(data<<200)|(t<<264);self.rxphase=2
    def consume(self):
        if self.rxphase!=2:raise ValueError('not published/already consumed')
        self.rxphase=3;self.peer_ack=1;return self.word
    def observe_ack(self,level):
        if level not in (0,1):raise ValueError('not a level')
        if self.sender==1 and level:
            self.sender=2 # reqlevel drops; CREDIT STILL NOT RELEASED.
        elif self.sender==2 and not level:
            self.sender=0 # returned ACK0 ends this exact physical word lease.
        elif self.sender==0 and level:
            raise ValueError('unexpected stale ACK1 while idle')
    def peer_observe_request(self,level):
        if not level:
            if self.rxphase!=3 or not self.peer_ack:raise ValueError('REQwithdrawn before consume')
            self.peer_ack=0;self.rxphase=0
    def reset(self,all_hops_drained):
        if not all_hops_drained or self.sender!=0 or self.peer_ack or self.rxphase:
            raise ValueError('active reset/no drain')
        # Payload FF remains held; control is idle already. Actual reset provider absent.
def reject(fn):
    try:fn()
    except ValueError:return 1
    raise AssertionError('negative unexpectedly passed')
if __name__=='__main__':
    pin=subprocess.check_output(['git','rev-parse','9b5ca5767'],text=True).strip();path='results/quality/w16_engram_eight_scale_binding_20261001/actual_rows.wire_beats.bin'
    raw=subprocess.check_output(['git','show',pin+':'+path]);assert len(raw)==12672
    oldraw=(ROOT/'repacked_192_enable_mask_contract.json').read_bytes();old=json.loads(oldraw)
    checks=negatives=0;digest=hashlib.sha256()
    for n in range(384):
        row,beat=divmod(n,8);layer,col=divmod(row,24);home=4*(24*layer+col)
        word=beat;data=int.from_bytes(raw[n*33:(n+1)*33],'little')
        for epoch in (7,263,2**31-1,2**32-1):
            t=tag(epoch,col,layer,beat,3);ctrl=request_encode(word,t)
            assert request_decode(ctrl,epoch,home)==(word,t)
            for mutant in (ctrl[:2],list(reversed(ctrl)),[ctrl[0],ctrl[0],ctrl[2]],ctrl[:2]+[ctrl[2]|(1<<15)],[f^(1<<16) for f in ctrl]):
                negatives+=reject(lambda mutant=mutant:request_decode(mutant,epoch,home))
            negatives+=reject(lambda:request_decode(ctrl,epoch,home^1))
            f0,f1=response_encode(data,t);h=Hop(t)
            negatives+=reject(lambda:h.start(1,True,True))
            negatives+=reject(lambda:h.start(0,False,True))
            negatives+=reject(lambda:h.start(0,True,False))
            h.start(0,True,True);h.fragment(f0)
            negatives+=reject(h.consume);negatives+=reject(lambda:h.fragment(f0));negatives+=reject(lambda:h.reset(False))
            negatives+=reject(lambda:h.peer_observe_request(0))
            h.fragment(f1);assert h.peer_ack==0
            negatives+=reject(lambda:h.fragment(f1));negatives+=reject(lambda:h.reset(True))
            got=h.consume();assert got==(data|(t<<264)) and h.peer_ack==1
            negatives+=reject(h.consume)
            h.observe_ack(1);assert h.sender==2 and h.reqlevel==0
            negatives+=reject(lambda:h.start(0,True,True));negatives+=reject(lambda:h.reset(True))
            # Held ACK1 does not generate a second credit.
            h.observe_ack(1);assert h.sender==2
            h.peer_observe_request(h.reqlevel);assert h.peer_ack==0 and h.word==got
            h.observe_ack(0);assert h.sender==0 and h.word==got
            negatives+=reject(h.consume);negatives+=reject(lambda:h.observe_ack(1))
            h.reset(True)
            stale=Hop(t);stale.start(0,True,True)
            negatives+=reject(lambda:stale.fragment(f1))
            negatives+=reject(lambda:stale.fragment(f0|(1<<255)))
            stale.fragment(f0)
            negatives+=reject(lambda:stale.fragment(f1|(1<<100)))
            negatives+=reject(lambda:stale.fragment(f1^(1<<200)))
            negatives+=reject(lambda:stale.fragment(f1^(1<<224)))
            digest.update(got.to_bytes(39,'little'));checks+=1
    # Preserve a concrete legacy E8 alias witness; same low8epoch=7.
    alias=dict(actual_epoch32_A=7,actual_epoch32_B=263,same_low8epoch=7,
        old24tag_equal=True,new48tag_equal=False,
        consequence='E8 alone cannot identify fullgeneration; drainedreuse/provider proof or fullE32 setup is mandatory.')
    assert tag(7,0,0,0,3)!=tag(263,0,0,0,3)
    hops=old['path_geometry']['wire_stage_sum']+8191
    extra=hops*(112+366);homes=[]
    # Keep every old FF/MUX. Explicit new home/session and rowlease state.
    for h in old['homes']:
        homes.append(dict(home_id=h['home_id'],actual_macros=h['actual_macros'],
            preserved_prior_FF_bits=h['total_storage_FF_bits'],
            request_setup_FF_bits=112*hops,response_E32_reassembly_FF_bits=366*hops,
            new_home_image_session_FF_bits=293,new_root_rowlease_FF_bits=92,
            total_storage_FF_bits=h['total_storage_FF_bits']+extra+385,
            feedback_MUX2_bits=h['total_storage_FF_bits']+extra+385,
            preserved_response_MUX2_bits=h['response_MUX2_bits'],request_demux_AND2_bits=h['request_demux_AND2_bits'],
            new_comparator_and_serializer_gate_cells=None))
    out=dict(schema='opentallas.engram.fullE32-control-fragment-levelACK-candidate.v1',
        status='PASS_INTEGER_CODEC_AND_STATE_TESTS_CONDITIONAL_NO_HARDWARE_PROVIDER',
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        source_fixture_pin=dict(commit=pin,path=path,sha256=hashlib.sha256(raw).hexdigest()),
        repacked_enablemask_sha256=hashlib.sha256(oldraw).hexdigest(),
        legacy_E8_alias_witness=alias,prior_a21_duplicateconsume_failure_preserved=True,
        request=dict(logical_bits=75,word_bits=27,tag_bits=48,control_wire_bits=51,setup_beats=3,
            fields='each51controlbeat:payload16[15:0],epoch32[47:16],phase2[49:48],REQlevel/valid1[50]; body43=word27+taglow16; phases0,1,2; last5payloadbitszero',
            checks='FullE32 repeated everycontrolbeat; exact phase/order/padding; targethome=4*(layer*24+column)+(macro15>>13); beat mustequalwordlow3; no free phase or highgeneration sideband.',
            held_level='REQ stays1 after3accepted controlbeats; receiverREADY0 prevents duplicate third acceptance. REQ clears only after storedACK1; source waits storedACK0 before new word/lease.'),
        response=dict(payload_bits=264,tag_bits=48,word_bits=312,fragment_bits=256,fragments=2,
            first='payload200bits0:199;tag48bits200:247;phase0bit248;7zero bits249:255',
            second='payloadhigh64bits0:63;bits64:199 zero;duplicate SAMEtag48bits200:247;phase1bit248;7zero',
            tag='epoch32 +column5 +layer1 +beat3 +valid1 +lease6; shard/row are validated from fullword27 control and locked physical endpoint context',
            cut_tracks=51+256+3,margin_of321=11,
            external_controls='requestREADY1,responsefragmentREADY1,storedwordACKlevel1; valids embedded in respective records'),
        storedACK=dict(protocol='lossless ordered fourphase LEVEL:REQ1 -> complete2fragments -> consumeraccept exactlyonce -> ACK1 -> sourceREQ0 -> peerACK0 -> sourceobservesACK0 -> localwordcreditreleased',
            source_owner_fullrow_rule='All8wordcredits PLUS finalrowconsumeraccept and reverseROWACK/visibility/drain before rowlease reuse; Ram independent rowchecker remains authority.',
            state6='RXphase2 EMPTY/HALF/FULL/DRAIN +senderFSM2 IDLE/WAIT_ACK1/WAIT_ACK0 +TXfragmentphase1 +peerACKlevel1; consumedonce encodedRXDRAIN; no uncounted boolcontrol.',
            stale_pulse_limitation='A21onebit pulse was unbound. E32 metadata alone does not qualify ACKlevels. Orderedlossless registered/CDC paths, allhopACK0/REQ0 and zeroqueue/backend/consumerdrain are mandatory actual provider gates.',
            reset='No reset while currentword/ACK/context islive; changing epoch/image requires全hop/backend/consumerdrain and barriers. Softwaredrain flag is an assumption, NOT an actual sourceproof.'),
        state_inventory=dict(all_physical_hop_endpoints_per_home=hops,homes=homes,
            new_request_state_bits_per_hop=112,new_request_recipe='75requestreassembly +32expectedgeneration +5requestphase/valid/setupguardflags',
            new_response_state_bits_per_hop=366,new_response_recipe='312assembledword +48expectedtag +6exactresponsecontrolFF',
            home_state293='imagehash256 +generation32 +imagevalid1 +sessionarmed1 +draincontroller3',
            row_state92='epoch32 +globalrow29 +layer1 +column5 +shard2 +lease6 +8wordACKbitmap +consumed1 +rowACKpending1 +rowACKreturned1 +drainflags2 +wordcounter4',
            all_old_FF_retained=sum(h['total_storage_FF_bits'] for h in old['homes']),
            aggregate_FF_bits=sum(h['total_storage_FF_bits'] for h in homes),
            all_image_session_row_state_FF_bits=192*385,
            clocks='ALLold+newFF and1500067macroclocks1.2GHzUNGATED; no stop/data/provider credit'),
        runtime=dict(macro_reads_per_lookup=8,request_controlbeats_per_lookup_per_selected_hop=24,
            response_fragments_per_lookup_per_selected_hop=16,wordACK1_edges_per_lookup=8,wordACK0_edges_per_lookup=8,
            root_image_setup_min_51bit_beats=6,root_image_setup_rule='At leastceil256/51=6bits-capacitybeats plus actual framing/order/authentication/drain/session records; six is NOT finalcontrollercalendar.',
            pipeline_and_fourphase_timing_cycles=None,actual_ROOT_PHY_frame_CRC_shared_port=None),
        gate=dict(roundtrip_words=checks,response_fragments=checks*2,request_control_fragments=checks*3,
            negative_rejections=negatives,word312_roundtrip_SHA256=digest.hexdigest(),
            exactlyonce_helddata_and_ACK1_REQ0_ACK0_credit_checked=True,
            fullE32_alias_requestpadding_shard_stalefragment_duplicateconsume_active_reset_checked=True),
        admission_blockers=['Actualimmutablehome image producer/configuration digest isNULL; no fullcheckpoint read',
            'Exactimage32generation/linkordering/CDC/globaldrain provider and completeoperator/rowbinding',
            'Comparator,serializer/controlgate cells and their reset/setup/CTS/PHY costs stillunpriced',
            'New4.36BFF ungated sourcepower and finite3control/2response/fourphase allhop calendar before any hardware',
            'Routedavailable tracks/SSFF, 4.33ps localmacro capture residual and physical endpoint placement'],
        physical_image_binding=None,actual_data_enable_provider=False,actual_drained_epoch_reuse_provider=False,
        L1_generated_source=None,checkpoint_reads=0,RTL_or_PnR_runs=False,physical_admission=False,headline_rate=None)
    target=ROOT/'epoch32_fragment_contract.json';assert not target.exists();target.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(),FF=out['state_inventory']['aggregate_FF_bits'],gate=out['gate'])))
