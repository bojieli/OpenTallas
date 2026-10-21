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
from hbm_layer_vehicle.layer_images import CpBus

CHECKPOINT_SHA256 = "f96ae55457396bc881ee592f7f7eb66d6f510b6be76faf40dca9a5629c0fa74d"
REQUIRED_INSTANCES = ("hc_eng", "hleaf_SE", "hc_SW", "calendar_SW", "hleaf_SW", "hb_ckgen")
ROOT_TGT, TABLE_TGT = 164, 165
# Selected SE leaf2 -> target pin/start -> sequencer pin/start -> event/root edge.
# This is an explicit source schedule to be checked by the coupled RTL case.
ROOT_APPLY_AFTER_LAUNCH = 8
TAIL_RESULT_LATENCY = 496
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


def checkpoint_parameters(path, layer, which="attn", expected_sha=CHECKPOINT_SHA256):
    """Read only the released input tensors; expected output is not an argument."""
    path = Path(path)
    actual_sha = sha_file(path)
    if actual_sha != expected_sha:
        raise ValueError(f"checkpoint SHA256 mismatch: {actual_sha}")
    values, provenance = {}, {}
    with path.open("rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(n))
        for suffix, count in (("base", 24), ("scale", 3)):
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
            provenance[suffix] = dict(tensor=name, dtype="F32", shape=[count],
                                      data_offsets=[lo, hi], sha256=hashlib.sha256(raw).hexdigest())
    return values, dict(checkpoint=str(path), checkpoint_sha256=actual_sha, tensors=provenance)


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
                   component_allocation, record=30, t0=16, boundary=None):
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
    table, programme, schedule = root_rows(parameters, timing["resp_phase"])
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("fixtures", "contract", "l12", "bundle", "checkpoint", "out"):
        ap.add_argument("--"+name, type=Path, required=True)
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
