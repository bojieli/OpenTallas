#!/usr/bin/env python3
"""Allocate a static HEAD provider-entry calendar from explicit source timing.

The compiler chooses slots; reset/transport origins and runtime job identity
are inputs. No runtime-ready signal schedules a frame. This source mechanism
does not qualify an unmeasured die transport or a whole-head token pass.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("hbc_codec", ROOT / "tools/s81_dv/hostctx_1021/gen_vectors.py")
CODEC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CODEC)


def uint(value, bits, name):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError(f"{name}: unsigned {bits}-bit input required")
    return value


def compile_entry(inventory, job, timing):
    if inventory.get("TP") != 4 or inventory.get("head_dies") != 4:
        raise ValueError("selected four-rank/four-head inventory required")
    # The selected model enumerates layer stages0..S-1 and a separate head
    # sink. Allocate its following address, rather than historical241/255.
    stage = uint(inventory["stages"], 8, "head stage after layer stages")
    if stage >= 241:
        raise ValueError("model stage allocation does not fit the existing HBC address space")
    rank = uint(job["rank"], 2, "rank")
    ctx = {k: uint(job[k], n, k) for k, n in
           (("tid",16),("user",10),("position",21),("token",21),("epoch",32),("programme",64))}
    t = {k: uint(timing[k], 48, k) for k in
         ("reset_deassert_edge", "host_counter_zero_edge", "link_ready_edge", "peer_to_hbc_input",
          "peer_frame_period", "peer_launch_modulus", "peer_launch_residue", "peer_to_ctl_settled",
          "commit_to_context_valid", "ctl_start_offset")}
    period, modulus = t["peer_frame_period"], t["peer_launch_modulus"]
    if not period or not modulus or period % modulus or t["peer_launch_residue"] >= modulus:
        raise ValueError("frame period must preserve the measured launch phase class")
    if t["host_counter_zero_edge"] < t["reset_deassert_edge"]:
        raise ValueError("counter origin precedes actual reset release")
    def slot(edge):
        return edge + (t["peer_launch_residue"] - edge) % modulus
    launch = slot(max(t["link_ready_edge"], t["reset_deassert_edge"] + period))
    zero = t["host_counter_zero_edge"]
    header = launch + t["peer_to_hbc_input"] - zero
    if header < 0:
        raise ValueError("HBC receive counter date would be negative")
    # LOAD/body are fixed four edges apart in the existing HBC protocol.
    if 4 % modulus:
        raise ValueError("HBC four-edge body gap leaves the qualified phase class")
    commit_gap = ((7 + modulus - 1) // modulus) * modulus
    commit = header + commit_gap
    # HBC's affine-book word count describes the HOST programme ABI, not
    # the separate80x1024-bit K_XB activation stream.
    words = uint(job.get("host_word_count",417), 10, "HBC HOST programme word count")
    if not words:
        raise ValueError("empty HOST affine programme book")
    command_scope=uint(timing.get("hbc_command_scope",0),2,"HBC command scope")
    if command_scope>2:
        raise ValueError("unknown HBC command namespace")
    if command_scope or words!=417:
        raise ValueError('variable HOST book and namespace alternatives are unadopted; retain current417 ABI')
    identity = int.from_bytes(hashlib.sha256(json.dumps(dict(timing=timing, stage=stage, rank=rank),
                                                       sort_keys=True).encode()).digest()[:8], "little") or 1
    # The affine book is HBC1's existing context format. HOST_FRAMES1 does
    # not execute its layer HBE words; keep the legacy417 ABI by default.
    # A variable HOST book is an explicit separate candidate, never inferred
    # from the80x1024-bit activation input.
    seed = 0
    first = commit - (header + 4) + 16
    ks = first + (words - 1) * 16 + 8
    body = 0
    for lo, width, value in (
        (0,16,ctx["tid"]),(16,10,ctx["user"]),(26,21,ctx["position"]),(47,21,ctx["token"]),
        (68,32,ctx["epoch"]),(100,64,ctx["programme"]),(164,48,seed),(212,48,first),
        (260,12,16),(272,10,words),(282,8,4),(290,8,4),(298,48,ks),
        (346,48,ks+12),(394,48,ks+4),(442,48,ks+8),(490,8,stage),(498,2,rank)):
        body = CODEC.put(body, lo, width, value)
    crc = CODEC.crc(body)
    def envelope(op, seq, length, date):
        return (0x31434248 | 1<<32 | op<<36 | stage<<40 | rank<<48 | seq<<50 | length<<66 |
                crc<<82 | identity<<114 | ctx["programme"]<<178 | date<<242)
    def frame(payload, kind=7):
        return (1<<552) | (payload<<16) | kind
    frames = [dict(lane=0, edge=launch, frame=frame(envelope(0,0,512,header+4)), kind="HBC_LOAD"),
              dict(lane=0, edge=launch+4, frame=frame(body), kind="HBC_BODY"),
              dict(lane=0, edge=zero+commit-t["peer_to_hbc_input"],
                   frame=frame(envelope(1,1,0,commit)), kind="HBC_COMMIT")]
    context_edge = zero + commit + t["commit_to_context_valid"]
    next_csr = slot(context_edge + period)
    values = {0:uint(job["plen"],21,"plen"),1:uint(job["glen"],21,"glen"),2:rank,
              3:uint(job["group"],4,"group"),4:uint(job["rbase"],17,"rbase"),
              9:(uint(job["issue_offset"],16,"issue offset")<<16)|uint(job["issue_period"],16,"issue period"),
              10:uint(job["merge_deadline"],16,"merge deadline"),8:1}
    mode=job.get('mode','ar')
    if mode=='mtp':
        # CSR5 is the real RESULT/DHRES{DEST,SRC}tag, not rank or row base.
        # It has no safe default: the selected MTP consumer owns this booking.
        values[5]=uint(job['mtp_result_mtag'],16,'actual MTP RESULT/DHRES mtag')
        values[8]=values.pop(8) # RUN remains the final configuration write
    elif mode!='ar' or job['glen']!=0:
        raise ValueError('AR-only entry requires glen0; MTP needs its explicit RESULT/DHRES tag')
    if not job["issue_period"] or not job["merge_deadline"]:
        raise ValueError("issue period and merge deadline must be nonzero")
    for address, value in values.items():
        frames.append(dict(lane=1, edge=next_csr, frame=(1<<552)|(value<<24)|(address<<16)|6,
                           kind="CSR", address=address, value=value,
                           settled_edge=next_csr+t["peer_to_ctl_settled"]))
        next_csr += period
    settled = max(f["settled_edge"] for f in frames if f["kind"]=="CSR")
    xb=[]
    activation=job.get('activation_beats')
    if activation is not None:
        if len(activation)!=80:
            raise ValueError('real HEAD xstore input is80K_XB beats,1024bits each')
        first_xb=uint(timing['xb_first_edge'],48,'actual XB source first edge')
        xb_period=uint(timing['xb_period'],16,'actual XB source period')
        to_resident=uint(timing['xb_pin_to_resident_edges'],16,'actual CTL XB pin-to-resident stages')
        if not xb_period:raise ValueError('XB period cannot be zero')
        for index,value in enumerate(activation):
            value=uint(value,1024,'XB payload')
            xb.append(dict(edge=first_xb+index*xb_period,index=index,kind='K_XB',
                           lepk_i0=(value<<21)|(index<<13)|(2<<1)|1,
                           ctrl_i0=(1<<31)|(ctx['user']<<21)|ctx['position']))
        resident=xb[-1]['edge']+to_resident
        start=max(settled,resident)+period
        issue=start+t['ctl_start_offset']+job['issue_offset']
    else:
        resident=start=issue=None
    # Addition can exceed48 bits even when every input individually fits.
    # Never silently truncate emitted dates when materializing RTL parameters.
    for name,value in dict(header=header,commit=commit,context=context_edge,settled=settled,
                           **({'START':start,'issue':issue} if start is not None else {})).items():
        uint(value,48,'compiled '+name+' edge')
    for record in frames+xb:uint(record['edge'],48,'compiled source launch edge')
    params=dict(LOCAL_STAGE=stage,LOCAL_RANK=rank,PHASE_BOUND=1,CLOCK_RESET_ID=identity,
                BOOT_HEADER_EDGE=header,BOOT_COMMIT_EDGE=commit)
    return dict(schema="opentallas.head.provider_entry.v1", scope="CURRENT_PROVIDER_ENTRY_ONLY",
                full_head_token=False, production_transport_qualified=False, transport_input_scope=timing.get("scope"),
                authority=dict(start_producer="@die.start", start_global_edge=start,
                               basis="explicit broadcast START input; static slots after all configuration and actual XB residency"),
                stage_basis="next address after model layer stages0..S-1; separate HEAD sink",
                host_params=params,
                timing=t, job=job, context_valid_global_edge=context_edge,
                first_issue_global_edge=issue, settled_configuration_edge=settled,
                frames=sorted(frames,key=lambda f:(f["edge"],f["lane"])),
                xb_records=xb,activation_resident_edge=resident,
                mode=mode,
                source_counts=dict(HBC_setup_records=3,CSR_records=len(values),ordinary_HFWD_records=0,
                                   activation_K_XB_records=len(xb),activation_halfwords512=len(xb)*2,
                                   activation_BF16_values=len(xb)*64,total_source_records=len(frames)+len(xb)),
                hbc_book_scope='legacy HOST affine-book descriptor; HOST_FRAMES1 disables HBE consumer; not activation data',
                added_data_cycles=0, missing_release_gates=["current die transport/reset binding",
                    "actual vector residence before first compute issue", "real-view die timing", "whole-head token"])


def boot_recipe_programme(schedule, transport):
    """Join emitted records to the existing plan/reset recipe audit.

    The two additional inputs identify the actual START source and the
    peer-to-HOST frame age. They cannot be inferred from a component pass.
    The caller must bind host_params into its candidate plan before auditing.
    """
    start=schedule['authority']['start_global_edge']
    if start is None:
        raise ValueError('no START without the actual80-beat XB source')
    producer=transport['start_producer']
    if not isinstance(producer,str) or not producer.strip():
        raise ValueError('actual START source required')
    t=schedule['timing'];job=schedule['job'];params=schedule['host_params']
    records=[]
    for f in schedule['frames']:
        if f['kind'].startswith('HBC_'):
            records.append(dict(receive_edge=f['edge']+t['peer_to_hbc_input']-t['host_counter_zero_edge'],
                                payload=(f['frame']>>16)&((1<<512)-1)))
    config={k:job[k] for k in ('plen','glen','group','rbase','issue_offset','issue_period','merge_deadline')}
    config['mode']=schedule['mode']
    if schedule['mode']=='mtp':config['mtp_result_mtag']=job['mtp_result_mtag']
    return dict(start=dict(producer=producer,die_edge=start),
                host_boot_counter_zero_global_edge=t['host_counter_zero_edge'],
                transport=dict(peer_to_hbc_input=t['peer_to_hbc_input'],
                               peer_to_host_frame=uint(transport['peer_to_host_frame'],48,'actual peer-to-HOST frame age'),
                               peer_to_ctl_csr_apply=t['peer_to_ctl_settled'],
                               hbc_commit_to_context_valid=t['commit_to_context_valid'],
                               peer_frame_period=t['peer_frame_period']),
                hbc_records=records,config=config,
                csr_apply_edges={str(f['address']):f['settled_edge'] for f in schedule['frames'] if f['kind']=='CSR'},
                test_only=schedule['transport_input_scope']!='CURRENT_DIE_TRANSPORT',
                expected_ctl_start_offset=t['ctl_start_offset'],
                expected_host_binding=params,
                source_counts=schedule['source_counts'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("inventory","job","timing","out"):p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise SystemExit("preserve existing schedule")
    result=compile_entry(json.loads(a.inventory.read_text()),json.loads(a.job.read_text()),json.loads(a.timing.read_text()))
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=1)+"\n")
    print(result["scope"],"frames",len(result["frames"]),"START",result["authority"]["start_global_edge"])


if __name__=="__main__":main()
