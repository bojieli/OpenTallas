#!/usr/bin/env python3
"""prd_seed.py -- does the ECO seed DB carry the netlist of the routed SPEF the ECO reads? (FLOW-24 11-03, class fix)

prd_mk.sh seeds the post-route ECO with the kit's 5_1_grt.odb / 5_2_route.odb and reads the kit's routed 6_final.spef.
A kit whose 6_final.{odb,spef,v,def} were rewritten by a later post-route ECO (S81-CORES-KITS-12 peco: hxeco_* hold
cells + slweco_* slew buffers, 1327 cells on S81 dsdv_gunit_l4_ccA_s1_C1h) keeps the PRE-ECO 5_1/5_2 DBs, so the ECO
session ran on a netlist the SPEF does not describe: 1001 "STA-1650 ... net hxeco_* not found", the signed-off hold
cells are absent, and the session died 31 min in (RSZ-0074, DIE-S81-50 l4).  The sign-off of such a kit is on 6_final.odb.

Check (no OpenROAD needed): odb stores every object name as a NUL-terminated byte string, so the set of printable
NUL-delimited runs of a .odb contains all its net / instance names.  A SPEF *NAME_MAP name that the kit's 6_final.odb
has but the seed lacks proves the seed predates 6_final (escaping cannot cause a false hit: both DBs are compared alike).

    prd_seed.py SEED_ODB FINAL_ODB SPEF   -> one JSON line; rc 0 consistent, 3 stale (seed from FINAL_ODB), 2 error
"""
import json
import re
import sys

RUN = re.compile(rb"(?<=\x00)[!-~]+(?=\x00)")


def odb_names(path):
    with open(path, "rb") as f:
        data = f.read()
    return set(RUN.findall(data))


CONN = re.compile(rb"^\*(?:D_NET|I|P) \*(\d+)", re.M)


def spef_names(path):
    """*NAME_MAP names the SPEF's nets actually use: *D_NET nets and the instances of their *CONN *I pins (the map
    also lists pin-less instances, e.g. FILLER_* cells that a filled 6_final.odb has and a 5_2_route.odb never had)"""
    with open(path, "rb") as f:
        data = f.read()
    used = set(CONN.findall(data))
    out = []
    for line in data[:data.find(b"\n*D_NET") + 1].split(b"\n"):
        if line.startswith(b"*NAME_MAP"):
            out = []
            continue
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[0][:1] == b"*" and parts[0][1:].isdigit() and parts[0][1:] in used:
            out.append(parts[1].strip())
    return out


def check(seed, final, spef, show=10):
    s, fn = odb_names(seed), odb_names(final)
    names = spef_names(spef)
    missing = []
    for n in names:
        forms = (n, n.replace(b"\\", b""))
        if any(x in fn for x in forms) and not any(x in s for x in forms):
            missing.append(n.decode(errors="replace"))
    return dict(seed=seed, final=final, spef=spef, spef_names=len(names), stale=bool(missing),
                missing=len(missing), examples=missing[:show])


def main(argv):
    if len(argv) != 4:
        print(__doc__.strip().splitlines()[-1].strip(), file=sys.stderr)
        return 2
    try:
        r = check(*argv[1:4])
    except OSError as e:
        print(json.dumps(dict(error=str(e))))
        return 2
    print(json.dumps(r))
    return 3 if r["stale"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
