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


def compile_hbc_setup(inventory, job, timing, *, clock_reset_id=None):
    """Compile only the three HBC setup records from their measured ingress.

    CSR/context/activation dates are downstream of this admission and are not
    prerequisites. No CSR, RUN or START authority is emitted here.
    """
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
    native_ages = timing.get('hbc_arrival_boot_edges')
    keys = (("reset_deassert_edge", "host_counter_zero_edge", "link_ready_edge", "peer_to_hbc_input",
             "peer_frame_period", "peer_launch_modulus", "peer_launch_residue") if native_ages is None else
            ("reset_deassert_edge", "link_ready_edge", "peer_frame_period", "peer_launch_modulus", "peer_launch_residue"))
    t = {k: uint(timing[k], 48, k) for k in keys}
    if native_ages is not None:
        if 'host_counter_zero_edge' in timing or 'peer_to_hbc_input' in timing:
            raise ValueError('native boot-age calendar cannot mix common-clock global timing')
        if not isinstance(native_ages, list) or len(native_ages) != 3:
            raise ValueError('three measured native HBC arrival boot ages required')
        native_ages = [uint(v, 48, 'measured HBC arrival boot age') for v in native_ages]
        t['hbc_arrival_boot_edges'] = native_ages
    period, modulus = t["peer_frame_period"], t["peer_launch_modulus"]
    if not period or not modulus or period % modulus or t["peer_launch_residue"] >= modulus:
        raise ValueError("frame period must preserve the measured launch phase class")
    if native_ages is None and t["host_counter_zero_edge"] < t["reset_deassert_edge"]:
        raise ValueError("counter origin precedes actual reset release")
    def slot(edge):
        return edge + (t["peer_launch_residue"] - edge) % modulus
    launch = slot(max(t["link_ready_edge"], t["reset_deassert_edge"] + period))
    zero = t.get("host_counter_zero_edge")
    header = native_ages[0] if native_ages is not None else launch + t["peer_to_hbc_input"] - zero
    if header < 0:
        raise ValueError("HBC receive counter date would be negative")
    # LOAD/body are fixed four edges apart in the existing HBC protocol.
    if 4 % modulus:
        raise ValueError("HBC four-edge body gap leaves the qualified phase class")
    commit_gap = ((7 + modulus - 1) // modulus) * modulus
    commit = header + commit_gap
    if native_ages is not None and native_ages != [header, header + 4, commit]:
        raise ValueError("measured native arrivals do not satisfy the fixed HBC four-edge calendar")
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
    if clock_reset_id is not None:
        identity = uint(clock_reset_id, 64, 'explicit clock/reset identity')
        if not identity:
            raise ValueError('explicit clock/reset identity must be nonzero')
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
              dict(lane=0, edge=launch+commit_gap,
                   frame=frame(envelope(1,1,0,commit)), kind="HBC_COMMIT")]
    params = dict(LOCAL_STAGE=stage, LOCAL_RANK=rank, PHASE_BOUND=1, CLOCK_RESET_ID=identity,
                  BOOT_HEADER_EDGE=header, BOOT_COMMIT_EDGE=commit)
    return dict(schema='opentallas.head.hbc_setup.v1', scope='HBC_SETUP_ONLY',
                host_params=params, frames=frames, context=ctx, timing=t,
                hbc_book_scope='legacy417 HOST affine book; no activation data',
                authority=dict(CSR=False, GO=False, START=False),
                added_data_cycles=0, full_head_token=False,
                production_transport_qualified=False,
                missing_release_gates=['actual HBC context admission', 'successful CSR transport and apply',
                                       'actual vector residence before issue', 'real-view timing', 'whole-head token'])


def compile_entry(inventory, job, timing):
    if "hbc_arrival_boot_edges" in timing:
        raise ValueError("native boot-age calendar is HBC setup only; full entry requires measured downstream global timing")
    setup = compile_hbc_setup(inventory, job, timing)
    params = setup['host_params']
    stage, rank = params['LOCAL_STAGE'], params['LOCAL_RANK']
    ctx = setup['context']
    t = dict(setup['timing'])
    for key in ('peer_to_ctl_settled', 'commit_to_context_valid', 'ctl_start_offset'):
        t[key] = uint(timing[key], 48, key)
    period, modulus = t['peer_frame_period'], t['peer_launch_modulus']
    zero, commit = t['host_counter_zero_edge'], params['BOOT_COMMIT_EDGE']
    def slot(edge):
        return edge + (t['peer_launch_residue'] - edge) % modulus
    frames = setup['frames']
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
    explicit=job.get('activation_records')
    if activation is not None and explicit is not None:
        raise ValueError('choose uniform activation_beats or explicit activation_records')
    records=[]
    if explicit is not None:
        if not isinstance(explicit,list) or len(explicit)!=80:
            raise ValueError('explicit HEAD activation requires80 records')
        for r in explicit:
            if not isinstance(r,dict) or not {'index','edge','payload'}<=set(r):
                raise ValueError('activation record requires index,edge,payload')
            records.append(dict(index=uint(r['index'],7,'XB index'),
                                edge=uint(r['edge'],48,'actual XB source edge'),
                                payload=uint(r['payload'],1024,'XB payload')))
        if {r['index'] for r in records}!=set(range(80)):
            raise ValueError('activation records must contain each index0..79 exactly once')
        if len({r['edge'] for r in records})!=80:
            raise ValueError('activation source dates collide on the single XB input')
        records.sort(key=lambda r:r['edge'])
    elif activation is not None:
        if len(activation)!=80:
            raise ValueError('real HEAD xstore input is80K_XB beats,1024bits each')
        first_xb=uint(timing['xb_first_edge'],48,'actual XB source first edge')
        xb_period=uint(timing['xb_period'],16,'actual XB source period')
        if not xb_period:raise ValueError('XB period cannot be zero')
        records=[dict(index=index,edge=uint(first_xb+index*xb_period,48,'actual XB source edge'),
                      payload=uint(value,1024,'XB payload')) for index,value in enumerate(activation)]
    if records:
        to_resident=uint(timing['xb_pin_to_resident_edges'],16,'actual CTL XB pin-to-resident stages')
        for r in records:
            xb.append(dict(edge=r['edge'],index=r['index'],kind='K_XB',
                           lepk_i0=(r['payload']<<21)|(r['index']<<13)|(2<<1)|1,
                           ctrl_i0=(1<<31)|(ctx['user']<<21)|ctx['position']))
        resident=uint(max(r['edge'] for r in records)+to_resident,48,'last XB resident edge')
        start=max(settled,resident)+period
        issue=start+t['ctl_start_offset']+job['issue_offset']
    else:
        resident=start=issue=None
    return dict(schema="opentallas.head.provider_entry.v1", scope="CURRENT_PROVIDER_ENTRY_ONLY",
                full_head_token=False, production_transport_qualified=timing.get("scope")=="CURRENT_DIE_TRANSPORT",
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


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("inventory","job","timing","out"):p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise SystemExit("preserve existing schedule")
    result=compile_entry(json.loads(a.inventory.read_text()),json.loads(a.job.read_text()),json.loads(a.timing.read_text()))
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=1)+"\n")
    print(result["scope"],"frames",len(result["frames"]),"START",result["authority"]["start_global_edge"])


if __name__=="__main__":main()
