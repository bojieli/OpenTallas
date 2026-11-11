"""DIE-HBM-92-LAT 11-08: HBM asbuilt.param_regen hook (F2 of the HBM latency event; tools/die_plan/bind.py regen_params).

Every HBM fixed-latency consumer parameter is regenerated from the LANDED depths of the bound die (after the R8 / loop
pads of physical/die_plan/hbm/r8/hbm_lat_pads.py), with the ABSOLUTE law of each module (reference value at zero die
stages + the landed register stages of its own legs), never "as-built + delta": the p37 as-built leaf parameters already
carry an older plan's lane depths (LG taps 25/15/19/15 = 11 + d44v-era lanes 14/4/8/4; rootctl VM_RT 75, CR_RT 36;
n12 VM_RT_EXTRA 171), so adding today's deltas to them would double count (COORD 11-08 caution).

A leg = the crossing members (sink leaf, sink port, source leaf) named in physical/die_plan/hbm/r8/hbm_lat_contract.json;
L(leg) = landed register stages of the leg (bind boundary flops + plan lane stages + landing pads), one value per leg
(the pads guarantee it; a leg with two values is a hook error, the bind fails).

Laws (q = hub quadrant NW/NE, k = local group 0..3; N_k = L(N_rq_qk) + L(N_rr_qk) = SU LG tap <-> its VM bank pair):
  LG taps (d4g_bank_latency RULES / TAP_CHAIN; faces bank pin +1; check: LG1/LG3 today N = 2+2 reproduce as-built):
    su_qk.g_tap_r8b.u_tap, su_qk.u_slice.g_leaf[0|1].u_leaf   READ_RETURN 11 + N_k   WRITE_RETURN  8 + N_k
    sfu_qk (ot_hgi_sfu_lg_pair_tap_leaf)                        READ_RETURN 15 + N_k   WRITE_RETURN 12 + N_k
    hc_qk  (ot_hgi_sfu_lg_pair_tap_leaf_term)                    READ_RETURN 19 + N_k   WRITE_RETURN 16 + N_k
  hc_q.u_q (ot_hbm_hc_q_static header: capture 23 / done 19 at the 18/15 term tap, pair leaf +1 each way):
    RD_CAPTURE = GATHER_PHASE = 23 + (hc_qk READ_RETURN - 18) + L(H_rq_qk) + L(H_rr_qk)     (equal for every k)
    DONE_LAT                  = 19 + (hc_qk WRITE_RETURN - 15) + L(H_rq_qk) + L(H_rr_qk)    (equal for every k)
  hb_idx__ctl (rootctl_am header: VM_RT / CR_RT = extra edges outside the tile; faces-bank die master am_pin = 1 / 1):
    VM_RT = 1 + L(IDX_rq4) + L(IDX_rr4)        CR_RT = 1 + L(IDX_cq) + L(IDX_cr)
  hb_idx__op_SW (n12 behind the rootctl share: 2 shell pin flops + VM_RT + its own share legs):
    VM_RT_EXTRA = 2 + VM_RT + L(IDXQ_rq) + L(IDXQ_rr)
  hb_argmax (r2 behind the share: VMX 5 + VM_RT; ACK 13 + its own echo 1 + L(cq) + L(cr))        [CHECK: owner look]
  hc_eng (ot_hbm_hc_root_static_s SYS_LAT = .. + 1 + XRD + 1 + .. + 1 + XRU + 1):  XRD = L(HCR_xrd)  XRU = L(HCR_xru)
Core pin cycles (HBM-HUB-RTL-1 11-11, DIE-HBM-97 vecd rd1; tools/die_plan/core_pin_cycles.py): asbuilt.core_pin_cycles
names bank recipes whose own read pins answer X edges later (rd1: rr0..rr4 and pr +1; *_done / eg / requests 0).  X is
read from the bound sources of each consumer pin (default: no declaration -> X = 0, every law above unchanged):
  read laws get + X (the faces-bank read constant): su/sfu/hc tap READ_RETURN, hc_q RD_CAPTURE / GATHER_PHASE (through
  the hc tap READ_RETURN), the SFU bridge READ_RETURN (through the sfu tap), VM_RT + X(IDX_rr4) (so n12 VM_RT_EXTRA and
  argmax VMX follow), CR_RT + X(the hub's bank pr); WRITE_RETURN / DONE_LAT stay (write done pins are not moved).
  Readers with no absolute law here take as-built + X (record.core_pin_regen; latency_consumers.py checks the loop):
  dma_back RR_RT (rr), VM share BANK_RT (vm_rr) and the share's clients (n12 VM_RT_EXTRA behind hb_idx__nwsh),
  xload RD_LAT (rr; per-bank vector: every element), n12 VM_RT_EXTRA reading banks directly.
  Any other consumer of a moved pin (a cut without parameters, e.g. hb_coll_q.__cut_vm behind a share) is a hook error:
  the bind fails rather than bind a torn read.  Diagnostic status pins (bank_status) are recorded only.
  Mixed X on one law (an rd1 and a non-rd1 bank in one LG pair / one share) is an error (loop pads are not modelled).
Leaves that are netlist cuts without parameters (sfucore_q.__cut_ctl = the SFU VM bridge, sfucore_q.__cut_lane* = sp2
lane RDX) cannot take a parameter: their required values are RECORDED (record.variant_values) for the parameterized
variants DIE-HBM-92-SU builds; the bridge law is supplied by asbuilt.param_regen.bridge = {read_k, write_k} once
SU-SFU2 confirms it (see record).

    python3 hbm_param_regen.py table PLAN BUS_GROUPS LANDING ASBUILT_JSON [--json OUT]   (offline: the values on a
        landing table, as-built and the as-built + delta law side by side)
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT = HERE.parent / "r8" / "hbm_lat_contract.json"
QS, KS = ("NW", "NE"), (0, 1, 2, 3)
TAP_K = {"su": (11, 8), "sfu": (15, 12), "hc": (19, 16)}
sys.path.insert(0, str(HERE.parents[3] / "tools" / "die_plan"))
# (module regex, response port regex, parameter): fixed-latency readers without an absolute law here -> as-built + X
PIN_READERS = [(r"ot_hgi_dma_back_static_vp4_banks\w*", r"rr", "RR_RT"),
               (r"ot_hbm_idx_vm_share2_static\w*", r"vm_rr", "BANK_RT"),
               (r"ot_hgi_sm_xload\w*ctl\w*", r"rr", "RD_LAT"),
               (r"ot_hbm_idx_vm_query_static_n12", r"vm_rr", "VM_RT_EXTRA")]
SHARE = (r"ot_hbm_idx_vm_share2_static\w*", "a_rr")        # a share's answer port: its clients see the share's + X
DIAG_PORT = r"(bank_status|b\d_status|status)"            # diagnostic: recorded, never priced
LAW_PINS = [(r"su_N[EW]\d\.g_tap_r8b\.u_tap", r"near_rr"), (r"hb_idx__ctl", r"vm_rr"),
            (r"hb_vms_\w+", r"(bk|b\d)_pr")]


def legs_of(contract):
    sys.path.insert(0, str(HERE.parent / "r8"))
    import hbm_lat_pads as LP
    legs, _, _ = LP.expand(contract)
    return {n: [LP.compile_sel(s) for s in (r["sel"] if isinstance(r["sel"], list) else [r["sel"]])]
            for n, r in legs.items()}


class Landed:
    """leg -> set of landed stages; built from (sink leaf, sink port, source leaf, landed) rows"""

    def __init__(self, rows):
        self.rows = rows

    def __call__(self, sels):
        out = set()
        for snk, pn, src, d in self.rows:
            for a, b, c in sels:
                if a.fullmatch(snk) and b.fullmatch(pn) and c.fullmatch(src):
                    out.add(d)
                    break
        return out


def rows_from_binder(ctx, sinks_rx):
    import bind_position_bank as PB
    F = ctx.F
    rx = re.compile(sinks_rx)
    rows = []
    for (ci, pn, i), d in ctx.sinks.items():
        if d[0] != "x":
            continue
        path = F.cells[ci].path
        if not rx.fullmatch(path):
            continue
        landed = ctx.bitcyc[(d[1], d[6], d[2], d[3], d[4])] + (d[7] if len(d) > 7 else 0) + PB.extra(ctx, ci, pn)
        rows.append((path, pn, F.cells[d[2]].path, landed))
    return rows


def rows_from_table(bg, landing):
    sys.path.insert(0, str(HERE.parent / "r8"))
    tab = {m["id"]: m["landed"] for m in landing["members"]}
    rows = []
    for g in bg["landing"]:
        for m in g["members"]:
            sb = ",".join(f"{a}:{b}" for a, b in m["sink_bits"])
            k = f"{g['sink']}.{m['sink_port']}[{sb}]<-{m['source']}@{m.get('asbuilt_lane_stages', m['asbuilt_stages'])}"
            rows.append((g["sink"], m["sink_port"], m["source"].rpartition(".")[0], tab.get(k, m["landed_stages"])))
    return rows


def derive(L, legs, bridge=None, xr=None):
    """-> (params {leaf: {P: v}}, record, errors); xr = core pin cycles {"N_{q}{k}" | "IDX" | "CR": X} (default 0)"""
    err, rec, params, variant = [], defaultdict(dict), defaultdict(dict), {}
    xr = xr or {}

    def one(name):
        v = L(legs[name])
        if len(v) != 1:
            err.append(f"leg {name}: landed depths {sorted(v)} (one value required; R8/loop pads missing?)")
            return max(v) if v else 0
        return v.pop()
    for q in QS:
        rd_cap, done = {}, {}
        for k in KS:
            n = one(f"N_rq_{q}{k}") + one(f"N_rr_{q}{k}")
            x = xr.get(f"N_{q}{k}", 0)
            rec["N"][f"{q}{k}"] = n
            if x:
                rec["X"][f"{q}{k}"] = x
            for unit, leaves in (("su", [f"su_{q}{k}.g_tap_r8b.u_tap", f"su_{q}{k}.u_slice.g_leaf[0].u_leaf",
                                          f"su_{q}{k}.u_slice.g_leaf[1].u_leaf"]),
                                 ("sfu", [f"sfu_{q}{k}"]), ("hc", [f"hc_{q}{k}"])):
                kr, kw = TAP_K[unit]
                for leaf in leaves:
                    params[leaf].update(READ_RETURN=kr + n + x, WRITE_RETURN=kw + n)
            h = one(f"H_rq_{q}{k}") + one(f"H_rr_{q}{k}")
            rd_cap[k] = 23 + (TAP_K["hc"][0] + n + x - 18) + h
            done[k] = 19 + (TAP_K["hc"][1] + n - 15) + h
            c = one(f"C_rq_{q}{k}") + one(f"C_rr_{q}{k}")
            variant[f"sfucore_{q}.__cut_ctl:LG{k}"] = dict(sfu_tap_read_return=TAP_K["sfu"][0] + n + x,
                                                           sfu_tap_write_return=TAP_K["sfu"][1] + n, ctl_legs=c)
        for what, d in (("RD_CAPTURE", rd_cap), ("DONE_LAT", done)):
            if len(set(d.values())) != 1:
                err.append(f"hc_{q}.u_q {what}: LG round trips differ {d} (loop pads missing)")
        params[f"hc_{q}.u_q"].update(RD_CAPTURE=max(rd_cap.values()), GATHER_PHASE=max(rd_cap.values()),
                                     DONE_LAT=max(done.values()))
        if bridge:
            rr = {k: bridge["read_k"] + variant[f"sfucore_{q}.__cut_ctl:LG{k}"]["sfu_tap_read_return"]
                  + variant[f"sfucore_{q}.__cut_ctl:LG{k}"]["ctl_legs"] for k in KS}
            wr = {k: bridge["write_k"] + variant[f"sfucore_{q}.__cut_ctl:LG{k}"]["sfu_tap_write_return"]
                  + variant[f"sfucore_{q}.__cut_ctl:LG{k}"]["ctl_legs"] for k in KS}
            if len(set(rr.values())) != 1 or len(set(wr.values())) != 1:
                err.append(f"SFU bridge {q}: LG round trips differ read {rr} write {wr} (loop pads missing)")
            variant[f"sfucore_{q}.__cut_ctl"] = dict(READ_RETURN=max(rr.values()), WRITE_RETURN=max(wr.values()),
                                                     law=f"{bridge['read_k']}/{bridge['write_k']} + sfu tap + ctl legs")
    vm_rt = 1 + one("IDX_rq4") + one("IDX_rr4") + xr.get("IDX", 0)
    cr_rt = 1 + one("IDX_cq") + one("IDX_cr") + xr.get("CR", 0)
    params["hb_idx__ctl"].update(VM_RT=vm_rt, CR_RT=cr_rt)
    params["hb_idx__op_SW"].update(VM_RT_EXTRA=2 + vm_rt + one("IDXQ_rq") + one("IDXQ_rr"))
    rec["check"]["hb_argmax"] = dict(VMX=5 + vm_rt, ACK=13 + cr_rt,
                                     note="r2 behind the rootctl share (header: VMX 5+VM_RT); ACK law assumed 13 + CR_RT; "
                                          "as-built 89 / 52 do not follow 5+75 / 13+36: owner look before emitting")
    params["hc_eng"].update(XRD=one("HCR_xrd"), XRU=one("HCR_xru"))
    rec["variant_values"] = variant
    return dict(params), dict(rec), err


def pin_cycles(ctx, rules):
    """{(sink leaf, sink port): {X}} over every bound sink pin fed by a source pin core_pin_cycles names (X > 0 only),
    and {(sink leaf, sink port): {share leaf}} for the clients of the VM shares"""
    import core_pin_cycles as CPC
    F, out, clients = ctx.F, defaultdict(set), defaultdict(set)
    share_rx = re.compile(SHARE[0])
    for (ci, pn, i), d in ctx.sinks.items():
        s = CPC.source_of(d)
        if s is None:
            continue
        sc = F.cells[s[0]]
        x = CPC.added(rules, sc.path, sc.module, s[1], s[2])
        if x:
            out[(F.cells[ci].path, pn)].add(x)
        elif s[1] == SHARE[1] and share_rx.fullmatch(sc.module or ""):
            clients[(F.cells[ci].path, pn)].add(sc.path)
    return out, clients


def pin_plan(ctx, px, clients, params):
    """-> (xr for derive, [core_pin_regen rows], {"leaf|port": X} record, errors)"""
    import core_pin_cycles as CPC
    err, xr, regen_rows, seen = [], {}, [], set()
    cells = {c.path: c for c in ctx.F.cells}

    def single(key, xs):
        if len(xs) != 1:
            err.append(f"core pin cycles {key}: sources answer {sorted(xs)} edges late (mixed rd1 / non-rd1 banks; "
                       "loop pads not modelled)")
        return max(xs)

    def law(snk, prt):
        hit = {(s, p) for (s, p) in px if re.fullmatch(snk, s) and re.fullmatch(prt, p)}
        seen.update(hit)
        return {x for k in hit for x in px[k]}
    for q in QS:
        for k in KS:
            xs = law(rf"su_{q}{k}\.g_tap_r8b\.u_tap", "near_rr")
            if xs:
                xr[f"N_{q}{k}"] = single(f"su_{q}{k} near_rr", xs)
    xs = law(r"hb_idx__ctl", "vm_rr")
    if xs:
        xr["IDX"] = single("hb_idx__ctl vm_rr", xs)
    xs = law(r"hb_vms_SW", r"(bk|b\d)_pr")
    if xs:
        xr["CR"] = single("hb_vms_SW pr (CR_RT)", xs)
    law(r"hb_vms_\w+", r"(bk|b\d)_pr")             # other hubs: the response calendar (compiler) moves, recorded
    share_x = {}
    for (s, p), xs in sorted(px.items()) + sorted((k, {max(px.get((sh, "vm_rr"), {0})) for sh in v} - {0})
                                                   for k, v in clients.items()):
        if (s, p) in seen or not xs:
            continue
        c = cells.get(s)
        if re.fullmatch(DIAG_PORT, p):
            seen.add((s, p))
            continue
        for mrx, prx, par in PIN_READERS:
            if c is not None and re.fullmatch(mrx, c.module or "") and re.fullmatch(prx, p):
                x = single(f"{s} {p}", xs)
                seen.add((s, p))
                if s in params and par in params[s]:
                    break                          # an absolute law already carries it (VM_RT behind hb_idx__ctl)
                try:
                    asb = int(str(c.params.get(par)).strip('"').replace("64'd", "").replace("'d", ""))
                except ValueError:
                    err.append(f"core pin cycles {s}.{par}: as-built value {c.params.get(par)!r} not an integer")
                    break
                v = CPC.plus(asb, x, par)
                params[s][par] = v
                regen_rows.append(dict(inst=s, param=par, asbuilt=asb, pin=x, bound=v))
                if re.fullmatch(SHARE[0], c.module or ""):
                    share_x[s] = x
                break
        else:
            err.append(f"core pin cycles: {s}.{p} ({c.module if c else '?'}) reads a moved bank pin (+{sorted(xs)}) and "
                       "has no regenerable parameter (cut / unlisted reader)")
    rec = {f"{s}|{p}": max(xs) for (s, p), xs in px.items()}
    return xr, regen_rows, rec, err


def regen(ctx):
    """bind.py asbuilt.param_regen hook"""
    spec = ctx.ab.get("param_regen", {})
    contract = json.loads(Path(spec.get("contract", CONTRACT)).read_text()) if not isinstance(spec.get("contract"), dict) \
        else spec["contract"]
    legs = legs_of(contract)
    rows = rows_from_binder(ctx, r"(vmb_\w+|su_N[EW]\d\.g_tap_r8b\.u_tap|sfu_N[EW]\d|hc_N[EW]\d?(\.u_q|\.u_cen\..*)?|"
                                 r"sfucore_N[EW]\.__cut_ctl|hb_idx__ctl|hb_idx__op_SW|hb_vms_SW|hb_argmax|hc_eng|"
                                 r"hb_router_ids)")
    import core_pin_cycles as CPC
    rules = CPC.load(ctx.ab, Path(getattr(ctx, "base", CPC.REPO)))
    px, clients = pin_cycles(ctx, rules) if rules else ({}, {})
    xr = {}
    if px:
        # pass 1: the absolute-law X; pass 2 (after derive) the as-built + X readers
        xr, _, _, _ = pin_plan(ctx, px, clients, defaultdict(dict))
    params, rec, err = derive(Landed(rows), legs, spec.get("bridge"), xr)
    if px:
        params = defaultdict(dict, params)
        _, regen_rows, pin_rec, perr = pin_plan(ctx, px, clients, params)
        err += perr
        rec.update(core_pin_cycles=pin_rec, core_pin_regen=regen_rows,
                   core_pin_rules=[r["src"] for r in rules])
    if err:
        raise ValueError("; ".join(err[:6]))
    # The exact native composed cut variant exposes its intrinsic boundary
    # contract. Old nonparameterized cuts remain recorded, never guessed.
    modules = {cell.path: cell.module for cell in ctx.F.cells}
    for q in QS:
        leaf = f"sfucore_{q}.__cut_ctl"
        if modules.get(leaf) == "ot_hgi_sfu_sp2_ctl":
            values = rec["variant_values"].get(leaf)
            if values is None:
                raise ValueError(f"{leaf}: explicit retained-edge bridge contract required")
            params[leaf] = dict(SFU_READ_RETURN=values["READ_RETURN"],
                                SFU_WRITE_RETURN=values["WRITE_RETURN"])
    return dict(params=params, record=dict(rule=__doc__.split("\n\n")[2], contract=contract.get("name"), **rec))


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("table")
    t.add_argument("bus_groups")
    t.add_argument("landing")
    t.add_argument("asbuilt_json")
    t.add_argument("--contract", default=str(CONTRACT))
    t.add_argument("--bridge", help="read_k,write_k of the SFU bridge law")
    t.add_argument("--json")
    t.add_argument("--tools", default=str(HERE.parents[3] / "tools" / "die_plan"))
    a = ap.parse_args(argv)
    bg = json.loads(Path(a.bus_groups).read_text())
    landing = json.loads(Path(a.landing).read_text())
    legs = legs_of(json.loads(Path(a.contract).read_text()))
    br = dict(zip(("read_k", "write_k"), map(int, a.bridge.split(",")))) if a.bridge else None
    params, rec, err = derive(Landed(rows_from_table(bg, landing)), legs, br)
    sys.path.insert(0, a.tools)
    import latency_consumers as LC
    leaves = LC.yosys_leaves(json.loads(Path(a.asbuilt_json).read_text()))
    asb = lambda leaf, p: leaves.get(leaf, {}).get("params", {}).get(p)
    rows = []
    for leaf, ps in sorted(params.items()):
        for p, v in sorted(ps.items()):
            rows.append(dict(inst=leaf, param=p, asbuilt=asb(leaf, p), regen=v))
            print(f"{leaf:40s} {p:14s} as-built {asb(leaf, p)!s:>5}  regen {v}")
    for k, v in rec.get("variant_values", {}).items():
        print(f"VARIANT {k} {v}")
    for k, v in rec.get("check", {}).items():
        print(f"CHECK {k} {v}")
    for e in err:
        print("ERROR", e)
    if a.json:
        Path(a.json).write_text(json.dumps(dict(rows=rows, record=rec, errors=err), indent=1) + "\n")
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
