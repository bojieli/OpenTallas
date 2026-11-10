#!/usr/bin/env python3
"""DIE-S81-85 FACEHOLD-S81 11-10 (COORD ask): ft OUT-FACE lockup latch as a PER-ITEM kit-wave event, 0 pin cycles.

The face class.  ft_hop_lockup (FTLOCK-S81, t27/t49) latches the INTERNAL station hops j -> j+1 and does nothing for
the two face hops of a station type:
  in face   neighbour's last station -> in port ftX_i -> u_ft_ftX_o_0  (type STA: in_min -40 vs vclk, the receiver half
            of the seam contract clock.seam_hold "receiver -40 / sender 0")
  out face  u_ft_ftX_o_<k-1> -> out port ftX_o -> neighbour's first station  (type STA: out_min 0, the sender half)
Both are seam hops whose launch flop hangs on a kit tap port with an early source latency up to the tap window (no
CRPR across ports).  A lockup latch fixes a hold race only on the LAUNCH side (a receiver-side latch closes at the same
rising edge and keeps the race), so:
  out face  -> THIS tool: plan clock.ft_face_lockup.types += T; bind.py / gen_rtl put ot_dp_lk #(W+1) u_fl_<o>_<n-1>
               after the last station of every ft slot of T (the LATCH-FACE 11-03 out-face form: face_flops.tcl output
               walker, lec.py port phase class 'low', bind_verify 0 transport stages, clock_taps u_fl_ follow-D pass puts
               it on the last station's tap).  T's own out_min 0 check and the neighbour's real seam hold gain ~T/2.
  in face   -> no in-type form exists (the launch flop belongs to the neighbour type).  The in-type number is the
               -40 receiver contract, judged by the parent (io_hold_parent receipt; signoff port_only_hold ->
               LOCAL_PASS_NEEDS_PARENT, OWNER 11-03 NEEDS_PARENT counts).  If the PARENT check fails, the structural
               fix is this same event on the SENDER type (named in the receipt's census), not on the receiver.
0 pin cycles: the last station launches at rise 0, the latch passes at fall T/2, the neighbour captures at rise T.

The die plan of record is NOT edited.  The event plan is a copy whose ONLY difference is clock.ft_face_lockup (checked);
kit_wave reads it only for the named items through die option item_inputs {item: {plan, kit_rtl}} (KW-FIX-38), exactly
as FTLOCK-S81, so row identity (block_sha, retry keys, counting) stays on the die plan and no other row's spec changes.
The bind that makes the item kit RTL must run with a bind.py / gen_rtl.py that knows ft_face_lockup (this branch).

usage:
  ft_face_lockup_item_event.py plan PLAN OUTDIR --items T ...          -> OUTDIR/plan_ftfl_<sha12>.json + receipt.json
  ft_face_lockup_item_event.py kit-rtl-script OUT --bind-out B --asbuilt A
  ft_face_lockup_item_event.py fragment OUT --die D --items T ... --plan EVPLAN --kit-rtl-script S [--cfg kit_wave.json]
  ft_face_lockup_item_event.py dryrun --kit-wave DIR --cfg CFG --state STATE --die D --fragment FRAG [--hub H]
  ft_face_lockup_item_event.py blocks PLAN_A PLAN_B [--block-ignore sec.key ...]
Nothing here writes kit_wave.json, the wave state, a kit or a plan of record; fragment/dryrun only read them."""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ft_hop_lockup_item_event as FT  # noqa: E402

EVENT = "FACEHOLD-S81"
T_PS = 833.0
sha = FT.sha


def face_census(plan, tn):
    """out-face latches of type tn: one per ft slot with >= 1 station, W+1 bits (data + epoch)"""
    rows = []
    for s in plan["partition_types"][tn].get("ft_slots") or []:
        k = int(s.get("stations", 1))
        if k < 1:
            continue
        rows.append(dict(slot=s["name"], stations=k, out_port=f"{s['name']}_o", latch_inst=f"u_fl_{s['name']}_o_{k - 1}",
                         width=int(s["width"]), latch_bits=int(s["width"]) + 1))
    return dict(slots=len(rows), latches=len(rows), latch_bits=sum(x["latch_bits"] for x in rows), per_slot=rows)


def apply(plan, items):
    """the event plan: plan + clock.ft_face_lockup.types |= items; every other byte of meaning unchanged (asserted)"""
    items = sorted(set(items))
    if not items:
        raise ValueError("no items")
    miss = [t for t in items if t not in plan.get("partition_types", {})]
    if miss:
        raise ValueError(f"types not in plan: {miss}")
    flat = [t for t in items if not face_census(plan, t)["latches"]]
    if flat:
        raise ValueError(f"types without an ft station slot (no out face to latch): {flat}")
    out = copy.deepcopy(plan)
    fl = dict(out["clock"].get("ft_face_lockup") or {})
    fl["types"] = sorted(set(fl.get("types", [])) | set(items))
    out["clock"]["ft_face_lockup"] = fl
    a, b = dict(plan), dict(out)
    ca, cb = dict(a.pop("clock")), dict(b.pop("clock"))
    old, new = ca.pop("ft_face_lockup", None), cb.pop("ft_face_lockup", None)
    if sha(a) != sha(b) or sha(ca) != sha(cb):
        raise AssertionError("event changed more than clock.ft_face_lockup")
    if set((new or {}).get("types", [])) - set((old or {}).get("types", [])) - set(items):
        raise AssertionError("event added types that were not named")
    return out


def cmd_plan(a):
    raw_b = Path(a.plan).read_bytes()
    raw = json.loads(raw_b)
    new = apply(raw, a.items)
    if a.note:
        new["clock"]["ft_face_lockup"]["note"] = a.note
    data = (json.dumps(new, indent=1) + "\n").encode()
    h = hashlib.sha256(data).hexdigest()
    od = Path(a.outdir)
    od.mkdir(parents=True, exist_ok=True)
    out = od / f"plan_ftfl_{h[:12]}.json"
    out.write_bytes(data)
    import gen_rtl
    rec = dict(event=EVENT, tool="tools/die_plan/ft_face_lockup_item_event.py", form="out-face latch",
               plan_in=str(a.plan), plan_in_sha256=hashlib.sha256(raw_b).hexdigest(),
               plan_out=str(out), plan_out_sha256=h, items=sorted(set(a.items)),
               ft_face_lockup_before=raw["clock"].get("ft_face_lockup"), ft_face_lockup=new["clock"]["ft_face_lockup"],
               changed_keys=["clock.ft_face_lockup"],
               partition_types_unchanged=sha(raw["partition_types"]) == sha(new["partition_types"]),
               face_lockup_on=sorted(t for t in new["partition_types"] if gen_rtl.ft_face_lockup(new, t)),
               face_lockup_on_before=sorted(t for t in raw["partition_types"] if gen_rtl.ft_face_lockup(raw, t)),
               hop_lockup_on=sorted(t for t in new["partition_types"] if gen_rtl.ft_hop_lockup(new, t)),
               census={t: face_census(new, t) for t in sorted(set(a.items))}, pin_cycles_added=0,
               zero_cycle_argument="last station launches at rise 0; the transparent-low latch (ot_dp_lk) passes it at "
                                   "fall T/2; the neighbour's first station captures at rise T: one cycle per seam hop "
                                   "as before, pins and plan latency unchanged")
    Path(od / "receipt.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("plan_out", "plan_out_sha256", "items", "face_lockup_on")}))
    return 0


KIT_RTL_SCRIPT = """#!/bin/bash
# {event} (DIE-S81-85 11-10): kit RTL of the named items from the ft_face_lockup event plan (item_inputs plan) and its
# strict bind {bind_out} (u_fl_<o>_<n-1> out-face latches after the last station), asbuilt {asbuilt}.
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


def cmd_fragment(a):
    cfg = json.loads(Path(a.cfg).read_text()) if a.cfg else {"dies": {a.die: {}}}
    s = FT.fragment(cfg["dies"][a.die], a.items, "latch", a.plan, a.kit_rtl_script,
                    note=a.note or f"{EVENT} out-face latch (DIE-S81-85 11-10): ft out-face seam hold, 0 pin cycles")
    frag = dict(event=EVENT, form="out-face latch", die=a.die, items=sorted(set(a.items)), set=s,
                applied=False, note="proposal only: kit_wave.json is not touched by this tool",
                retry_fix_template={f"{t}@<attempt>": f"REDESIGN: {EVENT} out-face latch on ft slots (0 pin cycles)"
                                    for t in sorted(set(a.items))})
    Path(a.out).write_text(json.dumps(frag, indent=1) + "\n")
    print(a.out)
    return 0


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
    f.add_argument("--plan", required=True)
    f.add_argument("--kit-rtl-script", required=True)
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
    if a.cmd == "kit-rtl-script":
        return cmd_kit_rtl_script(a)
    if a.cmd in ("blocks", "dryrun"):
        return dict(blocks=FT.cmd_blocks, dryrun=FT.cmd_dryrun)[a.cmd](a)
    return dict(plan=cmd_plan, fragment=cmd_fragment)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
