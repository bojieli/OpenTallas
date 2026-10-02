"""Candidate header144 and source-pinned post-NBA VM publication checker.
No getter, RTL encoder, remote assembly/arbitration or runtime is installed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import dsrom_I66_capture_owner as O
import dsrom_I66_common_gather_proposal as C

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'results/uarch/dsrom_I66_provider_clock_contract_20261002/inputs'
FIELDS=[('generation',32),('operation_sequence',32),('owner_stage',6),
        ('packet_kind',3),('packet_ordinal',3),('payload_bits',18),
        ('rank',2),('user',32),('reserved',16)]
WRITERS=('ww_h','rom','vw_me','vw_su','vw_rd','xs_vm','xs_res','vw_xe','ww_q','ww_x','xa','xb')


def uint(v,w):
    if type(v) is not int or not 0<=v<2**w:
        raise ValueError('unsigned source width')
    return v


def encode(fields):
    if set(fields)!=set(n for n,w in FIELDS):
        raise ValueError('complete144 header fields')
    word=0
    for name,width in FIELDS:
        word=(word<<width)|uint(fields[name],width)
    return word


def decode(word):
    uint(word,144);fields={}
    for name,width in reversed(FIELDS):
        fields[name]=word&((1<<width)-1);word>>=width
    return fields


def source_plan():
    names=('core.sv.txt','tile.sv.txt','runtime_spine.sv.txt')
    pins={n:hashlib.sha256((INPUT/n).read_bytes()).hexdigest() for n in names}
    tile=(INPUT/'tile.sv.txt').read_text()
    needles=['always @(posedge clk) begin','if (X_ROM != 0) begin',
             'if (rom_we[q]) vm[rom_waddr[q*AW +: VM_AW]] <= rom_wdata[32*q +: 32];',
             "if (xa_we) vm[{xa_waddr, 4'(e)}] <= xa_wdata[32*e +: 32];",
             'if (xb_we4[b])',"2'd0: xs_rd_q[32*q +: 32] <= vm[xa[VM_AW-1:0]];"]
    if not all(n in tile for n in needles):
        raise ValueError('publication or read source changed')
    return dict(source_sha256=pins,scope='SOURCE_PINNED_CALLBACK_PLAN_AND_SOFTWARE_CHECK_ONLY',
        candidate_header_bits=sum(w for n,w in FIELDS),reserved_bits_retained=16,
        user_bits=32,old_command_bits=221,new_command_bits=237,
        header_flits_at256=1,command_flits_at256=1,
        original_TX_RX_MAX_FLITS=256,original_CRC_function_unchanged=True,
        codec_metadata_comparator_replay_control_cost=None,
        header_delta_bits_per_disjoint_live_metadata_copy=16,
        command_delta_bits_per_disjoint_staging_copy=16,
        compiled_encoder_or_collector=False,
        header_fields_MSB_to_LSB=FIELDS,
        supersedes_header_alternative_only="b35f4479beec117896a314222dcb4cde53cf9957",
        visibility_credit_policy="actual VMvisible then positive captured return; no downstream lease assumption",
        proposed_common_owner=C.proposal()["common_control_owner_proposed"],
        gather_owner=C.proposal()["gather_owner_proposed"],
        C=None,stations=None,register_calendar=None,
        source_whole_header_flit_policy=dict(header_bits=144,header_flits=1,max_payload_flits=255,
            input5120words_packet_flits=[256,256,131],result576writer63_packet_flits=143,
            proposed_packet_shapes_unchanged=True,actual_codec_CRC_service_qualified=False),
        native_callback=dict(hierarchy='dut.u_tile',
            preedge='snapshot every enabled VM write after source mask/port/address expansion, plus producer context and raw row; record old VM reads separately',
            local_write='X_ROM!=0 && rom_we[q]; full address rom_waddr[q*AW+:AW], data rom_wdata[32*q+:32]',
            postNBA='after the same rising-edge eval has settled: inspect vm[resolved_address]; same edge plus explicit postNBA ordinal',
            collector_resolution='same native clock; no prediction, new eval, getter, or hardware debug port',
            no_hardware_write_reset_gate=True,
            healthy_epoch='rst_n/synchronizedreset accepted and matching generation required for healthy callback; does not claim tile write always block is reset-gated',
            sampled_writer_classes=list(WRITERS),
            collisions='reject overlapping enabled writers even when data equal; final contents alone cannot prove ownership',
            address='VM19 alias rejection at observer: raw full address must equal resolved address',
            error='source error can still write; observation must not label it healthy',
            source_link='u_core.g_rom.u_spine registered w_we/w_addr/w_data -> tile rom_we/rom_waddr/rom_wdata -> vm NBA',
            remote_path='xa/xb existing512 ports are concrete write points, not an implemented exclusive gather provider',
            block_write='xa/xb eachwrite16words without mask; observe all16 and every competing writer; lease/assembly/arbitration must be source-owned and priced'),
        credit_release='only this matched actual visibility observation plus positive captured return; packetACK cannot substitute',
        current_enrollment='current PHW10 source/binary/fourprogram/field+compiled callback closure and actual journal required separately',
        actual_current_journal=None,actual_consumer_deadline=None,new_jobs=False,RTL_GO=False)


def visible_callback(snapshot, publication):
    """Pure preedge/postNBA association; does not grant source qualification."""
    uint(snapshot['edge'],64)
    expected={'X_ROM':1,'ROM_R':128,'SUN':256,'ROM_PHW':10,'ROM_FBW':1632}
    if any(uint(snapshot['parameters'].get(k),32)!=v for k,v in expected.items()):
        raise ValueError('current PHW10 callback geometry')
    if (snapshot['pre_stage']!='preedge' or snapshot['post_stage']!='postNBA' or
        uint(snapshot['post_edge'],64)!=snapshot['edge']):
        raise ValueError('same source edge pre/postNBA required')
    if snapshot['sampled_writer_classes']!=list(WRITERS):
        raise ValueError('complete source writer closure required')
    if snapshot['reset_accepted'] is not True or snapshot['healthy'] is not True:
        raise ValueError('healthy synchronized reset epoch required')
    O.identity(publication['context']);O.identity(snapshot['context'])
    uint(publication['writer_port'],16)
    if publication['context']!=snapshot['context']:
        raise ValueError('publication stale context')
    row=uint(publication['row'],16)
    if row>=576 or uint(publication['physical_shard'],1)!=((row%256)//2)//64:
        raise ValueError('physical row owner')
    address=uint(publication['address'],19);data=uint(publication['data'],32)
    collisions=[]
    for w in snapshot['writes']:
        if w['kind'] not in WRITERS:
            raise ValueError('unknown VM writer')
        full=uint(w['address'],30);uint(w['data'],32);uint(w['port'],16)
        if full%(2**19)==address:
            collisions.append(w)
    # These source ports have no word mask. A flattened sample must retain
    # the full16-word block, even when only one row is being associated.
    for kind in ('xa','xb'):
        ports={w['port'] for w in snapshot['writes'] if w['kind']==kind}
        for port in ports:
            if (kind=='xa' and port!=0) or (kind=='xb' and not 0<=port<4):
                raise ValueError('external source port index')
            words=[w['address'] for w in snapshot['writes'] if w['kind']==kind and w['port']==port]
            base=min(words)//16*16
            if len(words)!=16 or sorted(words)!=list(range(base,base+16)):
                raise ValueError('unmasked source512 write must retain all16 words')
    if len(collisions)!=1:
        raise ValueError('not exclusively owned write')
    chosen=collisions[0]
    if chosen['address']!=address:
        raise ValueError('raw19 VM address alias')
    if chosen['kind']!=publication['writer_kind'] or chosen['port']!=publication['writer_port'] or chosen['data']!=data:
        raise ValueError('accepted writer/row association differs')
    if chosen['kind']=='rom' and row%256//2!=chosen['port']:
        raise ValueError('local root port mismatch')
    if uint(snapshot['post_VM'].get(str(address)),32)!=data:
        raise ValueError('postNBA VM value not visible')
    return dict(kind='home_postNBA',edge=snapshot['edge'],row=row,address=address,data=data,
                identity=publication['context'],physical_shard=publication['physical_shard'],
                source_runtime_enrolled=False,remote_lease_qualified=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.write_text(json.dumps(source_plan(),indent=2,sort_keys=True)+'\n')
