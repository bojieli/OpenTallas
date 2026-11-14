#!/usr/bin/env python3
"""DIE-QC-102 v2: R8 table = derived table, except
 (a) COORD option A: members whose sink is in an SU hard lane (sink_part *_su_l0/_su_l1) keep their pre-derive pad;
 (b) W5 r_v pad (structural, coherent): the WHOLE st_a->ctl lane bundle of each slice (r_d regions 0-3 together with
     r_v / r_idx / r_last / l9o_v / stn_fault, one lane) gets +k so region 0 r_d lands >= TARGET cycles after the st_b
     regions 4-7 (TARGET = pre-derive difference + EXTRA). Valid and data of region 0 move together (no r_v/r_d skew).
usage: pin_r8_v2.py DERIVED PRE OUT EXTRA     (PRE may be .json or .json.gz)
Importable: apply_pin(derived_table, pre_table, extra) -> pinned table.  land_r8_derive.py calls it from the derive step
(--pin-pre PRE --pin-extra N) and its check step re-applies it, so a derive that drops the pin fails the check.
PIN_MARK is written into the table note; land_r8_derive.py check refuses a marked table when --pin-pre is missing."""
import gzip, json, re, sys, collections

PIN_MARK = "pin_r8_v2.py"


def load(p):
    return json.load(gzip.open(p, "rt") if str(p).endswith(".gz") else open(p))


def apply_pin(b, a, extra, log=print):
    k = lambda m: (m["sink"], m["sink_port"], str(m["sink_bits"]), re.sub(r"\$\d+", "", m["source"]))
    am = {k(m): m for m in a["members"]}
    c = collections.Counter()
    for m in b["members"]:
        if re.search(r"_su_l[01]$", m["sink_part"]):
            o = am[k(m)]
            if o["pad"] != m["pad"]:
                c["su_pinned"] += 1
            m["pad"] = o["pad"]
            m["landed"] = m["bound"] + m["pad"]

    def rd(t, s, lo):
        v = {m["landed"] for m in t["members"] if m["sink"] == f"dvs_{s}.u_core.u_sub.u_ctl" and m["sink_port"] == "r_d"
             and m["sink_bits"][0][0] == lo}
        assert len(v) == 1, (s, lo, v)
        return v.pop()

    for s in ["W5", "W4", "W3", "W2", "W1", "W0", "E0", "E1", "E2", "E3", "E4", "E5"]:
        dpre = rd(a, s, 0) - rd(a, s, 256)
        dnow = rd(b, s, 0) - rd(b, s, 256)
        kk = max(0, dpre + extra - dnow)
        lane = f"sl_{s}_st_a__x_st_a_ctl"
        n = 0
        if kk:
            for m in b["members"]:
                if m["lane"] == lane and m["sink_part"] == f"sl_{s}_ctl":
                    m["pad"] += kk
                    m["landed"] += kk
                    n += 1
        log(s, "pre_diff", dpre, "derived_diff", dnow, "+", kk, "on", n, "members")
    b["note"] = b.get("note", "") + (f" | DIE-QC-102 {PIN_MARK} extra={extra}: su-lane sink pads pinned (COORD option A); "
                                     "st_a->ctl lane bundle padded so region-0 r_d/r_v land latest")
    log(dict(c))
    return b


if __name__ == "__main__":
    der, pre, out, extra = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    b = apply_pin(load(der), load(pre), extra)
    open(out, "w").write(json.dumps(b, indent=1) + "\n")
