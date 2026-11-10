#!/usr/bin/env python3
"""DIE-S81-85 FTLOCK-S81 11-10 (COORD ruling): ft station hop lockup latch as a PER-ITEM kit-wave event, 0 pin cycles.

Zero-logic ft station hops u_ft_<slot>_o_k -> u_ft_<slot>_o_<k+1> of a type whose two flops hang on different kit tap
ports fail FF hold by the tap window (S81 slice_station t27 ft6_o_1 -> _2 -15.26 ps, t49 ft9_o_3 -> _4 -20.86 ps after
late ECO i1).  OWNER rule (zero-logic seam hold): lockup latch and HB4 delay, both forms in parallel.

Latch form (the generator support already exists, nothing new is emitted by this tool):
  plan clock.ft_hop_lockup.types += T  ->  bind.py / gen_rtl emit, on every internal hop k -> k+1 of every ft slot of T,
      ot_dp_st u_ft_<o>_k -> ot_dp_lk #(W+1) u_fl_<o>_k (transparent while clk is LOW, data + epoch) -> ot_dp_st u_ft_<o>_<k+1>
  (no latch after the last station: the out face is unchanged).  clock_taps.tcl hangs each u_fl_ latch on its LAUNCH
  station's tap, face_flops.tcl puts it FIRM at the hop midpoint, lec.py maps latch_to_wire, bind_verify counts 0
  transport stages.  0 pin cycles: the station launches at the rising edge, the latch passes the value at the falling
  edge (T/2), the capture station takes it at the next rising edge -- the hop is still one cycle, the pins and the
  plan latency are byte-identical.  Hold of latch -> capture gains ~T/2; setup of that half hop gets T/2 - W.

The die plan of record is NOT edited.  The event plan is a copy whose ONLY difference is clock.ft_hop_lockup (checked);
kit_wave reads it only for the named items through die option item_inputs {item: {plan, kit_rtl}} (KW-FIX-38), so row
identity (block_sha, retry keys, counting) stays on the die plan and no other row's spec changes.

HB4 form (--form hb4, the parallel form): no plan change; die option type_args {item: [--hold-ff-margin PS]} makes the
item's own FF GRT hold repair (hold_pad_hb4.tcl, HB4xp67 only inside repair_timing -hold) pad its hops PS above the SDC.
That is the existing flow support; a kept HB4 chain in the bound RTL is NOT emitted (no generator support for it).

usage:
  ft_hop_lockup_item_event.py plan PLAN OUTDIR --items T ...          -> OUTDIR/plan_ftlk_<sha12>.json + receipt.json
  ft_hop_lockup_item_event.py kit-rtl-script OUT --bind-out B --asbuilt A
  ft_hop_lockup_item_event.py fragment OUT --die D --items T ... --form latch --plan EVPLAN --kit-rtl-script S
  ft_hop_lockup_item_event.py fragment OUT --die D --items T ... --form hb4 --hb4-margin-ps PS
  ft_hop_lockup_item_event.py blocks PLAN_A PLAN_B [--block-ignore sec.key ...]   (plan_block_identity, raw mode)
  ft_hop_lockup_item_event.py dryrun --kit-wave DIR --cfg CFG --state STATE --die D --fragment FRAG [--hub H]
Nothing here writes kit_wave.json, the wave state, a kit or a plan of record; fragment/dryrun only read them."""
import argparse
import copy
import hashlib
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hold_hop_lockup_event as H  # noqa: E402

EVENT = "FTLOCK-S81"
T_PS = 833.0


def sha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()


def hop_census(plan, tn):
    """internal ft station hops of type tn (the hops that get a latch): per slot k-1 hops of W+1 bits (data + epoch)"""
    rows = []
    for s in plan["partition_types"][tn].get("ft_slots") or []:
        k = int(s.get("stations", 1))
        if k < 2:
            continue
        r = s.get("regs_um") or []
        hop = max((abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(r, r[1:])), default=None)
        rows.append(dict(slot=s["name"], stations=k, hops=k - 1, width=int(s["width"]),
                         latch_bits=(k - 1) * (int(s["width"]) + 1),
                         max_hop_um=None if hop is None else round(hop, 3)))
    hops = [x["max_hop_um"] for x in rows if x["max_hop_um"] is not None]
    return dict(slots=len(rows), hops=sum(x["hops"] for x in rows), latch_bits=sum(x["latch_bits"] for x in rows),
                max_hop_um=max(hops) if hops else None,
                max_half_hop_um=round(max(hops) / 2, 3) if hops else None, per_slot=rows)


def apply(plan, items):
    """the event plan: plan + clock.ft_hop_lockup.types |= items; every other byte of meaning unchanged (asserted)"""
    items = sorted(set(items))
    if not items:
        raise ValueError("no items")
    miss = [t for t in items if t not in plan.get("partition_types", {})]
    if miss:
        raise ValueError(f"types not in plan: {miss}")
    flat = [t for t in items if not hop_census(plan, t)["hops"]]
    if flat:
        raise ValueError(f"types without an internal ft station hop (nothing to latch): {flat}")
    out = H.apply(plan, items, [])
    a, b = dict(plan), dict(out)
    ca, cb = dict(a.pop("clock")), dict(b.pop("clock"))
    lk_old, lk_new = ca.pop("ft_hop_lockup", None), cb.pop("ft_hop_lockup", None)
    if sha(a) != sha(b) or sha(ca) != sha(cb):
        raise AssertionError("event changed more than clock.ft_hop_lockup")
    if set((lk_new or {}).get("types", [])) - set((lk_old or {}).get("types", [])) - set(items):
        raise AssertionError("event added types that were not named")
    return out


def cmd_plan(a):
    raw_b = Path(a.plan).read_bytes()
    raw = json.loads(raw_b)
    new = apply(raw, a.items)
    if a.note:
        new["clock"]["ft_hop_lockup"]["note"] = a.note
    data = (json.dumps(new, indent=1) + "\n").encode()
    h = hashlib.sha256(data).hexdigest()
    od = Path(a.outdir)
    od.mkdir(parents=True, exist_ok=True)
    out = od / f"plan_ftlk_{h[:12]}.json"
    out.write_bytes(data)
    import gen_rtl
    rec = dict(event=EVENT, tool="tools/die_plan/ft_hop_lockup_item_event.py", form="latch",
               plan_in=str(a.plan), plan_in_sha256=hashlib.sha256(raw_b).hexdigest(),
               plan_out=str(out), plan_out_sha256=h, items=sorted(set(a.items)),
               ft_hop_lockup_before=raw["clock"].get("ft_hop_lockup"), ft_hop_lockup=new["clock"]["ft_hop_lockup"],
               changed_keys=["clock.ft_hop_lockup"], partition_types_unchanged=sha(raw["partition_types"]) == sha(new["partition_types"]),
               lockup_on=sorted(t for t in new["partition_types"] if gen_rtl.ft_hop_lockup(new, t)),
               lockup_on_before=sorted(t for t in raw["partition_types"] if gen_rtl.ft_hop_lockup(raw, t)),
               census={t: hop_census(new, t) for t in sorted(set(a.items))}, pin_cycles_added=0,
               zero_cycle_argument="station k launches at rise 0; the transparent-low latch (ot_dp_lk) passes it at fall T/2; "
                                   "station k+1 captures at rise T: one cycle per hop as before, pins and plan latency unchanged")
    Path(od / "receipt.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("plan_out", "plan_out_sha256", "items", "lockup_on")}))
    return 0


KIT_RTL_SCRIPT = """#!/bin/bash
# {event} (DIE-S81-85 11-10): kit RTL of the named items from the ft_hop_lockup event plan (item_inputs plan) and its
# strict bind {bind_out} (u_fl_<o>_k hop latches in the bound station chains), asbuilt {asbuilt}.
set -euo pipefail
export S81_ASBUILT={asbuilt}
export S81_BIND_OUT={bind_out}
exec bash physical/die_plan/s81/kit_wave/kit_rtl.sh
"""


def cmd_kit_rtl_script(a):
    Path(a.out).write_text(KIT_RTL_SCRIPT.format(event=EVENT, bind_out=a.bind_out, asbuilt=a.asbuilt))
    Path(a.out).chmod(0o755)
    print(a.out)
    return 0


def fragment(cfg_die, items, form, plan=None, script=None, margin=None, note=""):
    """-> {"set": {die option: {item: value}}} for the named items only; refuses to overwrite an existing entry"""
    items = sorted(set(items))
    if form == "latch":
        if not plan or not script:
            raise ValueError("latch form needs --plan and --kit-rtl-script")
        have = sorted(t for t in items if t in (cfg_die.get("item_inputs") or {}))
        if have:
            raise ValueError(f"item_inputs already set for {have}: compose by hand")
        return {"item_inputs": {t: {"plan": plan, "kit_rtl": {"script": script}, "note": note} for t in items}}
    if form == "hb4":
        if margin is None or margin <= 0:
            raise ValueError("hb4 form needs --hb4-margin-ps > 0")
        ta = cfg_die.get("type_args") or {}
        clash = sorted(t for t in items if "--hold-ff-margin" in (ta.get(t) or []))
        if clash:
            raise ValueError(f"type_args already set --hold-ff-margin for {clash}")
        return {"type_args": {t: list(ta.get(t) or []) + ["--hold-ff-margin", f"{margin:g}"] for t in items}}
    raise ValueError(f"unknown form {form}")


def apply_fragment(cfg, die, frag):
    out = copy.deepcopy(cfg)
    d = out["dies"][die]
    for opt, rows in frag["set"].items():
        d.setdefault(opt, {}).update(copy.deepcopy(rows))
    return out


def cmd_fragment(a):
    cfg = json.loads(Path(a.cfg).read_text()) if a.cfg else {"dies": {a.die: {}}}
    s = fragment(cfg["dies"][a.die], a.items, a.form, a.plan, a.kit_rtl_script, a.hb4_margin_ps,
                 note=a.note or f"{EVENT} {a.form} (DIE-S81-85 11-10): ft station hop hold, 0 pin cycles")
    frag = dict(event=EVENT, form=a.form, die=a.die, items=sorted(set(a.items)), set=s,
                applied=False, note="proposal only: kit_wave.json is not touched by this tool",
                retry_fix_template={f"{t}@<attempt>": f"REDESIGN: {EVENT} {a.form} form on internal ft station hops "
                                    f"(0 pin cycles)" for t in sorted(set(a.items))})
    Path(a.out).write_text(json.dumps(frag, indent=1) + "\n")
    print(a.out)
    return 0


def block_shas(plan, path, ignore=()):
    """kit_wave PROBE_PLAN raw block identity (block_ignore applied the same way)"""
    sys.path.insert(0, str(HERE.parent / "autopilot"))
    import plan_block_identity as BI
    p = copy.deepcopy(plan)
    for dotted in ignore:
        sec, key = dotted.split(".", 1)
        for v in (p.get("partition_types") or {}).values():
            if isinstance(v, dict) and isinstance(v.get(sec), dict):
                v[sec].pop(key, None)
                if not v[sec]:
                    del v[sec]
    return {n: v["block_sha"] for n, v in BI.identities(p, path, BI.RAW).items()}


def cmd_blocks(a):
    A = block_shas(json.loads(Path(a.a).read_text()), a.a, a.block_ignore)
    B = block_shas(json.loads(Path(a.b).read_text()), a.b, a.block_ignore)
    diff = sorted(n for n in set(A) | set(B) if A.get(n) != B.get(n))
    rep = dict(plan_a=a.a, plan_b=a.b, names=len(set(A) | set(B)), changed=diff, block_ignore=a.block_ignore)
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(rep, changed=diff[:20], n_changed=len(diff))))
    return 0


def row_keys(K, cfg, st, die, hub):
    """{name: (item_key, input_hash)} with kit_wave's own functions; blocks from the wave's cached plan probe"""
    d = cfg["dies"][die]
    probe = (st.get("plans") or {}).get(f"{d['gen_host']}:{d['plan']}|{d['event']}")
    if not probe or not probe.get("blocks"):
        raise ValueError("no cached plan probe for the die plan of record in the wave state")
    names = K.core_view_names(probe["blocks"], probe.get("core_views"))
    types = set(probe.get("types") or [])
    pk = probe.get("prov_keys") or {}
    c = dict(cfg, _otrun_status={})
    out = {}
    for n, b in sorted(names.items()):
        kind = "type" if n in types else "core"
        sp = K.spec_for(c, die, n, hub, kind=kind)
        out[n] = (K.item_key(die, d["event"], n, b), K.input_hash(sp, pk.get(n)), sp.get("plan"), json.dumps(sp.get("kit_rtl"), sort_keys=True),
                  json.dumps(sp.get("gen_args")))
    return out, probe


def dryrun(K, cfg, st, die, frag, hub):
    before, probe = row_keys(K, cfg, st, die, hub)
    after, _ = row_keys(K, apply_fragment(cfg, die, frag), st, die, hub)
    named = set(frag["items"])
    rows = []
    for n in sorted(set(before) | set(after)):
        b, x = before.get(n), after.get(n)
        rows.append(dict(item=n, named=n in named, key_before=b and b[0], key_after=x and x[0],
                         key_changed=(b and b[0]) != (x and x[0]),
                         input_hash_changed=(b and b[1]) != (x and x[1]),
                         plan_changed=(b and b[2]) != (x and x[2]), kit_rtl_changed=(b and b[3]) != (x and x[3]),
                         gen_args_changed=(b and b[4]) != (x and x[4])))
    ch = [r for r in rows if r["key_changed"] or r["input_hash_changed"] or r["plan_changed"] or r["kit_rtl_changed"] or r["gen_args_changed"]]
    blockers = [r["item"] for r in ch if not r["named"]]
    missing = sorted(named - set(before))
    return dict(die=die, event=cfg["dies"][die]["event"], plan=cfg["dies"][die]["plan"], plan_sha=probe.get("plan_sha"),
                rows=len(rows), changed=[r["item"] for r in ch], key_changed=[r["item"] for r in rows if r["key_changed"]],
                input_hash_changed=[r["item"] for r in rows if r["input_hash_changed"]],
                named_unchanged=sorted(t for t in named if t in before and t not in {r["item"] for r in ch}),
                named_missing=missing, blockers=blockers, ok=not blockers and not missing, detail=ch)


def cmd_dryrun(a):
    sys.path.insert(0, str(Path(a.kit_wave).resolve()))
    K = importlib.import_module("kit_wave")
    cfg = json.loads(Path(a.cfg).read_text())
    st = json.loads(Path(a.state).read_text())
    frag = json.loads(Path(a.fragment).read_text())
    rep = dryrun(K, cfg, st, a.die, frag, a.hub)
    rep.update(kit_wave_py=str(Path(K.__file__).resolve()),
               kit_wave_py_sha256=hashlib.sha256(Path(K.__file__).read_bytes()).hexdigest(),
               cfg=a.cfg, cfg_sha256=hashlib.sha256(Path(a.cfg).read_bytes()).hexdigest(),
               state=a.state, fragment=a.fragment, fragment_sha256=hashlib.sha256(Path(a.fragment).read_bytes()).hexdigest())
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("rows", "changed", "key_changed", "input_hash_changed", "blockers", "named_missing", "ok")}))
    return 0 if rep["ok"] else 2


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("plan")
    p.add_argument("outdir")
    p.add_argument("--items", nargs="+", required=True)
    p.add_argument("--note", default="")
    k = sub.add_parser("kit-rtl-script")
    k.add_argument("out")
    k.add_argument("--bind-out", required=True)
    k.add_argument("--asbuilt", required=True)
    f = sub.add_parser("fragment")
    f.add_argument("out")
    f.add_argument("--die", required=True)
    f.add_argument("--items", nargs="+", required=True)
    f.add_argument("--form", choices=("latch", "hb4"), default="latch")
    f.add_argument("--plan")
    f.add_argument("--kit-rtl-script")
    f.add_argument("--hb4-margin-ps", type=float)
    f.add_argument("--cfg", help="kit_wave.json (read only): refuse to overwrite an existing per-item entry")
    f.add_argument("--note", default="")
    b = sub.add_parser("blocks")
    b.add_argument("a")
    b.add_argument("b")
    b.add_argument("--block-ignore", nargs="*", default=[])
    b.add_argument("--out")
    d = sub.add_parser("dryrun")
    d.add_argument("--kit-wave", required=True, help="directory holding kit_wave.py")
    d.add_argument("--cfg", required=True)
    d.add_argument("--state", required=True)
    d.add_argument("--die", required=True)
    d.add_argument("--fragment", required=True)
    d.add_argument("--hub", default="intel2")
    d.add_argument("--out")
    a = ap.parse_args(argv)
    return dict(plan=cmd_plan, fragment=cmd_fragment, dryrun=cmd_dryrun, blocks=cmd_blocks)[a.cmd](a) \
        if a.cmd != "kit-rtl-script" else cmd_kit_rtl_script(a)


if __name__ == "__main__":
    sys.exit(main())
