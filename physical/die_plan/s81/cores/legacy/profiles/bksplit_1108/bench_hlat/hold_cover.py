#!/usr/bin/env python3
"""S81-ARCH-RTL-2 11-12: which hold violators of a dsdv_bksel_q OpenSTA hold dump (pa_hold/hold_all.rpt format:
'Startpoint: ... Endpoint: ... <slack> slack') sit on a hop that HLAT 1 latches (ot_s81ph_hlk u_fl_*), and the
uncovered residue.   usage: hold_cover.py hold_all.rpt [--json OUT]"""
import collections
import json
import re
import sys

HOPS = [  # (latch, launch regex, capture regex)
    ("u_fl_x  b_* -> x_*", r"u_q\.b_(idx|val|lv|last)", r"u_q\.u_s\.in_(idx|val|lv|last)"),
    ("u_fl_i0 x_* -> i0_*", r"u_q\.u_s\.in_", r"u_q\.u_s\.i0_(idx|val|lv|last)"),
    ("u_fl_c1 c1_* -> c2_*", r"u_q\.u_s\.c1_", r"u_q\.u_s\.c2_(p|gt|eq)"),
    ("u_fl_r1 r1 q -> c1_p", r"u_q\.u_s\.g_r1\[\d+\]\.q", r"u_q\.u_s\.c1_p"),
    ("u_fl_r1s rpb/memb -> r1 q", r"u_q\.u_s\.g_r1\[\d+\]\.(rpb|memb)", r"u_q\.u_s\.g_r1\[\d+\]\.q"),
    ("u_fl_pend pend_d1 -> pend_q/o0_p", r"pend_d1", r"u_q\.u_s\.(pend_q|o0_p)"),
    ("u_fl_pe e1/e0 -> pend_q/o0_p", r"u_q\.u_s\.g_pe\[\d+\]\.e[01]", r"u_q\.u_s\.(pend_q|o0_p)"),
    ("u_fl_o0m o0_m -> ofq", r"u_q\.u_s\.o0_m", r"u_q\.u_s\.u_ofq\.wdata"),
    ("u_fl_o0p o0_p/pend_q -> ofq", r"u_q\.u_s\.(pend_q|o0_p)", r"u_q\.u_s\.u_ofq\.wdata"),
    ("u_fl_o0s o0 sel -> ofq", r"u_q\.u_s\.g_o0\[\d+\]\.s[mp]", r"u_q\.u_s\.u_ofq\.wdata"),
    ("u_fl_row hist row -> bank stage", r"u_q\.u_s\.u_h[fc]\.g_row\[\d+\]\.(dg|en|v)", r"u_q\.u_s\.u_h[fc]\.g_bank\[\d+\]\.s_(dg|en|v)"),
    ("u_fl_g1 hist g1 -> s_g", r"u_q\.u_s\.u_h[fc]\.g_bank\[\d+\]\.g1", r"u_q\.u_s\.u_h[fc]\.g_bank\[\d+\]\.s_g"),
]


def main():
    txt = open(sys.argv[1]).read()
    cov, unc, ws = collections.Counter(), collections.Counter(), {}
    for p in txt.split("Startpoint: ")[1:]:
        L = p.split()[0]
        C = re.search(r"Endpoint: (\S+)", p).group(1)
        m = re.search(r"(-?[\d.]+)\s+slack", p)
        s = float(m.group(1)) if m else 0.0
        if s >= 0:
            continue
        hit = next((n for n, a, b in HOPS if re.search(a, L) and re.search(b, C)), None)
        key = hit or (re.sub(r"\[\d+\]", "[]", L.split("$")[0]) + " -> " + re.sub(r"\[\d+\]", "[]", C.split("$")[0]))
        (cov if hit else unc)[key] += 1
        ws[key] = min(ws.get(key, 0.0), s)
    port = {k for k in unc if "fcap" in k}
    rep = dict(violators=sum(cov.values()) + sum(unc.values()), covered=sum(cov.values()), left=sum(unc.values()),
               covered_by_hop={k: dict(n=v, wns=ws[k]) for k, v in cov.most_common()},
               left_wns=min((ws[k] for k in unc), default=0.0),
               left_wns_internal=min((ws[k] for k in unc if k not in port), default=0.0),
               left_port_fcap=sum(unc[k] for k in port),
               left_top={k: dict(n=v, wns=ws[k]) for k, v in unc.most_common(20)})
    print(f"HOLD_COVER violators {rep['violators']} covered {rep['covered']} left {rep['left']} "
          f"left_wns {rep['left_wns']} (internal {rep['left_wns_internal']}, port fcap {rep['left_port_fcap']})")
    if "--json" in sys.argv:
        open(sys.argv[sys.argv.index("--json") + 1], "w").write(json.dumps(rep, indent=1) + "\n")


if __name__ == "__main__":
    main()
