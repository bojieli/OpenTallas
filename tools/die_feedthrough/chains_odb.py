#!/usr/bin/env python3
"""Bit-exact relay-chain extraction for the die-side pushdown (FT-TOOL, coordinator priority 1, 10-23).

Runs INSIDE OpenROAD Python (`openroad -python -exit chains_odb.py`; chains.sh wraps docker), environment:
    FT_ODB      die ODB (read-only)            FT_PLAN   plan.json from plan.py (lanes[] with src/dst/bus/segments)
    FT_OUT      output directory               FT_DROP_RE  regex of DROPPABLE relay masters (pushdown removes them)
    FT_RELAY_RE regex of all die relay / landing / head masters (non-droppable ones are KEPT elements)

For every pushed lane (keep_channel false, >= 1 block segment) every source bit is traced through buffers and relays
(data pin i/a/y/d[k] -> o/b/q*[k], same bit index) to the sink bus.  Along each bit path the elements between the cut
points A (last kept element / source before the dropped run) and B (first kept element / sink after it) are the
DROPPED run.  A relay is dropped only when ALL of its data-output bits are on pushed bit paths and its side outputs
only feed dropped relays or the recorded tail sinks (fixpoint); a relay shared with a non-pushed lane is kept and the
run is re-cut (taps are therefore handled exactly: a tap relay stays, the pushed bits start after it).

Output FT_OUT/chains.json, schema opentallas.die_feedthrough.chains.v1:
  lanes[]: {lane, status, subchains[]}; subchain = one physical relay chain (one forwarded clock):
     bits[]: {src_bit, a_pin "inst/pin[k]" (A's output, or the source pin), a_net, b_pin (B's input), b_old_net}
     dropped[]: relay instances in chain order; masters{}; width (data bits of one relay)
     chained[]: {out_pin, in_pin, kind fclk|side}: side-chain pin pairs between consecutive relays (ck_o->ck/ckf,
                eb->ea), with head_net (the net on the first dropped relay's in_pin) and tail_sinks ["inst/pin"]
     static{}: per dropped relay {pin: net} for every other input (local clock, reset, k*, en, s ...) + xy
  dropped_all[]: every relay the ECO deletes;  kept_shared[]: relays kept because a non-pushed lane uses them
"""
import json
import os
import re
import time
from collections import defaultdict

import odb  # noqa: E402

PAIRS = (("i", "o"), ("a", "b"), ("y", "b"), ("d", "q"), ("d", "q0"), ("d", "q1"))
BUF_RE = re.compile(r"^(BUF|INV|HB\d|CKBUF|CKINV)\w*_ASAP7")
BIT_RE = re.compile(r"^(.*?)\[(\d+)\]$")


def split_bit(name):
    m = BIT_RE.match(name)
    return (m.group(1), int(m.group(2))) if m else (name, None)


def main():
    t0 = time.time()
    plan = json.load(open(os.environ["FT_PLAN"]))
    out = os.environ["FT_OUT"]
    drop_re = re.compile(os.environ["FT_DROP_RE"])
    relay_re = re.compile(os.environ["FT_RELAY_RE"])
    db = odb.dbDatabase.create()
    odb.read_db(db, os.environ["FT_ODB"])
    blk = db.getChip().getBlock()
    dbu = float(db.getTech().getDbUnitsPerMicron())
    print(f"read {time.time()-t0:.0f}s", flush=True)

    mcache = {}

    def minfo(master):
        n = master.getName()
        r = mcache.get(n)
        if r is not None:
            return r
        ins, outs = {}, {}
        for mt in master.getMTerms():
            if mt.getSigType() in ("POWER", "GROUND"):
                continue
            b, _ = split_bit(mt.getName())
            (ins if mt.getIoType() == "INPUT" else outs)[b] = True
        data = {}
        for i, o in PAIRS:
            if i in ins and o in outs:
                data.setdefault(i, []).append(o)
        r = dict(buf=bool(BUF_RE.search(n)), relay=bool(relay_re.search(n)), drop=bool(drop_re.search(n)),
                 data=data, data_out={o for v in data.values() for o in v}, block=master.isBlock())
        mcache[n] = r
        return r

    def sinks(net, depth=0):
        """(inst, iterm) sinks of net through pass-through buffers, plus the buffers walked."""
        res, bufs, stack, seen = [], [], [net], set()
        while stack:
            n = stack.pop()
            if n is None or n.getId() in seen:
                continue
            seen.add(n.getId())
            for it in n.getITerms():
                mt = it.getMTerm()
                if mt.getIoType() != "INPUT":
                    continue
                inst = it.getInst()
                mi = minfo(inst.getMaster())
                if mi["buf"]:
                    bufs.append(inst)
                    for o in inst.getITerms():
                        if o.getMTerm().getIoType() == "OUTPUT":
                            stack.append(o.getNet())
                else:
                    res.append(it)
            for bt in n.getBTerms():
                if bt.getIoType() == "OUTPUT":
                    res.append(bt)
        return res, bufs

    def xy(inst):
        b = inst.getBBox()
        return [round((b.xMin() + b.xMax()) / 2 / dbu, 2), round((b.yMin() + b.yMax()) / 2 / dbu, 2)]

    def iname(it):
        return f"{it.getInst().getName()}/{it.getMTerm().getName()}"

    lanes = [l for l in plan["lanes"] if not l.get("keep_channel") and l.get("segments")]
    # ---- pass 1: trace every bit path --------------------------------------------------------------------------
    paths = {}            # lane id -> list of dict(src_bit, elems[(inst, in_pin, out_pin)], end iterm)
    accounted = set()     # (relay, out_pin_bit) on pushed bit paths
    status = {}
    for lane in lanes:
        src = blk.findInst(lane["src"]) if lane["src"] not in ("PORT",) else None
        dst = blk.findInst(lane["dst"])
        if src is None or dst is None:
            status[lane["id"]] = "unsupported endpoint (PORT/CELL)"
            continue
        dbus = lane["dst_bus"]
        res = []
        for it in src.getITerms():
            b, k = split_bit(it.getMTerm().getName())
            if b != lane["src_bus"] or it.getNet() is None:
                continue
            # DFS: (net, elems)
            stack = [(it.getNet(), ())]
            found = None
            guard = 0
            while stack and found is None and guard < 20000:
                guard += 1
                net, elems = stack.pop()
                sk, _ = sinks(net)
                for s in sk:
                    if isinstance(s, odb.dbBTerm):
                        continue
                    inst = s.getInst()
                    pb, pk = split_bit(s.getMTerm().getName())
                    if inst.getId() == dst.getId() and pb == dbus:
                        found = (elems, s)
                        break
                    mi = minfo(inst.getMaster())
                    if mi["relay"] and pb in mi["data"] and not any(e[0] == inst.getName() for e in elems):
                        for ob in mi["data"][pb]:
                            on = f"{ob}[{pk}]" if pk is not None else ob
                            oit = inst.findITerm(on)
                            if oit is not None and oit.getNet() is not None:
                                stack.append((oit.getNet(), elems + ((inst.getName(), s.getMTerm().getName(), on),)))
            if found:
                elems, end = found
                res.append(dict(src_bit=it.getMTerm().getName(), src_net=it.getNet().getName(), elems=list(elems),
                                end=iname(end), end_net=end.getNet().getName()))
                for e in elems:
                    accounted.add((e[0], e[2]))
        paths[lane["id"]] = res
        status[lane["id"]] = "ok" if res else ("no bit reaches the sink: census phantom pair (a shared multi-bus relay "
                                                      "mixes src/dst buses; no real connection)")
    print(f"traced {sum(len(v) for v in paths.values())} bit paths {time.time()-t0:.0f}s", flush=True)

    # ---- pass 2: droppable relays (fixpoint) --------------------------------------------------------------------
    cand = {e[0] for v in paths.values() for p in v for e in p["elems"]}
    cand = {r for r in cand if minfo(blk.findInst(r).getMaster())["drop"]}
    # station-local registers: a static input (rs ...) driven, through BUF/INV, by a flop -> the flop + the path cells
    # belong to the station (S81: rfw_* DFFHQN on the forwarded clock, QN -> INV -> rs).  They are dropped with the
    # station and re-created at every new stage (die_eco), so the relay's own reset register is not left behind.
    def local_reg(it):
        net, cells, ninv = it.getNet(), [], 0
        for _ in range(8):
            if net is None:
                return None
            drv = next((x for x in net.getITerms() if x.getMTerm().getIoType() == "OUTPUT"), None)
            if drv is None:
                return None
            d = drv.getInst()
            mn = d.getMaster().getName()
            if minfo(d.getMaster())["buf"]:
                cells.append(d.getName())
                ninv += mn.startswith("INV") or mn.startswith("CKINV")
                net = next((x.getNet() for x in d.getITerms() if x.getMTerm().getIoType() == "INPUT"), None)
                continue
            if re.match(r"^(DFF|DHL|SDF|ASYNC_DFF)", mn):
                ck = d.findITerm("CLK")
                dd = d.findITerm("D")
                return dict(flop=d.getName(), flop_master=mn, flop_out=drv.getMTerm().getName(),
                            d_net=dd.getNet().getName() if dd is not None and dd.getNet() is not None else None,
                            ck_net=ck.getNet().getName() if ck is not None and ck.getNet() is not None else None,
                            path=cells, n_inv=ninv)
            return None
        return None

    units = {}
    for r in cand:
        inst = blk.findInst(r)
        mi = minfo(inst.getMaster())
        u = {}
        for it in inst.getITerms():
            mt = it.getMTerm()
            if mt.getIoType() != "INPUT" or split_bit(mt.getName())[0] in mi["data"]:
                continue
            lr = local_reg(it)
            if lr is not None:
                u[mt.getName()] = lr
        if u:
            units[r] = u
    unit_flops = {lr["flop"] for u in units.values() for lr in u.values()}
    print(f"station-local registers {len(unit_flops)}", flush=True)
    kept_shared = set()
    why = {}
    changed = True
    while changed:
        changed = False
        for r in sorted(cand):
            inst = blk.findInst(r)
            mi = minfo(inst.getMaster())
            ok = True
            for it in inst.getITerms():
                mt = it.getMTerm()
                if mt.getIoType() != "OUTPUT" or it.getNet() is None:
                    continue
                b, _ = split_bit(mt.getName())
                sk, _ = sinks(it.getNet())
                if not sk:
                    continue
                if b in mi["data_out"]:
                    if (r, mt.getName()) not in accounted:
                        ok = False
                        why[r] = "data bit not on a pushed lane"
                        break
                    continue
                # side output: sinks must be droppable relays or kept elements' chained inputs (recorded as tails)
                for s in sk:
                    if isinstance(s, odb.dbBTerm):
                        ok = False
                        why[r] = f"side {mt.getName()} -> die port"
                        break
                    sm = minfo(s.getInst().getMaster())
                    if not sm["relay"] and s.getInst().getName() not in unit_flops:
                        ok = False
                        why[r] = f"side {mt.getName()} -> {s.getInst().getMaster().getName()}/{s.getMTerm().getName()}"
                        break
                if not ok:
                    break
            if not ok:
                cand.discard(r)
                kept_shared.add(r)
                changed = True

    # ---- pass 3: cut each bit path at the dropped run, group into sub-chains ------------------------------------
    out_lanes = []
    dropped_all = set()
    for lane in lanes:
        lid = lane["id"]
        subs = {}
        bad = 0
        for p in paths.get(lid, []):
            el = p["elems"]
            flags = [e[0] in cand for e in el]
            # the longest contiguous dropped run
            best, cur = (0, -1, -1), None
            for i, f in enumerate(flags + [False]):
                if f and cur is None:
                    cur = i
                elif not f and cur is not None:
                    if i - cur > best[0]:
                        best = (i - cur, cur, i - 1)
                    cur = None
            if best[0] == 0:
                bad += 1
                continue
            s, e = best[1], best[2]
            run = el[s:e + 1]
            if s == 0:
                a_pin, a_net = f"{lane['src']}/{p['src_bit']}", p["src_net"]
            else:
                prev = el[s - 1]
                oit = blk.findInst(prev[0]).findITerm(prev[2])
                a_pin, a_net = f"{prev[0]}/{prev[2]}", oit.getNet().getName()
            if e == len(el) - 1:
                b_pin, b_net = p["end"], p["end_net"]
            else:
                nxt = el[e + 1]
                iit = blk.findInst(nxt[0]).findITerm(nxt[1])
                b_pin, b_net = f"{nxt[0]}/{nxt[1]}", iit.getNet().getName()
            key = (run[0][0], run[-1][0])
            sc = subs.setdefault(key, dict(dropped=[x[0] for x in run], bits=[]))
            if len(run) > len(sc["dropped"]):
                sc["dropped"] = [x[0] for x in run]
            sc["bits"].append(dict(src_bit=p["src_bit"], a_pin=a_pin, a_net=a_net, b_pin=b_pin, b_old_net=b_net,
                                   in_pin=run[0][1], out_pin=run[-1][2]))
        recs = []
        for key, sc in subs.items():
            chain = [blk.findInst(r) for r in sc["dropped"]]
            dropped_all.update(sc["dropped"])
            masters = {r.getName(): r.getMaster().getName() for r in chain}
            # side-chain pairs from consecutive relays; else from the names
            chained = {}
            for r0, r1 in zip(chain, chain[1:]):
                m0 = minfo(r0.getMaster())
                for it in r0.getITerms():
                    mt = it.getMTerm()
                    b, _ = split_bit(mt.getName())
                    if mt.getIoType() != "OUTPUT" or b in m0["data_out"] or it.getNet() is None:
                        continue
                    sk, _ = sinks(it.getNet())
                    for s in sk:
                        if not isinstance(s, odb.dbBTerm) and s.getInst().getId() == r1.getId():
                            chained[mt.getName()] = s.getMTerm().getName()
                if chained:
                    break
            if not chained:      # one-relay run: the chained pins by name
                names = {split_bit(mt.getName())[0] for mt in chain[0].getMaster().getMTerms()}
                for o_, i_ in (("ck_o", "ckf"), ("ck_o", "ck"), ("eb", "ea")):
                    if o_ in names and i_ in names and o_ not in chained:
                        chained[o_] = i_
            first, last = chain[0], chain[-1]
            ch = []
            for o_pin, i_pin in sorted(chained.items()):
                hit = first.findITerm(i_pin)
                tit = last.findITerm(o_pin)
                tails = []
                if tit is not None and tit.getNet() is not None:
                    sk, _ = sinks(tit.getNet())
                    tails = [iname(s) for s in sk if not isinstance(s, odb.dbBTerm)
                             and s.getInst().getName() not in sc["dropped"]]
                ch.append(dict(out_pin=o_pin, in_pin=i_pin, kind="fclk" if re.match(r"^ck", i_pin) else "side",
                               head_net=hit.getNet().getName() if hit is not None and hit.getNet() is not None else None,
                               tail_sinks=tails))
            chained_in = set(chained.values())
            static = {}
            for r in chain:
                mi = minfo(r.getMaster())
                pins = {}
                for it in r.getITerms():
                    mt = it.getMTerm()
                    b, _ = split_bit(mt.getName())
                    if mt.getIoType() != "INPUT" or b in mi["data"] or mt.getName() in chained_in:
                        continue
                    if mt.getSigType() in ("POWER", "GROUND"):
                        continue
                    pins[mt.getName()] = it.getNet().getName() if it.getNet() is not None else None
                static[r.getName()] = dict(xy=xy(r), master=r.getMaster().getName(), pins=pins,
                                           local_regs=units.get(r.getName(), {}))
            width = max((sum(1 for it in chain[0].getITerms() if split_bit(it.getMTerm().getName())[0] == ib)
                         for ib in minfo(chain[0].getMaster())["data"]), default=0)
            # reset PIPELINE: a station-local register whose D is the previous dropped station's pin net (rfwq of
            # station k-1 -> rfw_k.D).  reset_chain[pin] = {head: D net of the first station, tails: kept sinks of the
            # last station's pin net (through buffers) outside the dropped run}.
            reset_chain = {}
            run_flops = {lr["flop"] for r in sc["dropped"] for lr in units.get(r, {}).values()}
            for pin in sorted({p for r in chain for p in static[r.getName()]["local_regs"]}):
                piped = any(static[r1.getName()]["local_regs"].get(pin, {}).get("d_net") ==
                            static[r0.getName()]["pins"].get(pin) for r0, r1 in zip(chain, chain[1:]))
                if not piped:
                    continue
                lr0 = static[chain[0].getName()]["local_regs"].get(pin, {})
                tails = []
                lit = last.findITerm(pin)
                if lit is not None and lit.getNet() is not None:
                    sk, _ = sinks(lit.getNet())
                    tails = [iname(x) for x in sk if not isinstance(x, odb.dbBTerm)
                             and x.getInst().getName() not in sc["dropped"]
                             and x.getInst().getName() not in run_flops]
                reset_chain[pin] = dict(head=lr0.get("d_net"), tails=tails)
            recs.append(dict(dropped=sc["dropped"], masters=masters, width=width, bits=sc["bits"], chained=ch,
                             static=static, reset_chain=reset_chain))
        out_lanes.append(dict(lane=lid, status=status.get(lid, "?") if recs else (status.get(lid) or "no droppable run"),
                              bits_traced=len(paths.get(lid, [])), bits_uncut=bad, subchains=recs))
    dropped_cells = sorted({c for r in dropped_all for lr in units.get(r, {}).values()
                            for c in [lr["flop"]] + lr["path"]})
    js = dict(schema="opentallas.die_feedthrough.chains.v1", dropped_cells=dropped_cells, odb=os.environ["FT_ODB"], drop_re=drop_re.pattern,
              lanes=out_lanes, dropped_all=sorted(dropped_all), kept_shared=sorted(kept_shared),
              kept_why={r: why.get(r, "?") for r in sorted(kept_shared)},
              seconds=round(time.time() - t0, 1))
    with open(os.path.join(out, "chains.json"), "w") as f:
        json.dump(js, f)
    print(f"done lanes {len(out_lanes)} dropped {len(dropped_all)} kept_shared {len(kept_shared)} "
          f"{time.time()-t0:.0f}s", flush=True)


main()
