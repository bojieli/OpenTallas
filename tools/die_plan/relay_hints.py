#!/usr/bin/env python3
"""relay_hints.py: structural reset / run relay classes -> LEC correspondence hints (LEC-RELAYHINT-1, COORD 11-25).

Reset and start relays (ot_dp_rrelay / ot_dp_rgate / ot_dp_head_raw_export_pair and their _drive forms) are pure
shift registers of the pin-registered reset and start inputs.  Synthesis merges functionally identical relays and
keeps a different survivor on each side (s81_head hd_mesh: gold kept u_rrl_172, the gate u_rrl_68 for the u_lb reset
root), so name matching alone leaves the survivor of one side unpaired.  The earlier hint generator paired relays by
name proximity and produced wrong-phase pairs (hd_mesh: 85 of 360 relay hints, e.g. depth-4 u_srl_55 with depth-1
u_srl_0); the induction refuted them and dropped the alias the u_lb reset root needed, failing 9,556 SRAM pin points.

A relay's class is (kind, class(d), class(run)) recursively, rooted at the nets no relay drives.  Two relays of one
class compute the same value on every cycle from any reset/start input sequence once their shift depth has filled
(same depth, same gating), so 'both' eq hints to the class representative are correct; lec.py still proves each one
by induction (a hint is never a waiver).

    python3 -I relay_hints.py TOP.sv [--top MODULE] [--hints IN.json] [--out OUT.json]   (census / rewrite)"""
import argparse
import json
import re
import sys

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("lec_for_relay_hints", Path(__file__).resolve().with_name("lec.py"))
_lec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lec)
_R = _lec._RelayHints
module_text, relays, classes, hints, relay_key, audit, rewrite = (_R.module_text, _R.relays, _R.classes, _R.hints,
                                                                 _R.relay_key, _R.audit, _R.rewrite)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rtl", nargs="+")
    ap.add_argument("--top")
    ap.add_argument("--hints")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    text = "\n".join(module_text(open(f, errors="replace").read(), a.top) for f in a.rtl)
    rows = relays(text)
    supplied = json.load(open(a.hints)) if a.hints else []
    if isinstance(supplied, dict):
        supplied = supplied.get("post") or supplied.get("hints") or []
    out, info = rewrite(supplied, rows)
    if a.out:
        with open(a.out + ".part", "w") as f:
            json.dump(out, f)
        import os
        os.replace(a.out + ".part", a.out)
    print(json.dumps(info))
    return 0


if __name__ == "__main__":
    sys.exit(main())
