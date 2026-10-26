#!/usr/bin/env python3
"""Emit the explicitly requested HBE1v2 local mechanism fixture, never production slots."""
import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from hostb_envelope import Context, encode_boot
from ks_descriptor import encode

BOOT_SHA='f1c617d9224a57bf22b28124c78fe0f3f7f43dc29fd3c7d7723d90a80814de28'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--boot',type=Path,required=True)
    p.add_argument('--adapter-source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    assert sha(a.boot)==BOOT_SHA
    if a.out.exists():raise ValueError('preserve existing fixture; choose fresh output')
    words=[int(x,16) for x in a.boot.read_text().split()];assert len(words)==417
    c=Context(stage_id=1,rank=0,transaction_id=37,user=0,token=16754,position=1048575,
              epoch_identity=0x1021,programme_id64=0xf1c617d9224a57bf)
    route=[dict(adapter_id='TEST_stage0_nonlocal',receiver_clock_identity='TEST_commonclock_stage0',
                source_sha256=sha(a.adapter_source),configured=True,expected_header_stage=1)]
    slots=[]
    for i in range(417):
        h=100+16*i
        slots.append(dict(head_header_edge=h,head_body_edge=h+4,receiver_header_edge=h+3,
            receiver_body_capture_edge=h+7,transit=[dict(adapter_id='TEST_stage0_nonlocal',
                receiver_header_edge=h,header_slot=h,transit_body_edge=h+4)]))
    # Explicitly requested destination KS is last destination body +16.
    last_body=100+16*416+7;dest_ks=last_body+16;head_ks=dest_ks-3
    ks=dict(head_edge=head_ks,receiver_edge=dest_ks,deadline=dest_ks,slot=0,
            transit=[dict(adapter_id='TEST_stage0_nonlocal',receiver_header_edge=head_ks,header_slot=head_ks)])
    rawks=encode(user=c.user,token=c.token,position=c.position)
    records=encode_boot(words,c,slots,ks53=rawks,ks_slots=ks,transit_route=route)
    triples=[dict(index=i,legacy515=f'{w:0129x}',header512=records[2*i]['payload512'],
                  raw_body512=records[2*i+1]['payload512'],slots=slots[i]) for i,w in enumerate(words)]
    meta=dict(schema='opentallas.s81.hbe1v2.fixture_vectors.v1',status='TEST_COMPONENT_VECTORS_ONLY_UNEXECUTED',
        context=asdict(c),counter_units='edges; explicitly commonclock TEST component only',
        source=dict(boot_origin='ot-gold1:/srv/opentallas-scratch/claude/tokfunc2-s81/entry_jobs_r2/job15.host_boot.memh',
                    boot_sha256=BOOT_SHA,adapter_path=str(a.adapter_source),adapter_sha256=sha(a.adapter_source),
                    emitter_sha256=sha(__file__),codec_sha256=sha(Path(__file__).with_name('hostb_envelope.py'))),
        slot_authority='Explicit S81lead component TEST request; every adapter counter independently declared',
        transit_route=route,host_words=417,hfwd_records=835,ks53=f'{rawks:014x}',ks_slots=ks,
        source_model=dict(qualification='UNBUILT_SOURCE_MODEL_ONLY',host_crc_capture_to_emit_edges=2,
            HBE_RX_edges=1,HBE_TX_edges=2,HBE_transit_edges=3,ordinary_added_payload_register_edges=0,
            startup_enable_edges=3,seqhost_landing_optional_edges=1,
            collision='ordinary valid plus mature HBE faults and suppresses both; no reschedule'),
        production_stage_identity=False,production_epoch=False,production_first_command_anchor=None,
        global_phase_qualified=False,shipping_source_equivalence=False,full_stage=False,full_token=False,
        triples=triples,records=records)
    a.out.mkdir(parents=True)
    (a.out/'vectors.json').write_text(json.dumps(meta,indent=1)+'\n')
    (a.out/'hfwd512.memh').write_text(''.join(r['payload512']+'\n' for r in records))
    (a.out/'legacy515.memh').write_bytes(a.boot.read_bytes())
    print(a.out,'417 exact legacy words /835 HFWD, TEST only, no RTL execution')

if __name__=='__main__':main()
