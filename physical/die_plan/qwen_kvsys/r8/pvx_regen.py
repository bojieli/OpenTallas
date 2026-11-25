#!/usr/bin/env python3
"""FABLE-FIX-KV-PV compose 11-19: re-derive the KV PV owner pad tables (asbuilt.land_r8_extra) on a COMPOSED bind.

    pvx_regen.py TREE R8_MAIN OUT_COL OUT_V [--min-pad N] [--e-min-pad M] [--extra-first FILE ...]
                 [--td-asb 54 --fd-asb 58] [--check-col OLD_COL] [--check-v OLD_V]

Recovered 11-25 (KV-PV-ESTRIP, COORD FLOW-0930 K-03) from epyc8 fable-fix-kv-pv-sinkspread/w/pv/pvx_regen.py (sha256 prefix recorded in the
commit message); the original lived only in that lane's scratch.  Changes vs the recovered file: --asbuilt (the asbuilt json that names
the compose file; was hard-wired to plan_of_record/asbuilt_vN.json), the law code is loaded from the sibling r8/*.py of THIS file (not
from --tree), and EMPTY-GUARD-1125: exit 3 and write nothing when the R8 view holds no pvw bank members, or a table would have 0 members
(--allow-empty to accept an empty table).  kv_pv_v_pads.py regen delegates here.

Why this file exists: the tree generators r8/kv_pv_col_pads.py and r8/kv_pv_v_pads.py read the PV members by their AS-BUILT
leaf names (pvw_<k>__u_s<c>_b<b>.bc / bcx / pv2 / pe2).  Since the pair cores are composed (asbuilt.compose), a bind lists
those members under the composite leaf (native_composite_pv_<S>_<i>_pvg<g>_p<p>.s<k>__bc ...), and the tables of record
(pv_col_pads_7p.json, pv_v_pads_7p.json) were re-derived by a lane-private script (p7/kv7p_pvx.py, "composite names
mapped back; pinned R8 pads") that is on no host any more.  This is its replacement, built on the tree's own law code:

  1. R8_MAIN = the land_r8 table of the bind (land_r8_derive on the bind head's bus_groups.json + the KV pin): every
     crossing member with asbuilt / bound / pad.  Composite members are mapped back bit by bit through the asbuilt.compose
     file (cores[].ports[<port>].bits[i] = [{member, port, bit}]) to as-built members.
  2. kv_pv_col_pads.plan() (column law, --min-pad) runs on that view (+ the --extra-first tables, e.g. vport_w_pads) ->
     OUT_COL; kv_pv_v_pads.rule() (V-D-H = 0, pe2 one offset per source, --e-min-pad) runs on the view WITH OUT_COL
     applied -> OUT_V.  Members are written in the r8 member schema under their as-built ids, as the tables of record.
  --check-col / --check-v: compare the result with an existing table (id, asbuilt, bound, pad, landed); used to prove
  the method: R8 table + compose of the tree of record with --min-pad 0 --e-min-pad 0 must reproduce the tables of record.
The strict bind is the judge (R8_STALE fails closed per id; the param hook re-solves TRUNK_D / FLAG_D from the padded bind)."""
import argparse
import collections
import gzip
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

Q = "physical/die_plan/qwen_kvsys"


def _load(name, f):
    sp = importlib.util.spec_from_file_location(name, f)
    m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m
    sp.loader.exec_module(m)
    return m


def ranges(bits):
    bits = sorted(bits)
    out = []
    for b in bits:
        if out and b == out[-1][1] + 1:
            out[-1][1] = b
        else:
            out.append([b, b])
    return out


def member_id(m):
    rs = ",".join(f"{a}:{b}" if a != b else f"{a}" for a, b in m["sink_bits"])
    return f"{m['sink']}.{m['sink_port']}[{rs}]<-{m['source']}@{m['asbuilt']}"


class View:
    """as-built-named member view of an R8 table: composite sink members mapped back through the compose file"""

    def __init__(self, r8, compose, td_asb, fd_asb):
        self.td, self.fd = td_asb, fd_asb
        cmap = {}
        for c in compose["cores"]:
            for port, pv in (c.get("ports") or {}).items():
                if pv.get("dir") != "input":
                    continue
                for idx, bl in zip(pv["indices"], pv["bits"]):
                    cmap[(c["inst"], port, idx)] = bl
        self.rows = []          # r8-schema members under as-built names
        self.unmapped = 0
        acc = collections.OrderedDict()
        for m in r8["members"]:
            if not m["sink"].startswith("native_composite_pv_"):
                if re.match(r"^pvw_\d__u_", m["sink"]):
                    self.rows.append(dict(m))
                continue
            for a, b in m["sink_bits"]:
                for i in range(a, b + 1):
                    bl = cmap.get((m["sink"], m["sink_port"], i))
                    if not bl:
                        self.unmapped += 1
                        continue
                    for t in bl:
                        k = (t["member"], t["port"], m["source"], m["asbuilt"], m["bound"], m["pad"], m["lane"],
                             m.get("sink_part"), m.get("src_part"))
                        acc.setdefault(k, []).append(t["bit"])
        for (sink, port, source, asb, bound, pad, lane, sp_, srcp), bits in acc.items():
            for r in ranges(bits):                      # one member per contiguous bit range (the tables of record's form)
                x = dict(sink=sink, sink_part=sp_, src_part=srcp, sink_port=port, sink_bits=[r], source=source,
                         asbuilt=asb, bound=bound, pad=pad, landed=bound + pad, lane=lane)
                x["id"] = member_id(x)
                self.rows.append({k: x[k] for k in ("id", "sink", "sink_part", "src_part", "sink_port", "sink_bits", "source",
                                                    "asbuilt", "bound", "pad", "landed", "lane")})
        ids = collections.Counter(x["id"] for x in self.rows)
        dup = [i for i, n in ids.items() if n > 1]
        if dup:
            raise SystemExit(f"pvx: {len(dup)} duplicate as-built member ids after map-back, e.g. {dup[:3]}")
        self.by_id = {x["id"]: x for x in self.rows}

    def apply(self, table):
        """an owner table is authoritative per id (bind.py land_r8_extra)"""
        n = 0
        for m in table["members"]:
            x = self.by_id.get(m["id"])
            if x is None:
                continue
            if (x["asbuilt"], x["bound"]) != (m["asbuilt"], m["bound"]):
                raise SystemExit(f"pvx: extra member {m['id']} is stale against the R8 table (bound {m['bound']} vs {x['bound']})")
            x["pad"], x["landed"] = m["pad"], m["landed"]
            n += 1
        return n

    # ---- the two regen_constants.Bound methods the law code uses
    def members(self, source=None, sink=None, port=None):
        rs, rk, rp = (re.compile(x) if x else None for x in (source, sink, port))
        out = []
        for x in self.rows:
            if rk and not rk.search(x["sink"]):
                continue
            if rs and not rs.search(x["source"]):
                continue
            if rp and not rp.search(x["sink_port"]):
                continue
            out.append(dict(source=x["source"], sink=x["sink"], port=x["sink_port"], sink_part=x.get("sink_part"),
                            src_part=x.get("src_part"), asb=x["asbuilt"], bound=x["bound"], landed=x["landed"], lane=x.get("lane"),
                            bits=sum(b - a + 1 for a, b in x["sink_bits"]), _id=x["id"]))
        return out

    def asbuilt_param(self, inst_re, param, default=None, module=None):
        return dict(TRUNK_D=self.td, FLAG_D=self.fd).get(param, default)


def col_table(V, COL, r8, min_pad, src):
    law, members = COL.plan(V, min_pad)
    if min_pad:
        law["min_pad"] = int(min_pad)
    out, flops = [], collections.Counter()
    for m, target in members:
        x = V.by_id[m["_id"]]
        add = target - x["landed"]
        if add < 0:
            raise SystemExit(f"pvx: {x['id']} would need {add} stages")
        if add:
            out.append(dict(x, pad=x["pad"] + add, landed=target, pv_col_pad=add))
            flops["cmd" if x["sink_port"] in ("join_go", "bc", "bcx") else "flag"] += add * m["bits"]
    cols = law["columns"].values()
    return dict(schema="opentallas.die_plan.r8_extra.v1", die="qwen_kvsys", kind="kv_pv_column_equalisation", source_bind=src,
                source_r8_sha256=hashlib.sha256(json.dumps(r8, sort_keys=True).encode()).hexdigest(),
                note=(f"DIE-KV-14d PV column equalisation: every column command lands at as-built + {law['C']}, every column "
                      f"cmd + flag total equal per side -> regen_constants kv_pv_trunk law TRUNK_D {law['TRUNK_D']} / FLAG_D "
                      f"{law['FLAG_D']} (as-built {law['TRUNK_D_asb']} / {law['FLAG_D_asb']}); RTL via kv_pv_col_regen.py | "
                      f"FABLE-FIX-KV-PV 11-19: re-derived by pvx_regen.py (composite names mapped back through asbuilt.compose; "
                      f"pinned R8 pads; --min-pad {int(min_pad)})"),
                law=law, members=out,
                summary=dict(TRUNK_D=law["TRUNK_D"], FLAG_D=law["FLAG_D"], C=law["C"], members=len(out),
                             cmd_pad_stages_per_column=sum(r["cmd_pad"] for r in cols),
                             flag_pad_stages_per_column=sum(r["flag_pad"] for r in cols),
                             max_cmd_pad=max(r["cmd_pad"] for r in cols), min_cmd_pad=min(r["cmd_pad"] for r in cols),
                             max_flag_pad=max(r["flag_pad"] for r in cols),
                             pad_flops_cmd=flops["cmd"], pad_flops_flag=flops["flag"], pad_flops=flops["cmd"] + flops["flag"]))


def v_table(V, VP, r8, e_min_pad, src, residual=None):
    rows = VP.rule(V, e_min_pad)
    out, flops = [], collections.Counter()
    emin = None
    residual = residual or {}
    for m in rows:
        x = V.by_id[m["_id"]]
        m["target"] += residual.get(m["_id"], 0)
        add = m["target"] - x["landed"]
        if add < 0:
            raise SystemExit(f"pvx: {x['id']} needs {add} stages (V after its command)")
        if m["kind"] == "E":
            emin = m["target"] - x["bound"] if emin is None else min(emin, m["target"] - x["bound"])
        if add:
            out.append(dict(x, pad=x["pad"] + add, landed=m["target"], pv_v_pad=add))
            flops[m["kind"]] += add * m["bits"]
    return dict(schema="opentallas.die_plan.r8_extra.v1", die="qwen_kvsys", kind="kv_pv_v_landing", source_bind=src,
                source_r8_sha256=hashlib.sha256(json.dumps(r8, sort_keys=True).encode()).hexdigest(),
                note=("DIE-KV-16 PV V-word landing: every bank V-D-H = 0 (V vs its command vs its vport header, as-built "
                      "relative timing); astk pe2 one offset per source.  Law code r8/kv_pv_v_pads.py rule() | FABLE-FIX-KV-PV 11-19: "
                      f"re-derived by pvx_regen.py on the col-padded commands (composite names mapped back; --e-min-pad {int(e_min_pad)}"
                      + (f"; {sum(1 for v_ in residual.values() if v_)} V members keep the V-D-H residual of the table of record "
                         f"{sorted(set(v_ for v_ in residual.values() if v_))}" if any(residual.values()) else "") + ")"),
                members=out,
                summary=dict(members=len(out), max_pad=max((x["pv_v_pad"] for x in out), default=0),
                             min_pe2_pad=emin, rule_members=len(rows),
                             pad_flops_per_member=dict(flops), pad_flops_per_member_total=sum(flops.values())))


def compare(new, old_f, key):
    old = json.load(open(old_f))
    a = {m["id"]: (m["asbuilt"], m["bound"], m["pad"], m["landed"]) for m in new["members"]}
    b = {m["id"]: (m["asbuilt"], m["bound"], m["pad"], m["landed"]) for m in old["members"]}
    diff = [k for k in set(a) | set(b) if a.get(k) != b.get(k)]
    return dict(table=key, new=len(a), old=len(b), equal=not diff, different=len(diff),
                only_new=len(set(a) - set(b)), only_old=len(set(b) - set(a)),
                examples=[(k, a.get(k), b.get(k)) for k in sorted(diff)[:6]])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tree"); ap.add_argument("r8"); ap.add_argument("out_col"); ap.add_argument("out_v")
    ap.add_argument("--min-pad", type=int, default=0); ap.add_argument("--e-min-pad", type=int, default=0)
    ap.add_argument("--extra-first", action="append", default=[], help="owner tables applied before the law (asbuilt order), e.g. vport_w_pads")
    ap.add_argument("--asbuilt", default=f"{Q}/plan_of_record/asbuilt_vN.json", help="asbuilt json (relative to TREE) holding the compose path")
    ap.add_argument("--allow-empty", action="store_true", help="accept a table with 0 members (default: exit 3, EMPTY-GUARD-1125)")
    ap.add_argument("--td-asb", type=int, default=54); ap.add_argument("--fd-asb", type=int, default=58)
    ap.add_argument("--check-col"); ap.add_argument("--check-v")
    ap.add_argument("--record", nargs=3, metavar=("OLD_R8", "OLD_COL", "OLD_V"),
                    help="the tables of record and the land_r8 table they stand on: every V member keeps the V-D-H residual it has "
                         "in the table of record (the 7p V table carries -5 on 488 members of vports _1 / _2 that the tree's rule() "
                         "does not produce; its generator p7/kv7p_pvx.py is lost, so the residual is carried, not re-derived)")
    ap.add_argument("--src", default="", help="text for source_bind")
    a = ap.parse_args(argv)
    tree = Path(a.tree).resolve()
    ab = json.loads((tree / a.asbuilt).read_text())
    cf = tree / ab["compose"]
    compose = json.load(gzip.open(cf) if str(cf).endswith(".gz") else open(cf))
    r8 = json.load(open(a.r8))
    here = Path(__file__).resolve().parent
    COL = _load("ffkpv_kv_pv_col_pads", here / "kv_pv_col_pads.py")
    VP = _load("ffkpv_kv_pv_v_pads", here / "kv_pv_v_pads.py")
    V = View(r8, compose, a.td_asb, a.fd_asb)
    banks0 = {x["sink"] for x in V.rows if re.match(r"^pvw_\d__u_s\d+_b\d+$", x["sink"])}
    if not banks0 and not a.allow_empty:
        print(f"PVX_REGEN FAIL EMPTY: no pvw_<c>__u_s<k>_b<b> bank members in the R8 view ({len(V.rows)} rows, {V.unmapped} unmapped composite bits): "
              "wrong R8 table / compose file for this bind; nothing written")
        return 3
    rep = dict(view_members=len(V.rows), unmapped_composite_bits=V.unmapped, extra_first={})
    for f in a.extra_first:
        rep["extra_first"][f] = V.apply(json.load(open(f)))
    col = col_table(V, COL, r8, a.min_pad, a.src or str(a.r8))
    rep["col"] = col["summary"]
    V.apply(col)
    residual = {}
    if a.record:
        o_r8, o_col, o_v = (json.load(open(f)) for f in a.record)
        VO = View(o_r8, compose, a.td_asb, a.fd_asb)
        for f in a.extra_first:
            VO.apply(json.load(open(f)))
        if not compare(col_table(VO, COL, o_r8, 0, "record"), a.record[1], "col")["equal"]:
            raise SystemExit("pvx: the column table of record is not reproduced on its own R8 table: no basis for the V residual")
        VO.apply(o_col)
        rec = {m["id"]: m["landed"] for m in o_v["members"]}
        for r_ in VP.rule(VO, 0):
            residual[r_["_id"]] = rec.get(r_["_id"], VO.by_id[r_["_id"]]["landed"]) - r_["target"]
        rep["record_residual_hist"] = dict(collections.Counter(str(v_) for v_ in residual.values()))
        rep["record_residual_kinds"] = dict(collections.Counter(re.search(r"\.(pv2|pe2)\[", k).group(1) for k, v_ in residual.items() if v_))
    vt = v_table(V, VP, r8, a.e_min_pad, a.src or str(a.r8), residual)
    rep["v"] = vt["summary"]
    V.apply(vt)
    chk = VP.rule(V, 0)
    rep["v_d_h_bad_after"] = sum(1 for r_ in chk if r_["vdh"] != residual.get(r_["_id"], 0))
    rep["banks"] = len({r_["sink"] for r_ in chk})
    if a.check_col:
        rep["check_col"] = compare(col, a.check_col, "col")
    if a.check_v:
        rep["check_v"] = compare(vt, a.check_v, "v")
    if (not col["members"] or not vt["members"]) and not a.allow_empty:
        print(f"PVX_REGEN FAIL EMPTY: col members {len(col['members'])}, v members {len(vt['members'])}; nothing written (EMPTY-GUARD-1125)")
        return 3
    Path(a.out_col).write_text(json.dumps(col, indent=1) + "\n")
    Path(a.out_v).write_text(json.dumps(vt, indent=1) + "\n")
    print("PVX_REGEN " + json.dumps(rep))
    bad = rep["v_d_h_bad_after"] or rep["banks"] != 512 or any(not (rep.get(k) or {"equal": True})["equal"] for k in ("check_col", "check_v"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
