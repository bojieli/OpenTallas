#!/usr/bin/env python3
"""Compare priced protection candidates; no production consumer binding claimed."""
import hashlib,json,math
from hbm_result_relay_model import ROOT,hbm_result_relay_stage_model
POLY=0x1EDC6F41

def crc32c(value,width=286):
    crc=0
    for bit in range(width-1,-1,-1):
        feedback=((crc>>31)^((value>>bit)&1))&1
        crc=((crc<<1)&0xffffffff)^(POLY if feedback else 0)
    return crc

def protection_options():
    base=hbm_result_relay_stage_model();depth=base['balanced_latency_cycles']
    columns=[crc32c(1<<i)for i in range(286)]
    masks=[sum(1<<i for i,c in enumerate(columns)if(c>>j)&1)for j in range(32)]
    active_chunks=[[((m>>(36*k))&((1<<36)-1)).bit_count()for k in range(8)]for m in masks]
    xor_encoder=sum(max(n-1,0)for row in active_chunks for n in row)+32*(6+1)
    max_stage1_depth=max(math.ceil(math.log2(n))if n>1 else 0 for row in active_chunks for n in row)
    ff=.37908;xor=.13122;small=.08748
    encoder_ff=3*286+32*(8+2+1)+34
    # Two independently retained checker lanes carry the whole encoded frame.
    # Final control/identity state is duplicated. Actual gate cone and release
    # binding must be checked; this is a resource envelope, not RTL proof.
    # Fourth stage retains the complete frame through final comparison.
    checker_lane_ff=4*318+32*(8+2+1)
    control_ff=2*(16+math.ceil(math.log2(depth+8))+1)
    checker_ff=2*checker_lane_ff+control_ff
    encoder_raw=encoder_ff*ff+(xor_encoder+48)*xor+51*small
    checker_raw=checker_ff*ff+2*(xor_encoder+32+16)*xor+(2*31+64)*small
    syndrome_columns=columns+[1<<i for i in range(32)]
    assert len(set(syndrome_columns))==318 and all(syndrome_columns)
    return dict(schema='opentallas.hbm_result_relay_protection_options.v1',selected=False,
      status='modeled-options-not-production-RTL-or-consumer-qualified',
      source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'tools/hbm_result_relay_protection_model.py',ROOT/'tools/hbm_result_relay_model.py',ROOT/'results/uarch/hbm_result_relay_stage_20261007/result_paths.json']},
      crc_candidate=dict(polynomial_hex='1edc6f41',direction='MSB-first',initial_crc=0,final_xor=0,
        frame_layout='payload270 atbits0..269;beatsequence16 at270..285;CRC32 at286..317',
        covered_fields=['rv','rrow12','rdata256','fault','beatsequence16'],
        frame_bits=318,hard_slices_per_leaf=6,physical_transport_register_bits=base['physical_register_bits'],
        useful_encoded_register_bits=32*318*depth,padding_register_bits=base['physical_register_bits']-32*318*depth,
        wire_bits_per_cycle_per_leaf=318,wire_increase_fraction=48/270,
        encoder_latency_cycles=3,checker_latency_cycles=4,
        candidate_total_transport_cycles=depth+7,extra_latency_ps_per_traversal=7*base['period_ps'],
        encoder_matrix_xor2_count_upper=xor_encoder,encoder_stage_logic_depths=[max_stage1_depth,2,1],
        encoder_FF_bits=encoder_ff,duplicated_checker_FF_bits=checker_ff,
        encoder_raw_area_proxy_um2=encoder_raw,checker_raw_area_proxy_um2=checker_raw,
        encoder_area_at55pct_um2=encoder_raw/.55,checker_area_at55pct_um2=checker_raw/.55,
        all32_encoder_checker_area_at55pct_um2=32*(encoder_raw+checker_raw)/.55,
        area_scope='nativeasyncFF andTT XOR/AND/OR library area proxy; clock/reset buffering,routing andphysicalcut cost notmeasured',
        idle_rule='encodeeverycycle includingrv0; never gateCRCvalidation on receivedrv',
        reset_rule='zero frame is legalidle; checked local duplicatedfill count establishesexpectedsequence; payloadrv cannot waivecheck',
        identity_rule='16bitsequence increments everycycle; expectedsequence andfill counters duplicated; mismatch inhibitsconsumption',
        replay_limit='modulo65536 identity only; stale replay at exact65536-cycle distance can alias. Production requires a bounded lifetime below65536 cycles or a wider epoch priced separately',
        error_rule='either checker mismatch/identity mismatch/duplicatedcontrol mismatch sets persistentfault andinhibits actualconsumer release',
        consumer_binding='OPEN:encoded318bitframes must survive gather/storage to actualSU consumption; strippingCRC beforeoldgather is insufficient',
        downstream_width_change='all affectedgather trunk widths andviews need successor318/270pricing andqualification',
        spatial_mapping_gate='OPEN: metadata placement changes real per-slice wire demand andclearance; spare64bit storage doesnot prove existingpayload routes legal. Encoder270bitfanin andcheckerreassembly require legalactualpinroutes',
        normal_arithmetic='payloadbits andlogicalordering unchanged; onlyacceptedtiming shifts',
        matrix_masks_hex=[f'{m:072x}'for m in masks],
        analytic_single_and_double_bit_detection=True,
        coverage_limit='linearCRC guarantees checkedsingle/doublebiterror syndromes for318bitcodeword; notarbitrarymulti-error correction'),
      per_stage_parity_candidate=dict(payload_bits=64,parity_bits=1,error_rails=2,physical_bits_per_stage=67,
        extra_transport_FF_bits=3*base['station_replica_count'],extra_die_boundary_bits_per_leaf=3*6,
        checker_xor2_count_per_stage=63,extra_xor2_count_die=63*base['station_replica_count'],
        added_cell_area_proxy_um2=base['station_replica_count']*(3*ff+63*xor),
        scope='singlebitdetection only; evenweightcorruptions canescape; duplicatederrorrails mustreachcheckedconsumer; notselected'),
      physical_duplicate_candidate=dict(required_payload_andchecksum_transport_factor=2,
        extra_FF_bits=base['physical_register_bits'],extra_slot_area_um2=base['total_reserved_station_slot_area_um2'],
        scope='independentphysicalroutes/storage pluscheckedfinalcompare; commonmodeinputfaults requireupstreamchecks; notselected'),
      area_cell_provenance=dict(liberty_corner='TT forstructuralareaonly',async_FF='DFFASRHQNx1_ASAP7_75t_R',FF_um2=ff,
        XOR2='XOR2xp5_ASAP7_75t_R',XOR2_um2=xor,AND_OR2_um2=small),
      required_gates=['bind actualconsumerrelease andprotectederrorboundary beforeproductionRTL adoption',
        'model allencodedgather successors and legalencoder/checker floorplan slots beforebuild',
        'retainindependentchecker/control copies throughproductionmapping; faultinjection atallstorage/metadata/control boundaries',
        'unconditionalidle/reset/validflip,sequence/replay,checksum andfaultflag negatives',
        'prove bounded frame lifetime and reset epoch synchronization; modulo sequence is not unlimited replay protection',
        'source-pinnedSS/FF15psDRC0 andfulltraffic/globalreplicatedfit; recompose tokenlatency,energy andsilicon'])

if __name__=='__main__':print(json.dumps(protection_options(),indent=2))
