#!/usr/bin/env python3
"""Selected DS G22 HC tail lowering with a real root producer.

This module owns the root/table payload, not the shared slice/calendar assembly.
It never emits a drive to a root result pin.  A connected boundary must contain
hc_eng and hleaf_SE; the old SW-only boundary is rejected.  Assembly is not an
execution qualification, and the missing HC projection remains explicit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from hbm_layer_vehicle import hc_images as HC
sys.path.insert(0, str(TOOLS / "hbm_static"))
import leaf_split_latency as LS  # noqa: E402  HBM-P6-CMP over-cap leaf-split shifts
from hbm_layer_vehicle.layer_images import CpBus

# STEWARD-TOK-HBM-HC 10-21: the ds_native fixtures (records.json/operands.npz, HC_MIX_POST A -> O) are the full-shape
# W17/W19 run (tools/rtl_v41_fullshape_layer_campaign.Checkpoint: the RELEASED DeepSeek-V4.1-Flash snapshot, D 5120).
# The root's base24/scale3 runtime inputs must come from that same snapshot.  The reduced-v2 single-file checkpoint
# (dim 160, sha f96ae554...) has different hc_* tensors: feeding it made the actual root compute mHC(A, reduced params)
# exactly while the checks expected mHC(A, released params) -> k31 SLICE_FAIL 4/12 (rec30 hc_eng__result + 3 VM words).
RELEASED_SNAPSHOT_REVISION = "dba1be0a40aa45a94ad051997016db3960a90277"
RELEASED_SNAPSHOT = (Path.home() / ".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots"
                     / RELEASED_SNAPSHOT_REVISION)
CHECKPOINT_SHA256 = "f96ae55457396bc881ee592f7f7eb66d6f510b6be76faf40dca9a5629c0fa74d"   # reduced-v2: NOT the fixture's
REQUIRED_INSTANCES = ("hc_eng", "hleaf_SE", "hc_SW", "calendar_SW", "hleaf_SW", "hb_ckgen")
ROOT_TGT, TABLE_TGT = 164, 165
# Selected SE leaf2 -> target pin/start -> sequencer pin/start -> event/root edge.
# This is an explicit source schedule to be checked by the coupled RTL case.
ROOT_APPLY_AFTER_LAUNCH = 8
# HBM-P6-CMP: + LS 'hc_tail_result' (7 core edges, sinkhorn_s split root ot_hbm_hc_root_static_s; L 496 -> 503) when
# OT_HBM_LEAF_SPLIT=1 (default 0 = pinned root): every tail emit moves +7 with it.
TAIL_RESULT_LATENCY = 496 + LS.shift('hc_tail_result')
TAIL_EMIT_GUARD = 4
EVENT_FIELDS = {"clear": (104, 1), "gm": (60, 1), "gmq": (61, 2),
                "gmo": (63, 1), "tf": (105, 1), "tset": (106, 7),
                "tl": (113, 1), "tunit": (114, 1), "tpos": (115, 3),
                "emit": (118, 1), "qmask": (119, 4), "eunit": (123, 1)}


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def checkpoint_parameters(path, layer, which="attn", expected_sha=None):
    """Read only the released input tensors; expected output is not an argument.

    `path` = the released sharded snapshot directory (model.safetensors.index.json; the default and the only source
    consistent with the ds_native fixtures, revision RELEASED_SNAPSHOT_REVISION) or, for a non-fixture use, a single
    safetensors file whose whole-file SHA256 must equal `expected_sha`."""
    path = Path(path)
    if path.is_dir():
        if path.name != RELEASED_SNAPSHOT_REVISION:
            raise ValueError(f"HC parameters: snapshot {path} is not released revision {RELEASED_SNAPSHOT_REVISION}")
        weight_map = json.loads((path / "model.safetensors.index.json").read_text())["weight_map"]
        files = {s_: path / weight_map[f"layers.{layer}.hc_{which}_{s_}"] for s_ in ("base", "scale")}
        actual_sha = f"snapshot:{RELEASED_SNAPSHOT_REVISION}"
    else:
        if expected_sha is None:
            raise ValueError("HC parameters: a single-file checkpoint needs an explicit expected_sha (the ds_native "
                             "fixtures use the released snapshot directory)")
        actual_sha = sha_file(path)
        if actual_sha != expected_sha:
            raise ValueError(f"checkpoint SHA256 mismatch: {actual_sha}")
        files = {"base": path, "scale": path}
    values, provenance = {}, {}
    for suffix, count in (("base", 24), ("scale", 3)):
        with files[suffix].open("rb") as f:
            n = struct.unpack("<Q", f.read(8))[0]
            header = json.loads(f.read(n))
            name = f"layers.{layer}.hc_{which}_{suffix}"
            meta = header[name]
            if meta["dtype"] != "F32" or meta["shape"] != [count]:
                raise ValueError(f"unsupported real HC input tensor {name}: {meta}")
            lo, hi = meta["data_offsets"]
            if hi - lo != count * 4:
                raise ValueError(f"invalid tensor byte count: {name}")
            f.seek(8 + n + lo)
            raw = f.read(hi - lo)
        values[suffix] = list(struct.unpack("<" + "I" * count, raw))
        provenance[suffix] = dict(tensor=name, file=files[suffix].name, dtype="F32", shape=[count],
                                  data_offsets=[lo, hi], sha256=hashlib.sha256(raw).hexdigest())
    return values, dict(checkpoint=str(path), checkpoint_sha256=actual_sha, tensors=provenance)


def mix_post_reference(A, parameters, hc=4, sinkhorn_iters=20, eps=1e-6):
    """ds_native hc_mix_post (tools/hgi_sim/ds_native.py) in float64: [pre | post | Sinkhorn comb] of the 24 raw mixes.
    Used only as an input/expectation CONSISTENCY guard (wrong parameters give O(1) errors), never as a check value."""
    f32 = lambda u: np.asarray(u, np.uint32).view(np.float32).astype(np.float64)
    m, base, scale = f32(A), f32(parameters["base"]), f32(parameters["scale"])
    sig = lambda z: 1.0 / (1.0 + np.exp(-z))
    pre = sig(m[:hc] * scale[0] + base[:hc]) + eps
    post = 2.0 * sig(m[hc:2 * hc] * scale[1] + base[hc:2 * hc])
    c = (m[2 * hc:] * scale[2] + base[2 * hc:]).reshape(hc, hc)
    c = np.exp(c - c.max(axis=1, keepdims=True))
    c = c / c.sum(axis=1, keepdims=True) + eps
    c = c / (c.sum(axis=0, keepdims=True) + eps)
    for _ in range(sinkhorn_iters - 1):
        c = c / (c.sum(axis=1, keepdims=True) + eps)
        c = c / (c.sum(axis=0, keepdims=True) + eps)
    return np.concatenate([pre, post, c.ravel()])


def check_parameters_reproduce(A, expected_O, parameters, rtol=1e-4, atol=1e-6):
    """Refuse to emit when the runtime base/scale cannot produce the fixture's expected O from its A."""
    ref = mix_post_reference(A, parameters)
    exp = np.asarray(expected_O, np.uint32).view(np.float32).astype(np.float64)
    if not np.allclose(ref, exp, rtol=rtol, atol=atol):
        bad = int(np.argmax(np.abs(ref - exp)))
        raise ValueError(f"HC runtime parameters do not reproduce the fixture O (max |err| {np.abs(ref - exp).max():.3g}"
                         f" at [{bad}] ref {ref[bad]:.6g} exp {exp[bad]:.6g}): base/scale source differs from the "
                         f"fixture golden (use the released snapshot {RELEASED_SNAPSHOT_REVISION})")


def event_word(time, **fields):
    if not 0 <= time < 1 << 20:
        raise ValueError("root event time out of range")
    word = time
    for name, value in fields.items():
        bit, width = EVENT_FIELDS[name]
        if not 0 <= value < 1 << width:
            raise ValueError(f"root event field out of range: {name}")
        word |= value << bit
    return word


def root_rows(parameters, response_phase):
    """F20 rows for actual input table and a sparse, fixed-time G22 programme."""
    data = parameters["base"] + parameters["scale"] + [0]
    table = [(0xc7a1 << 240) | (pc << 224) |
             sum(data[7 * pc + k] << (32 * k) for k in range(7)) for pc in range(4)]
    g0 = HC.PROG_OUT + 1 + response_phase + 2
    tail = g0 + 32                    # last mix commits at g0+24; no ready polling
    emit = tail + TAIL_RESULT_LATENCY + TAIL_EMIT_GUARD
    origin = ROOT_APPLY_AFTER_LAUNCH
    schedule = [(g0 - 4, dict(clear=1)), (g0 - 3, dict(gm=1, gmq=0, gmo=1)),
                (g0 + 24, dict(tf=1, tset=0)), (g0 + 26, dict(gm=1, gmq=0, gmo=0)),
                (tail, dict(tl=1, tunit=0, tpos=0)),
                (emit, dict(emit=1, qmask=1, eunit=0))]
    words = [(0xc7a1 << 240) | (pc << 224) | event_word(edge - origin, **fields)
             for pc, (edge, fields) in enumerate(schedule)]
    return table, words, dict(root_apply_origin=origin, gather_row0_at=g0,
                             tail_launch_after=tail, result_after=emit,
                             tail_latency=TAIL_RESULT_LATENCY, emit_guard=TAIL_EMIT_GUARD,
                             gather_period=max(24,response_phase+1), npos=1,
                             extra_edges_per_additional_position=max(0,response_phase+1-24),
                             emit_after_row0=emit - (g0 - 1),
                             schedule=[dict(after_launch=edge, sequencer_time=edge-origin, fields=fields)
                                       for edge, fields in schedule])


def validate_connected_boundary(boundary):
    names = {x if isinstance(x, str) else x["name"] for x in boundary["instances"]}
    missing = set(REQUIRED_INSTANCES) - names
    inputs = {x["name"] for x in boundary["inputs"]}
    forbidden = sorted(x for x in inputs if x.startswith("hc_eng__result"))
    if missing or forbidden:
        raise ValueError(f"HC connected cut refused: missing={sorted(missing)}, result_inputs={forbidden}")


def lower_mix_post(A, expected_O, parameters, timing, *, a_sector, o_sector,
                   component_allocation, record=30, t0=16, boundary=None, source_profile=None, profile_contract=None):
    """Emit real root inputs/programme plus downstream expected checks.

    component_allocation=True is explicitly the bounded relocated probe.  Shared
    integration must supply its real allocation and keep that distinction honest.
    """
    if boundary is not None:
        validate_connected_boundary(boundary)
    if not (0 <= a_sector <= 8192-3 and 0 <= o_sector <= 8192-3):
        raise ValueError("bounded SW compiler requires an explicit three-sector SW allocation")
    if set(range(a_sector,a_sector+3)) & set(range(o_sector,o_sector+3)):
        raise ValueError("bounded G22 allocation requires disjoint input/output spans")
    check_parameters_reproduce(A, expected_O, parameters)
    if source_profile is None:
        table, programme, schedule = root_rows(parameters, timing["resp_phase"])
    else:
        from hbm_layer_vehicle import hc_safe2_phase40_1021 as HP
        if source_profile != HP.SAFE2_P40:
            raise ValueError("only explicit SAFE2 phase40 candidate profile is supported")
        if record != 30 or (a_sector,o_sector)!=(64,72) or np.asarray(A).size!=24:
            raise ValueError("SAFE2 profile only covers rank0k31/record30 relocated A64/O72 npos1")
        if profile_contract is None:
            raise ValueError("SAFE2 candidate requires actual matching source contract")
        contract=json.loads(Path(profile_contract).read_text())["instances"]
        model=HP.source_profile(source_profile)
        for instance,params in [('hc_SW',model['hub']),('hc_eng',model['root'])]:
            actual=contract[instance]['params']
            for key,value in params.items():
                if actual.get(key)!=value:
                    raise ValueError(f"SAFE2 source contract mismatch {instance}.{key}: {actual.get(key)} != {value}")
        table, programme, schedule = HP.root_rows_for_profile(root_rows, parameters, timing["resp_phase"],profile=source_profile,npos=1)
        schedule['profile_contract_sha256']=hashlib.sha256(Path(profile_contract).read_bytes()).hexdigest()
    prefix = CpBus(t0, src="image:HC_REAL_TABLE")
    prefix.install(TABLE_TGT, table, rec=record)
    prefix.src = "image:HC_REAL_ROOT"
    prefix.install(ROOT_TGT, programme, rec=record)
    prefix.desc(ROOT_TGT, 0, len(programme), 1, rec=record)
    tim = dict(timing, emit_after_row0=schedule["emit_after_row0"])
    g = HC.mix_post_record(A, expected_O, record, a_idx=a_sector, o_idx=o_sector, t0=prefix.t, tim=tim)
    # The shared historical compiler is reused only for qhub/calendar/VM checks.
    # Its fixture-result drive events are categorically forbidden in this mode.
    forbidden = lambda e: e["k"] == "D" and e.get("port", "").startswith("hc_eng__result")
    events = prefix.ev + [e for e in g["events"] if not forbidden(e)]
    assert not any(forbidden(e) or e.get("src") == "farend:hc_eng" for e in events)
    checks = g["chk"]
    if boundary is not None:
        outputs = {x["name"] for x in boundary["outputs"]}
        raw_internal = boundary.get("internal_nets", [])
        internal = ({x if isinstance(x, str) else x["name"] for x in raw_internal}
                    if isinstance(raw_internal, list) else set())
        # The boundary schema may retain only an internal-net count.  These
        # producer ports become internal by the required real root connections.
        internal.update(f"hc_SW__gathered_mix_{s}" for s in ("v", "row", "pos", "data"))
        internal.add("hc_SW__eng_fault")
        kept = []
        for e in checks:
            port = e["port"]
            if port.startswith("vm:") or port in outputs:
                kept.append(e)
            elif port not in internal:
                raise ValueError(f"check endpoint absent from connected cut: {port}")
        checks = kept
    return dict(schema="opentallas.hc_connected_lowering.v1", status="source_assembly_only",
                execution_qualified=False, qualifies_native_layer=False, qualifies_native_chain=False,
                required_instance_names=list(REQUIRED_INSTANCES), include_regex="^(hc_eng|hleaf_SE)$",
                boundary_checked=boundary is not None, component_allocation=component_allocation,
                projection_open="G22 post only: full HC weight projection and inter-rank producer remain separate",
                root_programme_rows=[f"{x:064x}" for x in programme],
                root_table_rows=[f"{x:064x}" for x in table],
                root_targets=dict(programme=ROOT_TGT, table=TABLE_TGT),
                root_schedule=dict(schedule, launch=g["launch"][0],
                                   finish=g["launch"][0]+schedule["result_after"]),
                root_data_producer="actual ot_hbm_hc_root_static via hleaf_SE, never fixture O",
                checkpoint_parameters_are_runtime_inputs=True,
                events=sorted(events+checks, key=lambda e:(e["dom"], e["cyc"], e["k"])),
                owner_footprints=dict(vm_reads=[g["a_sector"]+j for j in range(3)],
                                      vm_writes=[g["o_sector"]+j for j in range(3)],
                                      f20_targets=[HC.HC_TGT, HC.CAL_TGT, ROOT_TGT, TABLE_TGT]),
                qhub_timing={k:v for k,v in g.items() if k not in ("events", "chk")})




def _sfu_runtime_io(segments, read_return, write_return):
    from hbm_layer_vehicle import sfu_images as SI
    from sfu_vector_calendar import compile_vector
    from sfu_control_image import pack
    payloads=[]
    for seg in segments:
        n = seg["n"]
        # Four physical input groups are independent of the output SRAM group.
        ctl = compile_vector(words=n, bases=(0,0,0,0,0), m1=1, ad=1,
                             strides=(1,0,1,0,1), rnd=seg["rnd"])
        fields = [dict(row["fields"], cm_qm=1) for row in ctl["rows"]]
        # Keep arithmetic controls stable beyond the OUT stage, including BF16.
        fields += [dict(fields[-1], emit=0, ld=0) for _ in range(16)]
        control = [pack(f) for f in fields]
        io=[]; transfers=[]
        def add(fields=None):
            io.append(dict(scalar_enable=0xa, **(fields or {})))
            return len(io)-1
        # Serialized requests avoid both physical-bank and scalar-group clashes.
        for group,key in ((0,"a"),(2,"c"),(1,"b"),(3,"d")):
            count = n//8 if group in (0,2) else 1
            for j in range(count):
                word = seg[key] + 8*j
                sector, lane = divmod(word,8)
                bank = sector % 8
                scalar = group in (1,3)
                row = add(dict(prefetch_v=1<<bank, prefetch_sector=sector<<(16*bank),
                               prefetch_group=group<<(2*bank),
                               prefetch_local_addr=(8*j)<<(15*bank),
                               prefetch_scalar=int(scalar)<<bank,
                               prefetch_word=lane<<(3*bank)))
                transfers.append(dict(io_row=row, kind="scalar_read" if scalar else "vector_stage",
                                      vm_sector=sector, bank=bank, group=group,
                                      local_word=0 if scalar else 8*j, scalar_word=lane if scalar else None))
        # Metadata has [0:READ_RETURN], plus operand capture; explicit guard.
        arithmetic_start = len(io) + read_return + 8
        while len(io) <= arithmetic_start:
            add()
        io[arithmetic_start]["arithmetic_start"] = 1
        control_start = arithmetic_start + SI.IO_TO_CTL
        drain_start = control_start + len(control) + 8
        while len(io) < drain_start:
            add()
        for j in range(n//8):
            sector = seg["o"]//8+j
            row = add(dict(drain_v=1, drain_addr=8*j, drain_vm_sector=sector))
            transfers.append(dict(io_row=row, kind="output_drain", vm_sector=sector,
                                  bank=sector%8, local_output_word=8*j))
        # Real VM commit precedes the next segment's stage; no local O alias.
        for _ in range(write_return+10):
            add()
        if len(io)>SI.ROWS or len(control)>SI.ROWS:
            raise ValueError("HC_POST segment does not fit the actual resident store")
        io_words=[SI.pack_io(f) for f in io]
        payloads.append(dict(pass_index=seg["p"], output_index=seg["k"],
                             input_vm_words={k:seg[k] for k in "abcd"}, output_vm_word=seg["o"],
                             scalar_enable=0xa, scalar_local_addresses=[0,0,0,0],
                             ctl_rows=[f"{w:0436x}" for w in control],
                             io_rows=[f"{w:0118x}" for w in io_words],
                             prm=f"{SI.prm_row(0,len(control),0,len(io_words)):064x}",
                             transfers=transfers, arithmetic_start_io_row=arithmetic_start,
                             first_control_io_row=control_start, first_drain_io_row=drain_start,
                             io_cycles=len(io), ctl_cycles=len(control),
                             next_segment_requires="all fixed VM completion edges, then reinstall/launch"))
    return payloads


def lower_hc_post_io(*, D, quadrant, y_word, residual_word, coefficient_word,
                     output_word, one_word, component_allocation, selected_core):
    """Runtime scalar + real VM round-trip lowering; no output fixture argument.

    Each segment is a separate resident install/launch. Intermediate results are
    drained to VM before the next segment stages them into input group C. The
    returned fixed source schedule still requires the selected coupled RTL proof.
    All addresses are caller allocations in SW VM words, never logical defaults.
    """
    from hbm_layer_vehicle import sfu_fused_compile as SF

    expected = dict(LWB=15, LG_PATH=15, TAP_RR=24, TAP_WR=21)
    if selected_core.get("master") != "ot_hgi_sfu_core_split3":
        raise ValueError("HC_POST requires the actual selected split3 core")
    params = selected_core.get("params", {})
    if any(int(params.get(k, -1)) != v for k,v in expected.items()):
        raise ValueError(f"unsupported selected SFU parameters: {params}")
    if D <= 0 or D % 32 or quadrant not in range(4):
        raise ValueError("HC_POST requires four sector-aligned quadrant slices")
    n = D // 4
    if n > (1 << 15):
        raise ValueError("HC_POST slice exceeds the actual operand group capacity")
    spans = [(y_word,D), (residual_word,4*D), (coefficient_word,20),
             (output_word,4*D), (one_word,1)]
    if any(a < 0 or a+size > 8192*8 for a,size in spans):
        raise ValueError("HC_POST caller allocation is outside SW VM")
    if any(a % 8 for a in (y_word,residual_word,output_word)):
        raise ValueError("vector allocations must be sector aligned")
    for j,(a,size) in enumerate(spans):
        for b,other in spans[j+1:]:
            if max(a,b) < min(a+size,b+other):
                raise ValueError("HC_POST caller allocations overlap")
    # Actual selected split3 bridge: LG_PATH+1 registers in each direction.
    read_return = expected["TAP_RR"] + 2*(expected["LG_PATH"]+1)
    write_return = expected["TAP_WR"] + 2*(expected["LG_PATH"]+1)
    segments = SF.hc_post_passes(D=D, quadrant=quadrant, A=y_word,
                                B=residual_word, C=coefficient_word,
                                O=output_word, one=one_word)
    payloads = _sfu_runtime_io(segments, read_return, write_return)
    return dict(schema="opentallas.hc_post_runtime_io.v1", status="source_assembly_only",
                execution_qualified=False, qualifies_native_layer=False,
                component_allocation=component_allocation, D=D, quadrant=quadrant,
                selected_core=selected_core, fixed_bridge=dict(read_return=read_return,
                   write_return=write_return, metadata_last_index=read_return),
                constant_input=dict(vm_word=one_word,required_bits="3f800000",must_be_installed=True),
                coefficients="runtime VM: post[4], comb[4,4], root HC output excludes pre[4]",
                arithmetic="four ordered FP32 passes; BF16 rounding only final pass",
                physical_operand_groups=dict(A=0,B=1,C=2,D=3,output="separate SRAM drained to VM"),
                calendar_integration_required=True, segments=payloads)




def lower_hc_pre_mix(*, D, residual_word, pre_word, mixed_word, one_word,
                     selected_core, component_allocation, chunk_words=1280):
    """Actual runtime three-pass HC_PRE mix; RMSNorm remains a separate join.

    Split elementwise work into resident chunks without changing any element's
    summation order. Pre coefficients are actual VM inputs from HC root output.
    """
    expected=dict(LWB=15,LG_PATH=15,TAP_RR=24,TAP_WR=21)
    if selected_core.get("master")!="ot_hgi_sfu_core_split3" or any(
            int(selected_core.get("params",{}).get(k,-1))!=v for k,v in expected.items()):
        raise ValueError("HC_PRE mix requires the exact selected SFU core")
    if D<=0 or D%8 or chunk_words<=0 or chunk_words%8 or chunk_words>1280:
        raise ValueError("HC_PRE mix requires sector-aligned resident chunks<=1280words")
    spans=[(residual_word,4*D),(pre_word,4),(mixed_word,D),(one_word,1)]
    if any(a<0 or a+n>65536 for a,n in spans) or residual_word%8 or mixed_word%8:
        raise ValueError("HC_PRE explicit allocations must fit aligned SW VM")
    for i,(a,n) in enumerate(spans):
        if any(max(a,b)<min(a+n,b+m) for b,m in spans[i+1:]):
            raise ValueError("HC_PRE input/output allocations overlap")
    segments=[]
    for p in range(3):
        for offset in range(0,D,chunk_words):
            n=min(chunk_words,D-offset)
            if p==0:
                a,b,c,d=residual_word+offset,pre_word,residual_word+D+offset,pre_word+1
            else:
                a,b,c,d=residual_word+(p+1)*D+offset,pre_word+p+1,mixed_word+offset,one_word
            segments.append(dict(a=a,b=b,c=c,d=d,o=mixed_word+offset,p=p,k=offset,n=n,rnd=int(p==2)))
    return dict(schema="opentallas.hc_pre_runtime_mix.v1",status="mix_source_assembly_only",
                execution_qualified=False,qualifies_native_layer=False,
                component_allocation=component_allocation,D=D,selected_core=selected_core,
                constant_input=dict(vm_word=one_word,required_bits="3f800000",must_be_installed=True),
                arithmetic="BF16(seqsum_j pre[j]*residual[j]); FP32 intermediates; exactly three passes",
                segments=_sfu_runtime_io(segments,56,53),
                remaining=["real VM producer mapping and calendar", "coupled selected RTL execution",
                           "RMSNorm square/reduction/rsqrt/RF/gain joins"])


def lower_qdq_fp8(*, words, a_sector, o_sector, selected_engine,
                   component_allocation, record=16, t0=16):
    """Actual NW target48 runtime FP8 QDQ programme, without output injection.

    Addresses are allocated NW-local sector addresses. Common calendar/bank
    ownership and the current RL57 coupled execution remain mandatory.
    """
    expected = dict(RL=57, WC=4, COMPACT=1)
    if selected_engine.get("master") != "ot_hgi_qdq_host_split" or any(
            int(selected_engine.get("params",{}).get(k,-1)) != v for k,v in expected.items()):
        raise ValueError("QDQ requires the exact selected RL57/WC4/COMPACT1 NW engine")
    if not isinstance(words,int) or words < 128 or words % 32 or words//32 >= 1<<16:
        raise ValueError("compact QDQ requires at least four 32-word beats")
    sectors=words//8
    if any(not isinstance(a,int) or a<0 or a+sectors>8192 or a%4
           for a in (a_sector,o_sector)):
        raise ValueError("QDQ requires explicit four-sector-aligned NW allocation")
    if max(a_sector,o_sector)<min(a_sector+sectors,o_sector+sectors):
        raise ValueError("QDQ input/output allocations overlap")
    # record calendar current[31:0]=first timestamp; [47:32]=beats;
    # [63:48]/[79:64]=source/destination sector; [85:80]=op4(FP8).
    first=16;beats=words//32
    row=(0xc7a1<<240)|(4<<80)|(o_sector<<64)|(a_sector<<48)|(beats<<32)|first
    cp=CpBus(t0,src="image:QDQ_FP8_REAL_NW")
    cp.install(48,[row],rec=record)
    cp.desc(48,0,1,1,rec=record)
    cp.launch(rec=record)
    return dict(schema="opentallas.qdq_fp8_runtime.v1",status="source_assembly_only",
                execution_qualified=False,qualifies_native_layer=False,
                component_allocation=component_allocation,selected_engine=selected_engine,
                required_instance_names=["hb_quant_NW","hleaf_NW","hb_idx__nwsh"],
                required_request_padding_regex="^l12p_hb_quant_NW_hb_idx__nwsh_b_rq_",
                programme_rows=[f"{row:064x}"],events=cp.ev,
                local_counter_schedule=dict(first_command=first,last_command=first+beats-1,
                                            beats=beats,sectors_per_beat=4),
                fixed_source_parameters=dict(RL=57,WC=4,transport_NP=59,transport_ND=26),
                launch_to_counter_origin_qualified=False,
                command_footprints=[dict(counter=first+b,read_sectors=list(range(a_sector+4*b,a_sector+4*b+4)),
                                        write_sectors=list(range(o_sector+4*b,o_sector+4*b+4)))
                                    for b in range(beats)],
                owner_footprints=dict(quadrant="NW",vm_reads=list(range(a_sector,a_sector+sectors)),
                                      vm_writes=list(range(o_sector,o_sector+sectors)),f20_targets=[48]),
                calendar_integration_required=True,
                cross_quadrant_producer_mapping_qualified=False)



def hc_pre_global_sum_fragment(*, words, selected_core, first_tree_edge, tag):
    """Emit runtime-only whole-row PRETREE/reducer commands for HC_PRE squares.

    This fragment requires the real square producer to present global blocks in
    the returned order on one quarter's 128 lane outputs. It supplies no square
    values, expected sum, RF join or rsqrt substitute. Padding follows csum8.
    """
    from hbm_static import su_pretree_lower as PT
    if (selected_core.get("master") != "ot_hbm_su_static_qcore_r13" or
            int(selected_core.get("params",{}).get("PRETREE",0)) != 1):
        raise ValueError("HC_PRE sum requires the selected native PRETREE core")
    if words<=0 or words%128 or words>8192 or not 0<=tag<1<<32:
        raise ValueError("whole-row PRETREE fragment requires complete aligned128 blocks")
    # This compiler's control is shape-only. Zero values establish its tree
    # structure; neither its dummy operands nor expected exports leave here.
    sc=PT.Schedule()
    sc.lower("sum",[0]*words,tag,first_tree_edge)
    tree=[]
    for block,(edge,(_,count,_)) in enumerate(sc.tree.items()):
        cmd=PT.tree_cmd_word(0,count)
        tree.append(dict(block=block,first_global_word=128*block,words=count,
                         serial_edge=edge,tree_cmd_hex=f"{cmd:012x}",
                         programme_mask_hex=f"{cmd<<2422:0618x}",
                         required_producer="actual lane ro_x=FP32(mixed_BF16 * mixed_BF16), never fixture squares"))
    red=[dict(serial_edge=e,red_cmd_hex=f"{PT.red_cmd_word(cmd):019x}",
              programme_mask_hex=f"{PT.red_cmd_word(cmd):0618x}")
         for e,cmd in sorted(sc.red.items())]
    return dict(schema="opentallas.hc_pre_runtime_sum_fragment.v1",status="producer_join_open",
                execution_qualified=False,qualifies_native_layer=False,
                words=words,selected_core=selected_core,programme_bits=2470,
                arithmetic_order="global csum8 and padded aligned binary tree, one whole-row quarter",
                required_runtime_square_blocks=tree,reducer_commands=red,
                tree_to_reducer_edges=PT.PT_RED,reducer_dependency_edges=PT.DEP,
                export_command_edge=sc.exps[0][0],export_tag=tag,
                remaining=["real all-row square producer/VM allocation at each declared edge",
                           "scalar export/RF stage and KIND2 rsqrt control",
                           "gain from released checkpoint HBM input and final BF16 multiply pass",
                           "current selected coupled RTL execution"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("fixtures", "contract", "l12", "bundle", "out"):
        ap.add_argument("--"+name, type=Path, required=True)
    ap.add_argument("--checkpoint", type=Path, default=RELEASED_SNAPSHOT,
                    help="released V4.1-Flash snapshot dir (default) -- the fixtures' golden weights")
    ap.add_argument("--boundary", type=Path)
    ap.add_argument("--source-plan", action="store_true")
    ap.add_argument("--record", type=int, default=30)
    ap.add_argument("--rank", default="0")
    ap.add_argument("--a-sector", type=lambda s:int(s,0), required=True)
    ap.add_argument("--o-sector", type=lambda s:int(s,0), required=True)
    ap.add_argument("--component-allocation", action="store_true")
    a = ap.parse_args()
    if a.boundary is None and not a.source_plan:
        ap.error("connected mode requires --boundary; --source-plan never qualifies execution")
    contract = json.loads(a.contract.read_text())
    root = contract["instances"]["hc_eng"]
    if root["master"] != "ot_hbm_hc_root_static":
        raise ValueError(f"unsupported selected root: {root['master']}")
    meta = json.loads((a.fixtures/"records.json").read_text())
    tag = next(x["tag"] for x in meta["priced_records_unmatched"] if x["i"] == a.record)
    rec = next(x for x in meta["records"][a.rank] if x["op"] == "HC.HC_MIX_POST" and x["tag"] == tag+" post")
    which = "attn" if "attn" in tag else "ffn"
    values, provenance = checkpoint_parameters(a.checkpoint, meta["layer"], which)
    with np.load(a.fixtures/"operands.npz") as z:
        A, O = (z[rec[k][n]["array"]].copy() for k,n in (("inputs","A"),("outputs","O")))
    boundary = json.loads(a.boundary.read_text()) if a.boundary else None
    tim = HC.timing_from_contract(a.contract, a.l12)
    doc = lower_mix_post(A, O, values, tim, record=a.record, a_sector=a.a_sector,
                        o_sector=a.o_sector, component_allocation=a.component_allocation, boundary=boundary)
    files = json.loads((a.bundle/"master_files.json").read_text())
    paths = sorted(set(files[root["master"]]+files["ot_hbm_host_cfg_leaf_se2"]))
    doc.update(record=a.record, fixture_record=rec["k"], tag=tag, checkpoint_input_provenance=provenance,
               selected_root=root, source_files=[dict(path=p,sha256=sha_file(a.bundle/p)) for p in paths],
               source_contract_sha256=sha_file(a.contract),
               fixture_logical_addresses=dict(A_word=rec["desc"]["A"][0],
                                               A_sector=rec["desc"]["A"][0]//8,
                                               O_word=rec["desc"]["O"][0],
                                               O_sector=rec["desc"]["O"][0]//8),
               allocation_note=("explicit relocated bounded component allocation; actual native L0 allocation not claimed"
                                if a.component_allocation else "caller-assigned common allocation; upstream projection remains open"))
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out/"connected_hc.json").write_text(json.dumps(doc,indent=1)+"\n")
    for key, name in (("root_programme_rows","root_programme.mem"),("root_table_rows","root_table.mem")):
        (a.out/name).write_text("\n".join(doc[key])+"\n")
    print(json.dumps({k:doc[k] for k in ("status","record","boundary_checked","root_schedule","owner_footprints")}))


if __name__ == "__main__":
    main()
