#!/usr/bin/env python3
"""DIE-S81-45 10-31: serdes__t12 (lk_WS3) PMA pair + KP4 decoder SRAMs + line-side pads + rck pad clock in the WS3
replanned shore lot (COORD 17:0x WS3 exception, item: t12 PMA + KP4 SRAM placement).

The WS3 lot (u_phy origin/outline, clock keepout, die PG domain phy_lk_WS3 and die io io_lk_WS3_u_phy) is already the
2246.4 x 322.84 shore lot of the WS3 candidate, so only what delta_serdes_lots_1031 adds on the sibling types is added,
with the same placement functions: delta_pma_views_1031.place/part (pair at the lot top edge), the turning-slot
corner site of delta_serdes_lots_1031.corner_sites for the KP4 SRAM pair (t12: every ft slot S<->W, like t13/t4),
delta_kp4_srams_1031.PADS / rck_pad_clock, core_pg_connect.  Only serdes__t12 is rewritten (compact_plan._d text).
Refuses a second run.

    python3 physical/die_plan/s81/delta_t12pma_1031.py PLAN_IN PLAN_OUT RECEIPT
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))
import compact_plan as CP  # noqa: E402
import schema as S  # noqa: E402
import importlib.util  # noqa: E402


def _mod(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SL = _mod("delta_serdes_lots_1031")
PMA, KP4 = SL.PMA, SL.KP4
TN = "serdes__t12"


def main(src, dst, receipt):
    text = Path(src).read_text()
    plan = json.loads(text)
    orig = json.loads(text)
    t = plan["partition_types"][TN]
    c = next(c for c in t["contents"] if c.get("module") == "ot_pdie_serdes")
    if c.get("physical_parts") or t.get("pads") or "pad_clock" in t["clock"]:
        raise SystemExit(f"{TN}: already has PMA parts / pads / pad_clock (second run refused)")
    lo, lw = c["origin_um"], c["outline_um"]
    ko = t["clock"]["keepouts_um"][0]
    assert ko[1] <= lo[1] and lo[1] + lw[1] <= ko[3] + 1e-6 and lo[0] >= ko[0] and lo[0] + lw[0] <= ko[2] + 1e-6, (lo, lw, ko)
    got = PMA.place(lo, lw)
    if got is None or got[2] is None:
        raise SystemExit(f"{TN}: PMA pair does not fit the lot {lo} {lw}")
    x, y_tx, y_rx = got
    c["physical_parts"] = [PMA.part(*PMA.LEAVES[0], x, y_tx), PMA.part(*PMA.LEAVES[1], x, y_rx)]
    P = S.Plan(json.loads(text), src)
    taps = [(tx, ty) for _, tx, ty in S.tap_grid(P, TN)]
    sr = SL.corner_sites(t, taps)
    if sr is None:
        raise SystemExit(f"{TN}: no KP4 SRAM site")
    c["physical_parts"] += [KP4.part(*g) for g in sr]
    c["note"] = c.get("note", "") + ("; DIE-S81-45 10-31 (delta_t12pma_1031): + PMA abstracts u_ptx/u_prx + KP4 decoder "
                                     "SRAMs (delta_pma_views_1031 / delta_serdes_lots_1031.corner_sites placement functions)")
    t["core_pg_connect"] = True
    t["pads"] = [json.loads(json.dumps(p)) for p in KP4.PADS]
    rx = next(q for q in c["physical_parts"] if q["physical_master"] == "ot_s81_pma_rxm")
    t["clock"]["pad_clock"] = KP4.rck_pad_clock(P, t, rx, c["physical_parts"])
    # key order as on the sibling types: module, core_pg_connect, pads first
    sib = list(plan["partition_types"]["serdes__t13"].keys())
    t2 = {k: t[k] for k in sib if k in t}
    t2.update({k: v for k, v in t.items() if k not in t2})
    plan["partition_types"][TN] = t2
    ck = t2["clock"]
    t2["clock"] = {"pad_clock": ck["pad_clock"], **{k: v for k, v in ck.items() if k != "pad_clock"}}
    m = re.search(r"^  \"" + re.escape(TN) + r"\": ", text, re.M)
    old, j = json.JSONDecoder().raw_decode(text, m.end())
    assert CP._d(old, 2) == text[m.end():j], "t12 text style differs from compact_plan._d"
    out = text[:m.end()] + CP._d(t2, 2) + text[j:]
    assert json.loads(out) == plan
    for k in plan:
        if k != "partition_types":
            assert plan[k] == orig[k], k
    for k in plan["partition_types"]:
        if k != TN:
            assert plan["partition_types"][k] == orig["partition_types"][k], k
    Path(dst).write_text(out)
    sha = lambda s: hashlib.sha256(s.encode()).hexdigest()[:12]
    row = dict(type=TN, lot=[lo, lw], keepout=ko, pma=dict(x=x, y_tx=y_tx, y_rx=y_rx), sram_sites=[[g[1], g[3], g[4]] for g in sr],
               pad_clock=t2["clock"]["pad_clock"]["pins"][0]["xy_um"])
    Path(receipt).write_text(json.dumps(dict(kind="S81_T12_PMA_KP4_1031", plan_in=sha(text), plan_out=sha(out), row=row,
                                             unchanged="lot, keepout, die PG/io, outline, pins, buses, ft slots, stations, other types"),
                                        indent=1) + "\n")
    print(json.dumps(dict(plan_in=sha(text), plan_out=sha(out), row=row)))


if __name__ == "__main__":
    main(*sys.argv[1:4])
