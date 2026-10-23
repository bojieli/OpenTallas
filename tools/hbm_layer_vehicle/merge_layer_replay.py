#!/usr/bin/env python3
"""TOK-FUNC-HBM-PAY (10-21): merged per-layer SW-slice replay = the SU layer replay (layer_images, serial domain,
su_prog__*) + the stream-domain component payloads of the SAME layer on ONE absolute timeline:
  HC.HC_MIX (HC_MIX_POST gathered-mix form, hc_images.mix_post_record), COLL.GROUP_REDUCE_MCAST (on-die multicast phase,
  coll_images.gather_record) and COLL.ALL_GATHER (on-die quadrant phase, coll_images.gather_record), each regenerated on
  the die revision's own timing (contract hc_SW GATHER_PHASE / l12 LG read-request pads / hcollgi_SW VM_RT).

Placement: the components share host_cp_ingress (one F20 stream), calendar_SW (one programme store) and the gq / qhub
programme stores, so they run back to back in priced-record order (record index i = the layer's static order), each
GAP edges after the previous one's last event; their absolute cycles are therefore SEQUENTIAL-CP placements, not the
priced start cycles (the per-token CP install of the HC qhub / calendar rows alone is ~3,500 edges at the ingress rate:
resident programmes are the production form).  The SU replay is unchanged (its own absolute serial cycles).
VM: every component is relocated to sectors the SU replay never touches (preload or check) and that no other component
of the same part uses (M preloads are cycle-0 images).
Parts: a built TB holds NEV-1 timed events, so the merged layer is split into parts that all run the SAME timeline:
part 0 = SU drives + SU checks + the components that fit, later parts = SU drives (no SU checks) + further components;
a component that does not fit beside the SU drives runs alone in its part (flagged).  Component diagnostics only, never
complete-layer or native-chain proof (scope component_probe).

  python3 -m hbm_layer_vehicle.merge_layer_replay --su RJ/ds_l0.json --su-manifest EMIT/ds_l0/manifest.json
      --fixtures FIX/L00 --contract contract_func.json --l12 l12.json --boundary slice/boundary.json --nev 11633
      --out OUT --name ds_l0_merged
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from hbm_layer_vehicle import coll_images as CI  # noqa: E402
from hbm_layer_vehicle import coll_transport  # noqa: E402
from hbm_layer_vehicle import hc_images as HI  # noqa: E402

GAP = 256
NSEC = 1 << 13


def sectors(evs):
    s = set()
    for e in evs:
        if e["k"] == "M":
            s.add(int(e["sector"]) & (NSEC - 1))
        elif e["k"] == "C" and e["port"].startswith("vm:"):
            s.add(int(e["port"][3:], 16) & (NSEC - 1))
    return s


def components(meta, z, recs, tim, vm_rt, R=2, t_start=40, *, connected_boundary=None, checkpoint=None, transport=None):
    """[(i, op, kind, builder(base) -> generator dict, n_sectors)] for the layer's emitted component records."""
    out = []
    pri_hc = HI.priced_hc(meta, recs)
    for x in recs:
        op = x["op"]
        if op == "HC.HC_MIX_POST":
            base_tag = x["tag"][:-len(" post")] if x["tag"].endswith(" post") else x["tag"]
            i = pri_hc.get(base_tag)
            if i is None:
                continue
            A = z[x["inputs"]["A"]["array"]]
            O = z[x["outputs"]["O"]["array"]]
            if connected_boundary is not None:
                from hbm_layer_vehicle import hc_layer_lower_1021 as HL
                parameters, provenance = HL.checkpoint_parameters(checkpoint, int(meta['layer']), 'attn' if 'attn' in x['tag'] else 'ffn')
                def build(b, A=A, O=O, i=i, parameters=parameters, provenance=provenance):
                    real = HL.lower_mix_post(A, O, parameters, tim, a_sector=b, o_sector=b+8,
                                             component_allocation=True, record=i, boundary=connected_boundary)
                    return dict(real['qhub_timing'], events=[e for e in real['events'] if e['k'] != 'C'],
                                chk=[e for e in real['events'] if e['k'] == 'C'],
                                actual_root_provenance=provenance, root_schedule=real['root_schedule'],
                                execution_qualified=False)
            else:
                build=lambda b, A=A, O=O, i=i: HI.mix_post_record(A, O, i, a_idx=b, o_idx=b + 8, tim=tim)
            out.append(dict(i=i, op="HC.HC_MIX", kind="hc", tag=x["tag"], nsec=16, build=build))
        elif op in ("COLL.ALL_GATHER", "COLL.GROUP_REDUCE_MCAST"):
            pr = x.get("priced") or []
            if not pr:
                continue
            i = int(pr[0]["i"])
            O = np.asarray(z[x["outputs"]["O"]["array"]], np.uint32)
            probe = CI.gather_record(O, i, R=R, t_start=t_start, vm_rt=vm_rt, transport=transport)
            if probe["status"] != "emitted":
                continue
            out.append(dict(i=i, op=op, kind="grm" if op.endswith("MCAST") else "coll", tag=x["tag"],
                            nsec=4 * probe["stride"],
                            priced_cycles=round(pr[0]["end"] - pr[0]["start"], 2),
                            build=lambda b, O=O, i=i: CI.gather_record(O, i, R=R, t_start=t_start, dst_idx=b,
                                                                       vm_rt=vm_rt, transport=transport)))
    return sorted(out, key=lambda c: c["i"])


def comp_events(g, kind):
    if kind == "hc":
        return g["events"] + g["chk"]
    return g["events"] + g["chk_vm"] + g["chk_misc"] + g["chk_ring"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--connected-hc", action="store_true")
    ap.add_argument("--checkpoint", type=Path, help="SHA-pinned released HC input tensors")
    ap.add_argument("--shared-calendar", action="store_true", help="compile finite SU owner epoch then nonoverlapping CP client epochs; component-only, no connected-data claim")
    ap.add_argument("--su", type=Path, required=True, help="SU layer replay (layer_images replay.json)")
    ap.add_argument("--su-manifest", type=Path, required=True)
    ap.add_argument("--fixtures", type=Path, required=True)
    ap.add_argument("--contract", type=Path, required=True)
    ap.add_argument("--l12", type=Path, help="l12 report; otherwise derive exact pad depths from source contract")
    ap.add_argument("--boundary", type=Path, required=True)
    ap.add_argument("--nev", type=int, default=11633)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--sector-base", type=lambda s: int(s, 0), default=None,
                    help="first sector for components (default: above every SU sector, 64-aligned)")
    ap.add_argument("--coll-transport", type=Path, help="coll_transport.py profile: die lane timing for COLL gathers (TOKg)")
    a = ap.parse_args()
    su = json.loads(a.su.read_text())
    sman = json.loads(a.su_manifest.read_text())
    meta, z, recs = CI.load_fixture_records(a.fixtures)
    tim = HI.timing_from_contract(a.contract, a.l12)
    vm_rt = CI.vm_rt_from_contract(a.contract)
    transport = coll_transport.load(a.coll_transport) if a.coll_transport else None
    bnd = json.loads(a.boundary.read_text())
    ins = {e["name"] for e in bnd["inputs"]}
    outs = {e["name"] for e in bnd["outputs"]}
    cap = a.nev - 1
    if a.shared_calendar:
        from hbm_layer_vehicle.native_su_calendar import reserve_component
        su = reserve_component(su, bnd, finite=True)
    sev = su["events"]
    su_M = [e for e in sev if e["k"] == "M"]
    su_D = [e for e in sev if e["k"] == "D"]
    su_C = [e for e in sev if e["k"] == "C"]
    used_su = sectors(sev)
    base0 = a.sector_base if a.sector_base is not None else ((max(used_su) // 64) + 1) * 64
    comps = components(meta, z, recs, tim, vm_rt, connected_boundary=bnd if a.connected_hc else None, checkpoint=a.checkpoint, transport=transport)
    # ---- absolute timeline (sequential CP placement, priced order); sector-independent
    phase0 = su.get("su_owner_calendar", {}).get("end_reservation_stream", 0) + GAP if a.shared_calendar else 0
    t = phase0

    def free_base(nsec, taken=()):
        """lowest 64-aligned window of nsec sectors clear of every SU sector (fallback only: used when the default
        above-the-SU base leaves no room, e.g. a large SU_LOWER2 layer)"""
        busy = set(used_su) | set(taken)
        for b in range(0, NSEC - nsec + 1, 64):
            if not any(x in busy for x in range(b, b + nsec)):
                return b
        raise ValueError(f"no free {nsec}-sector VM window beside the SU replay")

    def build_ok(c, b):
        g = c["build"](b)
        if "events" not in g or (sectors(comp_events(g, c["kind"])) & used_su):
            return None
        return g
    for c in comps:
        g = build_ok(c, base0) if base0 + c["nsec"] <= NSEC else None
        if g is None:
            try:
                g = c["build"](free_base(c["nsec"]))
            except ValueError:
                g = c["build"](0)              # timing only: it will run in a standalone part (no SU events)
        evs = comp_events(g, c["kind"])
        nm = [e["cyc"] for e in evs if e["k"] != "M"]
        c["shift"] = t - 0
        c["span"] = (min(nm), max(nm))
        c["n_events"] = len(nm)
        t = t + max(nm) + GAP
    # ---- parts
    parts = []

    def new_part(with_su_checks):
        base = su_D + (su_C if with_su_checks else [])
        return dict(events=list(base), n=len(base), su_checks=with_su_checks, comps=[], cur=base0, standalone=False)
    cur = new_part(True)
    parts.append(cur)
    for c in comps:
        fits = lambda p: p["n"] + c["n_events"] <= cap and p["cur"] + c["nsec"] <= NSEC
        if not fits(cur):
            cur = new_part(False)
            parts.append(cur)
            if not fits(cur):
                cur.update(events=[], n=0, standalone=True)
                if cur["cur"] + c["nsec"] > NSEC:
                    cur["cur"] = 0                 # no SU events in a standalone part: the whole quadrant VM is free
        if cur["n"] + c["n_events"] > cap:
            raise ValueError(f"component r{c['i']} alone exceeds NEV {a.nev}: {c['n_events']}")
        b = cur["cur"]
        if cur["standalone"]:
            g = c["build"](b)
        else:
            g = build_ok(c, b) if b + c["nsec"] <= NSEC else None
            if g is None:
                b = free_base(c["nsec"], taken=cur.setdefault("taken", set()))
                g = c["build"](b)
        cur.setdefault("taken", set()).update(range(b, b + c["nsec"]))
        evs = comp_events(g, c["kind"])
        assert cur["standalone"] or not (sectors(evs) & used_su), ("component sector clash with SU", c["i"])
        for e in evs:
            e = dict(e)
            if e["k"] != "M":
                e["cyc"] += c["shift"]
            if e["k"] == "D":
                assert e["port"] in ins, e["port"]
            elif e["k"] == "C" and not e["port"].startswith("vm:"):
                assert e["port"] in outs, e["port"]
            cur["events"].append(e)
        cur["n"] += c["n_events"]
        cur["cur"] = b + ((c["nsec"] + 63) // 64) * 64
        cur["comps"].append(dict(i=c["i"], op=c["op"], tag=c["tag"], sector_base=b, shift=c["shift"],
                                 launch_to_check=g.get("check_cyc", 0) - (g.get("launch_cyc") or g["launch"][0]),
                                 check_cyc=g["check_cyc"] + c["shift"], events=c["n_events"],
                                 priced_cycles=c.get("priced_cycles"),
                                 measured_model=dict(launch_to_last_write=g.get("launch_to_last_write"),
                                                     gather_row0_at=g.get("gather_row0_at"))))
    a.out.mkdir(parents=True, exist_ok=True)
    pr_all = [r for r in sman["records"] if r.get("i") is not None]
    su_em = sorted(r["i"] for r in sman["records"] if r.get("status") == "emitted" and r.get("op", "SU.").startswith("SU."))
    sm_em = sorted(r["i"] for r in sman["records"] if r.get("status") == "emitted" and r.get("lowering") == "sm_slice_v1")
    comp_i = sorted({c["i"] for c in comps})
    man_parts = []
    for k, p in enumerate(parts):
        evs = sorted(p["events"] + su_M, key=lambda e: (e["dom"], e["cyc"], e["k"]))
        name = f"{a.name}_p{k}"
        rep = dict(schema="opentallas.hbm_slice_replay.v1", slice=bnd.get("slice_top", "sw"), design=su.get("design", "ds"),
                   layer=su.get("layer"), scope="component_probe", qualifies_native_layer=False,
                   qualifies_native_chain=False, lane="TOK-FUNC-HBM-PAY", t0_serial=su.get("t0_serial"),
                   priced_layer_cycles=su.get("priced_layer_cycles"), merged_part=k, su_checks=p["su_checks"],
                   standalone_component=p["standalone"], components=[c["i"] for c in p["comps"]],
                   shared_vm_calendar=dict(policy="finite SU owner0 epoch followed by disjoint HC/COLL CP epochs" if a.shared_calendar else "legacy overlapping diagnostics; no shared calendar proof", static=True, production_qualified=False, su_epoch=su.get("su_owner_calendar"), payload_first_stream=phase0, data_connection="independent relocated fixture probes; no produced-to-consumed connection"),
                   timing=dict(hc={kk: v for kk, v in tim.items() if kk != "hc_params"}, coll_vm_rt=vm_rt, coll_transport=None if transport is None else dict(launch_edges=transport["launch_edges"], ingress_edges=transport["ingress_edges"])),
                   assumptions=["SU part = layer_images replay as emitted (serial domain, absolute cycles)",
                                "components: sequential CP placement in priced order, GAP %d edges; VM sectors relocated "
                                "above the SU sectors" % GAP] + ([] if p["su_checks"] else
                                                                ["SU drives replayed, SU checks in part 0 only"]),
                   events=evs)
        txt = json.dumps(rep) + "\n"
        (a.out / f"{name}.json").write_text(txt)
        man_parts.append(dict(name=name, events=sum(1 for e in evs if e["k"] != "M"), su_checks=p["su_checks"],
                              standalone=p["standalone"], components=p["comps"],
                              replay_sha256=hashlib.sha256(txt.encode()).hexdigest()))
    doc = dict(schema="opentallas.hbm_merged_layer_replay.v1", lane="TOK-FUNC-HBM-PAY", layer=su.get("layer"),
               su_replay=str(a.su), fixtures=str(a.fixtures), contract=str(a.contract), nev=a.nev,
               priced_records=len(pr_all), su_emitted=su_em, component_emitted=comp_i,
               emitted_fraction=round((len(set(su_em) | set(comp_i) | set(sm_em))) / max(1, len(pr_all)), 4),
               **({"sm_emitted_separate_replay": sm_em} if sm_em else {}),
               timeline_stream_edges=t, real_hc_root=a.connected_hc, execution_qualified=False, shared_calendar_epochs=a.shared_calendar, qualifies_native_layer=False, qualifies_native_chain=False, scope="component_probe", parts=man_parts)
    (a.out / f"{a.name}_parts.json").write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(dict(layer=doc["layer"], priced=len(pr_all), su=len(su_em), comps=len(comp_i),
                          fraction=doc["emitted_fraction"], parts=[(m["name"], m["events"]) for m in man_parts])))


if __name__ == "__main__":
    main()
