"""Opt-in real clock-region landings for the as-built binder.

The regional clock report's table identifies PHYSICAL port hops, not lane
endpoints. This adapter puts the landing inside the receiving partition, exports
the sender clock beside its bus, and exposes ready/fault (never dropped). It
requires declared clock/status pins and uniform type masks; it does not invent
placement, waive clocks, or silently split hardened types.
"""
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path


_RING_PLAN = {}
LAND_SLOTS_SCHEMA = "land_slots/3"   # /2 ring_start; /3 explicitly typed origin_start



def ring_write_fall(plan, tn=None):
    """S81-RINGHOLD-4 variant (a): True when the plan opts into the falling-edge write of the landing rings
    (clock.ring_hold.write_edge == "fall"); landing_contract.ring_input_sdc then gives their inputs the T/2 budget.
    HEAD-RINGHOLD-1: the optional ring_hold.write_fall_types list scopes it to those receiver types (a split copy
    "<base>__<suffix>" matches its base); absent = every type.  With tn None: the die-level flag only."""
    rh = (plan.get("clock") or {}).get("ring_hold") or {}
    if rh.get("write_edge") != "fall":
        return False
    only = rh.get("write_fall_types")
    return tn is None or only is None or tn in only or tn.split("__")[0] in only

RING_FANOUT_CHOICES = (0, 1, 2, 4, 8, 16, 32, 64)


def ring_fanout_max(clock):
    """DIE-QC-97 CLAND-RING-FO (COORD 11-10): die-level clock.landing_ring_fanout_max = F (power of two <= 64; 0 /
    absent = legacy).  With F > 0 every WREG count-aligned ring has <= F loads per write-enable flop (write_chunk <= F)
    and per read-select copy (dsrep >= 64 / F on the legacy 64-bit read chunk), using the existing kept same-D register
    copies (0 cycles, no K change), and gen_phys emits set_max_fanout F in the kit SDC.  Default 0: byte-same kits.
    Pilot 1 (11-10 CTS): F drives the read-select copies (dsrep) and the reader START copies (RSTREP) only; the write
    chunk bound is the separate opt-in clock.landing_ring_write_chunk (ring_write_chunk_max) and the SDC line the
    separate opt-in clock.landing_ring_sdc_max_fanout (gen_phys.ring_fanout_sdc)."""
    f = (clock or {}).get("landing_ring_fanout_max", 0)
    if isinstance(f, bool) or not isinstance(f, int) or f not in RING_FANOUT_CHOICES:
        raise ValueError(f"clock.landing_ring_fanout_max must be one of {RING_FANOUT_CHOICES}, got {f!r}")
    return f


RING_WRITE_CHUNK_CHOICES = (0, 8, 16, 32, 64)


def ring_write_chunk_max(clock):
    """Opt-in write-enable fanout bound clock.landing_ring_write_chunk = C (0 / absent / 64 = legacy 64-bit chunks).
    Kept apart from landing_ring_fanout_max: halving the chunk doubles the enable flops on the forwarded start, and
    pilot 1 measured the start -> enable T/2 path failing on a wide ring (st_ei -13.4 ps TT, 52 endpoints)."""
    c = (clock or {}).get("landing_ring_write_chunk", 0)
    if isinstance(c, bool) or not isinstance(c, int) or c not in RING_WRITE_CHUNK_CHOICES:
        raise ValueError(f"clock.landing_ring_write_chunk must be one of {RING_WRITE_CHUNK_CHOICES}, got {c!r}")
    return 0 if c == 64 else c


def ring_fanout_wreg_cfg(clock, cfg):
    """The landing_ring_wreg cfg dict as built under the die fanout bound (a new dict; cfg itself when the bound is 0 or
    the type has no WREG cfg).  Read-select copies are raised only on the legacy 64-bit read chunk (read_chunk 0): a
    bounded read_chunk type keeps its own dsrep (ot_meso_dsel needs SREP | chunk width)."""
    f, cmax = ring_fanout_max(clock), ring_write_chunk_max(clock)
    if not (f or cmax) or not isinstance(cfg, dict) or not cfg:
        return cfg
    out = dict(cfg)
    wc = out.get("write_chunk", 64)
    if cmax and isinstance(wc, int) and not isinstance(wc, bool) and wc > cmax:
        out["write_chunk"] = cmax
    if f and not out.get("read_chunk"):
        ds = out.get("dsrep", 1)
        if isinstance(ds, int) and not isinstance(ds, bool) and ds * f < 64:
            out["dsrep"] = 64 // f
    return out


def ring_status_reg_all(clock):
    """DIE-QC-97 CLAND-RING-FO part (c): die-level clock.landing_ring_status_reg = true turns STATUS_REG=1 on for every
    count-aligned ring (the per-type landing_status_reg opt-in, die-wide).  Data q and ready keep their cycles; a rv/lap
    fault is seen one clk later (status_reg_added_fault_cycles 1).  Absent / false = legacy."""
    v = (clock or {}).get("landing_ring_status_reg", False)
    if not isinstance(v, bool):
        raise ValueError("clock.landing_ring_status_reg must be a boolean")
    return v


def ring_guard_reg_all(clock):
    """CLAND-RING-NEGEDGE GUARD-REG-1 (COORD 11-11 09:47): die-level clock.landing_ring_guard_reg = true turns GUARD_REG=1
    (and the STATUS_REG=1 it needs) on for every count-aligned ring: no logic on any half-cycle rclk path of the ring.
    The guards keep their falling-edge sample and their cycles (0 added); data q and ready keep their cycles; a rv/lap
    fault is seen one clk later (STATUS_REG).  Absent / false = legacy."""
    v = (clock or {}).get("landing_ring_guard_reg", False)
    if not isinstance(v, bool):
        raise ValueError("clock.landing_ring_guard_reg must be a boolean")
    return v


def ring_reset_copies(clock, w, depth, dsrep=1, read_chunk=0):
    """DIE-QC-97 CLAND-RING-FO part (d), RSTREP-1: extra same-D copies of a count-aligned ring's last reader-START stage
    under clock.landing_ring_fanout_max F (0 = legacy, no copies).  The ring (ot_dp_clk_landing_cas RSTREP) keeps the
    control flops on rst_n, gives the one-hot oh copy 0 and splits its read-select chunks (DSREP x DEPTH select flops each)
    over the remaining copies in contiguous groups of at most max(1, F // (DSREP x DEPTH)) chunks.  w = ring W (before
    the cas 64-bit padding), read_chunk = the wreg READ_CHUNK (0 = 64-bit chunks).  Returns 1 + number of chunk groups."""
    f = ring_fanout_max(clock)
    if not f:
        return 0
    rw = -(-int(w) // 64) * 64
    nch = -(-rw // int(read_chunk)) if read_chunk else rw // 64
    per = max(1, int(dsrep) * int(depth))
    cpc = max(1, f // per)
    return 1 + -(-nch // cpc)


HARD_RING_BASES = ("ot_dp_clk_landing_ca", "ot_dp_clk_landing_cas")
RING_FANOUT_KNOBS = ("landing_ring_fanout_max", "landing_ring_write_chunk")   # die-wide, soft rings only


def hard_ring_params(plan, tn, bus, key=None):
    """QC-PARAMWRAP 11-12: the exact parameters of a count-aligned ring that the plan realises as a SIGNED hard child
    (partition_types[tn].hard_cores[] with param_wrap {base: ot_dp_clk_landing_ca/_cas} at physical_inst
    u_bound.u_cland_<bus>), else None.  The child master (rtl/physical/.../<master>.sv, param_wrap.wrapper_sv) is built
    and signed from exactly these parameters, so the bound ring must carry them verbatim: die-wide ring knobs
    (clock.landing_ring_status_reg / _guard_reg / _fanout_max) apply to soft rings only and never re-parameterise a
    hard child (param_wrap.wrap_bound fails closed on any difference)."""
    for t in (tn, key):
        for hc in (plan or {}).get("partition_types", {}).get(t, {}).get("hard_cores", []) or []:
            pw = hc.get("param_wrap") or {}
            if (pw.get("base") in HARD_RING_BASES
                    and (hc.get("physical_inst") or "").removeprefix("u_bound.") == f"u_cland_{bus}"):
                return dict(pw["params"])
    return None


def ring_place_copies(clock, w, read_chunk=0):
    """DIE-QC-97 PLACEREP-1: True when clock.landing_ring_fanout_max F > 0 and the ring (W = w before the cas 64-bit padding,
    read_chunk = the wreg READ_CHUNK, 0 = 64-bit chunks) has more than one read chunk: every read chunk then keeps its own
    copy of the reader placement value (ot_dp_clk_landing_cas PLACEREP), so one placement net no longer loads every chunk's
    select decode.  Rings with one chunk and F = 0 keep today's logic."""
    if not ring_fanout_max(clock):
        return False
    rw = -(-int(w) // 64) * 64
    nch = -(-rw // int(read_chunk)) if read_chunk else rw // 64
    return nch > 1


def ring_write_reg(plan, tn, bus):
    """WREG-1 (DIE-HEAD-58 TURNB 11-03): {"depth": 1, "dsrep": n} when receiver type tn opts bus into the registered
    ring writer (partition_types[tn].clock.landing_ring_wreg = {"buses": [...], "dsrep": n}; a split copy
    "<base>__<suffix>" reads its base): t_rst_n registered at the face + one write-enable flop per (slot, 64-bit chunk)
    (ot_dp_clk_landing_cas WREG=1) and n read-select copies per chunk (DSREP).  The writer starts one fclk edge later, so
    count_align_bind.strap_ties ties K + 1 (the landing_writer_start W=1 rule); the word stream q is unchanged.
    None when absent."""
    pt = plan.get("partition_types", {})
    t = pt.get(tn) or pt.get(tn.split("__")[0]) or {}
    cfg = (t.get("clock") or {}).get("landing_ring_wreg")
    if not cfg:
        return None
    if not isinstance(cfg, dict) or not isinstance(cfg.get("buses"), list):
        raise ValueError(f"{tn}: clock.landing_ring_wreg must be {{\"buses\": [...], \"dsrep\": n}}")
    cfg = ring_fanout_wreg_cfg(plan.get("clock"), cfg)   # DIE-QC-97: die fanout bound (0 = cfg unchanged)
    if bus not in cfg["buses"]:
        return None
    dsrep = cfg.get("dsrep", 1)
    if isinstance(dsrep, bool) or not isinstance(dsrep, int) or dsrep < 1 or 64 % dsrep:
        raise ValueError(f"{tn}: landing_ring_wreg.dsrep must divide 64")
    # FREG-1 (DIE-HEAD-58 ruling 11-03): "freg": true adds the rising-fclk face register on d + t_rst_n (cas FREG=1):
    # data and writer start one cycle later together -> one more K at bind (keeps the ring window) = ONE added data
    # cycle on that crossing (q one clk later; TB_FREG bench)
    freg = cfg.get("freg", False)
    if not isinstance(freg, bool):
        raise ValueError(f"{tn}: landing_ring_wreg.freg must be a boolean")
    write_chunk = cfg.get("write_chunk", 64)
    if isinstance(write_chunk, bool) or not isinstance(write_chunk, int) or write_chunk not in (1, 2, 4, 8, 16, 32, 64):
        raise ValueError(f"{tn}: landing_ring_wreg.write_chunk must divide 64")
    numeric = cfg.get("freg_numeric_order", False)
    if not isinstance(numeric, bool) or (numeric and not freg):
        raise ValueError(f"{tn}: freg_numeric_order requires boolean true and freg=true")
    # DIE-HEAD-84 (CTL_n vC/vD): the cas READ_CHUNK / WRITE_TAIL internal form (bounded read chunks of any width,
    # partial last write chunk); same cycles, so no K or data-cycle change.  0 / false = the legacy form.
    read_chunk = cfg.get("read_chunk", 0)
    if isinstance(read_chunk, bool) or not isinstance(read_chunk, int) or not 0 <= read_chunk <= 64:
        raise ValueError(f"{tn}: landing_ring_wreg.read_chunk must be an integer 0..64")
    write_tail = cfg.get("write_tail", False)
    if not isinstance(write_tail, bool):
        raise ValueError(f"{tn}: landing_ring_wreg.write_tail must be a boolean")
    out = dict(depth=1 + int(freg), dsrep=dsrep, freg=freg)
    if write_chunk != 64:
        out["write_chunk"] = write_chunk
    if read_chunk:
        out["read_chunk"] = read_chunk
    if write_tail:
        out["write_tail"] = True
    if numeric:
        out["freg_numeric_order"] = True
    return out



def ring_read_select_copies(plan, tn, bus):
    """Optional read-select replication only; no writer stage or K adjustment.

    clock.landing_ring_dsrep = {"buses": [...], "dsrep": n} selects existing
    ot_dp_clk_landing_cas DSREP hardware independently of landing_ring_wreg.
    """
    types = plan.get("partition_types", {})
    typ = types.get(tn) or types.get(tn.split("__")[0]) or {}
    cfg = (typ.get("clock") or {}).get("landing_ring_dsrep")
    if cfg is None:
        return None
    if (not isinstance(cfg, dict) or not isinstance(cfg.get("buses"), list)
            or any(not isinstance(b, str) for b in cfg["buses"])):
        raise LandingError(f"{tn}: clock.landing_ring_dsrep must list buses and dsrep")
    copies = cfg.get("dsrep")
    if isinstance(copies, bool) or not isinstance(copies, int) or copies < 1 or 64 % copies:
        raise LandingError(f"{tn}: landing_ring_dsrep.dsrep must divide 64")
    f = ring_fanout_max(plan.get("clock"))   # DIE-QC-97: same die bound as ring_write_reg (no conflict with its dsrep)
    if f and copies * f < 64:
        copies = 64 // f
    return copies if bus in cfg["buses"] else None


def legacy_input_freg(plan, tn, bus):
    """Explicit rising-fclk payload capture of the legacy ring, +1 data cycle.

    This does not change its free-running pointer or receiver training. It is
    separate from the count-aligned WREG/FREG start/count-frame mechanism.
    """
    types = plan.get("partition_types", {})
    typ = types.get(tn) or types.get(tn.split("__")[0]) or {}
    cfg = typ.get("clock", {}).get("landing_input_freg")
    if cfg is None:
        return False
    if (not isinstance(cfg, list) or any(not isinstance(b, str) for b in cfg)
            or len(cfg) != len(set(cfg))
            or any(not re.fullmatch(r"[A-Za-z_]\w*", b) for b in cfg)):
        raise LandingError(f"{tn}: landing_input_freg must list unique legacy input buses")
    return bus in cfg


def ca_mixed(ca):
    """CA-MIXED-1 (TOK-VERIFY-1 11-11, opt-in count_aligned.mixed): the count-aligned / ring choice is made PER
    LANDING.  A landed crossing listed in count_aligned.ports gets the count-aligned ring and its region's count
    origin; every other landed crossing keeps today's ring (ot_dp_clk_landing, its own phase), priced at
    count_aligned.ring_cycles[pid] (the measured LEAD/LAG count, landing_ca_select.py) or the nominal 3.
    Without the flag a count-aligned table covers the whole network (every crossing must be in the bind)."""
    return bool(ca) and bool(ca.get("mixed"))


def ca_port(ca, pid):
    """True when landed crossing pid takes the count-aligned form: every crossing of a whole-network table, only
    the bind's crossings of a mixed table (CA-MIXED-1)."""
    if not ca:
        return False
    return pid in ca["ports"] if ca_mixed(ca) else True


def ring_cycles(ca, pid):
    """Priced data cycles of a ring (not count-aligned) crossing: nominal 3, or in a mixed table the per-landing
    measured count count_aligned.ring_cycles[pid] (positive integer)."""
    n = (ca.get("ring_cycles") or {}).get(pid, 3) if ca_mixed(ca) else 3
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise LandingError(f"{pid}: ring_cycles must be a positive integer, got {n!r}")
    return n


def output_qreg(plan, tn, bus):
    """CLAND-QREG-1 (COORD 11-11, owner rule: a pipeline cycle, not a setup/hold trade): receiver type tn lists input
    bus in partition_types[tn].clock.landing_output_qreg -> its landing ring (legacy ot_dp_clk_landing or count-aligned
    _ca/_cas) gets QREG=1: one kept rclk register stage on q between the ring readout and the boundary flop.  The ring,
    its window and ready/fault are unchanged; the crossing carries ONE more data cycle, counted once:
      legacy ring: +1 on the row added_cycles / lane cycles here (the sidecar added_cycles must say so);
      count-aligned ring (the HEAD FREG convention, n4_event "sched_lat +1, raw K unchanged"): the die event raises the
      sidecar sched_lat AND logical K by 1 and marks the port "output_qreg": 1; count_align_bind ties the physical ring
      K = logical K - 1 (the stage is outside the ring), so the window is unchanged and the cycle is in sched_lat.
    A split copy "<base>__<suffix>" reads its base.  Absent = byte-same RTL."""
    types = plan.get("partition_types", {})
    typ = types.get(tn) or types.get(tn.split("__")[0]) or {}
    cfg = (typ.get("clock") or {}).get("landing_output_qreg")
    if cfg is None:
        return False
    if (not isinstance(cfg, list) or any(not isinstance(b, str) for b in cfg) or len(cfg) != len(set(cfg))
            or any(not re.fullmatch(r"[A-Za-z_]\w*", b) for b in cfg)):
        raise LandingError(f"{tn}: landing_output_qreg must list unique landed input buses")
    return bus in cfg


def check_ca_freg_declared(plan, tn, bus, c, pid, err=None):
    """FREG-DECL-1 (COORD 11-11, fail closed): the count-aligned FREG face register (landing_ring_wreg.freg) delays data
    AND writer start one fclk; strap_ties adds K + 2 (WREG + FREG), so q is ONE clk later than the plan's geometric
    latency.  Neither the planner (count_align_plan lat_cycles) nor the generator adds that cycle: only a die event
    that raises the sidecar sched_lat by 1 (HEAD n4_event convention) counts it.  Such a crossing must therefore DECLARE
    it on its bind sidecar port: count_aligned.ports[pid]["freg"] = 1 ("this sched_lat includes the FREG cycle").
    A FREG ring without the mark (cycle uncounted: the receiver is one cycle late) or a mark without FREG (stale sidecar)
    is an error.  The legacy landing_input_freg needs no mark: its +1 is added here (crossing_cycles / Landings rows)
    and a sidecar added_cycles that disagrees already fails."""
    wreg = ring_write_reg(plan, tn, bus)
    freg = bool(wreg and wreg.get("freg"))
    if freg != bool(c.get("freg")):
        msg = (f"count-aligned landing {pid} ({tn}.{bus}): " + (
            "landing_ring_wreg.freg adds one data cycle but the bind sidecar port does not declare it; raise "
            "count_aligned.ports[].sched_lat (and the source sidecar added_cycles) by 1 and set \"freg\": 1"
            if freg else "bind sidecar declares \"freg\": 1 but the plan has no landing_ring_wreg.freg on this bus "
            "(stale sidecar: lower sched_lat by 1 and drop the mark)"))
        raise (err or LandingError)(msg)


def crossing_cycles(plan, ca, pid):
    """The plan selects hardware; its explicit capture is counted exactly once."""
    p = next(p for p in plan["ports"] if p["id"] == pid)
    tn = next(r["type"] for r in plan["partitions"] if r["name"] == p["dst"]["part"])
    capture = legacy_input_freg(plan, tn, p["dst"]["bus"])
    if ca_port(ca, pid) and capture:
        raise LandingError(f"{pid}: legacy input FREG and count-aligned form are exclusive")
    # CLAND-QREG-1: a count-aligned crossing carries its output stage inside sched_lat (see output_qreg)
    return ca_cycles(ca, pid) + int(capture) + (0 if ca_port(ca, pid) else int(output_qreg(plan, tn, p["dst"]["bus"])))


def ring_taps(plan, tn):
    """[(x, y)] of the taps whose wavefront relays drive rst_n_t<i> in type tn (type frame): the index space a ring
    reset node rst_n_t<i> refers to.  A plan clock.taps list of kind 'core' entries (S81 12.8a plan-defined core
    clock entries) is NOT that index space: the reset tree numbers its relays over schema.tap_grid
    (reset_tree._taps), so such types use the reset tree's own taps. A physical type with only tap_um/tap_mode
    also uses that generated grid; an absent explicit list must not silently assign every ring to tap zero.
    S81-RINGTAP-1 (11-08, slice_station__t45 G2 setup -199 ps): tap_mode "grid" / "grid+explicit" ALSO uses the
    reset tree's taps when the type carries an explicit clock.taps list: reset_tree._taps never reads that list in
    these modes, so numbering rst_n_t<i> over it picks a relay on another grid tap (t45 ft1_i ring at the W face took
    rst_n_t2, placed 1267 um away, instead of rst_n_t4 at 239 um: a 37-buffer sync-reset wire, TT -199 ps).
    QC-TYPES-10/CLAND (11-08): tap_mode "density" is the same case (reset_tree._taps = schema.tap_grid, which never
    reads clock.taps there): every QC soft type carries a 2-entry 'glue' clock.taps list, so every ring took
    rst_n_t0/t1 (slw_fe_v1 E-face rings on rst_rl_77, 897 um away; 680 ring raw copies >405 um in 80 QC types).
    Types without a mode keep their existing behaviour."""
    ck = plan["partition_types"][tn].get("clock", {})
    taps = ck.get("taps", [])
    generated_grid = (not taps and ("tap_um" in ck or "tap_mode" in ck)) or \
        ck.get("tap_mode") in ("grid", "grid+explicit", "density")
    if not generated_grid and not any(x.get("kind") == "core" for x in taps):
        return [tuple(x["xy"]) for x in taps]
    import schema
    import reset_tree as RT
    e = _RING_PLAN.get(id(plan))
    if e is None or e[0] is not plan:
        e = _RING_PLAN[id(plan)] = (plan, schema.Plan(plan))
    return [(x, y) for _, x, y in RT._taps(e[1], tn)]


def network_lane_cycles(plan):
    """Exact nominal data cycles from source-bound physical forwarded edges.

    Monitor edges add boot time only. Native fixed_cycles is left intact.
    The endpoint names are checked, so arbitrary clock metadata cannot price
    a functional lane or silently add a second copy of a physical crossing.
    """
    net=plan.get("clock",{}).get("landing_network")
    if not net:return {}
    ca=net.get("data_cycles_per_crossing")=="count_aligned"
    if not ca and net.get("data_cycles_per_crossing")!=3:raise LandingError("clock landing network requires the proved nominal +3 contract")
    if ca and not isinstance(net.get("count_aligned_cycles"),dict):raise LandingError("count-aligned landing network needs per-crossing count_aligned_cycles")
    # CA-MIXED-1: per-landing form; a crossing outside count_aligned_cycles is a ring at ring_cycles[pid] (default 3)
    mixed=ca and bool(net.get("count_aligned_mixed"))
    mca=dict(mixed=True,ports=net["count_aligned_cycles"],ring_cycles=net.get("ring_cycles") or {}) if mixed else None
    ports={p["id"]:p for p in plan["ports"]};owners=defaultdict(list)
    for lane in plan["lanes"]:
        for pid in lane["ports"]:owners[pid].append(lane["id"])
    out=defaultdict(int);seen=set()
    for edge in net.get("edges",[]):
        if not edge["id"].startswith("cland_clk__"):continue
        pid=edge["id"][len("cland_clk__"):];p=ports.get(pid)
        if p is None or pid in seen:raise LandingError("stale/duplicate functional clock landing "+pid)
        seen.add(pid)
        expected=dict(src=dict(part=p["src"]["part"],bus="fclk_out_"+p["src"]["bus"]),dst=dict(part=p["dst"]["part"],bus="fclk_in_"+p["dst"]["bus"]))
        if edge.get("kind")!="clock" or any(edge[k]!=expected[k] for k in ("src","dst")):
            raise LandingError("clock landing physical endpoints changed "+pid)
        if len(owners[pid])!=1:raise LandingError("clock landing must identify exactly one logical lane "+pid)
        if mixed:
            tn = next(q["type"] for q in plan["partitions"] if q["name"] == p["dst"]["part"])
            capture = legacy_input_freg(plan, tn, p["dst"]["bus"])
            if pid in mca["ports"]:
                if capture:raise LandingError(f"{pid}: legacy input FREG and count-aligned form are exclusive")
                out[owners[pid][0]] += int(mca["ports"][pid])
            else:
                out[owners[pid][0]] += ring_cycles(mca, pid) + int(capture) + int(output_qreg(plan, tn, p["dst"]["bus"]))
            continue
        if ca and pid not in net["count_aligned_cycles"]:raise LandingError("count-aligned crossing has no planned latency "+pid)
        tn = next(q["type"] for q in plan["partitions"] if q["name"] == p["dst"]["part"])
        capture = legacy_input_freg(plan, tn, p["dst"]["bus"])
        if ca and capture:
            raise LandingError(f"{pid}: legacy input FREG and count-aligned form are exclusive")
        out[owners[pid][0]] += int(net["count_aligned_cycles"][pid]) if ca else \
            3 + int(capture) + int(output_qreg(plan, tn, p["dst"]["bus"]))   # CLAND-QREG-1 (CA: inside sched_lat)
    if mixed:
        stale=sorted(set(net["count_aligned_cycles"])-seen)
        if stale:raise LandingError(f"count-aligned latency for {len(stale)} crossings with no landing edge: {stale[:3]}")
    return dict(out)


START_PIN_IN = "cland_tstart_in"     # == count_align_bind.START_PIN_IN
RAW_RESET_PIN_OUT = "cland_raw_reset_out"
START_PIN_OUT = "cland_tstart_out"   # == count_align_bind.START_PIN_OUT


def start_net_name(x):
    """die-level start-stage net name part of a region (== start_stage_emit.sv_name)"""
    return re.sub(r"\W", "_", x)


def start_pins(plan, ca):
    """START-TREE compose slice (DIE-HEAD-11): the dedicated start pins of a count-aligned table with start_ports.
    -> dict(ports={pid: dict(src, dst, src_part, dst_part)}, type_pins={type: {pin: dir}}, plan_ports=[real -> real],
            die_inputs=[real -> stage: top output rs_<region>], die_outputs=[stage -> real: top input pst_<region>]).
    A start port's real ends are its launch partition (src region origin) and capture partition (dst region origin); a
    virtual region ('st:' / regions[].virtual) is a die-level stage (start_stage_emit.py), never a partition."""
    parts = {p["name"]: p for p in plan["partitions"]}
    reg = ca["regions"]

    def real(x):
        if x not in reg:
            raise LandingError(f"start port end {x}: not a start-tree region")
        return not str(x).startswith("st:")
    ports, tp = {}, defaultdict(dict)
    plan_ports, die_in, die_out = [], [], []
    for pid, c in sorted(ca["start_ports"].items()):
        s_real, d_real = real(c["src"]), real(c["dst"])
        sp = (c.get("src_part") or c.get("launch_part")) if s_real else None
        dp = (c.get("dst_part") or c.get("capture_part")) if d_real else None
        for what, x, q in (("launch", c["src"], sp), ("capture", c["dst"], dp)):
            if q is not None and q not in parts:
                raise LandingError(f"start port {pid}: {what} partition {q} is not a plan partition")
            if (x == c["src"] and s_real or x == c["dst"] and d_real) and q is None:
                raise LandingError(f"start port {pid}: real region {x} has no {what} partition")
            org = reg[x].get("origin_part")
            if q is not None and org is not None and q != org:
                raise LandingError(f"start port {pid}: {what} partition {q} is not the origin {org} of {x}")
        ports[pid] = dict(src=c["src"], dst=c["dst"], src_part=sp, dst_part=dp)
        if sp:
            tp[parts[sp]["type"]][START_PIN_OUT] = "out"
        if dp:
            tp[parts[dp]["type"]][START_PIN_IN] = "in"
        if sp and dp:
            plan_ports.append(dict(port=pid, src_part=sp, dst_part=dp))
        elif sp:
            die_in.append(dict(port=pid, src_part=sp, net=f"rs_{start_net_name(c['src'])}", stage_region=c["dst"]))
        elif dp:
            die_out.append(dict(port=pid, dst_part=dp, net=f"pst_{start_net_name(c['dst'])}", stage_region=c["src"]))
    # a die-level stage reads one rs_<region> net per real parent region (fan-out inside the stage module)
    seen = {}
    for e in die_in:
        if seen.setdefault(e["net"], e["src_part"]) != e["src_part"]:
            raise LandingError(f"start net {e['net']}: two launch partitions")
    resets = []
    if ca.get("start_reset_wave"):
        resets = [dict(src_part=e["src_part"],region=e["net"][3:],net="rraw_"+e["net"][3:])
                  for e in sorted({e["net"]:e for e in die_in}.values(),key=lambda e:e["net"])]
        for e in resets:tp[parts[e["src_part"]]["type"]][RAW_RESET_PIN_OUT]="out"
    return dict(**(dict(reset_inputs=resets,reset_wave="bounded_synchronous_parent_relays") if ca.get("start_reset_wave") else {}),
                ports=ports, type_pins={k: dict(v) for k, v in sorted(tp.items())}, plan_ports=plan_ports,
                die_inputs=die_in, die_outputs=die_out, die_input_nets=sorted(seen),
                pins=dict(input=START_PIN_IN, output=START_PIN_OUT))


def requirements(plan, table):
    """Publish concrete type-mask/pin/latency work before changing a plan.

    Pin faces/windows are copied as placement references only. A scalar clock
    pin still needs a legal track and a status pin needs a destination; copying
    the data window does not constitute a physical placement approval.
    """
    parts = {p["name"]: p for p in plan["partitions"]}
    types = plan["partition_types"]
    ports = {p["id"]: p for p in plan["ports"]}
    masks = {pn: dict(inputs=set(), outputs=set()) for pn in parts}
    pin_refs, lanes = [], defaultdict(int)
    ca = table.get("count_aligned")
    for r in table["ports"]:
        p = ports[r["port"]]
        sp, sb, dp, db = p["src"]["part"], p["src"]["bus"], p["dst"]["part"], p["dst"]["bus"]
        if (sp, dp, int(p["width"])) != (r["src"], r["dst"], int(r["width"])):
            raise LandingError(f"stale clock landing endpoints/width on {r['port']}")
        masks[sp]["outputs"].add(sb)
        masks[dp]["inputs"].add(db)
        cyc = crossing_cycles(plan, ca, r["port"])
        lanes[r["lane"]] += cyc
        rca = ca_port(ca, r["port"])
        pin_refs.append(dict(port=r["port"], lane=r["lane"], src=sp, dst=dp,
                             src_bus=sb, dst_bus=db, width=p["width"],
                             required_src_pin=f"fclk_out_{sb}",
                             required_dst_pins=[f"fclk_in_{db}", f"landing_ready_{db}", f"landing_fault_{db}"]
                             + ([f"cland_fstart_in_{db}"] if rca else []),
                             **({"required_src_start_pin": f"cland_fstart_out_{sb}"} if rca else {}),
                             **({"form": "count_aligned" if rca else "ring"} if ca_mixed(ca) else {}),
                             extra_cycles=cyc))
        if not rca and legacy_input_freg(plan, parts[dp]["type"], db):
            status = 2 if (table.get("collector") or {}).get("monitor") in ("dataflow", "region") else 0
            pin_refs[-1].update(input_capture_cycles=1, input_capture_flops=int(p["width"]) + 1 + status)
        if output_qreg(plan, parts[dp]["type"], db):
            # CLAND-QREG-1: W output-stage flops (data only), +1 data cycle already in cyc (crossing_cycles)
            pin_refs[-1].update(output_qreg_cycles=1,
                                input_capture_flops=int(pin_refs[-1].get("input_capture_flops", 0)) + int(p["width"]))
    cohorts = defaultdict(dict)
    for pn, p in parts.items():
        mask = {k: sorted(v) for k, v in masks[pn].items()}
        key = json.dumps(mask, sort_keys=True)
        cohorts[p["type"]].setdefault(key, []).append(pn)
    groups = {}
    row_by_sink = {(r["dst"], r["dst_bus"]): r for r in pin_refs}
    for tn, cs in cohorts.items():
        groups[tn] = [dict(mask=json.loads(k), instances=ps,
                          proposed_type=tn if len(cs) == 1 else tn + "__cl" + hashlib.sha256(k.encode()).hexdigest()[:8])
                      for k, ps in sorted(cs.items())]
        for g in groups[tn]:
            rows = [row_by_sink[(g["instances"][0], b)] for b in g["mask"]["inputs"]]
            g["added_live_data_storage_flops"] = sum(5 * (int(r["width"]) + 1) + int(r.get("input_capture_flops", 0)) for r in rows)
            g["control_flops_upper_estimate"] = sum(73 + 4 * ((int(r["width"]) + 64) // 64) for r in rows)
            g["padded_data_storage_flops_upper_estimate"] = sum(5 * 64 * ((int(r["width"]) + 64) // 64) + int(r.get("input_capture_flops", 0)) for r in rows)
            g["clock_sink_addition_upper_estimate"] = g["added_live_data_storage_flops"] + g["control_flops_upper_estimate"]
            g["placement_required"] = [dict(bus=r["dst_bus"], ring_instance=f"u_cland_{r['dst_bus']}.u_ring",
                                            data_storage_flops=5 * (int(r["width"]) + 1),
                                            write_clock_pin=f"fclk_in_{r['dst_bus']}", read_clock="clk",
                                            window="received bus face; actual legal sites/tracks NOT assigned") for r in rows]
    return dict(schema="opentallas.clock_landing_requirements.v1", implemented=False,
                source_table_sha256=hashlib.sha256(json.dumps(table, sort_keys=True).encode()).hexdigest(),
                crossings=len(pin_refs),
                required_new_scalar_pins=len({(r["src"], r["src_bus"]) for r in pin_refs}) + 3 * len(pin_refs),
                added_live_data_storage_flops=sum(5 * (int(r["width"]) + 1) + int(r.get("input_capture_flops", 0)) for r in pin_refs),
                type_count_before=len(types), type_count_after=sum(map(len, groups.values())),
                split_types={tn: g for tn, g in groups.items() if len(g) > 1},
                cohorts=groups, ports=pin_refs, lane_added_cycles=dict(sorted(lanes.items())),
                nominal_added_cycles_per_crossing=("per landing: count_aligned or ring (CA-MIXED-1)" if ca_mixed(ca) else
                    "count_aligned (per crossing)" if ca else
                    "legacy per crossing: base3 + explicit input capture" if any(r.get("input_capture_cycles") for r in pin_refs) else 3),
                pending=["reserve forwarded-clock and observed status pin tracks", "split nonuniform landing masks",
                         "update lane/R8/calendar price", "emit actual landing RTL", "ring window STA and token pass"])


class LandingError(ValueError):
    pass


# count-aligned intra-region start relay: tx flop (origin partition) + rx flop (relay partition); must equal
# count_align_bind.RELAY_STAGES, which shifts the K of the relay partition's crossings by the same counts
RELAY_STAGES = 2
# Strap inputs the strap-form origin declares SCALAR (`input wire strap_ca_efall`, no [0:0]); every other strap is a
# vector.  gen_phys.strap_pin_sites names these pins without a bit index (FLOW-GEN-1 10-28, DIE-HEAD-9 bug 1).
SCALAR_STRAPS = frozenset({"strap_ca_efall", "strap_ca_root"})


def ca_cycles(ca, pid):
    """Added data cycles of one landed crossing: the proved old-ring +3, or (count-aligned form, MESO-INTEG-1) the
    plan's per-crossing schedule latency K + 1 + n_dst - n_src (count_align_bind.py)."""
    if not ca:
        return 3
    if not ca_port(ca, pid):
        return ring_cycles(ca, pid)
    c = ca["ports"].get(pid)
    if c is None:
        raise LandingError(f"count-aligned landing {pid}: no K/DEPTH/latency in the bind table")
    return int(c["sched_lat"])


def ident(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


# Same-region (non-seam) status inputs (DIE-S81-29, COORD DIE-S81-28-PARK (2)): every such pin bit loads ONLY the D of
# its own face capture flop ot_dp_landing_face (no reset term, so no gate between pin and D: face_guard 'unregistered'
# on the former AND2 of the reduction's synchronous reset).  +1 status cycle (boot-only training/status path,
# clock_landing_plan prices it in boot_transport_extra_cycles), 0 data cycles.  Types without such inputs are unchanged.
STATUS_FACE_CYCLES = 1


def status_face(logic, key, ready, fault, xy_um=None):
    """Append the two face flops of one same-region status pin pair; returns (ready_q, fault_q, instance records)."""
    k = ident(str(key))
    rq, fq = f"cland_dn_fq_ready_{k}", f"cland_dn_fq_fault_{k}"
    logic += [f"    wire {rq}, {fq};",
              f"    ot_dp_landing_face u_cland_face_ready_{k} (.clk(clk), .d({ready}), .q({rq}));",
              f"    ot_dp_landing_face u_cland_face_fault_{k} (.clk(clk), .d({fault}), .q({fq}));"]
    insts = [dict(name=f"u_cland_face_{kind}_{k}", module="ot_dp_landing_face", flops=1, pin=pin,
                  role="same-region status face capture", status_cycles_added=STATUS_FACE_CYCLES, data_cycles_added=0,
                  **({"xy_um": xy_um} if xy_um is not None else {}))
             for kind, pin in (("ready", ready), ("fault", fault))]
    return rq, fq, insts


def gate_observer(body,spec):
    """Bind the two real one-bit mission/observation inputs, never new IO."""
    module=re.escape(spec["module"])
    pattern=re.compile(r"(?m)^\s*"+module+r"(?:\s*#\([^;]*?\))?\s+(\w+)\s*\(\n",re.S)
    matches=[m for m in pattern.finditer(body) if m.group(1).endswith(spec["instance_suffix"])]
    if len(matches)!=1:raise LandingError(f"clock landing observer: expected one {spec['module']}.{spec['instance_suffix']}, found{len(matches)}")
    m=matches[0];end=body.find("\n    );",m.end())
    if end<0:raise LandingError("clock landing observer: instance terminator not found")
    block=body[m.start():end]
    for port,op,signal in ((spec["fault_port"],"|","cland_up_fault"),(spec["ready_port"],"&","cland_up_ready")):
        hits=list(re.finditer(r"\."+re.escape(port)+r"\s*\(",block))
        if len(hits)!=1:raise LandingError(f"clock landing observer: expected one exact input {port}")
        start=hits[0].end();depth=1;i=start
        while i<len(block) and depth:
            depth+=(block[i]=="(")-(block[i]==")");i+=1
        if depth:raise LandingError(f"clock landing observer: unbalanced input {port}")
        old=block[start:i-1].strip()
        if not old:raise LandingError(f"clock landing observer: empty input {port}")
        block=block[:start]+f"(({old}) {op} {signal})"+block[i-1:]
    return body[:m.start()]+block+body[end:]


def expand_station_types(binder,table):
    """Keep real native OUT stations enabled after phase/clock type splits.

    The compose tool explicitly records each current type's prelanding base.
    Phase type names preserve that original family as a complete prefix token.
    Native annotate still checks the actual source-station count against each
    lane's priced fixed_cycles; this does not exempt a station or add cycles.
    """
    selected=set(binder.ab.get("internal_stations_types",[]))
    if not selected:return
    lineage=table.get("collector",{}).get("types",{})
    out=set();represented=set()
    for tn in binder.types:
        base=lineage.get(tn,{}).get("base_type",tn)
        matches={s for s in selected if tn==s or base==s or base.startswith(s+"_")}
        if matches:out.add(tn);represented.update(matches)
    missing=selected-represented
    if missing:raise LandingError(f"clock landing native station families have no actual cohort: {sorted(missing)}")
    binder.ab["internal_stations_types"]=sorted(out)


def _ca_in(obj, pn):
    """CA-MIXED-1: count-aligned landed input buses of partition pn (all of them in the whole-network form)"""
    return obj.ca_ins[pn] if getattr(obj, "mixed", False) else set(obj.ins[pn])


def _ca_out(obj, pn):
    """CA-MIXED-1: output buses of pn that forward a count-aligned start (all landed outputs in the whole-network form)"""
    return obj.ca_outs[pn] if getattr(obj, "mixed", False) else set(obj.outs[pn])


def _cam(obj, tn):
    """CA-MIXED-1: the count-aligned subset {inputs, outputs} of type tn's landed buses; the whole-network form reads
    the type mask itself (by_type), so it is exactly the previous behaviour"""
    if getattr(obj, "mixed", False):
        return obj.ca_by_type.get(tn) or dict(inputs=(), outputs=())
    m = (getattr(obj, "by_type", None) or {}).get(tn) or {}
    return dict(inputs=tuple(m.get("inputs", ())), outputs=tuple(m.get("outputs", ())))


class Landings:
    def __init__(self, plan, table, *, require_geometry=True, ca_variants=False, plan_path=None):
        """ca_variants (MESO-STRAP-1, LEC only): count-aligned PARAMETER form without the TYPE_SPLIT stop, so
        type_rtl(..., inst=<partition>) can emit one copy's parameter wrapper (the LEC reference of a strap master)."""
        self.plan = plan
        self.plan_path = plan_path      # resolves plan-relative pin tables for tap_grid (added_taps -> reset_tree)
        self.ca_variants = ca_variants
        self.collector = table.get("collector")
        if self.collector is not None:
            # SIDECAR-COVERAGE (GEN-CLASS-1 11-12, DIE-S81-88 PSPLIT-SIDECAR-STALE): the sidecar is composed per plan
            # (clock_landing_plan.compose writes one collector.types row per partition type); a sidecar of another
            # plan (unsplit base vs psplit) lacks the split types and gen_rtl died on KeyError '<type>'.  Fail closed
            # here, before any RTL is written, with the class name and the missing types.
            ptypes = sorted({p["type"] for p in plan.get("partitions") or []})
            have = self.collector.get("types") or {}
            miss = [tn for tn in ptypes if tn not in have]
            if miss:
                raise LandingError(f"SIDECAR_STALE: clock-landing sidecar collector.types lacks {len(miss)} of "
                                   f"{len(ptypes)} plan partition types ({', '.join(miss[:6])}"
                                   f"{', ...' if len(miss) > 6 else ''}): the sidecar was composed for another plan; "
                                   f"pass the sidecar composed with this plan (--clock-landing)")
        # monitor="region" (opt-in, DIE-HEAD-3): the dataflow monitor plus same-region status links (registered ctl
        # pins on the region clock, no ring) from clock_landing_plan.compose(monitor="region").
        self.region_monitor = bool(self.collector) and self.collector.get("monitor", "reset") == "region"
        self.dataflow = bool(self.collector) and self.collector.get("monitor", "reset") in ("dataflow", "region")
        if self.collector and self.collector.get("monitor", "reset") not in ("reset", "dataflow", "region"):
            raise LandingError(f"clock landing: unknown monitor mode {self.collector.get('monitor')}")
        self.parts = {p["name"]: p for p in plan["partitions"]}
        self.types = plan["partition_types"]
        ports = {p["id"]: p for p in plan["ports"]}
        self.rows = []
        self.region = {}
        self.emitted_types = set()
        self.forwarded_clock_only_inputs = {}
        self.emitted_top = False
        self.reset_placements = {}
        for pn, p in self.parts.items():
            w, h = self.types[p["type"]]["outline_um"]
            x, y = p["origin_um"][0] + w / 2, p["origin_um"][1] + h / 2
            candidates = [r["tag"] for r in table["regions"]
                          if r["box_um"][0] <= x < r["box_um"][2]
                          and r["box_um"][1] <= y < r["box_um"][3]]
            if len(candidates) != 1:
                raise LandingError(f"clock landing {pn}: expected one whole-partition region")
            self.region[pn] = candidates[0]
        self.ins = defaultdict(dict)
        self.outs = defaultdict(set)
        self.ca = table.get("count_aligned")
        # CA-MIXED-1: count-aligned input / forwarded-start output buses per partition (== ins / outs without mixed)
        self.mixed = ca_mixed(self.ca)
        self.ca_ins = defaultdict(set)
        self.ca_outs = defaultdict(set)
        # MESO-STRAP-1 (OWNER 12.15a, opt-in: count_aligned.strap_form): K / PAD / EDGE_FALL / tree select / root become
        # strap_ca_* input pins of ONE design per type, tied at the parent to count_align_bind.strap_ties() values
        self.strap = None
        if self.ca and self.ca.get("strap_form"):
            import count_align_bind as CAB
            self.strap = CAB.strap_ties(self.ca, plan)
        # START-TREE compose slice (opt-in: count_aligned.start_ports): dedicated start pins, see _start_pins()
        self.tstart = self._start_pins(plan) if self.ca and self.ca.get("start_ports") else None
        seen = set()
        for r in table["ports"]:
            pid = r["port"]
            if pid in seen:
                raise LandingError(f"duplicate clock landing port {pid}")
            seen.add(pid)
            if pid not in ports:
                raise LandingError(f"clock landing has no physical plan port {pid}")
            p = ports[pid]
            if p.get("kind", "data") not in ("data", "ctl"):
                raise LandingError(f"clock landing {pid}: reset/clock needs its own contract")
            sp, sb = p["src"]["part"], p["src"]["bus"]
            dp, db = p["dst"]["part"], p["dst"]["bus"]
            if (sp, dp, int(p["width"])) != (r["src"], r["dst"], int(r["width"])):
                raise LandingError(f"stale clock landing endpoints/width on {pid}")
            if r["src_region"] == r["dst_region"]:
                raise LandingError(f"clock landing {pid} stays in one region")
            for part, region in ((sp, r["src_region"]), (dp, r["dst_region"])):
                if part not in self.parts:
                    raise LandingError(f"clock landing {pid}: non-partition endpoint {part}")
                if part in self.region and self.region[part] != region:
                    raise LandingError(f"clock landing region conflict for {part}")
                self.region[part] = region
            if db in self.ins[dp]:
                raise LandingError(f"two clock landings drive {dp}.{db}")
            # The ring form is a per-row choice (MESO-COUNT-1 may swap in a count-aligned variant): a sidecar row may name
            # ring_module + ring_params (+ ring_ports for extra receiver pins); the default is today's ring.
            rmod = r.get("ring_module", "ot_dp_clk_landing")
            if not re.fullmatch(r"ot_dp_clk_landing\w*", rmod):
                raise LandingError(f"clock landing {pid}: ring_module {rmod} is not an ot_dp_clk_landing variant")
            rpar, rports = dict(r.get("ring_params", {})), dict(r.get("ring_ports", {}))
            for k, v in list(rpar.items()) + list(rports.items()):
                if not re.fullmatch(r"[A-Za-z_]\w*", str(k)) or not re.fullmatch(r"[\w'\[\]:]+", str(v)):
                    raise LandingError(f"clock landing {pid}: bad ring_params/ring_ports entry {k}={v}")
            if {"W", "fclk", "clk", "rst_n", "d", "q", "ready", "fault"} & (set(rpar) | set(rports)):
                raise LandingError(f"clock landing {pid}: ring_params/ring_ports may not override the bound ring pins or W")
            rca = ca_port(self.ca, pid)     # CA-MIXED-1: per-landing form (whole network without count_aligned.mixed)
            capture = legacy_input_freg(plan, self.parts[dp]["type"], db)
            if capture and (rca or rmod != "ot_dp_clk_landing"):
                raise LandingError(f"{pid}: input FREG requires the legacy ring, not a count-aligned variant")
            if rmod == "ot_dp_clk_landing" and "FREG" in rpar and int(rpar["FREG"]) != int(capture):
                raise LandingError(f"{pid}: legacy FREG parameter must match its explicit plan selection")
            if capture:
                rpar["FREG"] = 1
            qreg = output_qreg(plan, self.parts[dp]["type"], db)   # CLAND-QREG-1: +1 data cycle on q
            if "QREG" in rpar and int(rpar["QREG"]) != int(qreg):
                raise LandingError(f"{pid}: ring QREG parameter must match its explicit plan selection")
            if qreg and not rca:
                rpar["QREG"] = 1
            cycles = (ring_cycles(self.ca, pid) if self.ca and not rca else 3) + int(capture) + int(qreg)
            if (capture or qreg) and int(r.get("added_cycles", cycles)) != cycles:
                raise LandingError(f"{pid}: legacy landing added_cycles must be {cycles}")
            row = dict(r, src_bus=sb, dst_bus=db, added_cycles=cycles,
                       module=rmod, ring_params=rpar, ring_ports=rports,
                       ring_depth=int(rpar.get("DEPTH", 4)), ring_offset=int(rpar.get("K", 2)),
                       ring_read_registered=True)
            if self.mixed:
                row["landing_form"] = "count_aligned" if rca else "ring"
            if rca:
                if "ring_module" in r or "ring_params" in r or "ring_ports" in r:
                    raise LandingError(f"clock landing {pid}: per-row ring_module/params/ports and the table "
                                       "count_aligned form are exclusive")
                c = self.ca["ports"].get(pid)
                if c is None:
                    raise LandingError(f"count-aligned landing {pid}: no K/DEPTH/latency in the bind table")
                if int(c["depth"]) not in (4, 8, 16):
                    raise LandingError(f"count-aligned landing {pid}: DEPTH {c['depth']} not 4/8/16")
                import count_align_bind as CAB
                reader_depth = CAB.reader_start_depth(plan, self.parts[dp]["type"])
                writer_depth = CAB.writer_start_depth(plan, self.parts[sp]["type"], sb)
                check_ca_freg_declared(plan, self.parts[dp]["type"], db, c, pid)   # FREG-DECL-1
                if bool(qreg) != bool(c.get("output_qreg")):
                    raise LandingError(f"count-aligned landing {pid}: plan landing_output_qreg and the bind sidecar "
                                       "output_qreg disagree (the event must raise sched_lat and K by 1 and mark the port)")
                row.update(added_cycles=int(c["sched_lat"]), module="ot_dp_clk_landing_cas" if self.strap else
                           "ot_dp_clk_landing_ca", ring_depth=int(c["depth"]),
                           ring_offset=None, ring_k=int(c["K"]) - reader_depth + writer_depth - int(qreg),
                           start_tree_port=bool(c["tree"]))
                if reader_depth:
                    row.update(reader_start_depth=reader_depth, logical_ring_k=int(c["K"]),
                               boot_extra_cycles=reader_depth, steady_data_cycles_added=0)
                if writer_depth:
                    row.update(writer_start_depth=writer_depth, logical_ring_k=int(c["K"]),
                               boot_extra_cycles=reader_depth + writer_depth, steady_data_cycles_added=0)
            if capture:
                row["input_capture_cycles"] = 1
            if qreg:
                row["output_qreg_cycles"] = 1
            self.rows.append(row)
            self.ins[dp][db] = row
            self.outs[sp].add(sb)
            if rca:
                self.ca_ins[dp].add(db)
                self.ca_outs[sp].add(sb)
        if self.mixed:
            stale = sorted(set(self.ca["ports"]) - seen)
            if stale:
                raise LandingError(f"mixed count-aligned table: {len(stale)} bind crossings are not landed rows: {stale[:3]}")
        # All copies of a type must expose identical hardware. Re-plan a type
        # split rather than changing only the first bound replica's wrapper.
        masks = defaultdict(dict)
        for pn, p in self.parts.items():
            form = tuple((b, r["module"], tuple(sorted(r["ring_params"].items())), tuple(sorted(r["ring_ports"].items())))
                         for b, r in sorted(self.ins[pn].items()))
            # CA-MIXED-1: which output buses forward a start (cland_fstart_out) is part of the type's hardware too
            mask = (tuple(sorted(self.ins[pn])), tuple(sorted(self.outs[pn])), form, tuple(sorted(self.ca_outs[pn])))
            masks[p["type"]].setdefault(mask, []).append(pn)
        bad = {tn: list(ms.values()) for tn, ms in masks.items() if len(ms) > 1}
        if bad:
            raise LandingError(f"clock landing TYPE_SPLIT required: {bad}")
        self.intra_in, self.intra_out, self.intra_links = defaultdict(set), defaultdict(set), []
        if self.region_monitor:
            self._region_links(ports)
        self.ca_type = self._count_aligned_types() if self.ca else {}
        self.by_type = {}
        self.ca_by_type = {}
        for tn, ms in masks.items():
            mask = next(iter(ms))
            self.by_type[tn] = dict(inputs=mask[0], outputs=mask[1])
            pn0 = ms[mask][0]
            self.ca_by_type[tn] = dict(inputs=tuple(sorted(self.ca_ins[pn0])), outputs=mask[3])
            if not require_geometry:
                continue
            declared = {b["name"]: b for b in self.types[tn].get("buses", [])}
            contract=self.types[tn].get("clock",{}).get("landing_contract",{})
            for pin in contract.get("pins",[]):
                declared[pin["name"]]=dict(pin,width=1,face="interior",window_um=[0,1],layers=[pin["layer"]])
            required = {f"fclk_out_{b}": "out" for b in mask[1]}
            if self.ca:
                cm = _cam(self, tn)
                required.update({f"cland_fstart_out_{b}": "out" for b in cm["outputs"]})
                required.update({f"cland_fstart_in_{b}": "in" for b in cm["inputs"]})
                cat = self.ca_type.get(tn)
                if self.tstart:
                    required.update({pin: d for pin, d in self.tstart["type_pins"].get(tn, {}).items()})
                if cat and cat["relay_tx"]:
                    required["cland_rstart_out"] = "out"
                if cat and cat["role"][0] == "relay":
                    required["cland_rstart_in"] = "in"
                if cat and cat.get("straps"):
                    # strap pins: types[].count_straps of the declared width (like id_straps: no plan bus; the parent
                    # ties each bit with its own TIEHI/TIELO next to the pin)
                    cs = {x["name"]: int(x["width"]) for x in self.types[tn].get("count_straps", [])}
                    for sp, w in cat["straps"].items():
                        if cs.get(sp) != int(w):
                            raise LandingError(f"clock landing {tn}: declare count strap {sp}[{w}] in types[].count_straps")
                        if sp in declared:
                            raise LandingError(f"clock landing {tn}.{sp}: a count strap is not a plan bus (types[].count_straps)")
            for b in mask[0]:
                required.update({f"fclk_in_{b}": "in"})
                if not self.collector:
                    required.update({f"landing_ready_{b}": "out", f"landing_fault_{b}": "out"})
            if self.dataflow:
                # monitor="dataflow" (FALLBACK-HEAD-2, opt-in): status rides each landed data crossing; every
                # pin is named by its DATA bus, so all instances of a type expose identical ports.
                info=self.collector["types"][tn]
                if sorted(info["mask"]["inputs"])!=sorted(mask[0]) or sorted(info["mask"]["outputs"])!=sorted(mask[1]):
                    raise LandingError(f"clock landing {tn}: dataflow monitor mask differs from the landed buses")
                for b in mask[1]:
                    required.update({f"cland_up_ready_{b}":"out",f"cland_up_fault_{b}":"out"})
                for b in mask[0]:
                    required.update({f"cland_dn_ready_{b}":"in",f"cland_dn_fault_{b}":"in"})
                tb=info["mask"].get("tree_bus")
                tree_outs=set(mask[1])
                if self.region_monitor:
                    ii,io=self._region_type_mask(tn,info,ms)
                    for b in ii:required.update({f"cland_dn_ready_{b}":"in",f"cland_dn_fault_{b}":"in"})
                    for b in io:required.update({f"cland_up_ready_{b}":"out",f"cland_up_fault_{b}":"out"})
                    tree_outs|=set(io)
                if (tb is None)!=bool(info["mask"].get("observer")) or (tb is not None and tb not in tree_outs):
                    raise LandingError(f"clock landing {tn}: dataflow tree bus {tb} is not one of its landed outputs")
                if not mask[0] and not self.region_monitor:
                    raise LandingError(f"clock landing {tn}: dataflow monitor needs a landed input (ring reset)")
            elif self.collector:
                info=self.collector["types"][tn]
                if info["mask"]["active"]:
                    if not info["mask"].get("observer"):
                        required.update(cland_up_ready="out",cland_up_fault="out")
                    if info["mask"]["up_seam"]:required["fclk_out_cland_up"]="out"
                    for c in info["children"]:
                        required[c["ready"]]="in";required[c["fault"]]="in"
                        if c["seam"]:required[f"fclk_in_cland_dn_{c['index']}"]="in"
            for name, direction in required.items():
                b = declared.get(name)
                if not b or b.get("dir") != direction or int(b.get("width", 0)) != 1:
                    raise LandingError(f"clock landing {tn}: declare placed scalar {direction} pin {name}")
                if not all(k in b for k in ("face", "window_um", "layers")):
                    raise LandingError(f"clock landing {tn}.{name}: missing physical pin geometry")

    def _region_links(self, ports):
        """monitor="region": the composed plan's same-region status ports cland_mon_{ready,fault}__<pid> whose pid is a
        plan port that is NOT a landed row (both ends in one clock region).  Fails closed on a half pair, a landed pid,
        a region-crossing pid or a pin name that does not follow the data bus."""
        rows = {r["port"] for r in self.rows}
        seen = defaultdict(set)
        # compose moves its cland_* pins to clock.landing_network.edges (infra edges); a hand plan may keep them as ports
        for p in list(self.plan["ports"]) + list(self.plan.get("clock", {}).get("landing_network", {}).get("edges", [])):
            m = re.fullmatch(r"cland_mon_(ready|fault)__(.+)", p["id"])
            if not m or m.group(2) in rows:
                continue
            kind, pid = m.groups()
            d = ports.get(pid)
            if d is None:
                raise LandingError(f"clock landing region monitor: {p['id']} names no plan port {pid}")
            sp, sb, dp, db = d["src"]["part"], d["src"]["bus"], d["dst"]["part"], d["dst"]["bus"]
            if (p["src"]["part"], p["src"]["bus"], p["dst"]["part"], p["dst"]["bus"]) != (sp, f"cland_up_{kind}_{sb}", dp, f"cland_dn_{kind}_{db}"):
                raise LandingError(f"clock landing region monitor: {p['id']} pins do not follow data port {pid}")
            if int(p.get("width", 1)) != 1:
                raise LandingError(f"clock landing region monitor: {p['id']} is not scalar")
            if sp not in self.parts or dp not in self.parts or self.region.get(sp) != self.region.get(dp):
                raise LandingError(f"clock landing region monitor: {pid} is not a same-region partition link")
            if db in self.ins[dp]:
                raise LandingError(f"clock landing region monitor: {dp}.{db} is both landed and same-region")
            seen[(pid, sp, sb, dp, db)].add(kind)
        for key, kinds in sorted(seen.items()):
            if kinds != {"ready", "fault"}:
                raise LandingError(f"clock landing region monitor: {key[0]} lacks a ready/fault pair")
            pid, sp, sb, dp, db = key
            self.intra_links.append(key)
            self.intra_out[sp].add(sb)
            self.intra_in[dp].add(db)

    def _region_type_mask(self, tn, info, ms):
        """Same-region monitor pins of type tn: identical on every instance and equal to the sidecar mask."""
        ii, io = info["mask"].get("intra_inputs", []), info["mask"].get("intra_outputs", [])
        for names in ms.values():
            for pn in names:
                got_i, got_o = sorted(self.intra_in[pn]), sorted(self.intra_out[pn] - self.outs[pn])
                if got_i != sorted(ii) or got_o != sorted(b for b in io if b not in self.outs[pn]):
                    raise LandingError(f"clock landing {tn}: region monitor pins of {pn} {got_i}/{got_o} differ from the sidecar {ii}/{io}")
        return sorted(ii), sorted(b for b in io if b not in set(next(iter(ms))[1]))

    def _region_reset(self, tn, key, body, logic, xy):
        """Raw (pre-START) reset for a region-monitor type WITHOUT a landed input: the nearest tap's timed wavefront
        relay copied at the same parent/depth (as the ring resets), or the delivered rst_n of a hard wrapper."""
        info = self.collector["types"][key]
        if (info.get("tree") or {}).get("hard"):
            if not re.search(r"\bwire rst_n = arst_n;", body):
                raise LandingError(f"{tn}: hard wrapper delivered reset rst_n not found (region monitor)")
            # AUTOBUILD-PIPE-5 10-31: one local pin register on clk (HARD_DEPTH = 1), never the raw arst_n port
            logic += ["    wire cland_reset_monitor;",
                      "    ot_dp_rrelay u_cland_rst_monitor (.clk(clk), .d(rst_n), .q(cland_reset_monitor));"]
            return "cland_reset_monitor", dict(net="cland_reset_monitor", xy_um=xy, copied_raw_parent="arst_n (delivered)",
                                               extra_control_flops=1, hard_wrapper=True)
        taps = ring_taps(self.plan, key)
        tap = min(range(len(taps)), key=lambda i: abs(taps[i][0]-xy[0]) + abs(taps[i][1]-xy[1])) if taps else 0
        reset = f"rst_n_t{tap}"
        relay = re.search(r"ot_dp_r(gate|relay)(?:_nl)?\s+\w+\s*\([^;]*?\.d\(([^)]+)\)[^;]*?\.q\(" + reset + r"\)\);", body)
        if relay is None:
            raise LandingError(f"{tn}: timed local wavefront reset relay {reset} not found (region monitor)")
        if relay.group(1) == "gate":
            reset = "cland_reset_monitor"
            logic += [f"    wire {reset};", f"    ot_dp_rrelay u_cland_rst_monitor (.clk(clk), .d({relay.group(2)}), .q({reset}));"]
        return reset, dict(net=reset, xy_um=list(taps[tap]) if taps else xy, copied_raw_parent=relay.group(2),
                           extra_control_flops=int(relay.group(1) == "gate"), must_be_ready_before_start=True)
    def _count_aligned_types(self, raise_split=True):
        """Count-aligned form (opt-in): one count origin per region; every copy of a type gets identical ring parameters
        and origin role, else TYPE_SPLIT.  Without a bind "parts" block (MESO-INTEG-1) a region must hold one landed
        partition.  With it (DIE-KV-3/CAORIGIN, COORD 21:14 ASK 3) the region's origin partition hosts the origin and a
        tx relay flop driving cland_rstart_out; every other landed partition of the region is a relay: rx flop on
        cland_rstart_in = its start (count_align_bind RELAY_STAGES = 2 = tx + rx)."""
        ca = self.ca
        regs = defaultdict(list)
        frames = ca.get("frame_clock_regions")
        if frames is not None:
            # Optional independent count origins on one physical clock group.
            # Physical clocks, masks and same-region data/status links continue
            # to use self.region; only START origin/count-frame grouping changes.
            if not ca.get("parts"):
                raise LandingError("count frame clock map requires explicit partition roles")
            for pn, pi in ca["parts"].items():
                if pn in self.parts and frames.get(pi["region"]) != self.region[pn]:
                    raise LandingError(f"count frame clock mismatch for {pn}")
        for pn in self.parts:
            # CA-MIXED-1: only partitions with a count-aligned crossing hold count frames (ring-only ones keep none)
            if _ca_in(self, pn) or _ca_out(self, pn):
                frame = ca["parts"][pn]["region"] if frames is not None else self.region[pn]
                regs[frame].append(pn)
        cparts = ca.get("parts")
        multi = {r: ps for r, ps in regs.items() if len(ps) > 1}
        if multi and cparts is None:
            raise LandingError("count-aligned landing needs one partition per region (intra-region start distribution "
                               f"is not built): {dict(list(multi.items())[:3])}")
        ports = {r["port"]: r for r in self.rows}
        out, per_type = {}, defaultdict(dict)
        self.ca_part_role = {}
        self.ca_part_cat = {}
        for reg, ps in sorted(regs.items()):
            rg = ca["regions"].get(reg)
            if rg is None:
                raise LandingError(f"count-aligned landing: region {reg} ({ps[0]}) not in the start tree")
            if cparts is None:
                org = ps[0]
            else:
                org = rg.get("origin_part")
                bad = [q for q in ps if q not in cparts or cparts[q]["region"] != reg]
                if bad or org not in ps or cparts[org]["role"] != "origin":
                    raise LandingError(f"count-aligned landing: region {reg} partitions {sorted(ps)} do not match the bind "
                                       f"roles (origin {org}, unknown {bad})")
                if sorted(q for q in ps if cparts[q]["role"] == "origin") != [org]:
                    raise LandingError(f"count-aligned landing: region {reg} needs exactly one origin partition")
            for pn in ps:
                if pn != org:
                    c = cparts[pn]
                    if c["role"] != "relay" or c["src"] != org or int(c["stages"]) != RELAY_STAGES:
                        raise LandingError(f"count-aligned landing: {pn} relay role {c} != relay({org}, {RELAY_STAGES})")
                    role = ("relay", org, RELAY_STAGES)
                elif rg["parent"] is None:
                    role = ("root", int(ca.get("root_settle_cycles", 64)))
                elif self.tstart and rg["tree_port"] in self.tstart["ports"]:
                    sp = self.tstart["ports"][rg["tree_port"]]
                    if sp["dst_part"] != pn or sp["src"] != rg["parent"]:
                        raise LandingError(f"count-aligned landing: start port {rg['tree_port']} does not start "
                                           f"{rg['parent']} -> {pn}")
                    role = ("child", START_PIN_IN, bool(rg["edge_fall"]), int(rg["pad"]))
                else:
                    r = ports.get(rg["tree_port"])
                    if r is None or r["dst"] != pn or r["src_region"] != rg["parent"]:
                        raise LandingError(f"count-aligned landing: tree port {rg['tree_port']} does not land {rg['parent']} -> {pn}")
                    role = ("child", r["dst_bus"], bool(rg["edge_fall"]), int(rg["pad"]))
                tx = pn == org and len(ps) > 1
                self.ca_part_role[pn] = dict(region=reg, role=role[0], origin=org, relay_tx=tx)
                sig = (tuple((b, r["ring_k"], r["ring_depth"]) for b, r in sorted(self.ins[pn].items())
                             if b in _ca_in(self, pn)),
                       role if role[0] != "relay" else role[::2], tx)
                self.ca_part_cat[pn] = dict(rings={b: dict(K=k, depth=d) for b, k, d in sig[0]}, role=sig[1], relay_tx=tx)
                if self.strap:
                    # strap form: K, PAD, EDGE_FALL, tree select and root/child are strap values, not type identity;
                    # only the relay pin list (rx in / tx out) still separates copies (residual TYPE_SPLIT)
                    sig = (tuple(sorted(_ca_in(self, pn))), role[0] == "relay", tx)
                per_type[self.parts[pn]["type"]].setdefault(sig, []).append(pn)
        bad = {tn: [ps for ps in sigs.values()] for tn, sigs in per_type.items() if len(sigs) > 1}
        self.ca_type_split = dict(types_needing_split=len(bad), type_count_before=len(per_type),
                                  type_count_after=sum(len(s) for s in per_type.values()))
        if bad and raise_split and not self.ca_variants:
            what = "relay rx/tx pins differ between copies" if self.strap else "K/DEPTH/origin differ between copies"
            raise LandingError(f"count-aligned landing TYPE_SPLIT required ({what}): "
                               f"{len(bad)} types, e.g. {dict(list(bad.items())[:2])}")
        for tn, sigs in per_type.items():
            pn0 = next(iter(sigs.values()))[0]
            out[tn] = dict(self.ca_part_cat[pn0])
            if self.strap:
                st = self.strap["types"][tn]
                o = st["origin"]
                role = out[tn]["role"]
                if role[0] != "relay" and o["form"] == "strap":
                    role = ("strap", tuple(o["tree_buses"]), o["padw"], int(self.ca.get("root_settle_cycles", 64)),
                            bool(o["root"]))
                out[tn] = dict(rings={b: dict(K=None, depth=v["depth"], kw=v["kw"]) for b, v in st["buses"].items()},
                               role=role, relay_tx=out[tn]["relay_tx"], straps=dict(st["straps"]))
        return out

    def _start_pins(self, plan):
        return start_pins(plan, self.ca)

    def validate_observer(self,binder):
        if not self.collector or not self.collector.get("observer"):return
        spec=self.collector["observer"];pn=spec["part"]
        if "OPEN" in (spec.get("module"),spec.get("instance_suffix"),spec.get("fault_port"),spec.get("ready_port")):
            raise LandingError(f"clock landing observer on {pn}: RTL module/instance/ports still OPEN in the sidecar")
        # The sidecar names the emitted wrapper member. Original ELAB paths
        # can be root-relative ("sys_face"), so use the exact binder emitter's
        # name transformation and still require one actual module/input pair.
        from bind import short_id
        matches=[ci for ci in binder.members.get(pn,[]) if binder.F.cells[ci].module==spec["module"]
                 and short_id("u_"+binder.rel_of(ci),90)==spec["instance_suffix"]]
        if len(matches)!=1:raise LandingError(f"clock landing observer: expected unique actual {pn}.{spec['module']}.{spec['instance_suffix']}")
        ci=matches[0];cell=binder.F.cells[ci]
        for port in (spec["fault_port"],spec["ready_port"]):
            if binder.G.dirs[ci].get(port)!="input" or len(cell.ports.get(port,[]))!=1:
                raise LandingError(f"clock landing observer {cell.path}.{port}: actual one-bit input required")
        self.observer_source=dict(path=cell.path,emitted_instance=spec["instance_suffix"],module=cell.module,ports=[spec["fault_port"],spec["ready_port"]],
                                  added_data_cycles=0,added_external_ports=0)

    def validate_observer_native(self, leaf_text, parse_ports):
        """gen_rtl (native, generated top) form of validate_observer: the observer module must be a declared leaf of
        the observer partition's type and expose the two named ports as ONE-BIT INPUTS in its actual header.  The
        unique instance / single existing connection is then enforced by gate_observer on the emitted body."""
        if not self.collector or not self.collector.get("observer"):return
        spec=self.collector["observer"];pn=spec["part"]
        if "OPEN" in (spec.get("module"),spec.get("instance_suffix"),spec.get("fault_port"),spec.get("ready_port")):
            raise LandingError(f"clock landing observer on {pn}: RTL module/instance/ports still OPEN in the sidecar")
        if pn not in self.parts:raise LandingError(f"clock landing observer partition {pn} missing")
        tn=self.parts[pn]["type"]
        if sum(p["type"]==tn for p in self.parts.values())!=1:
            raise LandingError(f"clock landing observer type {tn} is replicated")
        leaves=[c for c in self.types[tn].get("contents",[]) if c.get("module")==spec["module"]]
        if len(leaves)!=1:raise LandingError(f"clock landing observer: expected one {spec['module']} leaf in {tn}, found {len(leaves)}")
        ports=parse_ports(leaf_text(tn),spec["module"])
        if ports is None:raise LandingError(f"clock landing observer: module {spec['module']} not found in {tn} sources")
        for port in (spec["fault_port"],spec["ready_port"]):
            d,w=ports.get(port,(None,None))
            if d!="input" or w.replace(" ","") not in ("","[0:0]"):
                raise LandingError(f"clock landing observer {spec['module']}.{port}: actual one-bit input required (found {d} {w})")
        self.observer_source=dict(part=pn,type=tn,module=spec["module"],emitted_instance=spec["instance_suffix"],
                                  ports=dict(ready=spec["ready_port"],fault=spec["fault_port"]),gating="ready AND, fault OR",
                                  added_data_cycles=0,added_external_ports=0,check="native leaf header (gen_rtl)")

    def _branch_raw(self, tn, role, default):
        graph = getattr(self, "_raw_graphs", {}).get(tn)
        return graph.raw_for(role, default) if graph is not None else default

    def _reader_start_rtl(self, tn, bus, body, logic, type_key=None, head=""):
        """Transport the mature origin to one reader; mission/writer START stay unchanged. Returns (ring reset, body)."""
        key = type_key or tn
        cfg = self.types[key].get("clock", {}).get("landing_reader_start")
        if cfg is None:
            return "cland_start", body
        # FLOW-6 10-30 (DIE-HEAD-37 R2 attempt 1, st_str u_rrl_42 / n3_transit u_rrl_38 / st_m u_rrl_18): a plan raw
        # reset whose relay Q also drives an output port (assign rst_o_0 = rr_t7) makes that port flop feed internal
        # logic, which face_guard FAILs as 'shared' at kit synth. Such a relay becomes the existing private-RAW cell
        # ot_dp_head_raw_export_pair (same clk/D/Q, export_q <= D: same cycle, +1 flop, same site) and the reader
        # stage takes export_q; relays that drive no port are unchanged.
        outputs = set(re.findall(r"\boutput\s+(?:wire\s+|reg\s+)?(?:\[[^\]]*\]\s*)?(\w+)", head))
        private = {}
        import count_align_bind as CAB
        depth = CAB.reader_start_depth(self.plan, key)
        branch = cfg["branches"][bus]
        stages = branch.get("stages", []) if isinstance(branch, dict) else []
        if len(stages) != depth:
            raise LandingError(f"{tn}.{bus}: reader START needs exactly {depth} physical stages")
        records = []
        prev = "cland_start"
        for i, stage in enumerate(stages):
            xy, raw = stage.get("xy_um"), stage.get("raw_reset")
            raw = self._branch_raw(tn, f"reader:{bus}:{i}", raw)
            if (not isinstance(xy, list) or len(xy) != 2 or
                    any(isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x) for x in xy)):
                raise LandingError(f"{tn}.{bus}: reader START stage {i} needs finite xy_um")
            if not isinstance(raw, str) or not re.fullmatch(r"[A-Za-z_]\w*", raw):
                raise LandingError(f"{tn}.{bus}: reader START stage {i} needs a local registered raw reset")
            # Existing wavefront relays, not an invented/resetless control net.
            prior = re.search(r"\bot_dp_head_raw_export_pair\s+(\w+)\s*\([^;]*?\.q\(\s*" + re.escape(raw) +
                              r"\s*\)[^;]*?\.export_q\(\s*(" + re.escape(raw) + r"_reader_raw)\s*\)\s*\);", body, re.S)
            done = None if prior is None else dict(net=prior.group(2), instance=prior.group(1), port_net=raw,
                                                    added_flops=1, added_cycles=0)
            registered = done is not None or re.search(r"\bot_dp_rrelay(?:_nl)?\s+\w+\s*\([^;]*?\.q\(\s*" +
                                   re.escape(raw) + r"\s*\)[^;]*?\);", body + "\n" + "\n".join(logic), re.S)
            if not registered:
                raise LandingError(f"{tn}.{bus}: reader START raw reset {raw} has no registered wavefront driver")
            if done is None and (raw in outputs or any(
                    o in outputs for o in re.findall(r"\bassign\s+(\w+)\s*=\s*" + re.escape(raw) + r"\s*;", body))):
                rel = list(re.finditer(r"\bot_dp_rrelay\s+(\w+)\s*\(([^;]*?\.q\(\s*" + re.escape(raw) +
                                       r"\s*\)[^;]*?)\);", body, re.S))
                if len(rel) != 1:
                    raise LandingError(f"{tn}.{bus}: reader START raw reset {raw} drives an output port and its relay "
                                       f"is not one native body ot_dp_rrelay (private copy impossible)")
                m = rel[0]
                done = dict(net=f"{raw}_reader_raw", instance=m.group(1), port_net=raw, added_flops=1, added_cycles=0)
                body = (body[:m.start()] + f"ot_dp_head_raw_export_pair {m.group(1)} ({m.group(2).rstrip()}, "
                        f".export_q({done['net']}));" + body[m.end():])
                logic += [f"    wire {done['net']};  // FLOW-6 private reader START raw copy ({raw} drives an output port)"]
            if done is not None:
                private[raw] = done
                raw = done["net"]
            name = f"u_cland_reader_start_{ident(bus)}_{i}"
            net = f"cland_reader_start_{ident(bus)}_{i}"
            logic += [f"    wire {net};",
                      f'    (* keep = "true" *) ot_dp_landing_relay {name} (.clk(clk), .rst_raw_n({raw}), '
                      f".d({prev}), .q({net}));"]
            records.append(dict(instance=name, net=net, d=prev, xy_um=list(xy), raw_reset=raw,
                                stage=i, control_cycles_added=depth, steady_data_cycles_added=0))
            prev = net
        self.reset_placements.setdefault(tn, {})[bus]["reader_start"] = dict(
            depth=depth, stages=records, ring_reset=prev, K_adjustment=-depth,
            boot_extra_cycles=depth, steady_data_cycles_added=0,
            qualification="local raw-reset release and actual placed hops require plan timing",
            **({"private_raw_copies": private} if private else {}))
        return prev, body

    def _writer_start_rtl(self, tn, bus, head, body, logic, type_key=None):
        """W1 (DIE-HEAD-38): transport the sender's SAFE start_d (second sampler, never the first synchroniser
        stage) through W kept relays to the FSTART face flop of one output bus. Returns the face flop's D net."""
        key = type_key or tn
        cfg = self.types[key].get("clock", {}).get("landing_writer_start")
        if cfg is None or bus not in cfg.get("branches", {}):
            return "cland_start_d"
        import count_align_bind as CAB
        depth = CAB.writer_start_depth(self.plan, key)
        branch = cfg["branches"][bus]
        stages = branch.get("stages", []) if isinstance(branch, dict) else []
        reuse = cfg.get("reuse_relay_origin", False)
        if not isinstance(reuse, bool):
            raise LandingError(f"{tn}: reuse_relay_origin must be boolean")
        if reuse and (self.ca_type.get(key, {}).get("role", (None,))[0] != "relay" or
                      not self.types[key].get("landing_relay_start_copy", False)):
            raise LandingError(f"{tn}: writer origin reuse requires the actual registered relay origin")
        if reuse and depth < 2:
            raise LandingError(f"{tn}: relay-origin writer reuse needs phase >= 2")
        physical_depth = depth - int(reuse)
        if len(stages) != physical_depth:
            raise LandingError(f"{tn}.{bus}: writer START needs exactly {physical_depth} physical stages (new stages for phase {depth})")
        outputs = set(re.findall(r"\boutput\s+(?:wire\s+|reg\s+)?(?:\[[^\]]*\]\s*)?(\w+)", head))
        records = []
        prev = "cland_start" if reuse else "cland_start_d"
        for i, stage in enumerate(stages):
            xy, raw = stage.get("xy_um"), stage.get("raw_reset")
            raw = self._branch_raw(tn, f"writer:{bus}:{i}", raw)
            if (not isinstance(xy, list) or len(xy) != 2 or
                    any(isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x) for x in xy)):
                raise LandingError(f"{tn}.{bus}: writer START stage {i} needs finite xy_um")
            if not isinstance(raw, str) or not re.fullmatch(r"[A-Za-z_]\w*", raw):
                raise LandingError(f"{tn}.{bus}: writer START stage {i} needs a local registered raw reset")
            registered = re.search(r"\bot_dp_rrelay(?:_nl)?\s+\w+\s*\([^;]*?\.q\(\s*" +
                                   re.escape(raw) + r"\s*\)[^;]*?\);", body + "\n" + "\n".join(logic), re.S)
            if not registered:
                raise LandingError(f"{tn}.{bus}: writer START raw reset {raw} has no registered wavefront driver")
            # a port flop must feed only its port (face_guard 'shared'): the plan picks a non-port relay
            if raw in outputs or any(o in outputs for o in
                                     re.findall(r"\bassign\s+(\w+)\s*=\s*" + re.escape(raw) + r"\s*;", body)):
                raise LandingError(f"{tn}.{bus}: writer START raw reset {raw} drives an output port; "
                                   f"plan a non-port registered relay")
            name = f"u_cland_writer_start_{ident(bus)}_{i}"
            net = f"cland_writer_start_{ident(bus)}_{i}"
            logic += [f"    wire {net};",
                      f'    (* keep = "true" *) ot_dp_landing_relay {name} (.clk(clk), .rst_raw_n({raw}), '
                      f".d({prev}), .q({net}));"]
            records.append(dict(instance=name, net=net, d=prev, xy_um=list(xy), raw_reset=raw,
                                stage=i, control_cycles_added=depth, steady_data_cycles_added=0))
            prev = net
        self.reset_placements.setdefault(tn, {}).setdefault(bus, {})["writer_start"] = dict(
            depth=depth, stages=records, fstart_d=prev, K_adjustment_at_receiver=depth,
            **(dict(reused_origin_stage=1, added_flops=len(records)) if reuse else {}),
            boot_extra_cycles=depth, steady_data_cycles_added=0,
            qualification="local raw-reset release and actual placed hops require plan timing")
        return prev

    def type_rtl(self, tn, text, base=None, inst=None, depth=None):
        """Emit actual landing hardware before each incoming boundary/station.

        Existing data/epoch buses and their station chains stay intact. The
        landing streams ALL bits before the original capture, including epoch.
        """
        # A binder type split (T__vN, split_of=T) copies plan type T with different R8 pad depths only; the landing
        # hardware is per plan type (mask uniformity over all T instances is checked in __init__).
        key = base or tn
        mask = self.by_type[key]
        # CA-MIXED-1: the count-aligned subset of the type's landed buses (all of them without count_aligned.mixed)
        cmask = _cam(self, key)
        reader_cfg = self.types[key].get("clock", {}).get("landing_reader_start")
        if reader_cfg is not None:
            if not self.ca:
                raise LandingError(f"{tn}: landing_reader_start requires count-aligned rings")
            if set(reader_cfg.get("branches", {})) != set(cmask["inputs"]):
                raise LandingError(f"{tn}: landing_reader_start branches must cover exactly every input ring")
        writer_cfg = self.types[key].get("clock", {}).get("landing_writer_start")
        if writer_cfg is not None:
            if not self.ca or not self.strap:
                raise LandingError(f"{tn}: landing_writer_start requires strap-form count-aligned rings")
            if not writer_cfg.get("branches") or not set(writer_cfg["branches"]) <= set(cmask["outputs"]):
                raise LandingError(f"{tn}: landing_writer_start branches must name output rings of the type")
        collector_info=self.collector["types"][key] if self.collector else None
        active_collector=collector_info and collector_info["mask"]["active"]
        if not mask["inputs"] and not mask["outputs"] and not active_collector:
            if self.types[key].get('clock', {}).get('landing_origin_clock_port') is not None:
                raise LandingError(f'{tn}: landing_origin_clock_port needs active dedicated START origin hardware')
            self.emitted_types.add(tn)
            return text
        marker = "\n);\n"
        if marker not in text:
            raise LandingError(f"{tn}: binder ANSI module header not found")
        head, body = text.split(marker, 1)
        extra, logic = [], []
        cat = self.ca_type.get(key) if self.ca else None
        status_copy = self.types[key].get("landing_control_status_copy", False)
        if not isinstance(status_copy, bool):
            raise LandingError(f"{tn}: landing_control_status_copy must be a boolean")
        if status_copy and not cat:
            raise LandingError(f"{tn}: landing_control_status_copy needs count-aligned rings")
        # STATUS-REG-1 (KV-SLGLAND-2 11-07, opt-in): ring status crossings end at private per-slot flops; no data cycle
        status_reg = self.types[key].get("landing_status_reg", False)
        if not isinstance(status_reg, bool):
            raise LandingError(f"{tn}: landing_status_reg must be a boolean")
        # DIE-QC-97 (c): die-wide STATUS_REG on every count-aligned ring (plan clock.landing_ring_status_reg)
        if cat and ring_status_reg_all(self.plan.get("clock")):
            status_reg = True
        # GUARD-REG-1 (CLAND-RING-NEGEDGE): guard compare off the half-cycle path; needs (and turns on) STATUS_REG
        guard_reg = self.types[key].get("landing_guard_reg", False)
        if not isinstance(guard_reg, bool):
            raise LandingError(f"{tn}: landing_guard_reg must be a boolean")
        if cat and ring_guard_reg_all(self.plan.get("clock")):
            guard_reg = True
        if guard_reg and not cat:
            raise LandingError(f"{tn}: landing_guard_reg needs count-aligned rings")
        status_reg = status_reg or guard_reg
        if status_reg and not cat:
            raise LandingError(f"{tn}: landing_status_reg needs count-aligned rings")
        if inst is not None:
            # MESO-STRAP-1 LEC reference: the parameter wrapper of ONE copy (ca_variants), ring DEPTH from `depth`
            # (the strap master's per-bus DEPTH) so the two forms differ only in parameters vs tied straps
            if self.strap or not self.ca_variants:
                raise LandingError("type_rtl(inst=...) needs the parameter form with ca_variants=True")
            cat = json.loads(json.dumps(self.ca_part_cat[inst]))
            cat["role"] = tuple(cat["role"])
            for b, d in (depth or {}).items():
                cat["rings"][b]["depth"] = int(d)
        if self.types[key].get('clock', {}).get('landing_origin_clock_port') is not None and not cat:
            raise LandingError(f'{tn}: landing_origin_clock_port needs count-aligned START origin hardware')
        # DIE-HEAD-10 FSTART out (strap form, every origin but an intra-region relay rx): each forwarded start pin
        # cland_fstart_out_<b> is the Q of its OWN face flop u_cland_fstart_<b> (ot_dp_landing_relay on the region
        # start's raw reset, d = the start's D-side), equal to cland_start every cycle (0 added cycles); internal
        # loads keep cland_start.  Parameter forms and relay rx partitions keep the shared start.
        relay_copy = self.types[key].get("landing_relay_start_copy", False)
        if not isinstance(relay_copy, bool):
            raise LandingError(f"{tn}: landing_relay_start_copy must be a boolean")
        if relay_copy and (not cat or not self.strap or cat["role"][0] != "relay"):
            raise LandingError(f"{tn}: landing_relay_start_copy needs a strap-form relay origin")
        face_start = bool(cat) and bool(self.strap) and (cat["role"][0] != "relay" or relay_copy)
        raw_graph = None
        raw_cfg = self.types[key].get("clock", {}).get("landing_raw_branches")
        if raw_cfg is not None:
            # DIE-KV-58 10-31: also a strap-form origin with FSTART face flops (face_start), whose START-TREE origin
            # and face flops take the same literal copies (consumers origin / fstart:<bus>)
            if not cat or not face_start:
                raise LandingError(f"{tn}: literal START raw branches require a registered relay origin or a strap origin with FSTART face flops")
            from landing_raw_branches import RawBranches
            raw_graph = RawBranches(tn, raw_cfg, body, self.types[key].get("outline_um"))
            if not hasattr(self, "_raw_graphs"):
                self._raw_graphs = {}
            self._raw_graphs[tn] = raw_graph
            logic.extend(raw_graph.rtl)
            self.reset_placements.setdefault(tn, {})["local_resets"] = list(raw_graph.rows)
        if cat:
            logic.append("    wire cland_start;  // count origin of this region (count-aligned landings)")
            if face_start:
                logic.append("    wire cland_start_d, cland_start_raw;  // D-side + raw reset of cland_start (FSTART face flops)")
        ca_raw = {}
        # DIE-HEAD-9 FACE (c): a forwarded clock output is sourced in RTL from the SAME port its landing contract
        # declares (source_clock_port, which also feeds create_generated_clock -source and export_tcl); default clk.
        exp_src = {q["name"]: q["source_clock_port"]
                   for q in self.types[key].get("clock", {}).get("landing_contract", {}).get("pins", [])
                   if q.get("kind") == "clock" and q.get("dir") == "out" and q.get("source_clock_port")}

        def _exp(name):
            s_ = exp_src.get(name, "clk")
            if s_ != "clk" and not re.search(r"\binput\s+(?:wire\s+)?" + re.escape(s_) + r"\b", head):
                contract = self.types[key].get("clock", {}).get("landing_contract", {})
                if contract.get("forwarded_clock_only_inputs") is not True:
                    raise LandingError(f"{tn}: {name} contract source_clock_port {s_} is not an input port of the type")
                # The logical leaf may have one clock while its physical
                # wrapper has several planned tap inputs. Expose ONLY a tap
                # already in that physical interface, used by an actual clock
                # export. Do not remap any data or leaf clock.
                import schema
                if not hasattr(self, "_physical_clock_plan"):
                    self._physical_clock_plan = schema.Plan(self.plan, getattr(self, "plan_path", None))
                planned = {n for n, _x, _y in schema.tap_grid(self._physical_clock_plan, key)}
                if s_ not in planned:
                    raise LandingError(f"{tn}: forwarded clock source {s_} is not a planned physical tap input")
                needed = self.forwarded_clock_only_inputs.setdefault(tn, [])
                if s_ not in needed:
                    needed.append(s_)
                    extra.append(f"    input wire {s_}  /* planned physical tap: forwarded-clock export only */")
            return s_
        for b in mask["outputs"]:
            extra.append(f"    output wire fclk_out_{b}")
            logic.append(f"    assign fclk_out_{b} = {_exp(f'fclk_out_{b}')};")
            if cat and b in cmask["outputs"]:
                # the sender's start, forwarded beside its bus with fclk: resets the receiver ring's write count
                extra.append(f"    output wire cland_fstart_out_{b}")
                if face_start:
                    fstart_d = self._writer_start_rtl(tn, b, head, body, logic, type_key=key)
                    fstart_raw = self._branch_raw(tn, f"fstart:{b}", "cland_start_raw")
                    logic.append(f"    ot_dp_landing_relay u_cland_fstart_{b} (.clk(clk), .rst_raw_n({fstart_raw}), "
                                 f".d({fstart_d}), .q(cland_fstart_out_{b}));")
                elif (self.types[key].get("clock", {}).get("landing_writer_start") or {}).get("branches", {}).get(b):
                    raise LandingError(f"{tn}.{b}: landing_writer_start needs an FSTART face flop (strap-form origin)")
                else:
                    logic.append(f"    assign cland_fstart_out_{b} = cland_start;")
        part = next(p for p, v in self.parts.items() if v["type"] == key)
        for b in mask["inputs"]:
            r = self.ins[part][b]
            # Plan width excludes the in-band epoch bit; physical binding has
            # the complete width+1 bundle, just like the original station.
            input_decl = re.search(r"input\s+wire\s*\[(\d+):0\]\s+" + re.escape(b) + r"\b", head)
            if not input_decl:
                raise LandingError(f"{tn}: actual bound input {b} not found (unused/stale physical hop)")
            w = int(input_decl.group(1)) + 1
            if w > int(r["width"]) + 1:
                raise LandingError(f"{tn}.{b}: bound width {w} exceeds planned bundle capacity")
            # START must remain low while the rings train. Reusing the usual
            # START-gated rst_n would start training AFTER mission launch.
            # Copy the nearest tap's raw reset relay at the SAME parent/depth.
            # This is a timed local data relay, never another synchronizer.
            t = self.types[key]
            # A bus declaration without face/window is not physical geometry.
            geom = next((x for x in t.get("buses", []) if x["name"] == b and "face" in x and "window_um" in x), None)
            if geom is None and collector_info:
                geom=collector_info.get("bus_geometry",{}).get(b)
            if geom is None:
                slot = next((x for x in t.get("ft_slots", []) if x["name"] + "_i" == b), None)
                if slot:
                    geom = dict(face=slot["in_face"], window_um=slot["in_window_um"])
            if geom is None:
                raise LandingError(f"{tn}.{b}: receiver face geometry not found")
            face = geom["face"]; at = sum(geom["window_um"]) / 2
            tw, th = t["outline_um"]
            x, y = (0 if face == "W" else tw, at) if face in "EW" else (at, 0 if face == "S" else th)
            hard_tree = collector_info and (collector_info.get("tree") or {}).get("hard")
            taps = ring_taps(self.plan, key)
            if hard_tree:
                tap, xy = None, [x, y]
            elif taps:
                tap = min(range(len(taps)), key=lambda i: abs(taps[i][0]-x) + abs(taps[i][1]-y))
                xy = list(taps[tap])
            else:
                tap, xy = 0, t.get("clock", {}).get("tap_um", [tw/2, th/2])
            if hard_tree:
                # Hard partition (no generated reset tree): the ring sits in the
                # soft wrapper at the received window, on the delivered reset
                # that the wrapper's own boundary/ft stations already use.
                if not re.search(r"\bwire rst_n = arst_n;", body):
                    raise LandingError(f"{tn}.{b}: hard wrapper delivered reset rst_n not found")
                # AUTOBUILD-PIPE-5 10-31 (KV kv3_phy hard wrapper): the delivered rst_n is the raw arst_n PORT; the
                # ring / count origin take it through one local pin register on clk (the hard partition's reset depth
                # HARD_DEPTH = 1, "its pin register only"; same form as the START-gated tap case below), so the origin
                # sampler's D cone sees a clk flop Q, never the asynchronous port (face_guard land_slot).
                reset = f"cland_reset_{b}"
                logic += [f"    wire {reset};", f"    ot_dp_rrelay u_cland_rst_{b} (.clk(clk), .d(rst_n), .q({reset}));"]
                if raw_graph is not None:
                    raw_graph.baseline_relay(logic[-1])
                self.reset_placements.setdefault(tn, {})[b] = dict(net=reset, xy_um=xy, copied_raw_parent="arst_n (delivered)",
                    extra_control_flops=1, must_be_ready_before_start=True, boot_settle_cycles=21, hard_wrapper=True)
                relay = None
            else:
                reset = f"rst_n_t{tap}"
            relay = None if hard_tree else re.search(r"ot_dp_r(gate|relay)\s+\w+\s*\([^;]*?\.d\(([^)]+)\)[^;]*?\.q\(" + reset + r"\)\);", body)
            if relay is None and not hard_tree:
                raise LandingError(f"{tn}.{b}: timed local wavefront reset relay {reset} not found")
            if hard_tree:
                pass
            elif relay.group(1) == "gate":
                reset = f"cland_reset_{b}"
                logic += [f"    wire {reset};",
                          f"    ot_dp_rrelay u_cland_rst_{b} (.clk(clk), .d({relay.group(2)}), .q({reset}));"]
                if raw_graph is not None:   # default landing ring reset relay: pre-existing state for literal raw branches
                    raw_graph.baseline_relay(logic[-1])
            if not hard_tree:
                self.reset_placements.setdefault(tn, {})[b] = dict(net=reset, xy_um=xy,
                    copied_raw_parent=relay.group(2), extra_control_flops=int(relay.group(1) == "gate"),
                    must_be_ready_before_start=True, boot_settle_cycles=21)
            extra += [f"    input wire fclk_in_{b}"]
            if cat and b in cmask["inputs"]:
                extra += [f"    input wire cland_fstart_in_{b}"]
                ca_raw[b] = reset
                reader_start, body = self._reader_start_rtl(tn, b, body, logic, type_key=key, head=head)
                # QC-PARAMWRAP 11-12: a ring realised by a signed hard child keeps the child's exact parameters; the
                # die-wide STATUS_REG / GUARD_REG / RSTREP / PLACEREP knobs only re-parameterise soft rings
                hard = hard_ring_params(self.plan, tn, b, key)
                b_status, b_guard = status_reg, guard_reg
                if hard is not None:
                    b_status, b_guard = bool(hard.get("STATUS_REG")), bool(hard.get("GUARD_REG"))
                    for flag, on in (("landing_status_reg", b_status), ("landing_guard_reg", b_guard)):
                        if self.types[key].get(flag, False) and not on:
                            raise LandingError(f"{tn}.{b}: {flag} asks for a ring parameter the signed hard child "
                                               f"u_cland_{b} does not carry (param_wrap {hard})")
                if cat.get("straps"):
                    kw = cat["rings"][b]["kw"]
                    extra += [f"    input wire [{kw-1}:0] strap_ca_k_{b}"]
                    ring_mod = f"ot_dp_clk_landing_cas #(.W({{w}}), .DEPTH({cat['rings'][b]['depth']}))"
                    ring_rst = (f".t_rst_n(cland_fstart_in_{b}), .clk(clk), .rst_n({reader_start}), "
                                f".strap_k(strap_ca_k_{b})")
                else:
                    ring_mod = (f"ot_dp_clk_landing_ca #(.W({{w}}), .DEPTH({cat['rings'][b]['depth']}), "
                                f".K({cat['rings'][b]['K']}))")
                    ring_rst = f".t_rst_n(cland_fstart_in_{b}), .clk(clk), .rst_n({reader_start})"
                if status_copy:
                    ring_mod = ring_mod[:-1] + ", .CONTROL_STATUS_COPY(1))"
                    self.reset_placements[tn][b].update(control_status_copy=True,
                        status_copy_flops=2 * int(cat["rings"][b]["depth"]), status_copy_added_cycles=0)
                if output_qreg(self.plan, key, b) or output_qreg(self.plan, tn, b):
                    ring_mod = ring_mod[:-1] + ", .QREG(1))"   # CLAND-QREG-1: +1 data cycle (row output_qreg_cycles)
                    self.reset_placements[tn][b].update(output_qreg=True, output_qreg_added_data_cycles=1)
                if b_status:
                    ring_mod = ring_mod[:-1] + ", .STATUS_REG(1))"
                    self.reset_placements[tn][b].update(status_reg=True, status_reg_added_data_cycles=0,
                                                        status_reg_added_fault_cycles=1)
                if b_guard:
                    ring_mod = ring_mod[:-1] + ", .GUARD_REG(1))"
                    self.reset_placements[tn][b].update(guard_reg=True, guard_reg_added_cycles=0)
                # HEAD-RINGHOLD-1 (COORD 10-31 14:4x (3), option A): write_edge "fall" -> the count-aligned writer
                # (slots, count, tags, t_rst_n) on the falling fclk edge (ot_dp_clk_landing_ca/_cas WFALL, DIE-HEAD-48)
                if ring_write_fall(self.plan, key) or ring_write_fall(self.plan, tn):
                    ring_mod = ring_mod[:-1] + ", .WFALL(1))"
                # WREG-1 (DIE-HEAD-58 TURNB): registered writer start + per-(slot, chunk) write-enable flops; strap form
                # only (the strap K carries the +1, count_align_bind.strap_ties)
                # a hard child's ring is built without the die-wide fanout knobs (DSREP / WRITE_CHUNK raise)
                wplan = self.plan if hard is None else dict(self.plan, clock={
                    k: v for k, v in (self.plan.get("clock") or {}).items() if k not in RING_FANOUT_KNOBS})
                wreg = ring_write_reg(wplan, key, b) or ring_write_reg(wplan, tn, b)
                dsrep = ring_read_select_copies(self.plan, key, b)
                if dsrep is None:
                    dsrep = ring_read_select_copies(self.plan, tn, b)
                if dsrep is not None and not cat.get("straps"):
                    raise LandingError(f"{tn}.{b}: landing_ring_dsrep needs the count-aligned strap form")
                if wreg:
                    if dsrep is not None and dsrep != wreg["dsrep"]:
                        raise LandingError(f"{tn}.{b}: conflicting read-select copy counts in dsrep and wreg")
                    if not cat.get("straps"):
                        raise LandingError(f"{tn}.{b}: landing_ring_wreg needs the count-aligned strap form")
                    ring_mod = ring_mod[:-1] + f", .WREG(1), .DSREP({wreg['dsrep']})" + (f", .WRITE_CHUNK({wreg.get('write_chunk', 64)})" if wreg.get("write_chunk", 64) != 64 else "") + (", .WRITE_TAIL(1)" if wreg.get("write_tail") else "") + (f", .READ_CHUNK({wreg['read_chunk']})" if wreg.get("read_chunk") else "") + (", .FREG(1))" if wreg["freg"] else ")")
                    self.reset_placements[tn][b].update(ring_wreg=1, ring_dsrep=wreg["dsrep"], ring_freg=int(wreg["freg"]),
                                                        strap_k_delta=wreg["depth"])
                    if wreg.get("write_chunk", 64) != 64:
                        self.reset_placements[tn][b]["ring_write_chunk"] = wreg["write_chunk"]
                    if wreg.get("freg_numeric_order"):
                        self.reset_placements[tn][b]["ring_freg_numeric_order"] = 1
                elif dsrep is not None:
                    ring_mod = ring_mod[:-1] + f", .DSREP({dsrep}))"
                    self.reset_placements[tn][b].update(ring_dsrep=dsrep, ring_dsrep_added_cycles=0)
                # RSTREP-1 (DIE-QC-97 (d)): the last reader-START stage becomes 1 + N kept same-D relay copies at its
                # site (ot_dp_landing_relay_rep, same instance name, 0 cycles) and the ring splits its reset loads
                if reader_start != "cland_start" and cat.get("straps") and (hard is None or "RSTREP" in hard):
                    nrep = ring_reset_copies(self.plan.get("clock"), w + 2 if self.dataflow else w,
                                             int(cat["rings"][b]["depth"]),
                                             wreg["dsrep"] if wreg else (dsrep or 1), (wreg or {}).get("read_chunk", 0))
                    if nrep:
                        rx = re.compile(r'^(    \(\* keep = "true" \*\) )ot_dp_landing_relay (u_cland_reader_start_\w+) '
                                        r'(\(.*\.q\(' + re.escape(reader_start) + r'\))\);$')
                        hits = [i for i, ln in enumerate(logic) if rx.match(ln)]
                        if len(hits) != 1:
                            raise LandingError(f"{tn}.{b}: RSTREP needs exactly one last reader START relay "
                                               f"driving {reader_start}")
                        m = rx.match(logic[hits[0]])
                        logic[hits[0]] = (f"{m.group(1)}ot_dp_landing_relay_rep #(.N({nrep})) {m.group(2)} "
                                          f"{m.group(3)}, .qx({reader_start}_x));")
                        logic.insert(hits[0], f"    wire [{nrep - 1}:0] {reader_start}_x;")
                        ring_mod = ring_mod[:-1] + f", .RSTREP({nrep}))"
                        ring_rst += f", .rst_xn({reader_start}_x)"
                        self.reset_placements[tn][b]["reader_start"].update(ring_reset_copies=nrep,
                                                                            ring_reset_copies_added_cycles=0)
                # PLACEREP-1 (DIE-QC-97): under clock.landing_ring_fanout_max every strap-form ring gets one kept copy of the
                # reader placement value per read chunk (ot_dp_clk_landing_cas PLACEREP; rings with one chunk keep none).
                # The value is 0 - strap_k, read only by the align load inside the held reset: 0 cycles, same q/ready/fault.
                if cat.get("straps") and (hard is None or "PLACEREP" in hard) and ring_place_copies(
                        self.plan.get("clock"), w + 2 if self.dataflow else w, (wreg or {}).get("read_chunk", 0)):
                    ring_mod = ring_mod[:-1] + ", .PLACEREP(1))"
                    self.reset_placements[tn][b].update(ring_place_copies=True, ring_place_copies_added_cycles=0)
                if hard is not None:
                    # fail at bind, not at kit-rtl: the bound ring must be the signed child's exact paramod
                    got = ring_mod.format(w=w + 2 if self.dataflow else w)
                    want = ("ot_dp_clk_landing_cas" if cat.get("straps") else "ot_dp_clk_landing_ca") + " #(" + ", ".join(
                        f".{k}({int(v)})" for k, v in hard.items()) + ")"
                    if re.sub(r"\s", "", got) != re.sub(r"\s", "", want):
                        raise LandingError(f"{tn}.{b}: bound ring {got} differs from its signed hard child param_wrap "
                                           f"{want}: fix the plan param_wrap (re-sign the child) or the ring knobs")
                    self.reset_placements[tn][b].update(hard_child_params=dict(hard))
                self.reset_placements[tn][b].update(ring_rst_n=reader_start, origin_raw_reset=reset)
            else:
                # per-row ring form (main: ring_module/ring_params/ring_ports sidecar); default = today's ring
                rp = dict(r.get("ring_params", {}))
                # S81-RINGHOLD-4 (a): plan clock.ring_hold.write_edge "fall" -> falling-edge ring write on plain rings
                if ring_write_fall(self.plan, key) or ring_write_fall(self.plan, tn):
                    if r["module"] == "ot_dp_clk_landing":
                        rp.setdefault("WNEG", 1)
                    elif r["module"] in ("ot_dp_clk_landing_ca", "ot_dp_clk_landing_cas"):
                        rp.setdefault("WFALL", 1)   # HEAD-RINGHOLD-1: per-row count-aligned ring, same writer edge
                rpar = "".join(f", .{k}({v})" for k, v in sorted(rp.items()))
                rpin = "".join(f", .{k}({v})" for k, v in sorted(r.get("ring_ports", {}).items()))
                ring_mod = r["module"] + " #(.W({w})" + rpar.replace("{", "{{").replace("}", "}}") + ")"
                ring_rst = f".clk(clk), .rst_n({reset}){rpin}"
            if self.dataflow:
                extra += [f"    input wire cland_dn_ready_{b}", f"    input wire cland_dn_fault_{b}"]
            if self.collector:
                logic.append(f"    wire landing_ready_{b}, landing_fault_{b};")
            else:
                extra += [f"    output wire landing_ready_{b}",f"    output wire landing_fault_{b}"]
            landed = f"cland_{b}"
            # Rename the local NET only: a `.name(` port reference on a child instance is the child's port, never
            # this wrapper's bus (gen_rtl wrappers bind leaves by name: `.lep_fault_i(lep_fault_i_q)`).
            body = re.sub(r"(?<![.\w])" + re.escape(b) + r"\b", landed, body)
            if self.dataflow:
                # ring W+2: {fault, ready} of the sender's status ride the spare padded ring bits under the same
                # forwarded write clock; no extra data cycle, no die-top status wire beside the bus.
                ring = f"cland_ring_{b}"
                logic += [f"    wire [{w+1}:0] {ring};", f"    wire [{w-1}:0] {landed};",
                          f"    assign {landed} = {ring}[{w-1}:0];",
                          f"    {ring_mod.format(w=w+2)} u_cland_{b} (",
                          f"        .fclk(fclk_in_{b}), {ring_rst}, .d({{cland_dn_fault_{b}, cland_dn_ready_{b}, {b}}}), .q({ring}),",
                          f"        .ready(landing_ready_{b}), .fault(landing_fault_{b}));",
                          f"    wire cland_ok_{b} = {ring}[{w}] && landing_ready_{b} && !landing_fault_{b};",
                          f"    wire cland_bad_{b} = landing_fault_{b} || (landing_ready_{b} && {ring}[{w+1}]);"]
                continue
            logic += [f"    wire [{w-1}:0] {landed};",
                      f"    {ring_mod.format(w=w)} u_cland_{b} (",
                      f"        .fclk(fclk_in_{b}), {ring_rst}, .d({b}), .q({landed}),",
                      f"        .ready(landing_ready_{b}), .fault(landing_fault_{b}));"]
        if cat:
            logic += self._origin_rtl(tn, cat, ca_raw, body, extra, type_key=key, head=head)
            if self.tstart and self.tstart["type_pins"].get(key, {}).get(START_PIN_OUT):
                # START-TREE: the region start leaves on ONE dedicated pin (fanned out at the die top / to a stage)
                extra.append(f"    output wire {START_PIN_OUT}")
                if face_start:
                    # DIE-KV-32 10-29 face_guard 'shared': cland_start drives the internal ring/landing loads (44-678
                    # on KV io_cor/io_ft/hub_Ei), so the pin takes its OWN face flop u_cland_tstart_o, the same form
                    # as u_cland_fstart_<b> (d = start's D-side, start's raw reset): equal to cland_start every cycle.
                    logic.append(f"    ot_dp_landing_relay u_cland_tstart_o (.clk(clk), .rst_raw_n(cland_start_raw), "
                                 f".d(cland_start_d), .q({START_PIN_OUT}));")
                else:
                    logic.append(f"    assign {START_PIN_OUT} = cland_start;")
        if self.dataflow:
            body = self._dataflow_monitor(tn, key, mask, collector_info, extra, logic, body)
        elif active_collector:
            import landing_collector as LC
            # S81-OTHERFAIL-1 11-07: the collector chain walks the plan landing_contract tree (the reset relays' and
            # landing_place.tcl's tree), never a stale landing-table copy (LC.effective_tree)
            collector_info = dict(collector_info, tree=LC.effective_tree(self.types[key], collector_info["tree"]))
            if collector_info["mask"].get("observer"):
                logic.append("    wire cland_up_ready, cland_up_fault;")
            else:extra += ["    output wire cland_up_ready", "    output wire cland_up_fault"]
            if collector_info["mask"]["up_seam"]:
                extra.append("    output wire fclk_out_cland_up")
                logic.append(f"    assign fclk_out_cland_up = {_exp('fclk_out_cland_up')};")
            sources=list(collector_info["local_sources"])
            monitor_reset_copies = []
            for ch in collector_info["children"]:
                i=ch["index"]
                extra += [f"    input wire {ch['ready']}", f"    input wire {ch['fault']}"]
                src=dict(ch,name=f"child{i}")
                if ch["seam"]:
                    extra.append(f"    input wire fclk_in_cland_dn_{i}")
                    node=ch.get("node",f"rst_n_t{ch.get('tap',0)}")
                    reset, added, copies = LC.raw_reset(collector_info["tree"], node,
                                                       body+"\n"+"\n".join(logic))
                    logic.extend(added)
                    monitor_reset_copies.extend(copies)
                    logic += [f"    wire [1:0] cland_dn_word_{i};",
                              f"    wire cland_dn_trained_{i}, cland_dn_guard_{i};",
                              f"    ot_dp_clk_landing #(.W(2)) u_cland_monitor_{i} (",
                              f"        .fclk(fclk_in_cland_dn_{i}), .clk(clk), .rst_n({reset}),",
                              f"        .d({{{ch['fault']}, {ch['ready']}}}), .q(cland_dn_word_{i}),",
                              f"        .ready(cland_dn_trained_{i}), .fault(cland_dn_guard_{i}));"]
                    src.update(ready=f"(cland_dn_word_{i}[0] && cland_dn_trained_{i} && !cland_dn_guard_{i})",
                               fault=f"(cland_dn_word_{i}[1] || cland_dn_guard_{i})")
                else:
                    ready, fault, faces = status_face(logic, i, ch["ready"], ch["fault"], ch.get("xy_um"))
                    monitor_reset_copies.extend(faces)
                    src.update(ready=ready, fault=fault)
                sources.append(src)
            if collector_info["tree"].get("hard"):
                reduction=LC.build_hard_chain(collector_info["tree"],sources)
            else:
                reduction=LC.build_local(collector_info["tree"],sources,body+"\n"+"\n".join(logic),
                    root_node=collector_info.get("collector_root_node","rst_root_n"))
            reduction["instances"] = monitor_reset_copies + reduction["instances"]
            logic.extend(reduction["rtl"])
            self.reset_placements.setdefault(tn,{})["collector"]=reduction
            if collector_info["mask"].get("observer"):
                body=gate_observer(body,self.collector["observer"])
        logic[:] = self._local_resets(tn, key, body, logic)
        if raw_graph is not None:
            self.reset_placements[tn]["literal_raw_branches"] = raw_graph.validate(body + "\n" + "\n".join(logic))
        # The former last port can carry an end-of-line comment.
        lines = head.splitlines()
        code, sep, comment = lines[-1].partition("//")
        lines[-1] = code.rstrip() + "," + ((" //" + comment) if sep else "")
        head = "\n".join(lines) + "\n" + ",\n".join(extra)
        self.emitted_types.add(tn)
        emitted = head + marker + "\n".join(logic) + "\n" + body
        return self._regional_origin_source(tn, key, emitted)

    def _regional_origin_source(self, tn, key, text):
        """Default-OFF selected TT_C source event; never grants global/physical credit."""
        cfg = self.types[key].get('clock', {}).get('landing_regional_origin')
        if not cfg or not cfg.get('enabled', False):
            return text
        if tn != 'tt_ctlm' or key != 'tt_ctlm':
            raise LandingError('regional START event supports only the selected existing tt_ctlm type')
        model_path = Path(cfg['model_file'])
        if not model_path.is_absolute():
            raise LandingError('regional START model_file must identify the exact absolute frozen snapshot')
        data = model_path.read_bytes()
        if hashlib.sha256(data).hexdigest() != cfg['model_sha256']:
            raise LandingError('regional START model content differs from its paired source event')
        from tt_regional_origin.generated_adapter import apply_generated_type
        emitted, rec = apply_generated_type(tn, text, json.loads(data), enabled=True)
        placements = self.reset_placements.setdefault(tn, {})
        rec['original_count_origin'] = placements.get('count_origin')
        placements['count_origin'] = rec
        # Existing source verifiers/land_slots must explicitly consume this new
        # kind; retaining pending consumers prevents a local source transform
        # from masquerading as a complete global reset/clock derivation.
        self.__dict__.setdefault('regional_source_pending', {})[tn] = rec['pending_consumers']
        return emitted

    def _origin_clock_port(self, tn, role, head, type_key=None):
        key = type_key or tn
        typ = getattr(self, 'types', {}).get(key, {})
        chosen = typ.get('clock', {}).get('landing_origin_clock_port')
        if chosen is None:
            return 'clk'
        if (not isinstance(chosen, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', chosen)
                or not getattr(self, 'ca', None) or getattr(self, 'strap', None)
                or role[0] != 'child' or role[1] != START_PIN_IN):
            raise LandingError(f'{tn}: landing_origin_clock_port requires a dedicated parameter START child')
        import schema
        P = schema.Plan(self.plan, getattr(self, "plan_path", None))
        grid = schema.tap_grid(P, key)
        cores = schema.core_taps(P, key)
        canonical = lambda n: re.sub(r'\[0\]$', '', n.lstrip('\\'))
        names = [canonical(n) for n, *_ in grid + cores]
        if len(names) != len(set(names)):
            raise LandingError(f'{tn}: primary clock tap canonical root collision')
        # The generator's actual primary inventories are authoritative. A name
        # resembling clk_tN is not a role; explicit secondary/forwarded roles
        # and data ports cannot overlap the selected primary interface.
        forbidden = {canonical(e['port']) for e in typ.get('clock', {}).get('edge_clocks', [])}
        forbidden.update(canonical(p['name']) for p in typ.get('pads', []))
        forbidden.update(canonical(p['name']) for p in typ.get('clock', {}).get('landing_contract', {}).get('pins', [])
                         if p.get('kind') == 'clock')
        forbidden.update(canonical(p['name']) for p in typ.get('clock', {}).get('taps', [])
                         if p.get('kind') == 'landed' or p.get('forwarded') or p.get('clock_domain', 'clk') != 'clk')
        forbidden.update(canonical(p['name']) for p in typ.get('buses', []))
        forbidden.update(canonical(p['name'] + suffix) for p in typ.get('ft_slots', []) for suffix in ('_i', '_o'))
        if chosen not in names or chosen in forbidden:
            raise LandingError(f'{tn}: origin clock {chosen} is not an unambiguous primary Plan tap')
        selected_core = [tp for n, _x, _y, tp in cores if n == chosen]
        if selected_core and typ.get('clock', {}).get('native_domains') is not None:
            import native_clock_domains as NCD
            actual = NCD.contract(P, key)
            for tp in selected_core:
                members = tp.get('core_group', {}).get('members')
                roots = {root for (inst, _module, pin), root in actual['macro_pins'].items()
                         if (any(m['inst'] == inst and m['pin'] == pin for m in members) if members
                             else tp['name'] in (inst, inst + '.' + pin))}
                if roots != {actual['core_root']}:
                    raise LandingError(f'{tn}: selected core tap is not on the actual primary native root')
        if not isinstance(head, str):
            raise LandingError(f'{tn}: origin clock requires the actual emitted RTL input header')
        clean = re.sub(r'//[^\n]*|/\*.*?\*/', '', head, flags=re.S)
        module = re.search(r'\bmodule\s+[A-Za-z_]\w*\s*\(', clean)
        if module is None:
            raise LandingError(f'{tn}: origin clock needs the emitted ANSI header')
        ports, direction, width = [], None, ''
        ident = r'(\\[^\s,]+|[A-Za-z_][A-Za-z0-9_$]*)'
        for token in clean[module.end():].split(','):
            match = re.fullmatch(r'\s*(input|output|inout)\s+(?:(?:wire|reg|logic|signed|unsigned)\s+)*(\[[^\]]*\]\s*)?' + ident + r'\s*', token)
            if match:
                direction, width, name = match.group(1), match.group(2) or '', match.group(3)
            else:
                match = re.fullmatch(r'\s*' + ident + r'\s*', token)
                if not match or direction is None:
                    raise LandingError(f'{tn}: cannot prove scalar origin clock input from emitted header')
                name = match.group(1)
            ports.append((canonical(name), name.lstrip('\\'), direction, width))
        primary_ports = [n for n, _raw, _d, _w in ports if n in names]
        if len(primary_ports) != len(set(primary_ports)):
            raise LandingError(f'{tn}: emitted clock/port canonical root collision')
        if [(d, w) for _n, raw, d, w in ports if raw == chosen] != [('input', '')]:
            raise LandingError(f'{tn}: origin clock {chosen} is not an existing scalar INPUT in emitted RTL')
        return chosen

    def _origin_rtl(self, tn, cat, ca_raw, body, extra, type_key=None, head=None):
        """The region's count origin: root = ot_dp_landing_root (fixed settle count), child = ot_dp_landing_origin on
        the start-tree port (3-FF sync of the parent's forwarded start, edge/PAD from the bind).  Its raw reset is the
        timed local raw-reset relay of the tree bus (child) / of a landed input or tap 0 (root), never START-gated.
        Intra-region relay (ASK 3): the origin partition of a multi-partition region adds the tx flop u_cland_rstart_tx
        -> cland_rstart_out; a relay partition's start is the rx flop u_cland_rstart_rx on cland_rstart_in."""
        role = cat["role"]
        origin_clock = self._origin_clock_port(tn, role, head, type_key)
        raw_logic = []
        raw_fallback = None

        def local_raw(what):
            nonlocal raw_fallback
            raw = next(iter(ca_raw.values()), None)
            if raw is None:
                if raw_fallback is not None:return raw_fallback
                m = re.search(r"ot_dp_r(gate|relay)\s+\w+\s*\([^;]*?\.d\(([^)]+)\)[^;]*?\.q\((rst_n_t0)\)\);", body)
                raw = m.group(3) if m else ("rst_n" if re.search(r"\bwire rst_n = arst_n;", body) else None)
                if raw == "rst_n":
                    # AUTOBUILD-PIPE-5 10-31: hard wrapper -- the origin's raw reset through one clk pin register
                    raw = "cland_origin_reset"
                    raw_logic.extend(["    wire " + raw + ";",
                        "    ot_dp_rrelay u_cland_origin_rst (.clk(clk), .d(rst_n), .q(cland_origin_reset));"])
                if m and m.group(1) == "gate":
                    # The count origin/relay must release before START.  Match the
                    # tap's parent and depth without inheriting its START gate.
                    raw = "cland_origin_reset"
                    raw_logic.extend(["    wire " + raw + ";",
                        f"    ot_dp_rrelay u_cland_origin_rst (.clk(clk), .d({m.group(2)}), .q({raw}));"])
                if raw is None:
                    raise LandingError(f"{tn}: {what} needs a timed raw reset relay (rst_n_t0) or delivered rst_n")
                raw_fallback = raw
            return raw
        if role[0] == "relay":
            raw = local_raw("start relay rx")
            raw = self._branch_raw(tn, "origin", raw)
            self.reset_placements.setdefault(tn, {})["count_origin"] = dict(kind="relay", raw_reset=raw, stages=role[-1])
            extra.append("    input wire cland_rstart_in")
            if getattr(self, "types", {}).get(type_key or tn, {}).get("landing_relay_start_copy", False):
                # Same D and raw reset as the existing rx flop: private export Qs
                # equal cland_start on every edge, with zero count-frame change.
                raw_logic += ["    assign cland_start_d = cland_rstart_in;",
                              f"    assign cland_start_raw = {raw};"]
            return raw_logic + [f"    ot_dp_landing_relay u_cland_rstart_rx (.clk(clk), .rst_raw_n({raw}), .d(cland_rstart_in), "
                    f".q(cland_start));"]
        if role[0] == "strap":
            logic, raw = self._origin_strap_rtl(tn, role, ca_raw, extra, local_raw)
        elif role[0] == "child":
            b = role[1]
            if b == START_PIN_IN:
                # START-TREE: the parent's start on the dedicated start pin; raw reset = a local timed relay
                raw, p_start = local_raw("start-tree origin"), START_PIN_IN
                extra.append(f"    input wire {START_PIN_IN}")
            else:
                raw, p_start = ca_raw.get(b), f"cland_fstart_in_{b}"
            if raw is None:
                raise LandingError(f"{tn}: start-tree bus {b} is not a landed input of this type")
            self.reset_placements.setdefault(tn, {})["count_origin"] = dict(kind="child", tree_bus=b, raw_reset=raw,
                                                                         edge_fall=role[2], pad=role[3])
            if getattr(self, 'types', {}).get(type_key or tn, {}).get('clock', {}).get('landing_origin_clock_port') is not None:
                self.reset_placements[tn]['count_origin']['clock_port'] = origin_clock
            logic = [f"    ot_dp_landing_origin #(.PAD({role[3]}), .EDGE_FALL({int(role[2])})) u_cland_origin (",
                     f"        .clk({origin_clock}), .rst_raw_n({raw}), .p_start({p_start}), .start(cland_start));"]
        else:
            raw = local_raw("root count origin")
            self.reset_placements.setdefault(tn, {})["count_origin"] = dict(kind="root", raw_reset=raw, settle=role[1])
            if self.strap:
                logic = [f"    ot_dp_landing_root #(.SETTLE({role[1]})) u_cland_origin (.clk(clk), .rst_raw_n({raw}), "
                         ".start(cland_start), .start_d(cland_start_d));", f"    assign cland_start_raw = {raw};"]
            else:
                # DIE-HEAD-31: parameter form has no FSTART face flop; the root's start_d (a driven OUTPUT) is still bound to
                # its own declared net so every master port is connected (port_bind_gate nested check), no tie/exemption
                logic = ["    wire cland_start_d;  // D-side of cland_start (no FSTART face flop in the parameter form)",
                         f"    ot_dp_landing_root #(.SETTLE({role[1]})) u_cland_origin (.clk(clk), .rst_raw_n({raw}), "
                         ".start(cland_start), .start_d(cland_start_d));"]
        if cat.get("relay_tx"):
            self.reset_placements[tn]["count_origin"]["relay_tx"] = True
            extra.append("    output wire cland_rstart_out")
            logic.append(f"    ot_dp_landing_relay u_cland_rstart_tx (.clk(clk), .rst_raw_n({raw}), .d(cland_start), "
                         f".q(cland_rstart_out));")
        if self.tstart and self.tstart.get("reset_wave") and RAW_RESET_PIN_OUT in self.tstart["type_pins"].get(type_key or tn,{}):
            extra.append(f"    output wire {RAW_RESET_PIN_OUT}")
            # DIE-KV-32 10-29: the face flop is an ot_dp_rrelay instance driving the port alone (a kept reg aliased
            # to the port left a BUF onto the kept wire = 1 extra load, face_guard 'shared'); same flop, same D.
            logic.append(f"    ot_dp_rrelay u_cland_raw_reset_o (.clk(clk), .d({raw}), .q({RAW_RESET_PIN_OUT}));")
        return raw_logic + logic

    def _origin_strap_rtl(self, tn, role, ca_raw, extra, local_raw):
        """MESO-STRAP-1 strap origin: ot_dp_landing_origin_s (strap_ca_pad / strap_ca_efall), the parent's forwarded
        start and the child raw reset chosen by strap_ca_tsel among the copies' tree buses. Each tree bus has its own
        origin sampler; static selection follows those samplers (out-of-range values take the last bus). An optional
        root counter is chosen by strap_ca_root. The
        raw reset of each choice is exactly the parameter form's (child: the tree bus's timed relay; root: local_raw)."""
        _, tbs, padw, settle, root = role
        copy_export = getattr(self, "types", {}).get(tn, {}).get("clock", {}).get("landing_origin_export_copy", False)
        fwd_param = ", .FWD_COPY(1)" if copy_export else ""
        ca_raw = dict(ca_raw)
        if START_PIN_IN in tbs:
            # START-TREE: the dedicated start pin is one of the choices; its raw reset is a local timed relay
            # DIE-KV-58 10-31 (GEOM-93 r2r): a plan landing_raw_branches consumer "origin" gives the START-TREE strap
            # origin a literal same-depth copy of its raw reset placed next to it (as the relay role already does);
            # absent = the first landed input's raw (byte-identical default)
            ca_raw[START_PIN_IN] = self._branch_raw(tn, "origin", local_raw("start-tree origin"))
            extra.append(f"    input wire {START_PIN_IN}")

        def pin(b):
            return START_PIN_IN if b == START_PIN_IN else f"cland_fstart_in_{b}"
        for b in tbs:
            if b not in ca_raw:
                raise LandingError(f"{tn}: start-tree bus {b} is not a landed input of this type")
        extra.append(f"    input wire [{padw-1}:0] strap_ca_pad")
        extra.append("    input wire strap_ca_efall")   # SCALAR_STRAPS
        logic = []
        multi = len(tbs) > 1
        if multi:
            tsw = (len(tbs) - 1).bit_length()
            extra.append(f"    input wire [{tsw-1}:0] strap_ca_tsel")
            def sel(names):
                e = names[-1]
                for i in range(len(names) - 2, -1, -1):
                    e = f"(strap_ca_tsel == {tsw}'d{i}) ? {names[i]} : {e}"
                return e
            raw = "cland_oraw"
            logic += [f"    wire cland_oraw = {sel([ca_raw[b] for b in tbs])};"]
        else:
            p_start, raw = pin(tbs[0]), ca_raw[tbs[0]]
        start = "cland_start"
        if root:
            extra.append("    input wire strap_ca_root")   # SCALAR_STRAPS
            rraw = local_raw("root count origin")
            # FSTART face flops of a root+child type: the static strap select picks the D-side and the raw reset
            # BEFORE the flop (never on the port net)
            logic += ["    wire cland_start_child, cland_start_root, cland_start_child_d, cland_start_root_d;",
                      f"    wire cland_raw_sel = strap_ca_root ? {rraw} : {raw};",
                      f"    ot_dp_landing_root #(.SETTLE({settle})) u_cland_root (.clk(clk), .rst_raw_n({rraw}), "
                      ".start(cland_start_root), .start_d(cland_start_root_d));",
                      "    assign cland_start = strap_ca_root ? cland_start_root : cland_start_child;",
                      "    assign cland_start_d = strap_ca_root ? cland_start_root_d : cland_start_child_d;",
                      "    assign cland_start_raw = cland_raw_sel;"]
            start, start_d, raw_used = "cland_start_child", "cland_start_child_d", "cland_raw_sel"
        else:
            raw_used, start_d = raw, "cland_start_d"
            logic.append(f"    assign cland_start_raw = {raw};")
        if multi:
            # Each START owns its sampler. Static selection follows both registered and D-side taps,
            # preserving the dedicated forwarded START face flop's existing zero-cycle contract.
            starts = [f"cland_start_t{i}" for i in range(len(tbs))]
            starts_d = [f"cland_start_t{i}_d" for i in range(len(tbs))]
            logic.append(f"    wire {', '.join(starts + starts_d)};")
            for i, b in enumerate(tbs):
                logic += [f"    ot_dp_landing_origin_s #(.PADW({padw}){fwd_param}) u_cland_origin_t{i} (",
                          f"        .clk(clk), .rst_raw_n({ca_raw[b]}), .p_start({pin(b)}), .strap_efall(strap_ca_efall), "
                          f".strap_pad(strap_ca_pad), .start({starts[i]}), .start_d({starts_d[i]}));"]
            logic += [f"    assign {start} = {sel(starts)};", f"    assign {start_d} = {sel(starts_d)};"]
        else:
            logic += [f"    ot_dp_landing_origin_s #(.PADW({padw}){fwd_param}) u_cland_origin (",
                      f"        .clk(clk), .rst_raw_n({raw}), .p_start({p_start}), .strap_efall(strap_ca_efall), "
                      f".strap_pad(strap_ca_pad), .start({start}), .start_d({start_d}));"]
        self.reset_placements.setdefault(tn, {})["count_origin"] = dict(kind="strap", tree_buses=list(tbs), padw=padw,
                                                                     root=bool(root), raw_reset=raw_used,
                                                                     **({"per_bus_origins": [f"u_cland_origin_t{i}" for i in range(len(tbs))]} if multi else {}))
        return logic, raw_used

    def _status_input_stages(self, tn, key, ins, local_outs, collect, logic):
        """DIE-HEAD-38 R2 (plan clock.landing_status_input_stages, opt-in): n registered 1-input status relays
        u_cland_sin_<target>_<ring>_<k> on ONE ring's ready/fault (agg: cland_ok/cland_bad) before the N-input
        collect of <target>, so a collect fed from opposite faces is no longer one long hop.  ready (AND) and fault
        (OR) stay monotone; that input's status is observed n cycles later; 0 data cycles."""
        cfg = self.types[key].get("clock", {}).get("landing_status_input_stages")
        res = dict(agg={}, local={}, record={})
        if cfg is None:
            return res
        if not isinstance(cfg, dict) or not cfg:
            raise LandingError(f"{tn}: landing_status_input_stages must be a non-empty object")
        for tgt, rings in sorted(cfg.items()):
            if tgt != "agg" and tgt not in local_outs:
                raise LandingError(f"{tn}: landing_status_input_stages target {tgt} is not 'agg' or a local status output")
            if not isinstance(rings, dict) or not rings:
                raise LandingError(f"{tn}: landing_status_input_stages.{tgt} must name landed input rings")
            for ring, stages in sorted(rings.items()):
                if ring not in ins:
                    raise LandingError(f"{tn}: landing_status_input_stages.{tgt}.{ring} is not a landed input ring")
                if not isinstance(stages, list) or not stages:
                    raise LandingError(f"{tn}: landing_status_input_stages.{tgt}.{ring} needs >= 1 stage")
                cur = (f"cland_ok_{ring}", f"cland_bad_{ring}") if tgt == "agg" else (f"landing_ready_{ring}", f"landing_fault_{ring}")
                for k, s in enumerate(stages):
                    xy = s.get("xy_um") if isinstance(s, dict) else None
                    if (not isinstance(xy, list) or len(xy) != 2 or
                            any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in xy)):
                        raise LandingError(f"{tn}: landing_status_input_stages.{tgt}.{ring}[{k}] needs finite xy_um")
                    ro, fo = f"cland_sin_r_{ident(tgt)}_{ident(ring)}_{k}", f"cland_sin_f_{ident(tgt)}_{ident(ring)}_{k}"
                    logic.append(f"    wire {ro}, {fo};")
                    collect(f"u_cland_sin_{ident(tgt)}_{ident(ring)}_{k}", 1, cur[0], cur[1], ro, fo)
                    cur = (ro, fo)
                (res["agg"] if tgt == "agg" else res["local"].setdefault(tgt, {}))[ring] = cur
                res["record"].setdefault(tgt, {})[ring] = dict(stages=len(stages), status_cycles_added=len(stages),
                                                               data_cycles_added=0)
        return res

    def _status_anchor_check(self, tn, key, stages):
        """landing_status_anchors may only pin status stages this generator actually emitted."""
        anc = self.types[key].get("clock", {}).get("landing_status_anchors")
        if anc is None:
            return
        if not isinstance(anc, dict) or not anc:
            raise LandingError(f"{tn}: landing_status_anchors must be a non-empty object")
        bad = sorted(set(anc) - {s for s in stages if re.fullmatch(r"u_cland_(agg_\d+|loc_\w+_\d+)", s)})
        if bad:
            raise LandingError(f"{tn}: landing_status_anchors names {bad}, not an emitted agg/loc status stage")

    def _local_resets(self, tn, key, body, logic):
        """DIE-HEAD-38 R1 (plan clock.landing_local_resets, opt-in): each listed copy is a kept ot_dp_rrelay
        u_cland_lrst_<name> (d = a registered wavefront raw relay Q) and the listed landing consumers take its Q
        on their reset pin instead of the shared reset.  Same cycle: depth(raw)+1 must equal the depth of the
        reset each consumer had, so every release edge is unchanged; anything unverifiable fails closed."""
        cfg = self.types[key].get("clock", {}).get("landing_local_resets")
        if cfg is None:
            return logic
        if not isinstance(cfg, list) or not cfg:
            raise LandingError(f"{tn}: landing_local_resets must be a non-empty list")
        text = "\n".join(logic)
        allrtl = body + "\n" + text
        memo = {}

        def depth(net, seen=()):
            if net in memo:
                return memo[net]
            if net in seen:
                raise LandingError(f"{tn}: landing_local_resets: reset loop at {net}")
            m = re.search(r"\bot_dp_r(?:relay|gate)\s+\w+\s*\(([^;]*?)\.q\(\s*" + re.escape(net) +
                          r"\s*\)\s*\);[ \t]*(?://[^\n]*?\bdepth (\d+)\b)?", allrtl, re.S)
            if m and m.group(2):
                d = int(m.group(2))
            elif m:
                pm = re.search(r"\.d\(\s*(\w+)\s*\)", m.group(1))
                if not pm:
                    raise LandingError(f"{tn}: landing_local_resets: relay of {net} has no D")
                d = depth(pm.group(1), seen + (net,)) + 1
            else:
                a = re.search(r"\bassign\s+" + re.escape(net) + r"\s*=\s*(\w+)\s*;", allrtl)
                if not a:
                    raise LandingError(f"{tn}: landing_local_resets: reset {net} has no registered wavefront depth")
                d = depth(a.group(1), seen + (net,))
            memo[net] = d
            return d
        rec, used, decl = [], set(), []
        for r in cfg:
            name, raw = r.get("name"), r.get("raw")
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_]+", name) or name in {x["name"] for x in rec}:
                raise LandingError(f"{tn}: landing_local_resets: bad or duplicate name {name!r}")
            xy = r.get("xy_um")
            if (not isinstance(xy, list) or len(xy) != 2 or
                    any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in xy)):
                raise LandingError(f"{tn}: landing_local_resets.{name} needs finite xy_um")
            if not isinstance(raw, str) or not re.search(r"\bot_dp_rrelay(?:_nl)?\s+\w+\s*\([^;]*?\.q\(\s*" + re.escape(raw) +
                                                          r"\s*\)[^;]*?\);", allrtl, re.S):
                raise LandingError(f"{tn}: landing_local_resets.{name}: raw {raw!r} has no registered wavefront driver")
            net, inst = f"cland_lrst_{name}", f"u_cland_lrst_{name}"
            cons = r.get("consumers")
            if not isinstance(cons, list) or not cons:
                raise LandingError(f"{tn}: landing_local_resets.{name} needs consumers")
            olds = {}
            for c in cons:
                if c in used:
                    raise LandingError(f"{tn}: landing_local_resets: consumer {c} listed twice")
                used.add(c)
                ms = list(re.finditer(r"(\b\w[\w#().,\s]*?\s)(" + re.escape(c) + r")(\s*\()([^;]*?)(\);)", text, re.S))
                ms = [m for m in ms if not re.search(r"\.\s*$", m.group(1))]
                if len(ms) != 1:
                    raise LandingError(f"{tn}: landing_local_resets.{name}: consumer {c} is not one emitted landing instance")
                m = ms[0]
                pins = list(re.finditer(r"\.(rst_n|rst_raw_n)\(\s*(\w+)\s*\)", m.group(4)))
                if len(pins) != 1:
                    raise LandingError(f"{tn}: landing_local_resets.{name}: consumer {c} has {len(pins)} reset pins")
                old = pins[0].group(2)
                if depth(raw) + 1 != depth(old):
                    raise LandingError(f"{tn}: landing_local_resets.{name}: consumer {c} reset {old} depth {depth(old)} != "
                                       f"copy depth {depth(raw) + 1} (raw {raw}): release edge would move")
                conn = m.group(4)[:pins[0].start()] + f".{pins[0].group(1)}({net})" + m.group(4)[pins[0].end():]
                text = text[:m.start(4)] + conn + text[m.end(4):]
                olds[c] = old
            decl += [f"    wire {net};",
                     f'    (* keep = "true" *) ot_dp_rrelay {inst} (.clk(clk), .d({raw}), .q({net}));  '
                     f"// local same-cycle reset copy (depth {depth(raw) + 1})"]
            rec.append(dict(name=name, instance=inst, net=net, raw=raw, depth=depth(raw) + 1, xy_um=list(xy),
                            replaced=olds, added_flops=1, added_cycles=0))
        self.reset_placements.setdefault(tn, {}).setdefault("local_resets", []).extend(rec)
        return decl + [text]

    def _dataflow_monitor(self, tn, key, mask, info, extra, logic, body):
        """Registered dataflow monitor: local = AND(landing_ready) / OR(landing_fault), aggregate = AND(in_ok) /
        OR(in_bad) over every landed input (in_ok includes the local ring ready), registered
        local_registered_depth times. Every output pin gets its OWN dedicated output register (the last stage):
        the tree bus carries the aggregate, every other landed output the local status (registered
        local_status_depth times: int or {bus: int}, default 1). The observer type keeps
        the aggregate on cland_up_ready/fault for gate_observer (never new IO)."""
        ins = list(mask["inputs"]); n = len(ins)
        depth = int(info["local_registered_depth"])
        if depth < 1:raise LandingError(f"{tn}: dataflow monitor depth {depth} < 1")
        rp = self.reset_placements.setdefault(tn, {})
        root_xy = info.get("collector_root_xy")
        # One existing raw ring reset (nearest to the collector root): the monitor must train before START.
        def dist(b):
            xy = rp[b]["xy_um"];return (abs(xy[0]-root_xy[0])+abs(xy[1]-root_xy[1])) if root_xy else 0, b
        if ins:
            rst = rp[min(ins, key=dist)]["net"]
        else:                                   # monitor="region" only (checked in __init__)
            rst, rp["monitor_reset"] = self._region_reset(tn, key, body, logic, root_xy or [0, 0])
        ready_l = ", ".join(f"landing_ready_{b}" for b in ins); fault_l = ", ".join(f"landing_fault_{b}" for b in ins)
        ok_l = ", ".join(f"cland_ok_{b}" for b in ins); bad_l = ", ".join(f"cland_bad_{b}" for b in ins)
        intra_in, intra_out, faced = [], [], []
        if self.region_monitor:
            intra_in = sorted(info["mask"].get("intra_inputs", []))
            intra_out = [b for b in sorted(info["mask"].get("intra_outputs", [])) if b not in mask["outputs"]]
            for b in intra_in:
                extra += [f"    input wire cland_dn_ready_{b}", f"    input wire cland_dn_fault_{b}"]
            # same-region status: the sender's dedicated output register on the SAME region clock; each pin bit is
            # captured by its OWN face flop before the reduction (status_face, +1 status cycle, 0 data cycles)
            faced = [status_face(logic, b, f"cland_dn_ready_{b}", f"cland_dn_fault_{b}") for b in intra_in]
            ok_l = ", ".join([x for x in [ok_l] if x] + [f[0] for f in faced])
            bad_l = ", ".join([x for x in [bad_l] if x] + [f[1] for f in faced])
            n = n + len(intra_in)
            if not n:                           # nothing to train or hear: ready one registered cycle after reset
                ok_l, bad_l, n = "1'b1", "1'b0", 1
            if not ins:
                ready_l, fault_l = "1'b1", "1'b0"
        stages = []
        def collect(name, N, rdy, flt, ro, fo):
            logic.extend([f"    ot_dp_landing_collect #(.N({N})) {name} (",
                          f"        .clk(clk), .rst_n({rst}), .ready_i({{{rdy}}}),",
                          f"        .fault_i({{{flt}}}), .ready_o({ro}), .fault_o({fo}));"])
            stages.append(name)
        tree_bus = info["mask"].get("tree_bus")
        lsd = info.get("local_status_depth", 1)
        def local_depth(b):
            d = lsd.get(b, 1) if isinstance(lsd, dict) else lsd
            if isinstance(d, bool) or not isinstance(d, int) or d < 1:
                raise LandingError(f"{tn}: local_status_depth {b}={d!r} is not an integer >= 1")
            return d
        if isinstance(lsd, dict):
            bad = sorted(set(lsd) - (set(mask["outputs"]) | set(intra_out)) | ({tree_bus} & set(lsd)))
            if bad:raise LandingError(f"{tn}: local_status_depth names {bad}, not a local status output")
        sin = self._status_input_stages(tn, key, ins, [b for b in list(mask["outputs"]) + intra_out if b != tree_bus],
                                        collect, logic)
        if sin["agg"]:
            ok_l = ", ".join([sin["agg"].get(b, (f"cland_ok_{b}", f"cland_bad_{b}"))[0] for b in ins] + [f[0] for f in faced])
            bad_l = ", ".join([sin["agg"].get(b, (f"cland_ok_{b}", f"cland_bad_{b}"))[1] for b in ins] + [f[1] for f in faced])
        prev = None
        for k in range(1, depth):
            ro, fo = f"cland_agg_r{k}", f"cland_agg_f{k}"
            logic.append(f"    wire {ro}, {fo};")
            if prev is None:collect(f"u_cland_agg_{k}", n, ok_l, bad_l, ro, fo)
            else:collect(f"u_cland_agg_{k}", 1, prev[0], prev[1], ro, fo)
            prev = (ro, fo)
        final_in = prev or (ok_l, bad_l)
        final_n = 1 if prev else n
        outputs = []
        for b in list(mask["outputs"]) + intra_out:
            extra += [f"    output wire cland_up_ready_{b}", f"    output wire cland_up_fault_{b}"]
            if b == tree_bus:
                collect(f"u_cland_up_{b}", final_n, final_in[0], final_in[1], f"cland_up_ready_{b}", f"cland_up_fault_{b}")
                outputs.append(dict(bus=b, carries="aggregate", registered_depth=depth))
            else:
                # local status: local_status_depth (plan field, default 1) registered stages on THIS output only
                # (DIE-HEAD-36, OWNER (A) 10-29): d-1 status relays u_cland_loc_<b>_<k> before the dedicated output
                # register, so a long source-band -> status-pin path is cut into hops <= the plan reach. Status only
                # (level ready / sticky fault, observed d-1 cycles later), 0 data cycles; d=1 is the original form.
                ldep = local_depth(b)
                lin, ln = (ready_l, fault_l), max(1, len(ins))
                if sin["local"].get(b):
                    st = sin["local"][b]
                    lin = (", ".join(st.get(r, (f"landing_ready_{r}", f"landing_fault_{r}"))[0] for r in ins),
                           ", ".join(st.get(r, (f"landing_ready_{r}", f"landing_fault_{r}"))[1] for r in ins))
                for k in range(1, ldep):
                    ro, fo = f"cland_loc_r_{b}_{k}", f"cland_loc_f_{b}_{k}"
                    logic.append(f"    wire {ro}, {fo};")
                    collect(f"u_cland_loc_{b}_{k}", ln, lin[0], lin[1], ro, fo)
                    lin, ln = (ro, fo), 1
                collect(f"u_cland_up_{b}", ln, lin[0], lin[1], f"cland_up_ready_{b}", f"cland_up_fault_{b}")
                outputs.append(dict(bus=b, carries="local", registered_depth=ldep))
        if tree_bus is None:
            spec = self.collector.get("observer") or {}
            if "OPEN" in (spec.get("module"), spec.get("instance_suffix"), spec.get("fault_port"), spec.get("ready_port")):
                raise LandingError(f"{tn}: dataflow monitor observer RTL ports still OPEN in the sidecar")
            logic.append("    wire cland_up_ready, cland_up_fault;")
            collect("u_cland_up_observer", final_n, final_in[0], final_in[1], "cland_up_ready", "cland_up_fault")
            body = gate_observer(body, self.collector["observer"])
        self._status_anchor_check(tn, key, stages)
        rp["monitor"] = dict(mode="region" if self.region_monitor else "dataflow", raw_reset=rst, depth=depth, tree_bus=tree_bus, stages=stages,
                             outputs=outputs, flops=2*len(stages), data_cycles_added=0,
                             **({"status_input_stages": sin["record"]} if sin["record"] else {}),
                             **({"status_faces": [x for f in faced for x in f[2]], "status_face_flops": 2*len(faced),
                                 "status_cycles_added": STATUS_FACE_CYCLES} if faced else {}))
        return body

    def top_rtl(self, text, emitted_modules=None):
        """Connect the new forwarded-clock pins and observed status at die top.

        Region clocks are explicit inputs. No die-top data register or clock
        synthesizer is invented; physical die-clock emission supplies them.
        """
        modules=emitted_modules or {tn:t["module"] for tn,t in self.types.items()}
        if set(modules)!=set(self.types):raise LandingError("clock landing: emitted module/type inventory changed after cohort composition")
        self.emitted_modules=dict(modules)
        clocks = sorted(set(self.region.values()))
        n = len(self.rows)
        if not n:
            self.emitted_top = True
            return text
        names = [f"clk_region_{ident(r)}" for r in clocks]
        # START-TREE: die-level start-stage nets are die-top ports like the region clocks (the die clock emission /
        # start_stage_emit.py ot_die_start_stages drives pst_<region> and reads rs_<region>)
        ts = self.tstart
        ts_in = sorted({e["net"] for e in ts["die_outputs"]}) if ts else []
        ts_out = (ts["die_input_nets"] + [e["net"] for e in ts.get("reset_inputs",[])]) if ts else []
        ts_ports = [(f"input  wire {n}", f"    input wire {n};") for n in ts_in] + \
                   [(f"output wire {n}", f"    output wire {n};") for n in ts_out]
        names += ts_in + ts_out
        local_observer=self.collector and self.collector.get("observer")
        if not local_observer:names += ["clock_landing_ready", "clock_landing_fault"]
        match = re.search(r"(?m)^module (\w+) \(([^;]*)\);", text)
        if not match:
            raise LandingError("clock landing: binder non-ANSI die header not found")
        # gen_rtl (native generated top, LAND-HEAD-BIND-1) emits an ANSI header whose only clock is the die `clk`
        # feeding every partition clock pin (.clk / grid .clk_t<i> / early-core .clk_c<i>).  In the landed form each partition's
        # pins are its REGION clock; the die `clk` port is then unread and removed (the die clock emission supplies
        # the region clocks).  The binder's non-ANSI path below is unchanged.
        ansi = re.search(r"\b(input|output)\b", match.group(2)) is not None
        if ansi:
            if not local_observer:
                raise LandingError("clock landing: native (ANSI) top requires a local observer (dataflow monitor)")
            ports = match.group(2).rstrip()
            ports = re.sub(r"\n    input  wire clk,(?=\n)", "", ports, count=1)
            header = (f"module {match.group(1)} (" + ports + "".join(f",\n    input  wire clk_region_{ident(r)}" for r in clocks)
                      + "".join(f",\n    {a}" for a, _ in ts_ports) + "\n);")
        else:
            header = f"module {match.group(1)} ({match.group(2)}, " + ", ".join(names) + ");"
        text = text[:match.start()] + header + text[match.end():]
        decl = [] if ansi else [f"    input wire clk_region_{ident(r)};" for r in clocks] + [d for _, d in ts_ports]
        if not local_observer:
            decl += (["    output wire clock_landing_ready;","    output wire clock_landing_fault;"] if self.collector else
                     [f"    output wire [{n-1}:0] clock_landing_ready;",f"    output wire [{n-1}:0] clock_landing_fault;"])
        fwd = {(r["src"], r["src_bus"]): f"clock_landing_fwd_{ident(r['src'])}__{ident(r['src_bus'])}"
               for r in self.rows}
        decl += [f"    wire {w};" for w in sorted(set(fwd.values()))]
        # CA-MIXED-1: a start wire only beside a count-aligned sender bus
        fst = {k: v.replace("clock_landing_fwd_", "clock_landing_start_", 1) for k, v in fwd.items()
               if k[1] in _ca_out(self, k[0])} if self.ca else {}
        decl += [f"    wire {w};" for w in sorted(set(fst.values()))]
        tsw, tsi, trw = {}, {}, {}

        # KV-PLAN-2 11-09 (KV bind9c2 die_port_bind: 174 TOP_ASSIGN, 174 undriven + 172 unread bits): a launch partition
        # whose start / raw reset leaves the die top through exactly one DECLARED net (rs_* / rraw_* output port) drives
        # that net directly instead of a clock_landing_* wire plus a top-level alias assign.  Same connectivity; the die
        # top stays pure wiring.  Several nets per source, or a net not declared in the top, keep the wire + assign.
        def _declared(net):
            # the rs_* / rraw_* die-top output ports are emitted by this pass (ts_out); other nets must already be in the text
            if net in ts_out:
                return True
            return re.search(r"(?m)^\s*(?:output\s+wire|wire)\s+(?:\[[^\]]*\]\s*)?" + re.escape(net) + r"\s*[;,]",
                             text) is not None

        def _direct(edges):
            nets = defaultdict(set)
            for e in edges:
                nets[e["src_part"]].add(e["net"])
            return {sp: next(iter(ns)) for sp, ns in nets.items() if len(ns) == 1 and _declared(next(iter(ns)))}
        if ts:
            # one start wire per launch partition (its single cland_tstart_out, fanned out here)
            tsw = {e["src_part"]: f"clock_landing_tstart_{ident(e['src_part'])}" for e in ts["plan_ports"] + ts["die_inputs"]}
            tsw.update(_direct(ts["die_inputs"]))
            decl += [f"    wire {w};" for w in sorted(set(tsw.values())) if w.startswith("clock_landing_tstart_")]
            tsi = {e["dst_part"]: tsw[e["src_part"]] for e in ts["plan_ports"]}
            tsi.update({e["dst_part"]: e["net"] for e in ts["die_outputs"]})
            decl += [f"    assign {e['net']} = {tsw[e['src_part']]};"
                     for e in sorted({e["net"]: e for e in ts["die_inputs"]}.values(), key=lambda e: e["net"])
                     if e["net"] != tsw[e["src_part"]]]
        if ts and ts.get("reset_wave"):
            trw = {pn:f"clock_landing_raw_reset_{ident(pn)}" for pn,p in self.parts.items()
                   if RAW_RESET_PIN_OUT in ts["type_pins"].get(p["type"],{})}
            trw.update({sp: n for sp, n in _direct(ts.get('reset_inputs', [])).items() if sp in trw})
            decl += [f"    wire {w};" for w in sorted(trw.values()) if w.startswith("clock_landing_raw_reset_")]
            decl += [f"    assign {e['net']} = {trw[e['src_part']]};" for e in ts.get('reset_inputs',[])
                     if e["net"] != trw[e["src_part"]]]
        rpr = getattr(self, "ca_part_role", {}) if self.ca else {}
        rst = {r["origin"]: f"clock_landing_rstart_{ident(r['origin'])}" for r in rpr.values() if r["role"] == "relay"}
        decl += [f"    wire {w};" for w in sorted(set(rst.values()))]
        mon = {}
        if self.dataflow:
            # one wire pair per sender status pin (a source bus fanning out to several sinks shares its pin)
            mon = {(r["src"], r["src_bus"]): f"cland_mon_{ident(r['src'])}__{ident(r['src_bus'])}" for r in self.rows}
            for _pid, sp, sb, _dp, _db in self.intra_links:     # monitor="region": same-region status wires
                mon.setdefault((sp, sb), f"cland_mon_{ident(sp)}__{ident(sb)}")
            decl += [f"    wire {w}_ready, {w}_fault;" for w in sorted(set(mon.values()))]
        elif self.collector:
            for pn,p in self.collector["parts"].items():
                if p["active"] and p["parent"] is not None:
                    decl += [f"    wire cland_ready_{ident(pn)}, cland_fault_{ident(pn)};"]
            for e in self.collector["edges"]:
                if e["seam"]:decl.append(f"    wire cland_clock_{ident(e['src'])};")
        match = re.search(r"(?m)^module \w+ \([^;]*\);", text)
        text = text[:match.end()] + "\n" + "\n".join(decl) + text[match.end():]
        index = {(r["dst"], r["dst_bus"]): i for i, r in enumerate(self.rows)}
        for pn, p in self.parts.items():
            # Anchor on the instance, then the binder's own closing line; leaf
            # parameter parentheses can never terminate this module instance.
            pat = re.compile(r"(?m)^(    " + re.escape(modules[p["type"]]) +
                             r"(?: #\([^\n]*\))? " + re.escape(ident(pn)) + r" \(\n)(.*?)(\n    \);)", re.S)
            matches = list(pat.finditer(text))
            if len(matches) != 1:
                raise LandingError(f"clock landing: expected exactly one bound instance {pn}")
            m = matches[0]
            if ansi:
                body, count = re.subn(r"\.(clk(?:_[tc]\d+)?)\(clk\)", lambda mm: f".{mm.group(1)}(clk_region_{ident(self.region[pn])})", m.group(2))
                if not re.search(r"\.clk\(clk_region_", body):
                    raise LandingError(f"clock landing: default clock connection not found on {pn}")
            else:
                body, count = re.subn(r"\.clk\(clk_\w+\)", f".clk(clk_region_{ident(self.region[pn])})", m.group(2), count=1)
            if count < 1:
                raise LandingError(f"clock landing: default clock connection not found on {pn}")
            conn = [f"        .fclk_out_{b}({fwd[(pn,b)]})" for b in sorted(self.outs[pn])]
            # Functional binding uses the region source, as existing grid/core
            # tap connections do. The physical kit keeps the distinct planned
            # input pins and the export's source_clock_port contract.
            for tap in self.forwarded_clock_only_inputs.get(p["type"], []):
                if not re.search(r"\." + re.escape(tap) + r"\s*\(", body):
                    conn.append(f"        .{tap}(clk_region_{ident(self.region[pn])})")
            conn += [f"        .cland_fstart_out_{b}({fst[(pn,b)]})" for b in sorted(_ca_out(self, pn)) if self.ca]
            if ts:
                tpins = ts["type_pins"].get(p["type"], {})
                if RAW_RESET_PIN_OUT in tpins:
                    conn.append(f"        .{RAW_RESET_PIN_OUT}({trw[pn]})")
                if START_PIN_OUT in tpins:
                    conn.append(f"        .{START_PIN_OUT}({tsw.get(pn, '')})")
                if START_PIN_IN in tpins:
                    if pn in tsi:
                        conn.append(f"        .{START_PIN_IN}({tsi[pn]})")
                    elif rpr.get(pn, {}).get("role") == "root" and self.strap and tsw.get(pn):
                        # strap root copy of a root+child type: strap_ca_root selects the root counter, p_start unread.
                        # DIE-KV-13 trial: a literal here is not a declared strap_* pin (tie-off audit, OWNER 10-25 B), so
                        # the unread pin takes the copy's OWN start launch wire (its cland_tstart_out = cland_start)
                        conn.append(f"        .{START_PIN_IN}({tsw[pn]})")
                    elif rpr.get(pn, {}).get("role") == "root" and self.strap:
                        conn.append(f"        .{START_PIN_IN}(1'b0)")
                    else:
                        raise LandingError(f"clock landing {pn}: type {p['type']} has {START_PIN_IN} but no start "
                                           "port lands on this copy")
            if pn in rpr and rpr[pn]["relay_tx"]:
                conn.append(f"        .cland_rstart_out({rst[pn]})")
            if pn in rpr and rpr[pn]["role"] == "relay":
                conn.append(f"        .cland_rstart_in({rst[rpr[pn]['origin']]})")
            if self.strap and pn in self.strap["instances"]:
                # OWNER 12.15a / 1.8 rule 3: each strap bit a literal here; die_constant_cells.tcl maps every bit to its
                # own TIEHI/TIELO next to the pin; straps.audit_count_strap_values checks the pattern against the bind
                si = self.strap["instances"][pn]
                widths = self.strap["types"][si["type"]]["straps"]
                for sp in sorted(widths):
                    w = widths[sp]
                    conn.append(f"        .{sp}({w}'b{format(si['values'][sp], '0' + str(w) + 'b')})")
            if self.dataflow:
                for b in sorted(self.outs[pn]):
                    conn += [f"        .cland_up_ready_{b}({mon[(pn,b)]}_ready)", f"        .cland_up_fault_{b}({mon[(pn,b)]}_fault)"]
            for b, r in sorted(self.ins[pn].items()):
                i = index[(pn,b)]
                conn += [f"        .fclk_in_{b}({fwd[(r['src'],r['src_bus'])]})"]
                if self.ca and b in _ca_in(self, pn):
                    conn += [f"        .cland_fstart_in_{b}({fst[(r['src'],r['src_bus'])]})"]
                if self.dataflow:
                    w = mon[(r["src"], r["src_bus"])]
                    conn += [f"        .cland_dn_ready_{b}({w}_ready)", f"        .cland_dn_fault_{b}({w}_fault)"]
                elif not self.collector:
                    conn += [f"        .landing_ready_{b}(clock_landing_ready[{i}])",f"        .landing_fault_{b}(clock_landing_fault[{i}])"]
            if self.region_monitor:
                for b in sorted(self.intra_out[pn] - self.outs[pn]):
                    conn += [f"        .cland_up_ready_{b}({mon[(pn,b)]}_ready)", f"        .cland_up_fault_{b}({mon[(pn,b)]}_fault)"]
                for _pid, sp, sb, dp, db in sorted(self.intra_links):
                    if dp == pn:
                        w = mon[(sp, sb)]
                        conn += [f"        .cland_dn_ready_{db}({w}_ready)", f"        .cland_dn_fault_{db}({w}_fault)"]
            if self.collector and not self.dataflow and self.collector["parts"][pn]["active"]:
                cp=self.collector["parts"][pn]
                ready="clock_landing_ready" if cp["parent"] is None else "cland_ready_"+ident(pn)
                fault="clock_landing_fault" if cp["parent"] is None else "cland_fault_"+ident(pn)
                if cp["parent"] is not None or not local_observer:
                    conn += [f"        .cland_up_ready({ready})",f"        .cland_up_fault({fault})"]
                if self.collector["types"][p["type"]]["mask"]["up_seam"]:
                    conn.append(f"        .fclk_out_cland_up(cland_clock_{ident(pn)})")
                for e in self.collector["edges"]:
                    if e["dst"]!=pn:continue
                    i=e["dst_index"];child=ident(e["src"])
                    conn += [f"        .cland_dn_ready_{i}(cland_ready_{child})",f"        .cland_dn_fault_{i}(cland_fault_{child})"]
                    if e["seam"]:conn.append(f"        .fclk_in_cland_dn_{i}(cland_clock_{child})")
            body = ",\n".join(conn + [body])
            text = text[:m.start()] + m.group(1) + body + m.group(3) + text[m.end():]
        if ansi and re.search(r"\(clk\)", text):
            raise LandingError("clock landing: native top still drives a partition pin from the die clk")
        self.emitted_top = True
        return text

    def strap_declarations(self, binder_types=None):
        """MESO-STRAP-1: {type: {strap port: width}} of the strap form (binder_types: {binder type: plan type} for
        binder T__vN splits), for the parent strap manifest the tie-off audit reads."""
        if not self.strap:
            return {}
        out = {}
        for bt, pt in (binder_types or {t: t for t in self.strap["types"]}).items():
            if pt in self.strap["types"]:
                out[bt] = dict(self.strap["types"][pt]["straps"])
        return out

    def strap_expected(self):
        """MESO-STRAP-1: {instance: {strap port: (width, value)}} = count_align_bind.strap_ties tie values"""
        if not self.strap:
            return {}
        return {q: {sp: (self.strap["types"][v["type"]]["straps"][sp], v["values"][sp]) for sp in v["values"]}
                for q, v in self.strap["instances"].items()}

    def land_slots(self, tn):
        """kit land_slots.json of plan type tn for face_guard (DIE-HEAD-21; face_guard.kit_land / land_spec), or None.
        Only the count-aligned ring (ot_dp_clk_landing_ca / _cas -> ot_meso_ring_ca) is declared: its writer stores
        s_d[slot] <= t_d under the write-count enable (own-Q hold, no ICG), i.e. face_guard form "hold_mux", with D =
        the ring DEPTH type_rtl emits for that bus.  With the dataflow monitor the ring d = {cland_dn_fault_b,
        cland_dn_ready_b, b}, so both status pins land the same D slots.  The ring's forwarded START cland_fstart_in_b
        (t_rst_n of the ring writer + p_start of the count origin; no face flop: it would shift the count frame by one
        cycle) is declared {"form": "ring_start", "ring": b}: face_guard proves its fan-out ends only in ring b's writer
        flops and the origin's start sampler flops.  Schema land_slots/2 (/1 had no ring_start entries; face_guard
        ignores the schema string; older guards refuse unknown forms, fail-closed). The dedicated START input has
        explicit origin_start metadata naming its emitted origin instance, even when this type has no input ring. None:
        no count-aligned table or no landed input on tn (the default ot_dp_clk_landing ring and non-landed kits stay as
        they are)."""
        cat = self.ca_type.get(tn) if self.ca else None
        # CA-MIXED-1: only the count-aligned rings (a ring landing keeps the default ring, which is not declared)
        ins = _cam(self, tn)["inputs"]
        if not cat:
            return None
        buses = {}
        for b in sorted(ins):
            # DIE-HEAD-59 11-03 (DH59-FG): FREG-1 puts one rising-fclk face flop in front of the ring, so d, the status
            # pins and the start end in ordinary face registers (1 load each): no hold_mux / ring_start declaration.
            wr = ring_write_reg(self.plan, tn, b)
            if wr and wr["freg"]:
                continue
            d = {"D": int(cat["rings"][b]["depth"]), "form": "hold_mux"}
            for n in [b] + ([f"cland_dn_ready_{b}", f"cland_dn_fault_{b}"] if self.dataflow else []):
                buses[n] = dict(d)
            buses[f"cland_fstart_in_{b}"] = {"form": "ring_start", "ring": b}    # emitted with every ca landed input
        role = cat["role"]
        origin = None
        if role[0] == "child" and role[1] == START_PIN_IN:
            origin = "u_cland_origin"
        elif role[0] == "strap" and START_PIN_IN in role[1]:
            origin = (f"u_cland_origin_t{role[1].index(START_PIN_IN)}" if len(role[1]) > 1 else "u_cland_origin")
        if role[0] == "relay" and self.types[tn].get("landing_relay_start_copy", False):
            # The existing same-clock relay is the typed count-origin sampler.
            # Its input is die-timed; adding another input FF would shift K.
            buses["cland_rstart_in"] = {"form": "origin_start", "origin": "u_cland_rstart_rx"}
            # Declare the actual first sampler of the original input. Writer
            # transport changes the direct D loads; the final FSTART face flop
            # is no longer a same-D copy after an explicit writer branch.
            cfg = self.types[tn].get("clock", {}).get("landing_writer_start") or {}
            copies, stages = [], []
            for b in sorted(_cam(self, tn)["outputs"]):
                if b not in cfg.get("branches", {}):
                    copies.append(f"u_cland_fstart_{b}")
                elif not cfg.get("reuse_relay_origin", False):
                    # Samples the same input, but on its own local raw reset and feeding the next relay: not a copy.
                    stages.append(f"u_cland_writer_start_{ident(b)}_0")
            if self.tstart and self.tstart["type_pins"].get(tn, {}).get(START_PIN_OUT):
                copies.append("u_cland_tstart_o")
            if copies:
                # Every named private export is a physical same-D/reset/clock
                # copy of the typed origin, never an arbitrary extra sampler.
                buses["cland_rstart_in"]["copies"] = copies
            if stages:
                buses["cland_rstart_in"]["stages"] = stages
        if origin:
            buses[START_PIN_IN] = {"form": "origin_start", "origin": origin}
        return {"schema": LAND_SLOTS_SCHEMA, "buses": buses} if buses else None

    def manifest(self):
        by_lane = defaultdict(int)
        for r in self.rows:
            by_lane[r["lane"]] += int(r["added_cycles"])
        result = dict(schema="opentallas.clock_landing_rtl.v1",
                    implemented=self.emitted_top and self.emitted_types == set(self.types),
                    physical_qualified=False,
                    added_cycles_per_crossing=("per landing: count_aligned or ring (CA-MIXED-1)" if getattr(self, "mixed", False) else
                        "count_aligned (per crossing)" if self.ca else
                        "legacy per crossing: base3 + explicit input capture" if any(r.get("input_capture_cycles") for r in self.rows) else 3),
                    count_aligned=bool(self.ca),
                    count_straps=self.strap,
                    crossings=len(self.rows), ports=self.rows,
                    lane_added_cycles=dict(sorted(by_lane.items())),
                    types=self.by_type, reset_placements=self.reset_placements,
                    collector=self.collector,
                    observer_source=getattr(self,"observer_source",None),
                    forwarded_clock_only_inputs=self.forwarded_clock_only_inputs,
                    emitted_modules=getattr(self,"emitted_modules",None),
                    remaining_gates=["placed clock/status pins", "landing ring window STA",
                                     "trained region calendar offsets", "token pass"])
        if getattr(self, "mixed", False):
            result["count_aligned_mixed"] = dict(
                count_aligned=sum(1 for r in self.rows if r.get("landing_form") == "count_aligned"),
                ring=sum(1 for r in self.rows if r.get("landing_form") == "ring"),
                ca_types={tn: dict(v) for tn, v in sorted(self.ca_by_type.items()) if v["inputs"] or v["outputs"]})
        pending = getattr(self, "regional_source_pending", {})
        if pending:
            result["implemented"] = False
            result["regional_source_pending"] = pending
            result["remaining_gates"].append("regional source/global consumers listed in regional_source_pending")
        return result


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan")
    ap.add_argument("crossings")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    result = requirements(json.loads(Path(args.plan).read_text()), json.loads(Path(args.crossings).read_text()))
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: result[k] for k in ("crossings", "type_count_before", "type_count_after",
                                            "required_new_scalar_pins", "added_live_data_storage_flops")}))
