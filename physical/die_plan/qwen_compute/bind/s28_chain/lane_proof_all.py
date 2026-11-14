#!/usr/bin/env python3
"""QC-S28-BIND gate (COORD via DIE-QC-100 11-12): delivered lane latency on the bound RTL + kit-inserted stations, ALL lanes.
CTLCAP's lane_proof.py (ctlcap/lane_proof.py 6dee598549cf) counts one lane by applying kit_istations --apply to scratch
copies of the source and receiver bound modules.  This driver does the same with ONE kit_istations run per type (cached;
a type's bound module is shared by every lane of that type) and the SAME instance rule (imported from lane_proof.py's
source text, not re-typed):
  source u_ist_<bus_out>_<j> + u_bout_<bus_out>[_pad<j>] ; ft stations (table row) ; receiver landing = table row
  clock_landing (DIE-QC-100 rule; the u_cland ring DEPTH is not the landing cycle count) + u_bin_<bus_in>[_pad<j>] +
  u_ist_<bus_in>_<j> + u_lpad_<bus_in> D ; +1 per hard-macro endpoint (its boundary register is inside the macro, no RTL)
  measured == bind_latency plan_cycles (== bound_stages) else MISMATCH; a type kit_istations cannot run on -> UNMEASURED.
  Landing (OUT_landing.tsv): bound strap tie == bind ring_k mod 2^kw per receiver port; lane added_cycles == table.
usage (tree root): lane_proof_all.py BIND_DIR PLAN WORK OUT.tsv [--jobs N]     exit 0 clean / 4 mismatch / 5 unmeasured
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

LP = Path("/srv/opentallas-scratch2/claude/qc-s28-hf1c/ctlcap/lane_proof.py")
TOOLS = Path("tools/die_plan").resolve()


def _insts_fn():
    src = LP.read_text()
    i = src.index("def insts(")
    j = src.index("\n\n\n", i)
    ns = {"re": re}
    exec(src[i:j], ns)              # CTLCAP's exact counting rule
    return ns["insts"]


insts = _insts_fn()


def kit_one(args):
    """scratch kit copy prepared as bind.py kit-rtl does for kit_istations (CTLCAP kit_emul.py f0a3302e6429 steps):
    1. param_wrap.wrap_bound(bound, hard_cores) rename of planned param_wrap instances to their hard-core master;
    2. kit_rtl.json narrow_buses + spare_out_bits for every narrow OUTPUT (bound u_bout W < plan width).
    Narrow INPUTS are not emulated (need the bind dead-input proof) and are reported."""
    tn, f, plan, work = args
    sys.path.insert(0, str(TOOLS))
    import param_wrap
    import gen_rtl
    t = json.loads(Path(plan).read_text())["partition_types"][tn]
    d = Path(work) / tn
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    txt, rec, srcs = param_wrap.wrap_bound(Path(f).read_text(), t.get("hard_cores"))
    dst = d / Path(f).name
    dst.write_text(txt)
    fl = [str(dst)]
    for mname, src in srcs.items():
        q = d / (mname + ".sv")
        q.write_text(src)
        fl.append(str(q))
    narrow, spare = [], []
    for b in t.get("buses", []):
        if b["dir"] != "out":
            continue
        n = gen_rtl.sv_id(b["name"])
        w = re.findall(rf"\bot_dp_ste?\s+#\(\.W\((\d+)\)\)\s+u_bout_{re.escape(n)}\s*\(", txt)
        if len(w) == 1 and int(w[0]) < b["width"]:
            narrow.append(dict(port=n, plan=b["width"], bound=int(w[0])))
            spare.append(dict(port=n, bits=b["width"] - int(w[0])))
    (d / "kit_rtl.json").write_text(json.dumps({"files": fl, "bound_module": dst.name[:-3], "narrow_buses": narrow,
                                                "spare_out_bits": spare}, indent=1))
    r = subprocess.run([sys.executable, "-I", str(TOOLS / "kit_istations.py"), plan, tn, str(d), "--apply"],
                       capture_output=True, text=True, cwd=str(TOOLS.parent.parent))
    if r.returncode != 0:
        return tn, None, f"kit_istations rc {r.returncode}: {r.stderr.strip()[-300:]}"
    return tn, str(dst), None


def landing_check(bind, rows_t, ptype):
    """count-aligned landings (bind_clock_landings.json ports): (1) the strap tied at the parent on the receiver instance
    (bound top .strap_ca_k_<bus>(N'b...)) == (ring_k + WREG + FREG of that bound u_cland ring) mod 2^kw (count_straps kw) - the bound K is what bind solved;
    (2) the lane's landing cycles (SUM of added_cycles over its series crossings = its ports) == latency-table clock_landing.  K is the ring
    read-pointer alignment, NOT a latency: no K+1 rule.  Returns (rows, n_bad)."""
    d = json.loads((Path(bind) / "bind_clock_landings.json").read_text())
    kw = {(tn, b): v["kw"] for tn, t in d["count_straps"]["types"].items() for b, v in t.get("buses", {}).items()}
    top = next((Path(bind) / "rtl").glob("*_bound_top.sv")).read_text()
    ties = {}
    for m in re.finditer(r"^\s+\w+\s*(?:#\((?:[^()]|\([^()]*\))*\)\s*)?(\w+)\s*\((.*?)\);", top, re.M | re.S):
        for b, w, v in re.findall(r"\.strap_ca_k_(\w+)\(\s*(\d+)'b([01]+)\s*\)", m.group(2)):
            ties[(m.group(1), b)] = int(v, 2)
    # WREG / FREG of each receiver ring, read from the bound partition module (each adds 1 to the tied K)
    files = {}
    for f in (Path(bind) / "rtl").glob("*.sv"):
        with open(f) as fh:
            mm = re.search(r"partition type (\S+?)\.", fh.readline())
        if mm:
            files[mm.group(1)] = f
    regs = {}

    def kadd(tn, b):
        if (tn, b) not in regs:
            txt = files[tn].read_text() if tn in files else ""
            mm = re.search(r"ot_dp_clk_landing_cas\s*#\(((?:[^()]|\([^()]*\))*)\)\s*u_cland_" + re.escape(b) + r"\s*\(", txt)
            par = mm.group(1) if mm else ""
            g = lambda n: int((re.search(r"\." + n + r"\((\d+)\)", par) or [None, "0"])[1])
            regs[(tn, b)] = (g("WREG") + g("FREG")) if mm else None
        return regs[(tn, b)]
    out, bad, lane_add = [], 0, {}
    for q in d["ports"]:
        lane_add.setdefault(q["lane"], []).append(int(q.get("added_cycles", 0)))
        tn, b = ptype.get(q["dst"]), q["dst_bus"]
        k = q.get("ring_k")
        if (tn, b) in kw:
            ka = kadd(tn, b)
            want = None if ka is None else (int(k) + ka) % (1 << kw[(tn, b)])
            got = ties.get((q["dst"], b))
            v = ("NO_RING" if want is None else "OK" if got == want else
                 ("NO_TIE" if got is None else "STRAP_MISMATCH"))
            out.append([q["port"], q["lane"], q["dst"], b, str(k), str(want), str(got), v])
            bad += v != "OK"
    for ln, adds in lane_add.items():
        t = int((rows_t.get(ln) or {}).get("clock_landing", 0) or 0)
        v = "OK" if sum(adds) == t else "LANDING_CYCLES_MISMATCH"
        out.append(["lane", ln, "", "", str(len(adds)), str(t), str(sum(adds)), v])
        bad += v != "OK"
    return out, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bind")
    ap.add_argument("plan")
    ap.add_argument("work")
    ap.add_argument("out")
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text())
    parts = raw["partitions"]
    ptype = {p["name"]: p["type"] for p in parts} if isinstance(parts, list) else {k: v["type"] for k, v in parts.items()}
    rows_t = raw["latency"]["lanes"]
    PT = raw["partition_types"]
    lanes = json.loads((Path(a.bind) / "bind_latency.json").read_text())["buses"]
    files = {}
    for f in (Path(a.bind) / "rtl").glob("*.sv"):
        with open(f) as fh:
            m = re.search(r"partition type (\S+?)\.", fh.readline())
        if m:
            files[m.group(1)] = str(f)
    need = sorted({ptype[L["src"]] for L in lanes} | {ptype[L["dst"]] for L in lanes})
    unmeasured = {tn: f"no bound RTL file for type {tn}" for tn in need if tn not in files}
    jobs = [(tn, files[tn], a.plan, a.work) for tn in need if tn in files]
    kitted = {}
    with ProcessPoolExecutor(a.jobs) as ex:
        for tn, path, err in ex.map(kit_one, jobs):
            if err:
                unmeasured[tn] = err
            else:
                kitted[tn] = Path(path).read_text()
    out, mis, unm, priced = [], 0, 0, 0
    for L in lanes:
        st, dt = ptype[L["src"]], ptype[L["dst"]]
        row = rows_t.get(L["lane"], {})
        if st in unmeasured or dt in unmeasured:
            unm += 1
            out.append([L["lane"], st, dt, "", "", "", "", "", L["plan_cycles"], L["bound_stages"], "UNMEASURED",
                        unmeasured.get(st) or unmeasured.get(dt)])
            continue
        s, d = insts(kitted[st], L["bus_out"]), insts(kitted[dt], L["bus_in"])
        nist = sum(1 for x in s + d if x["inst"].startswith("u_ist_"))
        priced += nist > 0
        ft = int(row.get("stations", 0) or 0)
        land = int(row.get("clock_landing", 0) or 0)          # receiver landing = the TABLE value (not the ring DEPTH)
        hard = int(bool(PT[st].get("hard"))) + int(bool(PT[dt].get("hard")))   # boundary register inside a hard macro
        tot = sum(x["stages"] for x in s + d if not x["inst"].startswith("u_cland_")) + ft + land + hard
        ok = tot == L["plan_cycles"] == L["bound_stages"]
        mis += not ok
        out.append([L["lane"], st, dt, str(nist), str(ft), str(land), str(hard), str(tot), L["plan_cycles"],
                    L["bound_stages"], ("OK_HARD" if hard else "OK") if ok else "MISMATCH",
                    " ".join(f"{x['inst']}:{x['stages']}" for x in s + d)])
    with open(a.out, "w") as f:
        f.write("lane\tsrc_type\tdst_type\tn_ist\tft\tlanding_table\thard_boundary\tmeasured\tplan_cycles\tbound_stages\tverdict\tdetail\n")
        for r in out:
            f.write("\t".join(str(x) for x in r) + "\n")
    lrows, lbad = landing_check(a.bind, rows_t, ptype)
    with open(re.sub(r"\.tsv$", "", a.out) + "_landing.tsv", "w") as f:
        f.write("port\tlane\tdst\tbus\tring_k\twant_tie_or_table\tgot\tverdict\n")
        for r in lrows:
            f.write("\t".join(r) + "\n")
    import collections
    print("LANDING_PROOF", dict(collections.Counter(r[-1] for r in lrows)), "bad", lbad)
    mis += lbad
    print("LANE_PROOF lanes", len(lanes), "priced(u_ist)", priced, "mismatch", mis, "unmeasured", unm,
          "types kitted", len(kitted), "unmeasured types", sorted(unmeasured))
    sys.exit(4 if mis else 5 if unm else 0)


if __name__ == "__main__":
    main()
