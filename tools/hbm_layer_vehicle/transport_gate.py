#!/usr/bin/env python3
"""TOK-HBM 10-24: SU / HC transport bind gate for a post-relay HBM die (die.v only; r18h5 today, B2l native bind next).

The token gate (results/token_pass/tok_hbm_1024/README.md) fails every SU.VOP and HC_MIX record on r18h5 because the
relay layer gave legs that must land together different depths, and bound the latency parameters as if they were
equal.  Owner decision 10-24 18:47: bind B2l natively.  This gate states the rules that bind must meet, measures them
on a die.v with prog_transport's lane model (relay 1 edge; half-cycle lane stages N + landing ceil(N/2)+1+E, K from
the landing's ties) and prints the pads / parameters that would make the die meet them.

Rules (group = legs that must land on one edge relative to each other; FAIL if any rule is broken):
  HC_XRD   hc_eng.{d_v,i_v} -> hc_<q> (root -> quarter) equal over the 4 quarters, and hc_eng XRD == that depth
  HC_XRU   hc_eng.qps_v elements (quarter -> root) equal over the 4 quarters, and hc_eng XRU == that depth
           (ot_hbm_hc_root_static.sv:26-27; l3_vm_hc_coll.py: compiler RAW0 = 165 + XRD + XRU)
  HC_LAUNCH host launch -> hc_<q> / hc_eng equal (one programme start for root + quarters)
  SU_CFG   pgp_<q>.{cfg_we,cfg_bank,cfg_row,cfg_data,start,length} equal per quarter (a config write pairs one drive)
  SU_CMD   pgp_<q>.command -> su_<q><g>.{control,vmr_cmd,vmw_cmd,tree_cmd} equal over slices g and ports
  SU_BANK  per slice: RT_b = BANK + PIN + lane(su.lg_rq -> vmb_<q><b>.rq0) + lane(vmb.rr0 -> su.lg_rr) equal over
           the slice's two banks and READ_RETURN == 10 + RT - 6 (write: wq0 / wq_done0, WRITE_RETURN == 7 + RT - 3)
           (d4g_bank_latency.py rules EQUAL + PARAM, pin 1 = hfd_vms_bank_native_q0_faces)
  SU_CAL   INFO (not a gate rule since 2026-10-24 evening): rel_b = lane(calendar_<q> -> vmb_<q><b>.rslot)
           - lane(calendar_<q> -> su_<q><g>.lg_read) - lane(rq_b).  Every layer replay installs the SU calendar as
           cx_layer_1021.epoch_calendar = ONE constant row (all banks owner 0, all taps local) looped over the epoch,
           so rel_b cannot mis-time a grant inside the epoch; a multi-row calendar absorbs per-bank rel_b through
           native_su_calendar.compile_calendar(request_lane_edges_by_bank=...).  Reported for that compiler.
  python3 tools/hbm_layer_vehicle/transport_gate.py --die-v die.v --out gate.json
Source-functional lane timing only (K/N model), never a physical-clock qualification.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import coll_transport as CT  # noqa: E402
import prog_transport as PT  # noqa: E402

SCHEMA = "opentallas.hbm_transport_gate.v1"
QS = PT.QS
BANK_RD, BANK_WR = 6, 3
PIN = {"hfd_vms_bank_native_q0_faces": 1}


def params(die_v, names):
    """{instance: {param: int}} from the instance header lines of die.v."""
    out = {}
    rx = re.compile(r"^\s*(\w+)\s*#\((.*)\)\s+(\w+)\s*\(\s*$")
    for line in Path(die_v).open():
        m = rx.match(line)
        if m and m[3] in names:
            out[m[3]] = {k: int(v) for k, v in re.findall(r"\.(\w+)\((-?\d+)\)", m[2])}
    return out


def elems(inst, name, port):
    """per element of the port concat (MSB first): (latency, root)."""
    if name not in inst or port not in inst[name][1]:
        return []
    return [(x["latency_edges"], x["root"]) for x in PT.lanes_of_concat(inst, name, port)]


def lane_from(inst, name, port, src):
    """latency of the element of name.port whose root mentions src (None if absent; max if several)."""
    v = [lat for lat, root in elems(inst, name, port) if src in root]
    return max(v) if v else None


def rule(name, ok, **kw):
    return dict(rule=name, status="PASS" if ok else "FAIL", **kw)


def gate(die_v):
    names = ({f"pgp_{q}" for q in QS} | {f"hc_{q}" for q in QS} | {f"hleaf_{q}" for q in QS} | {"hc_eng"}
             | {f"calendar_{q}" for q in QS} | {f"su_{q}{g}" for q in QS for g in range(4)}
             | {f"vmb_{q}{b}" for q in QS for b in range(8)})
    PT.load_pads(die_v)
    inst = CT.parse_instances(die_v, names)
    par = params(die_v, names)
    res = []
    # ---- HC
    if "hc_eng" in inst:
        down = {q: PT.lane(inst, f"hc_{q}", "d_v")["latency_edges"] for q in QS if f"hc_{q}" in inst}
        up = [lat for lat, _ in elems(inst, "hc_eng", "qps_v")]
        xrd, xru = par.get("hc_eng", {}).get("XRD", 0), par.get("hc_eng", {}).get("XRU", 0)
        res.append(rule("HC_XRD", len(set(down.values())) == 1 and xrd == max(down.values()), legs=down,
                        bound_XRD=xrd, fix=dict(pad={q: max(down.values()) - v for q, v in down.items()},
                                                XRD=max(down.values()))))
        res.append(rule("HC_XRU", len(set(up)) == 1 and up and xru == max(up), legs=up, bound_XRU=xru,
                        fix=dict(pad=[max(up) - v for v in up], XRU=max(up) if up else None,
                                 RAW0=165 + max(down.values()) + (max(up) if up else 0))))
        la = {t: PT.lane(inst, t, "launch_v", through=2)["latency_edges"]
              for t in [f"hc_{q}" for q in QS] + ["hc_eng"] if t in inst and "launch_v" in inst[t][1]}
        res.append(rule("HC_LAUNCH", len(set(la.values())) == 1, legs=la,
                        fix=dict(pad={t: max(la.values()) - v for t, v in la.items()})))
    # ---- SU
    for q in QS:
        p = f"pgp_{q}"
        if p in inst:
            cfg = {x: PT.lane(inst, p, x)["latency_edges"] for x in PT.SU_PORTS if x in inst[p][1]}
            res.append(rule(f"SU_CFG_{q}", len(set(cfg.values())) == 1, legs=cfg,
                            fix=dict(pad={k: max(cfg.values()) - v for k, v in cfg.items()})))
        cmd = {}
        for g in range(4):
            s = f"su_{q}{g}"
            for port in ("control", "vmr_cmd", "vmw_cmd", "tree_cmd"):
                v = [lat for lat, root in elems(inst, s, port) if f"pgp_{q}__command" in root]
                if v:
                    cmd[f"{s}.{port}"] = sorted(set(v))
        if cmd:
            allv = [x for v in cmd.values() for x in v]
            res.append(rule(f"SU_CMD_{q}", len(set(allv)) == 1, legs=cmd, fix=dict(target=max(allv))))
        bank, cal = {}, {}
        lg = {g: lane_from(inst, f"su_{q}{g}", "lg_read", f"calendar_{q}__lg_local") for g in range(4)}
        for g in range(4):
            s = f"su_{q}{g}"
            if s not in inst:
                continue
            rr_p, wr_p = par.get(s, {}).get("READ_RETURN"), par.get(s, {}).get("WRITE_RETURN")
            rows = {}
            for b in (2 * g, 2 * g + 1):
                v = f"vmb_{q}{b}"
                if v not in inst:
                    continue
                pin = PIN.get(inst[v][0], 0)
                rq = lane_from(inst, v, "rq0", f"{s}__lg_rq")
                rr = lane_from(inst, s, "lg_rr", f"{v}__rr0")
                wq = lane_from(inst, v, "wq0", f"{s}__lg_wq")
                wd = lane_from(inst, s, "lg_w_done", f"{v}__wq_done0")
                slot = lane_from(inst, v, "rslot", f"calendar_{q}__")
                rows[b] = dict(rq=rq, rr=rr, wq=wq, wd=wd, slot=slot,
                               rt_rd=None if None in (rq, rr) else BANK_RD + pin + rq + rr,
                               rt_wr=None if None in (wq, wd) else BANK_WR + pin + wq + wd)
                if None not in (slot, lg[g], rq):
                    cal[b] = slot - lg[g] - rq
            rts = [r["rt_rd"] for r in rows.values() if r["rt_rd"] is not None]
            wts = [r["rt_wr"] for r in rows.values() if r["rt_wr"] is not None]
            ok = (rts and len(set(rts)) == 1 and rr_p == 10 + rts[0] - BANK_RD
                  and wts and len(set(wts)) == 1 and wr_p == 7 + wts[0] - BANK_WR)
            bank[s] = dict(banks=rows, READ_RETURN=rr_p, WRITE_RETURN=wr_p,
                           need_READ_RETURN=sorted({10 + x - BANK_RD for x in rts}),
                           need_WRITE_RETURN=sorted({7 + x - BANK_WR for x in wts}), ok=bool(ok))
        if bank:
            res.append(rule(f"SU_BANK_{q}", all(v["ok"] for v in bank.values()), slices=bank))
        if cal:
            res.append(dict(rule=f"SU_CAL_{q}", status="INFO", equal=len(set(cal.values())) == 1, rel=cal,
                            lg_read=lg, compile_request_lane_offset={b: max(cal.values()) - v for b, v in cal.items()}))
    fails = [r["rule"] for r in res if r["status"] == "FAIL"]
    return dict(schema=SCHEMA, die_v=str(die_v), verdict="PASS" if not fails else "FAIL", failing=fails, rules=res,
                scope="source-functional lane timing (K/N model, K from die.v landing ties); bind rules only")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--die-v", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    g = gate(a.die_v)
    a.out.write_text(json.dumps(g, indent=1) + "\n")
    print(f"TRANSPORT_GATE {g['verdict']} rules={len(g['rules'])} failing={','.join(g['failing']) or '-'}")
    return 0 if g["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
