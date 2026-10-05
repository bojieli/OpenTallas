#!/usr/bin/env python3
"""Independent bounded review of Ram CROM and partial dispatch compositions."""
import argparse
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import re
import subprocess
import w17_dispatch_alternatives as A
import w17_whole_dsrom_candidate as W

ROOT=Path(__file__).resolve().parents[1]
DISPATCH=('c8468d3f7be2b1e7a340d5c23b8ff936d2b94cb8','results/quality/w16_w17_dispatch_alternatives_20261001/comparison.json')
WHOLE=('64c6bffe0442cdf9126a6eaac752591b6a8e8389','results/quality/w16_w17_whole_dsrom_candidate_20261001/candidate.json')
TURING=('0043d810f6df6a0166e8002a5b419fd61d017d38','results/uarch/w16_expert_dispatch_costs_20261001/dispatch_r1.json')
LEF='physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.lef'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def blob(pin):return subprocess.check_output(['git','show',pin[0]+':'+pin[1]],cwd=ROOT)


def need(ok,msg):
    if not ok:raise ValueError(msg)


def validate_pins(pins):
    checked=[]
    for p in pins.values():
        need(sha(blob((p['commit'],p['path'])))==p['sha256'],'owner source pin mismatch '+p['path'])
        checked.append(p)
    return checked


def build():
    raw={k:blob(p) for k,p in [('dispatch',DISPATCH),('whole',WHOLE),('Turing',TURING)]}
    a=json.loads(raw['dispatch']);w=json.loads(raw['whole']);t=json.loads(raw['Turing'])
    for pin,path in [(DISPATCH[0],'tools/w17_dispatch_alternatives.py'),(WHOLE[0],'tools/w17_whole_dsrom_candidate.py')]:
        need((ROOT/path).read_bytes()==blob((pin,path)),'review requires exact owner source '+path)
    need((json.dumps(A.build(),indent=2)+'\n').encode()==raw['dispatch'],'Ram dispatch serialized source replay differs')
    need((json.dumps(W.build(),indent=2,sort_keys=True)+'\n').encode()==raw['whole'],'Ram whole candidate serialized source replay differs')
    checked=validate_pins(a['source_pins'])+validate_pins(w['source_pins'])
    for p,h in t['source_pins'].items():need(sha(blob((t['evidence_commit'],p)))==h,'frozenTuring source pin mismatch '+p)
    c=w['constants'];home=c['selected_minimal_home'];required=508800+40960
    need(required==c['resulting_required_words']==549760,'CROM producer extent arithmetic')
    need(required-2**19==25472==c['aperture_excess_words'],'oldaperture overflow')
    containers=(required+2)//3
    need(containers==183254==home['containers_needed'],'CROM container count')
    need(44*4096*3<required<=45*4096*3 and home['physical_4096x274_banks']==45,'minimal45bank capacity')
    need((required-1).bit_length()==home['logical_word_address_bits']==20,'logical20bit address prerequisite')
    need(45*4096*3-required==home['spare_logical_words']==3200,'sparecapacity')
    for address in (0,1,2,3,524287,524288,required-1):
        container,lane=divmod(address,3);bank,row=divmod(container,4096)
        need(0<=bank<45 and 0<=row<4096 and 0<=lane<3 and (bank*4096+row)*3+lane==address,'address roundtrip')
    lef=(ROOT/LEF).read_bytes();size=re.search(rb'\bSIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)',lef)
    need(size is not None,'macro outline unavailable')
    macro=D(size[1].decode())*D(size[2].decode())/1000000
    variants=[]
    for width in (1024,2048):
        x=next(x for x in a['candidates'] if x['link_bits_per_rank_source_cycle']==width and x['policy']=='compact_stage_activation_reuse')
        need(x['aggregate_bits_per_source_cycle']==4*width,'rank/link width units')
        need(x['tracks']['total']==832+2*(width+64),'track resource accounting')
        need(x['cfg_and_stream_partial_ticks']==329*40*6*3,'samepartial cfg/stream term')
        need(D(x['transport_plus_cfg_and_stream_partial_us'])==D(x['partial_transport_us'])+D('65.8'),'partial time composition')
        variants.append(dict(width_per_rank=width,transport_partial_us=x['partial_transport_us'],
            transport_cfg_stream_partial_us=x['transport_plus_cfg_and_stream_partial_us'],
            added_area_screen_mm2_stage_rank=x['area']['additional_screen_mm2_per_stage_rank'],
            residual_field_screen_mm2=x['area']['residual_field_after_candidate_additions_mm2'],
            tracks=x['tracks'],credits=x['credits'],performance_qualified=False))
    need(t['dispatch']['known_conditional_partial_fabric_cycles']==606960,'Turing frozenpartialcost')
    need(w['candidate']['allocated_subproblem_die_count']==724+4+4==732,'subproblem die count')
    phase=[]
    for p in w['power']['phase_rows']:
        phase.append(dict(family=p['family'],clock_static_coordination_W=p['clock_plus_static_W'],
            margin_to_budget_W=str(D('474.56')-D(p['clock_plus_static_W'])),source_qualified=False))
    return dict(schema='opentallas.w16.DSROM-CROM-dispatch-independent-review.v1',
        owner_replay='PASS exact source/records',checked_owner_source_blobs=len(checked),
        source_pins={k:dict(commit=p[0],path=p[1],sha256=sha(raw[k])) for k,p in [('dispatch',DISPATCH),('whole',WHOLE),('Turing',TURING)]},
        current_macro_LEF_pin=dict(path=LEF,sha256=sha(lef)),
        CROM=dict(writer_words=508800,generated_Engram_words=40960,required_words=required,
            old19bit_deficit_words=25472,minimal_banks=45,containers=containers,
            logical_capacity_words=552960,spare_words=3200,bank44_deficit_words=required-44*4096*3,
            logical_address_bits=20,container_address_bits=18,bank_bits=6,row_bits=12,lane_bits=2,
            unused_lane3_must_refuse=True,unused_slots_not_generated_operand_credit=True,
            padding_bits_container=82,source64word_bytes_rank=required*8,
            physical_backing_bits_rank=45*4096*274,macro_outline_mm2_rank=str(45*macro),
            macro_outline_mm2_four_homes=str(180*macro),scalar_ports=1,
            full_home_area_mm2=None,read_capture_select_latency_cycles=None,
            missing=['Source-complete generated G.mul(q,k) operand/producer mapping','20bit producer/consumer address change','45bankdecode+3lane registeredmux and responsehold cost','singleport arbitration/consumerlease calendar','CROM clock/power/route/SSFF and physical home fit']),
        dispatch_comparison=dict(Turing256_known_partial_us='505.8',Turing_full_dispatch_bound=None,
            Ram_variants=variants,comparison_is_measured_gain=False,
            explanation='Ram addsframes,75cycle routes,CDC,ownerreads and exactsix-distinct capacity DP with perstage activationreuse; Turing uses oldworstdistance serialization withoutthose service inputs. Different partial profiles, not validated gains.',
            common_missing=['Actual PHY/package service','q1024 stride96 exacttemplate/epoch replay','activation quantization/SU/SFU/TP intermediate and orderedoutput collectives','actual finalconsumerdone/reversecredit','connected corridor and slotfit/SSFF']),
        allocation=dict(expert_dies=724,head_dies=4,embedding_dies=4,allocated_subproblem_dies=732,
            CROM_homes=4,CROM_homes_not_four_additional_dies=True,complete_product_die_count=None,
            Engram_backing_bytes=202758032400,Engram_physical_homes=None),
        unpinned_power_phase_coordination=phase,power_values_not_admitted=True,
        engine_RTL_build_ready=False,physical_admission=False,headline_rate=None,jobs_launched=0)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    with a.out.open('x') as f:json.dump(build(),f,indent=2);f.write('\n')
    print('PASS bounded independent review; full admission remains blocked')
