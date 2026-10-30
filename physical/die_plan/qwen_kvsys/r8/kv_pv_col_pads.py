#!/usr/bin/env python3
"""DIE-KV-14d 10-28: KV PV column equalisation pads (pv_trunk_gen invariant) as an R8 extra table.

    kv_pv_col_pads.py BIND_DIR R8_LANDING.json OUT.json

Why: on the step-5 bind (die-kv-13 bind5) the PV column command depths are not uniform against the as-built ones
(landed - as-built = -10 .. +8 per column), and the column flag returns (y_valid / fault -> ctl col_valid / col_fault)
land at totals cmd + flag = 9 .. 141.  ot_qwen_tp8_pv_wide_ctl_tbf checks all 32 column flags in ONE cycle (cv_r
all-equal, cv_r[0] == out_slot at COL_CHK = COL_LAT + TRUNK_D + FLAG_D), and every column bank takes its V words on the
command it receives, so the two static parameters TRUNK_D / FLAG_D describe the die only if
  (1) every column command lands at as-built + C (one shift C for all 64 columns of both pairs), and
  (2) every column's landed cmd + flag total is the same (per pair side, the as-built reference column 0 offset kept).
These are exactly the MAIN regen_constants.kv_pv_trunk law conditions (cmd_delta_uniform, flag_uniform, S == N); the
law then gives TRUNK_D = TRUNK_D_asb + C and FLAG_D = max_s(cmd + flag) - (c0 as-built cmd + flag - FLAG_D - TRUNK_D)_asb
- TRUNK_D.  Pads only ADD stages, so C = max_s (landed - as-built) of the column commands and the flag target is the
largest total after the command pads (minimum pads that satisfy the law).

Members padded (sink-partition entry, r8 member schema; bind.py asbuilt.land_r8_extra is authoritative per id):
  pvw_<k>__u_ctl.cmd -> pvw_<k>__u_s<c>_j.join_go and -> pvw_<k>__u_s<c>_b<b>.bc   (pad = as-built + C - landed)
  pvw_<k>__u_s<c>_j.y_valid / .fault -> pvw_<k>__u_ctl.col_valid / col_fault      (pad = flag target - landed)
The bank commands (bc) take the SAME pad as their column's join_go: bank and join of one column receive one command word,
so they keep their as-built relative timing (fail closed if a bank's bc and its join_go land differently).
DIE-KV-19 (b2): the lc bank tile (ot_qwen_tp8_pv_slice_lc_t) has copy pins bcx = bc[18] x3, bc[17] x3 from the same
command word -> its bcx member is one more column command member and takes the same pad (absent on non-lc binds).
The RTL parameters follow from the padded bind through the param hook kv_pv_col_regen.py (same law, fail closed).
Not covered (reported, not padded): V words vport -> bank pv2 and ASTK response -> bank pe2 (see estimate.md)."""
import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# DIE-KV-37-FACE 10-29: load regen_constants by FILE, never by prepending a tools dir to sys.path.  Loaded as the bind
# param_regen hook (kv_pv_col_regen.py), the old sys.path.insert(0, <resolved tree>/tools/die_plan) made every LATER
# lazy import in the running bind (clock_landings -> `import landing_collector`) resolve from that other tree: on a
# symlinked bindroot it picked the pre-DIE-KV-32 landing_collector (no face rule) and silently dropped 49 raw
# pre-START reset copies on 25 KV types (monitors on the rst_o face flop Q).
import importlib.util as _ilu  # noqa: E402
_spec = _ilu.spec_from_file_location("kv_pv_col_pads_regen_constants",
                                     Path(__file__).resolve().parents[4] / "tools/die_plan/regen_constants.py")
RC = _ilu.module_from_spec(_spec)
sys.modules[_spec.name] = RC
_spec.loader.exec_module(RC)

SIDES = (("S", "pvw_0"), ("N", "pvw_1"))
CTL_MODULE = r"ot_qwen_tp8_pv_wide_ctl_tbf\w*"


def _col(path):
    return int(re.search(r"_s(\d+)_[jb]", path).group(1))


def plan(B):
    """per-column depths on the bind -> shift C, per-side flag totals, per-member target landed depth.
    B: regen_constants.Bound (generator) or LegView (bind param hook); both give members() and asbuilt_param()."""
    TD = B.asbuilt_param(r"pvw_\d__u_ctl$", "TRUNK_D", module=CTL_MODULE)
    FD = B.asbuilt_param(r"pvw_\d__u_ctl$", "FLAG_D", module=CTL_MODULE)
    if TD is None or FD is None:
        raise SystemExit("as-built TRUNK_D / FLAG_D of the PV ctl not found in the bind")
    TD, FD = int(TD), int(FD)
    sides = {}
    for side, pvw in SIDES:
        cmd = B.members(source=rf"^{pvw}__u_ctl\.cmd$", sink=rf"^{pvw}__u_s\d+_(j|b\d+)$", port=r"^(join_go|bc|bcx)$")
        flg = B.members(source=rf"^{pvw}__u_s\d+_j\.(y_valid|fault)$", sink=rf"^{pvw}__u_ctl$", port=r"^col_(valid|fault)$")
        cols = defaultdict(lambda: dict(cmd=set(), flag=set(), members=[]))
        for m in cmd:
            cols[_col(m["sink"])]["cmd"].add((m["asb"], m["landed"]))
            cols[_col(m["sink"])]["members"].append(("cmd", m))
        for m in flg:
            cols[_col(m["source"])]["flag"].add((m["asb"], m["landed"]))
            cols[_col(m["source"])]["members"].append(("flag", m))
        if len(cols) != 32:
            raise SystemExit(f"{pvw}: {len(cols)} PV columns (32 expected)")
        for c, v in sorted(cols.items()):
            if len(v["cmd"]) != 1 or len(v["flag"]) != 1:
                raise SystemExit(f"{pvw} column {c}: join/bank commands {sorted(v['cmd'])} flags {sorted(v['flag'])} "
                                 "(one depth per column required before padding)")
            (ca, cl), = v["cmd"]
            (fa, fl), = v["flag"]
            v.update(cmd_asb=ca, cmd_landed=cl, flag_asb=fa, flag_landed=fl, dcmd=cl - ca)
        c0 = cols[min(cols)]
        sides[side] = dict(pvw=pvw, cols=cols, k0=c0["cmd_asb"] + c0["flag_asb"] - FD - TD)
    C = max(v["dcmd"] for s in sides.values() for v in s["cols"].values())
    # flag total each side must reach: every column after its command pad, then one FLAG_D for both sides
    need = {k: max(v["cmd_asb"] + C + v["flag_landed"] for v in s["cols"].values()) for k, s in sides.items()}
    trunk = TD + C
    flag = max(need[k] - sides[k]["k0"] for k in sides) - trunk
    rows, members = {}, []
    for side, s in sides.items():
        tot = trunk + flag + s["k0"]
        for c, v in sorted(s["cols"].items()):
            cmd_t = v["cmd_asb"] + C
            flag_t = tot - cmd_t
            assert cmd_t >= v["cmd_landed"] and flag_t >= v["flag_landed"], (side, c)
            rows[f"{s['pvw']}.s{c}"] = dict(cmd_asb=v["cmd_asb"], cmd_landed=v["cmd_landed"], cmd_pad=cmd_t - v["cmd_landed"],
                                           flag_asb=v["flag_asb"], flag_landed=v["flag_landed"],
                                           flag_pad=flag_t - v["flag_landed"], total=cmd_t + flag_t)
            for kind, m in v["members"]:
                members.append((m, cmd_t if kind == "cmd" else flag_t))
    return dict(TRUNK_D_asb=TD, FLAG_D_asb=FD, C=C, TRUNK_D=trunk, FLAG_D=flag,
                k0={k: s["k0"] for k, s in sides.items()}, columns=rows), members


class LegView:
    """bind.py param_regen ctx -> the two Bound methods plan() uses (per crossing BIT; landed includes the R8 pads)"""

    def __init__(self, ctx):
        F = ctx.F
        self.ms = []
        for (ci, pn, i), d in ctx.sinks.items():
            if d[0] != "x":
                continue
            landed = ctx.bitcyc[(d[1], d[6], d[2], d[3], d[4])] + (d[7] if len(d) > 7 else 0)
            self.ms.append(dict(sink=F.cells[ci].path, port=pn, source=f"{F.cells[d[2]].path}.{d[3]}", asb=d[5],
                                bound=ctx.bitcyc[(d[1], d[6], d[2], d[3], d[4])], landed=landed, bits=1))
        self.ctl = {c.path: c for c in F.cells if re.fullmatch(CTL_MODULE, c.module) and re.search(r"pvw_\d__u_ctl$", c.path)}
        self.defaults = {p: ctx.param_defaults.get((c.ytype, c.module), {}) for p, c in self.ctl.items()}

    def members(self, source=None, sink=None, port=None):
        rs, rk, rp = (re.compile(x) if x else None for x in (source, sink, port))
        return [m for m in self.ms if (not rs or rs.search(m["source"])) and (not rk or rk.search(m["sink"]))
                and (not rp or rp.search(m["port"]))]

    def asbuilt_param(self, inst_re, param, module=None):
        vals = {str(c.params.get(param, self.defaults[p].get(param))).strip('"') for p, c in self.ctl.items()}
        if len(self.ctl) != 2 or len(vals) != 1:
            raise ValueError(f"PV ctl {param}: {len(self.ctl)} ctl leaves, values {sorted(vals)} (2 equal expected)")
        return vals.pop()


def pads(bind_dir, r8):
    B = RC.Bound(bind_dir)
    law, members = plan(B)
    by_key = defaultdict(list)
    for x in r8["members"]:
        by_key[(x["sink"], x["sink_port"], x["source"])].append(x)
    out, flops = [], defaultdict(int)
    for m, target in members:
        cands = by_key.get((m["sink"], m["port"], m["source"]), [])
        if len(cands) != 1:
            raise SystemExit(f"{m['sink']}.{m['port']} <- {m['source']}: {len(cands)} R8 members (one expected)")
        x = cands[0]
        if x["landed"] != m["landed"] or x["bound"] != m["bound"] or x["asbuilt"] != m["asb"]:
            raise SystemExit(f"{x['id']}: R8 table (asb {x['asbuilt']} bound {x['bound']} landed {x['landed']}) is not the "
                             f"bind's (asb {m['asb']} bound {m['bound']} landed {m['landed']}): stale R8 table")
        add = target - x["landed"]
        if add:
            out.append(dict(x, pad=x["pad"] + add, landed=target, pv_col_pad=add))
            flops["cmd" if x["sink_port"] in ("join_go", "bc", "bcx") else "flag"] += add * _bits(x)
    cols = law["columns"].values()
    return dict(schema="opentallas.die_plan.r8_extra.v1", die="qwen_kvsys", kind="kv_pv_column_equalisation",
                source_bind=str(bind_dir),
                source_r8_sha256=hashlib.sha256(json.dumps(r8, sort_keys=True).encode()).hexdigest(),
                note=(f"DIE-KV-14d PV column equalisation: every column command lands at as-built + {law['C']}, every column "
                      f"cmd + flag total equal per side -> regen_constants kv_pv_trunk law TRUNK_D {law['TRUNK_D']} / FLAG_D "
                      f"{law['FLAG_D']} (as-built {law['TRUNK_D_asb']} / {law['FLAG_D_asb']}); RTL via kv_pv_col_regen.py"),
                law=law, members=out,
                summary=dict(TRUNK_D=law["TRUNK_D"], FLAG_D=law["FLAG_D"], C=law["C"], members=len(out),
                             cmd_pad_stages_per_column=sum(r["cmd_pad"] for r in cols),
                             flag_pad_stages_per_column=sum(r["flag_pad"] for r in cols),
                             max_cmd_pad=max(r["cmd_pad"] for r in cols), max_flag_pad=max(r["flag_pad"] for r in cols),
                             pad_flops_cmd=flops["cmd"], pad_flops_flag=flops["flag"],
                             pad_flops=flops["cmd"] + flops["flag"]))


def _bits(x):
    return sum(b - a + 1 for a, b in x["sink_bits"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bind_dir")
    ap.add_argument("r8", help="the land_r8 table the bind used (members carry pad / landed)")
    ap.add_argument("out")
    a = ap.parse_args(argv)
    t = pads(a.bind_dir, json.load(open(a.r8)))
    Path(a.out).write_text(json.dumps(t, indent=1) + "\n")
    print(json.dumps(t["summary"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
