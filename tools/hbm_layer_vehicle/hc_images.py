#!/usr/bin/env python3
"""VEH-FMT-COLL2/HC (10-19): HC record payloads for the d4g SW-quadrant slice vehicle (GEN2 RTL) -- the hc_SW quadrant
hub (ot_hbm_hc_qhub_static, strap tgt 108) programme + its calendar_SW VM grants + the hc_eng (root, OUTSIDE the slice)
far end, for the HC.HC_MIX_POST record of the ds_native fixtures (gathered-mix / G22 form of HC.HC_MIX).

Static compiler of the qhub programme (no compiler existed): ONE 79-bit word per stream edge (ot_vms_calendar_static
W 79 inside ot_hbm_hc_q_static, programme rows {c7a1, pc, word} through ot_static_program_target, PCW 10):
  [0] residual_launch [4:1] residual_npos [20:5] residual_base [21] gather_phase [22] gather_launch [26:23] gather_npos
  [42:27] gather_base [58:43] gather_stride [59] store_slot [75:60] result_base [78:76] store_position
  (rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_q_static.sv:105-114; qhub_word() / test_hc_images.py pin it).
Timing (derived from the masters of the sw2 bundle, pre-checked on that RTL by tb_hc_replay.sv):
  launch D at cL on host_cp_ingress__launch_v -> hleaf_SW 2 flops -> target pin flop -> start -> calendar 4 edges:
  programme word k is on the qhub's c[] in the cycle after edge cL + PROG_OUT + k (PROG_OUT 9), sampled at edge
  cL + 10 + k.  calendar_SW (hfd_hgi_vm_calendar_f20, same leaf group a, same target + calendar pipeline) has the same
  word timing, so a common launch aligns qhub word k with calendar word k.
  GATHER (gathered-mix reader, RESP_PHASE 23): launch word g0 -> request (3 sectors, 3 banks, one edge) combinational
  in word g0+1's cycle (needs gather_phase there) -> lg_rq flop -> hc_SW<k> leaf flop -> the tap samples at the edge
  of word g0+3: calendar_SW lg_local_read tap 2 (bits 16+b) in word g0+3, bank group-0 read slot (rslot_v b, owner 0)
  in word g0+9 (hbm_vm_static_calendar fixed LG transport, +2 per tap); response sampled at word g0+24 (gather_phase
  there too: rr routes to the reader only under gather_phase, else the residual reader faults); gathered_mix rows
  0..23 of position 0 on the slice outputs hc_SW__gathered_mix_* AT edges cL + 35 + g0 + r.
  RESULT / STORE: hc_eng__result_v/result/result_position (slice inputs) in the cycle of word s-1 (pin flop) and
  store_slot in word s (the store faults on a store slot without a pinned result); lg_wq flop -> leaf -> tap samples at
  word s+2: calendar_SW lg_local_write tap 2 in word s+2, write slot (wslot_v b, owner 0) in word s+8.
  The root hc_eng is OUTSIDE the slice: its G22 tail (tools/rtl_hbm_hc_eng_static_gate.py --mode g22: gathered words on
  its pins at TB+2+o, tail launch TB+32, emit TB+529) puts the result on the pins EMIT_AFTER_ROW0 = 527 edges after the
  edge row 0 leaves the qhub (+-1 edge: the root is replayed, not simulated here).
  The qhub programme runs as TWO launches (segment A = gather, rows 0..; segment B = store, installed with A before the
  first descriptor because a cfg row after a descriptor restarts the install set): the 527-edge root latency would
  otherwise cost ~550 idle programme rows (40 ingress edges each).
Data = the bit-exact ds_native fixture: HC_MIX_POST A (24 raw mixes, FP32) gathered from VM, O (24 post mixes) = the
root's result, stored to VM.  Fixture TP-96 rank 0 owns NO mix row (rows 24 r / 96 .. 24 (r + 1) / 96 = 0..0), so
the projection part of HC.HC_MIX (residual x waves -> hcb banks -> qcen subtree sums ps) has no rank-0 operands: the
HC weight rows are not in the fixture (HC_MIX_ROWS B = HC aperture, absent for rank 0) -> 'projection_open'.
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

HC_TGT, CAL_TGT = 108, 96
QW = 79
FIELDS = dict(residual_launch=(0, 1), residual_npos=(1, 4), residual_base=(5, 16), gather_phase=(21, 1),
              gather_launch=(22, 1), gather_npos=(23, 4), gather_base=(27, 16), gather_stride=(43, 16),
              store_slot=(59, 1), result_base=(60, 16), store_position=(76, 3))
PROG_OUT = 9                    # word k on c[] after edge cL + PROG_OUT + k (launch D edge cL)
RESP_PHASE = 23
LG_GRANT = 2                    # tap samples 2 edges after the hub's combinational request (hub flop + leaf flop)
LG_ARRIVE = 6                   # calendar tap-2 grant word -> bank group-0 slot word (hbm_vm_static_calendar)
GATHER_WORDS = RESP_PHASE + 3   # gather_phase words 0 .. 25
EMIT_AFTER_ROW0 = 527           # root G22: emit TB+529 vs gathered row 0 on its pins at TB+2
STORE_PAD = 4                   # segment B: store word index s
VM_SETTLE = 40
SFAULT_MASK = (1 << 14) | (1 << 11) | (1 << 10)      # hleaf_SW s_fault: hc_SW hcq, calendar_SW fault / tgt_fault
SREADY_MASK = (1 << 10) | (1 << 7)                   # hleaf_SW s_ready: hc_SW configured, calendar_SW tgt_configured


def qhub_word(**f):
    w = 0
    for k, v in f.items():
        lo, n = FIELDS[k]
        assert 0 <= int(v) < 1 << n, (k, v)
        w |= int(v) << lo
    assert w < 1 << QW
    return w


def prog_rows(words, base=0):
    return [(0xc7a1 << 240) | ((base + j) << 224) | w for j, w in enumerate(words)]


def sec16(q, idx):
    assert 0 <= idx < 1 << 13
    return (q << 13) | idx


def word256(words8):
    v = 0
    for j, w in enumerate(words8):
        v |= int(w) << (32 * j)
    return v


def cal_spec():
    import hbm_vm_static_calendar as C
    abi = json.loads((ROOT / "results/arch/hbm_vm_static_1014/quadrant_abi.json").read_text())
    return C, C.layout(abi, "SW", universal=True)


def cal_programme(n, grants, base):
    """calendar_SW rows: n words, grants = [(word, 'r'|'w', bank)] -> tap-2 LG bit at word, group-0 slot at word+6."""
    C, spec = cal_spec()
    cyc = [dict() for _ in range(n)]
    for w, kind, b in grants:
        f = "lg_local_read" if kind == "r" else "lg_local_write"
        cyc[w][f] = cyc[w].get(f, 0) | (1 << (16 + b))
        a = w + LG_ARRIVE
        sv = "rslot_v" if kind == "r" else "wslot_v"
        cyc[a][sv] = cyc[a].get(sv, 0) | (1 << b)              # owner field 0 = LG group 0
    prog = C.compile_schedule(spec, dict(base=base, loops=1, cycles=cyc))
    return [int(x["data"], 16) for x in prog["configuration_writes"]], cyc


def mix_post_record(A, O, i_rec, q=0, a_idx=0x40, o_idx=0x48, t0=16, res_shift=0, grant_shift=0, flip=None):
    """HC_MIX_POST (G22 form) for quadrant q: gather A (24 FP32) from VM -> gathered_mix outputs; root result O (24 FP32)
    replayed on hc_eng__result -> stored to VM.  Mutant knobs: res_shift (far-end edges), grant_shift (calendar read
    grant word), flip (bit of the A preload)."""
    from hbm_layer_vehicle.layer_images import CpBus, AXI_WRITE_EDGES
    A = np.asarray(A, np.uint32)
    O = np.asarray(O, np.uint32)
    assert len(A) == 24 and len(O) == 24
    asec, osec = sec16(q, a_idx), sec16(q, o_idx)
    # ---- qhub programme: segment A (rows 0..) gather, segment B store
    wa = [qhub_word(gather_phase=1, gather_launch=1, gather_npos=1, gather_base=asec, gather_stride=0)] + \
         [qhub_word(gather_phase=1)] * (GATHER_WORDS - 1)
    s = STORE_PAD
    wb = [0] * s + [qhub_word(store_slot=1, result_base=osec, store_position=0)]
    nA, nB = len(wa), len(wb)
    q_rows = prog_rows(wa, 0) + prog_rows(wb, nA)
    # ---- calendar_SW: segment A read grants (word 3 + shift), segment B write grants (word s + 2)
    ga = 1 + LG_GRANT + grant_shift
    ca, cyc_a = cal_programme(ga + LG_ARRIVE + 2, [(ga, "r", (asec + j) % 8) for j in range(3)], 0)
    cb, cyc_b = cal_programme(s + LG_GRANT + LG_ARRIVE + 2, [(s + LG_GRANT, "w", (osec + j) % 8) for j in range(3)],
                              len(ca))
    ev, chk = [], []
    bus = CpBus(t0, src="image:HC")
    bus.install(HC_TGT, q_rows, 0)
    bus.src = "image:CAL"
    bus.install(CAL_TGT, ca + cb, 0)

    def descs(qb, ql, cb_, cl):
        bus.src = "image:HC"
        d1 = bus.desc(HC_TGT, qb, ql, 1)
        bus.src = "image:CAL"
        d2 = bus.desc(CAL_TGT, cb_, cl, 1)
        # targets scan their rows (1 / edge) after the descriptor: launch only after the longer scan (+ leaf/pin flops)
        return max(d1 + (ql - qb), d2 + (cl - cb_)) + 8
    ready = descs(0, nA, 0, len(ca))
    bus.t = max(bus.t, ready - AXI_WRITE_EDGES)
    bus.src = "image:launch"
    cL = bus.launch()
    chk.append(dict(k="C", dom="stream", cyc=cL, port="hleaf_SW__s_ready", val=f"{SREADY_MASK:x}",
                    mask=f"{SREADY_MASK:x}", src="check:targets_configured", rec=i_rec))
    A0 = cL + PROG_OUT + 1                         # edge sampling word 0
    G0 = A0 + RESP_PHASE + 2                       # row 0 AT this edge
    for r in range(24):
        for p, v in (("v", 1), ("row", r), ("pos", 0), ("data", int(A[r]))):
            chk.append(dict(k="C", dom="stream", cyc=G0 + r, port=f"hc_SW__gathered_mix_{p}", val=f"{v:x}",
                            src="golden:ds_native_fixture" if p == "data" else "check:gather_stream", rec=i_rec))
    chk.append(dict(k="C", dom="stream", cyc=G0 + 24, port="hc_SW__gathered_mix_v", val="0", src="check:gather_stream",
                    rec=i_rec))
    # ---- segment B: descriptors after segment A is done, launch so that the far-end result meets store word s
    T_res = (G0 - 1) + EMIT_AFTER_ROW0             # result on the hub's pins after this edge (row 0 left after G0 - 1)
    cL2 = T_res - PROG_OUT + 1 - s                 # result in word s-1's cycle: after edge cL2 + PROG_OUT + s - 1
    bus.t = max(bus.t, A0 + nA + 8)
    ready = descs(nA, nA + nB, len(ca), len(ca) + len(cb))
    if ready > cL2:
        raise ValueError(f"segment B descriptors ({ready}) miss the launch edge {cL2}")
    bus.t = cL2 - AXI_WRITE_EDGES
    bus.src = "image:launch"
    got = bus.launch()
    assert got == cL2, (got, cL2)
    ev += bus.ev
    chk.append(dict(k="C", dom="stream", cyc=cL2, port="hleaf_SW__s_ready", val=f"{SREADY_MASK:x}",
                    mask=f"{SREADY_MASK:x}", src="check:targets_configured", rec=i_rec))
    # ---- far end: root hc_eng result pins (SW = quadrant 0 slice of the 4-quadrant bus)
    res = word256(O[:8]) | (word256(O[8:16]) << 256) | (word256(O[16:]) << 512)
    tr = T_res + res_shift
    ev += [dict(k="D", dom="stream", cyc=tr, port="hc_eng__result_v", val="1", src="farend:hc_eng", rec=i_rec),
           dict(k="D", dom="stream", cyc=tr, port="hc_eng__result_position", val="0", src="farend:hc_eng", rec=i_rec),
           dict(k="D", dom="stream", cyc=tr, port="hc_eng__result", val=f"{res:x}", src="farend:hc_eng", rec=i_rec),
           dict(k="D", dom="stream", cyc=tr + 1, port="hc_eng__result_v", val="0", src="farend:hc_eng", rec=i_rec)]
    # ---- VM preload (A) + checks
    pre = [word256(A[8 * j: 8 * j + 8]) for j in range(3)]
    if flip is not None:
        pre[flip // 256] ^= 1 << (flip % 256)
    for j in range(3):
        sct = asec + j
        ev.append(dict(k="M", dom="stream", cyc=0, mem="vm", quarter=q, sector=sct, bank=sct % 8,
                       row=(sct & 0x1fff) >> 3, val=f"{pre[j]:064x}", src="image:VM_preload", rec=i_rec))
    T = cL2 + PROG_OUT + 1 + s + LG_GRANT + VM_SETTLE
    full = "ffffffff" * 8
    for j in range(3):
        chk.append(dict(k="C", dom="stream", cyc=T, port=f"vm:{osec + j:x}", val=f"{word256(O[8 * j: 8 * j + 8]):064x}",
                        mask=full, src="golden:ds_native_fixture", rec=i_rec))
        chk.append(dict(k="C", dom="stream", cyc=T, port=f"vm:{asec + j:x}", val=f"{word256(A[8 * j: 8 * j + 8]):064x}",
                        mask=full, src="golden:ds_native_fixture(A kept)", rec=i_rec))
    chk.append(dict(k="C", dom="stream", cyc=T, port="hleaf_SW__s_fault", val="0", mask=f"{SFAULT_MASK:x}",
                    src="check:no_fault", rec=i_rec))
    chk.append(dict(k="C", dom="stream", cyc=T, port="hc_SW__eng_fault", val="0", src="check:no_fault", rec=i_rec))
    return dict(status="emitted", form="G22 gathered-mix (TP-96 rank-0 HC_MIX_POST: gather + root tail + store)",
                a_sector=asec, o_sector=osec, launch=[cL, cL2], word0_edge=[A0, cL2 + PROG_OUT + 1], gather_row0_at=G0,
                result_pins_after=T_res, store_word=s, check_cyc=T, qhub_rows=dict(A=nA, B=nB),
                calendar_rows=dict(A=len(ca), B=len(cb)), emit_after_row0=EMIT_AFTER_ROW0,
                words_checked=24 + 24, events=ev, chk=chk)


PRE_PORTS = {"host_cp_ingress__cfg_v": 0, "host_cp_ingress__cfg_target": 1, "host_cp_ingress__cfg_addr": 2,
             "host_cp_ingress__cfg_data": 3, "host_cp_ingress__desc_v": 4, "host_cp_ingress__desc_base": 5,
             "host_cp_ingress__desc_limit": 6, "host_cp_ingress__desc_loops": 7, "host_cp_ingress__launch_v": 8,
             "hc_eng__result_v": 10, "hc_eng__result_position": 11, "hc_eng__result": 12,
             "hc_SW__gathered_mix_v": 20, "hc_SW__gathered_mix_row": 21, "hc_SW__gathered_mix_pos": 22,
             "hc_SW__gathered_mix_data": 23, "hc_SW__eng_fault": 24, "hleaf_SW__s_fault": 25, "hleaf_SW__s_ready": 26}


def pre_events(evs):
    """replay events -> tb_hc_replay.sv event file: '<cyc> <kind 1 D|2 C|3 M> <port> <sector|mask hex> <value hex>'."""
    out = []
    for e in sorted(evs, key=lambda e: (e["cyc"], e["k"])):
        if e["k"] == "M":
            out.append(f"0 3 0 {e['sector']:x} {e['val']}")
        elif e["port"].startswith("vm:"):
            out.append(f"{e['cyc']} 2 30 {e['port'][3:]} {e['val']}")
        else:
            m = e.get("mask", "ffff") if e["port"].startswith("hleaf") else "ffff"
            out.append(f"{e['cyc']} {1 if e['k'] == 'D' else 2} {PRE_PORTS[e['port']]} {m} {e['val']}")
    return "\n".join(out) + "\n"


def priced_hc(meta, recs):
    """priced HC.HC_MIX records of the layer (unmatched in the fixture) keyed by tag; HC_MIX_POST tag = '<tag> post'."""
    return {x["tag"]: x["i"] for x in meta.get("priced_records_unmatched", []) if x["op"] == "HC.HC_MIX"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fixtures", type=Path, required=True)
    ap.add_argument("--boundary", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--rank", default="0")
    ap.add_argument("--nev", type=int, default=6309)
    ap.add_argument("--name-prefix", default=None)
    ap.add_argument("--pre-events", type=Path, help="also write <name>.events.txt for tb_hc_replay.sv here")
    ap.add_argument("--mutants", action="store_true", help="also write mutant pre-check event files (witnesses)")
    a = ap.parse_args()
    meta = json.loads((a.fixtures / "records.json").read_text())
    z = np.load(a.fixtures / "operands.npz")
    recs = meta["records"][str(a.rank)]
    L = meta["layer"]
    prefix = a.name_prefix or (f"ds_l{L}" if isinstance(L, int) else f"ds_{L}")
    bnd = json.loads(a.boundary.read_text())
    ins = {e["name"] for e in bnd["inputs"]}
    outs = {e["name"] for e in bnd["outputs"]}
    pri = priced_hc(meta, recs)
    a.out.mkdir(parents=True, exist_ok=True)
    man = []
    for x in recs:
        if x["op"] != "HC.HC_MIX_POST":
            continue
        base_tag = x["tag"][:-len(" post")] if x["tag"].endswith(" post") else x["tag"]
        i_rec = pri.get(base_tag)
        ent = dict(k_layer=x["k"], tag=x["tag"], op=x["op"], priced_op="HC.HC_MIX", i=i_rec,
                   projection="projection_open: HC.HC_MIX rows (residual x waves -> hcb banks -> qcen ps -> root) need the "
                              "HC weight rows; fixture TP-96 rank 0 owns no mix row (no HC_MIX_ROWS record / operands)")
        if i_rec is None:
            ent.update(status="unpriced", reasons=["no priced HC.HC_MIX with this tag"])
            man.append(ent)
            continue
        A = z[x["inputs"]["A"]["array"]]
        O = z[x["outputs"]["O"]["array"]]
        g = mix_post_record(A, O, i_rec)
        evs = sorted(g["events"] + g["chk"], key=lambda e: (e["dom"], e["cyc"], e["k"]))
        n_nm = sum(1 for e in evs if e["k"] != "M")
        assert n_nm <= a.nev - 1, n_nm
        for e in evs:
            if e["k"] == "D":
                assert e["port"] in ins, e["port"]
            elif e["k"] == "C" and not e["port"].startswith("vm:"):
                assert e["port"] in outs, e["port"]
        name = f"{prefix}_hc_r{i_rec:03d}"
        rep = dict(schema="opentallas.hbm_slice_replay.v1", slice=bnd.get("slice_top", "sw"), design="ds", layer=str(L),
                   record=i_rec, tag=x["tag"], lane="VEH-FMT-COLL2",
                   assumptions=["G22 gathered-mix form = fixture TP-96 rank 0 (no own mix rows): qhub gathers the 24 raw "
                                "mixes (HC_MIX_POST A) to the root, root result (HC_MIX_POST O) replayed as far end",
                                f"root emit {EMIT_AFTER_ROW0} edges after gathered row 0 (rtl_hbm_hc_eng_static_gate g22 "
                                "schedule, +-1 edge, root not in the slice)",
                                "VM sectors of A / O chosen in quadrant SW (no d4g HC vector layout exists)",
                                "calendar_SW = HC-only grants (sole VM owner in this replay)",
                                "projection part of HC.HC_MIX not replayed (weights absent from the fixture)"],
                   events=evs)
        txt = json.dumps(rep) + "\n"
        (a.out / f"{name}.json").write_text(txt)
        if a.pre_events:
            a.pre_events.mkdir(parents=True, exist_ok=True)
            (a.pre_events / f"{name}.events.txt").write_text(pre_events(evs))
            if a.mutants:
                for mn, kw in (("res_late", dict(res_shift=1)), ("grant_late", dict(grant_shift=1)),
                               ("a_bit", dict(flip=37))):
                    gm = mix_post_record(A, O, i_rec, **kw)
                    (a.pre_events / f"mut_{mn}_{name}.events.txt").write_text(pre_events(gm["events"] + gm["chk"]))
        ent.update({k: v for k, v in g.items() if k not in ("events", "chk")})
        ent.update(status="emitted", replays=[dict(name=name, events=n_nm, vm_preload=sum(1 for e in evs if e["k"] == "M"),
                                                    cycles=g["check_cyc"] + 64,
                                                    checks=sum(1 for e in evs if e["k"] == "C"),
                                                    replay_sha256=hashlib.sha256(txt.encode()).hexdigest())])
        man.append(ent)
    doc = dict(schema="opentallas.hbm_hc_images.v1", lane="VEH-FMT-COLL2", fixtures=str(a.fixtures), layer=L,
               records=man, counts={s: sum(1 for m in man if m["status"] == s) for s in sorted({m["status"] for m in man})},
               unpriced_hc=[x for x in meta.get("priced_records_unmatched", []) if x["op"].startswith("HC")])
    (a.out / f"{prefix}_hc_manifest.json").write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(dict(layer=L, counts=doc["counts"], replays=[p["name"] for m in man for p in m.get("replays", [])])))


if __name__ == "__main__":
    main()
