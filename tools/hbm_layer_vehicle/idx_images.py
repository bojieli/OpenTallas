#!/usr/bin/env python3
"""VEH-CUTS (10-19): IDX.TOPK record payload for the d4g GEN2b SW(+central IDX) slice vehicle.

Which quadrant carries IDX / ATT (die.v GEN2b 92accd203 pb_early, instance table):
  * IDX.TOPK (DS route.top6) runs on hb_idx__ctl (ot_hbm_idx_rootctl_static, SID 0) -> its ot_hbm_idx_topk_static
    engine reads the SW VM banks (vmb_SW0..7 read group 4 = rq4) and writes through the SW hub packet client 1
    (hb_vms_SW cq = {hb_idx__ctl__cq, hb_argmax__cq}).  Descriptor + go come from the central collar col_idx
    (col_idx__rec[155:0] / col_idx__go[0]); the VM bank owner grants come from calendar_SW (CP target 96 via hleaf_SW).
    => the record is executable on SW + hb_idx__ctl alone (cuts: swx = SW quadrant + central IDX; idxtk = hleaf_SW +
    calendar_SW + hb_vms_SW + vmb_SW0..7 + hb_idx__ctl, the minimum component).
  * IDX.INDEX (indexer frame) spans all four quadrants' hb_idx__qctl/op/q/s + the central xq tree / root / selector /
    link, with key lines from the SMs (svg_*__sm_packet): one quadrant + central root is the minimum vehicle; its
    programme (col_idx pw_*, hbm_idx_static_calendar) + SM key-line payload are NOT emitted here (SM payload open).
  * ATT.QK / ATT.PV run on the attention SMs sm_SW0..7 / sm_NW0..7 (ot_hbm_accel_smh_attn; SE / NE have none):
    commands = xc_SW* (tgt 192..195) cmd_ext + kv_desc and cp_svg_SW* rows, KV from HBM -> SM payload (open).

Payload of one TOPK record (all at the slice inputs whose driver is outside the slice):
  * calendar_SW programme (tools/hbm_vm_static_calendar.compile_schedule, universal layout, SW params): one word per
    edge from the compiler timeline of tools/hbm_idx_topk_static_vectors.schedule (written from the engine header,
    never read back from RTL): R = read group 4 on the sector's bank, H = hub bank_enable + bank_client 1 (and
    client_seq = write index), P = bank wslot packet-write code WG+2 = 4, A = response_enable[1] + response_seq;
    installed through host_cp_ingress (layer_images.CpBus, ingress rate), desc, one launch.
  * word 0 of the calendar is sampled at edge E0 = launch_edge + CAL_DELTA (measured on the calx cut);
    go is sampled at G = E0 + G_AFTER_E0 (col_idx__go D at G-1, the descriptor on col_idx__rec held from G-1);
  * VM preload (M, cyc 0, SW quarter 0): A (n FP32 words) at A_SEC.., the O sector zeroed;
  * checks (rec = priced i): the O sector = the ds_native fixture ids (words k..7 untouched = 0) at end + VM_SETTLE;
    topk_busy 1 inside the window and 0 after it; topk_fault / ctl fault / share_fault / hb_vms_SW vmstat 0.
Golden: hgi_sim.machine.topk_ids(A, k, asc) must equal the fixture O (self-test, else status golden_mismatch).

  PYTHONPATH=tools python3 -m hbm_layer_vehicle.idx_images --fixtures results/rtl/hbm_ds_layer_tput_1018/fixtures/L02
      --boundary slice/boundary.json --out OUT [--cal-delta N] [--mutant]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

CAL_TGT = 96
IDX_RG, PKT_WCODE, IDX_CLIENT = 4, 4, 1      # SW bank read group 4 (rq4), packet write WG+2 (WG 2), hub client 1
CW = 2                                        # SW hub client field bits per bank (N = 2 clients + replay)
CAL_DELTA = 10                                # launch drive edge -> calendar word 0 sample edge (calx probe 10-19: D=10, 8/8 words)
G_AFTER_E0 = 2
VM_SETTLE = 16
A_SEC, O_SEC = 0x100, 0x180                   # quarter-0 sectors (bank = sector % 8)
FAULT_OUTS = ["hb_idx__ctl__topk_fault", "hb_idx__ctl__fault", "hb_idx__ctl__share_fault"]


def rec_word(k, order, n, m, a_base, a_str, o_base, o_str, a_mirror=0, o_mirror=0, has_r=0, r_base=0, r_str=0):
    """col_idx__rec[155:0] (die.v hb_idx__ctl topk_* slices)."""
    f = [(k, 0, 4), (order, 4, 1), (n, 5, 20), (m, 25, 20), (a_mirror, 45, 1), (a_base, 46, 18), (a_str, 64, 18),
         (o_mirror, 82, 1), (o_base, 83, 18), (o_str, 101, 18), (has_r, 119, 1), (r_base, 120, 18), (r_str, 138, 18)]
    v = 0
    for x, lo, w in f:
        assert 0 <= x < 1 << w, (x, lo, w)
        v |= x << lo
    return v


def calendar_words(ev, E0):
    """compiler events (kind, sample edge, val) -> universal calendar word dicts, word i sampled at E0 + i."""
    last = max(e for _, e, _ in ev)
    assert min(e for _, e, _ in ev) >= E0, "calendar event before word 0"
    words = [dict() for _ in range(last - E0 + 1)]
    for kind, e, val in ev:
        w = words[e - E0]
        if kind == "R":
            assert not (w.get("rslot_v", 0) >> val) & 1, ("read bank double-booked", e)
            w["rslot_v"] = w.get("rslot_v", 0) | 1 << val
            w["rslot"] = w.get("rslot", 0) | IDX_RG << (3 * val)
        elif kind == "H":
            assert not (w.get("bank_enable", 0) >> val) & 1
            w["bank_enable"] = w.get("bank_enable", 0) | 1 << val
            w["bank_client"] = w.get("bank_client", 0) | IDX_CLIENT << (CW * val)
        elif kind == "P":
            assert not (w.get("wslot_v", 0) >> val) & 1
            w["wslot_v"] = w.get("wslot_v", 0) | 1 << val
            w["wslot"] = w.get("wslot", 0) | PKT_WCODE << (3 * val)
        elif kind == "A":
            assert not (w.get("response_enable", 0) >> IDX_CLIENT) & 1, ("two responses on one edge", e)
            w["response_enable"] = w.get("response_enable", 0) | 1 << IDX_CLIENT
            w["response_seq"] = w.get("response_seq", 0) | val << (2 * IDX_CLIENT)
        else:
            raise ValueError(kind)
    return words


def topk_record(A, O, i_rec, k, order, cal_delta=CAL_DELTA, t_frames=16, mutant=False, shift=None, pin_in=1):
    """one IDX.TOPK record (m = 1 row).  Returns dict(events, checks, numbers)."""
    import hbm_vm_static_calendar as C
    from hbm_idx_topk_static_vectors import schedule, ACK
    from hbm_layer_vehicle.layer_images import CpBus
    from hgi_sim.machine import topk_ids
    A = np.asarray(A, np.uint32)
    O = np.asarray(O, np.uint32)
    n = len(A)
    gold = topk_ids(A.view(np.float32), k, bool(order)).astype(np.uint32)
    if not np.array_equal(gold, O):
        return dict(status="golden_mismatch", reasons=[f"topk_ids {gold.tolist()} != fixture O {O.tolist()}"])
    rec = dict(k=k, order=order, n=n, m=1, am=0, a=A_SEC * 8, a_str=n, o=O_SEC * 8, o_str=k, has_r=0, r=0, r_str=0)
    # pin_in 1 (VEH-TOPKFIX 10-19): every d4g quadrant binds hfd_vms_bank_native_q0_faces (literal bank input pin
    # flops): engine capture n+9, hub echo +1, ACK 13 -- needs hb_idx__ctl = ot_hbm_idx_rootctl_static_pin.
    ev0, end0, legal = schedule(rec, 0, pin_in)
    assert legal
    # calendar: the events are relative to G; word 0 is sampled at E0 = G - G_AFTER_E0
    # shift (probe only, never evidence): per calendar event kind R/H/P/A edge offset, to localise a die timing
    # mismatch against the engine's documented timeline; recorded in the replay assumptions
    shift = shift or {}
    rel = [(kind, e + G_AFTER_E0 + shift.get(kind, 0), v) for kind, e, v in ev0]
    words = calendar_words(rel, 0)
    abi = json.loads((ROOT / "results/arch/hbm_vm_static_1014/quadrant_abi.json").read_text())
    spec = C.layout(abi, "SW", universal=True)
    # client_seq (hub, sampled with cq on the H edge) = the write index; a single-sector O (m 1, k <= 8 aligned) is
    # write 0 -> field 0.  A split output would need seq 1 on its second H edge.
    assert sum(1 for kind, _, _ in rel if kind == "H") == 1, "split O / R output: client_seq 1 not emitted"
    cal = C.compile_schedule(spec, dict(base=0, loops=1, cycles=words))
    bus = CpBus(t_frames, src="image:CAL")
    bus.install(CAL_TGT, [int(w["data"], 16) for w in cal["configuration_writes"]], 0)
    bus.desc(CAL_TGT, 0, len(words), 1)
    bus.src = "image:launch"
    cL = bus.launch()
    E0 = cL + cal_delta
    G = E0 + G_AFTER_E0
    end = G + end0
    ev = list(bus.ev)
    rw = rec_word(k, order, n, 1, A_SEC * 8, n, O_SEC * 8, k)
    ev.append(dict(k="D", dom="stream", cyc=G - 1, port="col_idx__rec", val=f"{rw:x}", src="image:IDX_desc", rec=i_rec))
    ev.append(dict(k="D", dom="stream", cyc=G - 1, port="col_idx__go", val="1", src="image:IDX_go", rec=i_rec))
    ev.append(dict(k="D", dom="stream", cyc=G, port="col_idx__go", val="0", src="image:IDX_go", rec=i_rec))
    ev.append(dict(k="D", dom="stream", cyc=end + 8, port="col_idx__rec", val="0", src="image:IDX_desc", rec=i_rec))
    Ain = A.copy()
    if mutant:                                   # witness: the best-scored id loses its sign -> a different top-k
        j = int(gold[0]) if not order else int(topk_ids(A.view(np.float32), 1, False)[0])
        Ain[j] ^= np.uint32(0x80000000)
    ns = -(-n // 8)
    for j in range(ns):
        s = A_SEC + j
        w8 = [int(x) for x in Ain[8 * j: 8 * j + 8]] + [0] * max(0, 8 * j + 8 - n)
        val = sum(w << (32 * b) for b, w in enumerate(w8))
        ev.append(dict(k="M", dom="stream", cyc=0, mem="vm", quarter=0, sector=s, bank=s % 8, row=(s & 0x1fff) >> 3,
                       val=f"{val:064x}", src="fixture:A" + (" (MUTANT sign flip)" if mutant else ""), rec=i_rec))
    ev.append(dict(k="M", dom="stream", cyc=0, mem="vm", quarter=0, sector=O_SEC, bank=O_SEC % 8,
                   row=(O_SEC & 0x1fff) >> 3, val="0" * 64, src="image:O_zero", rec=i_rec))
    T = end + VM_SETTLE
    oval = sum(int(x) << (32 * b) for b, x in enumerate(O))
    chk = [dict(k="C", dom="stream", cyc=T, port=f"vm:{O_SEC:x}", val=f"{oval:064x}", mask="f" * 64,
                src="golden:ds_native_fixture O (+ untouched words 0)", rec=i_rec),
           dict(k="C", dom="stream", cyc=G + 4, port="hb_idx__ctl__topk_busy", val="1", src="check:busy_window",
                rec=i_rec),
           dict(k="C", dom="stream", cyc=end + 4, port="hb_idx__ctl__topk_busy", val="0", src="check:busy_window",
                rec=i_rec),
           dict(k="C", dom="stream", cyc=T, port="hb_vms_SW__vmstat", val="0", src="check:vm_status", rec=i_rec)]
    chk += [dict(k="C", dom="stream", cyc=T, port=p, val="0", src="check:no_fault", rec=i_rec) for p in FAULT_OUTS]
    return dict(status="emitted", n=n, k=k, order=order, launch_cyc=cL, cal_delta=cal_delta, E0=E0, G=G,
                engine_end_rel_G=end0, end=end, check_cyc=T, ack=ACK + pin_in, pin_in=pin_in, calendar_words=len(words),
                calendar_configuration_writes=len(cal["configuration_writes"]), rec_word=hex(rw),
                expected_O=O.tolist(), events=ev, checks=chk, mutant=bool(mutant))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fixtures", type=Path, required=True)
    ap.add_argument("--boundary", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cal-delta", type=int, default=CAL_DELTA)
    ap.add_argument("--rank", default="0")
    ap.add_argument("--name-prefix", default=None)
    ap.add_argument("--pin-in", type=int, default=1, help="1 = pin-registered VM banks (GEN2b faces; engine "
                    "ot_hbm_idx_rootctl_static_pin), 0 = historical non-face timing (capture n+8, ACK 12)")
    ap.add_argument("--mutant", action="store_true", help="also emit the sign-flip witness replay")
    ap.add_argument("--probe-shift", default="", help="PROBE ONLY: e.g. R=1,A=1 shifts calendar event kinds (name suffix _s<..>)")
    a = ap.parse_args()
    shift = {kv.split('=')[0]: int(kv.split('=')[1]) for kv in a.probe_shift.split(',') if kv}
    meta = json.loads((a.fixtures / "records.json").read_text())
    z = np.load(a.fixtures / "operands.npz")
    L = meta["layer"]
    prefix = a.name_prefix or f"ds_l{L}"
    bnd = json.loads(a.boundary.read_text())
    ins = {e["name"] for e in bnd["inputs"]}
    outs = {e["name"] for e in bnd["outputs"]}
    a.out.mkdir(parents=True, exist_ok=True)
    man = []
    for x in meta["records"][a.rank]:
        if x["op"] != "IDX.TOPK":
            continue
        pr = x.get("priced") or []
        i_rec = int(pr[0]["i"]) if pr else None
        ent = dict(k_layer=x["k"], tag=x["tag"], i=i_rec, op=x["op"],
                   priced_cycles=round(pr[0]["end"] - pr[0]["start"], 2) if pr else None,
                   priced_base_cost=pr[0].get("base_cost") if pr else None)
        if i_rec is None:
            man.append(dict(ent, status="unpriced"))
            continue
        A = np.asarray(z[x["inputs"]["A"]["array"]]).view(np.uint32)
        O = np.asarray(z[x["outputs"]["O"]["array"]]).view(np.uint32)
        k = len(O)
        order = 1 if np.all(np.diff(O.astype(np.int64)) > 0) else 0      # route.top6: ascending ids (TOPK_ASC)
        parts = []
        for mut in ([False, True] if a.mutant else [False]):
            g = topk_record(A, O, i_rec, k, order, cal_delta=a.cal_delta, mutant=mut, shift=shift, pin_in=a.pin_in)
            if g["status"] != "emitted":
                ent.update(g)
                break
            evs = g["events"] + g["checks"]
            for e in evs:
                if e["k"] == "D":
                    assert e["port"] in ins, e["port"]
                elif e["k"] == "C" and not e["port"].startswith("vm:"):
                    assert e["port"] in outs, e["port"]
            name = f"{prefix}_idx_r{i_rec:03d}" + ("_mut_sign" if mut else "") + \
                ("_probe_" + "".join(f"{k_}{v_:+d}" for k_, v_ in sorted(shift.items())) if shift else "")
            rep = dict(schema="opentallas.hbm_slice_replay.v1", slice=bnd.get("slice_top"), design="ds", layer=str(L),
                       record=i_rec, tag=x["tag"], lane="VEH-TOPKFIX" if a.pin_in else "VEH-CUTS", scope="component_probe",
                       state_seed_provenance=["fixture:ds_native A operand (VM preload)", "image:O sector zeroed"],
                       assumptions=[f"calendar word 0 sampled at launch + {a.cal_delta} (calx cut measurement)",
                                    f"engine timeline PIN_IN {a.pin_in} (read capture n+{8 + a.pin_in}, "
                                    f"ACK {12 + a.pin_in}): the run checks it",
                                    "calendar_SW = IDX-only programme (sole VM owner in this replay)"] +
                                   ([f"PROBE calendar shift {shift} (not evidence)"] if shift else []),
                       events=sorted(evs, key=lambda e: (e["dom"], e["cyc"], e["k"])))
            txt = json.dumps(rep) + "\n"
            (a.out / f"{name}.json").write_text(txt)
            parts.append(dict(name=name, mutant=mut, events=sum(1 for e in evs if e["k"] != "M"),
                              vm_preload=sum(1 for e in evs if e["k"] == "M"), cycles=g["check_cyc"] + 64,
                              replay_sha256=hashlib.sha256(txt.encode()).hexdigest()))
            if not mut:
                ent.update({kk: v for kk, v in g.items() if kk not in ("events", "checks")})
        ent.update(replays=parts)
        man.append(ent)
    doc = dict(schema="opentallas.hbm_idx_images.v1", lane="VEH-CUTS", fixtures=str(a.fixtures), layer=L,
               cal_delta=a.cal_delta, records=man)
    (a.out / f"{prefix}_idx_manifest.json").write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(dict(layer=L, records=[(m["i"], m.get("status"), [p["name"] for p in m.get("replays", [])])
                                            for m in man])))


if __name__ == "__main__":
    main()
