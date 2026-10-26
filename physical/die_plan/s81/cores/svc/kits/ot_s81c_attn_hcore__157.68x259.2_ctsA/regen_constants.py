#!/usr/bin/env python3
"""CAL-AUTO 10-23: ONE automated path from a bound die top to every schedule constant the compilers and RTL need.

    regen_constants.py --die {qwen_compute,qwen_kvsys,hbm,s81} --bound BIND_DIR [--out-json F] [--out-sv F]
                       [--peer BIND_DIR] [--expect EXPECT.json] [--src-root REPO] [--write-fixture DIR]

Why: every plan or bind change shifts lane latencies (QC: 1601 of 1858 crossing buses changed vs as-built) and each
token agent re-derived calendars and schedule constants by hand (tp8 MU calendar at LS 389, xdie seam / TXDP, KV
RESPONSE_LAT / QK_ISSUE_AGE / KVN_A0, HBM leaf-split shifts, treq vs cmd).  This tool reads ONLY the bind outputs
(BIND_DIR = tools/die_plan/bind.py --out: bus_groups.json[.gz] landing members with as-built / bound / LANDED stages,
bind_latency.json[.gz] per crossing bus, param_regen.json = the RTL parameters the bind's die hook applied) and
re-derives every constant with the generator's own law, per die, into one JSON (schema opentallas.die_plan.
regen_constants.v1) + one SV package (<die>_sched_pkg).

Depth convention: D = LANDED stages of a crossing member (bound lane stages + R8 / PV landing pads), the depth the
netlist actually has; a pin not on a crossing has depth 0.  Delta = D - as-built full-path stages of the same member.

Every constant carries: value, kind (rtl = leaf parameter the bind must carry, boot = boot image / cal word,
compiler = programme / calendar input), formula, inputs (the depths it used), and, for kind rtl, a cross-check
against param_regen.json: the bind applied value must EQUAL the regenerated one, else status MISMATCH (the RTL
and the compilers would disagree -> the bind gate fails).  --expect pins hand values of record (tests).

Laws (one place; sources cited per rule):
  QC  coll: tools/qwen_split/lane_groups.collective_calendar (BINDER2 coll_regen.py, TOKh tp8 LS 389) on
            TX_j/RX_j/RS_j landed depths; MU window calendar LS = the same LS.
      treq: per hop landed(treq_i) - landed(cmd_i) (BINDER3 treq_vs_cmd.py).
      seam: d2d_link_calendar STAGE_NAMES CS_* = as-built seam stage + Delta of the record_bundles bundle members
            (one Delta per bundle, else MISMATCH); TXDP C = producer_txd_c + PINREG_EXT.
  KV  kv_param_regen_check.py (KV-P5) laws on LANDED depths: RESPONSE_LAT = 8 + D(krq) + D(krs) (one value on every
      frame), QK_ISSUE_AGE = max(34, RL + 11), RRL = RL + 7, row_latency_for_calendar = RL + 2, AP_OFS_s = asb +
      Delta(ap_s) + Delta(f_aqm), FR_OFS asb (intra hub_C), TRUNK_D/FLAG_D pv_trunk_gen, KVN_A0 = asb +
      Delta(kvn_word_valid -> seq core) - Delta(att_rx_v -> kvs_attn) (KV-P6 18:09), vport RT/DQ/cfg_fia, d2d ages,
      hroot down/ret; seam KS_*/SK_* = landed d2d_kv <-> kvs_attn depths (KV-P6-BOOT KST); TXDP K.
  HBM leaf-split shifts (tools/hbm_static/leaf_split_latency.py, bound twins detected in the bound RTL) + bank-client
      round trips (tools/hbm_die_v16/d4g_bank_latency.py RULES: param = ref + RT - ref_rt, RT_b = BANK + PIN +
      D(rq->bank) + D(bank->rr)).
  S81 frame / BF calendar inputs: per lane-class landed delta (x_*_out -> column p1..p6, BF return, LP coll lanes) =
      the calendar's LANE_LANDING_CYCLES hooks (TOKi-PRICE price_s81_plan_lat.py).
A die without a bound top yet reports status PENDING per rule, never a guessed value.
"""
import argparse
import gzip
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
SCHEMA = "opentallas.die_plan.regen_constants.v1"


# ------------------------------------------------------------------------------------------------------------ inputs
def _load(p):
    p = Path(p)
    for q in (p, Path(str(p) + ".gz")):
        if q.exists():
            op = gzip.open if q.suffix == ".gz" else open
            with op(q, "rt") as f:
                return json.load(f)
    return None


class Bound:
    """read-only view of a bind output dir.  Records every member it hands out (for --write-fixture)."""

    def __init__(self, d):
        self.dir = Path(d)
        bg = _load(self.dir / "bus_groups.json")
        if bg is None:
            raise SystemExit(f"{d}: no bus_groups.json[.gz] (not a bind output dir)")
        self.bg_meta = {k: v for k, v in bg.items() if k not in ("landing", "replica")}
        self.landing = bg["landing"]
        bl = _load(self.dir / "bind_latency.json") or {"buses": []}
        self.buses = bl["buses"]
        self.param_regen = _load(self.dir / "param_regen.json") or {}
        self.used_m, self.used_b = set(), set()
        # members flattened once
        self.M = []
        for gi, g in enumerate(self.landing):
            for mi, m in enumerate(g["members"]):
                self.M.append((gi, mi, g, m))

    # -- members
    def members(self, source=None, sink=None, port=None):
        """landing members: dict(source, sink, port, sink_part, src_part, asb, bound, landed, lane, bits)"""
        rs = re.compile(source) if source else None
        rk = re.compile(sink) if sink else None
        rp = re.compile(port) if port else None
        out = []
        for gi, mi, g, m in self.M:
            if rk and not rk.search(g["sink"]):
                continue
            if rs and not rs.search(m["source"]):
                continue
            if rp and not rp.search(m["sink_port"]):
                continue
            self.used_m.add((gi, mi))
            out.append(dict(source=m["source"], sink=g["sink"], port=m["sink_port"], sink_part=g.get("sink_part"),
                            src_part=g.get("src_part"), asb=m["asbuilt_stages"], bound=m["bound_stages"],
                            landed=m.get("landed_stages", m["bound_stages"]), lane=m.get("lane"),
                            bits=sum(b - a + 1 for a, b in m.get("sink_bits", [[0, 0]]))))
        return out

    def one(self, what, source=None, sink=None, port=None, key="landed", default=None):
        ms = self.members(source, sink, port)
        if not ms:
            if default is not None:
                return default, []
            raise RuleError(f"{what}: no crossing member source~{source} sink~{sink} port~{port}")
        v = sorted({m[key] for m in ms})
        if len(v) != 1:
            raise RuleError(f"{what}: members land at {v} {key} stages (one depth per leg required)")
        return v[0], ms

    def bus(self, leaf, src=None, dst=None):
        out = []
        for i, b in enumerate(self.buses):
            if re.search(leaf, " ".join(b["leaves"])) and (src is None or re.match(src, b["src"])) and \
                    (dst is None or re.match(dst, b["dst"])):
                self.used_b.add(i)
                out.append(b)
        return out

    # -- the hook-applied RTL parameters
    def applied(self):
        """{(inst, param): (asbuilt str, bound value)} from param_regen.json changed[]"""
        return {(c["inst"], c["param"]): (c["asbuilt"], c["bound"]) for c in self.param_regen.get("changed", [])}

    def asbuilt_param(self, inst_re, param, default=None, module=None):
        """as-built value: param_regen.json changed[].asbuilt; a bind WITHOUT a param_regen hook still carries the
        as-built values in its RTL -> read them from BIND_DIR/rtl (module regex)."""
        vals = {a for (i, p), (a, b) in self.applied().items() if p == param and re.search(inst_re, i)}
        if not vals and module and not self.param_regen.get("changed") and (self.dir / "rtl").is_dir():
            vals = {v["params"][param] for v in self.rtl_insts(module).values() if param in v["params"]}
        if len(vals) > 1:
            raise RuleError(f"as-built {param} differs across {inst_re}: {sorted(vals)}")
        return next(iter(vals)) if vals else default

    def rtl_insts(self, module_re):
        """{inst: {param: value}} for instances of modules matching module_re in BIND_DIR/rtl/*.sv"""
        out = {}
        pat = re.compile(r"\b(" + module_re + r")\s*#\s*\((.*?)\)\s*(\\?[\w\[\]\.$]+)\s*\(", re.S)
        for f in sorted((self.dir / "rtl").glob("*.sv")) + sorted((self.dir / "rtl").glob("*.v")):
            t = f.read_text(errors="replace")
            for m in pat.finditer(t):
                ps = dict(re.findall(r"\.(\w+)\s*\(([^()]*)\)", m.group(2)))
                out[m.group(3)] = dict(module=m.group(1), params=ps, file=f.name)
        return out

    def top_sha(self):
        h = hashlib.sha256()
        for f in sorted((self.dir / "rtl").glob("*")) if (self.dir / "rtl").is_dir() else []:
            if f.is_file():
                h.update(f.name.encode())
                h.update(f.read_bytes())
        return h.hexdigest()[:16] if (self.dir / "rtl").is_dir() else None

    def write_fixture(self, out):
        """the subset of the bind this run read (members + buses + param_regen) -> a small test fixture"""
        out = Path(out)
        out.mkdir(parents=True, exist_ok=True)
        groups = defaultdict(list)
        for gi, mi in sorted(self.used_m):
            groups[gi].append(self.landing[gi]["members"][mi])
        land = [dict({k: v for k, v in self.landing[gi].items() if k != "members"}, members=ms) for gi, ms in groups.items()]
        json.dump(dict(self.bg_meta, landing=land, replica=[], fixture_of=str(self.dir)),
                  gzip.open(out / "bus_groups.json.gz", "wt"), indent=0)
        json.dump(dict(buses=[self.buses[i] for i in sorted(self.used_b)], fixture_of=str(self.dir)),
                  gzip.open(out / "bind_latency.json.gz", "wt"), indent=0)
        if self.param_regen:
            json.dump(self.param_regen, open(out / "param_regen.json", "w"), indent=0)


class RuleError(Exception):
    pass


# ----------------------------------------------------------------------------------------------------- accumulator
class Out:
    def __init__(self, die, B):
        self.die, self.B = die, B
        self.c = {}           # name -> record
        self.notes = []

    def add(self, name, value, kind, formula, inputs=None, inst=None, param=None, group=None, note=None, status="OK"):
        r = dict(value=value, kind=kind, formula=formula, status=status)
        if inputs is not None:
            r["inputs"] = inputs
        if group:
            r["group"] = group
        if note:
            r["note"] = note
        if inst is not None:
            r["rtl"] = dict(inst=inst, param=param or name)
        self.c[name] = r
        return r

    def pending(self, name, kind, why, group=None):
        self.c[name] = dict(value=None, kind=kind, status="PENDING", formula=why, group=group)

    def error(self, name, kind, err, group=None):
        self.c[name] = dict(value=None, kind=kind, status="ERROR", formula=str(err), group=group)

    def rule(self, group, fn, *a):
        try:
            fn(self, *a)
        except RuleError as e:
            self.error(f"{group}.__rule__", "rule", e, group=group)

    def crosscheck(self):
        """kind rtl constants vs the bind-applied parameters (param_regen.json): must be equal."""
        ap = self.B.applied() if self.B else {}
        hook_vals = defaultdict(set)
        for (i, p), (a, b) in ap.items():
            hook_vals[p].add((i, str(b)))
        for n, r in self.c.items():
            rt = r.get("rtl")
            if not rt or r["status"] not in ("OK", "WARN"):
                continue
            exp = r.get("sv_literal", r["value"])
            got = [(i, b) for (i, b) in hook_vals.get(rt["param"], set()) if re.search(rt["inst"], i)]
            if not got:
                r["bind_applied"] = "not in param_regen.json (as-built value kept by the bind, or no hook)"
                continue
            bad = sorted({b for i, b in got if str(b) != str(exp)})
            r["bind_applied"] = sorted({b for _, b in got})
            if bad:
                r["status"] = "MISMATCH"
                r["mismatch"] = f"bind applied {bad} on {len([1 for i, b in got if str(b) != str(exp)])} inst, regen {exp}"

    def rtl_check(self, table):
        """the bound RTL itself (BIND_DIR/rtl) must carry the regenerated values: table = [(constant, module_re, param)];
        every instance of the module must hold the constant's value (as integers), else MISMATCH."""
        if not self.B or not (self.B.dir / "rtl").is_dir():
            return
        for name, mod, param in table:
            r = self.c.get(name)
            if not r or r["status"] not in ("OK", "WARN") or r["value"] is None:
                continue
            want = _int(r["sv_literal"]) if "sv_literal" in r else r["value"]   # TXDP / AP_OFS literals -> int
            if isinstance(want, list):
                continue
            insts = {i: v for i, v in self.B.rtl_insts(mod).items() if param in v["params"]}
            got = {}
            for i, v in insts.items():
                try:
                    got[f"{v['file']}:{i}"] = _int(v["params"][param])
                except ValueError:
                    got[f"{v['file']}:{i}"] = v["params"][param]
            bad = {k: v for k, v in got.items() if v != want}
            r["rtl_bound"] = dict(module=mod, param=param, instances=len(got), values=sorted({str(v) for v in got.values()}))
            if not got:
                r["rtl_bound"]["note"] = "no instance carries the parameter in BIND_DIR/rtl (RTL default / hard leaf)"
            elif bad:
                r["status"] = "MISMATCH"
                r["mismatch"] = (r.get("mismatch", "") + f" bound RTL {param}={sorted({str(v) for v in bad.values()})} on "
                                 f"{len(bad)}/{len(got)} {mod} instances, regen {want}").strip()

    def verdict(self):
        st = defaultdict(int)
        for r in self.c.values():
            st[r["status"]] += 1
        return dict(st)


def _int(s):
    s = str(s).strip().strip('"')
    m = re.fullmatch(r"(\d+)'s?([bhd])([0-9a-fA-F_xz]+)", s)
    if m:
        return int(m.group(3).replace("_", ""), dict(b=2, h=16, d=10)[m.group(2)])
    return int(s)


def _s16(x):
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x


# ======================================================================================================== QC (qwen_compute)
COLL = "io_collective.u_io"
SERDES = ["io_serdes", "io_serdes_1", "io_serdes_2"]
PEER = {0: 2, 1: 1, 2: 0}
QC_ANCHOR = dict(PS=339, RU=0,
                 # as-built compute seam (MU release pair, d2d_cal_image_production.sh default; record_bundles seam_stages)
                 seam=dict(CS_TXS=2, CS_RXV=2, CS_RXP=2, CS_X3S=3, SC_TX=2, SC_X3=2))
QC_SEAM_BUNDLES = {   # stage -> [(src leaf, src port, sink leaf, sink port)]  (record_bundles.BUNDLES compute side)
    "CS_TXS": [("d2d_rom", "native_tx_slot", "native59", "tx_slot"), ("d2d_rom", "native_tx_slot_kind", "native59", "tx_slot_kind"),
               ("d2d_rom", "native_tx_slot_beat", "native59", "tx_slot_beat")],
    "CS_RXV": [("d2d_rom", "native_rx_v", "native59", "native_rx_v"), ("d2d_rom", "native_rx_slot", "native59", "rx_slot"),
               ("d2d_rom", "native_rx_slot_kind", "native59", "rx_slot_kind"),
               ("d2d_rom", "native_rx_slot_beat", "native59", "rx_slot_beat")],
    "CS_RXP": [("d2d_rom", "rx_payload", "native59", "native_rx_payload")],
    "CS_X3S": [("d2d_rom", "kv_x3_slot", "native59", "kv_x3_slot")],
    "SC_TX": [("native59", "native_tx_v", "d2d_rom", "native_tx_v"), ("native59", "native_tx_payload", "d2d_rom", "native_tx_payload")],
    "SC_X3": [("native59", "x3", "d2d_rom", "x3"), ("native59", "x3_identity", "d2d_rom", "x3_identity"),
              ("native59", "x3_generation", "d2d_rom", "x3_generation")],
}
# d2d_link_calendar.py constants (producer law)
N59_TX, N59_X3 = 2, 2
PINREG_EXT = {"C": [2, 2, 0, 2], "K": [2, 2, 2, 2]}
KV_CODEC_LANDED = 2        # qkd_kvs_attn .LAND(1) (layer_compile.kv_codec_edges, HKV-DIE 10-19)


def _txdp_word(v):
    return sum(x << (8 * p) for p, x in enumerate(v))


def _lg(src_root):
    sys.path.insert(0, str(Path(src_root) / "tools" / "qwen_split"))
    import lane_groups as LG
    return LG


def qc_coll(o, src_root):
    B = o.B
    face = lambda j: f"{re.escape(COLL)}\\.g_face\\[{2 + j}\\]\\.u_face$"
    TX = [B.one(f"TX{j}", sink=f"^{SERDES[j]}$", port=r"^(tx_flit|tx_v)$")[0] for j in range(3)]
    RX = [B.one(f"RX{j}", sink=face(j), port=r"^(phy_rx|phy_rx_valid|phy_up)$")[0] for j in range(3)]
    RS = []
    for j in range(3):
        t = B.one(f"RS{j} core->face", sink=face(j), port=r"^(tx_data|tx_valid)$")[0]
        r = B.one(f"RS{j} face->core", sink=re.escape(COLL) + r"\.u_collective$", port=rf"^sr{j}_(rec|valid)$")[0]
        if t != r:
            raise RuleError(f"RS{j}: core->face {t} vs face->core {r} (the face calendar takes one R per port)")
        RS.append(t)
    ru = [B.one("RU0", sink=re.escape(COLL) + r"\.g_face\[0\]\.u_face$", port=r"^(tx_data|tx_valid)$", default=0)[0],
          B.one("RU1", sink=re.escape(COLL) + r"\.g_face\[1\]\.u_face$", port=r"^(tx_data|tx_valid)$", default=0)[0]]
    if set(ru) != {QC_ANCHOR["RU"]}:
        raise RuleError(f"UCIe relay depths {ru} != as-built RU {QC_ANCHOR['RU']} (LU has no lane knob)")
    LX = [TX[PEER[j]] + RX[j] for j in range(3)]
    LG = _lg(src_root)
    cal = LG.collective_calendar(LX, dict(RU=QC_ANCHOR["RU"], RS0=RS[0], RS1=RS[1], RS2=RS[2], PS=QC_ANCHOR["PS"]),
                                 root=Path(src_root))
    LS = cal["LS"]
    inp = dict(TX=TX, RX=RX, RS=RS, LX=LX, PS=cal["PS"], KC=cal["KC"], KW=cal["KW"])
    g = "coll"
    o.add("COLL_LS", LS, "rtl", cal["rule"], inp, inst=re.escape(COLL) + r"\.(u_collective|g_face\[[234]\]\.u_face)$",
          param="LS", group=g)
    o.c["COLL_LS"]["rtl"]["also"] = "face L"
    o.add("MU_CAL_LS", LS, "compiler", "tp8 MU window calendar period = COLL_LS (TOKh 14:17: regenerated at LS 389)",
          dict(COLL_LS=LS), group=g)
    for j in range(3):
        f = re.escape(COLL) + rf"\.g_face\[{2 + j}\]\.u_face$"
        o.add(f"COLL_F{2 + j}_PHY", cal["PS"] + LX[j], "rtl", "PS + LX_j", dict(PS=cal["PS"], LX=LX[j]), inst=f, param="PHY", group=g)
        o.add(f"COLL_F{2 + j}_L", LS, "rtl", "L = LS", None, inst=f, param="L", group=g)
        o.add(f"COLL_F{2 + j}_R", RS[j], "rtl", "R = RS_j (core<->face relay depth)", None, inst=f, param="R", group=g)
        o.add(f"COLL_F{2 + j}_PEER_R", RS[PEER[j]], "rtl", "PEER_R = RS_peer(j)", None, inst=f, param="PEER_R", group=g)
    o.add("COLL_BENCH_ARGS", f"--relays {QC_ANCHOR['RU']} {RS[0]} {RS[1]} {RS[2]} --lanes {TX[0]} {TX[1]} {TX[2]} "
          f"{RX[0]} {RX[1]} {RX[2]} --lx {LX[0]} {LX[1]} {LX[2]}", "compiler", "tp8/tp8_mu bench arguments", None, group=g)
    # slice <-> collective command / stream legs (compiler: per-layer coll issue / drain timing)
    legs = {}
    for name, src, sink, port in (("cmd", r"u_fdn\.cc_o$", re.escape(COLL) + r"\.u_collective$", r"^cmd_"),
                                  ("in", r"u_fdn\.ch_dn_o$", re.escape(COLL) + r"\.u_collective$", r"^in_"),
                                  ("out", re.escape(COLL) + r"\.u_collective\.out_", r"u_fdn$", r"^ch_dn_i$")):
        ms = B.members(src, sink, port)
        if ms:
            legs[name] = dict(landed=sorted({m["landed"] for m in ms}), asbuilt=sorted({m["asb"] for m in ms}),
                              delta=sorted({m["landed"] - m["asb"] for m in ms}))
    o.add("COLL_SLICE_LEGS", legs, "compiler", "landed depth of the slice<->collective cmd / in / out legs (per-bit as-built "
          "offsets kept by R8 when delta is one value)", group=g,
          status="OK" if all(len(v["delta"]) == 1 for v in legs.values()) else "WARN")


def qc_treq(o):
    B = o.B
    hops = defaultdict(lambda: defaultdict(set))
    for m in B.members(sink=r"u_fdn$|u_stm$", port=r"^(treq_i|cmd_i)$"):
        hops[(m["source"].rpartition(".")[0], m["sink"])][m["port"]].add(m["landed"])
    rows, offs = [], set()
    for (s, d), v in sorted(hops.items()):
        if "treq_i" not in v or "cmd_i" not in v:
            continue
        off = max(v["treq_i"]) - max(v["cmd_i"])
        offs.add(off)
        rows.append(dict(src=s, sink=d, treq=sorted(v["treq_i"]), cmd=sorted(v["cmd_i"]), offset=off))
    if not rows:
        o.pending("TREQ_CMD_OFFSET", "compiler", "no treq_i/cmd_i hop on this bind (pre QC-P5-TIE top)", group="treq")
        return
    o.add("TREQ_CMD_OFFSET", sorted(offs)[0] if len(offs) == 1 else sorted(offs), "compiler",
          "per slice hop landed(treq_i) - landed(cmd_i) at u_fdn (treq_vs_cmd.py); one value -> scalar", dict(hops=len(rows)),
          group="treq", status="OK" if len(offs) == 1 else "WARN", note=None if len(offs) == 1 else "per-hop table in TREQ_HOPS")
    o.add("TREQ_HOPS", rows, "compiler", "per hop table", group="treq")


def qc_xfill(o):
    """QC-TOK 10-24 (xt1 on bound_r8: FAULT heads, x leaf q_bad = an x element read before it was written): the x-slice
    arm / go (hr: u_fdn.hr_q -> u_tap.hr_q) and the x fill stream (u_fdn.sw_q -> u_stm.sw_i, then u_stm.xt_* -> u_tap)
    are different crossings, so the bound top changes their relative latency; the static schedule (xt1 bench lead =
    cycles from the hr x-prefill arm to the first fill beat on st_up_i) must add the difference.
    XT1_FILL_LEAD_OFFSET = (landed - as-built) of the hr leg - that of the fill legs, per slice; one value -> scalar."""
    B = o.B
    rows, offs = [], set()
    for hr in B.members(sink=r"\.u_tap$", port=r"^hr_q$"):
        sl = hr["sink"].rpartition(".u_tap")[0]
        sw = B.members(sink=re.escape(sl) + r"\.u_stm$", port=r"^sw_i$")
        xt = B.members(sink=re.escape(sl) + r"\.u_tap$", port=r"^xt_(a|d|vcopies)$")
        if not sw or not xt:
            continue
        d_hr = hr["landed"] - hr["asb"]
        d_sw = {m["landed"] - m["asb"] for m in sw}
        d_xt = {m["landed"] - m["asb"] for m in xt}
        if len(d_sw) != 1 or len(d_xt) != 1:
            o.error("XT1_FILL_LEAD_OFFSET", "compiler", f"{sl}: fill legs land at several offsets sw {sorted(d_sw)} xt "
                    f"{sorted(d_xt)}", group="xfill")
            return
        off = d_hr - next(iter(d_sw)) - next(iter(d_xt))
        offs.add(off)
        rows.append(dict(slice=sl, hr=d_hr, sw=next(iter(d_sw)), xt=next(iter(d_xt)), offset=off))
    if not rows:
        o.pending("XT1_FILL_LEAD_OFFSET", "compiler", "no u_fdn->u_tap hr crossing with u_stm fill legs on this bind",
                  group="xfill")
        return
    o.add("XT1_FILL_LEAD_OFFSET", sorted(offs)[0] if len(offs) == 1 else sorted(offs), "compiler",
          "(landed - as-built)(u_tap.hr_q) - (landed - as-built)(u_stm.sw_i) - (landed - as-built)(u_tap.xt_*), per slice: "
          "added to the x fill lead (hr arm -> first st_up_i beat; xt1 bench --lead 8 + offset)", dict(slices=len(rows)),
          group="xfill", status="OK" if len(offs) == 1 else "WARN",
          note=None if len(offs) == 1 else "per-slice table in XT1_FILL_SLICES")
    o.add("XT1_FILL_SLICES", rows, "compiler", "per slice legs of XT1_FILL_LEAD_OFFSET", group="xfill")


def seam_half(o, bundles, anchor, prefix):
    B = o.B
    st, inp = {}, {}
    for s, mem in bundles.items():
        ds = set()
        lv = []
        for sl, sp, dl, dp in mem:
            ms = B.members(source=rf"^{sl}\.{sp}$", sink=rf"^{dl}$", port=rf"^{dp}$")
            if not ms:
                raise RuleError(f"seam {s}: member {sl}.{sp} -> {dl}.{dp} is not a crossing on this bind")
            for m in ms:
                ds.add(m["landed"] - m["asb"])
                lv.append(m["landed"])
        if len(ds) != 1:
            raise RuleError(f"seam {s}: bundle members shift by {sorted(ds)} (one bundle = one age; R8 must keep it)")
        st[s] = anchor[s] + ds.pop()
        inp[s] = dict(landed=sorted(set(lv)), anchor=anchor[s])
    return st, inp


def qc_seam(o):
    st, inp = seam_half(o, QC_SEAM_BUNDLES, QC_ANCHOR["seam"], "C")
    names = ("CS_TXS", "CS_RXV", "CS_RXP", "CS_X3S", "SC_TX", "SC_X3")
    o.add("XDIE_SEAM_C", ",".join(str(st[n]) for n in names), "compiler",
          "d2d_link_calendar --die-stages compute half CS_TXS,CS_RXV,CS_RXP,CS_X3S,SC_TX,SC_X3 = as-built seam + Delta(bundle)",
          inp, group="xdie")
    c = [st["CS_TXS"] + N59_TX + st["SC_TX"], 1, 1, st["CS_X3S"] + N59_X3 + 1 + st["SC_X3"]]
    c = [x + p for x, p in zip(c, PINREG_EXT["C"])]
    r = o.add("D2D_TXDP_C", c, "rtl", "producer_txd_c + PINREG_EXT (d2d_link_calendar.py); byte p = port p",
              dict(st), inst=r"(^|\.)d2d_rom$|u_d2d", param="TXDP", group="xdie")
    r["sv_literal"] = f"32'h{_txdp_word(c):08x}"
    return st


# ============================================================================================================ KV
KV_STACKS = ("WS", "WN", "ES", "EN")
KV_ANCHOR = dict(FR_OFS=-7, KVN_A0=32, RESPONSE_LAT=80, QK_ISSUE_AGE=91,
                 seam=dict(KS_RXV=11, KS_RXP=11, KS_TXS=9, KS_TXK=9, KS_TXB=9, SK_TXV=9, SK_TXP=9))
KV_SEAM = {"KS_RXV": ("d2d_kv", r"att_rx_v", "kvs_attn", r"d2d__srx"),
           "KS_RXP": ("d2d_kv", r"rx_payload", "kvs_attn", r"d2d__rx_payload"),
           "KS_TXS": ("d2d_kv", r"att_tx_slot", "kvs_attn", r"d2d__att_tx_slot"),
           "KS_TXK": ("d2d_kv", r"att_tx_kind", "kvs_attn", r"d2d__att_tx_kind"),
           "KS_TXB": ("d2d_kv", r"att_tx_beat", "kvs_attn", r"d2d__att_tx_beat"),
           "SK_TXV": ("kvs_attn", r"attn__tx_valid", "d2d_kv", r"att_tx_v"),
           "SK_TXP": ("kvs_attn", r"attn__tx_payload", "d2d_kv", r"att_tx_payload")}
LANDING_SEG, VPORT_RT_SEG, VPORT_RL_BASE, QK_WBR, QK_KIT = 8, 9, 4, 11, 34


def kv_ectl(o):
    B = o.B
    req, rsp = defaultdict(set), defaultdict(set)
    for m in B.members(source=r"(^|\.)ectl_\w+\.req_", port=r"^kreq$"):
        req[m["source"].rpartition(".")[0]].add(m["landed"])
    for m in B.members(sink=r"(^|\.)ectl_\w+$", port=r"^rsp_"):
        rsp[m["sink"]].add(m["landed"])
    if not req:
        raise RuleError("no ectl krq crossing on this bind")
    rts = {}
    for f in sorted(req):
        q, s = req[f], rsp.get(f, set())
        if len(q) != 1 or len(s) != 1:
            raise RuleError(f"ECTL {f}: krq {sorted(q)} krs {sorted(s)} (one landed depth per leg)")
        rts[f] = LANDING_SEG + q.pop() + s.pop()
    rl = max(rts.values())
    uni = len(set(rts.values())) == 1
    g = "ectl"
    o.add("RESPONSE_LAT", rl, "rtl", "8 (landing seg) + D(krq) + D(krs); one value on every ECTL frame (type parameter)",
          dict(frames=len(rts), round_trips=sorted(set(rts.values()))), inst=r"(^|\.)ectl_\w+$", group=g,
          status="OK" if uni else "WARN", note=None if uni else "frames below the max need krq pads (rl - rt) x width")
    qk = max(QK_KIT, rl + QK_WBR)
    o.add("QK_ISSUE_AGE", qk, "rtl", "max(34, RESPONSE_LAT + 11) (static_qk_calendar write-before-read; 34 = attn calendar "
          "QK_CONSUME floor, KV owner choice KV-P6 18:09)", dict(RESPONSE_LAT=rl), inst=r"(^|\.)ectl_\w+$", group=g)
    o.add("ROW_RETURN_LAT", rl + 7, "rtl-derived", "RESPONSE_LAT + 7 (localparam inside qkd_ectl3_kiss_st)", group=g)
    o.add("QK_ROW_LATENCY", rl + 2, "compiler", "row_latency_for_calendar = RESPONSE_LAT + 2 (KV-P6-BOOT qk_row_latency)", group=g)
    o.add("QK_D_QK", qk - QK_KIT, "compiler", "kv_qkh_safe32.calendar_d_qk: D_QK = QK_ISSUE_AGE - 34 (+ data edges); must be "
          ">= 0", group=g, status="OK" if qk >= QK_KIT else "ERROR")


def kv_ahub(o):
    B = o.B
    asb = B.asbuilt_param(r"^ahub$", "AP_OFS", module=r"qkd_ahub_static_dw\w*")
    if asb is None:
        raise RuleError("as-built AP_OFS not in param_regen.json (bind without the KV hook)")
    v = _int(asb)
    ap_asb = {st: _s16(v >> (16 * k)) for k, st in enumerate(KV_STACKS)}
    lag = {}
    for st in KV_STACKS:
        side = "w" if st[0] == "W" else "e"
        d, ms = B.one(f"f_aqm_{side}", source=rf"seq__u_core\.f_aqm_{side}$", key="landed")
        a = {m["asb"] for m in ms}
        lag[st] = d - max(a)
    ap = {}
    for k, st in enumerate(KV_STACKS):
        d, ms = B.one(f"ap {st}", source=rf"astk_{st}__u_strip_u_strip_u_ctl\.ap$", sink=r"^ahub$")
        ap[st] = ap_asb[st] + d - ms[0]["asb"] + lag[st]
    lit = "64'h" + "".join(f"{ap[s] & 0xffff:04x}" for s in reversed(KV_STACKS))
    r = o.add("AP_OFS", [ap[s] for s in KV_STACKS], "rtl", "AP_OFS_s = asb_s + Delta D(ap_s) + Delta D(f_aqm) (stack order "
              "WS WN ES EN = [15:0]..[63:48])", dict(asbuilt=ap_asb, lag=lag), inst=r"^ahub$", group="ahub")
    r["sv_literal"] = lit
    intra = [b["lane"] for b in B.bus(r"kvs_attn\.(ahs|pvfst|pvst)|pvfin\.|ahub\.fr") if b["src"] != b["dst"]]
    o.add("FR_OFS", KV_ANCHOR["FR_OFS"], "rtl", "as-built: every FR_OFS term is intra hub_C (no lane)", inst=r"^ahub$",
          group="ahub", status="OK" if not intra else "ERROR", note=f"crossings on FR_OFS paths: {intra}" if intra else None)
    am = {}
    for k, st in enumerate(KV_STACKS):
        ms = B.members(source=rf"^ahub\.am{k}$", sink=rf"astk_{st}__u_strip_u_strip_u_ctl")
        am[st] = (ms[0]["landed"] - ms[0]["asb"] - lag[st]) if ms else None
    o.add("AM_LAG_DELTA", am, "compiler", "compiler EXP_START per stack: Delta D(am_s) - Delta L_s (kv_static_programme)",
          group="ahub")


def kv_pv_trunk(o):
    B = o.B
    TD = B.asbuilt_param(r"pvw_\d__u_ctl$", "TRUNK_D", module=r"ot_qwen_tp8_pv_wide_ctl_tbf\w*")
    FD = B.asbuilt_param(r"pvw_\d__u_ctl$", "FLAG_D", module=r"ot_qwen_tp8_pv_wide_ctl_tbf\w*")
    if TD is None or FD is None:
        raise RuleError("as-built TRUNK_D/FLAG_D not in param_regen.json")
    TD, FD = int(TD), int(FD)
    regen, per = {}, {}
    for side, pvw in (("S", "pvw_0"), ("N", "pvw_1")):
        cmd, flg = defaultdict(set), defaultdict(set)
        for m in B.members(source=pvw + r"__u_ctl\.cmd$", port=r"^join_go$"):
            cmd[int(re.search(r"_s(\d+)_j", m["sink"]).group(1))].add((m["asb"], m["landed"]))
        for m in B.members(source=pvw + r"__u_s\d+_j\.(y_valid|fault)$", port=r"^col_(valid|fault)$"):
            flg[int(re.search(r"_s(\d+)_j", m["source"]).group(1))].add((m["asb"], m["landed"]))
        if not cmd:
            raise RuleError(f"{pvw}: no cmd -> join_go crossing")
        cols = {}
        for s in sorted(cmd):
            if len(cmd[s]) != 1 or len(flg.get(s, ())) != 1:
                raise RuleError(f"{pvw} column {s}: cmd {sorted(cmd[s])} flag {sorted(flg.get(s, ()))} (one depth each)")
            (ca, cb), = cmd[s]
            (fa, fb), = flg[s]
            cols[s] = dict(cmd_asb=ca, cmd=cb, flag_asb=fa, flag=fb, dcmd=cb - ca)
        dc = {v["dcmd"] for v in cols.values()}
        tot = {s: v["cmd"] + v["flag"] for s, v in cols.items()}
        c0 = cols[min(cols)]
        trunk = TD + max(dc)
        flag = max(tot.values()) - (c0["cmd_asb"] + c0["flag_asb"] - FD - TD) - trunk
        regen[side] = dict(TRUNK_D=trunk, FLAG_D=flag, cmd_delta_uniform=len(dc) == 1,
                           flag_uniform=len(set(tot.values())) == 1)
        per[side] = cols
    same = regen["S"]["TRUNK_D"] == regen["N"]["TRUNK_D"] and regen["S"]["FLAG_D"] == regen["N"]["FLAG_D"]
    aligned = all(r["cmd_delta_uniform"] and r["flag_uniform"] for r in regen.values())
    st = "OK" if same and aligned else "WARN"
    note = None if aligned else ("column command Deltas / D+R not uniform on the landed depths: TRUNK_D/FLAG_D alone do not "
                                 "keep the pv_trunk_gen invariant -> PV pads (KV-P6-PV entry table) must equalise first")
    pvt = (B.param_regen.get("record") or {}).get("pv_table")
    law = dict(TRUNK_D=regen["S"]["TRUNK_D"], FLAG_D=regen["S"]["FLAG_D"])
    if pvt:
        # a PV pad table (KV-P6-PV model: V-D-H launch shift, entry pads) owns TRUNK_D/FLAG_D; the KV-P5 pv_trunk law on
        # the landed depths is the independent check.  Disagreement = table and lanes are not from one bind -> WARN.
        app = (B.param_regen.get("record") or {}).get("applied", {})
        for k in ("TRUNK_D", "FLAG_D"):
            v = app.get(k)
            agree = v == law[k]
            o.add(k, v, "rtl", f"PV pad table {pvt.get('file')} ({pvt.get('source', '')[:80]}); check: KV-P5 pv_trunk law on "
                  f"landed depths = {law[k]}", dict(asbuilt=TD if k == "TRUNK_D" else FD, law=law, sides=regen),
                  inst=r"pvw_\d__u_ctl$", group="pv", status="OK" if agree and st == "OK" else "WARN",
                  note=None if agree else f"law {law[k]} != table {v}: confirm the PV table belongs to this bind (KV owner)")
        return
    o.add("TRUNK_D", law["TRUNK_D"], "rtl", "TRUNK_D_asb + max_s Delta(cmd_s) (pv_trunk_gen)",
          dict(asbuilt=TD, sides=regen), inst=r"pvw_\d__u_ctl$", group="pv", status=st, note=note)
    o.add("FLAG_D", law["FLAG_D"], "rtl", "max_s(D_s + R_s) - TRUNK_D - (D+R - TRUNK_D - FLAG_D)_asb",
          dict(asbuilt=FD), inst=r"pvw_\d__u_ctl$", group="pv", status=st, note=note)


def kv_vport(o):
    B = o.B
    rows = {}
    for a in B.bus(r"vport_\w+\.vq"):
        vp = re.search(r"(vport_\w+?)\.vq", " ".join(a["leaves"])).group(1)
        for c in [x for x in B.bus(r"slg_\w+\.rsp", dst="pv") if x["src"] == a["dst"] and x["dst"] == a["src"]]:
            rows.setdefault(vp, []).append(VPORT_RT_SEG + a["bound_stages"] + c["bound_stages"])
    W = {m["sink"]: m["landed"] for m in B.members(r"pvw_\d__u_ctl\.req_t", sink=r"^vport_", port="pr_t")}
    if not rows:
        o.pending("VPORT_RT", "boot", "no vport vq/rsp crossing on this bind", group="vport")
        return
    out = {vp: dict(RT=max(r), W=W.get(vp)) for vp, r in sorted(rows.items())}
    if any(v["W"] is None for v in out.values()):
        o.pending("VPORT_DQ", "boot", "W request lane (pvw ctl req_t -> vport pr_t) not found for every vport", group="vport")
        o.add("VPORT_RT", {k: v["RT"] for k, v in out.items()}, "boot", "9 + max_g(D(vq_g) + D(rs_g))", group="vport")
        return
    rl = max(v["RT"] + v["W"] for v in out.values())
    dq = {k: rl - (v["RT"] + v["W"]) for k, v in out.items()}
    o.add("VPORT_RT", {k: v["RT"] for k, v in out.items()}, "boot", "9 + max_g(D(vq_g) + D(rs_g)) (<= 31)", group="vport",
          status="OK" if all(v["RT"] <= 31 for v in out.values()) else "ERROR")
    o.add("VPORT_DQ", dq, "boot", "max_q(W_q + RT_q) - (W_p + RT_p) (<= 15, else W-lane pads)", group="vport",
          status="OK" if max(dq.values()) <= 15 else "WARN",
          note=None if max(dq.values()) <= 15 else f"DQ > 15 on {[k for k, v in dq.items() if v > 15]}: W request pads")
    o.add("CFG_FIA", VPORT_RL_BASE + rl + 1, "boot", "4 + max_p(W_p + RT_p) + 1 (KV-P5 rule)", group="vport", status="WARN",
          note="KV-P6-BOOT: the boot generator RL = 4 + WP + O + DQ + RT (adds O) and the PV entry-pad table sets cfg_fia; "
               "the compiled boot image (KV_BOOT recipe) is authoritative for cfg_fia / DQ")


def kv_prog(o):
    B = o.B
    a0 = B.asbuilt_param(r"seq__u_core$", "KVN_A0", KV_ANCHOR["KVN_A0"], module=r"qkd_seq_core_static_s\w*")
    kvn, mk = B.one("kvn -> seq core", source=r"^d2d_kv\.kvn_word_valid$", sink=r"^seq__u_core$")
    rx, mr = B.one("att_rx -> kvs_attn", source=r"^d2d_kv\.att_rx_v$", sink=r"^kvs_attn$")
    dk, dr = kvn - mk[0]["asb"], rx - mr[0]["asb"]
    v = int(a0) + dk - dr
    o.add("KVN_A0", v, "rtl", "KVN_A0_asb + Delta(d2d kvn_word_valid -> seq core) - Delta(d2d att_rx_v -> kvs_attn) "
          "(KV-P6 18:09: age a starts at the attention programme request, triggered by att_rx)",
          dict(asbuilt=int(a0), kvn=[mk[0]["asb"], kvn], att_rx=[mr[0]["asb"], rx]), inst=r"seq__u_core$", group="prog",
          status="OK" if 0 <= v and v + 4 < 256 else "ERROR")
    ages = {}
    for name, src, sink in (("programme_start", r"^dcal\.tok_start$", r"^kvs_ctl$"),
                            ("d2d_to_attention_rx", r"^d2d_kv\.att_rx_v$", r"^kvs_attn$"),
                            ("d2d_to_writer", r"^d2d_kv\.kvn_word_valid$", r"^kvs_ctl$"),
                            ("d2d_to_seq_kvn", r"^d2d_kv\.kvn_word_valid$", r"^seq__u_core$")):
        ms = B.members(src, sink)
        ages[name] = sorted({m["landed"] for m in ms}) if ms else None
    tx = B.members(r"^kvs_attn\.attn__tx_valid$", r"^d2d_kv$")
    ages["attention_tx"] = sorted({m["landed"] for m in tx}) if tx else None
    o.add("D2D_AGES", ages, "boot", "landed depth d2d_kv/dcal -> kvs_ctl / kvs_attn / seq core, attn tx -> d2d_kv "
          "(kv_boot_v36.py DIE_TABLE inputs)", group="prog")
    dr_ = {}
    for st in KV_STACKS:
        d = B.members(rf"kvs_ctl\.o_hroot_{st}$", sink=r"kvs_hroot")
        r = B.members(rf"kvs_hroot_{st}\.o_ctl$", sink=r"^kvs_ctl$")
        dr_[st] = [d[0]["landed"] if d else None, r[0]["landed"] if r else None]
    o.add("HROOT_DOWN_RET", dr_, "boot", "kvs_ctl.o_hroot_s -> hroot / hroot.o_ctl -> kvs_ctl landed (emb_fill / writer_die)",
          group="prog")


def kv_seam(o):
    B = o.B
    st, inp = {}, {}
    for s, (sl, sp, dl, dp) in KV_SEAM.items():
        ms = B.members(source=rf"^{sl}\.{sp}$", sink=rf"^{dl}$", port=rf"^{dp}$")
        if not ms:
            raise RuleError(f"seam {s}: {sl}.{sp} -> {dl}.{dp} not a crossing")
        ds = {m["landed"] - m["asb"] for m in ms}
        if len(ds) != 1:
            raise RuleError(f"seam {s}: members shift by {sorted(ds)}")
        st[s] = KV_ANCHOR["seam"][s] + ds.pop()
        inp[s] = sorted({m["landed"] for m in ms})
    names = ("KS_RXV", "KS_RXP", "KS_TXS", "KS_TXK", "KS_TXB", "SK_TXV", "SK_TXP")
    o.add("XDIE_SEAM_K", ",".join(str(st[n]) for n in names), "compiler",
          "d2d_link_calendar --die-stages KV half (KV-P6-BOOT KST) = as-built seam + Delta", inp, group="xdie")
    k = [st["KS_TXS"] + KV_CODEC_LANDED + st["SK_TXP"], 2, 1, 1]
    k = [x + p for x, p in zip(k, PINREG_EXT["K"])]
    r = o.add("D2D_TXDP_K", k, "rtl", "[KS_TXS + KV_CODEC(2) + SK_TXP, 2 + host, 1, 1] + PINREG_EXT (d2d_link_calendar "
              "producer_txd); the compute die must bind the same pair image", dict(st), inst=r"d2d_kv$|u_d2d", param="TXDP",
              group="xdie")
    r["sv_literal"] = f"32'h{_txdp_word(k):08x}"
    asb = KV_ANCHOR["seam"]["KS_TXS"] + KV_CODEC_LANDED + KV_ANCHOR["seam"]["SK_TXP"] + PINREG_EXT["K"][0]
    o.add("D2D_KV_TX_LAT", k[0], "compiler", "shared QC<->KV pair image KV TX latency = TXDP K[0] = KS_TXS + KV_CODEC + "
          "SK_TXP + PR pin flops, from the KV bound top; BOTH dies bind the same pair image (QC emits it with --peer)",
          dict(KS_TXS=st["KS_TXS"], SK_TXP=st["SK_TXP"], asbuilt=asb), group="xdie",
          note=None if k[0] == asb else f"moved {asb} -> {k[0]} vs as-built: re-bind the pair image on both dies")


# ============================================================================================================ HBM
def hbm_rules(o, src_root, hbm_tools):
    B = o.B
    # leaf-split shifts: fixed per bound twin (leaf property, benched lock-step)
    ls = None
    for cand in [hbm_tools, Path(src_root) / "tools" / "hbm_static", REPO / "tools" / "hbm_static"]:
        if cand and (Path(cand) / "leaf_split_latency.py").exists():
            sys.path.insert(0, str(cand))
            import leaf_split_latency as ls
            break
    if ls is None:
        o.pending("LEAF_SPLIT_SHIFTS", "compiler", "tools/hbm_static/leaf_split_latency.py not found (claude/hbm-p6-cmp-1023)",
                  group="leaf_split")
    else:
        twins = {"sfu": r"ot_hgi_sfu_core_split3_sp2", "su": r"ot_hbm_su_static_pgslice_lg_s\b",
                 "hc": r"ot_hbm_hc_root_static_s|tail_unit_static_s", "coll": r"ot_hgi_coll_reduce_static_pr|coll_q2_hard_v8g_s",
                 "tkm": r"ot_hgi_coll_tkm_static_p"}
        text = ""
        if B and (B.dir / "rtl").is_dir():
            text = " ".join(f.read_text(errors="replace") for f in (B.dir / "rtl").glob("*.sv"))
        bound = {u: bool(re.search(p, text)) for u, p in twins.items()} if text else None
        sh = {}
        for k, (e, where, src) in ls.SHIFTS.items():
            u = k.split("_")[0]
            on = bound.get(u) if bound is not None else None
            sh[k] = dict(edges=e if on else 0, edges_if_bound=e, twin_bound=on, where=where)
        o.add("LEAF_SPLIT_SHIFTS", sh, "compiler", "leaf_split_latency.SHIFTS for the twins bound in this top (0 when the "
              "pinned unit is bound); compilers: OT_HBM_LEAF_SPLIT=1 iff any twin_bound", group="leaf_split",
              status="OK" if bound is not None else "PENDING")
        o.add("OT_HBM_LEAF_SPLIT", int(any(v["twin_bound"] for v in sh.values())) if bound is not None else None,
              "compiler", "1 iff the bound top instantiates a leaf-split twin", group="leaf_split",
              status="OK" if bound is not None else "PENDING")
    if B is None:
        o.pending("BANK_CLIENT_RT", "rtl", "no HBM bound top yet (BINDER4 d4g bind running)", group="l12")
        return
    # bank-client round trips (d4g_bank_latency RULES, l12 budget law) on landed depths
    sys.path.insert(0, str(Path(src_root) / "tools" / "hbm_die_v16"))
    try:
        import d4g_bank_latency as BL
    except ImportError as e:
        o.pending("BANK_CLIENT_RT", "rtl", f"d4g_bank_latency not importable: {e}", group="l12")
        return
    banks = B.rtl_insts("|".join(BL.BANK_PIN))
    clients = B.rtl_insts("|".join(re.escape(m) for m in BL.RULES))
    res = {}
    for inst, c in sorted(clients.items()):
        for port, kind, param, ref, ref_rt, bank_lat, why in BL.RULES[c["module"]]:
            back = BL.READ.get(port) or BL.WRITE.get(port) or port.replace("q", "r")
            rts = {}
            for m in B.members(source=rf"^{re.escape(inst)}\.{port}\d*$"):
                bk = banks.get(m["sink"])
                if not bk:
                    continue
                rr = B.members(source=rf"^{re.escape(m['sink'])}\.", sink=rf"^{re.escape(inst)}$", port=rf"^{back}")
                pin = BL.BANK_PIN.get(bk["module"], 0)
                rts[m["sink"]] = bank_lat + pin + m["landed"] + (max(x["landed"] for x in rr) if rr else 0)
            if not rts:
                continue
            rt = max(rts.values())
            res[f"{inst}.{param}"] = dict(value=ref + rt - ref_rt, per_bank={b: ref + v - ref_rt for b, v in rts.items()},
                                          equal=len(set(rts.values())) == 1, module=c["module"])
    if not res:
        o.pending("BANK_CLIENT_RT", "rtl", "no bank client / bank crossing found in the bound RTL", group="l12")
    else:
        o.add("BANK_CLIENT_RT", res, "rtl", "param = ref + RT - ref_rt; RT_b = BANK + PIN + D(rq->bank) + D(bank->rr) "
              "(d4g_bank_latency.py l12 law; SCALAR = max over banks + pads, VECTOR = per bank)", group="l12")


# ============================================================================================================ S81
def s81_rules(o):
    B = o.B
    if B is None:
        for k in ("FRAME_CAL_LANE_DELTA", "BF_RETURN_DELTA"):
            o.pending(k, "compiler", "no S81 bound top yet (BINDER4-S81 bind on plan v4.6/v4.7 running)", group="frame")
        return
    cls, bf, unpl = defaultdict(dict), {}, []
    for b in B.buses:
        if not b.get("lane"):
            unpl.append(f"{b['src']}->{b['dst']} {b['bus_out']}->{b['bus_in']}")
            continue
        c = re.match(r"[A-Za-z]+", b["lane"]).group(0)
        row = dict(asbuilt=b["asbuilt_stages"], bound=b["bound_stages"], delta=b["bound_stages"] - b["asbuilt_stages"][1],
                   src=b["src"], dst=b["dst"])
        cls[c][b["lane"]] = row
        if re.search(r"(^|[._])bf|bf_ret|\.ret", " ".join(b["leaves"])):
            bf[b["lane"]] = row
    o.add("FRAME_CAL_LANE_DELTA", {c: dict(sorted(v.items())) for c, v in sorted(cls.items())}, "compiler",
          "per crossing lane (class = alphabetic plan lane prefix: x, xo, rt, fi, up, dn, attn, coll, ...): bound stages and delta vs the as-built max = the frame calendar's "
          "LANE_LANDING_CYCLES / per-crossing die-lane term (TOKi-PRICE price_s81_plan_lat.py hooks)", group="frame",
          note=f"{len(unpl)} buses ride no plan lane: {unpl[:5]}" if unpl else None, status="OK" if not unpl else "WARN")
    o.add("BF_RETURN_DELTA", bf, "compiler", "BF return lanes (leaves bf*/ret) bound vs as-built (frame_schedule.py BF "
          "return edges; anchor = S81-P8 measured LP calendar)", group="frame", status="OK" if bf else "PENDING")


# constants the bound RTL must carry (module regex, parameter): checked on BIND_DIR/rtl by Out.rtl_check
RTL_CHECK = {
    "qwen_compute": [("COLL_LS", r"qfd_io_collective_static\w*", "LS")],
    "qwen_kvsys": [("RESPONSE_LAT", r"qkd_ectl3_kiss_st\w*", "RESPONSE_LAT"), ("QK_ISSUE_AGE", r"qkd_ectl3_kiss_st\w*", "QK_ISSUE_AGE"),
                   ("AP_OFS", r"qkd_ahub_static_dw\w*", "AP_OFS"), ("FR_OFS", r"qkd_ahub_static_dw\w*", "FR_OFS"),
                   ("KVN_A0", r"qkd_seq_core_static_s\w*", "KVN_A0"), ("TRUNK_D", r"ot_qwen_tp8_pv_wide_ctl_tbf\w*", "TRUNK_D"),
                   ("FLAG_D", r"ot_qwen_tp8_pv_wide_ctl_tbf\w*", "FLAG_D"), ("D2D_TXDP_K", r"qkd_d2d_static\w*", "TXDP")],
}


# ============================================================================================================ emit
def _sv_name(n):
    return re.sub(r"\W", "_", n).upper()


def sv_package(die, doc):
    pk = f"{die}_sched_pkg"
    L = [f"// GENERATED by tools/die_plan/regen_constants.py --die {die} --bound {doc['bound']} (do not edit)",
         f"// bound top sha {doc.get('bound_sha')}; verdict {doc['verdict']}",
         f"package {pk};"]
    for n, r in doc["constants"].items():
        v = r.get("sv_literal", r["value"])
        if r["status"] in ("PENDING", "ERROR") or v is None:
            L.append(f"  // {n}: {r['status']} {str(r['formula'])[:100]}")
            continue
        if isinstance(v, bool):
            v = int(v)
        if isinstance(v, int):
            L.append(f"  localparam int {_sv_name(n)} = {v};")
        elif isinstance(v, str) and re.fullmatch(r"\d+'[bhd][0-9a-fA-F_]+", v):
            w = int(v.split("'")[0])
            L.append(f"  localparam logic [{w - 1}:0] {_sv_name(n)} = {v};")
        elif isinstance(v, str) and re.fullmatch(r"\d+(,\d+)+", v):
            L.append(f"  localparam int {_sv_name(n)} [{v.count(',') + 1}] = '{{{v.replace(',', ', ')}}};")
        elif isinstance(v, list) and v and all(isinstance(x, int) for x in v):
            L.append(f"  localparam int {_sv_name(n)} [{len(v)}] = '{{{', '.join(str(x) for x in v)}}};")
        else:
            L.append(f"  // {n}: table (see JSON)")
    L.append(f"endpackage : {pk}")
    return "\n".join(L) + "\n"


def run(die, bound, src_root=REPO, hbm_tools=None, peer=None):
    B = Bound(bound) if bound else None
    o = Out(die, B)
    if die == "qwen_compute":
        o.rule("coll", qc_coll, src_root)
        o.rule("treq", qc_treq)
        o.rule("xfill", qc_xfill)
        o.rule("xdie", qc_seam)
    elif die == "qwen_kvsys":
        o.rule("ectl", kv_ectl)
        o.rule("ahub", kv_ahub)
        o.rule("pv", kv_pv_trunk)
        o.rule("vport", kv_vport)
        o.rule("prog", kv_prog)
        o.rule("xdie", kv_seam)
    elif die == "hbm":
        o.rule("hbm", hbm_rules, src_root, hbm_tools)
    elif die == "s81":
        o.rule("s81", s81_rules)
    else:
        raise SystemExit(f"unknown die {die}")
    if peer:      # pair seam: the full --die-stages string for the d2d calendar image
        po = run({"qwen_compute": "qwen_kvsys", "qwen_kvsys": "qwen_compute"}[die], peer, src_root)
        po.pop("_bound_obj", None)
        mine = o.c
        theirs = po["constants"]
        cs = (mine if die == "qwen_compute" else theirs).get("XDIE_SEAM_C", {}).get("value")
        ks = (theirs if die == "qwen_compute" else mine).get("XDIE_SEAM_K", {}).get("value")
        if die == "qwen_compute" and theirs.get("D2D_KV_TX_LAT", {}).get("status") == "OK":
            t = theirs["D2D_KV_TX_LAT"]
            o.add("D2D_KV_TX_LAT", t["value"], "compiler", "from the KV peer bound top (--peer): " + t["formula"],
                  dict(t["inputs"], peer=str(peer)), group="xdie", note=t.get("note"))
            k = theirs["D2D_TXDP_K"]
            r = o.add("D2D_TXDP_K", k["value"], "compiler", "pair image KV TXDP from the KV peer bound top", dict(peer=str(peer)),
                      group="xdie")
            r["sv_literal"] = k.get("sv_literal")
        if cs and ks:
            o.add("XDIE_DIE_STAGES", f"{cs}/{ks}", "compiler", "D2D_DIE_STAGES for tools/qwen_split/d2d_cal_image_production.sh "
                  "(pair calendar image; both dies bind its TXDP)", dict(peer=str(peer)), group="xdie")
    if B:
        o.crosscheck()
        o.rtl_check(RTL_CHECK.get(die, []))
    rec = {}
    if B and die == "qwen_kvsys" and o.c.get("XDIE_SEAM_K", {}).get("value"):
        bg = next((str(B.dir / f) for f in ("bus_groups.json", "bus_groups.json.gz") if (B.dir / f).exists()), None)
        rec["kv_boot_image"] = (f"S=<scratch>/boot BG={bg} KST={o.c['XDIE_SEAM_K']['value']} "
                                "bash physical/die_plan/qwen_kvsys/boot_v36/run.sh   # KV-P6-BOOT generator (claude/kv-p6-boot-1023)")
    ds = o.c.get("XDIE_DIE_STAGES", {}).get("value")
    if ds:
        rec["xdie_pair_image"] = (f"D2D_DIE_STAGES={ds} D2D_MU=1 D2D_EMB_WINDOW=595 D2D_ATTN_TX_SHIFT=1 D2D_STATUS_DELAY=213 "
                                  "bash tools/qwen_split/d2d_cal_image_production.sh <out>   # both dies bind its TXDP")
    if die == "qwen_compute" and o.c.get("COLL_BENCH_ARGS", {}).get("value"):
        rec["tp8_bench"] = f"tp8 / tp8_mu link benches: {o.c['COLL_BENCH_ARGS']['value']} (LS {o.c['COLL_LS']['value']})"
    doc = dict(schema=SCHEMA, die=die, bound=str(bound) if bound else None, bound_sha=B.top_sha() if B else None,
               generator="tools/die_plan/regen_constants.py", bind_hook=B.param_regen.get("file") if B else None,
               verdict=o.verdict(), constants=o.c, recipes=rec)
    doc["_bound_obj"] = B
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--die", required=True, choices=["qwen_compute", "qwen_kvsys", "hbm", "s81"])
    ap.add_argument("--bound", help="bind output dir (tools/die_plan/bind.py --out); omit = no bound top yet (PENDING)")
    ap.add_argument("--peer", help="the other die's bind dir (Qwen compute <-> KV) -> XDIE_DIE_STAGES")
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-sv", type=Path)
    ap.add_argument("--expect", type=Path, help="JSON {name: value} hand values of record; any difference -> exit 1")
    ap.add_argument("--src-root", type=Path, default=REPO, help="repo tree with tools/qwen_split + rtl (coll RTL defaults)")
    ap.add_argument("--hbm-tools", type=Path, help="dir with leaf_split_latency.py (default: <src-root>/tools/hbm_static)")
    ap.add_argument("--write-fixture", type=Path, help="write the members this run read as a small test fixture")
    a = ap.parse_args(argv)
    doc = run(a.die, a.bound, a.src_root, a.hbm_tools, a.peer)
    B = doc.pop("_bound_obj")
    rc = 0
    if a.expect:
        exp = json.loads(a.expect.read_text())
        diffs = {k: dict(expect=v, got=doc["constants"].get(k, {}).get("value")) for k, v in exp.items()
                 if not k.startswith("_") and doc["constants"].get(k, {}).get("value") != v}
        doc["expect"] = dict(file=str(a.expect), diffs=diffs, pass_=not diffs)
        rc |= bool(diffs)
    if a.write_fixture and B:
        B.write_fixture(a.write_fixture)
    js = json.dumps(doc, indent=1, default=str) + "\n"
    if a.out_json:
        a.out_json.parent.mkdir(parents=True, exist_ok=True)
        a.out_json.write_text(js)
    if a.out_sv:
        a.out_sv.parent.mkdir(parents=True, exist_ok=True)
        a.out_sv.write_text(sv_package(a.die, doc))
    for n, r in doc["constants"].items():
        v = r.get("sv_literal", r["value"])
        s = json.dumps(v, default=str)
        print(f"[{r['status']:8s}] {r.get('group') or '':10s} {n:22s} {s[:100]}" +
              (f"  !! {r['mismatch']}" if r.get("mismatch") else "") + (f"  ({r['formula'][:120]})" if r["status"] in ("ERROR", "PENDING") else ""))
    bad = {k: v for k, v in doc["verdict"].items() if k in ("ERROR", "MISMATCH")}
    print(f"REGEN_CONSTANTS {a.die} {'FAIL' if bad or rc else 'PASS'} {doc['verdict']}" +
          (f" expect_diffs={doc['expect']['diffs']}" if a.expect and doc['expect']['diffs'] else ""))
    return 1 if (bad or rc) else 0


if __name__ == "__main__":
    sys.exit(main())
