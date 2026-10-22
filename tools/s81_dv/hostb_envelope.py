#!/usr/bin/env python3
"""HBE1 software field codec for the actual legacy HOST and KS input wires.

Every routing/context/date field is supplied explicitly. This codec does not
provide a HOST producer, armed epoch, stage programme anchor, safe head pacing,
or physical circuit. HBE1 version2 uses ROOT-selected CRC32C plus an exact
receiver-local body capture edge; CRC is bounded error detection, not a proof
against every collision/substitution. A preview cannot qualify delivery.
"""
from dataclasses import dataclass, asdict
from fractions import Fraction
import argparse
import hashlib
import json
from pathlib import Path

from ks_descriptor import fixture_word, validate as validate_ks

MAGIC = 0x31454248
VERSION = 2
HOST_WORD, KS_DESCRIPTOR, ARM, STAGE_RETURN = range(4)
LENGTHS = {HOST_WORD: 514, KS_DESCRIPTOR: 53, ARM: 0, STAGE_RETURN: 131}
FIELDS = dict(magic=(0,32), version=(32,4), opcode=(36,4), stage_id=(40,8),
              rank=(48,2), transaction_id=(50,16), body_bits=(66,10), host_class=(76,2),
              user=(78,10), position=(88,21), token=(109,21), epoch_identity=(130,32),
              date48=(162,48), programme_id64=(210,64), inline=(274,238))
G8_KIT_SOURCE = dict(
    seqhost_sha256='8af2dd4720c27e883180cc5e3262715bc6323899bbc616572a630fe680669bce',
    issuer_sha256='6c77b4c5d7f2e84da15089bc5e0f94abedc5b7a4f772cc911a8193aee80d0a3f')


def uint(name, value, width):
    if type(value) is not int or not 0 <= value < 1 << width:
        raise ValueError(f'{name} requires an explicit unsigned {width}-bit integer')
    return value


@dataclass(frozen=True)
class Context:
    stage_id: int
    rank: int
    transaction_id: int
    user: int
    position: int
    token: int
    epoch_identity: int
    programme_id64: int

    def __post_init__(self):
        for name, value in asdict(self).items():
            uint(name, value, FIELDS[name][1])
        if self.stage_id > 240:
            raise ValueError('HBE1 stage ID must name an explicit S000..S240 strap')


def pack_header(context, *, opcode, host_class, date48, inline):
    if opcode not in LENGTHS:
        raise ValueError('unassigned HBE1 opcode')
    values = dict(asdict(context), magic=MAGIC, version=VERSION, opcode=opcode,
                  body_bits=LENGTHS[opcode], host_class=host_class,
                  date48=date48, inline=inline)
    word = 0
    for name, value in values.items():
        lo, width = FIELDS[name]
        word |= uint(name, value, width) << lo
    return word


def decode_header(word):
    uint('HFWD payload', word, 512)
    fields = {name:(word >> lo)&((1 << width)-1) for name,(lo,width) in FIELDS.items()}
    if fields['magic'] != MAGIC or fields['version'] != VERSION:
        raise ValueError('HBE1 magic/version mismatch')
    op = fields['opcode']
    if op not in LENGTHS or fields['body_bits'] != LENGTHS[op]:
        raise ValueError('HBE1 opcode/length mismatch')
    context = Context(**{k:fields[k] for k in Context.__dataclass_fields__})
    inline = fields['inline']
    if op != HOST_WORD and fields['host_class'] != 0:
        raise ValueError('inline opcode has nonzero reserved HOST class')
    if op == HOST_WORD and inline >> 32:
        raise ValueError('HOST CRC32C field has nonzero reserved upper inline bits')
    if op == KS_DESCRIPTOR:
        if inline >> 56 or (inline >> 53)&7 > 5:
            raise ValueError('KS slot/reserved field mismatch')
        validate_ks(inline & ((1 << 53)-1), user=context.user, token=context.token, position=context.position)
    if op == ARM and inline >> 6:
        raise ValueError('ARM inline field exceeds selection mask6')
    if op == STAGE_RETURN and inline >> 131:
        raise ValueError('RETURN inline reserved bits are nonzero')
    return fields


def check_context(fields, expected):
    if any(fields[k] != v for k,v in asdict(expected).items()):
        raise ValueError('HBE1 stage/rank/transaction/context/epoch/programme identity mismatch')


def validate_g8_walk_return(fields, *, seqhost_sha256, issuer_sha256):
    """Specific G8 producer: tokens[slot] -> kit_tok -> {valid,tok21,zero32}.

    No context is reconstructed from KIT. Header user/position still come from
    the admitted descriptor. This source does not encode either in t_kd; a
    future MU producer needs its own exact source-bound return contract.
    """
    if dict(seqhost_sha256=seqhost_sha256,issuer_sha256=issuer_sha256)!=G8_KIT_SOURCE:
        raise ValueError('RETURN producer is not this exact G8 walk/seqhost source contract')
    if fields['opcode']!=STAGE_RETURN:
        raise ValueError('KIT return validator requires STAGE_RETURN')
    kd=fields['inline']>>77
    if kd>>53 and (((kd>>32)&((1<<21)-1))!=fields['token'] or kd&0xffffffff):
        raise ValueError('actual G8 KIT token/padding differs from admitted descriptor contract')
    return dict(contract='G8_WALK_TOKENS_SLOT',source=G8_KIT_SOURCE,
                raw_t_host77=fields['inline']&((1<<77)-1),raw_t_kd54=kd,
                user_position_encoded_in_KIT=False,runtime_provenance_qualified=False)


def crc32c(data):
    """Reflected CRC32C: poly82f63b78, init/finalxor ffffffff, byte LSB first."""
    crc=0xffffffff
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc=(crc >> 1) ^ (0x82f63b78 if crc & 1 else 0)
    return crc ^ 0xffffffff


def host_word(legacy515, context, *, body_capture_edge):
    uint('legacy HOST {class2,data512,valid}', legacy515, 515)
    if not legacy515 & 1:
        raise ValueError('inactive legacy HOST word must not become an active HFWD write')
    uint('exact receiver-local body_capture_edge', body_capture_edge, 48)
    cls = legacy515 >> 513
    data = (legacy515 >> 1)&((1 << 512)-1)
    crc=crc32c(data.to_bytes(64,'little'))
    header = pack_header(context, opcode=HOST_WORD, host_class=cls, date48=body_capture_edge, inline=crc)
    return [header,data]


def ks_word(raw53, slot, context, *, deadline):
    validate_ks(raw53, user=context.user, token=context.token, position=context.position)
    uint('KS slot', slot, 3)
    if slot > 5:
        raise ValueError('KS slot must select one actual six-position starter slot')
    return inline_word(KS_DESCRIPTOR, raw53 | slot << 53, context, deadline=deadline)


def arm_word(mask6, context, *, deadline):
    uint('ARM active-slot selection mask', mask6, 6)
    return inline_word(ARM, mask6, context, deadline=deadline)


def return_word(t_host77, t_kd54, context, *, deadline):
    uint('actual t_host', t_host77, 77); uint('actual t_kd', t_kd54, 54)
    return inline_word(STAGE_RETURN, t_host77 | t_kd54 << 77, context, deadline=deadline)


def inline_word(opcode, inline, context, *, deadline):
    uint('inline deadline', deadline, 48)
    if opcode == HOST_WORD:
        raise ValueError('HOST must have a raw512 body')
    word = pack_header(context, opcode=opcode, host_class=0, date48=deadline, inline=inline)
    decode_header(word)
    return word


def decode_stream(records, expected, *, return_contract=None):
    """Track pairs even for a header-shaped raw body. Never magic-reinterpret it.

    Input dates are actual receiver-local captures, never head emission dates.
    CRC/slot/context failure occurs before emitting a decoded legacy word.
    """
    out=[]; pending=None; previous=-1
    for edge, word in records:
        uint('record edge', edge, 48); uint('HFWD payload', word, 512)
        if edge <= previous:
            raise ValueError('HFWD slots must be explicit, unique and strictly increasing')
        previous=edge
        if pending is not None:
            if edge != pending['date48']:
                raise ValueError('HOST body missed its exact receiver-local capture edge')
            if crc32c(word.to_bytes(64,'little')) != pending['inline']:
                raise ValueError('HOST raw512 CRC32C mismatch before legacy write')
            out.append(dict(opcode=HOST_WORD, context={k:pending[k] for k in asdict(expected)},
                            legacy515=(pending['host_class'] << 513) | (word << 1) | 1))
            pending=None
            continue
        fields=decode_header(word); check_context(fields,expected)
        if edge > fields['date48']:
            raise ValueError('inline/header message missed its explicit deadline')
        if fields['opcode']==HOST_WORD:
            pending=fields
        else:
            if fields['opcode']==STAGE_RETURN:
                if return_contract is None:
                    raise ValueError('RETURN consumption requires an explicit producer source contract')
                fields['producer_source_validation']=validate_g8_walk_return(fields,**return_contract)
            out.append(fields)
    if pending is not None:
        raise ValueError('stream ended with a missing HOST body')
    return out


def wire_cost(records):
    # Wire-only lower bound. No head holding, hop, landing or receiver latency
    # is supplied by this fraction; caller-booked slots remain mandatory.
    cap = Fraction(456,596)*Fraction(1023,1024)
    lower = Fraction(records,1)/cap
    return dict(records=records, ring_beats=records,
                reliable_wire_cap=dict(numerator=cap.numerator,denominator=cap.denominator),
                minimum_wire_cycles=(lower.numerator+lower.denominator-1)//lower.denominator,
                qualification='WIRE_ONLY_LOWER_BOUND; head spacing/route/receiver/clock/calendar UNQUALIFIED')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def transit_book(route, bookings, context, *, has_body):
    """Bind each transit adapter's own counter slots, never destination dates.

    A nonlocal HOST header latches transit_body_edge48 at that adapter. Its
    wire date48 remains the destination-local body edge and is never rewritten.
    """
    if len(route) != len(bookings):
        raise ValueError('every nonlocal adapter requires its own explicit slot book')
    out=[]
    for adapter,slots in zip(route,bookings):
        for key in ('adapter_id','receiver_clock_identity','source_sha256'):
            if not isinstance(adapter.get(key),str) or not adapter[key]:
                raise ValueError('transit adapter identity/clock/source must be explicit')
        digest=adapter['source_sha256']
        if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('transit adapter requires an exact source SHA256')
        if adapter.get('configured') is not True or adapter.get('expected_header_stage') != context.stage_id:
            raise ValueError('HOST/KS transit requires configured destination-stage contract')
        if slots.get('adapter_id') != adapter['adapter_id']:
            raise ValueError('transit slot book names the wrong adapter')
        uint('transit receiver_header_edge',slots['receiver_header_edge'],48)
        uint('transit header_slot',slots['header_slot'],48)
        if slots['header_slot'] != slots['receiver_header_edge']:
            raise ValueError('transit header must match its exact receiver-local header slot')
        if has_body:
            uint('transit_body_edge',slots['transit_body_edge'],48)
            if slots['transit_body_edge'] <= slots['receiver_header_edge']:
                raise ValueError('transit body must follow its header in the same adapter counter')
        out.append(dict(adapter=adapter,slots=slots))
    return out


def encode_boot(boot_words, context, host_slots, *, ks53, ks_slots,
                starter_words=None, starter_slots=None, arm_slots=None, transit_route=()):
    """Produce HFWD payloads with separately supplied head/receiver slot books.

    No latency or clock-origin offset is inferred between those two books.
    Receiver-local slots are used only to validate codec roundtrip/CRC fields.
    """
    words=list(boot_words);book=list(host_slots)
    if starter_words is not None:
        if len(starter_words)!=2 or starter_slots is None or len(starter_slots)!=2 or arm_slots is None:
            raise ValueError('real SYNC/ARM requires both full legacy CSR words, their bookings and separate inline selection')
        for word,opcode in zip(starter_words,(0x19,0x17)):
            uint('real starter legacy CSR',word,515)
            if not word&1 or word>>513 != 0 or (word>>1)&255 != opcode:
                raise ValueError('starter words must preserve class0 full512 SYNC0x19 then ARM0x17')
        words+=list(starter_words);book+=list(starter_slots)
    elif starter_slots is not None or arm_slots is not None:
        raise ValueError('inline ARM mask cannot replace the real SYNC/ARM CSR contract')
    if len(words) != len(book):
        raise ValueError('every legacy word requires its own explicit two-record slot booking')
    emitted=[]; arrivals=[]
    for index,(legacy,slots) in enumerate(zip(words,book)):
        required=('head_header_edge','head_body_edge','receiver_header_edge','receiver_body_capture_edge')
        for name in required:
            uint(name,slots[name],48)
        if slots['head_header_edge'] >= slots['head_body_edge'] or slots['receiver_header_edge'] >= slots['receiver_body_capture_edge']:
            raise ValueError('HOST pair must be atomic and ordered in both named counter domains')
        transits=transit_book(transit_route,slots.get('transit',[]),context,has_body=True)
        pair=host_word(legacy,context,body_capture_edge=slots['receiver_body_capture_edge'])
        for part,(source,capture,payload) in enumerate(zip(
                [slots['head_header_edge'],slots['head_body_edge']],
                [slots['receiver_header_edge'],slots['receiver_body_capture_edge']],pair)):
            emitted.append(dict(head_edge=source,receiver_capture_edge=capture,
                opcode='HOST_WORD',word_index=index,part=part,expected_header_stage=context.stage_id,
                destination_header_slot=slots['receiver_header_edge'],transit_slot_books=transits,payload512=f'{payload:0128x}'))
            arrivals.append((capture,payload))
    if arm_slots is not None:
        for name in ('head_edge','receiver_edge','deadline','mask6'):
            uint(name,arm_slots[name],6 if name=='mask6' else 48)
        payload=arm_word(arm_slots['mask6'],context,deadline=arm_slots['deadline'])
        emitted.append(dict(head_edge=arm_slots['head_edge'],receiver_capture_edge=arm_slots['receiver_edge'],
                            opcode='ARM_SELECTION_ONLY',expected_header_stage=context.stage_id,destination_header_slot=arm_slots['receiver_edge'],transit_slot_books=transit_book(transit_route,arm_slots.get('transit',[]),context,has_body=False),payload512=f'{payload:0128x}'))
        arrivals.append((arm_slots['receiver_edge'],payload))
    for name in ('head_edge','receiver_edge','deadline','slot'):
        uint(name,ks_slots[name],3 if name=='slot' else 48)
    payload=ks_word(ks53,ks_slots['slot'],context,deadline=ks_slots['deadline'])
    emitted.append(dict(head_edge=ks_slots['head_edge'],receiver_capture_edge=ks_slots['receiver_edge'],
                        opcode='KS_DESCRIPTOR',expected_header_stage=context.stage_id,destination_header_slot=ks_slots['receiver_edge'],transit_slot_books=transit_book(transit_route,ks_slots.get('transit',[]),context,has_body=False),payload512=f'{payload:0128x}'))
    arrivals.append((ks_slots['receiver_edge'],payload))
    if any(a['head_edge'] >= b['head_edge'] for a,b in zip(emitted,emitted[1:])):
        raise ValueError('head slots overlap/interleave or reorder a HOST pair')
    decoded=decode_stream(arrivals,context)
    restored=[r['legacy515'] for r in decoded if r['opcode']==HOST_WORD]
    if restored != words:
        raise ValueError('exact legacy class/data/valid roundtrip differs')
    return emitted


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--boot-memh',type=Path,required=True)
    p.add_argument('--metadata',type=Path,required=True,
        help='explicit context + epoch_source/clock identities + programme source SHA/anchor status; no defaults')
    p.add_argument('--slots',type=Path,required=True,
        help='417 HOST two-record head/receiver bookings plus KS booking, in explicit counter domains')
    p.add_argument('--fixture-meta',type=Path,required=True)
    p.add_argument('--starter-csr-memh',type=Path,
                   help='two actual full legacy515 SYNC0x19/ARM0x17 words; never synthesized from mask6')
    p.add_argument('--plan',type=Path,required=True,help='ROOT-selected HBE1v2 source contract to pin')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():
        raise ValueError('preserve prior envelope; select a fresh output directory')
    compact=''.join(a.plan.read_text().lower().split())
    if 'version2' not in compact and 'version=2' not in compact:
        raise ValueError('requires the ROOT-selected HBE1 version2 plan, not the superseded v1 framing')
    meta=json.loads(a.metadata.read_text());slots=json.loads(a.slots.read_text())
    for key in ('epoch_source','head_clock_identity','receiver_clock_identity','counter_units','programme_metadata','route_metadata'):
        if key not in meta or not meta[key]:
            raise ValueError('required explicit metadata missing: '+key)
    route=meta['route_metadata']
    if not isinstance(route.get('transit_adapters'),list) or not route.get('source_model_qualification'):
        raise ValueError('route requires explicit transit_adapters (empty only for local proof) and source MODEL qualification')
    programme=meta['programme_metadata']
    if 'first_command_anchor' not in programme or 'anchor_qualification' not in programme:
        raise ValueError('programme anchor/status must be explicit; null with OPEN is allowed, no anchor is synthesized')
    if programme['first_command_anchor'] is None and not str(programme['anchor_qualification']).startswith('OPEN'):
        raise ValueError('absent first-command anchor must remain explicitly OPEN')
    if programme['source_sha256'] != sha(a.boot_memh):
        raise ValueError('programme identity does not name this exact boot source')
    context=Context(**meta['context'])
    destination=route.get('destination_adapter') or {}
    if destination.get('receiver_clock_identity') != meta['receiver_clock_identity']:
        raise ValueError('destination adapter must bind the named receiver clock')
    first=slots['host_words'][0]
    transit_book([destination],[dict(adapter_id=destination.get('adapter_id'),
        receiver_header_edge=first['receiver_header_edge'],header_slot=first['receiver_header_edge'],
        transit_body_edge=first['receiver_body_capture_edge'])],context,has_body=True)
    words=[int(s,16) for s in a.boot_memh.read_text().split()]
    if len(words)!=417:
        raise ValueError('bounded existing entry producer requires exactly417 legacy HOST words')
    fixture=json.loads(a.fixture_meta.read_text())
    rawks=fixture_word(fixture,user=context.user)
    validate_ks(rawks,user=context.user,token=context.token,position=context.position)
    starter=None
    if a.starter_csr_memh:
        starter=[int(s,16) for s in a.starter_csr_memh.read_text().split()]
        if programme.get('starter_csr_source_sha256') != sha(a.starter_csr_memh):
            raise ValueError('real SYNC/ARM CSR source identity is required explicitly')
    records=encode_boot(words,context,slots['host_words'],ks53=rawks,ks_slots=slots['ks'],
                        starter_words=starter,starter_slots=slots.get('starter_words'),arm_slots=slots.get('arm'),
                        transit_route=route['transit_adapters'])
    a.out.mkdir(parents=True)
    (a.out/'hfwd512.memh').write_text(''.join(r['payload512']+'\n' for r in records))
    receipt=dict(schema='opentallas.s81.hbe1v2.boot_codec.v1',
        status='SOURCE_CODEC_ROUNDTRIP_ONLY_NOT_HOST_DELIVERY',header_version=VERSION,
        context=asdict(context),metadata=meta,legacy_boot_words=417,
        real_sync_arm_CSR_words=2 if starter is not None else 0,ks53=f'{rawks:014x}',
        source_sha256=dict(boot=sha(a.boot_memh),metadata=sha(a.metadata),slot_book=sha(a.slots),
                          fixture_meta=sha(a.fixture_meta),plan=sha(a.plan),codec=sha(__file__)),
        records=records,cost=wire_cost(len(records)),
        crc32c='poly82f63b78 reflected/initffffffff/finalxorffffffff;64 raw body bytes little-endian',
        date48='HOST exact destination-receiver-local body capture; inline opcodes explicit arrival deadline',
        transit_body_edge='Required separate per-adapter receiver-local HOST body capture; never inferred from destination date48',
        route_pipeline_qualification='SOURCE MODEL only; explicit slot books do not prove phase, pacing or physical latency',
        reserved_inline='HOST CRC32C32, KS raw53+slot3, ARM selection6, RETURN raw t_host77+t_kd54',
        real_sync_arm_CSRs='Full class0 0x19/0x17 must be separately supplied HOST_WORDs; inlineARM cannot replace them',
        body_integrity='bounded CRC error detection, not universal collision/substitution proof',
        actual_starter_armed_proved=False,global_programme_anchor_bound=False,receiver_pipeline_measured=False,
        head_safe_spacing_qualified=False,runtime_provenance_qualified=False,full_stage=False,full_token=False)
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
    print('HBE1V2_CODEC417_HOST+KS',len(records),'HFWD records; source codec only, actual producer/epoch/anchor OPEN')


if __name__=='__main__':
    main()
