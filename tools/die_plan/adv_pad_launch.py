"""adv_pad_launch.py -- PRECHECK ADV-PAD-LAUNCH (COORD 11-23 21:0x, static estimator, advisory, never a gate).

FABLE-RC-QC found on QC sle_ctl (hub 79a52775, census in lanes/posts/QC-SLECTL-RESYN.md RESULT 2/3): internal_stations
x_su_c_p1_o / x_su_c_p2_o price the station chain as launched from the control core leaf (launch u_ctl, from_um = leaf_um),
but the real launching register is a pad-stage register (r8b_strap_r8pad_u_rp_chd_q_1) about 400 um away from the first
station: 320 endpoints, worst -93 ps TT.  The plan priced hop 0 as leaf -> regs_um[0]; silicon sees pad -> decode -> regs_um[0].

Check, per partition type and internal_stations row (regs_um present):
  priced hop0  = dist(from_um, regs_um[0])
  real   hop0  = dist(real launch, regs_um[0])
  HIT when real hop0 > hop (default 300 um, the kit station knee) and real hop0 - priced hop0 > hop/4.
Real launch candidates, strongest first:
  MEASURED  kw measured={type: {conn: [x, y]}} (a placed-DB census; the RC lanes' evidence)
  R8PAD     PROXY (stations launched from a core leaf, i.e. launch is not a face register): nearest strap_r8pad_* count-strap site of the same type, only when it lies within die.rep_um of the priced
            launch (a pad stage that plausibly feeds this core pin group); the plan has no per-lane pad site, so this is
            an estimate and is labelled PROXY.
Fix owner: seat the last pad stage next to the first station (relay_sites) or add a stage-0 station at the decode output.
findings(raw, plan_path, tree=None, **kw) -> WARN lines; hits(raw, ...) -> structured rows.
"""
import math

CHECK = "ADV-PAD-LAUNCH"
MAX_LINES = 20
HOP_UM = 300.0


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def _d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _r8_sites(t):
    out = []
    for c in t.get("count_straps") or []:
        if "r8pad" in str(c.get("name", "")):
            out += [s for s in c.get("sites_um") or [] if isinstance(s, (list, tuple)) and len(s) == 2]
    return out


def hits(raw, hop=None, measured=None, rep=None):
    hop = float(hop or HOP_UM)
    rep = float(rep or (raw.get("die") or {}).get("rep_um") or 450.0)
    measured = measured or {}
    rows = []
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        r8 = _r8_sites(t)
        for s in t.get("internal_stations") or []:
            regs, src = s.get("regs_um") or [], s.get("from_um")
            if not regs or not src or len(regs[0]) != 2:
                continue
            conn = s.get("conn")
            r0 = regs[0]
            priced = _d(src, r0)
            real = None
            m = (measured.get(tn) or {}).get(conn)
            if m:
                real = ("MEASURED", m, _d(m, r0))
            elif r8 and not str(s.get("launch", "")).startswith("face"):
                near = [q for q in r8 if _d(q, s.get("leaf_um") or src) <= rep]
                if near:
                    site = min(near, key=lambda q: _d(q, r0))
                    real = ("R8PAD-PROXY", site, _d(site, r0))
            if real and real[2] > hop and real[2] - priced > hop / 4:
                rows.append(dict(type=tn, conn=conn, launch=s.get("launch"), basis=real[0], priced_from=list(src),
                                 real_from=list(real[1]), priced_hop=round(priced), real_hop=round(real[2]),
                                 gap=round(_d(src, real[1])), stations=len(regs)))
    rows.sort(key=lambda r: -(r["real_hop"] - r["priced_hop"]))
    return rows


def findings(raw, plan_path, tree=None, **kw):
    try:
        rows = hits(raw, kw.get("hop"), kw.get("measured"))
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]
    out = [_w(f"{r['type']} {r['conn']}:", f"priced launch {r['launch']} {r['priced_from']} hop0 {r['priced_hop']} um, "
              f"real launch {r['basis']} {r['real_from']} hop0 {r['real_hop']} um (gap {r['gap']} um) > station reach; "
              "fix: seat the pad stage at the first station or add a stage-0 station") for r in rows[:MAX_LINES]]
    out.append(_w("summary", f"{len(rows)} station chain(s) priced from a launch point that differs from the real launching register"))
    return out


if __name__ == "__main__":
    import json
    import sys
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1]):
        print(ln)
