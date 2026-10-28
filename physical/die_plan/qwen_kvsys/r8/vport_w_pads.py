#!/usr/bin/env python3
"""DIE-KV-13 10-28: KV vport W request-lane pads (the DQ <= 15 rule of qkd_pv16_vport_b) as an R8 extra table.

    vport_w_pads.py BIND_DIR R8_LANDING.json OUT.json [--dq-max 15]

VPORT_DQ comes from the MAIN regen_constants.kv_vport rule on the bind (one model, no copy of the formula):
  RT_p = 9 + max_g(D(vq_g) + D(rs_g)),  W_p = landed stages of pvw ctl req_t -> vport_p.pr_t,
  DQ_p = max_q(W_q + RT_q) - (W_p + RT_p).
A vport with DQ_p > dq_max gets pad_p = DQ_p - dq_max extra ot_dp_dly stages on its W request word (pr_t AND pr_valid,
which generic R8 already aligns), so DQ_p = dq_max and RL = max(W + RT) is unchanged (no added round-trip latency).
Output: opentallas.die_plan.r8_extra.v1 members (the R8 table member of the same id with pad/landed raised); bind.py
asbuilt.land_r8_extra makes them authoritative for those ids.  Fails closed if a vport has no pr_t/pr_valid R8 member or
the two do not land together.  Replaces the stale hand table kvbind1025/r8_position_2144/vport_request_extra.json
(no generator was committed for it)."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools/die_plan"))
import regen_constants as RC  # noqa: E402


def pads(bind_dir, r8, dq_max=15, boot=None):
    B = RC.Bound(bind_dir)
    o = RC.Out("qwen_kvsys", B)
    RC.kv_vport(o)
    rec = o.c.get("VPORT_DQ")
    if not rec or rec.get("value") is None:
        raise SystemExit(f"VPORT_DQ not computable on {bind_dir}: {o.c.get('VPORT_DQ') or o.c.get('VPORT_RT')}")
    dq, rt = rec["value"], o.c["VPORT_RT"]["value"]
    model = "regen_constants.kv_vport (RL = max(W + RT), no O)"
    if boot is not None:
        # DIE-KV-13 10-28: the compiled boot image is authoritative for DQ (regen_constants note: boot RL = 4 + WP + O + DQ + RT
        # adds the per-port O); take DQ from kv_boot_v36 prep vport_dq_pads.json made on the SAME bind (no second formula).
        if set(boot["dq_unpadded"]) != set(dq):
            raise SystemExit(f"boot vport set {sorted(boot[dq_unpadded])} != bind vports {sorted(dq)}")
        dq = dict(boot["dq_unpadded"])
        model = "kv_boot_v36 prep vport_dq_pads.json (kv_static_params.schedule, RL = 4 + W + O + DQ + RT)"
    by = {}
    for m in r8["members"]:
        if m["sink"] in dq and m["sink_port"] in ("pr_t", "pr_valid"):
            by.setdefault(m["sink"], []).append(m)
    out, rows = [], {}
    for vp, d in sorted(dq.items()):
        ms = by.get(vp, [])
        if {m["sink_port"] for m in ms} != {"pr_t", "pr_valid"} or len({m["landed"] for m in ms}) != 1:
            raise SystemExit(f"{vp}: R8 W word members {[(m['sink_port'], m['landed']) for m in ms]} (need pr_t+pr_valid aligned)")
        p = max(d - dq_max, 0)
        rows[vp] = dict(RT=rt[vp], DQ=d, pad=p, W=ms[0]["landed"], W_padded=ms[0]["landed"] + p, sink_part=ms[0]["sink_part"])
        if p:
            for m in ms:
                out.append(dict(m, pad=m["pad"] + p, landed=m["landed"] + p, w_pad=p))
    bits = sum((b - a + 1) for m in out for a, b in m["sink_bits"])
    return dict(schema="opentallas.die_plan.r8_extra.v1", die="qwen_kvsys",
                source_bind=str(bind_dir), source_r8_sha256=hashlib.sha256(json.dumps(r8, sort_keys=True).encode()).hexdigest(),
                note=f"DIE-KV-13 vport W request pads: DQ <= {dq_max} ({model}); RL unchanged",
                members=out, ports=rows,
                summary=dict(vports=len(rows), padded=sum(1 for r in rows.values() if r["pad"]),
                             pad_stages=sum(r["pad"] for r in rows.values()), max_pad=max(r["pad"] for r in rows.values()),
                             pad_flops=sum(m["w_pad"] * sum(b - a + 1 for a, b in m["sink_bits"]) for m in out),
                             padded_bits=bits,
                             **(dict(RL=max(r["RT"] + r["W"] for r in rows.values()),
                                     RL_after=max(r["RT"] + r["W_padded"] for r in rows.values())) if boot is None else
                                dict(RL_boot=boot["RL"], RL_note="boot RL = 4 + W + O + DQ + RT; pads = DQ - 15 keep it by construction"))))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bind_dir"); ap.add_argument("r8"); ap.add_argument("out")
    ap.add_argument("--dq-max", type=int, default=15)
    ap.add_argument("--boot-dq", metavar="VPORT_DQ_PADS_JSON", help="kv_boot_v36 prep/vport_dq_pads.json on the same bind: "
                    "DQ from the boot generator (authoritative; adds the per-port O) instead of regen_constants")
    a = ap.parse_args(argv)
    t = pads(a.bind_dir, json.load(open(a.r8)), a.dq_max, json.load(open(a.boot_dq)) if a.boot_dq else None)
    Path(a.out).write_text(json.dumps(t, indent=1) + "\n")
    print(json.dumps(t["summary"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
