#!/usr/bin/env python3
"""DIE-KV-16 10-28: KV PV V-word landing pads (V-D-H rule) as an R8 extra table, plus the check.

    kv_pv_v_pads.py pads  BIND_DIR R8_LANDING.json OUT.json     # table from a bind made WITHOUT this table
    kv_pv_v_pads.py check BIND_DIR [--json OUT]                 # PASS iff every bank meets the rule (exit 0)

Why (RTL, not a new gate): ot_qwen_tp8_pv_wide_ctl_tbf_p checks the 8 vport headers (in_valid/in_t) at one age pa and issues
"the command word for the arrival at pa+1" to every column bank (cmd reg + column pin reg); the bank
(ot_qwen_tp8_pv_slice_t) registers pv2 and bc on one edge and takes V on c_r.take.  So, per bank b fed by vport p, the
V word must reach b exactly (as-built) cycles after p's header reached the ctl plus the bank's command depth:
    VDH(b) = dV(b) - dcmd(b) - dH(p) = 0,   dX = landed - as-built of that crossing member
(V = vport_p.out_v_* -> b.pv2, cmd = pvw ctl.cmd -> b.bc, H = vport_p.out_t -> pvw ctl.in_t).  The vport launch (DQ/W/RT
boot schedule) moves V and H together, so no boot value can absorb a VDH != 0; only landing depths can.  This is the
KV-P6-PV correction d218a2b989 ("V-D-H shift must be 0"), which the DIE-KV-14d column table (cmd/flag only) dropped.
The DIE-KV-15 v_offset_check (one d per vport source, d = dV - dcmd) is necessary, not sufficient: it lets every bank of a
vport sit one constant off its command, and it treats out_v_lo / out_v_hi (one row register, one edge) as two sources.
ASTK response -> pe2: the astk owner launch is free in the PV schedule (KV-P6-PV model: external source), so the rule is
one e = dpe2 - dcmd per astk source (pads lift every bank to the source's max e).
Pads only ADD stages on the V / pe2 member (sink-partition entry; bind.py shares one ot_dp_dly per (in-lane bit, pad)
inside a partition, so the 8 banks of a column and the columns of one pv partition that need the same pad share it).
Fails closed: a member that would need a negative pad (V later than its command) or an R8 row that is not this bind's."""
import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools/die_plan"))
import regen_constants as RC  # noqa: E402

V_SRC = r"^vport_\w+\.out_v_(lo|hi)$"
E_SRC = r"^astk_\w+_owner_\d+__u_owner\.response_data$"
BANK = r"^pvw_\d__u_s\d+_b\d+$"


def _bits(sb):
    return sum(abs(b - a) + 1 for a, b in sb)


def rule(B):
    """per-member target landed depth from the bind (no pads applied by this table yet)."""
    cmd = {}
    for m in B.members(source=r"^pvw_\d__u_ctl\.cmd$", sink=BANK, port=r"^bc$"):
        d = m["landed"] - m["asb"]
        if cmd.setdefault(m["sink"], d) != d:
            raise SystemExit(f"{m['sink']}.bc: two command depths")
    hdr = collections.defaultdict(set)
    for m in B.members(source=r"^vport_\w+\.out_(t|valid)$", sink=r"^pvw_\d__u_ctl$", port=r"^in_(t|valid)$"):
        hdr[m["source"].rsplit(".", 1)[0]].add(m["landed"] - m["asb"])
    for vp, s in hdr.items():
        if len(s) != 1:
            raise SystemExit(f"{vp}: header out_t/out_valid land at different depths {sorted(s)}")
    rows = []
    for m in B.members(source=V_SRC, sink=BANK, port=r"^pv2$"):
        vp = m["source"].rsplit(".", 1)[0]
        if m["sink"] not in cmd or vp not in hdr:
            raise SystemExit(f"{m['sink']}.pv2 <- {m['source']}: no command or header member")
        (dh,) = hdr[vp]
        vdh = (m["landed"] - m["asb"]) - cmd[m["sink"]] - dh
        rows.append(dict(m, kind="V", vdh=vdh, target=m["landed"] - vdh))
    es = B.members(source=E_SRC, sink=BANK, port=r"^pe2$")
    emax = collections.defaultdict(lambda: -10 ** 9)
    for m in es:
        emax[m["source"]] = max(emax[m["source"]], (m["landed"] - m["asb"]) - cmd[m["sink"]])
    for m in es:
        e = (m["landed"] - m["asb"]) - cmd[m["sink"]]
        rows.append(dict(m, kind="E", vdh=e - emax[m["source"]], target=m["landed"] + emax[m["source"]] - e))
    return rows


def check(B):
    rows = rule(B)
    bad = [r for r in rows if r["vdh"] != 0]
    by = collections.Counter((r["kind"], r["vdh"]) for r in bad)
    banks = {r["sink"] for r in rows}
    s = dict(banks=len(banks), members=len(rows), v_members=sum(r["kind"] == "V" for r in rows),
             e_members=sum(r["kind"] == "E" for r in rows), bad=len(bad),
             worst_v=min((r["vdh"] for r in bad if r["kind"] == "V"), default=0),
             worst_e=min((r["vdh"] for r in bad if r["kind"] == "E"), default=0),
             verdict="PASS" if not bad and len(banks) == 512 else "FAIL")
    return s, dict(sorted(((f"{k}:{v}", n) for (k, v), n in by.items())))


def pads(bind_dir, r8):
    B = RC.Bound(bind_dir)
    rows = rule(B)
    by_key = collections.defaultdict(list)
    for x in r8["members"]:
        by_key[(x["sink"], x["sink_port"], x["source"])].append(x)
    out, flops, shared = [], collections.Counter(), {}
    for m in rows:
        add = m["target"] - m["landed"]
        if add < 0:
            raise SystemExit(f"{m['sink']}.{m['port']} <- {m['source']}: needs {add} stages (V after its command)")
        cands = [x for x in by_key.get((m["sink"], m["port"], m["source"]), []) if _bits(x["sink_bits"]) == m["bits"] and x["lane"] == m["lane"]]
        if len(cands) != 1:
            raise SystemExit(f"{m['sink']}.{m['port']} <- {m['source']}: {len(cands)} R8 members (one expected)")
        x = cands[0]
        if x["landed"] != m["landed"] or x["bound"] != m["bound"] or x["asbuilt"] != m["asb"]:
            raise SystemExit(f"{x['id']}: R8 table (asb {x['asbuilt']} bound {x['bound']} landed {x['landed']}) is not the "
                             f"bind's (asb {m['asb']} bound {m['bound']} landed {m['landed']}): stale R8 table")
        if add:
            out.append(dict(x, pad=x["pad"] + add, landed=m["target"], pv_v_pad=add))
            flops[m["kind"]] += add * m["bits"]
            shared[(m["kind"], m["sink_part"], m["source"], x["lane"], add)] = add * m["bits"]
    sh = collections.Counter()
    for k, v in shared.items():
        sh[k[0]] += v
    return dict(schema="opentallas.die_plan.r8_extra.v1", die="qwen_kvsys", kind="kv_pv_v_landing",
                source_bind=str(bind_dir),
                source_r8_sha256=hashlib.sha256(json.dumps(r8, sort_keys=True).encode()).hexdigest(),
                note="DIE-KV-16 PV V-word landing: every bank V-D-H = 0 (V vs its command vs its vport header, as-built "
                     "relative timing); astk pe2 one offset per source.  Generator r8/kv_pv_v_pads.py; check mode reruns it.",
                members=out,
                summary=dict(members=len(out), max_pad=max((x["pv_v_pad"] for x in out), default=0),
                             pad_flops_per_member=dict(flops), pad_flops_per_member_total=sum(flops.values()),
                             pad_flops_shared_est=dict(sh), pad_flops_shared_est_total=sum(sh.values())))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("pads"); p.add_argument("bind_dir"); p.add_argument("r8"); p.add_argument("out")
    c = sp.add_parser("check"); c.add_argument("bind_dir"); c.add_argument("--json")
    a = ap.parse_args(argv)
    if a.cmd == "pads":
        t = pads(a.bind_dir, json.load(open(a.r8)))
        Path(a.out).write_text(json.dumps(t, indent=1) + "\n")
        print(json.dumps(t["summary"]))
        return 0
    s, hist = check(RC.Bound(a.bind_dir))
    print("V_D_H", json.dumps(s)); print("  bad hist", json.dumps(hist)[:2000])
    if a.json:
        Path(a.json).write_text(json.dumps(dict(summary=s, bad_hist=hist), indent=1) + "\n")
    return 0 if s["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
