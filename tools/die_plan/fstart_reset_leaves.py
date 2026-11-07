#!/usr/bin/env python3
"""FSTART per-face reset leaves (DIE-HEAD-76-SPNRST 11-06): a reset tree instead of one far reset relay.

Class (HEAD hd_spn vA/vB GRT TT -111.77 / -151.98, hd_spn_end wave a5 -181/-241): the count-aligned landing emitter gives
every FSTART face flop u_cland_fstart_<bus> the same raw reset, cland_start_raw = cland_reset_<first landed input>, one
ot_dp_rrelay (u_cland_rst_<bus>) whose Q fans out to all writer faces.  On hd_spn the 8 faces sit on the N and S edges of a
587 x 2074 um strip, so that one flop is >= 1 mm from some face and placement buffers eat the cycle.

Form: one leaf per FSTART face flop through the EXISTING plan option clock.landing_local_resets (DIE-HEAD-38 R1,
clock_landings.Landings._local_resets): a kept ot_dp_rrelay u_cland_lrst_<name> whose D is a registered reset-wavefront
relay of the SAME depth as the shared relay's D, nearest to that face, placed half way between that relay and the face
flop (landing_place.py 'local-reset' FIRM site).  Depth(raw)+1 == depth(old reset) is checked by the generator itself, so
every release edge is unchanged: 0 added cycles, +1 flop per face.  rst_n is held >= 64 clk at boot; every reset-tree
relay is a plain delay of arst_n (no gate in the chain), so all same-depth relays are equal from cycle depth+1 on.

    python3 -I fstart_reset_leaves.py plan   RTL PLACEMENT_TCL OUTLINE_W OUTLINE_H [--prefix fstart_face] > entries.json
    python3 -I fstart_reset_leaves.py apply  RTL PLACEMENT_TCL entries.json OUT_RTL OUT_PLACEMENT_TCL [--type hd_spn]

'plan' prints the landing_local_resets entries to add to the type's plan (plan delta).  'apply' re-emits an already
generated kit wrapper with exactly the generator's own transform (Landings._local_resets on the emitted text) and adds
the matching local-reset FIRM rows, for a kit built before the plan delta lands.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

FSTART = re.compile(r"\bot_dp_landing_relay\s+(u_cland_fstart_\w+)\s*\(([^;]*?)\);", re.S)
RRL = re.compile(r"\bot_dp_(?:rrelay|head_raw_export_pair)\s+(\w+)\s*\(\s*\.clk\(clk\),\s*\.d\((\w+)\),\s*\.q\((\w+)\)"
                 r"[^;]*\);[ \t]*//[^\n]*?\bdepth (\d+) @ \(([-\d.]+),\s*([-\d.]+)\)")
EXPORT_PAIR = re.compile(r"\bot_dp_head_raw_export_pair(\s+\w+\s*\([^;\n]*?\.q\(\s*\w+\s*\)),\s*\.export_q\(\s*\w+\s*\)\s*\);")


class LeafError(ValueError):
    pass


def normalized(text):
    """Read-only copy for depth lookups: a raw export pair is the same clk/D/Q relay plus an export flop."""
    return EXPORT_PAIR.sub(r"ot_dp_rrelay\1);", text)


def resolve(text, net, seen=()):
    """Follow plain 'assign a = b;' aliases to the net a relay drives."""
    while True:
        a = re.search(r"\bassign\s+" + re.escape(net) + r"\s*=\s*(\w+)\s*;", text)
        if not a:
            return net
        if net in seen:
            raise LeafError(f"alias loop at {net}")
        seen += (net,)
        net = a.group(1)


def placement_rects(tcl):
    return {m.group(1): tuple(float(v) for v in m.group(2).split())
            for m in re.finditer(r"^\s*\{(\w+) \{([-\d.\s]+)\} [^}]*\}\s*$", tcl, re.M)}


def plan_entries(rtl, tcl, outline_um, prefix="fstart_face"):
    """landing_local_resets entries: one leaf per FSTART face flop whose reset is shared by >1 face."""
    rects = placement_rects(tcl)
    relays = {m.group(3): dict(inst=m.group(1), d=m.group(2), depth=int(m.group(4)),
                              xy=(float(m.group(5)), float(m.group(6)))) for m in RRL.finditer(rtl)}
    groups = {}
    for m in FSTART.finditer(rtl):
        pins = re.findall(r"\.rst_raw_n\(\s*(\w+)\s*\)", m.group(2))
        if len(pins) != 1:
            raise LeafError(f"{m.group(1)}: {len(pins)} rst_raw_n pins")
        groups.setdefault(resolve(rtl, pins[0]), []).append(m.group(1))
    out = []
    for shared, cons in groups.items():
        if len(cons) < 2:
            continue
        drv = re.search(r"\bot_dp_rrelay\s+(\w+)\s*\(\s*\.clk\(clk\),\s*\.d\((\w+)\),\s*\.q\(" + re.escape(shared) +
                        r"\)\);", rtl)
        if drv is None or drv.group(2) not in relays:
            raise LeafError(f"shared FSTART reset {shared}: not a plain relay of a depth-annotated wavefront relay")
        depth = relays[drv.group(2)]["depth"]
        same = {q: r for q, r in relays.items() if r["depth"] == depth and q.startswith("rst_rl_")}
        for c in cons:
            if c not in rects:
                raise LeafError(f"{c}: no FIRM landing site in the placement")
            x0, y0, x1, y1 = rects[c]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            raw = min(sorted(same), key=lambda q: abs(same[q]["xy"][0] - cx) + abs(same[q]["xy"][1] - cy))
            rx, ry = same[raw]["xy"]
            x = min(max((rx + cx) / 2, 2.16), outline_um[0] - 2.16)
            y = min(max((ry + cy) / 2, 2.16), outline_um[1] - 2.16)
            out.append(dict(name=f"{prefix}_{c[len('u_cland_fstart_'):]}", raw=raw, xy_um=[round(x, 3), round(y, 3)],
                            consumers=[c]))
            print(f"{c}: leaf u_cland_lrst_{out[-1]['name']} D={raw} (depth {depth} @ {rx},{ry}; was {shared} from "
                  f"{drv.group(2)}); hops {abs(rx - x) + abs(ry - y):.1f} + {abs(x - cx) + abs(y - cy):.1f} um",
                  file=sys.stderr)
    return out


class _Stub:
    pass


def apply_kit(rtl, tcl, entries, type_key="hd_spn"):
    """Re-emit the wrapper with the generator's own landing_local_resets transform; returns (rtl, tcl, records)."""
    import clock_landings as CL
    stub = CL.Landings.__new__(CL.Landings)
    stub.types = {type_key: {"clock": {"landing_local_resets": entries}}}
    stub.reset_placements = {}
    firsts = [m.start() for c in (e for x in entries for e in x["consumers"])
              for m in [re.search(r"\b\w+\s+" + re.escape(c) + r"\s*\(", rtl)] if m]
    if len(firsts) != sum(len(x["consumers"]) for x in entries):
        raise LeafError("consumer instance not found in the wrapper")
    first = min(firsts)
    last_decl = [m.end() for m in re.finditer(r"^[^\n]*\bu_cland_lrst_\w+[^\n]*\n", rtl, re.M) if m.end() <= first]
    cut = max(last_decl) if last_decl else rtl.rfind("\n", 0, first) + 1
    out = stub._local_resets(type_key, type_key, normalized(rtl), [rtl[cut:]])
    new_rtl = rtl[:cut] + "".join(line + "\n" for line in out[:-1]) + out[-1]
    rows = "".join(f"  {{u_cland_lrst_{e['name']} {{{e['xy_um'][0]-2.16:.5f} {e['xy_um'][1]-2.16:.5f} "
                   f"{e['xy_um'][0]+2.16:.5f} {e['xy_um'][1]+2.16:.5f}}} local-reset}}\n" for e in entries)
    lr = [m.end() for m in re.finditer(r"^  \{u_cland_lrst_\w+ \{[^}]*\} local-reset\}\n", tcl, re.M)]
    if not lr:
        m = re.search(r"^set cland_groups \{\n", tcl, re.M)
        if not m:
            raise LeafError("landing placement has no cland_groups list")
        lr = [m.end()]
    new_tcl = tcl[:max(lr)] + rows + tcl[max(lr):]
    return new_rtl, new_tcl, stub.reset_placements[type_key]["local_resets"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("rtl"); p.add_argument("tcl"); p.add_argument("w", type=float); p.add_argument("h", type=float)
    p.add_argument("--prefix", default="fstart_face")
    a = sub.add_parser("apply")
    a.add_argument("rtl"); a.add_argument("tcl"); a.add_argument("entries")
    a.add_argument("out_rtl"); a.add_argument("out_tcl"); a.add_argument("--type", default="hd_spn")
    args = ap.parse_args(argv)
    rtl = Path(args.rtl).read_text(); tcl = Path(args.tcl).read_text()
    if args.cmd == "plan":
        json.dump(plan_entries(rtl, tcl, (args.w, args.h), args.prefix), sys.stdout, indent=1)
        print()
        return 0
    entries = json.loads(Path(args.entries).read_text())
    new_rtl, new_tcl, rec = apply_kit(rtl, tcl, entries, args.type)
    Path(args.out_rtl).write_text(new_rtl); Path(args.out_tcl).write_text(new_tcl)
    json.dump(rec, sys.stdout, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
