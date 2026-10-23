#!/usr/bin/env python3
"""HBM-P4-SM (10-23): structural quarter-crossing check of ot_hbm_accel_smh_attn (COORD R6(1), README "RTL changes").

The SM top is elaborated with yosys (proc + flatten of the top glue only); its hard children (u_front, the 16 tiles, the 8
BEs, the int8 tile) are black boxes.  Their port launch / capture kinds come from the MEASURED hierarchical-netlist
classification (inputs/sm_conn_r18g.json + sm_internal_census.tsv, tools/net_analyze.py on the r18h5 SM view): the
children are unchanged by QSPLIT, only the top changes.  Quarters: children from sm_split.json; top flops by instance
name (u_qs_b_* -> b, every other top flop / gate -> c, the top glue's quarter); SM input ports land on d (QSPLIT 0, the
as-built plan) or c (QSPLIT 1, R2-alt); the result ports (rv / rrow / rdata / fault / schedule_fault) land on a.

Every top-level path (source = child output / top flop / input port, through top comb glue, sink = child input / top flop
D / output port) is checked: each change of quarter along it must be launched by a flop and captured by a flop
(no top comb glue on the crossing side, child port kind 'reg'), and quarters must be adjacent (a-b-c-d).

  qsplit_check.py --qsplit 0|1 [--int8 1 --int8w 1] --out R.json      (exit 0 iff no unregistered / non-adjacent bit)
"""
import argparse
import collections
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPLIT = HERE.parent
ROOT = SPLIT.parents[3]
YOSYS = os.environ.get("YOSYS") or os.path.expanduser("~/.local/opentallas-tools/yosys-0.68/bin/yosys")
TOP = "ot_hbm_accel_smh_attn"
CHILD_FILES = ["rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_front_static.sv", "rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_tile.sv",
               "rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_be.sv", "rtl/hbm_accel/sm/static/ot_smh_int8_tile.sv",
               "rtl/hbm_accel/sm/static/ot_smh_static_int8.sv"]
DEFINES = ["OT_SMH_FC_HIER", "OT_SMH_HIER", "OT_SMH_XLK", "OT_FP_DATA_NORST", "OT_SMH_DRST0", "OT_SMH_RSTRELAY"]
ORDER = "abcd"
IN_PORTS = {"command", "kv_desc", "packet", "xw_en", "xw_addr", "xw_grp", "xw_data"}
OUT_PORTS = {"rv", "rrow", "rdata", "fault", "schedule_fault"}
SKIP_PORTS = {"clk", "rst_n", "request"}       # clock / reset trees are planned per quarter; request is unconnected on die


def elaborate(qsplit, int8, int8w, work, qsmut=0):
    js = work / f"top_q{qsplit}_m{qsmut}.json"
    d = " ".join(f"-D{x}" for x in DEFINES)
    lib = " ".join(str(ROOT / f) for f in CHILD_FILES)
    ys = (f"read_verilog -sv -lib {d} {lib}\n"
          f"read_verilog -sv {d} {ROOT / 'rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv'}\n"
          f"chparam -set QSPLIT {qsplit} -set ENABLE_INT8 {int8} -set INT8W {int8w} -set QSMUT {qsmut} {TOP}\n"
          f"hierarchy -top {TOP}\nproc\nflatten\nopt -purge\nwrite_json {js}\n")
    (work / f"top_q{qsplit}_m{qsmut}.ys").write_text(ys)
    r = subprocess.run([YOSYS, "-q", "-s", str(work / f"top_q{qsplit}_m{qsmut}.ys")], capture_output=True, text=True)
    (work / f"yosys_q{qsplit}.log").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        raise SystemExit(f"yosys failed, see {work}/yosys_q{qsplit}.log")
    return json.loads(js.read_text())


def port_kinds():
    """(inst, port, 'out'|'in') -> 'reg' | 'logic' from the measured classification (mixed -> logic)."""
    k = {}

    def put(key, kinds):
        kinds = set(kinds) - {"logic(ff-ctl)"}
        v = "reg" if kinds and kinds <= {"reg"} else "logic"
        if k.get(key) == "logic":
            return
        k[key] = v
    for r in json.loads((SPLIT / "inputs/sm_conn_r18g.json").read_text())["rows"]:
        for kk in r["kinds"]:
            a, b = kk.split("|")
            if r["src_port"] and not r["src"].startswith("PORT") and r["src"] not in ("const", "undriven", "top_reg"):
                put((r["src"], r["src_port"], "out"), a.split(","))
            if r["dst_port"] not in ("clk", "rst_n"):
                put((r["dst"], r["dst_port"], "in"), b.split(","))
    with open(SPLIT / "sm_internal_census.tsv") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["dst_inst"].startswith("PORT:") and r["src_inst"] == "u_front" and r["via_top_glue"] == "0":
                put(("u_front", r["src_port"], "out"), [r["launch"]])
    # u_front.schedule_fault is `output reg schedule_fault` (ot_hbm_sm_attn_front_static.sv); the census 'logic' row is
    # the top OR with the int8 fault (via_top_glue 1), which this check sees as top glue itself
    k[("u_front", "schedule_fault", "out")] = "reg"
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qsplit", type=int, required=True)
    ap.add_argument("--int8", type=int, default=1)
    ap.add_argument("--int8w", type=int, default=1)
    ap.add_argument("--qsmut", type=int, default=0, help="QSMUT bench mutant (negative control of this check)")
    ap.add_argument("--work", default="/tmp/qsplit_check")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    J = elaborate(a.qsplit, a.int8, a.int8w, work, a.qsmut)
    M = J["modules"][TOP]
    split = json.loads((SPLIT / "sm_split.json").read_text())
    childq = {c["inst"]: c["quarter"] for c in split["children"]}
    pk = port_kinds()
    in_q = "c" if a.qsplit else "d"

    def child_inst(name):
        return name.lstrip("\\")
    drv = {}                       # bit -> ('child', inst, port) | ('ff', name) | ('port', name) | ('comb', cellname)
    sinks = []                     # (bit, ('child', inst, port) | ('ff', name) | ('port', name))
    comb_in = {}                   # comb cell -> input bits
    unknown = collections.Counter()
    for pn, p in M["ports"].items():
        for b in p["bits"]:
            if isinstance(b, str) or pn in SKIP_PORTS:
                continue
            if p["direction"] == "input":
                drv[b] = ("port", pn)
            else:
                sinks.append((b, ("port", pn)))
    for cn, c in M["cells"].items():
        t = c["type"]
        name = child_inst(cn)
        dirs = c.get("port_directions", {})
        if not t.startswith("$"):
            if name not in childq and "u_int8" not in name and name != "u_front":
                unknown[t] += 1
            for pn, bits in c["connections"].items():
                if pn in ("clk", "rst_n", "rst_a"):
                    continue
                for b in bits:
                    if isinstance(b, str):
                        continue
                    if dirs.get(pn) == "output":
                        drv[b] = ("child", name, pn)
                    else:
                        sinks.append((b, ("child", name, pn)))
        elif "dff" in t.lower() or "dlatch" in t.lower():
            for b in c["connections"]["Q"]:
                drv[b] = ("ff", name)
            for b in c["connections"]["D"]:
                if not isinstance(b, str):
                    sinks.append((b, ("ff", name)))
        else:
            ins = [b for pn, bits in c["connections"].items() if dirs.get(pn) == "input" for b in bits if not isinstance(b, str)]
            for pn, bits in c["connections"].items():
                if dirs.get(pn) == "output":
                    for b in bits:
                        drv[b] = ("comb", name)
            comb_in[name] = ins

    def quarter(n):
        if n[0] == "child":
            if n[1] in childq:
                return childq[n[1]]
            return "c"                                   # u_front, int8 tile
        if n[0] == "ff":
            return "b" if "u_qs_b_" in n[1] else "a" if "u_qs_a_" in n[1] else "d" if "u_qs_d_" in n[1] else "c"
        if n[0] == "port":
            return in_q if n[1] in IN_PORTS else "a"
        return "c"

    def lkind(n):
        if n[0] == "child":
            key = (n[1], n[2], "out")
            if n[1].startswith("g_int8") and key not in pk:
                key = ("g_int8.g_hard.u_int8", n[2], "out")
            return pk.get(key, "logic")
        return "reg"                                      # top flop, or a die-lane landing register (input port)

    def ckind(n):
        if n[0] == "child":
            key = (n[1], n[2], "in")
            if n[1].startswith("g_int8") and key not in pk:
                key = ("g_int8.g_hard.u_int8", n[2], "in")
            return pk.get(key, "logic")
        return "reg"                                      # top flop D, or the die-lane landing register (output port)

    memo = {}

    def sources(b):
        """set of (source node, via_glue) for one bit"""
        if b in memo:
            return memo[b]
        memo[b] = set()
        d = drv.get(b)
        if d is None:
            r = {(("undriven",), False)}
        elif d[0] == "comb":
            r = set()
            for ib in comb_in[d[1]]:
                if isinstance(ib, str):
                    continue
                for s, _g in sources(ib):
                    r.add((s, True))
        else:
            r = {(d, False)}
        memo[b] = r
        return r

    def lab(n):
        return n[1] + ("." + n[2] if n[0] == "child" else "") if len(n) > 1 else n[0]
    rows = collections.Counter()
    for b, snk in sinks:
        for src, glue in sources(b):
            if src[0] == "undriven":
                continue
            sq, dq = quarter(src), quarter(snk)
            hops = [sq] + (["c"] if glue else []) + [dq]
            bad = []
            for i in range(len(hops) - 1):
                x, y = hops[i], hops[i + 1]
                if x == y:
                    continue
                if abs(ORDER.index(x) - ORDER.index(y)) > 1:
                    bad.append("non-adjacent")
                launch = lkind(src) if (i == 0) else "logic"           # leaving top glue = gate-launched
                capture = ckind(snk) if (i == len(hops) - 2) else "logic"
                if launch != "reg":
                    bad.append("launch=logic")
                if capture != "reg":
                    bad.append("capture=logic")
            cross = sq != dq or (glue and "c" not in (sq, dq))
            rows[(lab(src), sq, lab(snk), dq, glue, cross, ",".join(sorted(set(bad))) or "ok")] += 1
    # aggregate child-name buses (strip bit-level ff names to their instance prefix)

    def agg(n):
        if "u_qs_" in n:
            return "top_reg(" + "u_qs_" + n.split("u_qs_")[1].split(".")[0] + ")"
        if ".g_b[" in n:
            return n.split(".g_b[")[0]
        if n.startswith("$") or "$procdff" in n or "$auto" in n:
            return "top_reg"
        return n
    tab = collections.Counter()
    for (s, sq, d, dq, glue, cross, bad), n in rows.items():
        tab[(agg(s), sq, agg(d), dq, glue, cross, bad)] += n
    out = []
    for (s, sq, d, dq, glue, cross, bad), n in sorted(tab.items(), key=lambda kv: (kv[0][6] == "ok", kv[0])):
        if sq != dq or bad != "ok":
            out.append(dict(src=s, src_q=sq, dst=d, dst_q=dq, via_top_glue=glue, bits=n, verdict=bad))
    bad_bits = sum(r["bits"] for r in out if r["verdict"] != "ok")
    cross_bits = collections.Counter()
    for r in out:
        if r["src_q"] != r["dst_q"]:
            cross_bits["-".join(sorted((r["src_q"], r["dst_q"])))] += r["bits"]
    res = dict(schema="opentallas.hbm.sm_qsplit_check.v1", qsplit=a.qsplit, qsmut=a.qsmut, int8=a.int8, int8w=a.int8w,
               inputs_land=in_q, unknown_children=dict(unknown), crossing_bits=dict(cross_bits),
               unregistered_or_nonadjacent_bits=bad_bits, rows=out,
               verdict="PASS" if bad_bits == 0 and not unknown else "FAIL",
               method=__doc__.strip().splitlines()[0])
    Path(a.out).write_text(json.dumps(res, indent=1))
    for r in out:
        if r["verdict"] != "ok":
            print("BAD", r)
    print(f"QSPLIT_CHECK {res['verdict']} qsplit={a.qsplit} qsmut={a.qsmut} crossing_bits={dict(cross_bits)} bad_bits={bad_bits}")
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
