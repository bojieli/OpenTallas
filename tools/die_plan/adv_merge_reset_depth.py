#!/usr/bin/env python3
"""adv_merge_reset_depth.py -- PRECHECK-R2 static advisory ADV-MERGE-RESET-DEPTH (owner 11-19: an estimator, never a gate).

A hard core with hard_cores[].native_port_adapter.merge {core_port: [native pin, ...]} has several native pins that the
private kit (kit_core_clocks.adapt_core_ports) folds into ONE core pin.  The bind wires every native pin on its own, so
the fold is legal only when all pins of the group carry the same net: either no relay_depth chain on any of them, or
the SAME chain on all of them (ASTK-MERGE-1122 equal_stage_chains: equal stage count, one source).  Otherwise kit-rtl
fails closed with

    core astk_EN: g_phys_fault_u_fault__rst_n merge group is not one net: [i_host_die_rst_n_q[0], lp_astk_EN_..._0[0]]

(real case OPUS-FIX-KV-HUB-R6 11-22: kv3_hub_Eo/Wo astk_* on plan bf83bf83b70c, sealed kits died at kit_rtl rc 2:
reset_leg_plan form M wrote a relay_depth row on the port's own pin only).

Static rule per (type, core, merge group), from the plan only:
  - relay_depth rows (partition_types.<T>.relay_depth[], side sink) whose inst is the core leaf (core inst, or the old
    bound form u_<inst>) and whose port is a pin of the group;
  - PARTIAL: rows on some pins of the group but not all  -> WARN (fix: give every pin the same D, or drop all);
  - UNEQUAL: the pins' D values differ (or one pin carries two D)                          -> WARN;
  - SITES: relay_sites stage keys u_y_xd_<inst>_<pin>_0_<s>.q differ in stage count between pins that carry rows,
    or the stage count != D (sites are seated per chain)                                    -> WARN.
A group with no rows at all is the clean "none" form.  Tools >= main e0c10098d792 generate full equal groups, so a hit
means a hand-written row or an old-tool row.

    findings(raw, plan_path, tree=None, **kw) -> ["WARN ADV-MERGE-RESET-DEPTH ..."]
"""
import re

CHECK = "MERGE-RESET-DEPTH"
MAX_LINES = 20


def _w(obj, msg):
    return f"WARN ADV-{CHECK} {obj}: {msg}"


def _leaf_keys(inst):
    """row inst forms that name this core: the bind leaf (= core inst) and the old bound form u_<inst>."""
    return {inst, "u_" + inst}


def _site_stages(sites, inst, pin):
    """{stage index} seated in relay_sites for the chain u_y_xd_<inst>_<pin>_0_<s>.q (bind's stage names)."""
    if not sites:
        return set()
    pat = re.compile(r"u_y_xd_" + re.escape(inst) + "_" + re.escape(pin) + r"_0_(\d+)\.q(?:\[\d+\])?$")
    out = set()
    for k in sites:
        if pin in k:
            m = pat.match(k)
            if m:
                out.add(int(m.group(1)))
    return out


def check_type(tn, t):
    """-> [(kind, line)] for one partition type."""
    out = []
    rows = [r for r in (t.get("relay_depth") or []) if isinstance(r, dict) and r.get("side", "sink") == "sink"]
    sites = t.get("relay_sites") if isinstance(t.get("relay_sites"), dict) else {}
    for c in t.get("hard_cores") or []:
        spec = c.get("native_port_adapter") or {}
        merge = spec.get("merge") or {}
        if not merge:
            continue
        inst = str(c.get("inst"))
        keys = _leaf_keys(inst)
        by_pin = {}
        for r in rows:
            if r.get("inst") in keys:
                by_pin.setdefault(str(r.get("port")), []).append(r)
        for port, names in sorted(merge.items()):
            names = [str(n) for n in names or []]
            if len(names) < 2:
                continue
            hit = {n: sorted({int(r.get("D", 0)) for r in by_pin.get(n, [])}) for n in names if by_pin.get(n)}
            if not hit:
                continue
            obj = f"{tn} {inst}.{port}"
            miss = [n for n in names if n not in hit]
            ds = sorted({d for v in hit.values() for d in v})
            dtxt = ", ".join(f"{n} D={'/'.join(map(str, v))}" for n, v in sorted(hit.items()))
            if miss:
                out.append(("partial", _w(obj, f"merge group of {len(names)} native pins has relay_depth rows on "
                                               f"{len(hit)} only ({dtxt}; none on {', '.join(miss[:4])}"
                                               f"{' ...' if len(miss) > 4 else ''}) -> kit_rtl 'merge group is not one "
                                               f"net'. Fix: same D={ds[-1]} row on every pin of the group "
                                               f"(reset_leg_plan form M, tools >= e0c10098d792) or drop all rows")))
            if len(ds) > 1 or any(len(v) > 1 for v in hit.values()):
                out.append(("unequal", _w(obj, f"merge group relay_depth D differs between pins ({dtxt}); one depth "
                                               f"required (kit_core_clocks.equal_stage_chains). Fix: one D for the "
                                               f"whole group (max {ds[-1]})")))
            if sites:
                st = {n: len(_site_stages(sites, inst, n)) for n in hit}
                seated = {n: k for n, k in st.items() if k}
                # ASTK-MERGE-1122 form M seats only the port's own chain (the other pins' stages are placed by the
                # tool), so unseated pins are fine; seated chains must agree with each other and with D
                if len(set(seated.values())) > 1 or any(k > hit[n][-1] for n, k in seated.items()):
                    out.append(("sites", _w(obj, "relay_sites stage chains disagree in the merge group ("
                                                 + ", ".join(f"{n} {k} sites vs D {hit[n][-1]}"
                                                             for n, k in sorted(seated.items()))
                                                 + "). Fix: one equal chain (D stages) for the whole group")))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        types = (raw or {}).get("partition_types") or {}
        if not isinstance(types, dict):
            return [_w("not checked", "plan has no partition_types map")]
        res, groups = [], 0
        for tn in sorted(types):
            t = types[tn]
            if not isinstance(t, dict):
                continue
            for c in t.get("hard_cores") or []:
                groups += sum(1 for v in ((c.get("native_port_adapter") or {}).get("merge") or {}).values()
                              if len(v or []) > 1)
            res += check_type(tn, t)
        lines = [ln for _, ln in res]
        out = lines[:MAX_LINES]
        if True:
            kinds = {}
            for k, _ in res:
                kinds[k] = kinds.get(k, 0) + 1
            out.append(_w("summary", f"{len(lines)} finding(s) on {groups} merge group(s) of native_port_adapter "
                                     f"hard cores ({', '.join(f'{k} {v}' for k, v in sorted(kinds.items())) or 'clean'})"
                                     + (f"; first {MAX_LINES} shown" if len(lines) > MAX_LINES else "")))
        return out
    except Exception as e:  # never raise
        return [_w("not checked", f"{type(e).__name__}: {e}")]


if __name__ == "__main__":
    import json
    import sys
    import time
    t0 = time.time()
    p = sys.argv[1]
    r = json.load(open(p))
    t1 = time.time()
    for ln in findings(r, p, sys.argv[2] if len(sys.argv) > 2 else None):
        print(ln)
    print(f"# load {t1 - t0:.1f}s check {time.time() - t1:.2f}s")
