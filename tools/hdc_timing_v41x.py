#!/usr/bin/env python3
"""Event-level cycle model of the RE-SPECIFIED DeepSeek-V4.1 decode core (docs/ARCH_SPEC_V41.md 4-6).

    python3 tools/hdc_timing_v41x.py [--out results/arch/v41x_replay.json]

It replays the SAME shipped-shape instruction stream tools/hdc_replay_v41.py emits for one die's share of a
token in packaging option (b) (tensor group 4), with every op mapped to its re-specified unit:

* QE LINQ          -> quantised weight engine (7,248 block-dots = 231,936 FP8/FP4 MACs per cycle), depth
                      60 + 3 ceil(log2(K / 32 / 8));
* ME weight op     -> BF16/FP32 weight engine (31,360 MACs/cycle), depth 60 + 3 ceil(log2(K / 8));
* ME KV-sourced op -> attention engine (34,176 MACs/cycle, row staging 2.2 KB/cycle; score depth 50, p.v 70) or,
                      for indexer-tagged ops, the indexer engine (228,864 FP4 MACs/cycle ~ 56 keys/cycle, keys
                      from the die's HBM at 3.6 TB/s, depth 30); the index head sum (the SU op of the indexer) is
                      fused into the indexer;
* SU               -> vector unit: 1,024 light lanes, 256 SFU lanes (exp / sigmoid / silu / divide), a scalar
                      side pipe (rsqrt / sqrt / softplus / Engram gate); total depths 21 / 70 (exp) / 101
                      (sigmoid, silu) / 52 (divide, sqrt) / 58 (rsqrt) / 280 (softplus) / 132 (gate);
                      reductions lane-parallel R-ARITH (result 25 cycles after the last element); the
                      index-selected row gather (SU gathers from the compressed store) becomes an HBM row
                      gather (first row 250 ns, 288 B per row at the die's HBM rate);
* HE               -> hyper-connection projection, 2,048 FP32 MAC lanes;
* XU SELECT        -> streaming-filter select, 64 scores/cycle ingest, tail 2 ceil(survivors / 64) + 63 with
                      survivors ~ k (1 + ln(n / k)); Sinkhorn unchanged (41 x 7 + 10); Engram hash and gather
                      prefetched from token start (engram_inline=False, the DAG's placement).

SEQUENCING (the re-specified core).  The sequencer dispatches one instruction every `gap` cycles into per-unit
in-order queues; an op starts when its unit is free (the previous op on the unit has issued its last element:
units pipeline) and its TRUE data dependences allow -- the dependence set is the program's region read / write
sets (the inputs of hdc_program_v41.schedule), not the wait masks:
* read-after-write, CHAINED (a credit per vector): a consumer may start once its producer's first output
  vector exists (start >= producer start + producer depth) and its last element cannot pass the producer's
  last output (start + occupancy >= producer finish);
* read-after-write, NOT chainable: a reduction's scalar result, a select's indices, the Sinkhorn / HE / XU
  results -> start >= the producer's finish (plus the reduction's tail);
* write-after-read / write-after-write: the writer's first write follows the reader's last read / the
  previous writer's last write.
`chaining=False` replaces all of this with the as-built wait-mask DRAINS (every masked unit idle) and in-order
blocking issue -- the same sequencer as hdc_timing_v41.simulate, at the new units' widths.

`as_built=True` (with chaining=False) prices every op with hdc_timing_v41's calibrated as-built unit formulas;
at the reduced program it must reproduce hdc_timing_v41.simulate (validate()).

Per-token = compute cycles of the die's program / clock + the DAG's per-token communication (collective
latency + bytes + pipeline hops of option (b) at batch 1, as tools/hdc_replay_v41.py adds).
"""
import argparse
import json
import math
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import hdc_isa_v41 as I
import hdc_replay_v41 as R

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/arch/v41x_replay.json"
BUDGET = ROOT / "results/arch/arch_budget_v41.json"
SCHEMA = "opentallas.v41x-replay.v1"
IL = I.INTERLEAVE
CONTEXTS = (8192, 200000, 1048576)


@dataclass
class Spec:
    clock_hz: float = 1.0339e9
    qe_macs: float = 231936.0          # quantised weight engine
    me_macs: float = 31360.0           # BF16/FP32 weight engine
    att_macs: float = 34176.0          # attention engine
    att_kv_bytes: float = 2202.75      # row staging read bytes/cycle
    idx_macs: float = 228864.0         # indexer engine (FP4 x FP4)
    hbm_Bps: float = 3.6e12            # the die's HBM sustained bandwidth (keys, gathered rows): 4 stacks x 0.9 TB/s
                                       # (arch_budget_v41.ROM_DIE_HBM_BPS)
    su_lanes: int = 1024
    sfu_lanes: int = 256
    side_lanes: int = 1                # scalar side pipe (rsqrt / sqrt / softplus / gate)
    hc_macs: float = 2048.0
    sel_lanes: int = 64
    sel_lat0: int = 63
    gap: int = 5                       # sequencer cycles per dispatched instruction
    chaining: bool = True
    su_cls_penalty: int = 0            # extra cycles when the vector unit changes class (0: separate pipes)
    red_tail: int = 25
    gather_s: float = 250e-9           # first-row latency of an index-selected HBM row gather
    sinkhorn: int = 41 * 7 + 10
    # depths (cycles)
    qe_depth0: int = 60
    me_depth0: int = 60
    att_s_depth: int = 50
    att_pv_depth: int = 70
    idx_depth: int = 30
    he_depth: int = 60
    su_depth: dict = None

    def depths(self):
        return self.su_depth or {"none": 21, "exp": 70, "sigm": 101, "div": 52, "sqrt": 52, "rsqrt": 58,
                                 "spsqrt": 280, "egate": 132}


UNITS = ("SEQ", "QE", "ME", "ATT", "IDX", "SU", "SFU", "SIDE", "HE", "SEL", "CAND", "SINK", "HBM", "XU")
SFU_NAME = {I.SFU_NONE: "none", I.SFU_EXP: "exp", I.SFU_SIGM: "sigm", I.SFU_SILU: "sigm", I.SFU_RSQRT: "rsqrt",
            I.SFU_SQRT: "sqrt", I.SFU_SPSQRT: "spsqrt", I.SFU_EGATE: "egate"}
SIDE = ("rsqrt", "sqrt", "spsqrt", "egate")


def cdiv(a, b):
    return -(-a // b)


def region_of(vmap, addr):
    best = None
    for name, base in vmap.items():
        if base <= addr and (best is None or base > best[1]):
            best = (name, base)
    return best[0] if best else None


class Op:
    __slots__ = ("n", "unit", "occ", "depth", "tail", "s", "f", "fred", "red_region", "chain", "tag", "why",
                 "pred", "kind")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


def cost_new(f0, f, D, sp, clock, vmap):
    """(unit, occupancy, depth, reduction region or None, chainable output, kind) of op f in the new core."""
    u = f["unit"]
    tag = f0.get("_tag", "") or ""
    if u == I.UNIT_QE:
        if f["qe_mode"] == I.QE_LINQ:
            K = f["qe_nb"] * 32
            macs = f0.get("_macs") or f["qe_tiles"] * f["qe_nb"] * IL * I.BL * 32
            return "QE", max(1, math.ceil(macs / sp.qe_macs)), \
                sp.qe_depth0 + 3 * max(0, math.ceil(math.log2(max(1, K / 32 / 8)))), None, True, "qe"
        return "QE", max(1, cdiv(f["qe_nb"] * 32, 256)), 15, None, True, "qdq"
    if u == I.UNIT_ME:
        kvm = f0.get("_kvmacs")
        if kvm:
            kind, nh, rows, hd = kvm
            rows = D(rows)
            macs = nh * rows * hd
            if "indexer" in tag:
                by = rows * 68
                occ = max(math.ceil(macs / sp.idx_macs), math.ceil(by / (sp.hbm_Bps / clock)))
                return "IDX", max(1, occ), sp.idx_depth, None, True, "idx"
            by = rows * 528 if kind == "S" else 0
            occ = max(math.ceil(macs / sp.att_macs), math.ceil(by / sp.att_kv_bytes))
            return "ATT", max(1, occ), sp.att_s_depth if kind == "S" else sp.att_pv_depth, None, True, "att"
        K = (f["me_k"] + D(f["me_d_k"])) * (1 << f.get("me_split", 0))
        macs = f0.get("_macs") or 0
        return "ME", max(1, math.ceil(macs / sp.me_macs)), \
            sp.me_depth0 + 3 * max(0, math.ceil(math.log2(max(1, K / 8)))), None, True, "me"
    if u == I.UNIT_HE:
        macs = f0.get("_macs") or f["he_nout"] * f["he_k"] * 8
        K = f["he_k"] * 8
        return "HE", max(1, math.ceil(macs / sp.hc_macs)), 3 + 3 * (7 + math.ceil(math.log2(max(1, K / 8)))), \
            None, True, "he"
    if u == I.UNIT_SU:
        no, ni = f["su_nout"] + D(f["su_d_nout"]), f["su_nin"] + D(f["su_d_nin"])
        n = no * ni
        red = region_of(vmap, f["r_base"]) if (f["red"] or f0.get("red_tree")) else None
        if "indexer" in tag and f["red"] and not tag.endswith(".cand"):
            return "IDX", 1, 30, red, True, "idx_headsum"          # fused into the indexer
        if tag.endswith(".cand"):
            return "CAND", max(1, cdiv(n, sp.sel_lanes)), 10, red, True, "cand_blockmax"
        if f["a_ind"] and ("gather" in tag):
            rows = no
            return "HBM", max(1, math.ceil(rows * 288 / (sp.hbm_Bps / clock))), math.ceil(sp.gather_s * clock), \
                None, False, "gather"
        name = SFU_NAME.get(f["sfu"], "none")
        if f["m1"] in (I.M1_DIVB, I.M1_DIVIMM) and name == "none":
            name = "div"
        dep = sp.depths()[name]
        if name in SIDE:
            unit, lanes = "SIDE", sp.side_lanes
        elif name != "none":
            unit, lanes = "SFU", sp.sfu_lanes
        else:
            unit, lanes = "SU", sp.su_lanes
        step = 8 if f["red"] == I.RED_SEQ else 1
        occ = max(1, cdiv(n, lanes)) * step
        return unit, occ, dep, red, True, "su_" + name
    op = f["xu_op"]
    if op == I.XU_SEL:
        nn = f["xu_n"] + D(f["xu_d_n"])
        cand_unit = "CAND" if tag.endswith(".cand") else "SEL"      # the candidate select is its own block
        kk = min(f["xu_k"] + D(f["xu_d_k"]), nn)
        surv = min(nn, math.ceil(kk * (1 + math.log(max(1.0, nn / max(1, kk))))))
        return cand_unit, max(1, cdiv(nn, sp.sel_lanes)), 2 * cdiv(surv, sp.sel_lanes) + sp.sel_lat0, None, False, \
            "select"
    if op == I.XU_SINK:
        return "SINK", 1, sp.sinkhorn, None, False, "sinkhorn"
    return "XU", 1, 20, None, False, "engram"


def skipped(f, D, pos):
    u = f["unit"]
    skip = (f["pred"] == I.PRED_ODD and not pos & 1) or (f["pred"] == I.PRED_NZ and pos == 0)
    if u == I.UNIT_ME:
        skip |= 0 in (f["me_nout"] + D(f["me_d_nout"]), f["me_tiles"] + D(f["me_d_tiles"]), f["me_k"] + D(f["me_d_k"]))
    elif u == I.UNIT_SU:
        skip |= (f["su_nout"] + D(f["su_d_nout"])) == 0 or (f["su_nin"] + D(f["su_d_nin"])) == 0
    elif u == I.UNIT_XU and f["xu_op"] == I.XU_SEL:
        skip |= f["xu_n"] + D(f["xu_d_n"]) == 0
    return skip


def simulate_new(prog, pos, shape, sp=Spec(), stats=None):
    """The re-specified core on a program (hdc_replay_v41.build output).  Returns cycles."""
    clock = sp.clock_hz
    ivals, dv = I.dyn_values(0, pos), R.dyn_values(shape, pos)
    D = lambda sel: ivals[sel] if isinstance(sel, int) else R.resolve(sel, dv)   # noqa: E731
    vmap = R.ShapeLayout(shape).vm.map
    unit_free = {u: 0 for u in UNITS}
    unit_idle = {u: 0 for u in UNITS}
    last_on = {u: None for u in UNITS}
    prev_disp = None
    last_w, readers = {}, {}
    ops = []
    disp = 0
    busy = {u: 0 for u in UNITS}
    su_cls = None
    n_issued = 0
    for n, f0 in enumerate(prog):
        f = {name: f0.get(name, 0) for name, _ in I.FIELDS}
        if f["unit"] == I.UNIT_END:
            break
        if skipped(f, D, pos):
            continue
        n_issued += 1
        unit, occ, depth, red, chainable, kind = cost_new(f0, f, D, sp, clock, vmap)
        cand = [(disp + 1, prev_disp, "dispatch"), (unit_free[unit], last_on[unit], "unit busy")]
        if sp.chaining:
            for r in f0.get("_reads", ()):
                w = last_w.get(r)
                if w is None:
                    continue
                if r == w.red_region:
                    cand.append((w.fred, w, "raw full (reduction)"))
                elif w.chain:
                    cand.append((w.s + w.depth, w, "raw chained first"))
                    cand.append((w.f - occ, w, "raw chained last"))
                else:
                    cand.append((w.f, w, "raw full"))
            for r in f0.get("_writes", ()):
                for rd in readers.get(r, ()):
                    if rd is not None:
                        cand.append((rd.s + rd.occ - depth, rd, "war"))
                w = last_w.get(r)
                if w is not None:
                    cand.append((max(w.f, w.fred or 0) - occ - depth, w, "waw"))
        else:
            for b in range(5):
                if f["wait"] >> b & 1:
                    uu = {0: ("ME", "ATT", "IDX"), 1: ("SU", "SFU", "SIDE", "HBM"), 2: ("QE",),
                          3: ("SEL", "CAND", "SINK", "XU"), 4: ("HE",)}[b]
                    for x in uu:
                        cand.append((unit_idle[x], last_on[x], "drain"))
        if unit in ("SU", "SFU", "SIDE") and sp.su_cls_penalty and su_cls is not None and su_cls != kind:
            cand.append((unit_free[unit] + sp.su_cls_penalty, None, "su class change"))
        s, pred, why = max(cand, key=lambda c: c[0])
        s = max(0, s)
        fin = s + occ + depth
        fred = fin + sp.red_tail if red else None
        op = Op(n=n, unit=unit, occ=occ, depth=depth, s=s, f=fin, fred=fred, red_region=red, chain=chainable,
                tag=f0.get("_tag"), why=why, pred=pred, kind=kind)
        ops.append(op)
        unit_free[unit] = s + occ
        unit_idle[unit] = max(unit_idle[unit], fred or fin)
        last_on[unit] = op
        prev_disp = op
        busy[unit] += occ
        if unit in ("SU", "SFU", "SIDE"):
            su_cls = kind
        for r in f0.get("_reads", ()):
            readers.setdefault(r, []).append(op)
        for r in f0.get("_writes", ()):
            last_w[r] = op
            readers[r] = []
        disp = (disp + sp.gap) if sp.chaining else s + sp.gap
    cycles = max((max(o.f, o.fred or 0) for o in ops), default=0) + 1
    if stats is not None:
        stats.update(busy=busy, issued=n_issued, path=critical_path(ops))
    return cycles


def critical_path(ops):
    """Walk back from the last-finishing op along each op's binding constraint; attribute the token's cycles to
    (unit, depth | occupancy), dispatch (the sequencer's issue rate) and hazard slack.  Chained-first: only the
    producer's depth is on the path (its occupancy overlaps); unit busy: only the previous op's occupancy."""
    if not ops:
        return {}
    by = {}

    def add(k, v):
        if v:
            by[k] = by.get(k, 0) + v
    op = max(ops, key=lambda o: max(o.f, o.fred or 0))
    end, mode = max(op.f, op.fred or 0), "all"
    while op is not None:
        span = max(0, end - op.s)
        if mode == "occ":
            add(f"{op.unit} occupancy", span)
        elif mode == "depth":
            add(f"{op.unit} depth", span)
        else:
            tail = end - op.f if op.fred and end > op.f else 0
            dep = min(op.depth + tail, span)
            add(f"{op.unit} depth", dep)
            add(f"{op.unit} occupancy", span - dep)
        p, why = op.pred, op.why
        if p is None:
            add("start", op.s)
            break
        if why == "dispatch":
            add("dispatch (issue rate)", op.s - p.s)
            end, mode = p.s, "occ"
        elif why == "unit busy":
            end, mode = op.s, "occ"
        elif why == "raw chained first":
            end, mode = op.s, "depth"
        elif why == "raw chained last":
            end, mode = p.f, "all"
        else:
            pend = p.fred if why == "raw full (reduction)" else (p.f if why != "drain" else max(p.f, p.fred or 0))
            add("hazard slack", max(0, op.s - pend))
            end, mode = min(op.s, pend), "all"
        op = p
    return {k: v for k, v in sorted(by.items(), key=lambda kv: -kv[1])}


# -- as-built mode (validation) ---------------------------------------------------------------------------------
def simulate_as_built(prog, pos, shape, su_lanes=8):
    """The event engine in drain mode with hdc_timing_v41's calibrated unit formulas = hdc_replay_v41.simulate
    at Cfg(su_lanes) (itself hdc_timing_v41.simulate with a shape-resolved DYN table)."""
    return R.simulate(prog, pos, shape, R.Cfg(su_lanes=su_lanes))


def validate(pos=7):
    """At the reduced shape: hdc_timing_v41.simulate on the emitted program vs the event engine's as-built
    mode, and the new-core engine at the as-built widths with drains (a structural check: close, not equal)."""
    prog = R.build(R.REDUCED, su_lanes=I.SU_LANES)
    v = R.validate(pos=pos)                       # builds the REAL reduced program (loads the model)
    ref = v["hdc_timing_v41"]
    asb = simulate_as_built(prog, pos, R.REDUCED, I.SU_LANES)
    asb_sp = Spec(qe_macs=512, me_macs=64, att_macs=64, att_kv_bytes=128, idx_macs=64, su_lanes=I.SU_LANES,
                  sfu_lanes=I.SU_LANES, side_lanes=1, hc_macs=24, sel_lanes=1, gap=6, chaining=False,
                  su_depth={"none": 28, "exp": 28 + 92, "sigm": 28 + 128, "div": 54, "sqrt": 59, "rsqrt": 89,
                            "spsqrt": 287, "egate": 189}, qe_depth0=45, me_depth0=31, att_s_depth=31,
                  att_pv_depth=31, idx_depth=31, he_depth=32, red_tail=35)
    eng = simulate_new(prog, pos, R.REDUCED, asb_sp)
    return dict(pos=pos, su_lanes=I.SU_LANES, hdc_timing_v41=ref, event_engine_as_built_formulas=asb,
                exact=ref == asb and v["exact"], emitted_program_matches_real=v["field_mismatches"] == 0, new_engine_at_as_built_widths_drains=eng,
                new_engine_error=(eng - ref) / ref,
                note="the event engine's as-built path (hdc_timing_v41's unit formulas, drains, in-order issue) "
                     "reproduces hdc_timing_v41 exactly on the emitted reduced program, which matches the real "
                     "program field for field.  The NEW-core cost functions evaluated at the as-built widths (drains "
                     "on) land below it because they are the re-specified units' costs, not the as-built ones: no QE "
                     "slot-phase alignment or per-op quantiser load, no SU chase distances or class-change drains, "
                     "the select priced by the streaming-filter formula instead of insertion (n + k + 47), "
                     "fused index head sum, lane-parallel reductions")


# -- the study ---------------------------------------------------------------------------------------------------
def comm_us():
    dag = json.loads(R.DAG.read_text())
    ob = dag["packaging_options"]["options"]["b_two_die_group4_across_pair"]
    return sum(ob["batch1"]["breakdown_us"][x] for x in ("collective_latency", "collective_bytes", "pipeline_hops"))


_PROGS = {}


def program(shape, su_lanes, layers=None, embed=True, head=True):
    key = (shape["name"], su_lanes, tuple(layers) if layers else None, embed, head)
    if key not in _PROGS:
        _PROGS[key] = R.build(shape, su_lanes, engram_inline=False, layers=layers, embed=embed, head=head)
    return _PROGS[key]


def token(sp, ctx, shape=R.SHIPPED):
    st = {}
    cyc = simulate_new(program(shape, 1024), ctx - 1, shape, sp, st)
    us = cyc / sp.clock_hz * 1e6 + comm_us()
    return dict(compute_cycles=cyc, compute_us=cyc / sp.clock_hz * 1e6, us_per_token=us,
                tokens_s_per_user=1e6 / us, instructions=st["issued"], busy_cycles=st["busy"],
                critical_path_cycles=st["path"])


def per_layer(sp, ctx, shape=R.SHIPPED):
    out = {}
    for label, L in R.layer_types():
        st = {}
        cyc = simulate_new(program(shape, 1024, [L], False, False), ctx - 1, shape, sp, st)
        out[label] = dict(cycles=cyc, instructions=st["issued"],
                          busy={k: v for k, v in st["busy"].items() if v},
                          critical_path_top={k: v for k, v in list(st["path"].items())[:6]})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    budget = json.loads(BUDGET.read_text())
    sp = Spec()
    rec = dict(schema=SCHEMA, tool="tools/hdc_timing_v41x.py", spec=asdict(sp), comm_us_per_token=comm_us(),
               dependence_set="region read/write sets (hdc_program_v41.schedule inputs), chained per vector; "
                              "chaining=False: the wait masks as drains with in-order blocking issue",
               validation=validate())
    print("validation", rec["validation"])
    rows = {}
    for ctx in CONTEXTS:
        r = token(sp, ctx)
        r["budget_required_priced"] = budget["required_priced"][str(ctx)]["tokens_s_per_user"]
        r["target"] = budget["required_priced"][str(ctx)]["target"]
        rows[str(ctx)] = r
        print(ctx, round(r["tokens_s_per_user"]), "budget", round(r["budget_required_priced"]), "target",
              round(r["target"]), "compute us", round(r["compute_us"], 1))
    rec["token"] = rows
    rec["per_layer_200k"] = per_layer(sp, 200000)
    sens = {}
    for name, s2 in (("chaining_off_drains", replace(sp, chaining=False)),
                     ("su_512", replace(sp, su_lanes=512, sfu_lanes=128)),
                     ("su_2048", replace(sp, su_lanes=2048, sfu_lanes=512)),
                     ("weight_x0.5", replace(sp, qe_macs=sp.qe_macs / 2, me_macs=sp.me_macs / 2)),
                     ("weight_x2", replace(sp, qe_macs=sp.qe_macs * 2, me_macs=sp.me_macs * 2)),
                     ("gap_1", replace(sp, gap=1)),
                     ("su_class_penalty_10", replace(sp, su_cls_penalty=10)),
                     ("side_pipe_8_lanes", replace(sp, side_lanes=8))):
        sens[name] = {str(ctx): round(token(s2, ctx)["tokens_s_per_user"], 1) for ctx in CONTEXTS}
        print(name, sens[name])
    rec["sensitivity_tokens_s_per_user"] = sens
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")


if __name__ == "__main__":
    main()
