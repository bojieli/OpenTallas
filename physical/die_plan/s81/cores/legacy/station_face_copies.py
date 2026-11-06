#!/usr/bin/env python3
"""Registered-face re-cut of a native (mapped gate netlist) station split, zero added cycles (S81-T51-RECUT, COORD 10:2x (1)).

    python3 -I station_face_copies.py apply SPLIT.json --top MOD --pose CHILD=POSE.tcl ... --out DIR
    python3 -I station_face_copies.py check SPLIT.json DIR/split_fc.json DIR/face_copies.json

Input is the yosys JSON of the split (parent + child modules; s81_station_hierarchy_split.py + clean_abi.py), whose
identity vs the unsplit source is already certified (conservation_clean.json).  Per child, every signal port is
classified exactly as tools/die_plan/face_guard.py will (buffers / inverters are transparent):

  output ports
    * dedicated   driver chain = FF Q/QN -> single-fanout buffers/inverters -> port only: unchanged;
    * shared      the chain's FF (or a chain net) also has local loads: a DEDICATED FACE COPY is made (spec item 2):
                  a new FF of the same master on the same D and CLK bits (and any other input pin), plus a copy of
                  each buffer / inverter of the chain; the copy chain drives the port bit only, the original keeps
                  every local load.  Same function every cycle (identical register), 0 added cycles, no new port.
  input ports (never changed; declared for the kit)
    * capture     single load chain to one FF D: unchanged;
    * pair        that FF's output chain drives exactly one output port and nothing else: a one-station pair
                  (recipe ft1_pairs; face_guard verifies it bit by bit);
    * land        exactly 4 loads, all inside one u_cland_ft<N>_i / u_cland_monitor_<N> landing (the ring write
                  slots): recipe land_slots {D: 4, form: hold_mux}; face_guard proves each slot equation;
    * reset       driven (in the other child, through the parent) by a reset relay FF (u_rrl_* / u_rst_in):
                  the core reset_ports contract (synchronous input timed under the IO budget, gen_phys.core_reset_sdc);
    * status      loads only cells of u_cland_collect_* (the collector ready/fault ANDs): declared with the resets
                  (COORD 10:2x (1): collect ANDs declared, no added cycle);
    anything else is refused (exit 1).
Pose: each copy FF gets the nearest free site in its original's row (same orientation), so the reviewed native pose
(gen_core_kit_legacy native_ff_pose) declares every FF incl. the copies.

check: removes each copy (and its chain), reconnects the port bit to the original chain net, and requires the result to
be connection-identical to the input split (so the source conservation receipt carries over), and every copy to be a
structurally identical register (same type / parameters / every input bit) of its original."""
import argparse
import collections
import copy as _copy
import hashlib
import json
import re
import sys
from pathlib import Path

FF_RE = re.compile(r"DFF", re.I)
BUF_RE = re.compile(r"^(BUF|INV|HB)", re.I)
RESET_SRC = re.compile(r"^u_bound\.(u_rrl_\d+(?:_t)?|u_rst_in)/")
LAND_GRP = re.compile(r"^u_bound\.(u_cland_ft\d+_i|u_cland_monitor_\d+)/")
STATUS_GRP = re.compile(r"^u_bound\.u_cland_collect_[A-Za-z0-9_]+/")
RESET_TOP_PORTS = ("arst_n", "rst_n")     # the unsplit type's own reset inputs (face_guard SKIP_RE class)
SITE_W = 0.054


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Net:
    """driver / loads of one module's bits (port bits count: input port = driver, output port = load)."""

    def __init__(self, m):
        self.m = m
        self.drv, self.lds = {}, collections.defaultdict(list)
        for n, c in m["cells"].items():
            for p, bits in c["connections"].items():
                out = c["port_directions"][p] == "output"
                for b in bits:
                    if isinstance(b, str):
                        continue
                    if out:
                        if b in self.drv:
                            raise ValueError(f"multi-driven bit {b}")
                        self.drv[b] = (n, p)
                    else:
                        self.lds[b].append((n, p))
        for p, v in m["ports"].items():
            for b in v["bits"]:
                if isinstance(b, str):
                    continue
                if v["direction"] == "input":
                    self.drv[b] = ("<port>", p)
                else:
                    self.lds[b].append(("<port>", p))

    def ctype(self, n):
        return self.m["cells"][n]["type"]

    def ins(self, n):
        c = self.m["cells"][n]
        return [(p, bits) for p, bits in c["connections"].items() if c["port_directions"][p] != "output"]

    def outs(self, n):
        c = self.m["cells"][n]
        return [(p, bits) for p, bits in c["connections"].items() if c["port_directions"][p] == "output"]


def out_chain(N, bit):
    """port bit -> [(net bit, extra local loads)] back to the driving FF; (ff, chain_cells, shared, why)."""
    chain, shared, cur = [], False, bit
    first, chain_next = True, None
    while True:
        d = N.drv.get(cur)
        if d is None:
            return None, chain, shared, "undriven"
        if first:
            extra = [x for x in N.lds[cur] if x[0] != "<port>"]
            if len([x for x in N.lds[cur] if x[0] == "<port>"]) != 1:
                return None, chain, shared, "net drives several ports"
        else:
            extra = [x for x in N.lds[cur] if x != chain_next]
        if extra:
            shared = True
        n, p = d
        if n == "<port>":
            return None, chain, shared, "feedthrough"
        t = N.ctype(n)
        if FF_RE.search(t):
            return n, chain, shared, None
        if not BUF_RE.match(t):
            return None, chain, shared, f"driven by {t} {n}"
        ins = N.ins(n)
        if len(ins) != 1 or len(ins[0][1]) != 1:
            return None, chain, shared, f"buffer pins {n}"
        chain.append(n)
        chain_next = (n, ins[0][0])
        cur = ins[0][1][0]
        first = False


def in_chain(N, bit):
    """input port bit -> (kind, ff or None, loads at the first fanout net)."""
    cur = bit
    while True:
        ld = N.lds[cur]
        if len(ld) != 1:
            return "fanout", None, ld
        n, p = ld[0]
        if n == "<port>":
            return "feedthrough", None, ld
        t = N.ctype(n)
        if FF_RE.search(t):
            return ("capture" if p == "D" else "ffpin"), n, ld
        if not BUF_RE.match(t):
            return "logic", None, ld
        cur = N.outs(n)[0][1][0]


def parent_sources(split, top, child_modules):
    """{(child module, input port): (driver child module, its output port)} through the parent's bits / buffers."""
    P = split["modules"][top]
    PN = Net(P)
    inst = {c["type"]: (n, c) for n, c in P["cells"].items() if c["type"] in child_modules}
    src = {}
    for cm, (n, c) in inst.items():
        mod = split["modules"][cm]
        for p, v in mod["ports"].items():
            if v["direction"] != "input":
                continue
            b = c["connections"][p][0]
            hops = 0
            while True:
                d = PN.drv.get(b)
                if d is None or d[0] == "<port>":
                    src[(cm, p)] = ("<parent-port>", d[1] if d else None)
                    break
                dn, dp = d
                dc = P["cells"][dn]
                if dc["type"] in child_modules:
                    src[(cm, p)] = (dc["type"], dp)
                    break
                if BUF_RE.match(dc["type"]) and hops < 8:
                    ins = [bits for q, bits in dc["connections"].items() if dc["port_directions"][q] != "output"]
                    b = ins[0][0]
                    hops += 1
                    continue
                src[(cm, p)] = ("<parent-logic>", dn)
                break
    return src


def is_clock_port(name, abi):
    return abi.get(name, {}).get("kind") == "clock" or not re.fullmatch(r"p\d{5}", name)


def classify(split, top, child_modules, abi):
    src = parent_sources(split, top, child_modules)
    out = {}
    nets = {cm: Net(split["modules"][cm]) for cm in child_modules}
    for cm in child_modules:
        N = nets[cm]
        mod = split["modules"][cm]
        res = dict(copies=[], dedicated=0, capture=0, pairs=[], land=[], reset=[], status=[], refused=[])
        out_ff = {}
        for p, v in sorted(mod["ports"].items()):
            if is_clock_port(p, abi.get(cm, {})) or v["direction"] != "output":
                continue
            ff, chain, shared, why = out_chain(N, v["bits"][0])
            if why:
                res["refused"].append(f"{p}: output {why}")
                continue
            out_ff[p] = ff
            if shared:
                res["copies"].append(dict(port=p, ff=ff, chain=chain))
            else:
                res["dedicated"] += 1
        ff_out_ports = collections.defaultdict(list)
        for p, ff in out_ff.items():
            ff_out_ports[ff].append(p)
        copied = {c["port"] for c in res["copies"]}
        for p, v in sorted(mod["ports"].items()):
            if is_clock_port(p, abi.get(cm, {})) or v["direction"] != "input":
                continue
            kind, ff, ld = in_chain(N, v["bits"][0])
            s = src.get((cm, p), (None, None))
            sff = None
            if s[0] in child_modules:
                o = split["modules"][s[0]]["ports"][s[1]]["bits"][0]
                sff = out_chain(nets[s[0]], o)[0]
            if kind == "capture":
                outs = ff_out_ports.get(ff, [])
                if len(outs) == 1 and outs[0] not in copied:
                    res["pairs"].append([p, outs[0]])
                else:
                    res["capture"] += 1
                continue
            if (sff and RESET_SRC.match(sff)) or (s[0] == "<parent-port>" and s[1] in RESET_TOP_PORTS):
                res["reset"].append(dict(port=p, source=f"{s[0]}.{s[1]}", source_ff=sff, loads=len(ld)))
                continue
            names = [n for n, _ in ld]
            if kind == "fanout" and len(ld) == 4 and len({LAND_GRP.match(n)[1] if LAND_GRP.match(n) else None
                                                          for n in names}) == 1 and LAND_GRP.match(names[0]):
                res["land"].append(p)
                continue
            if all(STATUS_GRP.match(n) for n in names) and names:
                res["status"].append(dict(port=p, source=f"{s[0]}.{s[1]}", source_ff=sff, loads=names))
                continue
            res["refused"].append(f"{p}: input {kind} loads {names[:4]} source {s} ff {sff}")
        out[cm] = res
    return out


def dead_ffs(m):
    """FFs whose forward comb cone reaches no port and no live FF (fixpoint): ORFS synth (eliminate_dead_logic) removes
    exactly these, so the pose must not demand them (t51: W 24 / E 39 reset relay leaves, matched 1:1 against 1_synth.v).
    A child-dead FF is dead in the unsplit type too: every crossing is a port."""
    N = Net(m)
    reach = {}
    for n, c in m["cells"].items():
        if not FF_RE.search(c["type"]):
            continue
        seen, st, port, tgt = set(), [b for _, bb in N.outs(n) for b in bb], False, set()
        while st:
            b = st.pop()
            if isinstance(b, str) or b in seen:
                continue
            seen.add(b)
            for ln, _ in N.lds[b]:
                if ln == "<port>":
                    port = True
                elif FF_RE.search(N.ctype(ln)):
                    tgt.add(ln)
                else:
                    st += [x for _, bb in N.outs(ln) for x in bb]
        reach[n] = (port, tgt)
    live = {n for n, (p, _) in reach.items() if p}
    grew = True
    while grew:
        grew = False
        for n, (_, t) in reach.items():
            if n not in live and t & live:
                live.add(n)
                grew = True
    return sorted(set(reach) - live)


def read_blockages(path):
    """lines 'name x0 y0 x1 y1' (um): the floorplan's fixed non-FF cells (tapcells, row-end cells) of the kit."""
    out = []
    for ln in Path(path).read_text().split("\n"):
        if ln.strip():
            n, a, b, c, d = ln.rsplit(None, 4)
            out.append((n, float(a), float(b), float(c), float(d)))
    return out


def legalize(sites, blockages):
    """move every posed FF that overlaps a blockage or an earlier posed FF of its row to the nearest free site of the
    SAME row (orientation kept), inside the row's [first, last] blockage span (row-end cells); returns moves."""
    rows = collections.defaultdict(list)
    for _, x0, y0, x1, y1 in blockages:
        rows[round(y0, 4)].append((x0, x1))
    moves = []
    occ = collections.defaultdict(list)
    for name in sorted(sites, key=lambda n: (sites[n][1], sites[n][0], n)):
        x, y, w, h, o, m = sites[name]
        ry = round(y, 4)
        blk = rows.get(ry, [])
        lo = min((a for a, _ in blk), default=None)
        hi = max((b for _, b in blk), default=None)

        def free(nx):
            if lo is not None and (nx < lo - 1e-6 or nx + w > hi + 1e-6):
                return False
            return all(nx + w <= a + 1e-6 or nx >= b - 1e-6 for a, b in blk) and \
                all(nx + w <= a + 1e-6 or nx >= b - 1e-6 for a, b in occ[ry])
        nx = x
        if not free(x):
            for k in range(1, 20000):
                hit = [c for c in (round(x + k * SITE_W, 6), round(x - k * SITE_W, 6)) if free(c)]
                if hit:
                    nx = hit[0]
                    break
            else:
                raise ValueError(f"no legal site for {name} near {x} {y}")
            moves.append((name, round(nx - x, 4)))
            sites[name] = (nx, y, w, h, o, m)
        occ[ry].append((nx, nx + w))
    return moves


def read_pose(path):
    t = Path(path).read_text()
    ent = re.findall(r"^ \{(.+?)\} \{([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) (\S+) (\S+)\} \\$", t, re.M)
    return t, {n: (float(x), float(y), float(w), float(h), o, m) for n, x, y, w, h, o, m in ent}


def free_site(sites, x, y, w, h):
    """nearest same-row x (site grid) whose [x, x+w) overlaps no posed FF of that row."""
    row = [(sx, sx + sw) for sx, sy, sw, sh, _, _ in sites.values() if abs(sy - y) < 1e-6]
    for k in range(1, 4000):
        for dx in (k * SITE_W, -k * SITE_W):
            nx = round(x + dx, 6)
            if nx < 0:
                continue
            if all(nx + w <= a + 1e-6 or nx >= b - 1e-6 for a, b in row):
                return nx
    raise ValueError(f"no free site near {x} {y}")


def apply(split, top, child_modules, abi, poses, blockages=None):
    cls = classify(split, top, child_modules, abi)
    bad = {cm: r["refused"] for cm, r in cls.items() if r["refused"]}
    if bad:
        raise SystemExit("REFUSED " + json.dumps(bad, indent=1)[:4000])
    new = _copy.deepcopy(split)
    nb = 1 + max([b for m in split["modules"].values() for v in m.get("netnames", {}).values()
                  for b in v["bits"] if isinstance(b, int)]
                 + [b for m in split["modules"].values() for c in m.get("cells", {}).values()
                    for bits in c["connections"].values() for b in bits if isinstance(b, int)]
                 + [b for m in split["modules"].values() for v in m.get("ports", {}).values()
                    for b in v["bits"] if isinstance(b, int)])
    pose_out, record, record_dead = {}, {}, {}
    for cm in child_modules:
        mod = new["modules"][cm]
        text, sites = read_pose(poses[cm])
        added = []
        recs = []
        for c in cls[cm]["copies"]:
            p, ff, chain = c["port"], c["ff"], c["chain"]
            port_bit = mod["ports"][p]["bits"][0]
            cells = [ff] + list(reversed(chain))       # FF first, then buffers/inverters toward the port
            prev_out, names = None, []
            for i, n in enumerate(cells):
                src = mod["cells"][n]
                cn = f"{n}__fc_{p}"
                if cn in mod["cells"]:
                    raise ValueError("copy name collision " + cn)
                cc = _copy.deepcopy(src)
                cc.setdefault("attributes", {})["keep"] = "00000000000000000000000000000001"
                cc["attributes"]["ot_face_copy_of"] = n
                for q, bits in cc["connections"].items():
                    if cc["port_directions"][q] == "output":
                        if i == len(cells) - 1:
                            cc["connections"][q] = [port_bit]
                        else:
                            cc["connections"][q] = [nb]
                            nb += 1
                for q, bits in cc["connections"].items():          # chain input = previous copy's output
                    if i and cc["port_directions"][q] != "output":
                        cc["connections"][q] = [prev_out]
                prev_out = [b for q, b in cc["connections"].items() if cc["port_directions"][q] == "output"][0][0]
                mod["cells"][cn] = cc
                names.append(cn)
            # the original chain's last net keeps its local loads on a fresh bit; the port bit is the copy's only
            last = mod["cells"][cells[-1]]
            keep_bit = nb
            nb += 1
            for q, bits in last["connections"].items():
                if last["port_directions"][q] == "output":
                    last["connections"][q] = [keep_bit if b == port_bit else b for b in bits]
            for n2, c2 in mod["cells"].items():
                if n2 in names:
                    continue
                for q, bits in c2["connections"].items():
                    if c2["port_directions"][q] != "output" and port_bit in bits:
                        c2["connections"][q] = [keep_bit if b == port_bit else b for b in bits]
            mod["netnames"][f"{p}__local"] = dict(hide_name=0, bits=[keep_bit], attributes={})
            for k, cn in enumerate(names[1:], 1):
                ob = [b for q, b in mod["cells"][cn]["connections"].items()
                      if mod["cells"][cn]["port_directions"][q] == "output"][0][0]
                if ob != port_bit:
                    mod["netnames"][f"{p}__fc_n{k}"] = dict(hide_name=0, bits=[ob], attributes={})
            fo = [b for q, b in mod["cells"][names[0]]["connections"].items()
                  if mod["cells"][names[0]]["port_directions"][q] == "output"][0][0]
            if fo != port_bit:
                mod["netnames"][f"{p}__fc_q"] = dict(hide_name=0, bits=[fo], attributes={})
            if ff not in sites:
                raise ValueError(f"copied FF {ff} not in the pose")
            x, y, w, h, o, m = sites[ff]
            nx = free_site(sites, x, y, w, h)
            sites[names[0]] = (nx, y, w, h, o, m)
            added.append((names[0], (nx, y, w, h, o, m)))
            recs.append(dict(port=p, original=ff, copy=names[0], chain=chain, chain_copies=names[1:],
                             site=[nx, y], original_site=[x, y], dx_um=round(nx - x, 4)))
        # pose: append the copies to the reviewed dict (same fail-closed guards; count rises by the copies)
        lines = "".join(f" {{{n}}} {{{x:.6f} {y:.6f} {w:.6f} {h:.6f} {o} {m}}} \\\n" for n, (x, y, w, h, o, m) in added)
        anchor = "\n]\nset ot_np_blk"
        if text.count(anchor) != 1:
            raise ValueError("pose dict anchor changed")
        pose_out[cm] = text.replace(anchor, "\n" + lines.rstrip("\n").rstrip() + "\n]\nset ot_np_blk", 1) if lines else text
        pose_out[cm] = pose_out[cm].replace(" \\\n\n", " \\\n")
        # legal sites: the reviewed pose was made without the kit's tapcell / row-end cells (LOCKED at floorplan), so
        # LOCKED-on-LOCKED overlaps would stop DPL; each overlapping FF moves to the nearest free site of its own row
        legal_moves = []
        if blockages and blockages.get(cm):
            dead_now = set(dead_ffs(mod))
            live_sites = {n: v for n, v in sites.items() if n not in dead_now}
            legal_moves = legalize(live_sites, read_blockages(blockages[cm]))
            mv = dict(legal_moves)
            out_lines = []
            for ln in pose_out[cm].split("\n"):
                mm = re.match(r"^ \{(.+?)\} \{([0-9.]+) ", ln)
                if mm and mm.group(1) in mv:
                    x, y, w, h, o, m = live_sites[mm.group(1)]
                    ln = f" {{{mm.group(1)}}} {{{x:.6f} {y:.6f} {w:.6f} {h:.6f} {o} {m}}} \\"
                out_lines.append(ln)
            pose_out[cm] = "\n".join(out_lines)
            for r in recs:
                r["site"] = [live_sites[r["copy"]][0], r["site"][1]]
                r["dx_um"] = round(r["site"][0] - r["original_site"][0], 4)
        # dead FFs leave the pose (synth removes them; the pose's missing-FF guard stays exact for every live FF);
        # the kit's own face capture flops ot_fcap_* (unused-input pin registers, core_face_post_synth.tcl, FIRM at the
        # pin by face_flops.tcl) are not source FFs: the undeclared-FF guard skips that one name class only
        dead = dead_ffs(mod)
        dset = set(dead)
        keep_lines = []
        for ln in pose_out[cm].split("\n"):
            mm = re.match(r"^ \{(.+?)\} \{", ln)
            if mm and mm.group(1) in dset:
                continue
            keep_lines.append(ln)
        if len(keep_lines) != len(pose_out[cm].split("\n")) - len(dead):
            raise ValueError(f"{cm}: dead FF not found in the pose")
        pose_out[cm] = "\n".join(keep_lines)
        g_old = "if {[string match *DFF* [[$ot_np_i getMaster] getName]]} {error \"NATIVE_POSE undeclared source FF"
        g_new = ("if {[string match *DFF* [[$ot_np_i getMaster] getName]] && ![string match ot_fcap_* $ot_np_nm]} "
                 "{error \"NATIVE_POSE undeclared source FF")
        if pose_out[cm].count(g_old) != 1:
            raise ValueError("pose undeclared-FF guard changed")
        pose_out[cm] = pose_out[cm].replace(g_old, g_new)
        record_dead[cm] = dead
        # the pose runs after face_flops.tcl, which made face-register FFs FIRM: odb refuses moving a FIRM instance
        # (ODB-0359/0360), so release to PLACED, move, then lock
        m_old = " $ot_np_i setOrient $o\n"
        if pose_out[cm].count(m_old) != 1:
            raise ValueError("pose move line changed")
        pose_out[cm] = pose_out[cm].replace(m_old, " $ot_np_i setPlacementStatus PLACED\n" + m_old)
        # odb has no status FIXED ("ValueError Unknown placement status" at global_place); LOCKED = DEF FIXED
        pose_out[cm] = pose_out[cm].replace("setPlacementStatus FIXED", "setPlacementStatus LOCKED").replace(
            "# Uses FIXED status", "# Uses LOCKED (= DEF FIXED) status")
        # pin contract names every child port as a scalar (pins.json / io.tcl findBTerm {fclk_in_ft13_i}); a 1-bit port
        # tagged single_bit_vector is written "[0:0]" and becomes BTerm "fclk_in_ft13_i[0]" (floorplan: native multiPORT
        # BTerm missing).  Drop the tag on 1-bit port nets: same bit, same connections, scalar declaration.
        scalar = []
        for pn, pv in mod["ports"].items():
            nn = mod["netnames"].get(pn)
            if len(pv["bits"]) == 1 and nn and nn.get("attributes", {}).pop("single_bit_vector", None) is not None:
                scalar.append(pn)
        record[cm] = dict(copies=recs, scalar_ports=sorted(scalar), dead_ffs_not_posed=record_dead[cm],
                          legalized=dict(blockages=str(blockages.get(cm)) if blockages else None,
                                         blockages_sha256=sha(blockages[cm]) if blockages and blockages.get(cm) else None,
                                         moved=len(legal_moves),
                                         max_abs_dx_um=max((abs(d) for _, d in legal_moves), default=0.0),
                                         moves=legal_moves))
    # second pass on the transformed netlist: every output is now dedicated; inputs are declared from what the kit sees
    # (a copied relay that is also an input face register makes its capture input fan out: it is a reset input)
    cls2 = classify(new, top, child_modules, abi)
    for cm in child_modules:
        c2 = cls2[cm]
        if c2["refused"] or c2["copies"]:
            raise SystemExit(f"REFUSED after copies {cm}: {c2['refused'][:5]} shared outputs {len(c2['copies'])}")
        record[cm].update(dedicated_outputs=c2["dedicated"], capture_inputs=c2["capture"],
                          ft1_pairs=c2["pairs"], land_slots=c2["land"],
                          reset_ports=[r["port"] for r in c2["reset"]] + [r["port"] for r in c2["status"]],
                          reset_detail=c2["reset"], status_detail=c2["status"])
    return new, pose_out, record


def _outbit(c):
    return [b for q, b in c["connections"].items() if c["port_directions"][q] == "output"][0][0]


def check(orig, new, record):
    """un-replicate new -> must equal orig connection for connection; copies identical registers of originals."""
    work = _copy.deepcopy(new)
    for cm, rec in record.items():
        om, m = orig["modules"][cm], work["modules"][cm]
        for r in rec["copies"]:
            names = [r["copy"]] + r["chain_copies"]
            orig_cells = [r["original"]] + list(reversed(r["chain"]))
            prev = None
            for cn, on in zip(names, orig_cells):
                a, b = m["cells"][cn], m["cells"][on]
                if a["type"] != b["type"] or a.get("parameters", {}) != b.get("parameters", {}):
                    raise ValueError(f"copy {cn} type/params differ from {on}")
                for q, bits in a["connections"].items():
                    if a["port_directions"][q] == "output":
                        continue
                    if prev is None and bits != b["connections"][q]:
                        raise ValueError(f"copy {cn}.{q} not on the original's bit")
                    if prev is not None and bits != [prev]:
                        raise ValueError(f"copy chain {cn}.{q} not fed by the previous copy")
                prev = _outbit(a)
            port_bit = m["ports"][r["port"]]["bits"][0]
            if prev != port_bit:
                raise ValueError(f"copy chain of {r['port']} does not end at the port bit")
            users = [n for n, c in m["cells"].items() for q, bits in c["connections"].items()
                     if c["port_directions"][q] != "output" and port_bit in bits and n not in names]
            if users:
                raise ValueError(f"port {r['port']} bit has other loads {users[:3]}")
            keep_bit = _outbit(m["cells"][orig_cells[-1]])
            for cn in names:
                del m["cells"][cn]
            for n, c in m["cells"].items():
                for q, bits in c["connections"].items():
                    c["connections"][q] = [port_bit if x == keep_bit else x for x in bits]
        if set(m["cells"]) != set(om["cells"]):
            raise ValueError(f"{cm}: cell inventory differs after removing copies")
        for n, c in m["cells"].items():
            o = om["cells"][n]
            if c["type"] != o["type"] or c["connections"] != o["connections"]:
                raise ValueError(f"{cm}: cell {n} differs after removing copies")
            if {k: v for k, v in c.get("attributes", {}).items()} != o.get("attributes", {}):
                raise ValueError(f"{cm}: cell {n} attributes differ")
        if {p: v["bits"] for p, v in m["ports"].items()} != {p: v["bits"] for p, v in om["ports"].items()}:
            raise ValueError(f"{cm}: ports differ")
    for mn in orig["modules"]:
        if mn in record:
            continue
        if json.dumps(orig["modules"][mn], sort_keys=True) != json.dumps(work["modules"][mn], sort_keys=True):
            raise ValueError(f"module {mn} changed")
    return dict(verdict="PASS", copies={cm: len(r["copies"]) for cm, r in record.items()})


def ff_count(split, mn):
    return sum(1 for c in split["modules"][mn]["cells"].values() if FF_RE.search(c["type"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("apply")
    a.add_argument("split"); a.add_argument("--top", required=True); a.add_argument("--abi", required=True)
    a.add_argument("--pose", action="append", default=[], help="CHILD_MODULE=pose.tcl")
    a.add_argument("--blockages", action="append", default=[],
                   help="CHILD_MODULE=fixed.txt (floorplan LOCKED non-FF cells, 'name x0 y0 x1 y1' um): legalize the pose")
    a.add_argument("--out", required=True)
    c = sub.add_parser("check")
    c.add_argument("orig"); c.add_argument("new"); c.add_argument("record")
    args = ap.parse_args(argv)
    if args.cmd == "apply":
        split = json.loads(Path(args.split).read_text())
        abi_doc = json.loads(Path(args.abi).read_text())["children"]
        poses = dict(x.split("=", 1) for x in args.pose)
        child_modules = sorted(poses)
        abi = {f"{args.top}_{k}": v for k, v in abi_doc.items()}
        blk = dict(x.split("=", 1) for x in args.blockages)
        new, pose_out, record = apply(split, args.top, child_modules, abi, poses, blk)
        out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
        (out / "split_fc.json").write_text(json.dumps(new) + "\n")
        summary = {}
        for cm in child_modules:
            pf = out / Path(poses[cm]).name
            pf.write_text(pose_out[cm])
            summary[cm] = dict(ffs_before=ff_count(split, cm), ffs_after=ff_count(new, cm),
                               cells_after=len(new["modules"][cm]["cells"]), pose=str(pf), pose_sha256=sha(pf),
                               copies=len(record[cm]["copies"]), land=len(record[cm]["land_slots"]),
                               pairs=len(record[cm]["ft1_pairs"]), reset_ports=len(record[cm]["reset_ports"]))
        rec = dict(schema="opentallas.s81.station_face_copies.v1", split=args.split, split_sha256=sha(args.split),
                   cycles_added=0, summary=summary, children=record)
        (out / "face_copies.json").write_text(json.dumps(rec, indent=1) + "\n")
        print(json.dumps(summary, indent=1))
    else:
        rec = json.loads(Path(args.record).read_text())
        r = check(json.loads(Path(args.orig).read_text()), json.loads(Path(args.new).read_text()), rec["children"])
        print(json.dumps(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
