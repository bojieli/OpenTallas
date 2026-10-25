"""Fail-closed clock delivery for hard entries and opt-in local glue CTS roots.

An ETM already contains clock insertion in its launch/check arcs. Source latency
compensates that reference once; it must never be added back to the ETM arcs.
"""
import json
import math
import re
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hier_contract'))
import child_lint
import direct_macro_clock_entries
import async_gray_fifo_constraints
import cdc_sync_constraints
import gray_fifo_cdc_constraints
import single_clock_contract
import forwarded_clock_outputs

MODES = ("entries", "hybrid_entries", "multiple_cts_roots")

CORNERS = ('tt', 'ff', 'ss')
ENTRY_DOMAIN_API_VERSION = 1


def signoff_period(spec):
    """Opt-in leaf signoff period; all existing profiles retain their ABI."""
    actual = single_clock_contract.validate(spec)
    if actual is not None:
        return actual
    route = spec.get('route', {})
    value = route.get('signoff_period_ps', 833.333)
    # Exact 833ps is the common release policy (owner10-24); tightening to it needs no per-leaf clock waiver.
    if 'signoff_period_ps' in route and value != 833.0 and not native_leaf(spec):
        raise ValueError('signoff_period_ps requires native leaf timing ownership (multiple_cts_roots or hybrid_entries tile)')
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError('signoff_period_ps must be finite and positive')
    if 'signoff_period_ps' in route:
        physical = route.get('period_ps', 770)
        if isinstance(physical, bool) or not isinstance(physical, (int, float)) or not math.isfinite(physical) or physical <= 0 or physical > value:
            raise ValueError('route period must be finite, positive and no greater than signoff_period_ps')
    return float(value)


def related_data(spec):
    """Explicit opt-in to ordinary STA across related leaf roots."""
    policy = spec.get('clock_data_paths', 'independent')
    relationship = spec.get('clock_relationship')
    if policy == 'independent':
        if relationship is not None:
            raise ValueError('independent leaf datapaths do not consume a clock_relationship declaration')
        return False
    if policy == 'async_gray_fifo':
        async_gray_fifo_constraints.relationship(spec)
        return False
    if policy == cdc_sync_constraints.ASYNC_POLICY:
        # Asynchronous stream833.333 / HBM1024 roots whose only crossings are the linted cdc_synchronizers
        # structure (Gray source, >= 2-stage chain, gated payload capture); no ordinary STA across the roots.
        cdc_sync_constraints.async_relationship(spec)
        return False
    if policy == gray_fifo_cdc_constraints.POLICY:
        # Asynchronous clock families: no ordinary STA across them; only the reviewed FIFO crossings are bounded.
        gray_fifo_cdc_constraints.relationship(spec)
        return False
    if policy == 'related_pll_ratio':
        # One die PLL, stream /3 and serial /4 of the VCO, common epoch origin (3 serial = 4 stream cycles): the
        # serial domain declares ratio 4/3 of the core period.  Ordinary STA times every crossing at the actual
        # related edge windows (VCO-tick setup window, coincident-edge hold); no exception is generated.
        if relationship != dict(kind='same_pll_fixed_phase', ratio=[4, 3], phase_ps=0):
            raise ValueError('related_pll_ratio leaf datapaths require explicit same_pll_fixed_phase ratio4/3 phase0 relationship')
        return True
    if policy == 'related_pll_dividers':
        pll_divider_ratios(spec)
        return True
    if policy != 'related_same_frequency' or relationship != dict(kind='same_pll_fixed_phase', ratio=[1, 1], phase_ps=0):
        raise ValueError('related leaf datapaths require explicit same_pll_fixed_phase ratio1/1 phase0 relationship')
    return True


def pll_divider_ratios(spec):
    """Explicit phase-zero /3, /4 and /12 roots of the same 3.6 GHz PLL.

    The /12 epoch bank removes a direct 3:4 data crossing structurally.
    Every declared path still receives ordinary setup and hold analysis.
    A different divider, phase or frequency needs its own reviewed contract.
    """
    relationship = spec.get('clock_relationship') or {}
    if not isinstance(relationship, dict):
        raise ValueError('PLL clock relationship must be an explicit object')
    declared = spec.get('clock_entry_domains')
    dividers = relationship.get('vco_dividers')
    if (set(relationship) != {'kind', 'phase_ps', 'vco_dividers'}
            or relationship.get('kind') != 'same_pll_fixed_phase'
            or relationship.get('phase_ps') != 0
            or not isinstance(declared, dict) or not isinstance(dividers, dict)
            or set(dividers) != set(declared) or 'core' not in dividers
            or any(type(v) is not int or v not in (3, 4, 12) for v in dividers.values())):
        raise ValueError('related_pll_dividers requires exact phase0 /3,/4,/12 PLL divider ownership for every domain')
    expected_period = 833.333 * dividers['core'] / 3
    if abs(signoff_period(spec) - expected_period) > 0.001:
        raise ValueError('PLL divider signoff period must preserve the actual 3.6 GHz VCO frequency')
    ratios = {}
    for name, divider in dividers.items():
        ratio = Fraction(divider, dividers['core'])
        ratios[name] = [ratio.numerator, ratio.denominator]
        if not isinstance(declared[name], dict) or declared[name].get('ratio') != ratios[name]:
            raise ValueError(f'PLL divider ratio mismatch for {name}')
    return ratios


def native_leaf(spec):
    return spec.get("clock") == "multiple_cts_roots" or (spec.get("kind") == "tile" and spec.get("clock") == "hybrid_entries")


def landed_cluster(spec):
    """PL-KIT 10-18 (landed-regions standard): a kind-cluster multiple_cts_roots parent built by tools/landed_parent/lp.py.
    Every clock_ports entry is one region CTS root (TritonCTS per root, as the multi-root leaf); each hard child's clock
    pin is an ordinary sink of its region root (RTL: ck_<r> -> child clock pin), measured at its effective flops
    (entry-wire arrival + the child's views/<child>/insertion.json boundary min / mean / max).  Cross-root datapaths are
    the lp landings (cell multicycles from spec "landed_record") and the 1-bit regional reset runs, timed as related
    same-frequency roots.  Leaf tiles and every other mode are unchanged."""
    return spec.get("clock") == "multiple_cts_roots" and spec.get("kind") == "cluster"


def forwarded_clock_ports(spec):
    """S81-FRAME4 10-19 (forwarded-clock class of a LANDED cluster): spec "forwarded_clock_ports" names the parent input
    ports that carry a FORWARDED clock (a source-synchronous lane clock that travels with its data, e.g. the S81 frame
    port xk feeding the crs4 landing write side and the dvrly xo relays).  Such a port is not a region CTS root: a
    bound hard-child clock pin whose net traces structurally (ot_ce_net_root_port, through single-input standard cells)
    to it is a FORWARDED sink, counted toward the landed coverage and judged per forwarded port bit at the child flops
    (measured pin arrival + the child's insertion.json boundary min..max): spread <= 80 ps at TT and FF (post-CTS / routed,
    fail closed; pre-CTS reported).  Opt-in: without the key the generated SDC is byte-identical.  [] / absent = none."""
    ports = spec.get('forwarded_clock_ports')
    if ports is None:
        return []
    if not landed_cluster(spec):
        raise ValueError('forwarded_clock_ports: only a landed cluster (kind cluster + multiple_cts_roots) has a forwarded class')
    if (not isinstance(ports, list) or not all(isinstance(x, str) and re.fullmatch(r'[A-Za-z_]\w*', x) for x in ports)
            or len(set(ports)) != len(ports)):
        raise ValueError('forwarded_clock_ports: requires a list of distinct plain port names')
    ins = {p for d in (spec.get('clock_entry_domains') or {}).values() if isinstance(d, dict) for p in d.get('inputs') or []}
    if any(x not in ins for x in ports):
        raise ValueError('forwarded_clock_ports: each forwarded port must be an input of a clock_entry_domains domain '
                         '(its cells and data belong to that domain)')
    if set(ports) & set(spec.get('clock_ports') or []):
        raise ValueError('forwarded_clock_ports: a forwarded port cannot also be a region CTS root (clock_ports)')
    return list(ports)


def forwarded_soft_clocks(spec):
    """Exact mapped soft-register ownership on a forwarded input, without adding a CTS root.

    Each entry names one actual port bit and its exact mapped sequential cells.
    Clock ancestry and complete sink membership are checked in the loaded design.
    """
    entries = spec.get('forwarded_soft_clocks', [])
    if not isinstance(entries, list):
        raise ValueError('forwarded_soft_clocks: expected a list')
    allowed = forwarded_clock_ports(spec)
    seen_ports, seen_cells = set(), set()
    out = []
    for i, e in enumerate(entries):
        if not isinstance(e, dict) or set(e) != {'port', 'domain', 'cells'}:
            raise ValueError('forwarded_soft_clocks: requires exact port/domain/cells')
        port, domain, cells = e['port'], e['domain'], e['cells']
        if not isinstance(port, str) or not re.fullmatch(r'[A-Za-z_]\w*(?:\[[0-9]+\])?', port):
            raise ValueError('forwarded_soft_clocks: requires an exact port bit')
        base = port.split('[')[0]
        ds = domains(spec)
        owners = [n for n, d in ds.items() if base in d['inputs']]
        if base not in allowed or owners != [domain] or port in seen_ports:
            raise ValueError('forwarded_soft_clocks: missing, duplicate or wrong source domain')
        if (not isinstance(cells, list) or not cells or
                any(not isinstance(c, str) or not c or any(x in c for x in '{}\\;*?\n\r') for c in cells) or
                len(set(cells)) != len(cells) or set(cells) & seen_cells):
            raise ValueError('forwarded_soft_clocks: requires unique exact mapped cell names')
        seen_ports.add(port); seen_cells.update(cells)
        out.append(dict(e, clock=f'ot_forwarded_{i}'))
    return out


BAND_GENERATOR = "tools/s81_dv/frame_hier_kit.py"


def landed_band_record(spec, root, rec, path):
    """S81 frame MAIN-hier (b2, STW-S81c-DIE-FRAME 10-22): the record of ONE hard row band of an lp landed parent.
    A band is a single region (one root) of the parent; a landing whose ring and read both sit in it would be whole
    (impossible: a landing joins two regions, so "landings" is empty); every landing is a HALF ("landing_halves": side "w" =
    ring here, its bank / epo / vld leave on output ports; side "r" = read here, they arrive on input ports), timed by
    landed_sdc as the same -setup E / -hold D-1 multicycle against the port.  Validated against the parent lp record
    (fail closed): every half exists there, with this band's region on the right side."""
    if rec.get("kind") != "landed_band" or rec.get("top") != spec.get("top"):
        raise ValueError(f'{path}: not the landed_band record of {spec.get("top")}')
    regions = rec.get("regions")
    if not isinstance(regions, dict) or len(regions) != 1:
        raise ValueError(f"{path}: a band is exactly one region of its parent")
    (rname, reg), = regions.items()
    if [reg.get("clock_port")] != list(spec["clock_ports"]) or reg.get("clock_port") != spec["clock_port"]:
        raise ValueError(f"{path}: band clock port {reg.get('clock_port')} differs from clock_ports")
    parent = json.loads((Path(root) / rec["parent_record"]).read_text())
    if parent.get("generator") != "tools/landed_parent/lp.py":
        raise ValueError(f"{path}: parent_record is not an lp.py record")
    if (rec.get("D"), rec.get("E")) != (parent.get("D"), parent.get("E")):
        raise ValueError(f"{path}: D / E differ from the parent record")
    if rec.get("landing_implementation") != parent.get("landing_implementation"):
        raise ValueError(f"{path}: landing_implementation differs from the parent record")
    pl = {L["name"]: L for L in parent.get("landings") or []}
    if rec.get("landings"):
        # a landing crosses two regions and a band is one region: every landing of a band is a half
        raise ValueError(f"{path}: a band holds no whole landing (ring and read sit on different region roots)")
    seen = set()
    for h in rec.get("landing_halves") or []:
        P = pl.get(h.get("name"))
        side = h.get("side")
        if P is None or side not in ("w", "r") or h["name"] in seen:
            raise ValueError(f"{path}: invalid landing half {h}")
        if (side == "w" and P["src_region"] != rname) or (side == "r" and P["dst_region"] != rname):
            raise ValueError(f"{path}: half {h['name']}/{side} is on the wrong region (band region {rname})")
        ports = h.get("ports")
        if not isinstance(ports, list) or sorted(ports) != sorted(f"lpl_{h['name']}_{k}" for k in ("bank", "epo", "vld")):
            raise ValueError(f"{path}: half {h['name']} must carry exactly its bank / epo / vld ports")
        seen.add(h["name"])
    names = [L.get("name") for L in rec.get("landings") or []]
    if any(not isinstance(n, str) or not re.fullmatch(r"[A-Za-z0-9_]+", n) for n in names) or len(set(names)) != len(names):
        raise ValueError(f"{path}: invalid landing names")
    return rec


def half_landing_sdc(rec):
    """port-side multicycles of a band's landing halves (see landed_band_record); [] without halves"""
    hs = rec.get("landing_halves") or []
    if not hs:
        return []
    D, E = rec["D"], rec["E"]
    o = [f"# ---- landed band: {len(hs)} landing halves at the band face, multicycle -setup {E} -hold {D - 1} against the port",
         "set ot_lh_miss 0"]
    for h in hs:
        n = h["name"]
        cells = f"u_lpl_{n}_{h['side']}"
        ports = " ".join(f"lpl_{n}_{k}*" for k in ("bank", "epo", "vld"))
        o += [f"set ot_lh_c [get_cells -quiet {cells}.*]",
              f"if {{[llength $ot_lh_c] == 0}} {{ set ot_lh_c [get_cells -quiet {cells}/*] }}",
              f"set ot_lh_p [get_ports -quiet {{{ports}}}]",
              "if {[llength $ot_lh_c] == 0 || [llength $ot_lh_p] == 0} { incr ot_lh_miss } else {"]
        if h["side"] == "r":
            o += [f"  set_multicycle_path -setup {E} -from $ot_lh_p -to $ot_lh_c",
                  f"  set_multicycle_path -hold {D - 1} -from $ot_lh_p -to $ot_lh_c", "}"]
        else:
            o += [f"  set_multicycle_path -setup {E} -from $ot_lh_c -to $ot_lh_p",
                  f"  set_multicycle_path -hold {D - 1} -from $ot_lh_c -to $ot_lh_p", "}"]
    o.append(f'puts "OT_LP_HALF_SDC [expr {{{len(hs)} - $ot_lh_miss}}] of {len(hs)} landing halves constrained"')
    return o


def landed_record(spec, root):
    """The lp.py record (<top>_lp_record.json) of a landed cluster, validated against the spec (fail closed)."""
    if not landed_cluster(spec):
        return None
    path = spec.get("landed_record")
    if not isinstance(path, str) or not path:
        raise ValueError('landed cluster (kind cluster + multiple_cts_roots) requires "landed_record": the lp.py '
                         '<top>_lp_record.json of this parent')
    if not spec.get("children"):
        raise ValueError("landed cluster requires hard children (children[])")
    if spec.get("clock_data_paths") != "related_same_frequency":
        raise ValueError('landed cluster: landings and reset runs cross region roots; requires clock_data_paths '
                         '"related_same_frequency" (same_pll_fixed_phase ratio1/1 phase0)')
    # TW2-QCTLM 10-19: raw-memory sinks of a region root are allowed (raw_macro_clocks.contract: exact instance / master /
    # clock pin / region root); CDC synchronizers stay a leaf-tile feature (regions are related same-frequency roots)
    if spec.get("cdc_synchronizers") is not None:
        raise ValueError("landed cluster: CDC synchronizers are leaf-tile features")
    rec = json.loads((Path(root) / path).read_text())
    if (rec.get("generator") == BAND_GENERATOR) != (spec.get("landed_band") is True):
        raise ValueError(f'{path}: spec "landed_band": true iff the record is a {BAND_GENERATOR} landed_band record')
    if rec.get("generator") == BAND_GENERATOR:
        return landed_band_record(spec, root, rec, path)
    if rec.get("generator") != "tools/landed_parent/lp.py" or rec.get("top") != spec.get("top"):
        raise ValueError(f'{path}: not the lp.py record of {spec.get("top")}')
    regions = rec.get("regions")
    if not isinstance(regions, dict) or not regions:
        raise ValueError(f"{path}: no regions")
    ports = [r.get("clock_port") for r in regions.values()]
    if sorted(ports) != sorted(spec["clock_ports"]) or ports[0] != spec["clock_port"]:
        raise ValueError(f'{path}: region clock ports {ports} differ from clock_ports (first region = clock_port)')
    D, E = rec.get("D"), rec.get("E")
    if type(D) is not int or type(E) is not int or not 0 < E < D:
        raise ValueError(f"{path}: invalid landing depth D / read offset E")
    names = [L.get("name") for L in rec.get("landings") or []]
    if any(not isinstance(n, str) or not re.fullmatch(r"[A-Za-z0-9_]+", n) for n in names) or len(set(names)) != len(names):
        raise ValueError(f"{path}: invalid landing names")
    return rec


# Rule H1 (tools/hier_contract/pair_check.HOLD_TREE = 50 ps hold margin + 50 ps die skew): the hold margin part of the
# per-pair hold uncertainty a leaf signs off between two different clock entries; the rest is the die-skew tolerance.
H1_HOLD_MARGIN_PS = 50.0


def _tcl_words(text, var):
    """the words of a generated `set ::<var> {{a} {b}}` line (None when absent)"""
    m = re.search(r'^set ::' + var + r' \{(.*)\}\s*$', text, re.M)
    return [a or b for a, b in re.findall(r'\{([^{}\s]+)\}|([^{}\s]+)', m[1])] if m else None


def landed_raw_pins(view, root):
    """HF-4d 10-19 (coordinator option A, Q.STA.TTC.2): the RAW-MEMORY clock pins of a hard child in a LANDED cluster.
    A hybrid_entries leaf (h16c ot_qfd_tt_ctlm_static_hr) exposes, besides its CTS-root pin (ck_head), direct SRAM clock
    entries (ck_pm0/ck_pm1: port -> one SRAM clk).  Its ETM has only min/max_clock_tree_path on them and NO arcs, so
    all_registers never reaches them and the ETM says nothing about when they must arrive.  The requirement is in the
    leaf's CLOSED RECORD, not the ETM: the record's sign-off SDC compensates every entry to one phase phi (latency = phi -
    wire - R, the direct SRAM row with R = 0, phi = the CTS root's routed boundary mean), i.e. each SRAM clock pin is
    CO-TIMED with the boundary flops of the CTS-root pin; the per-pair hold uncertainty between two entries (rule H1:
    50 margin + 50 die skew) is the arrival tolerance the leaf signed off.
    Returns {raw pin: {"ref": cts-root pin, "tol": ps, "refs": {corner: [lo, mean, hi]}, "record": sign-off SDC,
    "verdict": verdict.json}} with refs = the leaf's measured port -> SRAM clk wire (insertion.json clock_measurements[pin][corner].all, n = 1), so the parent
    judges  wire(raw) + refs.mean  ==  wire(ref) + R(ref).boundary.mean  within tol at TT and FF.  {} when the child has
    no raw entry.  Fail closed on any record mismatch.
    ROOT-INF21 10-19 (coordinator, INF.21.1): also MULTI-ROOT sign-off records (landed_record_pins)."""
    return landed_record_pins(view, root)['raw']


def _lib_pin_blocks(text):
    """{pin name: its Liberty pin(...) group text} of an ETM (quoted or bare names, bus bits included)"""
    out = {}
    for m in re.finditer(r'\bpin\s*\(\s*"?([^")\s]+)"?\s*\)\s*\{', text):
        depth, i = 1, m.end()
        while depth and i < len(text):
            depth += {'{': 1, '}': -1}.get(text[i], 0)
            i += 1
        out[m[1]] = text[m.end():i - 1]
    return out


def landed_unused_pins(view, root):
    """HBM-PGLG2 10-19: the UNLOADED input pins of a hard child, proven by its CLOSED route's ROUTED NETLIST.
    KIND0 kind0_l4_leaf1 keeps clock ports clk_insert_0..3 / clk_stage_4 that drive nothing inside the closed leaf; the
    landed pgslice parent ties them to the region root with the leaf's real clock pins, and clock_entries.tcl refused
    the root ("must reach only standard-cell clock pins").  Evidence: <record route>/unloaded_pins.json written by
    tools/ref_tile/unloaded_pins.py from the closed route's 6_final.v (no instance connection, no assign reads the
    port bit).  Never classified by name.  Every listed pin is cross-checked against the leaf's routed ETMs at every
    corner (pin group present, capacitance 0, no timing group, not a clock, never a related_pin) and must not be a
    bound clock pin of the record; any mismatch fails closed.  [] for a child without a closed-record link
    (port_latency.json) or without the evidence file (every existing kit: byte-identical)."""
    view = Path(view)
    try:
        pl = json.loads((view / 'port_latency.json').read_text())
    except (OSError, ValueError):
        return []
    job = pl.get('job') if isinstance(pl, dict) else None
    if not job:
        return []
    vpath = Path(root) / 'results' / 'closure_loop' / job / 'verdict.json'
    try:
        verdict = json.loads(vpath.read_text())
    except (OSError, ValueError):
        return []
    routes = [r.get('to') for r in (verdict.get('job_spec') or {}).get('record') or []
              if isinstance(r, dict) and str(r.get('from', '')).endswith('/record/route')]
    if len(routes) != 1 or not routes[0]:
        return []
    epath = Path(root) / routes[0] / 'unloaded_pins.json'
    if not epath.is_file():
        return []
    where = f'{view}: unloaded-pin evidence {epath}'
    if verdict.get('status') != 'CLOSED' or verdict.get('job') != job:
        raise ValueError(f'{where}: {vpath} is not the CLOSED record of {job}')
    try:
        ev = json.loads(epath.read_text())
        pins = ev['unloaded']
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise ValueError(f'{where}: unreadable ({e})')
    if (ev.get('schema') != 1 or ev.get('job') != job or ev.get('top') != view.name or not ev.get('netlist_sha256')
            or not isinstance(pins, list) or not all(isinstance(x, str) and x for x in pins) or len(set(pins)) != len(pins)):
        raise ValueError(f'{where}: not the routed-netlist evidence of {view.name} / {job}')
    bound = set((pl.get('control_roles') or {}).get('clocks') or [])
    try:
        bound |= set(json.loads((view / 'insertion.json').read_text()).get('clock_measurements') or {})
    except (OSError, ValueError):
        pass
    for c in CORNERS:
        lib = view / f'{view.name}_{c}.lib'
        try:
            text = lib.read_text()
        except OSError as e:
            raise ValueError(f'{where}: {lib} missing ({e})')
        blocks = _lib_pin_blocks(text)
        related = set(re.findall(r'related_pin\s*:\s*"?([^";\s]+)"?\s*;', text))
        for pin in pins:
            b = blocks.get(pin)
            cap = re.search(r'capacitance\s*:\s*([-\d.eE+]+)\s*;', b or '')
            if (b is None or not re.search(r'direction\s*:\s*input\s*;', b) or not cap or float(cap[1]) != 0.0
                    or 'timing' in b or re.search(r'clock\s*:\s*true', b) or pin in related or pin in bound):
                raise ValueError(f'{where}: {pin} is not an unloaded input of the routed ETM {lib.name} '
                                 '(needs capacitance 0, no timing group, not a clock / related pin / bound clock)')
    return sorted(pins)


def landed_record_pins(view, root):
    """ROOT-INF21 10-19 (coordinator INF.21.1, pgslice_lg children): the closed-record clock reference of a hard child
    with raw clock pins (no routed boundary flops), for BOTH record models:
      'hybrid'     one CTS root + direct raw SRAM entries (HF-4d, h16c): unchanged.
      'multi_root' a multiple_cts_roots leaf sign-off (KIND0 kind0_l4_leaf1: 7 CTS roots; bank6_clock7: 3 CTS roots +
                   6 direct SRAM entries).  The record measures EVERY CTS root per root (OT_HYBRID CTS_MEASURE: its
                   boundary flops, or all its internal sinks when it has none: reference_scope=all_internal_only) and
                   compensates every entry to ONE phase phi (latency = phi - wire - R).  So every clock pin p of the
                   child is co-timed: wire(p) + R(p) equal for all p within the record's die-skew tolerance, R(p) =
                   routed boundary mean | routed all-internal mean (CTS root without boundary flops) | leaf pin -> SRAM
                   wire (direct entry).  R is the child's ROUTED-view STA (views/<child>/insertion.json
                   clock_measurements: 6_final.odb + SPEF, every root, TT/FF/SS), never invented.
    Returns {"model", "raw": {pin: as landed_raw_pins}, "cotimed": {boundary pin != ref: {ref, tol, record, verdict}},
    "anchor": pin with the largest R (None for 'hybrid'), "R": {pin: {corner: mean}}}.  "raw" pins are judged against
    "ref" = the boundary CTS root with the largest TT boundary mean; "cotimed" boundary pins likewise (post-CTS SDC and
    pre-route gate); the post-CTS tap delays every pin except "anchor" by R(anchor) - R(p) (landed_tap_targets).
    Children whose pins all have routed boundary flops read no record (empty result, kits byte-identical).
    HBM-PGLG2 10-19: "unused" = the child's routed-netlist-proven UNLOADED input pins (landed_unused_pins),
    in every result; a region root may reach them (clock_entries.tcl ::ot_ce_landed_unused), nothing is measured."""
    view = Path(view)
    unused = landed_unused_pins(view, root)
    empty = dict(model=None, raw={}, cotimed={}, anchor=None, R={}, unused=unused)
    ins = json.loads((view / 'insertion.json').read_text())
    cm = ins.get('clock_measurements') or {}
    raw_like = sorted(p for p, r in cm.items() if any(not (r.get(c) or {}).get('boundary') for c in CORNERS))
    if not raw_like:
        return empty
    where = f'{view}: raw child clock pins {raw_like}'
    try:
        pl = json.loads((view / 'port_latency.json').read_text())
        job = pl['job']
        clocks = list(pl['control_roles']['clocks'])
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise ValueError(f'{where}: no closed-record port_latency.json job / clock roles ({e})')
    vpath = Path(root) / 'results' / 'closure_loop' / job / 'verdict.json'
    try:
        verdict = json.loads(vpath.read_text())
    except (OSError, ValueError) as e:
        raise ValueError(f'{where}: leaf closed record {vpath} unreadable ({e})')
    if verdict.get('status') != 'CLOSED' or verdict.get('job') != job:
        raise ValueError(f'{where}: {vpath} is not the CLOSED record of {job}')
    routes = [r.get('to') for r in (verdict.get('job_spec') or {}).get('record') or []
              if isinstance(r, dict) and str(r.get('from', '')).endswith('/record/route')]
    if len(routes) != 1 or not routes[0]:
        raise ValueError(f'{where}: {vpath} names no unique record route directory')
    sdc_path = Path(root) / routes[0] / 'signoff.sdc'
    try:
        sdc = sdc_path.read_text()
    except OSError as e:
        raise ValueError(f'{where}: leaf sign-off SDC {sdc_path} missing ({e})')
    ports, roots = _tcl_words(sdc, 'ot_ce_ports'), _tcl_words(sdc, 'ot_ce_cts_roots')
    direct = re.search(r'^set ::ot_ce_direct_entries (.*)$', sdc, re.M)
    raw = {m[3]: m[4] for m in re.finditer(r'\{\{([^{}\s]+)\} \{([^{}\s]+)\} \{([^{}\s]+)\} \{([^{}\s]+)\} ',
                                            direct[1])} if direct else {}
    hold = re.findall(r'^\s*set_clock_uncertainty -hold ([\d.]+) -from \$a -to \$b\s*$', sdc, re.M)
    comp = 'set latency [expr {$ref - $wire - $mean}]' in sdc
    direct_row = 'lappend rows [list [lindex $sources 0] $pin $wire 0 0 0 $clock 0 $domain]' in sdc
    multi = bool(roots) and len(roots) > 1
    if not multi:
        if not ports or not roots or len(roots) != 1 or not raw or len(hold) != 1 or not (comp and direct_row):
            raise ValueError(f'{where}: {sdc_path} is not a hybrid-entries sign-off with one CTS root, direct raw SRAM '
                             'entries (R 0), entry compensation and one per-pair hold uncertainty')
    else:
        root_row = 'lappend rows [list [get_ports $name] [lindex $pins 0] 0 $lo $mean $hi $clock $mean $domain]' in sdc
        internal = 'set scope all_internal_only' in sdc and 'if {![llength $boundary]} { set boundary $pins;' in sdc
        if (not ports or len(hold) != 1 or not comp or not root_row or (raw and not direct_row)
                or len(set(roots)) != len(roots) or set(roots) & set(raw)):
            raise ValueError(f'{where}: {sdc_path} is not a multi-root sign-off (one measured row per CTS root, entry '
                             'compensation to one phase, direct entries R 0, one per-pair hold uncertainty)')
    if sorted(ports) != sorted(clocks) or sorted(ports) != sorted(cm) or sorted(ports) != sorted([*roots, *raw]):
        raise ValueError(f'{where}: bound clock pins differ: record SDC {ports}, port_latency {clocks}, insertion '
                         f'{sorted(cm)}, CTS roots {roots} + raw {sorted(raw)}')
    bounded = [p for p in roots if p not in raw_like]
    internal_roots = sorted(p for p in roots if p in raw_like)
    if sorted([*raw, *internal_roots]) != raw_like or not bounded:
        raise ValueError(f'{where}: pins without a routed boundary differ from the record raw entries {sorted(raw)}'
                         + (f' + internal-only CTS roots {internal_roots}' if multi else '')
                         + ('' if bounded else '; no CTS root with routed boundary flops to co-time them with'))
    if internal_roots and not internal:
        raise ValueError(f'{where}: {sdc_path} has CTS roots without boundary flops {internal_roots} but no '
                         'all-internal-sink reference scope')
    tol = float(hold[0]) - H1_HOLD_MARGIN_PS
    if not tol > 0:
        raise ValueError(f'{where}: record hold uncertainty {hold[0]} leaves no die-skew tolerance')

    def bmean(p, c):
        b = (cm[p].get(c) or {}).get('boundary') or {}
        if not b.get('n') or (cm[p].get(c) or {}).get('errors'):
            raise ValueError(f'{where}: {p}/{c}: no routed boundary reference')
        v = float(b['mean'])
        if not math.isfinite(v) or v < 0:
            raise ValueError(f'{where}: {p}/{c}: invalid routed boundary reference')
        return v
    ref = max(bounded, key=lambda p: (bmean(p, 'tt'), -bounded.index(p))) if multi else roots[0]
    record = f'{routes[0]}/signoff.sdc'
    vrel = f'results/closure_loop/{job}/verdict.json'
    out, R = {}, {}
    for pin in sorted([*raw, *internal_roots]):
        refs = {}
        for c in CORNERS:
            rc, bc = cm[pin].get(c) or {}, (cm[ref].get(c) or {}).get('boundary') or {}
            a = rc.get('all') or {}
            mac = rc.get('macros') or {}
            if pin in raw:
                bad = rc.get('errors') or a.get('n') != 1 or mac.get('n') != 1 or not bc.get('n')
                what = 'not one measured SRAM clock wire'
            else:
                bad = rc.get('errors') or not isinstance(a.get('n'), int) or a['n'] < 1 or mac or not bc.get('n')
                what = 'not a measured routed all-internal-sink reference of a CTS root'
            if bad:
                raise ValueError(f'{where}: {pin}/{c}: {what}, or {ref} has no boundary')
            v = [float(a[k]) for k in ('min', 'mean', 'max')]
            if not all(math.isfinite(x) and x >= 0 for x in v) or not v[0] <= v[1] <= v[2]:
                raise ValueError(f'{where}: {pin}/{c}: invalid leaf wire reference')
            refs[c] = v
        out[pin] = dict(ref=ref, tol=tol, refs=refs, record=record, verdict=vrel)
        R[pin] = {c: refs[c][1] for c in CORNERS}
    if not multi:
        return dict(model='hybrid', raw=out, cotimed={}, anchor=None, R=R, unused=unused)
    for p in bounded:
        R[p] = {c: bmean(p, c) for c in CORNERS}
    meas = pl.get('clock_reference')
    if meas is not None:
        # a generated (no pin registers) port_latency.json carries the routed-view references it was made from: they
        # must be the view's own measurements (fail closed on any drift between the record files)
        for p in ports:
            for c in CORNERS:
                got = ((meas.get(p) or {}).get(c) or {}).get('mean')
                if got is None or abs(float(got) - R[p][c]) > 1e-6:
                    raise ValueError(f'{where}: port_latency.json clock_reference {p}/{c} {got} differs from the routed '
                                     f'view reference {R[p][c]}')
    cotimed = {p: dict(ref=ref, tol=tol, record=record, verdict=vrel) for p in bounded if p != ref}
    anchor = max(ports, key=lambda p: (R[p]['tt'], -ports.index(p)))
    return dict(model='multi_root', raw=out, cotimed=cotimed, anchor=anchor, R=R, unused=unused)


def landed_raw_targets(spec, root):
    """HF-4d 10-19: {"<master>/<raw pin>": {"ref": pin, "tt"|"ff"|"ss": ps, "record": path}} for the post-CTS raw-pin
    delay tap (physical/common_flow/landed_raw_tap.tcl): the pin-arrival offset raw - ref the leaf's closed record signed
    off, R(ref).boundary.mean - w_leaf(raw).mean per corner; {} for every kit without raw child clock pins."""
    out = {}
    if not landed_cluster(spec):
        return out
    for child in spec.get('children', []):
        view = Path(root) / child['view']
        raw = landed_raw_pins(view, root)
        if not raw:
            continue
        cm = json.loads((view / 'insertion.json').read_text())['clock_measurements']
        for pin, info in raw.items():
            row = dict(ref=info['ref'], record=info['record'], verdict=info['verdict'])
            for c in CORNERS:
                row[c] = round(float(cm[info['ref']][c]['boundary']['mean']) - info['refs'][c][1], 3)
            out[f'{view.name}/{pin}'] = row
    return out


def landed_tap_targets(spec, root):
    """ROOT-INF21 10-19: the post-CTS tap targets (landed_raw_tap.tcl ::ot_lrt_targets).  'hybrid' children: the raw-pin
    targets (landed_raw_targets, unchanged).  'multi_root' children: the record co-times EVERY clock pin to one phase,
    and TritonCTS gives every clock pin of a hard child the same pin arrival (macro tree), so every pin p except the
    anchor (largest R) is delayed by R(anchor) - R(p) (>= 0 at TT) measured against the anchor pin: raw pins, internal-
    only roots AND boundary roots (bank6_clock7: clk 60.8 / clk_rd 84.9 boundary vs clk_ws 151.1 internal at TT -- the
    raw pin needs to arrive EARLIER than a boundary ref, which a delay-only tap on the raw pin cannot give)."""
    out = {}
    if not landed_cluster(spec):
        return out
    for child in spec.get('children', []):
        view = Path(root) / child['view']
        rec = landed_record_pins(view, root)
        if rec['model'] == 'hybrid':
            cm = json.loads((view / 'insertion.json').read_text())['clock_measurements']
            for pin, info in rec['raw'].items():
                row = dict(ref=info['ref'], record=info['record'], verdict=info['verdict'])
                for c in CORNERS:
                    row[c] = round(float(cm[info['ref']][c]['boundary']['mean']) - info['refs'][c][1], 3)
                out[f'{view.name}/{pin}'] = row
        elif rec['model'] == 'multi_root':
            a = rec['anchor']
            info = next(iter(rec['raw'].values()))
            for pin in sorted(rec['R']):
                if pin == a:
                    continue
                row = dict(ref=a, record=info['record'], verdict=info['verdict'])
                for c in CORNERS:
                    row[c] = round(rec['R'][a][c] - rec['R'][pin][c], 3)
                out[f'{view.name}/{pin}'] = row
    return out


def landed_cotimed_pins(spec, root):
    """ROOT-INF21 10-19: {"<master>/<boundary pin>": {ref, tol, record}} of multi-root children (co-timed with ref)"""
    out = {}
    if not landed_cluster(spec):
        return out
    for child in spec.get('children', []):
        view = Path(root) / child['view']
        for pin, info in landed_record_pins(view, root)['cotimed'].items():
            out[f'{view.name}/{pin}'] = info
    return out


_TIMING_HDR = re.compile(r'timing\s*\(\s*\)\s*\{([^{}]*)')
_CHECK_TYPE = re.compile(r'timing_type\s*:\s*"?(setup|hold|recovery|removal)_(rising|falling)"?\s*;')
_RELATED = re.compile(r'related_pin\s*:\s*"?([^";\s]+)"?\s*;')


def liberty_check_pins(text):
    """clock pins named as related_pin of a timing CHECK (setup/hold/recovery/removal) in a Liberty text (the ETM of a
    hard child): the capture clocks whose sinks STA times through check arcs (ROOT-LANDEDHC 10-19)"""
    out = set()
    for m in _TIMING_HDR.finditer(text):
        hdr = m[1]
        if _CHECK_TYPE.search(hdr):
            r = _RELATED.search(hdr)
            if r:
                out.add(r[1])
    return out


def landed_pre_cts_tcl(spec, root):
    """pre_cts.tcl lines a LANDED cluster needs BEFORE clock_entries.tcl wraps CTS (ONE landed-parent hard-child clock
    mechanism for every landed parent: S81 SerDes column, HBM pslice, Qwen tt_ctlm).  clock_entries.tcl admits a hard
    child's clock pin as a region-root sink only for masters in ::ot_ce_counts and, for a raw SRAM clock pin, keys in
    ::ot_ce_landed_raw; both were set only by clock_entry.sdc (post-CTS), and write_sdc drops Tcl variables, so every
    real landed kit failed "CTS source must reach only standard-cell clock pins" (TW-HBM-PSLICE pslice_c5_lp real3,
    b895c55d9; the unit flows set the dict by hand).  [] for every other kit (byte-identical)."""
    if not landed_cluster(spec):
        return []
    counts = {}
    for ch in spec.get('children', []):
        m = Path(ch['view']).name
        counts[m] = counts.get(m, 0) + int(ch.get('count', 1))
    out = ['set ::ot_ce_counts [dict create ' + ' '.join(f'{{{m}}} {n}' for m, n in counts.items()) + ']']
    raw = landed_raw_targets(spec, root)
    if raw:
        out.append('set ::ot_ce_landed_raw [dict create ' + ' '.join(
            f'{{{k}}} {{ref {v["ref"]}}}' for k, v in sorted(raw.items())) + ']')
    # HBM-PGLG2 10-19: routed-netlist-proven unloaded child input pins a region root may reach (no sink, no arc)
    unused, seen = [], set()
    for ch in spec.get('children', []):
        view = Path(root) / ch['view']
        if view.name in seen:
            continue
        seen.add(view.name)
        unused.extend(f'{view.name}/{p}' for p in landed_record_pins(view, root)['unused'])
    if unused:
        out.append('set ::ot_ce_landed_unused [dict create ' + ' '.join(f'{{{k}}} 1' for k in sorted(unused)) + ']')
    return out


def landed_raw_tcl(spec, root):
    """pre_cts.tcl lines that arm landed_raw_tap.tcl ([] without raw child clock pins: kits byte-identical)"""
    targets = landed_tap_targets(spec, root)
    if not targets:
        return []
    rows = ' '.join(f'{{{k}}} {{ref {v["ref"]} tt {v["tt"]:g} ff {v["ff"]:g} ss {v["ss"]:g}}}' for k, v in sorted(targets.items()))
    return [f'set ::ot_lrt_targets [dict create {rows}]', 'source /src/physical/common_flow/landed_raw_tap.tcl']


def child_centre_tap(spec, root):
    """HBM-ELEM13/SU-PSLICE14 10-21 (opt-in spec "child_centre_tap": {"children": [inst, ..], "why": ..}): the LANDED
    multiple_cts_roots cluster's hard children whose clock pin gets the post-CTS centring tap
    (physical/common_flow/child_centre_tap.tcl).  Returns {inst: {tt: [min, max], ff: .., ss: ..}} from each child's
    views/<child>/insertion.json boundary; {} without the key (kits byte-identical).  Fails closed on a non-landed spec,
    an unknown / duplicate instance or a view without a boundary range."""
    cfg = spec.get("child_centre_tap")
    if cfg is None:
        return {}
    if not landed_cluster(spec):
        raise ValueError("child_centre_tap requires a landed multiple_cts_roots cluster")
    if not isinstance(cfg, dict) or not isinstance(cfg.get("why"), str) or not cfg["why"].strip():
        raise ValueError('child_centre_tap: {"children": [inst, ..], "why": "..."}')
    kids = cfg.get("children")
    if not isinstance(kids, list) or not kids or len(set(kids)) != len(kids) or not all(isinstance(k, str) for k in kids):
        raise ValueError("child_centre_tap.children: a nonempty list of distinct hard-child instances")
    views = {ch.get("inst"): ch.get("view") for ch in spec.get("children") or [] if isinstance(ch, dict)}
    out = {}
    for k in kids:
        if not views.get(k):
            raise ValueError(f"child_centre_tap: {k} is not a hard child (children[].inst) of this cluster")
        ins = json.loads((Path(root) / views[k] / "insertion.json").read_text())
        row = {}
        for c in ("tt", "ff", "ss"):
            b = (ins.get(c) or {}).get("boundary") or {}
            if b.get("min") is None or b.get("max") is None:
                raise ValueError(f"child_centre_tap: {views[k]}/insertion.json has no {c} boundary min/max")
            row[c] = [float(b["min"]), float(b["max"])]
        out[k] = row
    return out


def child_centre_tcl(spec, root):
    """pre_cts.tcl lines that arm child_centre_tap.tcl ([] without the spec key: kits byte-identical)"""
    rows = child_centre_tap(spec, root)
    if not rows:
        return []
    body = " ".join(f"{{{k}}} {{" + " ".join(f"{c} {{{v[c][0]:g} {v[c][1]:g}}}" for c in ("tt", "ff", "ss")) + "}"
                    for k, v in sorted(rows.items()))
    return [f"set ::ot_cct_children [dict create {body}]", "source /src/physical/common_flow/child_centre_tap.tcl"]


def landed_sdc(spec, root):
    """Landing multicycles (LANDING-CONTRACT L5, lp.py Pm.sdc): ring u_lpl_<n>_w -> read u_lpl_<n>_r -setup E -hold D-1.
    Cell-based, so they are independent of the root clock names; '' for every non-landed spec (kits byte-identical).
    HBM-PGSTREAM-B 10-19: plus seam_window_sdc (opt-in "seam_windows" of a related_pll_ratio leaf; '' without it)."""
    rec = landed_record(spec, root)
    seam = seam_window_sdc(spec)
    if rec is None:
        return seam
    impl = rec.get("landing_implementation") or {}
    if impl.get("direct_quarter_period_timing"):
        if (rec["D"], rec["E"]) != (4, 2) or not 1 <= int(impl.get("chunk_bits", 0)) <= 24:
            raise ValueError("direct landing requires proven D4/E2 and chunk_bits1..24")
        residual = int(spec.get("landing_direct_residual_ps", -1))
        if residual < 150:
            raise ValueError("direct landing must explicitly preserve high-entry210/hold100 reserves: residual>=150ps")
        # This block follows ot_ce_apply. Charge the full existing high-entry
        # reserve plus the conservative default phase envelope; no MCP survives.
        return ("# PL-KIT direct D4/E2; diagnostic/adoption requires source-pinned native phase receipt.\n"
                "set ot_lp_direct_T [get_property [get_clocks core_clk] period]\n"
                "set ot_lp_direct_roots [lmap c [get_clocks ot_entry_*] {get_full_name $c}]\n"
                "set ot_lp_direct_clocks {}\n"
                "foreach c [all_clocks] {\n"
                " if {[ot_cf_root [get_full_name $c]] in $ot_lp_direct_roots} {lappend ot_lp_direct_clocks $c}\n"
                "}\n"
                "foreach a $ot_lp_direct_clocks {\n"
                " foreach b $ot_lp_direct_clocks {\n"
                "  if {[ot_cf_root [get_full_name $a]] eq [ot_cf_root [get_full_name $b]]} continue\n"
                f"  set_clock_uncertainty -setup [expr {{{60 + residual}.0 + 0.75 * $ot_lp_direct_T}}] -from $a -to $b\n"
                f"  set_clock_uncertainty -hold {25 + residual}.0 -from $a -to $b\n"
                " }\n}\n" + seam)
    D, E = rec["D"], rec["E"]
    names = [L["name"] for L in rec.get("landings") or []]
    if rec.get("kind") == "landed_band" and not impl.get("no_data_multicycle"):
        seam = "\n".join(half_landing_sdc(rec)) + ("\n" if rec.get("landing_halves") else "") + seam
    if impl.get("no_data_multicycle"):
        # QW-CTLM3 10-19 (lp.py landing_mcp false): no exception at all -- every ring -> read cone (slot data, valid,
        # selectors, reset-adjacent) is timed single-cycle at full STA, which is conservative for a read K >= 1 edges
        # after the slot write.  Tightening only: nothing is relaxed relative to the default related-root analysis.
        return (f"# ---- PL-KIT landed cluster ({spec['landed_record']}): {len(names)} landings, NO data multicycle "
                f"(single-cycle full STA, D {D} / K {E})\n"
                f'puts "OT_LP_LAND_SDC 0 of {len(names)} landings multicycled (no_data_multicycle)"\n' + seam)
    # TW2-PSLICE2 10-19 (lp.py share_rings): a landing may read ANOTHER landing's ring ("ring": "u_lpl_<g>_w (ck_<r>)")
    ring = {L["name"]: (str(L.get("ring") or "").split() or [""])[0] for L in rec.get("landings") or []}
    ring = {n: (g[6:-2] if g.startswith("u_lpl_") and g.endswith("_w") else n) for n, g in ring.items()}
    shared = any(g != n for n, g in ring.items())
    o = [f"# ---- PL-KIT landed cluster ({spec['landed_record']}): {len(names)} landings, multicycle -setup {E} -hold {D - 1}"]
    if names and shared:
        o += ["set ot_lp_pairs {" + " ".join(f"{ring[n]} {n}" for n in names) + "}",
              "set ot_lp_lands {}; foreach {ot_lw ot_ln} $ot_lp_pairs { lappend ot_lp_lands $ot_ln; set ot_lp_ring($ot_ln) $ot_lw }",
              "set ot_lp_miss 0", "foreach ot_ln $ot_lp_lands {",
              "  set ot_lw $ot_lp_ring($ot_ln)",
              "  set ot_lf [get_cells -quiet u_lpl_${ot_lw}_w.*]",
              "  set ot_lt [get_cells -quiet u_lpl_${ot_ln}_r.*]",
              "  if {[llength $ot_lf] == 0} { set ot_lf [get_cells -quiet u_lpl_${ot_lw}_w/*] }",
              "  if {[llength $ot_lt] == 0} { set ot_lt [get_cells -quiet u_lpl_${ot_ln}_r/*] }",
              "  if {[llength $ot_lf] == 0 || [llength $ot_lt] == 0} { incr ot_lp_miss; continue }",
              f"  set_multicycle_path -setup {E} -from $ot_lf -to $ot_lt",
              f"  set_multicycle_path -hold {D - 1} -from $ot_lf -to $ot_lt", "}",
              'puts "OT_LP_LAND_SDC [expr {[llength $ot_lp_lands] - $ot_lp_miss}] of [llength $ot_lp_lands] landings constrained"']
    elif names:
        o += ["set ot_lp_lands {" + " ".join(names) + "}", "set ot_lp_miss 0", "foreach ot_ln $ot_lp_lands {",
              "  set ot_lf [get_cells -quiet u_lpl_${ot_ln}_w.*]",
              "  set ot_lt [get_cells -quiet u_lpl_${ot_ln}_r.*]",
              "  if {[llength $ot_lf] == 0} { set ot_lf [get_cells -quiet u_lpl_${ot_ln}_w/*] }",
              "  if {[llength $ot_lt] == 0} { set ot_lt [get_cells -quiet u_lpl_${ot_ln}_r/*] }",
              "  if {[llength $ot_lf] == 0 || [llength $ot_lt] == 0} { incr ot_lp_miss; continue }",
              f"  set_multicycle_path -setup {E} -from $ot_lf -to $ot_lt",
              f"  set_multicycle_path -hold {D - 1} -from $ot_lf -to $ot_lt", "}",
              'puts "OT_LP_LAND_SDC [expr {[llength $ot_lp_lands] - $ot_lp_miss}] of [llength $ot_lp_lands] landings constrained"']
    return "\n".join(o) + "\n" + seam


SEAM_WINDOW_KEYS = {'name', 'launch', 'capture', 'from', 'setup_q', 'hold_q', 'why'}


def seam_windows(spec):
    """HBM-PGSTREAM-B 10-19 (coordinator 07:11, CLOCKING STANDARD 10-18 landed crossings): validated "seam_windows" of a
    related_pll_ratio multiple_cts_roots LEAF tile.  A banked 3:4 seam INSIDE one tile (bank written on one root, read
    on the other at a fixed calendar edge, no handshake) is a landed crossing, not an ordinary related-clock path: STA's
    default related window is the nearest edge pair (1 VCO tick q = core period / 3) less the distinct-entry reserve,
    while the static calendar guarantees setup >= setup_q * q and rewrite-after-read >= hold_q * q (measured by the
    bench window checker).  Each entry:
      name     identifier;  launch / capture  two different clock_ports (the bank root, the reader root);
      from     cell glob patterns of the BANK registers (launch root), e.g. "*u_bq.rq_b0*";
      setup_q  >= 2 (VCO ticks from the bank write edge to its read edge);  hold_q >= 2 (read edge to rewrite edge);
      why      the calendar the windows come from.
    None for every spec without the key (all existing kits)."""
    sw = spec.get('seam_windows')
    if sw is None:
        return None
    if not (native_leaf(spec) and spec.get('kind') == 'tile' and spec.get('clock') == 'multiple_cts_roots'
            and spec.get('clock_data_paths') == 'related_pll_ratio'):
        raise ValueError('seam_windows requires a multiple_cts_roots leaf tile under related_pll_ratio')
    ports = list(spec.get('clock_ports') or [])
    if not isinstance(sw, list) or not sw:
        raise ValueError('seam_windows must be a nonempty list')
    names = set()
    for w in sw:
        if not isinstance(w, dict) or set(w) != SEAM_WINDOW_KEYS:
            raise ValueError(f'seam_windows entry needs exactly {sorted(SEAM_WINDOW_KEYS)}')
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', str(w['name'])) or w['name'] in names:
            raise ValueError(f'seam_windows: invalid or duplicate name {w["name"]!r}')
        names.add(w['name'])
        if w['launch'] not in ports or w['capture'] not in ports or w['launch'] == w['capture']:
            raise ValueError(f'seam_windows {w["name"]}: launch / capture must be two different clock_ports')
        if (not isinstance(w['from'], list) or not w['from']
                or any(not isinstance(x, str) or not re.fullmatch(r'[A-Za-z0-9_.*]+', x) or '*' not in x[:1] for x in w['from'])):
            raise ValueError(f'seam_windows {w["name"]}: "from" must be cell globs [A-Za-z0-9_.*] starting with *')
        for k in ('setup_q', 'hold_q'):
            if type(w[k]) is not int or not 2 <= w[k] <= 12:
                raise ValueError(f'seam_windows {w["name"]}: {k} must be an integer 2..12 VCO ticks (landed: >= 2q)')
        if not isinstance(w['why'], str) or not w['why'].strip():
            raise ValueError(f'seam_windows {w["name"]}: why (the calendar) is required')
    return sw


def seam_window_sdc(spec):
    """Seam-window constraints (see seam_windows): per window, from the bank registers to every register of the reader
    root, set_max_delay setup_q * q and set_min_delay -hold_q * q with clock latency INCLUDED (OpenSTA path delay to a
    register check: required = window + capture latency + inter-clock uncertainty - setup, launch edge time removed),
    so the sign-off reserve (setup 150/210, hold 100 between different entries) still applies on top of the calendar
    window.  q is read from core_clk (period / 3), so the route SDC (route period) and signoff.sdc (sign-off period)
    scale alike.  Fail closed: a window whose patterns match no cell is an error.  The gate's cross_clock check sees
    these as declared (max_delay / min_delay); their slack is ordinary sign-off timing.  '' without the key."""
    sw = seam_windows(spec)
    if sw is None:
        return ''
    ports = list(spec['clock_ports'])
    o = [f'# ---- seam windows (landed 3:4 crossings inside this leaf, {len(sw)} windows; q = core period / 3)',
         'set ot_sw_q [expr {[get_property [get_clocks core_clk] period] / 3.0}]']
    for w in sw:
        pats = ' '.join(w['from'])
        o += [f'# {w["name"]}: {w["launch"]} -> {w["capture"]} setup {w["setup_q"]}q hold {w["hold_q"]}q ({w["why"]})',
              'set ot_sw_f {}',
              f'foreach ot_sw_p {{{pats}}} {{',
              '  set ot_sw_c [get_cells -quiet $ot_sw_p]',
              '  if {![llength $ot_sw_c]} { set ot_sw_c [get_cells -quiet -hierarchical $ot_sw_p] }',
              '  set ot_sw_f [concat $ot_sw_f $ot_sw_c]', '}',
              f'if {{![llength $ot_sw_f]}} {{ error "OT_SEAM_WINDOW: {w["name"]} bank patterns match no cell" }}',
              f'set ot_sw_t [get_clocks ot_entry_{ports.index(w["capture"])}]',
              f'set_max_delay [expr {{{w["setup_q"]} * $ot_sw_q}}] -from $ot_sw_f -to $ot_sw_t',
              f'set_min_delay [expr {{-{w["hold_q"]} * $ot_sw_q}}] -from $ot_sw_f -to $ot_sw_t',
              f'puts "OT_SEAM_WINDOW {w["name"]} cells=[llength $ot_sw_f] setup_ps=[expr {{{w["setup_q"]} * $ot_sw_q}}] '
              f'hold_ps=[expr {{{w["hold_q"]} * $ot_sw_q}}]"']
    return '\n'.join(o) + '\n'


def domains(spec):
    """Explicit related PLL /3 and /4 clock domains. No exception policy."""
    declared = spec.get('clock_entry_domains')
    leaf = native_leaf(spec)
    if leaf:
        signoff_period(spec)
        related_data(spec)
    # a cluster qualifies only as a LANDED cluster (lp.py record named; landed_record() validates it in load_spec)
    landed = landed_cluster(spec) and isinstance(spec.get('landed_record'), str) and bool(spec.get('children'))
    # a landed BAND (landed_band_record: one region of an lp parent, "landed_band": true) has exactly one root
    band = landed and spec.get('landed_band') is True
    if leaf and (spec.get('kind') != 'tile' and not landed or declared is None
                 or len(spec.get('clock_ports', [])) < (1 if band else 2)):
        raise ValueError('multiple_cts_roots requires a leaf tile, at least two roots and explicit IO domains')
    if declared is None:
        return {'core': dict(ratio=[1, 1], ports=list(spec['clock_ports']),
                             inputs=['*'], outputs=['*'])}
    if not isinstance(declared, dict) or 'core' not in declared:
        raise ValueError('entries: explicit domains require core ratio1/1')
    asynchronous = spec.get('clock_data_paths') == 'async_gray_fifo'
    if asynchronous:
        async_gray_fifo_constraints.relationship(spec)
    divided = spec.get('clock_data_paths') == 'related_pll_dividers'
    if divided:
        pll_divider_ratios(spec)
    families = spec.get('clock_data_paths') == gray_fifo_cdc_constraints.POLICY
    if families:
        gray_fifo_cdc_constraints.relationship(spec)
    cdc_async = spec.get('clock_data_paths') == cdc_sync_constraints.ASYNC_POLICY
    if cdc_async:
        cdc_sync_constraints.async_relationship(spec)
    owners = {}
    out = {}
    for name, data in declared.items():
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name):
            raise ValueError('entries: invalid domain name')
        if set(data) - {'ratio', 'ports', 'inputs', 'outputs', 'io_budget'}:
            raise ValueError('entries: unsupported domain policy (no clock exceptions)')
        ratio = data.get('ratio')
        if asynchronous or cdc_async:
            expected_ratio = [1, 1] if name == 'core' else [3072000, 2499999]
            if ratio != expected_ratio:
                raise ValueError(f'{spec.get("clock_data_paths")} requires actual stream833.333 / HBM1024 periods')
        if families and ratio != gray_fifo_cdc_constraints.family_ratio(name):
            raise ValueError(f'reviewed_gray_fifos {name} ratio must be the actual family period ratio')
        if not (divided or asynchronous or families or cdc_async) and ratio not in ([1, 1], [4, 3]):
            raise ValueError('entries: only related CK1/1 and CKV4/3 are supported')
        pll = leaf and spec.get('clock_data_paths') == 'related_pll_ratio'
        if leaf and (ratio != [1, 1] and not (divided or asynchronous or families or cdc_async or pll and ratio == [4, 3] and name != 'core') or not (asynchronous or families) and len(data.get('ports', [])) != 1):
            raise ValueError('multiple_cts_roots requires one actual related phase0 root per domain '
                             '(samefrequency, or a non-core 4/3 domain under related_pll_ratio)')
        if name == 'core' and ratio != [1, 1]:
            raise ValueError('entries: core ratio must be1/1')
        for field in ('ports', 'inputs', 'outputs'):
            if not isinstance(data.get(field), list) or any(not isinstance(x, str) for x in data[field]):
                raise ValueError(f'entries: {name}.{field} must be an explicit string list')
        if leaf and any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', x) for f in ('inputs', 'outputs') for x in data[f]):
            raise ValueError('multiple_cts_roots requires literal base IO names, no wildcard domains')
        if not data['ports']:
            raise ValueError(f'entries: {name} needs at least one actual entry port')
        for port in data['ports']:
            if port in owners:
                raise ValueError(f'entries: duplicate domain clock port {port}')
            owners[port] = name
        out[name] = data
    if spec.get('cdc_synchronizers') is not None:
        if set(owners) != set(spec['clock_ports']):
            raise ValueError('entries: domain clock coverage differs from actual source ports')
        if families:
            gray_fifo_cdc_constraints.event_groups(spec)   # family-period groups, linted with the FIFOs (gray_fifo (d))
        else:
            cdc_sync_constraints.validate(spec)
    if leaf and spec.get('clock_data_paths') == 'related_pll_ratio' and not any(d['ratio'] == [4, 3] for d in out.values()):
        raise ValueError('related_pll_ratio requires at least one actual 4/3 domain (else use related_same_frequency)')
    if set(owners) != set(spec['clock_ports']):
        raise ValueError('entries: domain clock coverage differs from actual source ports')
    if owners[spec['clock_port']] != 'core':
        raise ValueError('entries: primary clock_port must belong to core')
    return out


def virtual_clock(domain):
    return 'core_clk' if domain == 'core' else f'ot_io_{domain}'


def clocks(spec, period):
    if spec.get('clock') not in MODES:
        return f"create_clock -name core_clk -period {period} [get_ports {spec['clock_port']}]\n"
    ds = domains(spec)
    owners = {p: name for name, d in ds.items() for p in d['ports']}
    lines = [f'# OT_CLOCK_ENTRY_DOMAIN_API_VERSION {ENTRY_DOMAIN_API_VERSION}']
    for name, d in ds.items():
        value = period * d['ratio'][0] / d['ratio'][1]
        lines.append(f"create_clock -name {virtual_clock(name)} -period {value:.9f}")
    for i, port in enumerate(spec['clock_ports']):
        ratio = ds[owners[port]]['ratio']
        value = period * ratio[0] / ratio[1]
        lines.append(f"create_clock -name ot_entry_{i} -period {value:.9f} [get_ports {{{port}}}]")
    soft = forwarded_soft_clocks(spec)
    if soft:
        lines.append('set ::ot_ce_fwd_soft [dict create ' + ' '.join(
            '{' + e['port'] + '} {clock ' + e['clock'] + ' domain ' + e['domain'] + ' cells {' +
            ' '.join('{' + c + '}' for c in e['cells']) + '}}' for e in soft) + ']')
    if forwarded_clock_outputs.contract(spec):
        lines.append(forwarded_clock_outputs.metadata(spec).rstrip('\n'))
    for e in soft:
        d = ds[e['domain']]
        value = period * d['ratio'][0] / d['ratio'][1]
        lines.append(f"create_clock -name {e['clock']} -period {value:.9f} [get_ports {{{e['port']}}}]")
    return '\n'.join(lines) + '\n'


def forwarded_pre_cts_tcl(spec, entry_sdc):
    """Restore the existing forwarded-clock contract in a fresh CTS process.

    write_sdc preserves clocks, but not Tcl metadata.  The CTS wrapper needs
    these exact generated dictionaries before it checks sink ownership; the
    complete entry SDC is reapplied after CTS as before.  No clock, endpoint
    policy or timing constraint is changed here.
    """
    if not forwarded_soft_clocks(spec):
        return []
    out = []
    prefixes = ['set ::ot_ce_fwd_soft ', 'set ::ot_ce_refs ']
    if forwarded_clock_outputs.contract(spec):
        prefixes.append('set ::ot_ce_fwd_outputs ')
    for prefix in prefixes:
        matches = [line for line in entry_sdc.splitlines() if line.startswith(prefix)]
        if len(matches) != 1:
            raise ValueError('forwarded pre-CTS: missing or duplicate generated contract ' + prefix)
        out.extend(matches)
    return out



def domain_io_budget(name, d):
    """(in, out) outside-share fractions of a clock-entry domain's period.  Default 0.2 / 0.2 (the nominal native pin
    budget).  A domain may carry "io_budget": {"in": f, "out": f} derived from the composed parent hop (wire length +
    the peer's measured residual); only TIGHTENING (f >= 0.2, f <= 0.8) is accepted, so a child can never be closed
    against a looser boundary than the nominal one."""
    io = d.get('io_budget') or {}
    unknown = set(io) - {'in', 'out'}
    if unknown:
        raise ValueError(f'domain {name}: unknown io_budget keys {sorted(unknown)}')
    vals = []
    for k in ('in', 'out'):
        f = float(io.get(k, 0.2))
        if not (0.2 <= f <= 0.8):
            raise ValueError(f'domain {name}: io_budget {k} {f} outside [0.2, 0.8] (only tightening is allowed)')
        vals.append(f)
    return tuple(vals)

def strip_hold_budget(text, die):
    """FLOW-HOLD 2026-10-16: the die boundary hold budget lines (fenced '# OT_BH begin' .. '# OT_BH end', or a line
    ending ';# OT_BH') are emitted only for a spec with "hold_budget": "die", so every other kit regenerates unchanged."""
    if die:
        return text
    out, skip = [], False
    for line in text.split('\n'):
        t = line.strip()
        if t.startswith('# OT_BH begin'):
            skip = True
            continue
        if skip:
            skip = not t.startswith('# OT_BH end')
            continue
        if t.endswith(';# OT_BH'):
            continue
        out.append(line)
    return '\n'.join(out)


def generate(spec, root):
    return strip_hold_budget(_generate(spec, root), spec.get('hold_budget', 'tile') == 'die')


def _generate(spec, root):
    if spec.get('clock') not in MODES:
        return ''
    ds = domains(spec)
    direct = direct_macro_clock_entries.load(spec, root)
    roots = list(spec['clock_ports']) if spec.get('clock') == 'multiple_cts_roots' else (spec.get('clock_cts_roots', []) if spec.get('clock') == 'hybrid_entries' else [])
    if spec.get('clock') == 'hybrid_entries' and (not isinstance(roots, list) or not roots or
            not all(isinstance(p, str) for p in roots) or len(set(roots)) != len(roots) or not set(roots) < set(spec['clock_ports'])):
        raise ValueError('hybrid_entries requires a nonempty proper subset of distinct clock_cts_roots')
    refs, counts, raw, check_only, cotimed = {}, {}, {}, {}, {}
    landed = landed_cluster(spec)
    for child in spec.get('children', []):
        view = Path(root) / child['view']
        master = view.name
        counts[master] = counts.get(master, 0) + int(child.get('count', 1))
        if master in refs:
            continue
        record = json.loads((view / 'insertion.json').read_text())
        pins = record.get('clock_measurements')
        if not pins:
            pin = record.get('lib_clock_pin')
            if not pin:
                # Legacy exports have one routed root named ck and one actual
                # Liberty clock pin named clk. Only a unique pin can bind it.
                clocks = child_lint.clock_insertion((view / f'{master}_tt.lib').read_text())
                if len(clocks) != 1 or not record.get('clock'):
                    raise ValueError(f'{view}: ambiguous routed clock pin association')
                pin = next(iter(clocks))
            pins = {pin: record}
        if len(pins) > 1 and spec.get('clock_entry_domains') is None:
            raise ValueError(f'{view}: multi-clock child requires explicit entry domain/ratio/IO mapping')
        refs[master] = {}
        # HF-4d 10-19: a landed cluster's hard child may carry raw SRAM clock entries (no ETM arcs, no routed boundary);
        # their reference and tolerance come from the leaf's CLOSED RECORD (landed_raw_pins), never from the ETM
        child_rec = landed_record_pins(view, root) if landed else dict(raw={}, cotimed={})
        child_raw = child_rec['raw']
        for pin, info in child_rec['cotimed'].items():
            cotimed[f'{master}/{pin}'] = info
        if landed:
            # ROOT-LANDEDHC 10-19: the child clock pins that carry Liberty TIMING CHECKS (setup/hold/recovery/removal
            # related_pin) may be reached by net trace as check-only sinks (TW-HBM-COLLP); a pin with no check arc (a raw
            # SRAM entry) never is, so a raw pin can never pass as an ordinary child sink
            for pin in sorted(liberty_check_pins((view / f'{master}_tt.lib').read_text())):
                if pin in pins and pin not in child_raw:
                    check_only[f'{master}/{pin}'] = 1
        for pin, info in child_raw.items():
            raw[f'{master}/{pin}'] = info
        for pin, measured in pins.items():
            refs[master][pin] = {}
            for corner in CORNERS:
                lib = view / f'{master}_{corner}.lib'
                if not lib.is_file():
                    raise ValueError(f'{lib}: missing bound child ETM')
                clocks = child_lint.clock_insertion(lib.read_text())
                if pin not in clocks or set(clocks) != set(pins):
                    raise ValueError(f'{lib}: routed/Liberty clock pin association mismatch')
                if pin in child_raw:
                    refs[master][pin][corner] = child_raw[pin]['refs'][corner]
                    continue
                data = measured.get(corner, {})
                b = data.get('boundary') or {}
                if not b.get('n'):
                    raise ValueError(f'{view}/{pin}/{corner}: missing real routed boundary reference')
                values = [float(b[k]) for k in ('min', 'mean', 'max')]
                if data.get('errors') or not all(math.isfinite(x) for x in values):
                    raise ValueError(f'{view}/{pin}/{corner}: missing real routed boundary reference')
                if not values[0] <= values[1] <= values[2]:
                    raise ValueError(f'{view}/{pin}/{corner}: inconsistent boundary reference')
                refs[master][pin][corner] = values
    expected = sum(counts[m] * len(refs[m]) for m in refs) + len(direct['entries'])
    if landed:
        # every port is a region root; the hard-child clock pins are root sinks, counted by the Tcl (fail closed)
        if direct['entries'] or not refs:
            raise ValueError('landed cluster: no raw macro entries; hard children are sinks of their region root')
    elif expected != len(spec['clock_ports']) - len(roots):
        raise ValueError(f'entries: {expected} bound child clock pins, {len(spec["clock_ports"]) - len(roots)} hard source ports')
    rows = []
    for master, pins in refs.items():
        for pin, corners in pins.items():
            row = ' '.join(f'{c} {{{" ".join(map(str, corners[c]))}}}' for c in CORNERS)
            rows.append(f'{{{master}/{pin}}} {{{row}}}')
    domain_rows = []
    owner_rows = []
    for name, d in ds.items():
        patterns = lambda names: ' '.join('{' + n + '}' for n in names)
        period = signoff_period(spec) * d["ratio"][0] / d["ratio"][1]
        fin, fout = domain_io_budget(name, d)
        out_row = '' if fout == 0.2 else " io_budget_out_ps " + str(round(period * fout, 3))
        domain_rows.append("{" + name + "} {clock " + virtual_clock(name) + " io_budget_ps " + str(round(period * fin, 3)) + out_row + " inputs {" + patterns(d["inputs"]) + "} outputs {" + patterns(d["outputs"]) + "}}")
        owner_rows.extend(f"{{{p}}} {{{name}}}" for p in d['ports'])
    body = (landed_raw_body(LANDED_BODY, bool(cotimed)) if raw else LANDED_BODY) if landed else LEAF_BODY if native_leaf(spec) else BODY
    mrc = multi_root_children(spec, root) if landed else []
    if mrc:
        body = multi_root_body(body)
    fwd = forwarded_clock_ports(spec)
    if fwd:
        body = forwarded_body(body)
    soft = forwarded_soft_clocks(spec)
    if soft:
        body = forwarded_soft_body(body)
    if spec.get('clock_data_paths') == 'async_gray_fifo':
        body = async_gray_fifo_constraints.extend(body, spec, root)
    if spec.get('cdc_synchronizers') is not None and spec.get('clock_data_paths') != gray_fifo_cdc_constraints.POLICY:
        body = cdc_sync_constraints.extend(body, spec, root)
    if spec.get('clock_data_paths') == gray_fifo_cdc_constraints.POLICY:
        body = gray_fifo_cdc_constraints.extend(body, spec, root)
    if direct['entries']:
        body = direct_body(body, direct)
    return (f'# OT_CLOCK_ENTRY_DOMAIN_API_VERSION {ENTRY_DOMAIN_API_VERSION}\n'
            '# AUTO clock entries: bound insertion.json boundary refs; no ETM arc modification.\n'
            + (('set ::ot_ce_leaf_roots 1\nset ::ot_ce_related_data ' + str(int(related_data(spec))) + '\n') if native_leaf(spec) else '')
            + (f'set ::ot_ce_landed_cluster 1\nset ::ot_ce_landed_child_pins {expected}\n' if landed else '')
            + ('set ::ot_ce_multi_root_children {' + ' '.join('{' + c + '}' for c in mrc) + '}\n' if landed and mrc else '')
            + ('set ::ot_ce_fwd_ports {' + ' '.join('{' + p + '}' for p in fwd) + '}\n' if fwd else '')
            + ('set ::ot_ce_fwd_soft [dict create ' + ' '.join(
                '{' + e['port'] + '} {clock ' + e['clock'] + ' domain ' + e['domain'] + ' cells {' +
                ' '.join('{' + c + '}' for c in e['cells']) + '}}' for e in soft) + ']\n' if soft else '')
            + forwarded_clock_outputs.metadata(spec, root)
            + ('set ::ot_ce_landed_raw [dict create ' + ' '.join(
                f'{{{k}}} {{ref {v["ref"]} tol {v["tol"]:g} record {v["record"]}}}' for k, v in sorted(raw.items())) + ']\n'
               if raw else '')
            + ('set ::ot_ce_landed_cotimed [dict create ' + ' '.join(
                f'{{{k}}} {{ref {v["ref"]} tol {v["tol"]:g} record {v["record"]}}}' for k, v in sorted(cotimed.items())) + ']\n'
               if cotimed else '')
            + ('set ::ot_ce_check_only [dict create ' + ' '.join(f'{{{k}}} 1' for k in sorted(check_only)) + ']\n'
               if check_only else '') +
            'set ::ot_ce_refs [dict create ' + ' '.join(rows) + ']\n'
            'set ::ot_ce_counts [dict create ' + ' '.join(f'{{{m}}} {n}' for m, n in counts.items()) + ']\n'
            'set ::ot_ce_domains [dict create ' + ' '.join(domain_rows) + ']\n'
            'set ::ot_ce_source_domains [dict create ' + ' '.join(owner_rows) + ']\n'
            'set ::ot_ce_explicit_domains ' + str(int(spec.get('clock_entry_domains') is not None)) + '\n'
            'set ::ot_ce_cts_roots {' + ' '.join('{' + p + '}' for p in roots) + '}\n'
            'set ::ot_ce_ports {' + ' '.join('{' + p + '}' for p in spec['clock_ports']) + '}\n' + body)


BODY = r'''
proc ot_ce_corner {} {
  if {[info exists ::ot_ioref_scene] && $::ot_ioref_scene eq "BC"} { return ff }
  if {[info exists ::ot_ce_corner]} { return $::ot_ce_corner }
  # WC is a scene label, not an actual library corner: option-B overlays WC
  # with TT. Bind the reference to actual loaded child Liberty objects.
  set found {}
  foreach cell [get_cells -quiet -hierarchical *] {
    set master [get_property $cell ref_name]
    if {![dict exists $::ot_ce_counts $master]} continue
    set libcells [get_lib_cells -quiet -of_objects $cell]
    if {![llength $libcells]} { error "OT_ENTRIES: $master has no loaded Liberty association" }
    foreach lc $libcells {
      set full [get_full_name $lc]
      if {![regexp -nocase {_(tt|ff|ss)/} $full -> corner]} { error "OT_ENTRIES: unknown actual child Liberty corner $full" }
      dict set found [string tolower $corner] 1
    }
  }
  if {[dict size $found] == 1} { return [lindex [dict keys $found] 0] }
  # A multi-mode database needs its actual setup corner or BC scene shim.
  if {[info exists ::env(OT_MM_SETUP_CORNER)]} {
    switch -nocase -- $::env(OT_MM_SETUP_CORNER) {
      TC - tt {set corner tt} BC - ff {set corner ff} WC - ss {set corner ss}
      default { error "OT_ENTRIES: unknown actual setup corner" }
    }
    if {[dict exists $found $corner]} { return $corner }
  }
  error "OT_ENTRIES: ambiguous actual loaded child corners [dict keys $found]"
}
# get_property pin arrival_max_rise is a DATA arrival query. On a clock-only
# macro pin it returns an infinity sentinel even with a finite propagated clock
# path. Read propagated clock tags in the current scene and remove the
# source waveform edge time; falling-edge-only registers include that phase.
proc ot_ce_finite {value} {
  return [expr {[string is double -strict $value] && ![regexp -nocase {inf|nan} $value]}]
}
proc ot_ce_clock_wire {pin clock} {
  set scene [get_property [sta::cmd_scene] name]
  set clock_name [get_full_name $clock]
  set by_transition [dict create rise {} fall {}]
  set waveform {}
  foreach time [$clock waveform] {lappend waveform [sta::time_sta_ui $time]}
  if {[llength $waveform] != 2 || ![ot_ce_finite [lindex $waveform 0]] ||
      ![ot_ce_finite [lindex $waveform 1]]} {
    error "OT_ENTRIES: invalid source clock waveform $clock_name"
  }
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    foreach transition {rise fall} marker {^ v} {
      set paths [$vertex path_iterator $transition max]
      while {[$paths has_next]} {
        set path [$paths next]
        # Sink transition and source clock edge are distinct (inverting trees).
        # Exclude data, ideal, other-scene and other-clock paths as before.
        set tag [$path tag]
        set edge [lindex $tag 4]
        if {[lindex $tag 1] ne $scene || [lindex $tag 2] ne "${marker}max" ||
            [lindex $tag 3] ne $clock_name || $edge ni {^ v} ||
            [string first "(clock prop)" $tag] < 0} continue
        set arrival [sta::time_sta_ui [$path arrival]]
        if {![ot_ce_finite $arrival]} {
          $paths finish
          error "OT_ENTRIES: nonfinite propagated clock arrival on [get_full_name $pin] scene=$scene clock=$clock_name"
        }
        set phase [lindex $waveform [expr {$edge eq "^" ? 0 : 1}]]
        dict lappend by_transition $transition [expr {$arrival - $phase}]
      }
      $paths finish
    }
  }
  # Preserve the rising pin-transition reference. An inverted/negedge clock
  # may associate it with the falling source edge; remove that actual phase.
  # Fall-only pins remain measurable. Multiple same-transition tags fail.
  set values [dict get $by_transition rise]
  if {![llength $values]} {set values [dict get $by_transition fall]}
  if {[llength $values] != 1} {
    # Synthesis/floorplan have no extracted entry wire. This is solely a finite
    # pre-CTS diagnostic reference; routed gates must measure a clock path.
    if {![llength $values] && [info exists ::ot_ref_pre_cts] && $::ot_ref_pre_cts &&
        (![info exists ::ot_ce_require_wire] || !$::ot_ce_require_wire)} {
      puts "OT_ENTRIES PRE_CTS_ZERO_WIRE [get_full_name $pin] scene=$scene"
      return 0.0
    }
    error "OT_ENTRIES: missing unique finite propagated clock arrival on [get_full_name $pin] scene=$scene clock=$clock_name"
  }
  return [lindex $values 0]
}
# Match the structural IO boundary population in ck_insertion.py and io_ref_routed.sdc.
proc ot_ce_boundary_cells {} {
  set regs {}
  foreach p [all_registers -clock_pins] {
    set n [get_full_name $p]
    dict set regs [regsub {/[^/]+$} $n {}] $n
  }

set bnd {}
set ot_ck_data {}
set ot_ck_async {}
foreach p [all_registers -async_pins] { dict set ot_ck_async [get_full_name $p] 1 }
foreach p [all_registers -data_pins] {
  set n [get_full_name $p]
  if {![dict exists $ot_ck_async $n]} { dict set ot_ck_data $n 1 }
}
set din [all_inputs -no_clocks]
if {[llength $din]} {
  foreach p [get_fanout -from $din -flat -endpoints_only -trace_arcs all] {
    set n [get_full_name $p]
    if {![dict exists $ot_ck_data $n]} continue
    set i [regsub {/[^/]+$} $n {}]
    if {[dict exists $regs $i]} { dict set bnd $i 1 }
  }
}
set dout [all_outputs]
if {[llength $dout]} {
  foreach p [get_fanin -to $dout -flat -startpoints_only -trace_arcs all] {
    set i [regsub {/[^/]+$} [get_full_name $p] {}]
    if {[dict exists $regs $i]} { dict set bnd $i 1 }
  }
}

  return $bnd
}
# Owner 2026-10-17 0dq clock rule for one glue CTS root in the current scene: FAIL iff the pin-flop spread
# (pin_hi - pin_lo over the boundary registers, or every sink when none is at the boundary) exceeds 80 ps at
# TT or FF; SS is sensitivity only.  > 15k sinks and > 300 ps insertion only WARN.
proc ot_ce_clock_rule {corner name sinks all_mean pin_mean pin_lo pin_hi scope} {
  set spread [expr {$pin_hi - $pin_lo}]
  set warn {}
  if {$sinks > 15000} { lappend warn "sinks $sinks > 15000 (guidance)" }
  if {$all_mean > 300 || $pin_mean > 300} {
    lappend warn "insertion all_mean [format %.1f $all_mean] / pin_mean [format %.1f $pin_mean] ps > 300 (guidance)"
  }
  if {[string tolower $corner] in {tt ff} && $spread > 80} {
    set level FAIL
  } elseif {[llength $warn]} {
    set level WARN
  } else {
    set level PASS
  }
  puts "OT_HYBRID CLOCK_RULE $corner $name $level pin_spread=[format %.1f $spread] scope=$scope sinks=$sinks[expr {[llength $warn] ? " WARN: [join $warn {; }]" : ""}]"
  return $level
}

proc ot_ce_boundary_pins {pins boundary_cells} {
  set regs {}; set boundary {}
  foreach pin $pins {dict set regs [regsub {/[^/]+$} [get_full_name $pin] {}] $pin}
  dict for {name unused} $boundary_cells {
    if {[dict exists $regs $name]} {dict set boundary $name [dict get $regs $name]}
  }
  return [dict values $boundary]
}

proc ot_ce_apply {} {
  set corner [ot_ce_corner]
  set clk [get_clocks core_clk]
  if {[llength $clk] != 1} { error "OT_ENTRIES: core_clk missing" }
  # Wires-only parents have no CTS tree to set this flag for us.
  # Ideal clocks silently report zero network arrival despite real entry wires.
  set_propagated_clock [get_clocks ot_entry_*]
  # Before CTS, a standard-cell root is still one unbuffered high-fanout
  # net. Propagating that net invents multi-ns skew and clock-pin slew;
  # its delay is not the tree that CTS will build. Keep only these declared
  # CTS roots ideal during the explicit pre-CTS diagnostic. Raw macro and
  # hardened-child entries retain actual entry-wire propagation. Routed
  # require-wire checks always propagate and measure every physical root.
  if {[info exists ::ot_ref_pre_cts] && $::ot_ref_pre_cts &&
      (![info exists ::ot_ce_require_wire] || !$::ot_ce_require_wire)} {
    foreach name $::ot_ce_cts_roots {
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      unset_propagated_clock $clock
      puts "OT_ENTRIES PRE_CTS_IDEAL_CTS_ROOT $name"
    }
  }
  set sources {}; set names {}
  foreach c [get_clocks ot_entry_*] {
    foreach p [get_property $c sources] { lappend sources $p; lappend names [get_full_name $p] }
  }
  if {[lsort $names] ne [lsort $::ot_ce_ports]} { error "OT_ENTRIES: source clock coverage differs from spec" }
  foreach c [get_clocks ot_entry_*] { set_clock_latency -source 0 $c }
  sta::worst_slack_cmd max
  set rows {}; set seen {}; set counts {}
  foreach cell [get_cells -quiet -hierarchical *] {
    set master [get_property $cell ref_name]
    if {![dict exists $::ot_ce_counts $master]} continue
    dict incr counts $master
    foreach pin [get_pins -quiet -of_objects $cell] {
      set key "$master/[get_property $pin lib_pin_name]"
      if {![dict exists $::ot_ce_refs $key]} continue
      set ports [get_ports -quiet -of_objects [get_nets -quiet -of_objects $pin]]
      if {[llength $ports] != 1} { error "OT_ENTRIES: [get_full_name $pin] lacks one direct top clock port" }
      set port [lindex $ports 0]; set name [get_full_name $port]
      if {$name ni $::ot_ce_ports || $name in $::ot_ce_cts_roots || [dict exists $seen $name]} { error "OT_ENTRIES: duplicate or undeclared source $name" }
      dict set seen $name 1
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      if {[llength $clock] != 1} { error "OT_ENTRIES: $name has no unique related clock" }
      set wire [ot_ce_clock_wire $pin $clock]
      if {![ot_ce_finite $wire]} { error "OT_ENTRIES: nonfinite entry wire clock arrival on [get_full_name $pin]" }
      if {abs($wire) < 1.0e-9 && [info exists ::ot_ce_require_wire] && $::ot_ce_require_wire} {
        # A zero arrival is admissible only if actual source and child pin are
        # physically coincident. Missing parasitics/ideal clocks cannot qualify.
        if {![llength [info commands ord::get_db_block]]} { error "OT_ENTRIES: zero wire lacks physical source/pin proof" }
        set block [ord::get_db_block]
        set bt [$block findBTerm $name]
        set it [$block findITerm [get_full_name $pin]]
        if {$bt eq "NULL" || $it eq "NULL"} { error "OT_ENTRIES: missing physical source/child clock pin" }
        set pb [$bt getBBox]; set ib [$it getBBox]
        set distance [expr {(abs(([$pb xMin]+[$pb xMax])-([$ib xMin]+[$ib xMax])) + abs(([$pb yMin]+[$pb yMax])-([$ib yMin]+[$ib yMax]))) / 2.0 / [$block getDbUnitsPerMicron]}]
        if {$distance > 0.001} { error "OT_ENTRIES: zero clock wire arrival despite $distance um source/pin separation on $name" }
        puts "OT_ENTRIES ZERO_WIRE_PROVEN $name [get_full_name $pin] distance=$distance"
      }
      lassign [dict get $::ot_ce_refs $key $corner] lo mean hi
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      if {[llength $clock] != 1} { error "OT_ENTRIES: $name has no unique related clock" }
      set ttmean [lindex [dict get $::ot_ce_refs $key tt] 1]
      set domain [dict get $::ot_ce_source_domains $name]
      set vc [get_clocks [dict get $::ot_ce_domains $domain clock]]
      if {abs([get_property $vc period]-[get_property $clock period])>0.001} { error "OT_ENTRIES: domain/source period mismatch $name" }
      lappend rows [list $port $pin $wire $lo $mean $hi $clock $ttmean $domain]
    }
  }
  dict for {m n} $::ot_ce_counts {
    if {![dict exists $counts $m] || [dict get $counts $m] != $n} { error "OT_ENTRIES: bound child count mismatch $m" }
  }
  # Source latencies are zero for this whole measurement loop, and no STA
  # constraints/netlist change until rows are complete. Query the same bounded
  # boundary population once per apply/current corner, never across calls.
  set boundary_cells {}; set boundary_cells_ready 0
  # Each glue root owns a real CTS tree. Measure every propagated standard-cell
  # clock sink in the current scene; never substitute a declared/common phase.
  foreach name $::ot_ce_cts_roots {
    set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
    set pins [all_registers -clock [get_full_name $clock] -clock_pins]
    if {![llength $pins]} { error "OT_HYBRID: glue root $name has no actual sequential clock sinks" }
    set arrivals {}; set measured {}; set total 0.0
    foreach pin $pins {
      set cell [get_cells -of_objects $pin]
      set master [get_property $cell ref_name]
      if {[dict exists $::ot_ce_counts $master]} { error "OT_HYBRID: CTS root $name reaches a hard child" }
      set arrival [ot_ce_clock_wire $pin $clock]
      lappend arrivals $arrival
      dict set measured [get_full_name $pin] $arrival
      set total [expr {$total + $arrival}]
    }
    set arrivals [lsort -real $arrivals]
    set lo [lindex $arrivals 0]; set hi [lindex $arrivals end]
    set tree_mean [expr {$total / [llength $arrivals]}]
    set mean $tree_mean
    if {[info exists ::ot_ce_require_wire] && $::ot_ce_require_wire && $mean <= 0} {
      error "OT_HYBRID: glue root $name lacks a positive actual propagated CTS insertion"
    }
    if {!$boundary_cells_ready} {
      set boundary_cells [ot_ce_boundary_cells]; set boundary_cells_ready 1
    }
    set boundary [ot_ce_boundary_pins $pins $boundary_cells]
    set scope boundary
    if {![llength $boundary]} { set boundary $pins; set scope all_internal_only }
    set arrivals {}; set total 0.0
    foreach pin $boundary {
      set arrival [dict get $measured [get_full_name $pin]]
      lappend arrivals $arrival; set total [expr {$total + $arrival}]
    }
    set arrivals [lsort -real $arrivals]
    set lo [lindex $arrivals 0]; set hi [lindex $arrivals end]
    set mean [expr {$total / [llength $arrivals]}]
    # Clock rule (owner 2026-10-17 0dq, textbook_lint.clock_rule_eval): FAIL only on the pin-flop (boundary
    # register; child-flop on a region-rooted parent) spread > 80 ps at TT or FF.  > 15k sinks on one root and
    # insertion > 300 ps are guidance (WARN): the neighbour boundary is matched by the source-latency
    # compensation below / a ring crossing and judged by native_pin_audit --relative-to.
    if {[ot_ce_clock_rule $corner $name [llength $pins] $tree_mean $mean $lo $hi $scope] eq "FAIL"} {
      error "OT_HYBRID: glue root $name pin-flop spread [format %.1f [expr {$hi-$lo}]] ps > 80 at $corner ($scope, [llength $boundary] of [llength $pins] sinks)"
    }
    set domain [dict get $::ot_ce_source_domains $name]
    lappend rows [list [get_ports $name] [lindex $pins 0] 0 $lo $mean $hi $clock $mean $domain]
    dict set seen $name 1
    puts "OT_HYBRID CTS_MEASURE $corner $name sinks=[llength $pins] reference_scope=$scope boundary_sinks=[llength $boundary] min=$lo mean=$mean max=$hi all_mean=$tree_mean"
  }
  if {[dict size $seen] != [llength $::ot_ce_ports]} { error "OT_ENTRIES: incomplete actual child/source coverage" }
  set ref 0
  foreach row $rows { lassign $row p pin wire lo mean hi; set ref [expr {max($ref, $wire + $mean)}] }
  set low {}; set high {}; set lowclocks {}; set highclocks {}; set domain_low {}; set domain_high {}
  foreach row $rows {
    lassign $row p pin wire lo mean hi clock ttmean domain
    # Physical source level includes the entry wire, not just the hard
    # child's internal insertion. Only a TT scene measures the TT wire.
    # Other physical scenes conservatively reserve the deep pair budget;
    # they must not guess TT wire delay from FF/SS or an ideal zero arrival.
    set deep [expr {$ttmean > 300}]
    set level_basis "zero-wire diagnostic"
    if {$corner eq "tt"} {
      set deep [expr {$ttmean + $wire > 300}]
      set level_basis "TT timing-graph entry arrival + child R (physical proof required for route/signoff)"
    } elseif {[info exists ::ot_ce_require_wire] && $::ot_ce_require_wire} {
      set deep 1
      set level_basis "TT wire level not measured in this scene; conservative210ps setup"
    }
    if {$deep} { lappend highclocks $clock } else { lappend lowclocks $clock }
    puts "OT_ENTRIES LEVEL [get_full_name $p] deep=$deep basis=$level_basis"
    set latency [expr {$ref - $wire - $mean}]
    if {![ot_ce_finite $ref] || ![ot_ce_finite $latency]} { error "OT_ENTRIES: nonfinite reference/source latency on [get_full_name $p]" }
    set_clock_latency -source $latency $clock
    lappend low [expr {$ref + $lo - $mean}]; lappend high [expr {$ref + $hi - $mean}]
    dict lappend domain_low $domain [expr {$ref + $lo - $mean}]
    dict lappend domain_high $domain [expr {$ref + $hi - $mean}]
    puts "OT_ENTRIES COMP $corner [get_full_name $p] -> [get_full_name $pin] wire=$wire R=$mean latency=$latency phi=$ref"
  }
  # Every entry is synchronous and related. Reserve die skew on internal hops;
  # no asynchronous groups, false paths or ETM insertion add-back.
  # H1 authoritative pair_check.HOLD_TREE =50ps hold margin+50ps die skew (hold 100, setup 150).
  # Each deep tile has its own earlier trunk tap. The authoritative TREE
  # pair budget uses150ps die skew when either reference exceeds300ps,
  # including deep-to-deep pairs (pair_check.SKEW_DEEP) (setup 210).
  # S-ELEM-PQ 2026-10-15: a register pair on ONE glue CTS root of this tile shares one die tap and one
  # propagated standard-cell tree whose real skew STA already sees, so it is timed like every single-root
  # tile (base uncertainty); the die-skew reserve applies to every pair of DIFFERENT entries and to hard-
  # child entries (dsfd_bf_front_static: the uniform rule put hold 100 / setup 210 on all 12,276 core-root
  # paths -> 15,826 hold endpoints, 119k buffers).
  set ot_ce_glue {}
  foreach name $::ot_ce_cts_roots { lappend ot_ce_glue [get_full_name [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]] }
  set ot_ce_high {}
  foreach c $highclocks { lappend ot_ce_high [get_full_name $c] }
  foreach a [get_clocks ot_entry_*] {
    foreach b [get_clocks ot_entry_*] {
      set an [get_full_name $a]; set bn [get_full_name $b]
      if {$an eq $bn && $an in $ot_ce_glue} { continue }
      set_clock_uncertainty -setup [expr {($an in $ot_ce_high || $bn in $ot_ce_high) ? 210 : 150}] -from $a -to $b
      set_clock_uncertainty -hold 100 -from $a -to $b
    }
  }
  # Preserve measured boundary spread: balancing the mean does not erase the
  # earliest/latest physical boundary arrivals or change ETM setup/hold arcs.
  set lmin [lindex [lsort -real $low] 0]; set lmax [lindex [lsort -real $high] end]
  unset_input_delay [all_inputs]; unset_output_delay [all_outputs]
  set sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 90}]
  set hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
  set hki [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]
  # OT_BH begin -- DIE BOUNDARY HOLD BUDGET (FLOW-HOLD 2026-10-16, results/arch/boundary_hold_budget_1016/RULE.md;
  # opt-in OT_IO_HOLD_BUDGET=die): output min = U - (L_min + C), input min = L_min + C + U per domain, as io_ref_skew.sdc
  set bh_die [expr {[info exists ::env(OT_IO_HOLD_BUDGET)] && $::env(OT_IO_HOLD_BUDGET) eq "die"}]
  set bhc [expr {[info exists ::env(OT_BH_LAUNCH_MIN_PS)] ? $::env(OT_BH_LAUNCH_MIN_PS) : 25}]
  set bhu [expr {[info exists ::env(OT_BH_TILE_HOLD_UNC_PS)] ? $::env(OT_BH_TILE_HOLD_UNC_PS) : 25}]
  set bhr [expr {[info exists ::env(OT_BH_ROUTE_RELIEF_PS)] ? $::env(OT_BH_ROUTE_RELIEF_PS) : 0}]
  # OT_BH end
  set covered_in {}; set covered_out {}
  dict for {domain info} $::ot_ce_domains {
    if {![dict exists $domain_low $domain]} { error "OT_ENTRIES: domain $domain has no actual child clock pins" }
    set dlmin [lindex [lsort -real [dict get $domain_low $domain]] 0]
    set dlmax [lindex [lsort -real [dict get $domain_high $domain]] end]
    set vc [get_clocks [dict get $info clock]]
    set budget [dict get $info io_budget_ps]
    # Optional composition-derived output budget (domain "io_budget": {"out": f}, f >= 0.2): the outside share of the
    # cycle on this domain's outputs; larger = a TIGHTER launch (flop -> pin) inside the child, never a relaxation.
    set budget_out [expr {[dict exists $info io_budget_out_ps] ? [dict get $info io_budget_out_ps] : $budget}]
    set inputs {}; set outputs {}
    foreach pattern [dict get $info inputs] {
      foreach p [get_ports -quiet $pattern -filter "direction == input"] {
        set n [get_full_name $p]
        if {$n in $::ot_ce_ports} continue
        if {[dict exists $covered_in $n]} { error "OT_ENTRIES: input $n has duplicate IO domains" }
        dict set covered_in $n $domain; lappend inputs $p
      }
    }
    foreach pattern [dict get $info outputs] {
      foreach p [get_ports -quiet $pattern -filter "direction == output"] {
        set n [get_full_name $p]
        if {[dict exists $covered_out $n]} { error "OT_ENTRIES: output $n has duplicate IO domains" }
        dict set covered_out $n $domain; lappend outputs $p
      }
    }
    if {[llength $inputs]} {
      set_input_delay [expr {$budget+$dlmax+$sk}] -max -clock $vc $inputs
      set_input_delay [expr {$dlmin-$hki}] -min -clock $vc $inputs
      if {$bh_die} { set_input_delay [expr {$dlmin+$bhc+$bhu+$bhr}] -min -clock $vc $inputs }  ;# OT_BH
    }
    if {[llength $outputs]} {
      set_output_delay [expr {$budget_out-$dlmax+$sk}] -max -clock $vc $outputs
      set_output_delay [expr {-$dlmin-$hk}] -min -clock $vc $outputs
      if {$bh_die} { set_output_delay [expr {$bhu+$bhr-$dlmin-$bhc}] -min -clock $vc $outputs }  ;# OT_BH
    }
    if {[info exists ::env(OT_IO_INTER)] && $::env(OT_IO_INTER) ne ""} {
      foreach pattern [split $::env(OT_IO_INTER) ","] {
        foreach p [get_ports -quiet $pattern] {
          set n [get_full_name $p]
          if {[dict exists $covered_in $n] && [dict get $covered_in $n] eq $domain} {
            set_input_delay [expr {$budget+$dlmax+150}] -max -clock $vc $p
          }
          if {[dict exists $covered_out $n] && [dict get $covered_out $n] eq $domain} {
            set_output_delay [expr {$budget_out-$dlmax+150}] -max -clock $vc $p
          }
        }
      }
    }
    puts "OT_ENTRIES DOMAIN $domain [get_property $vc period]ps IO[llength $inputs]/[llength $outputs] boundary=$dlmin..$dlmax"
  }
  if {[dict size $covered_in] != [llength [all_inputs -no_clocks]] || [dict size $covered_out] != [llength [all_outputs]]} {
    error "OT_ENTRIES: incomplete actual IO domain coverage (resets must also have a domain)"
  }
  puts "OT_ENTRIES COMP DONE $corner [llength $rows] entries phi=$ref boundary=$lmin..$lmax"
}
ot_ce_apply
'''


LEAF_OWNERSHIP = r'''
# Constants are proved from actual OpenDB connectivity and the loaded Liberty
# output functions. Cell/port names, case analysis and timing-graph constant
# pruning are never proofs. A cell output is constant when every loaded corner
# gives its master the same Liberty function and that function is a literal, or a
# combinational expression whose every variable is an input pin of the same
# instance on a net with no input port and exactly one driver that is itself
# constant (TIEHI/TIELO prove themselves through their literal function; a
# synthesis buffer/inverter or any gate of constants follows). Registers never
# qualify; unknown or unparsable functions fail closed.
proc ot_ce_constant_net {net seen remaining} {
  if {$remaining <= 0 || $net in {"" NULL}} {return 0}
  foreach port [$net getBTerms] {if {[$port getIoType] ne "OUTPUT"} {return 0}}
  set drivers {}
  foreach pin [$net getITerms] {if {[$pin isOutputSignal]} {lappend drivers $pin}}
  if {[llength $drivers] != 1} {return 0}
  return [ot_ce_constant_iterm [lindex $drivers 0] $seen $remaining]
}
proc ot_ce_constant_iterm {pin seen remaining} {
  if {$remaining <= 0 || ![$pin isOutputSignal]} {return 0}
  set inst [$pin getInst];set name "[$inst getName]/[[$pin getMTerm] getName]"
  if {[dict exists $seen $name]} {return 0}
  if {[info exists ::ot_ce_const_memo] && [dict exists $::ot_ce_const_memo $name]} {return [dict get $::ot_ce_const_memo $name]}
  dict set seen $name 1
  set result [ot_ce_constant_iterm_eval $inst $pin $seen $remaining]
  dict set ::ot_ce_const_memo $name $result
  return $result
}
proc ot_ce_constant_iterm_eval {inst pin seen remaining} {
  if {[info exists ::ot_ce_register_cells] && [dict exists $::ot_ce_register_cells [$inst getName]]} {return 0}
  set master [[$inst getMaster] getName];set output [[$pin getMTerm] getName]
  set functions {};set matched 0
  foreach library [get_libs -quiet *] {
    set cell [$library find_liberty_cell $master]
    if {$cell in {"" NULL}} continue
    set lp [$cell find_liberty_port $output]
    if {$lp in {"" NULL} || [sta::liberty_port_direction $lp] ne "output"} {return 0}
    dict set functions [string map {" " "" "\t" "" "\n" ""} [$lp function]] 1
    incr matched
  }
  if {!$matched || [dict size $functions] != 1} {return 0}
  set function [lindex [dict keys $functions] 0]
  if {$function in {0 1}} {return 1}
  if {$function eq "" || ![regexp {^[A-Za-z0-9_!'*&+|^()]+$} $function]} {return 0}
  set inputs [lsort -unique [regexp -all -inline {[A-Za-z_][A-Za-z0-9_]*} $function]]
  if {![llength $inputs]} {return 0}
  foreach input $inputs {
    set in [$inst findITerm $input]
    if {$in in {"" NULL} || ![$in isInputSignal]} {return 0}
    if {![ot_ce_constant_net [$in getNet] $seen [expr {$remaining-1}]]} {return 0}
  }
  return 1
}
# Timing startpoint -> constant proof. An output-port startpoint is followed to
# its net driver; an input port is never constant.
proc ot_ce_constant_cone {start} {
  set block [ord::get_db_block]
  if {[sta::object_type $start] eq "Port" || ([sta::object_type $start] eq "Pin" && [$start is_top_level_port])} {
    set port [$block findBTerm [get_full_name $start]]
    if {$port in {"" NULL} || [$port getIoType] ne "OUTPUT"} {return 0}
    return [ot_ce_constant_net [$port getNet] {} 64]
  }
  if {[sta::object_type $start] ne "Pin"} {return 0}
  set inst [$block findInst [get_full_name [$start instance]]]
  if {$inst in {"" NULL}} {return 0}
  set pin [$inst findITerm [get_property $start lib_pin_name]]
  if {$pin in {"" NULL}} {return 0}
  return [ot_ce_constant_iterm $pin {} 64]
}
# Classification is immutable during one ownership validation. Memoize only
# in the caller's local dictionary; no STA object/classification survives it.
proc ot_ce_startpoint_class {start purpose memo_name} {
  upvar 1 $memo_name memo
  set name [get_full_name $start]
  set key [list $purpose [sta::object_type $start] $name]
  if {[dict exists $memo $key]} {return [dict get $memo $key]}
  if {$purpose eq "input" && [llength [get_ports -quiet $name]]} {
    set result [list port $name]
  } elseif {$purpose eq "output" && [sta::object_type $start] eq "Pin" && [$start is_top_level_port]} {
    set result [list top_pin $name]
  } else {
    set result [list cell [get_full_name [get_cells -quiet -of_objects $start]]]
  }
  dict set memo $key $result
  return $result
}
# A multi-root leaf contains independent synchronous datapaths. Domain declarations
# are checked against the real synthesized timing graph, not trusted as metadata.
proc ot_ce_leaf_ownership {inputs outputs} {
  set expected {}
  dict for {domain info} $::ot_ce_domains {lappend expected [dict get $info clock]}
  for {set i 0} {$i < [llength $::ot_ce_ports]} {incr i} {lappend expected ot_entry_$i}
  set actual {}
  foreach c [all_clocks] {lappend actual [get_full_name $c]}
  if {[lsort $actual] ne [lsort $expected]} {error "OT_MULTI_ROOT: undeclared clock alias or relationship"}
  set cells {}; set clocks {}; set crossing_pairs {}; set domain_roots {}
  foreach root $::ot_ce_ports {
    set domain [dict get $::ot_ce_source_domains $root]
    dict set domain_roots $domain $root
    set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $root]]
    foreach pin [all_registers -clock [get_full_name $clock] -clock_pins] {
      set cell [get_full_name [get_cells -of_objects $pin]]
      if {[dict exists $cells $cell]} { error "OT_MULTI_ROOT: duplicate clock ownership $cell" }
      dict set cells $cell $domain
    }
  }
  foreach pin [all_registers -clock_pins] {
    set cell [get_full_name [get_cells -of_objects $pin]]
    if {![dict exists $cells $cell]} { error "OT_MULTI_ROOT: unowned register $cell" }
  }
  set ::ot_ce_register_cells {}
  foreach r [all_registers -cells] {dict set ::ot_ce_register_cells [get_full_name $r] 1}
  set ::ot_ce_const_memo {}
  set startpoint_classes {}
  # OpenSTA's -data_pins population includes asynchronous clear/preset
  # controls. Classify these from the actual loaded Liberty sequential arcs,
  # never from port names or reset_ports. They retain recovery/removal timing;
  # only ordinary synchronous D/control paths require data-domain ownership.
  set async_pins {}
  foreach pin [all_registers -async_pins] {dict set async_pins [get_full_name $pin] 1}
  foreach pin [all_registers -data_pins] {
    if {[dict exists $async_pins [get_full_name $pin]]} continue
    set cell [get_full_name [get_cells -of_objects $pin]]
    set expected [dict get $cells $cell]
    foreach start [get_fanin -flat -startpoints_only -to $pin] {
      lassign [ot_ce_startpoint_class $start input startpoint_classes] source_kind source
      if {$source_kind eq "port"} {
        set name [get_full_name $start]
        if {![dict exists $inputs $name] || [dict get $inputs $name] ne $expected} {
          error "OT_MULTI_ROOT: input $name has wrong domain for $cell"
        }
      } else {
        if {![dict exists $cells $source]} {
          if {[ot_ce_constant_cone $start]} {
            puts "OT_MULTI_ROOT LIBERTY_CONSTANT [get_full_name $start] -> [get_full_name $pin]"
            continue
          }
          error "OT_MULTI_ROOT: unowned data path $source -> $cell"
        }
        set source_domain [dict get $cells $source]
        if {$source_domain ne $expected} {
          if {!$::ot_ce_related_data} {error "OT_MULTI_ROOT: cross-domain data path $source -> $cell requires explicit related profile"}
          dict set crossing_pairs [list $source_domain $expected] 1
        }
      }
    }
  }
  dict for {name domain} $outputs {
    foreach start [get_fanin -flat -startpoints_only -to [get_ports $name]] {
      # A die-strap tie output (contract v1.2 tie_hi/tie_lo), possibly
      # synthesis-buffered, has no clock and no data domain to own; it must be
      # proved constant above. Registers and ports keep their domain checks.
      lassign [ot_ce_startpoint_class $start output startpoint_classes] source_kind source
      if {$source_kind eq "top_pin"} {
        if {[ot_ce_constant_cone $start]} {
          puts "OT_MULTI_ROOT LIBERTY_CONSTANT [get_full_name $start] -> $name"
          continue
        }
        error "OT_MULTI_ROOT: output $name has wrong or unregistered source domain [get_full_name $start]"
      }
      if {![dict exists $cells $source] && [ot_ce_constant_cone $start]} {
        puts "OT_MULTI_ROOT LIBERTY_CONSTANT [get_full_name $start] -> $name"
        continue
      }
      if {![dict exists $cells $source] || [dict get $cells $source] ne $domain} {
        error "OT_MULTI_ROOT: output $name has wrong or unregistered source domain $source"
      }
    }
  }
  dict for {pair unused} $crossing_pairs {
    lassign $pair source_domain target_domain
    set source_root [dict get $domain_roots $source_domain]
    set target_root [dict get $domain_roots $target_domain]
    set from [all_registers -clock ot_entry_[lsearch -exact $::ot_ce_ports $source_root] -clock_pins]
    set to {}
    foreach pin [all_registers -clock ot_entry_[lsearch -exact $::ot_ce_ports $target_root] -data_pins] {
      if {![dict exists $async_pins [get_full_name $pin]]} {lappend to $pin}
    }
    foreach kind {max min} {
      set paths [find_timing_paths -from $from -to $to -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
      if {![llength $paths] && [info exists ::env(OT_HOLD_MM)] && $::env(OT_HOLD_MM) eq "1" &&
          ![info exists ::ot_mm_active]} {
        # Multi-mode route/gate (tools/orfs_hold_mm.tcl): this SDC is being read into mode ss BEFORE any scene is
        # defined, so the unscened default scene has no clocks and no path can be found yet.  The crossing population
        # above is structural (actual fanin) and unchanged; the finite-path proof runs strictly in every single-scene
        # read (non-MM stages, corner_sta / sign-off), which carries the timing claim.
        puts "OT_MULTI_ROOT RELATED_PATH_DEFERRED $source_domain -> $target_domain $kind (multi-mode read before scene definition; strict at sign-off)"
        continue
      }
      if {![llength $paths] || ![ot_ce_finite [get_property [lindex $paths 0] slack]]} {
        error "OT_MULTI_ROOT: related crossing lacks actual finite $kind STA path $source_domain -> $target_domain"
      }
      puts "OT_MULTI_ROOT RELATED_PATH $source_domain -> $target_domain $kind slack=[get_property [lindex $paths 0] slack] (ordinary synchronous timing retained)"
    }
  }
  puts "OT_MULTI_ROOT OWNERSHIP PASS roots=[llength $::ot_ce_cts_roots] registers=[dict size $cells] inputs=[dict size $inputs] outputs=[dict size $outputs] async_control_pins=[dict size $async_pins]"
}
'''


def leaf_body():
    """Extend the proven hard-entry timing algorithm without changing legacy SDC bytes."""
    body = BODY
    substitutions = [
        ('  set found {}\n  foreach cell [get_cells -quiet -hierarchical *] {\n    set master [get_property $cell ref_name]\n    if {![dict exists $::ot_ce_counts $master]} continue\n',
         r'''  set found {}; set clock_cells {}
  # Physical-only taps/endcaps have no Liberty association. The clock corner
  # belongs to actual sequential clock sinks, not every physical instance.
  foreach pin [all_registers -clock_pins] {
    set cell [get_cells -quiet -of_objects $pin]
    if {[llength $cell] != 1 || $cell eq "NULL"} {error "OT_MULTI_ROOT: clock sink lacks one actual sequential cell"}
    dict set clock_cells [get_full_name $cell] $cell
  }
  if {![dict size $clock_cells]} {error "OT_MULTI_ROOT: no actual sequential cells for corner inference"}
  foreach cell [dict values $clock_cells] {
    set master [get_property $cell ref_name]
'''),
        ('    if {![llength $libcells]} { error "OT_ENTRIES: $master has no loaded Liberty association" }\n',
         '    if {![llength $libcells] || "NULL" in $libcells} { error "OT_MULTI_ROOT: actual sequential cell $master has no loaded Liberty association" }\n'),
        ('      if {![regexp -nocase {_(tt|ff|ss)/} $full -> corner]} { error "OT_ENTRIES: unknown actual child Liberty corner $full" }\n',
         '      if {![regexp -nocase {_(tt|ff|ss)/|_(tt|ff|ss)_} $full -> corner alt]} { error "OT_ENTRIES: unknown actual Liberty corner $full" }\n      if {$corner eq ""} {set corner $alt}\n'),
        ('      foreach p [get_ports -quiet $pattern -filter "direction == input"] {\n',
         '      set match [get_ports -quiet $pattern -filter "direction == input"]\n      if {$::ot_ce_leaf_roots && ![llength $match]} {set match [get_ports -quiet [format {%s\\[*\\]} $pattern] -filter "direction == input"]}\n      if {$::ot_ce_leaf_roots && ![llength $match]} {error "OT_MULTI_ROOT: unknown input $pattern"}\n      foreach p $match {\n'),
        ('      foreach p [get_ports -quiet $pattern -filter "direction == output"] {\n',
         '      set match [get_ports -quiet $pattern -filter "direction == output"]\n      if {$::ot_ce_leaf_roots && ![llength $match]} {set match [get_ports -quiet [format {%s\\[*\\]} $pattern] -filter "direction == output"]}\n      if {$::ot_ce_leaf_roots && ![llength $match]} {error "OT_MULTI_ROOT: unknown output $pattern"}\n      foreach p $match {\n'),
        ('  puts "OT_ENTRIES COMP DONE $corner [llength $rows] entries phi=$ref boundary=$lmin..$lmax"\n',
         '  if {$::ot_ce_leaf_roots} { ot_ce_leaf_ownership $covered_in $covered_out }\n  puts "OT_ENTRIES COMP DONE $corner [llength $rows] entries phi=$ref boundary=$lmin..$lmax"\n'),
    ]
    for old, new in substitutions:
        if body.count(old) != 1:
            raise ValueError("clock-entry body changed; revalidate multi-root extension")
        body = body.replace(old, new)
    return LEAF_OWNERSHIP + body


LEAF_BODY = leaf_body()


RULE_ABORT = ('    if {[ot_ce_clock_rule $corner $name [llength $pins] $tree_mean $mean $lo $hi $scope] eq "FAIL"} {\n'
              '      error "OT_HYBRID: glue root $name pin-flop spread [format %.1f [expr {$hi-$lo}]] ps > 80 at $corner '
              '($scope, [llength $boundary] of [llength $pins] sinks)"\n'
              '    }\n')


def landed_body():
    """PL-KIT 10-18: the multi-root leaf body for a LANDED cluster (landed_cluster): hard-child clock pins are sinks of
    their region root, measured at the child's flops (entry-wire arrival + insertion.json boundary min / mean / max of
    the actual corner); every bound child clock pin must be reached from a root (fail closed); a hard child belongs to
    the domain of the root its clock pin sits on.  LEAF_BODY (leaf tiles) is unchanged."""
    body = LEAF_BODY
    child_sink = (
        '      set arrival [ot_ce_clock_wire $pin $clock]\n'
        '      if {[dict exists $::ot_ce_counts $master]} {\n'
        '        # landed cluster: a hard child on its region root, judged at its flops (entry wire + routed child insertion)\n'
        '        set key "$master/[get_property $pin lib_pin_name]"\n'
        '        if {![dict exists $::ot_ce_refs $key]} { error "OT_LANDED: CTS root $name reaches unbound hard-child pin [get_full_name $pin]" }\n'
        '        set cname [get_full_name $cell]\n'
        '        if {[dict exists $::ot_ce_landed_owner $cname] && [dict get $::ot_ce_landed_owner $cname] ne [dict get $::ot_ce_source_domains $name]} {\n'
        '          error "OT_LANDED: hard child $cname clock pins on different region roots"\n'
        '        }\n'
        '        dict set ::ot_ce_landed_owner $cname [dict get $::ot_ce_source_domains $name]\n'
        '        lassign [dict get $::ot_ce_refs $key $corner] clo cmean chi\n'
        '        dict set ot_ce_child_ext [get_full_name $pin] [list [expr {$arrival + $clo}] [expr {$arrival + $chi}]]\n'
        '        puts "OT_LANDED CHILD_SINK $corner $name [get_full_name $pin] wire=$arrival R=$cmean min=[expr {$arrival + $clo}] max=[expr {$arrival + $chi}]"\n'
        '        set arrival [expr {$arrival + $cmean}]\n'
        '        incr ot_ce_landed_hits\n'
        '      }\n')
    substitutions = [
        # hard children are not entries of their own: their clock pins are visited on the region roots below
        ('      if {![dict exists $::ot_ce_refs $key]} continue\n',
         '      if {![dict exists $::ot_ce_refs $key] || $::ot_ce_landed_cluster} continue\n'),
        ('  set boundary_cells {}; set boundary_cells_ready 0\n',
         '  set boundary_cells {}; set boundary_cells_ready 0\n  set ot_ce_landed_hits 0; set ::ot_ce_landed_owner [dict create]\n'),
        # TW-HBM-COLLP 10-19: bound CHECK-ONLY child clock pins (no clk->Q arc, so not in all_registers) are sinks of the
        # region root their net is wired to (ot_ce_net_root_port: structural, mode-independent), measured like the others
        ('    set pins [all_registers -clock [get_full_name $clock] -clock_pins]\n'
         '    if {![llength $pins]} { error "OT_HYBRID: glue root $name has no actual sequential clock sinks" }\n',
         '    set pins [all_registers -clock [get_full_name $clock] -clock_pins]\n'
         '    set ot_ce_pin_seen [dict create]\n'
         '    foreach pin $pins {dict set ot_ce_pin_seen [get_full_name $pin] 1}\n'
         '    foreach cell [get_cells -quiet -hierarchical *] {\n'
         '      set master [get_property $cell ref_name]\n'
         '      if {![dict exists $::ot_ce_counts $master]} continue\n'
         '      foreach pin [get_pins -quiet -of_objects $cell] {\n'
         '        set key "$master/[get_property $pin lib_pin_name]"\n'
         '        if {![dict exists $::ot_ce_refs $key] || [dict exists $ot_ce_pin_seen [get_full_name $pin]]} continue\n'
         '        if {![info exists ::ot_ce_check_only] || ![dict exists $::ot_ce_check_only $key]} continue\n'
         '        if {[ot_ce_net_root_port $pin] ne $name} continue\n'
         '        lappend pins $pin; dict set ot_ce_pin_seen [get_full_name $pin] 1\n'
         '        puts "OT_LANDED CHECK_CLOCK_PIN $name [get_full_name $pin] (timing-check-only child clock pin)"\n'
         '      }\n'
         '    }\n'
         '    if {![llength $pins]} { error "OT_HYBRID: glue root $name has no actual sequential clock sinks" }\n'),
        # a hard child with several clock pins on ONE region root (writer clk_body + clk_bank0-7) is one owner, not a
        # duplicate; pins of one child on different roots still fail ("clock pins on different region roots")
        ('      if {[dict exists $cells $cell]} { error "OT_MULTI_ROOT: duplicate clock ownership $cell" }\n',
         '      if {[dict exists $cells $cell] && ([dict get $cells $cell] ne $domain'
         ' || ![dict exists $::ot_ce_counts [get_property [get_cells -of_objects $pin] ref_name]])} {\n'
         '        error "OT_MULTI_ROOT: duplicate clock ownership $cell"\n'
         '      }\n'),
        ('    set arrivals {}; set measured {}; set total 0.0\n',
         '    set arrivals {}; set measured {}; set total 0.0; set ot_ce_child_ext [dict create]\n'),
        ('      if {[dict exists $::ot_ce_counts $master]} { error "OT_HYBRID: CTS root $name reaches a hard child" }\n'
         '      set arrival [ot_ce_clock_wire $pin $clock]\n', child_sink),
        ('    set mean [expr {$total / [llength $arrivals]}]\n',
         '    set mean [expr {$total / [llength $arrivals]}]\n'
         '    foreach pin $boundary {\n'
         '      if {![dict exists $ot_ce_child_ext [get_full_name $pin]]} continue\n'
         '      lassign [dict get $ot_ce_child_ext [get_full_name $pin]] clo chi\n'
         '      set lo [expr {min($lo, $clo)}]; set hi [expr {max($hi, $chi)}]\n'
         '    }\n'),
        # a landed parent is judged per LINKED child pair at the child flops (pre_route_gate root_child_flops +
        # clock_rule_eval, TT and FF <= 80), not on the whole-root span that mixes landed soft halves and children:
        # the in-flow line is reported, the verdict is the gate's
        (RULE_ABORT,
         '    if {[ot_ce_clock_rule $corner $name [llength $pins] $tree_mean $mean $lo $hi $scope] eq "FAIL"} {\n'
         '      puts "OT_LANDED CLOCK_RULE_SPAN $corner $name: whole-root span over 80 ps; verdict per linked child pair '
         '(pre_route_gate root_child_flops)"\n'
         '    }\n'),
        ('  if {[dict size $seen] != [llength $::ot_ce_ports]} { error "OT_ENTRIES: incomplete actual child/source coverage" }\n',
         '  if {$ot_ce_landed_hits != $::ot_ce_landed_child_pins} { error "OT_LANDED: $ot_ce_landed_hits of $::ot_ce_landed_child_pins'
         ' bound hard-child clock pins reached from the region roots" }\n'
         '  if {[dict size $seen] != [llength $::ot_ce_ports]} { error "OT_ENTRIES: incomplete actual child/source coverage" }\n'),
    ]
    for old, new in substitutions:
        if body.count(old) != 1:
            raise ValueError("multi-root leaf body changed; revalidate landed-cluster extension")
        body = body.replace(old, new)
    return body


# TW-HBM-COLLP 10-19: a hard child's CHECK-ONLY clock pins (setup/hold arcs, no clk->Q in the ETM, e.g. the COLL
# writer's clk_rgx_data0-3 / clk_rgx_ctrl / clk_meta / clk_tkw landing captures) are not register clock pins for
# OpenSTA (all_registers -clock_pins needs a clk->Q arc).  The root that drives such a pin is found STRUCTURALLY: walk
# the pin's net back through single-input standard cells (CTS buffers / inverters) to a top port.  Never ask the
# timing graph (get_property <pin> clocks): its answer depends on the command mode, and the ORFS multi-mode load
# (orfs_hold_mm.tcl read_sdc -mode ss) returns no clocks there (AD-HBM-COLLP lpk4: 47 of 54 although the pins sit on
# ck_wr).
LANDED_ROOT_PROC = r"""proc ot_ce_net_root_port {pin} {
  set net [get_nets -quiet -of_objects $pin]
  for {set i 0} {$i < 256 && [llength $net] == 1} {incr i} {
    set ports [get_ports -quiet -of_objects $net]
    if {[llength $ports] == 1} { return [get_full_name [lindex $ports 0]] }
    if {[llength $ports]} { return "" }
    set drv [get_pins -quiet -of_objects $net -filter "direction == output"]
    if {[llength $drv] != 1} { return "" }
    set cell [get_cells -quiet -of_objects $drv]
    if {[llength $cell] != 1 || [dict exists $::ot_ce_counts [get_property $cell ref_name]]} { return "" }
    set ins [get_pins -quiet -of_objects $cell -filter "direction == input"]
    if {[llength $ins] != 1} { return "" }
    set net [get_nets -quiet -of_objects $ins]
  }
  return ""
}
"""


LANDED_BODY = LANDED_ROOT_PROC + landed_body()


def landed_raw_body(body, cotimed=False):
    """HF-4d 10-19 (coordinator option A): LANDED_BODY for a cluster whose hard child carries raw SRAM clock entries
    (::ot_ce_landed_raw from landed_raw_pins: the leaf's closed record).  all_registers never reaches such a pin (no ETM
    arcs), so after every region root is measured each bound raw pin is visited on the root of its co-timed CTS-root pin
    (h16c ck_pm0/ck_pm1 -> the root of ck_head): effective = entry-wire arrival + the leaf's own pin -> SRAM wire, judged
    against the co-timed pin's effective arrival (wire + routed R boundary mean) = the leaf sign-off phase.  Post-CTS
    (propagated, measured) |skew| > the leaf's sign-off tolerance is an ERROR (fail closed); pre-CTS it is only reported.
    A raw pin reached as a register, an unreached co-timed pin or a raw pin not on that root (no propagated arrival)
    fails.  Landed kits without raw entries keep LANDED_BODY byte-identical.
    ROOT-INF21 10-19, cotimed (multi-root child records only; hybrid kits byte-identical): every OTHER boundary CTS-root
    pin of such a child (::ot_ce_landed_cotimed) is judged the same way against the same ref -- both effective arrivals
    (pin wire + routed boundary mean) from the region-root sink loop -- because the leaf record co-timed every root to
    one phase within the same tolerance."""
    raw_visit = (
        '  # HF-4d raw SRAM clock entries of hard children: co-timed with their CTS-root pin per the leaf closed record\n'
        '  set ot_ce_raw_fail {}\n'
        '  set ot_ce_raw_diag [expr {[info exists ::ot_ref_pre_cts] && $::ot_ref_pre_cts && (![info exists ::ot_ce_require_wire] || !$::ot_ce_require_wire)}]\n'
        '  foreach cell [get_cells -quiet -hierarchical *] {\n'
        '    set master [get_property $cell ref_name]\n'
        '    if {![dict exists $::ot_ce_counts $master]} continue\n'
        '    set cname [get_full_name $cell]\n'
        '    foreach pin [get_pins -quiet -of_objects $cell] {\n'
        '      set key "$master/[get_property $pin lib_pin_name]"\n'
        '      if {![dict exists $::ot_ce_landed_raw $key]} continue\n'
        '      set refpin [dict get $::ot_ce_landed_raw $key ref]; set tol [dict get $::ot_ce_landed_raw $key tol]\n'
        '      if {![dict exists $ot_ce_landed_eff "$cname/$refpin"]} {\n'
        '        error "OT_LANDED: raw child clock pin [get_full_name $pin]: its co-timed pin $cname/$refpin was not reached from a region root"\n'
        '      }\n'
        '      lassign [dict get $ot_ce_landed_eff "$cname/$refpin"] rclock rname reff\n'
        '      # TW-HBM-COLLP net trace (structural, mode-independent): a raw pin wired to another region root fails\n'
        '      set rport [ot_ce_net_root_port $pin]\n'
        '      if {$rport ne "" && $rport ne $rname} {\n'
        '        error "OT_LANDED: raw child clock pin [get_full_name $pin] is wired to region root $rport, its co-timed pin $cname/$refpin to $rname"\n'
        '      }\n'
        '      set wire [ot_ce_clock_wire $pin [get_clocks $rclock]]\n'
        '      lassign [dict get $::ot_ce_refs $key $corner] rlo rmean rhi\n'
        '      set eff [expr {$wire + $rmean}]; set skew [expr {$eff - $reff}]\n'
        '      set verdict [expr {$ot_ce_raw_diag ? "PRE_CTS" : (abs($skew) <= $tol ? "PASS" : "FAIL")}]\n'
        '      puts "OT_LANDED RAW_PIN $corner $rname [get_full_name $pin] wire=$wire R=$rmean eff=$eff co_timed=$cname/$refpin eff_ref=$reff skew=[format %.1f $skew] tol=$tol $verdict"\n'
        '      if {$verdict eq "FAIL"} { lappend ot_ce_raw_fail "[get_full_name $pin] [format %.1f $skew] ps" }\n'
        '      incr ot_ce_landed_hits\n'
        '    }\n'
        '  }\n'
        + (
        '  # ROOT-INF21 multi-root child records: the other boundary CTS-root pins are co-timed with the same ref\n'
        '  if {[info exists ::ot_ce_landed_cotimed]} {\n'
        '    dict for {ckey cinfo} $::ot_ce_landed_cotimed {\n'
        '      lassign [split $ckey /] cmaster cpin\n'
        '      set crefpin [dict get $cinfo ref]; set ctol [dict get $cinfo tol]\n'
        '      foreach cell [get_cells -quiet -hierarchical *] {\n'
        '        if {[get_property $cell ref_name] ne $cmaster} continue\n'
        '        set cname [get_full_name $cell]\n'
        '        if {![dict exists $ot_ce_landed_eff "$cname/$cpin"] || ![dict exists $ot_ce_landed_eff "$cname/$crefpin"]} {\n'
        '          error "OT_LANDED: co-timed child clock pin $cname/$cpin or its ref $cname/$crefpin was not reached from a region root"\n'
        '        }\n'
        '        set ceff [lindex [dict get $ot_ce_landed_eff "$cname/$cpin"] 2]; set creff [lindex [dict get $ot_ce_landed_eff "$cname/$crefpin"] 2]\n'
        '        set skew [expr {$ceff - $creff}]\n'
        '        set verdict [expr {$ot_ce_raw_diag ? "PRE_CTS" : (abs($skew) <= $ctol ? "PASS" : "FAIL")}]\n'
        '        puts "OT_LANDED COTIMED_PIN $corner $cname/$cpin eff=$ceff co_timed=$cname/$crefpin eff_ref=$creff skew=[format %.1f $skew] tol=$ctol $verdict"\n'
        '        if {$verdict eq "FAIL"} { lappend ot_ce_raw_fail "$cname/$cpin [format %.1f $skew] ps" }\n'
        '      }\n'
        '    }\n'
        '  }\n' if cotimed else '') + (
        '  if {[llength $ot_ce_raw_fail]} {\n'
        '    error "OT_LANDED: raw child clock pin arrival vs its co-timed CTS-root pin beyond the leaf sign-off tolerance at $corner: [join $ot_ce_raw_fail {, }]"\n'
        '  }\n'))
    substitutions = [
        # a raw SRAM pin is visited on its co-timed pin's root below, never as a check-only pin
        ('        if {![info exists ::ot_ce_check_only] || ![dict exists $::ot_ce_check_only $key]} continue\n',
         '        if {[dict exists $::ot_ce_landed_raw $key]} continue\n'
         '        if {![info exists ::ot_ce_check_only] || ![dict exists $::ot_ce_check_only $key]} continue\n'),
        ('  set ot_ce_landed_hits 0; set ::ot_ce_landed_owner [dict create]\n',
         '  set ot_ce_landed_hits 0; set ::ot_ce_landed_owner [dict create]; set ot_ce_landed_eff [dict create]\n'),
        ('        if {![dict exists $::ot_ce_refs $key]} { error "OT_LANDED: CTS root $name reaches unbound hard-child pin [get_full_name $pin]" }\n',
         '        if {![dict exists $::ot_ce_refs $key]} { error "OT_LANDED: CTS root $name reaches unbound hard-child pin [get_full_name $pin]" }\n'
         '        if {[dict exists $::ot_ce_landed_raw $key]} { error "OT_LANDED: raw child clock pin [get_full_name $pin] reached as a register (record says no ETM arcs)" }\n'),
        ('        set arrival [expr {$arrival + $cmean}]\n        incr ot_ce_landed_hits\n',
         '        set arrival [expr {$arrival + $cmean}]\n        incr ot_ce_landed_hits\n'
         '        dict set ot_ce_landed_eff "$cname/[get_property $pin lib_pin_name]" [list [get_full_name $clock] $name $arrival]\n'),
        ('  if {$ot_ce_landed_hits != $::ot_ce_landed_child_pins}', raw_visit + '  if {$ot_ce_landed_hits != $::ot_ce_landed_child_pins}'),
    ]
    for old, new in substitutions:
        if body.count(old) != 1:
            raise ValueError("landed body changed; revalidate the raw child clock pin extension")
        body = body.replace(old, new)
    return body


def direct_body(body, direct):
    """Add explicitly bound raw-memory pin references without changing ETM semantics."""
    marker = '  # Each glue root owns a real CTS tree.'
    hook = r'''  foreach row [ot_ce_direct_rows $corner] {
    set name [get_full_name [lindex $row 0]]
    if {[dict exists $seen $name]} {error "OT_DIRECT_MACRO: duplicate hard-source ownership $name"}
    dict set seen $name 1
    lappend rows $row
  }
'''
    if body.count(marker) != 1:
        raise ValueError('clock entry body changed; revalidate direct macro extension')
    body = body.replace(marker, hook + marker)
    # A parent with only direct raw SRAMs has no routed ETM master from which
    # to identify the current scene; use its actual linked SRAM libraries too.
    marker = '    if {![dict exists $::ot_ce_counts $master]} continue'
    if 'proc ot_ce_leaf_ownership ' in body:
        # The native-leaf corner census already covers every actual sequential
        # clock sink, including raw memories; do not narrow it to macro masters.
        if body.count(marker) != 1:
            raise ValueError('native leaf corner body changed; revalidate direct macro extension')
    else:
        if body.count(marker) != 2:
            raise ValueError('clock entry corner body changed; revalidate direct macro extension')
        body = body.replace(marker, '    if {![dict exists $::ot_ce_counts $master] && $master ni $::ot_ce_direct_masters} continue', 1)
    body = body.replace('if {[dict exists $::ot_ce_counts $master]} { error "OT_HYBRID: CTS root',
                        'if {[dict exists $::ot_ce_counts $master] || $master in $::ot_ce_direct_masters} { error "OT_HYBRID: CTS root')
    masters = sorted({e['master'] for e in direct['entries']})
    return ('set ::ot_ce_direct_masters {' + ' '.join(masters) + '}\n'
            + direct['bindings_tcl'] + body)


# Generated clocks retain their actual phase/scenario constraints. This only
# expands physical ownership/census; it creates no timing exceptions.
CLOCK_FAMILY_TCL = (Path(__file__).resolve().parents[2] /
                    "physical/common_flow/clock_family.tcl").read_text()

def _clock_family_body(body):
    for marker in ("  foreach c [get_clocks ot_entry_*] { set_clock_latency -source 0 $c }",
                   "set pins [all_registers -clock [get_full_name $clock] -clock_pins]",
                   "  foreach a [get_clocks ot_entry_*] {\n    foreach b [get_clocks ot_entry_*] {",
                   "proc ot_ce_clock_wire {pin clock} {"):
        if body.count(marker) != 1:
            raise ValueError("clock-entry body changed; revalidate generated-clock family extension")
    body = body.replace("  foreach c [get_clocks ot_entry_*] { set_clock_latency -source 0 $c }",
                        "  foreach c [get_clocks ot_entry_*] { set_clock_latency -source 0 $c }\n  ot_cf_refresh")
    body = body.replace("proc ot_ce_leaf_ownership {inputs outputs} {",
                        "proc ot_ce_leaf_ownership {inputs outputs} {\n  ot_cf_refresh")
    body = body.replace("set pins [all_registers -clock [get_full_name $clock] -clock_pins]",
                        "lassign [ot_cf_pins $clock] pins ot_ce_family_owners")
    body = body.replace("foreach pin [all_registers -clock [get_full_name $clock] -clock_pins] {",
                        "lassign [ot_cf_pins $clock] ot_ce_family_pins ot_ce_family_owners\n    foreach pin $ot_ce_family_pins {")
    body = body.replace("foreach c [all_clocks] {lappend actual [get_full_name $c]}",
                        "foreach c [all_clocks] {if {![$c is_generated]} {lappend actual [get_full_name $c]}}")
    body = body.replace("  foreach a [get_clocks ot_entry_*] {\n    foreach b [get_clocks ot_entry_*] {\n      set an [get_full_name $a]; set bn [get_full_name $b]",
                        "  set ot_ce_family_clocks {}\n  foreach c [all_clocks] {\n    if {[ot_cf_root [get_full_name $c]] in [lmap x [get_clocks ot_entry_*] {get_full_name $x}]} {lappend ot_ce_family_clocks $c}\n  }\n  foreach a $ot_ce_family_clocks {\n    foreach b $ot_ce_family_clocks {\n      set an [ot_cf_root [get_full_name $a]]; set bn [ot_cf_root [get_full_name $b]]")
    body = body.replace("proc ot_ce_clock_wire {pin clock} {",
                        "proc ot_ce_legacy_clock_wire {pin clock} {")
    # Existing ordinary-clock selection/pre-CTS semantics stay unchanged.
    wrapper = r'''
proc ot_ce_clock_wire {pin clock} {
  if {[info exists ::ot_cf_master] && [dict size $::ot_cf_master]} {
    set owners [get_property $pin clocks]
    if {[llength $owners] != 1 || [ot_cf_root [get_full_name $owners]] ne [ot_cf_root [get_full_name $clock]]} {
      error "OT_CLOCK_FAMILY: wrong/ambiguous source ownership [get_full_name $pin]"
    }
    return [ot_cf_wire $pin $owners]
  }
  return [ot_ce_legacy_clock_wire $pin $clock]
}
'''
    return CLOCK_FAMILY_TCL + wrapper + body

BODY = _clock_family_body(BODY)
LEAF_BODY = _clock_family_body(LEAF_BODY)
LANDED_BODY = _clock_family_body(LANDED_BODY)


# S81-FRAME4 10-19: the FORWARDED-CLOCK class of a landed cluster (forwarded_clock_ports).  A forwarded port is a data
# input of the parent SDC (no create_clock: the frame times it as a core-domain input, as the kit always did), so its
# sinks carry DATA arrival tags, never "(clock prop)" ones: the pin arrival is the largest finite max data arrival in the
# current scene.  Within one forwarded port bit the input-delay term is common, so the child-flop spread
# max(arr + R_max) - min(arr + R_min) over its sinks is the forwarded tree's own skew at the child flops.
FORWARDED_PROCS = r"""proc ot_ce_fwd_arrival {pin} {
  set scene [get_property [sta::cmd_scene] name]
  set best ""
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    foreach transition {rise fall} {
      set paths [$vertex path_iterator $transition max]
      while {[$paths has_next]} {
        set path [$paths next]
        set tag [$path tag]
        if {[lindex $tag 1] ne $scene || ![string match *max [lindex $tag 2]]} continue
        set a [sta::time_sta_ui [$path arrival]]
        if {![ot_ce_finite $a]} continue
        if {$best eq "" || $a > $best} {set best $a}
      }
      $paths finish
    }
  }
  return $best
}
proc ot_ce_fwd_domain {port} {
  # a forwarded clock travels with its data: its cells belong to the clock-entry domain that owns the port as an input
  set base $port
  regsub {\[[0-9]+\]$} $port {} base
  dict for {domain info} $::ot_ce_domains {
    foreach p [dict get $info inputs] { if {[string match $p $base] || [string match $p $port]} { return $domain } }
  }
  error "OT_LANDED: forwarded clock port $port is no input of a clock-entry domain"
}
proc ot_ce_forwarded_visit {corner} {
  # every bound hard-child clock pin whose net traces to a forwarded port: one FORWARDED sink (fail closed below)
  set ::ot_ce_fwd_cells [dict create]
  set groups [dict create]; set hits 0
  set judged [expr {!([info exists ::ot_ref_pre_cts] && $::ot_ref_pre_cts) || ([info exists ::ot_ce_require_wire] && $::ot_ce_require_wire)}]
  foreach cell [get_cells -quiet -hierarchical *] {
    set master [get_property $cell ref_name]
    if {![dict exists $::ot_ce_counts $master]} continue
    foreach pin [get_pins -quiet -of_objects $cell] {
      set key "$master/[get_property $pin lib_pin_name]"
      if {![dict exists $::ot_ce_refs $key]} continue
      set port [ot_ce_net_root_port $pin]
      if {$port eq ""} continue
      set base $port
      regsub {\[[0-9]+\]$} $port {} base
      if {[lsearch -exact $::ot_ce_fwd_ports $base] < 0} continue
      set full [get_full_name $pin]
      set arr [ot_ce_fwd_arrival $pin]
      if {$arr eq ""} {
        if {$judged} { error "OT_LANDED: forwarded clock pin $full (port $port) has no measured arrival" }
        set arr 0.0
        puts "OT_LANDED FORWARDED_UNMEASURED $corner $port $full (pre-CTS: wire taken 0)"
      }
      lassign [dict get $::ot_ce_refs $key $corner] clo cmean chi
      set lo [expr {$arr + $clo}]; set hi [expr {$arr + $chi}]
      dict lappend groups $port [list $full $lo $hi]
      dict set ::ot_ce_fwd_cells [get_full_name $cell] $port
      puts "OT_LANDED FORWARDED_SINK $corner $port $full wire=$arr R=$cmean min=$lo max=$hi"
      incr hits
    }
  }
  dict for {port rows} $groups {
    set lo ""; set hi ""
    foreach r $rows {
      lassign $r full a b
      if {$lo eq "" || $a < $lo} {set lo $a}
      if {$hi eq "" || $b > $hi} {set hi $b}
    }
    set spread [expr {$hi - $lo}]
    set verdict [expr {$spread <= 80.0 ? "PASS" : "FAIL"}]
    puts "OT_LANDED FORWARDED_CLOCK $corner $port sinks=[llength $rows] child_flop_spread=[format %.1f $spread] ps (<= 80 at TT and FF) $verdict[expr {$judged ? {} : { (pre-CTS: reported)}}]"
    if {$verdict eq "FAIL" && $judged && $corner in {tt ff}} {
      error "OT_LANDED: forwarded clock $port child-flop spread [format %.1f $spread] ps > 80 at $corner ([llength $rows] sinks)"
    }
  }
  return $hits
}
"""


def forwarded_body(body):
    """The landed body with the forwarded-clock class (forwarded_clock_ports): forwarded sinks are visited after the
    region roots and count toward the landed coverage (a pin reached by neither a region root nor a forwarded port
    still fails "N of M"); their cells are owned by the forwarded port (OT_MULTI_ROOT ownership); spread judged per port
    bit at the child flops (FORWARDED_PROCS)."""
    substitutions = [
        ('  if {$ot_ce_landed_hits != $::ot_ce_landed_child_pins}',
         '  incr ot_ce_landed_hits [ot_ce_forwarded_visit $corner]\n'
         '  if {$ot_ce_landed_hits != $::ot_ce_landed_child_pins}'),
        ('    if {![dict exists $cells $cell]} { error "OT_MULTI_ROOT: unowned register $cell" }\n',
         '    if {![dict exists $cells $cell] && [info exists ::ot_ce_fwd_cells] && [dict exists $::ot_ce_fwd_cells $cell]} {\n'
         '      dict set cells $cell [ot_ce_fwd_domain [dict get $::ot_ce_fwd_cells $cell]]\n'
         '    }\n'
         '    if {![dict exists $cells $cell]} { error "OT_MULTI_ROOT: unowned register $cell" }\n'),
    ]
    for old, new in substitutions:
        if body.count(old) != 1:
            raise ValueError("landed body changed; revalidate the forwarded-clock extension")
        body = body.replace(old, new)
    return FORWARDED_PROCS + body


FORWARDED_SOFT_PROCS = r"""
proc ot_ce_forwarded_soft_visit {corner groups_name} {
  upvar 1 $groups_name groups
  set seen [dict create]
  foreach pin [all_registers -clock_pins] {
    set cell [get_full_name [get_cells -of_objects $pin]]
    if {[dict exists $::ot_ce_counts [get_property [get_cells -of_objects $pin] ref_name]]} continue
    set port [ot_ce_net_root_port $pin]
    if {![dict exists $::ot_ce_fwd_soft $port]} continue
    set info [dict get $::ot_ce_fwd_soft $port]
    if {[lsearch -exact [dict get $info cells] $cell] < 0} {
      error "OT_FORWARDED_SOFT: undeclared register $cell on $port"
    }
    if {[dict exists $seen $cell]} {error "OT_FORWARDED_SOFT: duplicate clock pin $cell"}
    dict set seen $cell 1
    set clock [get_clocks [dict get $info clock]]
    if {[llength $clock] != 1} {error "OT_FORWARDED_SOFT: missing clock $port"}
    set actual {}
    foreach p [all_registers -clock [get_full_name $clock] -clock_pins] {lappend actual [get_full_name $p]}
    if {[get_full_name $pin] ni $actual} {error "OT_FORWARDED_SOFT: actual clock mismatch $cell $port"}
    set a [ot_ce_clock_wire $pin $clock]
    dict lappend groups $port [list [get_full_name $pin] $a $a]
    dict set ::ot_ce_fwd_cells $cell $port
    puts "OT_LANDED FORWARDED_SOFT_SINK $corner $port [get_full_name $pin] wire=$a"
  }
  dict for {port info} $::ot_ce_fwd_soft {
    foreach cell [dict get $info cells] {
      if {![dict exists $seen $cell]} {error "OT_FORWARDED_SOFT: missing or wrong-source register $cell ($port)"}
    }
  }
}
"""


def forwarded_soft_body(body):
    substitutions = [
        # Only explicit real-clock ports have propagated clock tags. Their hard
        # and soft sinks must use the same phase-normalized clock metric. The
        # legacy data-only forwarded class keeps its existing arrival query.
        ('      set arr [ot_ce_fwd_arrival $pin]',
         '      if {[dict exists $::ot_ce_fwd_soft $port]} {\n'
         '        set info [dict get $::ot_ce_fwd_soft $port]\n'
         '        set clock [get_clocks [dict get $info clock]]\n'
         '        if {[llength $clock] != 1} {error "OT_FORWARDED_SOFT: missing clock $port"}\n'
         '        set arr [ot_ce_clock_wire $pin $clock]\n'
         '        puts "OT_FORWARDED_SOFT HARD_CLOCK_BASIS $corner $port $full clock=[get_full_name $clock] metric=phase_normalized_clock wire=$arr"\n'
         '      } else {\n'
         '        set arr [ot_ce_fwd_arrival $pin]\n'
         '      }'),
        ('  set_propagated_clock [get_clocks ot_entry_*]',
         '  set_propagated_clock [get_clocks ot_entry_*]\n  set_propagated_clock [get_clocks ot_forwarded_*]'),
        ('  foreach c [all_clocks] {if {![$c is_generated]} {lappend actual [get_full_name $c]}}',
         '  dict for {port info} $::ot_ce_fwd_soft {lappend expected [dict get $info clock]}\n'
         '  foreach c [all_clocks] {if {![$c is_generated]} {lappend actual [get_full_name $c]}}'),
        ('  dict for {port rows} $groups {',
         '  ot_ce_forwarded_soft_visit $corner groups\n  dict for {port rows} $groups {'),
        ('        if {$n in $::ot_ce_ports} continue',
         '        if {$n in $::ot_ce_ports || [dict exists $::ot_ce_fwd_soft $n]} continue'),
    ]
    for old, new in substitutions:
        if body.count(old) != 1:
            raise ValueError('forwarded soft clock body changed; revalidate extension')
        body = body.replace(old, new)
    return FORWARDED_SOFT_PROCS + body


# STW-S81c-COLLA2 10-22 (STEWARD-S81c decision (A), seq (B) parents): a landed cluster may DECLARE closed hard children
# that own clock pins on SEVERAL region roots (the seq (B) landing bands: lk+sq / sq+vc).  Opt-in spec key
# "multi_root_children": [{"inst": <child inst>, "job": <its CLOSED daemon job>}]; absent = byte-identical SDC.  Only the
# landed_body "one hard child = one region root" ownership assertion is lifted for the declared instances; every pin is
# still a sink of the root it is wired to, judged at ITS OWN child insertion (refs <master>/<pin>, per corner), and the
# per-root 80 ps TT+FF pin-flop spread / neighbour-matched boundary rules are unchanged.  A declared child must be a
# CLOSED record (results/closure_loop/<job>/verdict.json status CLOSED) whose views record is this child's view dir and
# whose routed sign-off SDC names exactly the child's measured clock pins as its CTS roots (>= 2): no stand-ins.
MULTI_ROOT_OWNER = ('if {[dict exists $::ot_ce_landed_owner $cname] && [dict get $::ot_ce_landed_owner $cname] ne '
                    '[dict get $::ot_ce_source_domains $name]} {')


def multi_root_children(spec, root):
    decl = spec.get("multi_root_children")
    if decl is None:
        return []
    if not landed_cluster(spec):
        raise ValueError("multi_root_children: only a landed cluster (kind cluster + multiple_cts_roots) declares them")
    if not isinstance(decl, list) or not decl:
        raise ValueError("multi_root_children: a nonempty list of {inst, job}")
    kids = {c.get("inst"): c for c in spec.get("children", [])}
    out = []
    for d in decl:
        if not isinstance(d, dict) or set(d) != {"inst", "job"} or not all(isinstance(d[k], str) and d[k] for k in d):
            raise ValueError(f"multi_root_children: entry {d!r} must be exactly {{inst, job}}")
        inst, job = d["inst"], d["job"]
        child = kids.get(inst)
        if child is None or int(child.get("count", 1)) != 1 or inst in out:
            raise ValueError(f"multi_root_children: {inst} is not one unique hard child of this parent")
        view = Path(root) / child["view"]
        where = f"multi_root_children {inst} ({child['view']})"
        cm = json.loads((view / "insertion.json").read_text()).get("clock_measurements") or {}
        if len(cm) < 2:
            raise ValueError(f"{where}: fewer than two measured clock pins; declare only multi-root children")
        try:
            verdict = json.loads((Path(root) / "results/closure_loop" / job / "verdict.json").read_text())
        except (OSError, ValueError) as e:
            raise ValueError(f"{where}: CLOSED record of {job} unreadable ({e})")
        if verdict.get("status") != "CLOSED" or verdict.get("job") != job:
            raise ValueError(f"{where}: {job} is not a CLOSED record")
        recs = (verdict.get("job_spec") or {}).get("record") or []
        views = [r.get("to") for r in recs if isinstance(r, dict) and str(r.get("from", "")).endswith("/record/views")]
        routes = [r.get("to") for r in recs if isinstance(r, dict) and str(r.get("from", "")).endswith("/record/route")]
        if views != [str(Path(child["view"]).parent)]:
            raise ValueError(f"{where}: {job} record views {views} are not this child's view dir")
        if len(routes) != 1:
            raise ValueError(f"{where}: {job} names no unique record route directory")
        try:
            sdc = (Path(root) / routes[0] / "signoff.sdc").read_text()
        except OSError as e:
            raise ValueError(f"{where}: record sign-off SDC missing ({e})")
        if sorted(_tcl_words(sdc, "ot_ce_cts_roots")) != sorted(cm):
            raise ValueError(f"{where}: record CTS roots {_tcl_words(sdc, 'ot_ce_cts_roots')} differ from the measured "
                             f"clock pins {sorted(cm)}")
        out.append(inst)
    return out


# STW-S81c-COLLA3 10-22 (seq b1m/b1f2 gate "OT_LANDED: 11 of 7 bound hard-child clock pins reached"): OpenSTA's
# all_registers -clock <root> -clock_pins returns EVERY clock pin of a multi-root child's ETM for each of its roots
# (u_blk/ck_lk and u_blk/ck_sq under both ck_lk and ck_sq), so each band pin was measured and counted on both roots.  A
# declared multi-root child's pin is a sink ONLY of the root its net is structurally wired to (ot_ce_net_root_port, the
# same walk the check-only pins use); the other roots drop it from their sink list BEFORE measuring (a `continue` in
# the measure loop left it in $pins and the boundary pass then missed its arrival: b1m gate 14:30 'key "u_blk/ck_sq" not
# known in dictionary').  Only multi_root_children instances are filtered.
MULTI_ROOT_SINK = '    set ot_ce_pin_seen [dict create]\n'
MULTI_ROOT_FILTER = ('    set ot_ce_mr_keep {}\n'
                     '    foreach pin $pins {\n'
                     '      if {[lsearch -exact $::ot_ce_multi_root_children [get_full_name [get_cells -of_objects $pin]]] >= 0'
                     ' && [ot_ce_net_root_port $pin] ne $name} continue\n'
                     '      lappend ot_ce_mr_keep $pin\n'
                     '    }\n'
                     '    set pins $ot_ce_mr_keep\n')


# STW-S81c-COLLA3 10-22 rev3 (b1f2 regate 14:55 'OT_MULTI_ROOT: duplicate clock ownership u_blk'): the leaf ownership
# proof (ot_ce_leaf_ownership) keys every register CELL to one domain.  A declared multi-root child is one cell whose ETM
# clock pins sit on several region roots, so it owns the SET of those domains: a data/IO path to or from it is in-domain
# when the domain sets meet (each pin's own timing stays ordinary STA on its own root, and the child's record closed it).
# Every other cell keeps the single-domain rules; only multi_root_children instances get a set.
MULTI_ROOT_LEAF_SUBS = [
    ("proc ot_ce_leaf_ownership {inputs outputs} {\n",
     "proc ot_ce_mr_doms {mrd cells c} {\n"
     "  if {[dict exists $mrd $c]} {return [lsort -unique [dict get $mrd $c]]}\n"
     "  return [list [dict get $cells $c]]\n"
     "}\n"
     "proc ot_ce_mr_meet {la lb} {foreach x $la {if {[lsearch -exact $lb $x] >= 0} {return 1}}; return 0}\n"
     "proc ot_ce_leaf_ownership {inputs outputs} {\n"),
    ("  set cells {}; set clocks {}; set crossing_pairs {}; set domain_roots {}\n",
     "  set cells {}; set clocks {}; set crossing_pairs {}; set domain_roots {}\n  set ot_ce_mrd {}\n"),
    ('      if {[dict exists $cells $cell] && ([dict get $cells $cell] ne $domain || ',
     '      if {[lsearch -exact $::ot_ce_multi_root_children $cell] >= 0} {\n'
     '        if {[ot_ce_net_root_port $pin] eq $root} {\n'
     '          dict lappend ot_ce_mrd $cell $domain\n'
     '          if {![dict exists $cells $cell]} {dict set cells $cell $domain}\n'
     '        }\n'
     '        continue\n'
     '      }\n'
     '      if {[dict exists $cells $cell] && ([dict get $cells $cell] ne $domain || '),
    ("        if {![dict exists $inputs $name] || [dict get $inputs $name] ne $expected} {\n",
     "        if {![dict exists $inputs $name] || ([dict get $inputs $name] ne $expected && "
     "![ot_ce_mr_meet [list [dict get $inputs $name]] [ot_ce_mr_doms $ot_ce_mrd $cells $cell]])} {\n"),
    ("        if {$source_domain ne $expected} {\n",
     "        if {$source_domain ne $expected && "
     "![ot_ce_mr_meet [ot_ce_mr_doms $ot_ce_mrd $cells $source] [ot_ce_mr_doms $ot_ce_mrd $cells $cell]]} {\n"),
    ("      if {![dict exists $cells $source] || [dict get $cells $source] ne $domain} {\n",
     "      if {![dict exists $cells $source] || ([dict get $cells $source] ne $domain && "
     "![ot_ce_mr_meet [ot_ce_mr_doms $ot_ce_mrd $cells $source] [list $domain]])} {\n"),
]


def multi_root_body(body):
    if body.count(MULTI_ROOT_OWNER) != 1 or body.count(MULTI_ROOT_SINK) != 1:
        raise ValueError("landed body changed; revalidate multi_root_children")
    body = body.replace(MULTI_ROOT_SINK, MULTI_ROOT_FILTER + MULTI_ROOT_SINK)
    if 'proc ot_ce_leaf_ownership {inputs outputs} {' in body:
        for a, b in MULTI_ROOT_LEAF_SUBS:
            if body.count(a) != 1:
                raise ValueError("leaf ownership body changed; revalidate multi_root_children")
            body = body.replace(a, b)
    return body.replace(MULTI_ROOT_OWNER, MULTI_ROOT_OWNER[:-3] +
                        ' && [lsearch -exact $::ot_ce_multi_root_children $cname] < 0} {')
