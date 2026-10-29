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
    words = uint(job.get("activation_words",160), 10, "HEAD activation word count")
    if not words:
        raise ValueError("empty HEAD activation stream")
    identity = int.from_bytes(hashlib.sha256(json.dumps(dict(timing=timing, stage=stage, rank=rank),
                                                       sort_keys=True).encode()).digest()[:8], "little") or 1
    # The affine book is part of HBC1's existing context format. HEAD uses
    # HOST_FRAMES rather than the layer HBE consumer, but emits a fully legal
    # variable-word context rather than a fabricated417-word layer booking.
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
    if not job["issue_period"] or not job["merge_deadline"]:
        raise ValueError("issue period and merge deadline must be nonzero")
    for address, value in values.items():
        frames.append(dict(lane=1, edge=next_csr, frame=(1<<552)|(value<<24)|(address<<16)|6,
                           kind="CSR", address=address, value=value,
                           settled_edge=next_csr+t["peer_to_ctl_settled"]))
        next_csr += period
    settled = max(f["settled_edge"] for f in frames if f["kind"]=="CSR")
    start = settled + period
    issue = start + t["ctl_start_offset"] + job["issue_offset"]
    return dict(schema="opentallas.head.provider_entry.v1", scope="CURRENT_PROVIDER_ENTRY_ONLY",
                full_head_token=False, production_transport_qualified=timing.get("scope")=="CURRENT_DIE_TRANSPORT",
                authority=dict(start_producer="@die.start", start_global_edge=start,
                               basis="explicit broadcast START input; static compiler slots after all configuration"),
                stage_basis="next address after model layer stages0..S-1; separate HEAD sink",
                host_params=dict(LOCAL_STAGE=stage,LOCAL_RANK=rank,PHASE_BOUND=1,CLOCK_RESET_ID=identity,
                                 BOOT_HEADER_EDGE=header,BOOT_COMMIT_EDGE=commit,HBC_VARIABLE_WORDS=1),
                timing=t, job=job, context_valid_global_edge=context_edge,
                first_issue_global_edge=issue, settled_configuration_edge=settled,
                frames=sorted(frames,key=lambda f:(f["edge"],f["lane"])),
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
