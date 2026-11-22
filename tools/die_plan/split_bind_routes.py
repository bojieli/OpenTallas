"""Opt-in deterministic preservation of clean pre-split lane payloads.

The reference freezes symbolic leaf pins and old-lane bit order, never raw SCI
numbers.  New cut lanes stage those pins inside one old partition group before
its original outgoing lane is populated.  This reserves each original lane for
its measured payload instead of allowing greedy forwarding to duplicate a
multicast stream into another streams capacity.  Source/body and delay receipts
are the exporters responsibility; this helper independently checks cell shape,
parameters, identity, output pin bounds and old/new partition membership.
"""
from collections import ChainMap, defaultdict
import re
import hashlib
import json

SCHEMA = "opentallas.split_lane_reference.v1"


class SplitRouteError(ValueError):
    pass


def cell_fingerprint(cell):
    """Stable interface/parameter fingerprint; excludes staging paths and net IDs."""
    value = dict(module=cell.module, params=cell.params,
                 kind=getattr(cell,"kind",None), ytype=getattr(cell,"ytype",None),
                 yparams=getattr(cell,"yparams",None),
                 dirs=dict(sorted(cell.dirs.items())),
                 widths={k:len(v) for k,v in sorted(cell.ports.items())})
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()


def payload_sha256(lanes):
    """Hash the frozen lane/bit order, excluding later provenance annotations."""
    try:
        canonical=[{k:r[k] for k in ("id","src","dst","drivers")} for r in lanes]
        body=json.dumps(canonical,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    except (KeyError,TypeError,ValueError) as exc:
        raise SplitRouteError(f"malformed frozen lane payload: {exc}") from exc
    return hashlib.sha256(body.encode()).hexdigest()



def reserve_ingress_cuts(b, declared, lanes, old_ids, inverse, recv, put):
    """Keep the frozen inlet payload on an explicitly named, full-width intra-group cut.

    An ingress cut carries the bits from one original lane whose local inlet is
    named in the reference. Both endpoints of this new cut belong to the same
    old partition. Bit order is inherited from that original inlet.
    """
    if not isinstance(declared, dict):
        raise SplitRouteError("ingress_cuts must map cut lane IDs to ingress bus names")
    if not declared:
        return 0
    planned = []
    used = set()
    notes = {row["id"]: row.get("note", "") for row in b.plan.get("lanes", [])}
    for cut_id, inlet in declared.items():
        cut = lanes.get(cut_id)
        if (cut is None or cut_id in old_ids or cut["src"] not in inverse
                or inverse[cut["src"]] != inverse.get(cut["dst"])):
            raise SplitRouteError(f"ingress cut {cut_id} is not a new intra-group lane")
        source_label = re.search(r"\bcut leg of bus:(\S+) piece [0-9]+ -> [0-9]+", notes.get(cut_id, ""))
        if source_label is None or source_label[1] != inlet:
            raise SplitRouteError(f"ingress cut {cut_id} does not declare launch bus {inlet!r}")
        incoming = [lanes[old_id] for old_id in old_ids
                    if lanes[old_id]["dst"] == cut["src"] and lanes[old_id].get("iname") == inlet]
        if not isinstance(inlet, str) or not inlet or len(incoming) != 1:
            raise SplitRouteError(f"ingress cut {cut_id} needs one frozen inlet {inlet!r}")
        source = incoming[0]
        keys = list(source["carried"])
        if cut["left"] != cut["cap"] or len(keys) != cut["cap"]:
            raise SplitRouteError(f"ingress cut {cut_id} cannot reserve full payload of inlet {inlet}")
        for key in keys:
            cell, pin, bit = key
            source_part = b.cpart[cell]
            sink_key = (cut["dst"],) + key
            previous = recv.get((cut["src"],) + key)
            demand = b.cross.get((source_part, cut["dst"]), {}).get((cell, pin), ())
            if (previous is None or previous[0] is not source or bit not in demand
                    or sink_key in recv or sink_key in used):
                raise SplitRouteError(f"ingress cut {cut_id} is not the unique next hop for inlet {inlet}")
            used.add(sink_key)
        planned.append((cut, keys))
    for cut, keys in planned:
        for key in keys:
            put(cut, key, None)
    return len(used)


def prefill(b, reference, allL, put, recv, holders, out_of, heapq):
    """Prefill frozen original payloads, returning a small receipt.

    ``reference=None`` does nothing.  The v1 dictionary has part_groups mapping
    old partition names to current piece names, cells mapping symbolic paths to
    {fingerprint,part}, and lanes [{id,src,dst,drivers:[[path,port,bit],...]}].
    Original plan-cell lanes may have empty drivers; their planned payload stays
    under the existing plan-cell mechanism.  Every invalid reference fails before
    any callback; routing deadlock aborts the bind with exact unresolved lanes.
    """
    if reference is None:
        return dict(enabled=False,original_lanes=0,original_bits=0,cut_puts=0)
    if not isinstance(reference,dict) or reference.get("schema")!=SCHEMA:
        raise SplitRouteError("split lane reference schema mismatch")
    if reference.get("payload_sha256")!=payload_sha256(reference.get("lanes",[])):
        raise SplitRouteError("frozen lane payload_sha256 mismatch")
    groups={k:tuple(v) for k,v in reference.get("part_groups",{}).items()}
    if not groups or any(not v or len(set(v))!=len(v) for v in groups.values()):
        raise SplitRouteError("split lane reference empty/duplicate partition group")
    inverse={}
    known=set(getattr(b,"parts",{}) or [p["name"] for p in b.plan.get("partitions",[])])
    for old,pieces in groups.items():
        for p in pieces:
            if p in inverse:raise SplitRouteError(f"piece {p} belongs to two reference groups")
            if p not in known:raise SplitRouteError(f"reference piece {p} absent from current plan")
            inverse[p]=old
    lanes={}
    for L in allL:
        if L["id"] in lanes:raise SplitRouteError(f"duplicate current lane {L['id']}")
        lanes[L["id"]]=L
    records=reference.get("lanes")
    if not isinstance(records,list):raise SplitRouteError("reference lanes must be a list")
    seen=set(); rows=[]
    for r in records:
        lid=r.get("id")
        if lid in seen or lid not in lanes:raise SplitRouteError(f"duplicate/missing original lane {lid}")
        seen.add(lid)
        if r.get("src") not in groups or r.get("dst") not in groups:
            raise SplitRouteError(f"original lane {lid} names an unknown old partition")
        L=lanes[lid]
        if L["src"] not in groups[r["src"]] or L["dst"] not in groups[r["dst"]]:
            raise SplitRouteError(f"original lane {lid} endpoint left its old partition group")
        ds=r.get("drivers")
        if not isinstance(ds,list):raise SplitRouteError(f"lane {lid} drivers must be a list")
        if len(ds)>int(L["cap"]):raise SplitRouteError(f"original lane {lid} payload {len(ds)} exceeds cap {L['cap']}")
        rows.append((r,L))
    by_path={}
    for ci,c in enumerate(b.F.cells):
        if c.path in by_path:raise SplitRouteError(f"ambiguous current cell path {c.path}")
        by_path[c.path]=ci
    declared=reference.get("cells",{})
    checked={}
    def resolve(d):
        if not isinstance(d,(list,tuple)) or len(d)!=3:raise SplitRouteError(f"malformed symbolic driver {d!r}")
        path,pn,bit=d
        if path not in by_path or path not in declared:raise SplitRouteError(f"unresolved/undeclared source {path}")
        ci=by_path[path];c=b.F.cells[ci];meta=declared[path]
        if path not in checked:
            if meta.get("fingerprint")!=cell_fingerprint(c):raise SplitRouteError(f"source fingerprint changed {path}")
            old=meta.get("part")
            if old not in groups or b.cpart.get(ci) not in groups[old]:
                raise SplitRouteError(f"source {path} moved outside declared old partition {old}")
            checked[path]=True
        if not isinstance(bit,int) or isinstance(bit,bool) or pn not in c.ports or not 0<=bit<len(c.ports[pn]):
            raise SplitRouteError(f"source bit out of range {path}.{pn}[{bit}]")
        if c.dirs.get(pn) not in ("output","inout"):
            raise SplitRouteError(f"source is not an output {path}.{pn}")
        return ci,pn,bit
    planned=[]
    for r,L in rows:
        keys=[resolve(d) for d in r["drivers"]]
        if len(set(keys))!=len(keys):raise SplitRouteError(f"duplicate payload key on original lane {L['id']}")
        if L.get("plan") and keys:raise SplitRouteError(f"raw reference payload conflicts with plan-cell lane {L['id']}")
        carried=L.get("carried",{})
        prefix=[k for k,_v in sorted(carried.items(),key=lambda kv:kv[1])]
        if prefix!=keys[:len(prefix)]:raise SplitRouteError(f"original lane {L['id']} already has a different payload")
        if len(keys)-len(prefix)>int(L["left"]):raise SplitRouteError(f"original lane {L['id']} lacks payload capacity")
        planned.append((r,L,keys))
    # Only new lanes wholly inside the old sender group may stage a source.
    cut_by_group=defaultdict(list)
    for L in allL:
        group=inverse.get(L["src"])
        if L["id"] not in seen and group is not None and inverse.get(L["dst"])==group:
            cut_by_group[group].append(L)
    for ls in cut_by_group.values():ls.sort(key=lambda L:L["id"])
    _pl=(getattr(b,"plan",None) or {}).get("lanes",[])
    _lane_note={x["id"]:x.get("note","") for x in (_pl if isinstance(_pl,list) else []) if isinstance(x,dict) and "id" in x}
    pending=planned[:];done=0;nbits=0;cut_puts=0;passes=0
    while pending:
        passes+=1;later=[];reasons={};progress=False
        for r,L,keys in pending:
            if not keys:
                done+=1;progress=True;continue
            group=set(groups[r["src"]])
            available={key:((set(holders.get(key,())) & group) |
                            ({b.cpart[key[0]]} if b.cpart[key[0]] in group else set())) for key in keys}
            missing=[key for key,v in available.items() if not v]
            if missing:
                later.append((r,L,keys));reasons[L["id"]]=f"awaiting {len(missing)} source keys in sender group";continue
            # Dry-run staging first.  A blocked lane must not consume cut capacity
            # that a later reference lane can use to establish another holder.
            virtual={x["id"]:dict(x,carried=ChainMap({},x["carried"])) for x in cut_by_group[r["src"]]}
            vout=defaultdict(list)
            for x in virtual.values():vout[x["src"]].append(x)
            actions=[];blocked=None
            # OPUS-FIX-KV-PV-R7 11-22: a reference lane whose plan has its OWN station cut leg (lane note "cut leg of
            # bus:<oname> piece") stages its keys through that leg even when another leg already brought the same source
            # keys into the piece (kv3_pv_v12: o_vport_E_N_vo and o_vport_E_N_vo_d2 both forward i_vport_E_N_vo_d1; the
            # second leg o_vport_E_N_vo_d1_p_2 stayed empty -> native stations "expected one outgoing lane").
            _o=L.get("oname","")
            _own=[x for x in virtual.values() if _o and x["dst"]==L["src"] and x["src"] in group and
                  re.search(r"cut leg of bus:"+re.escape(_o)+r" piece ",_lane_note.get(x["id"],"") or "")]
            for key in keys:
                if _own and key not in _own[0]["carried"] and (available[key]-{L["src"]}):
                    path=b._route(available[key]-{L["src"]},L["src"],[key],vout,heapq,only=lambda x,i=_own[0]["id"]:x["id"]==i)
                    if path:
                        for x in path:
                            if key not in x["carried"]:
                                if x["left"]<=0:raise SplitRouteError("own cut leg exceeded capacity")
                                x["carried"][key]=-1;x["left"]-=1;actions.append((lanes[x["id"]],key))
                        continue
                if L["src"] in available[key]:continue
                # OPUS-FIX-KV-PV-R5 11-21: the cut leg named for this lane's own bus (<oname>_p, <oname>_p_N: the split's
                # station cut of that bus) is tried first; the lane-id tie-break alone put kv3_pv_v3 o_vport_W_N_vqN /
                # sN_j_fault / y_valid bits on a lower-id wide cut lane (o_vport_E_N_vo_p) and left their own legs empty
                # (native stations 'expected one outgoing lane').
                # FLOW-STRIPBODY-R2 11-21: type_split names the cut leg o_<stem>_p with stem = the bus without its o_/i_
                # prefix, so a bus with no prefix (S81 lepe_mu_C leafdn_o2 -> o_leafdn_o2_p) matches the o_-prefixed form too.
                own=lambda x,g=group,o=L.get("oname",""):(x["id"] not in seen and x["src"] in g and x["dst"] in g and
                                                          bool(o) and re.fullmatch("(?:"+re.escape(o)+"|o_"+re.escape(re.sub(r"^[oi]_","",o))+r")_p(_\d+)?",
                                                                                   x.get("oname","")) is not None)
                path=b._route(available[key],L["src"],[key],vout,heapq,only=own)
                if path is None:
                    path=b._route(available[key],L["src"],[key],vout,heapq,
                                  only=lambda x,g=group:x["id"] not in seen and x["src"] in g and x["dst"] in g)
                if path is None:
                    blocked=f"no cut-only path for {b.F.cells[key[0]].path}.{key[1]}[{key[2]}] to {L['src']}";break
                for x in path:
                    if x["src"] not in available[key]:raise SplitRouteError("cut path uses unavailable source")
                    if key not in x["carried"]:
                        if x["left"]<=0:raise SplitRouteError("cut path exceeded capacity")
                        x["carried"][key]=-1;x["left"]-=1;actions.append((lanes[x["id"]],key))
                    available[key].add(x["dst"])
            if blocked:
                later.append((r,L,keys));reasons[L["id"]]=blocked;continue
            for x,key in actions:
                if x["src"]!=b.cpart[key[0]] and (x["src"],)+key not in recv:
                    raise SplitRouteError(f"cut source missing recv at {x['src']}")
                put(x,key,None);cut_puts+=1
            for key in keys:
                if L["src"]!=b.cpart[key[0]] and (L["src"],)+key not in recv:
                    raise SplitRouteError(f"original lane {L['id']} source missing recv")
                put(L,key,None)
            actual=[k for k,_v in sorted(L["carried"].items(),key=lambda kv:kv[1])]
            if actual!=keys:raise SplitRouteError(f"original lane {L['id']} payload order changed")
            done+=1;nbits+=len(keys);progress=True
        if not progress:
            text="; ".join(f"{r['id']}: {reasons[r['id']]}" for r,_L,_k in later[:12])
            raise SplitRouteError(f"reference prefill stalled on {len(later)} lanes: {text}")
        pending=later
    ingress_puts = reserve_ingress_cuts(b, reference.get("ingress_cuts", {}),
                                        lanes, seen, inverse, recv, put)
    receipt = dict(enabled=True,original_lanes=done,original_bits=nbits,cut_puts=cut_puts,
                   source_cells=len(checked),passes=passes)
    if ingress_puts:
        receipt["ingress_cut_puts"] = ingress_puts
    return receipt
