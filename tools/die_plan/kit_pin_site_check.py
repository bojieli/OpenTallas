#!/usr/bin/env python3
"""kit_pin_site_check.py KIT [KIT ...]  (advisory, FAM-KV-IOPC-R2 11-21)

Face pins (io.tcl place_pin, not '# interior') whose own-layer shape lies inside a reserved die clock-tree site route
obstruction (reserved_sites.tcl dbObstruction_create, M1-M7).  Such a pin has no legal access: DRT leaves shorts against
the obstruction or stops with DRT-0255.  kv3_io_cor_v1 proof (11-21): the six pins this check lists (ft11_i[2..7] under
the east-seam site 1276.99-1278.72 x 517.86-518.94) are exactly the six final route DRC shorts.  D26 KV kits: hg family
ft1_o 2, hgi_v3 ft24_i 17, hub_Eo / hub_Wo 24, pv family 20-55, sys_c ft1_o 6.
The cure is in the plan (face pin bits or the die clock site off each other at the seam), not in the kit: carving the
obstruction would put type wires through the die cell's via stack.  Exit 1 when any kit has a hit.
"""
import collections
import re
import sys
from pathlib import Path

OB = re.compile(r"dbObstruction_create \$rs_b \[\[ord::get_db_tech\] findLayer (M\d)\] "
                + r" ".join([r"\[expr \{round\(([-\d.]+)\*\$rs_u\)\}\]"] * 4))
PP = re.compile(r"place_pin -pin_name \{(\S+)\} -layer (\S+) -location \{([-\d.]+) ([-\d.]+)\} "
                r"-pin_size \{([-\d.]+) ([-\d.]+)\}([^\n]*)")


def scan(K):
    """[(pin, layer, x, y, site rect)] of the face pins of kit K inside a same-layer reserved-site obstruction"""
    K = Path(K)
    obs = collections.defaultdict(list)
    for m in OB.finditer((K / "reserved_sites.tcl").read_text()):
        obs[m.group(1)].append(tuple(map(float, m.groups()[1:])))
    hits = []
    for m in PP.finditer((K / "io.tcl").read_text()):
        n, lay = m.group(1), m.group(2)
        if "interior" in m.group(7):
            continue
        x, y, w, h = map(float, m.groups()[2:6])
        r = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
        for s in obs.get(lay, ()):
            if r[0] < s[2] and s[0] < r[2] and r[1] < s[3] and s[1] < r[3]:
                hits.append((n, lay, x, y, s))
                break
    return hits


def main(argv):
    bad = 0
    for K in argv:
        try:
            h = scan(K)
        except OSError as e:
            print(f"{K}: ERR {e}")
            continue
        bad += bool(h)
        bus = collections.Counter(re.sub(r"\[\d+\]$", "", n) for n, *_ in h)
        print(f"{K}: pins_in_obs {len(h)} {dict(bus.most_common(4))}")
        for n, lay, x, y, s in h[:8]:
            print(f"  {n} {lay} ({x:g}, {y:g}) in site {list(s)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
