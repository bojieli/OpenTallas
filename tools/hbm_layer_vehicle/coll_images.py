#!/usr/bin/env python3
"""VEH-FMT-COLL (10-18): COLL record payloads for the d4g SW-quadrant slice vehicle (GEN2 RTL) -- COLL.ALL_GATHER,
on-die quadrant phase, through the per-quadrant gather master.

RTL of record (die.v GEN2, sw2 cut bundle):
  hcollgi_SW  ot_hgi_coll_gq_issue (strap tgt 176; F20 frames straight from host_cp_ingress__*, no leaf)
  hcollgl_SW  ot_hgi_coll_gq_land   hcollrs_SW / hcollks_SW  static VM read / kq-write owner splits
  hb_coll_SW  ot_hfd_coll_q3_hard_v8x (ring A stop = ot_hgi_coll_ring_ag, commands on ra_* from hcollgi_SW)
  hcollb_SW   ot_hgi_coll_ring_b_stop (ring B)
  calendar_SW hfd_hgi_vm_calendar_f20 (tgt 96, via hleaf_SW): VM bank owner grants (rslot group 3 = COLL read share,
              wslot code 2 = COLL kq write).  The banks (ot_vms_bank_q0_faces_body.sv:239-263) execute a read / write
              ONLY on an edge whose calendar slot names that owner -- every VM-touching replay must load calendar_SW.
Payload (one record):
  * gq descriptor row 0 (ot_hgi_coll_gq.sv header): {period, stride, dst, src, Bs, F, t_start, self, r2, qbg}, F20
    frame with the c7a1 / row header, desc (base 0, limit 1, loops 1);
  * calendar_SW programme (tools/hbm_vm_static_calendar.compile_schedule, universal layout): ONE word granting
    read group 3 + write code 2 on all 8 banks, looped over the gather window (COLL is the only VM owner in this
    replay); the exact per-edge reservations (tools/hgi_sim/collq_gather_1018.reservations) are listed in the
    manifest for the composed layer calendar;
  * one broadcast launch (host_cp_ingress__launch_v);
  * VM preload of SW's own slice (M events);
  * FAR ENDS at their scheduled edges (the canonical two-ring schedule, collq_gather_1018 / gq.sv header):
    global flit i -> ring r = i % R, ring index k = i // R, direction d = k & 1 (0 = CW), tag k % 8, ttl 3;
    issue IE(k) = FE + 1 + 3 (k >> 1) + (k & 1), FE = L + 3 + t_start (L = launch sample edge); ring inject
    c = IE + 29; arrival (rx_slot sample) at a stop c + 2 h, h = 1..3, source PREV^h(q) on CW / NEXT^h(q) on CCW,
    ring order q0 -> q1 -> q3 -> q2 -> q0 (SW 0, SE 1, NW 2, NE 3 = die.v qid straps).  SW's cw_i = hb_coll_NW.pr_cw_o /
    hcollb_NW.cw_o, ccw_i = hb_coll_SE.pr_ccw_o / hcollb_SE.ccw_o: the flit the neighbour's out register holds is
    driven at edge c + 2h - 2 (sampled into SW's pin register at c + 2h - 1, checked at c + 2h);
    flit = {v 1, kind 3, src q, src q, ttl 2, tag 3, 12'b0, data 256} (ot_hgi_coll_ring_ag_lane.sv inject);
  * CHECKS (C, rec = priced record i): SW's own injects (out at c + 1) and forwards (h = 1, 2: out at c + 2h + 1, ttl - 1)
    on hb_coll_SW.pr_cw_o / pr_ccw_o and hcollb_SW.cw_o / ccw_o; every landed VM sector (publish write sample
    IE + 34 + 2h, collq KQ_SHARE 2) and SW's own slice, at the last write + VM_SETTLE; gq / land / ring B / share
    faults 0; hcollgi_SW configured before the launch.
Data = the bit-exact ds_native fixture (results/rtl/hbm_ds_layer_tput_1018/fixtures/L<NN>): the record's gathered
vector O (n FP32 words).  ASSUMPTION (flagged per record): quadrant q holds the contiguous quarter q of O
(n/4 words = F sectors, plain mode, FP32 on the wire); the cross-DIE part of the DS all-gather (hb_coll link programme
over ep_S0/S1) is NOT in this payload: the hb_coll ISA (1536-b uop rows of ot_hgi_coll_issuer_m) has no production
compiler (rtl/.../p2p/STATIC_V4_CONTRACT.md: "full native programs remain open").
Run: replays exceeding the built TB's NEV split into p0 (drives + VM / fault checks) and p1 (drives + ring-output
checks); both run the whole gather.

  PYTHONPATH=tools python3 -m hbm_layer_vehicle.coll_images --fixtures results/rtl/hbm_ds_layer_tput_1018/fixtures/L00
      --boundary slice/boundary.json --out OUT [--records 2,33] [--R 2] [--t-start 40] [--nev 6309] [--name-prefix ds_l0]
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

GQ_TGT, CAL_TGT = 176, 96
NEXT = {0: 1, 1: 3, 3: 2, 2: 0}
PREV = {v: k for k, v in NEXT.items()}
QNAME = {0: "SW", 1: "SE", 2: "NW", 3: "NE"}
ISSUE_TO_INJECT, FIRE_FROM_LAUNCH, KQ_SHARE = 29, 3, 2
PUBLISH_WRITE = 32 + KQ_SHARE                      # + 2h after IE (collq_gather_1018 schedule())
VM_SETTLE = 16                                     # write sample -> SRAM cells (n+3 commit) + margin
COLL_RG, COLL_WCODE = 3, 2                         # calendar owner codes (collq_gather_1018 COLL_RG / COLL_WCODE)
IN_PORTS = {(0, 0): "hb_coll_NW__pr_cw_o", (0, 1): "hb_coll_SE__pr_ccw_o",
            (1, 0): "hcollb_NW__cw_o", (1, 1): "hcollb_SE__ccw_o"}
OUT_PORTS = {(0, 0): "hb_coll_SW__pr_cw_o", (0, 1): "hb_coll_SW__pr_ccw_o",
             (1, 0): "hcollb_SW__cw_o", (1, 1): "hcollb_SW__ccw_o"}
FAULT_OUTS = ["hcollgi_SW__fault", "hcollgi_SW__tgt_fault", "hcollgl_SW__fault", "hcollb_SW__fault",
              "hcollks_SW__fault", "hcollrs_SW__fault"]


def src_of(q, d, h):
    s = q
    for _ in range(h):
        s = PREV[s] if d == 0 else NEXT[s]
    return s


def issue_rel(k):
    return 1 + 3 * (k >> 1) + (k & 1)


def span(F, R, vm_rt=0):
    """fire -> last bank write sample (collq_gather_1018.span; --vm-rt V: span +V)."""
    K = (F + R - 1) // R
    return issue_rel(K - 1) + 38 + KQ_SHARE + vm_rt


def vm_rt_from_contract(contract, q="SW"):
    """TOK-FUNC-HBM-PAY (10-21): hcollgi_<q> VM_RT of a die revision's functional contract (l12 applied; 0 = GEN2 timing).
    ot_hgi_coll_gq.sv header: read REQUESTS keep their edges, every stage from the rr capture moves VM_RT later (ring-A
    inject c = issue + 29 + V, every landing write +V)."""
    c = json.loads(Path(contract).read_text())["instances"]
    return int(c[f"hcollgi_{q}"]["params"].get("VM_RT") or 0)


def flit(src, ttl, tag, data):
    """ring gather flit (ot_hgi_coll_ring_ag_lane.sv inject / ring_ag flit(): gath -> kind 3, dst field = qid)."""
    assert 0 <= data < 1 << 256 and 0 < ttl < 4
    return (1 << 279) | (3 << 277) | (src << 275) | (src << 273) | (ttl << 271) | ((tag & 7) << 268) | data


def sec16(q, idx, mirror=0):
    assert 0 <= idx < 1 << 13
    return (mirror << 15) | (q << 13) | idx


def word256(words8):
    """8 FP32 words (uint32), word j at bits [32j +: 32] (VM sector layout, layer_images M/C convention)."""
    v = 0
    for j, w in enumerate(words8):
        v |= int(w) << (32 * j)
    return v


def gq_row(F, R, t_start, src, dst, stride, period, qbg=0, self_land=0, Bs=0):
    """descriptor payload [223:0] (ot_hgi_coll_gq.sv rows 0..15)."""
    assert 0 < F < 1024 and stride % 8 == 0 and stride < 1 << 16 and period > t_start and period < 1 << 16
    return (qbg | (int(R == 2) << 1) | (self_land << 2) | (t_start << 3) | (F << 19) | (Bs << 29) | (src << 37) |
            (dst << 53) | (stride << 69) | (period << 85))


def f20_word(row, payload):
    return (0xc7a1 << 240) | (row << 224) | payload


def calendar_window(loops):
    """calendar_SW programme: one universal-layout word granting COLL read group 3 + kq write code 2 on all 8 banks,
    looped `loops` edges (hbm_vm_static_calendar.compile_schedule)."""
    import hbm_vm_static_calendar as C
    abi = json.loads((ROOT / "results/arch/hbm_vm_static_1014/quadrant_abi.json").read_text())
    spec = C.layout(abi, "SW", universal=True)
    rb, wb = spec["params"]["RB"], spec["params"]["WB"]
    word = dict(rslot_v=0xff, wslot_v=0xff, rslot=sum(COLL_RG << (rb * b) for b in range(8)),
                wslot=sum(COLL_WCODE << (wb * b) for b in range(8)))
    prog = C.compile_schedule(spec, dict(base=0, loops=loops, cycles=[word]))
    return prog, word


def gather_record(O, i_rec, R=2, t_start=40, dst_idx=0x100, t_frames=16, q=0, vm_rt=0, src_idx=None, transport=None):
    """COLL.ALL_GATHER of the n-word vector O (uint32) on the 4 quadrants, quadrant q's view.  Returns dict with
    events (replay.v1 D / C / M), the checks split by kind, cycles, and the model numbers.
    transport (coll_transport.load, TOKg 10-23): the die revision's lane timing; None = GEN2 / tb_coll_replay timing
    (0 launch edges, far-end flit at the stop the edge after the pin).  With it every gather edge (fire, issue, inject,
    ring outputs, landing writes, VM / fault checks) moves by launch_edges, and each far-end drive is issued
    ingress_edges[port] edges earlier than the stop arrival needs.  The host-ingress programme and the configured
    check keep their edges (they precede the launch lane)."""
    Ls = int(transport["launch_edges"]) if transport else 0
    ing = {p: int(v) for p, v in transport["ingress_edges"].items()} if transport else {}
    # TOKj-HBM 10-23: landing write lanes hcollgl -> hcollks -> vmb (per bank; absent in pre-kq profiles = 0)
    kqw = {int(b): int(v) for b, v in (transport.get("kq_write_edges") or {}).items()} if transport else {}
    from hbm_layer_vehicle.layer_images import CpBus
    O = np.asarray(O, np.uint32)
    n = len(O)
    if n % 32:
        return dict(status="format_open", reasons=[f"n={n}: quadrant slice n/4 not a whole number of 8-word VM "
                                                   "sectors (gq moves whole sectors)"])
    sw = n // 4
    F = sw // 8
    if F >= 1024:
        return dict(status="format_open", reasons=[f"F={F} sectors exceeds the 10-b descriptor field"])
    stride = -(-F // 8) * 8
    if dst_idx + 4 * stride > 1 << 13 or (src_idx is not None and src_idx + F > 1 << 13):
        return dict(status="format_open", reasons=["gathered vector exceeds the quadrant VM slice"])
    sl = {s: [word256(O[s * sw + 8 * j: s * sw + 8 * j + 8]) for j in range(F)] for s in range(4)}
    # own slice in place (segment q) by default; TOK-FUNC2-HBM-CX: src_idx = the layer placement of the own slice
    # (ot_hgi_coll_gq.sv reads g_src + i independently of the landing run dst + stride*s + i; self_land 0)
    src = sec16(q, dst_idx + q * stride if src_idx is None else src_idx)
    dst = sec16(q, dst_idx)
    period = t_start + 1
    payload = gq_row(F, R, t_start, src, dst, stride, period)
    ev, chk_vm, chk_ring, chk_misc = [], [], [], []
    # ---- programme on ONE ingress stream (layer_images.CpBus, ingress rate): gq row + desc, calendar row + desc, one
    # global launch (F30) that starts both armed targets
    sp = span(F, R, vm_rt)
    win = t_start + FIRE_FROM_LAUNCH + sp + 96           # calendar grant window (edges), from calendar start
    if transport and Ls - int(transport["calendar_launch_edges"]) > 96:
        return dict(status="format_open", reasons=[f"gq launch lane {Ls} trails the calendar launch lane by more than the "
                                                   "96-edge grant margin: window would end before the last write"])
    cal, cal_word = calendar_window(win)
    bus = CpBus(t_frames, src="image:COLL")
    bus.install(GQ_TGT, [f20_word(0, payload)], 0)
    bus.desc(GQ_TGT, 0, 1, 1)
    bus.src = "image:CAL"
    bus.install(CAL_TGT, [int(w["data"], 16) for w in cal["configuration_writes"]], 0)
    bus.desc(CAL_TGT, 0, 1, win)
    bus.src = "image:launch"
    cL = bus.launch()
    ev += bus.ev
    chk_misc.append(dict(k="C", dom="stream", cyc=cL, port="hcollgi_SW__configured", val="1", src="check:gq_target",
                         rec=i_rec))
    L = cL + 1
    FE = L + FIRE_FROM_LAUNCH + t_start + Ls
    # ---- VM preload: own slice
    for j in range(F):
        s = src + j
        ev.append(dict(k="M", dom="stream", cyc=0, mem="vm", quarter=q, sector=s, bank=s % 8, row=(s & 0x1fff) >> 3,
                       val=f"{sl[q][j]:064x}", src="image:VM_preload", rec=i_rec))
    # ---- far ends + ring output checks + landed sectors
    drv = {p: {} for p in IN_PORTS.values()}
    outc = {}
    last_w = 0
    landed = {}
    for i in range(F):
        r, k = i % R, i // R
        d = k & 1
        IE = FE + issue_rel(k)
        c = IE + ISSUE_TO_INJECT + vm_rt
        key = (OUT_PORTS[(r, d)], c + 1)
        assert key not in outc, ("ring output double-booked", key)
        outc[key] = flit(q, 3, k, sl[q][i])
        for h in (1, 2, 3):
            s = src_of(q, d, h)
            A = c + 2 * h
            p = IN_PORTS[(r, d)]
            D = A - 2 - ing.get(p, 0)
            assert D > cL, ("far-end drive before the launch", p, D, cL)
            assert D not in drv[p], ("far-end link double-booked", p, D)
            drv[p][D] = flit(s, 4 - h, k, sl[s][i])
            if h < 3:
                key = (OUT_PORTS[(r, d)], A + 1)
                assert key not in outc, ("ring output double-booked", key)
                outc[key] = flit(s, 3 - h, k, sl[s][i])
            w = IE + PUBLISH_WRITE + vm_rt + 2 * h          # master publish edge (GEN2 = bank write sample)
            sec = dst + s * stride + i
            wb_ = w + kqw.get(sec % 8, 0)                   # bank write sample after the kq write lane
            last_w = max(last_w, wb_)
            landed[sec] = (sl[s][i], w, wb_)
    for p, m in drv.items():
        for cyc in sorted(m):
            ev.append(dict(k="D", dom="stream", cyc=cyc, port=p, val=f"{m[cyc]:x}", src=f"farend:{p.split('__')[0]}",
                           rec=i_rec))
            if cyc + 1 not in m:
                ev.append(dict(k="D", dom="stream", cyc=cyc + 1, port=p, val="0", src=f"farend:{p.split('__')[0]}",
                               rec=i_rec))
    for (p, cyc), v in sorted(outc.items(), key=lambda x: (x[0][1], x[0][0])):
        chk_ring.append(dict(k="C", dom="stream", cyc=cyc, port=p, val=f"{v:x}", src="check:ring_out", rec=i_rec))
    T = last_w + VM_SETTLE
    full = "ffffffff" * 8
    for s_, (v, _, _) in sorted(landed.items()):
        chk_vm.append(dict(k="C", dom="stream", cyc=T, port=f"vm:{s_:x}", val=f"{v:064x}", mask=full,
                           src="golden:ds_native_fixture", rec=i_rec))
    for j in range(F):
        chk_vm.append(dict(k="C", dom="stream", cyc=T, port=f"vm:{src + j:x}", val=f"{sl[q][j]:064x}", mask=full,
                           src="golden:ds_native_fixture(own slice kept)", rec=i_rec))
    for p in FAULT_OUTS:
        chk_misc.append(dict(k="C", dom="stream", cyc=T, port=p, val="0", src="check:no_fault", rec=i_rec))
    # every landed sector must be on a distinct (bank, write edge) -- the conflict rule the master faults on
    wb = {}
    for s_, (_, w, _) in landed.items():
        assert (s_ % 8, w) not in wb, ("two landing writes on one bank edge", s_, w)
        wb[(s_ % 8, w)] = s_
    words_checked = 4 * F * 8
    exp_O = np.zeros(n, np.uint32)                        # reconstruct O from the checked sectors (self-test)
    for s in range(4):
        for j in range(F):
            v = landed[dst + s * stride + j][0] if s != q else sl[q][j]
            for b in range(8):
                exp_O[s * sw + 8 * j + b] = (v >> (32 * b)) & 0xffffffff
    assert np.array_equal(exp_O, O)
    # exact per-edge bank reservations (collq_gather_1018.schedule rule, plain mode) for the composed layer calendar:
    # (edge relative to the descriptor fire, bank, owner)
    rsv = sorted([(issue_rel(i // R) + 16, (src + i) % 8, "r3") for i in range(F)] +
                 [(wb_ - FE, s_ % 8, "w2") for s_, (_, _, wb_) in landed.items()])
    # read requests keep their edges; with VM_RT they reach the bank through the l12 request pads (hcollrs BANK_RT):
    # the window grant above covers them (it spans the whole gather)
    reservations = dict(reads=F, writes=len(landed), first=rsv[0][0], last=rsv[-1][0],
                        rule="read sample IE+16 (plain), publish write sample IE+34+2h; calendar word = fire_index + "
                             "edge + OWNER_LEAD 1 (collq_gather_1018 on origin/main)")
    return dict(status="emitted", F=F, R=R, stride=stride, src_sector=src, dst_sector=dst, t_start=t_start, vm_rt=vm_rt,
                transport=dict(launch_edges=Ls, ingress_edges=ing, kq_write_edges=kqw) if transport else None,
                n_words=n, launch_cyc=cL, L=L, fire=FE, last_write=last_w, check_cyc=T,
                model_span_fire_to_last_write=sp, launch_to_last_write=last_w - L,
                calendar=dict(target=CAL_TGT, loops=win, word={k: hex(v) for k, v in cal_word.items()},
                              configuration_writes=len(cal["configuration_writes"])),
                gq=dict(target=GQ_TGT, row0_payload=hex(payload)), collq_reservations=reservations,
                events=ev, chk_vm=chk_vm, chk_ring=chk_ring, chk_misc=chk_misc, words_checked=words_checked,
                far_end_flits=sum(len(m) for m in drv.values()))


def replays(g, nev):
    """one replay (all checks) or two (p0 drives + VM / fault checks, p1 drives + ring-output checks)."""
    cap = nev - 1
    base = g["events"]
    allc = g["chk_vm"] + g["chk_misc"] + g["chk_ring"]
    nm = lambda evs: sum(1 for e in evs if e["k"] != "M")
    if nm(base) + len(allc) <= cap:
        return [("", base + allc)]
    p0, p1 = base + g["chk_vm"] + g["chk_misc"], base + g["chk_ring"] + g["chk_misc"]
    if nm(p0) > cap or nm(p1) > cap:
        raise ValueError(f"record does not fit NEV {nev} even split: {nm(p0)} / {nm(p1)}")
    return [("_p0", p0), ("_p1", p1)]


PRE_PORTS = {"host_cp_ingress__cfg_v": 0, "host_cp_ingress__cfg_target": 1, "host_cp_ingress__cfg_addr": 2,
             "host_cp_ingress__cfg_data": 3, "host_cp_ingress__desc_v": 4, "host_cp_ingress__desc_base": 5,
             "host_cp_ingress__desc_limit": 6, "host_cp_ingress__desc_loops": 7, "host_cp_ingress__launch_v": 8,
             IN_PORTS[(0, 0)]: 10, IN_PORTS[(0, 1)]: 11, IN_PORTS[(1, 0)]: 12, IN_PORTS[(1, 1)]: 13,
             OUT_PORTS[(0, 0)]: 20, OUT_PORTS[(0, 1)]: 21, OUT_PORTS[(1, 0)]: 22, OUT_PORTS[(1, 1)]: 23,
             "hcollgi_SW__fault": 40, "hcollgl_SW__fault": 40, "hcollgi_SW__configured": 41, "hcollb_SW__fault": 42,
             "hcollks_SW__fault": 44, "hcollrs_SW__fault": 45, "hcollgi_SW__tgt_fault": 46}


def pre_events(evs):
    """replay events -> tb_coll_replay.sv event file (one-quadrant gather pre-check, no calendar / host leaf)."""
    out = []
    for e in sorted(evs, key=lambda e: (e["cyc"], e["k"])):
        if e["k"] == "M":
            out.append(f"0 3 0 {e['sector']:x} {e['val']}")
        elif e["port"].startswith("vm:"):
            out.append(f"{e['cyc']} 2 30 {e['port'][3:]} {e['val']}")
        elif e["port"] in PRE_PORTS:
            out.append(f"{e['cyc']} {1 if e['k'] == 'D' else 2} {PRE_PORTS[e['port']]} 0 {e['val']}")
    return "\n".join(out) + "\n"


def load_fixture_records(fdir, rank="0"):
    recs = json.loads((Path(fdir) / "records.json").read_text())
    z = np.load(Path(fdir) / "operands.npz")
    return recs, z, recs["records"][str(rank)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fixtures", type=Path, required=True)
    ap.add_argument("--boundary", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--records", help="comma list of priced record indices i (default: every priced ALL_GATHER)")
    ap.add_argument("--R", type=int, default=2, choices=(1, 2))
    ap.add_argument("--t-start", type=int, default=40)
    ap.add_argument("--nev", type=int, default=6309)
    ap.add_argument("--name-prefix", default=None)
    ap.add_argument("--rank", default="0")
    ap.add_argument("--pre-events", type=Path, help="also write <name>.events.txt for tb_coll_replay.sv here")
    ap.add_argument("--contract", type=Path, help="die functional contract: hcollgi_SW VM_RT (default 0 = GEN2)")
    ap.add_argument("--lane", default="VEH-FMT-COLL")
    ap.add_argument("--transport", type=Path, help="coll_transport.py profile of the die revision (default: GEN2 timing)")
    a = ap.parse_args()
    vm_rt = vm_rt_from_contract(a.contract) if a.contract else 0
    if a.transport:
        from hbm_layer_vehicle import coll_transport
        if a.pre_events:
            ap.error("--pre-events is the GEN2 tb_coll_replay timing (no relays); do not combine with --transport")
    tr = coll_transport.load(a.transport) if a.transport else None
    meta, z, recs = load_fixture_records(a.fixtures, a.rank)
    L = int(meta["layer"]) if str(meta["layer"]).isdigit() else meta["layer"]
    prefix = a.name_prefix or (f"ds_l{L}" if isinstance(L, int) else f"ds_{L}")
    bnd = json.loads(a.boundary.read_text())
    ins = {e["name"] for e in bnd["inputs"]}
    outs = {e["name"] for e in bnd["outputs"]}
    want = set(int(x) for x in a.records.split(",")) if a.records else None
    a.out.mkdir(parents=True, exist_ok=True)
    man = []
    for x in recs:
        if x["op"] != "COLL.ALL_GATHER":
            continue
        pr = x.get("priced") or []
        i_rec = int(pr[0]["i"]) if pr else None
        if want is not None and i_rec not in want:
            continue
        ent = dict(k_layer=x["k"], tag=x["tag"], i=i_rec, op=x["op"],
                   priced_cycles=round(pr[0]["end"] - pr[0]["start"], 2) if pr else None)
        if i_rec is None:
            ent.update(status="unpriced", reasons=["record not in the priced layer (no i): not replayed"])
            man.append(ent)
            continue
        O = np.asarray(z[x["outputs"]["O"]["array"]], np.uint32)
        g = gather_record(O, i_rec, R=a.R, t_start=a.t_start, vm_rt=vm_rt, transport=tr)
        if g["status"] != "emitted":
            ent.update(g)
            man.append(ent)
            continue
        safe = x["tag"].replace(" ", "_").replace("(", "").replace(")", "").replace("+", "").replace(".", "_")
        parts = []
        for suf, evs in replays(g, a.nev):
            name = f"{prefix}_coll_r{i_rec:03d}{suf}"
            for e in evs:
                if e["k"] == "D":
                    assert e["port"] in ins, e["port"]
                elif e["k"] == "C" and not e["port"].startswith("vm:"):
                    assert e["port"] in outs, e["port"]
            evs = sorted(evs, key=lambda e: (e["dom"], e["cyc"], e["k"]))
            rep = dict(schema="opentallas.hbm_slice_replay.v1", slice=bnd.get("slice_top", "sw"), design="ds", layer=str(L),
                       record=i_rec, tag=x["tag"], lane=a.lane, scope="component_probe", vm_rt=vm_rt,
                       transport=g.get("transport"),
                       assumptions=["quadrant q holds contiguous quarter q of the gathered vector O (plain FP32, no QBG)",
                                    "on-die quadrant phase only (cross-die hb_coll link programme: no compiler)",
                                    "calendar_SW = COLL-only window grant (sole VM owner in this replay)"],
                       events=evs)
            txt = json.dumps(rep) + "\n"
            (a.out / f"{name}.json").write_text(txt)
            if a.pre_events:
                a.pre_events.mkdir(parents=True, exist_ok=True)
                (a.pre_events / f"{name}.events.txt").write_text(pre_events(evs))
            parts.append(dict(name=name, events=sum(1 for e in evs if e["k"] != "M"),
                              vm_preload=sum(1 for e in evs if e["k"] == "M"), cycles=g["check_cyc"] + 64,
                              checks=sum(1 for e in evs if e["k"] == "C"),
                              replay_sha256=hashlib.sha256(txt.encode()).hexdigest()))
        ent.update({k: v for k, v in g.items() if k not in ("events", "chk_vm", "chk_ring", "chk_misc")})
        ent.update(replays=parts, slug=safe)
        man.append(ent)
    doc = dict(schema="opentallas.hbm_coll_images.v1", lane="VEH-FMT-COLL", fixtures=str(a.fixtures), layer=L,
               R=a.R, t_start=a.t_start, nev=a.nev, records=man,
               counts={s: sum(1 for m in man if m["status"] == s) for s in sorted({m["status"] for m in man})})
    (a.out / f"{prefix}_coll_manifest.json").write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(dict(layer=L, counts=doc["counts"],
                          replays=[p["name"] for m in man for p in m.get("replays", [])])))


if __name__ == "__main__":
    main()
