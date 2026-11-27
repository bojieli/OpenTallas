#!/usr/bin/env python3
"""S81-COLGEN-1 11-14 (FABLE-TYPES-S81-COL C2): per-region replication of a reset / flush fan-out driver in a bound type.

Why: in col_h9_r2 one register (`u_d7_6_Y`, last stage of a 7-stage 1-bit ot_dp_dly, 114 loads over the whole partition)
launches the flush / reset of every core in ONE cycle: worst setup endpoint u_e13e.u_view.u_c/rst_n_pin, GRT -360 ps.

What: plan `partition_types[T].reset_replicate` = [{"driver": "u_d7_6_Y"            exact bound instance name, or
                                                    "driver_re": "u_d\\d+_6_Y",      fullmatch regex,
                                                    "region_re": "^u_(.*?)(?:_\\d+|_sk)?$",   optional, group 1 = region
                                                    "grid_um": 300,                  optional, see below
                                                    "optional": true,                a type without the driver is a no-op
                                                    "min_loads": 20,                 drivers with fewer loads are left alone
                                                    "copy_depth": 3,                 optional, FABLE-DIE-S81 11-16, see below
                                                    "form": "rsync",                 optional, KV-D23-REACH 11-18, see below
                                                    "tail_clear": "sync"}]           optional, rsync form only, see below
The driver `ot_dp_dly #(.W(1), .D(n)) u_x (.clk, .d(S), .q(x))` becomes

    ot_dp_dly #(.W(1), .D(n-1)) u_x (.clk, .d(S), .q(x))          common part (absent when n == 1: S feeds the copies)
    ot_dp_rrelay u_x_r<k> (.clk(clk), .d(x[0] | S), .q(x_r<k>))   one kept flop per region (keep_hierarchy: no opt_merge)

and every load of x is re-pointed to the copy of ITS region.  Total stages from S to every load stay n: LATENCY IS EQUAL
(checked here, again by bind_verify's transport model: ot_dp_rrelay counts 1).  A load outside any instance (an `assign`)
gets the region "rest".  Region of a sink instance: with grid_um and a position for the instance (hard core origin from the
plan, `positions`) the grid cell "g<ix>_<iy>" = core-tap neighbourhood; else the regex group (default: the instance name
without its trailing relay index _<n> / _sk, so the legs u_y_rt_24a_0.._5 of one relay group share one copy).
copy_depth k > 1 (FABLE-DIE-S81 11-16, col reset-copy class: the common flop -> region copy hop was 780..1,246 um in ONE
cycle, -100..-151 ps routed on col_h9_r2): each region gets a private CHAIN of k kept flops u_x_r<i>_s0 .. _s<k-2>, u_x_r<i>
taken from the driver's own depth (common part D(n-k); k is capped at n-1 so one common stage stays), so the way from the
common flop to the loads of a region is k + 1 hops instead of 2.  Total stages stay n: 0 added cycles, same LATCHECK.  The
chain flops are 2-pin nets end to end, so placement spreads them along the way (no site needed, works for regions
without a plan position).  Absent or 1 = one copy per region, byte-identical to before.
Reset spine landing driver (KV-D23-REACH 11-18, kv3_pv_v12: u_rs_ri_pv_u_g0_j_rst_n -> the rst_n pins of 16 kv3_pv_pair
cores 2.8 mm apart in ONE hop, -959 ps): with "form": "rsync" in the row the
driver is `ot_dp_rsync #(.W(1), .S(n)) u_rs_x (.clk, .a(A), .q(x))` (absent = the ot_dp_dly form above) and becomes

    ot_dp_rsync #(.W(1), .S(n-k)) u_rs_x (.clk, .a(A), .q(x))                the synchroniser, never copied (n - k >= 2)
    ot_dp_rtail #(.D(k)) u_rs_x_r<i> (.clk, .a(A), .d(x[0]), .q(x_r<i>))     per region: k kept relay stages, async clear by A

k = copy_depth capped at n - 2: only the stages AFTER the two synchroniser flops are taken, so with S = 2 (the default
landing) the driver is left unchanged and the row says so; the stages come from asbuilt.reset_spines[].sink_stages
(bind.py, per sink type), which is the only latency change (reset release + k clocks; assert stays asynchronous).  The
n-stage chain A -> load is the same function as the single ot_dp_rsync #(.S(n)) (every stage cleared by A, shifted on clk).
"tail_clear": "sync" (FABLE-FIX-KV-PV 11-20, COORD-approved; absent = "async", byte-identical): the copies are NOT cleared by
the spine: `.a(1'b1)`, so each copy is a plain kept k-stage shift register of the synchroniser output x.  Why: with .a(A) the
spine net runs from the type's reset port to the async clear pins of every copy across the type, a timed recovery path in
ONE cycle (owner reset rule: only the die root synchroniser is exempt); kv3_pv_v8 D25e kits: port ri_pv_u_g0_j_rst_n
(vclk input 341 ps) -> 20 copies over ~1 ns of buffers, recovery TT -255 ps.  Effect: RELEASE is on the same clock edge as
before at every load (x releases after n - k edges, then k shifts: the copies had D = x = 0 at every edge before that);
ASSERT reaches the loads k clocks after the spine (x clears asynchronously, then k shifts), the same k at every region, so
all copies assert on the same edge.  Needs the clock running for >= k cycles while the spine is held (boot holds rst_n
>= 64 clk).  Only the near-port synchroniser keeps the spine on its clear pins.
"tail_clear": "sync_output" takes asynchronous clear from the common synchroniser Q. Q asserts asynchronously and
already supplies the relay D. Its release after the common stages keeps the copies' first high sample and total release
edge unchanged. The raw input serves only the common synchroniser. Qualify its Q-to-clear recovery and fanout as
internal timing paths when placing this form.
Each copy line carries the tail-copy marker `// landing pad tail copy for core <region>:` so the siting hook
(gen_phys.tail_copy_place / tail_copy_anchor.tcl) lists it; use region_re "^(.*)$" for one copy per consumer instance.
With "lockup_regions", a generated NK latch on the reset load belongs to the hard core wired to its Q.
An unresolved or shared latch keeps a common copy. The tail siting hook follows these latches to their core pins.
W must be 1 (a reset / flush level).  Pure text transform of the module `emit_type` returns; nothing happens unless the plan
type carries the key (absent = byte-identical).
usage: reset_replicate.py BOUND.sv SPEC.json [--positions POS.json] [-o OUT.sv]   (smoke / kit use)
       reset_replicate.py plan PLAN.json OUT.json TYPE_RE --driver-re RE [--grid-um N] [--region-re RE] [--optional]
           (writes the plan key partition_types[T].reset_replicate on every type matching TYPE_RE)
"""
import json
import re
import sys

DLY = re.compile(r"^(?P<ind>\s*)ot_dp_dly\s*#\(\s*\.W\((?P<W>\d+)\)\s*,\s*\.D\((?P<D>\d+)\)\s*\)\s+(?P<inst>\S+)\s*"
                 r"\(\s*\.clk\((?P<clk>[^)]*)\)\s*,\s*\.d\((?P<d>.*)\)\s*,\s*\.q\((?P<q>\w+)\)\s*\)\s*;(?P<tail>.*)$")
RSY = re.compile(r"^(?P<ind>\s*)ot_dp_rsync\s*#\(\s*\.W\((?P<W>\d+)\)\s*,\s*\.S\((?P<D>\d+)\)\s*\)\s+(?P<inst>\S+)\s*"
                 r"\(\s*\.clk\((?P<clk>[^)]*)\)\s*,\s*\.a\((?P<d>.*)\)\s*,\s*\.q\((?P<q>\w+)\)\s*\)\s*;(?P<tail>.*)$")
HDR = re.compile(r"^\s*(?P<mod>[A-Za-z_]\w*)\s*(?:#\(.*\))?\s+(?P<inst>\\?[\w$]+)\s*\(\s*$")
NK_LOCKUP = re.compile(r"^\s*ot_dp_lk\s*#\(\.W\(\d+\)\)\s+u_lk_nk_\w+\s*"
                       r"\(\.clk\([^()]*\),\s*\.d\([^()]*\),\s*\.q\((\w+)\)\);")
CORE_PORT = re.compile(r"^\s*\.\w+\((.*?)\)[,;]?\s*(?://.*)?$")
ASSIGN = re.compile(r"^\s*assign\s+(?P<lhs>\w+)\s*=\s*(?P<rhs>.*?)\s*;\s*(?://.*)?$")
DEFAULT_REGION_RE = r"^(.*?)(?:_\d+|_sk)?$"
CELL = "ot_dp_rrelay"
TAIL = "ot_dp_rtail"
TAIL_CELL = """// ot_dp_rtail (KV-D23-REACH): D post-synchroniser relay stages of a reset spine landing, one instance per consumer region.
// Every stage is cleared asynchronously by the spine (a), like the stages of ot_dp_rsync, and released one clock after
// the stage before it; kept, so the per-region copies are not merged back into one flop.
module ot_dp_rtail #(parameter integer D = 1) (
    input  wire clk,
    input  wire a,
    input  wire d,
    output wire q
);
    (* keep *) reg [D-1:0] r;
    integer i;
    always @(posedge clk or negedge a)
        if (!a) r <= {D{1'b0}};
        else begin
            r[0] <= d;
            for (i = 1; i < D; i = i + 1) r[i] <= r[i-1];
        end
    assign q = r[D-1];
endmodule
"""


class ReplicateError(ValueError):
    pass


def _sid(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def _region_of(inst, spec, positions):
    grid = spec.get("grid_um")
    if grid and positions and inst in positions:
        x, y = positions[inst]
        return f"g{int(x // grid)}_{int(y // grid)}"
    m = re.match(spec.get("region_re") or DEFAULT_REGION_RE, inst)
    if not m:
        raise ReplicateError(f"region_re {spec.get('region_re')!r} does not match sink instance {inst}")
    return _sid(m.group(1 if m.groups() else 0))


def apply(text, specs, positions=None):
    """text of one bound module -> (new text, [report row per replicated driver]).  Raises ReplicateError."""
    lines = text.split("\n")
    report = []
    for spec in specs:
        if spec.get("form") == "kreg_branch":
            import kreg_reset_branch

            try:
                updated, row = kreg_reset_branch.apply("\n".join(lines), spec)
            except (KeyError, TypeError, ValueError) as exc:
                raise ReplicateError(str(exc)) from exc
            lines = updated.split("\n")
            report.append(row)
            continue
        drv, drv_re = spec.get("driver"), spec.get("driver_re")
        if spec.get("form") not in (None, "rsync"):
            raise ReplicateError(f"reset_replicate form {spec.get('form')!r}: expected \"rsync\" or no form")
        tail_clear = spec.get("tail_clear")
        if tail_clear not in (None, "async", "sync", "sync_output"):
            raise ReplicateError(f"reset_replicate tail_clear {tail_clear!r}: expected async, sync or sync_output")
        if tail_clear in ("sync", "sync_output") and spec.get("form") != "rsync":
            raise ReplicateError(f"reset_replicate tail_clear {tail_clear} needs form rsync")
        if not drv and not drv_re:
            raise ReplicateError("reset_replicate entry needs driver or driver_re")
        hits = []
        for i, ln in enumerate(lines):
            m = RSY.match(ln) if spec.get("form") == "rsync" else DLY.match(ln)
            if m and (m["inst"] == drv if drv else re.fullmatch(drv_re, m["inst"])):
                hits.append((i, m))
        if not hits and spec.get("optional"):
            report.append(dict(driver=drv or drv_re, copies=0, note="driver absent in this type (optional)"))
            continue
        if not hits:
            raise ReplicateError(f"reset_replicate driver {drv or drv_re!r}: no "
                                 f"{'ot_dp_rsync' if spec.get('form') == 'rsync' else 'ot_dp_dly'} instance of that name")
        for i, m in hits:
            lines, row = _one(lines, i, m, spec, positions)
            report.append(row)
    return "\n".join(lines), report


def _one(lines, di, m, spec, positions):
    W, D, inst, q, dexpr, clk = int(m["W"]), int(m["D"]), m["inst"], m["q"], m["d"], m["clk"].strip()
    rsync = spec.get("form") == "rsync"
    if W != 1:
        raise ReplicateError(f"{inst}: W={W}; only a 1-bit reset / flush level is replicated")
    use = re.compile(r"\b" + re.escape(q) + r"\b")
    decl = re.compile(r"^\s*wire\s*(?:\[[^\]]*\])?\s*" + re.escape(q) + r"\s*;")
    di_decl, cur, encl = None, None, {}
    for i, ln in enumerate(lines):
        h = HDR.match(ln)
        if h and not ln.lstrip().startswith(("assign", "wire", "//", "ot_dp_")):
            cur = h["inst"]
        elif ln.strip().startswith(");"):
            cur = None
        encl[i] = None if ln.lstrip().startswith("assign") else cur
        if i != di and decl.match(ln):
            di_decl = i
    if rsync and spec.get("lockup_regions") and positions:
        lockups = {match[1]: i for i, line in enumerate(lines) if (match := NK_LOCKUP.match(line))}
        core_loads = {}
        for i, line in enumerate(lines):
            port, assign = CORE_PORT.match(line), ASSIGN.match(line)
            if port or assign:
                expression = port[1] if port else assign["rhs"]
                for signal in re.findall(r"\b\w+\b", expression):
                    if signal in lockups:
                        core_loads.setdefault(signal, set()).add(encl[i])
        for signal, i in lockups.items():
            cores = core_loads.get(signal, set())
            encl[i] = next(iter(cores)) if len(cores) == 1 and cores <= positions.keys() else None
    orig = list(lines)
    uses = [i for i, ln in enumerate(orig) if i not in (di, di_decl) and use.search(ln)]
    if not uses:
        raise ReplicateError(f"{inst}: q wire {q} has no load")
    if len(uses) < int(spec.get("min_loads", 0)):        # a low-fanout driver of the same name pattern is left alone
        return lines, dict(driver=inst, depth=D, regions=0, copies=0, loads=len(uses), note=f"{len(uses)} load(s) < min_loads")
    wdecl = {}                                          # wire -> '[n:0]' of its declaration

    def width(x):
        if x not in wdecl:
            wdecl[x] = next((mm["w"] or "" for ln in orig for mm in [re.match(r"^\s*wire\s*(?P<w>\[[^\]]*\])?\s*" + re.escape(x) + r"\s*;", ln)] if mm), "")
        return wdecl[x]

    def loads(x, skip):
        xu = re.compile(r"\b" + re.escape(x) + r"\b")
        return [j for j, ln in enumerate(orig) if j != skip and j != di and xu.search(ln)
                and not re.match(r"^\s*wire\s*(?:\[[^\]]*\])?\s*" + re.escape(x) + r"\s*;", ln)]

    memo = {}

    def regs(x, skip, stack=()):
        """regions an assign-defined wire x reaches (transitively through further assigns); 'rest' = a non-instance load"""
        if x in memo:
            return memo[x]
        res = set()
        for j in loads(x, skip):
            am = ASSIGN.match(orig[j])
            if am and am["lhs"] != x and am["lhs"] not in stack:
                res |= regs(am["lhs"], j, stack + (x,))
            elif am:
                res.add("rest")
            else:
                res.add("rest" if encl[j] is None else _region_of(encl[j], spec, positions))
        memo[x] = res
        return res

    plain, top = {}, []                                 # region -> [plain load line]; top-level assign loads of q
    for i in uses:
        am = ASSIGN.match(orig[i])
        if am:
            top.append((i, am["lhs"]))
        else:
            plain.setdefault("rest" if encl[i] is None else _region_of(encl[i], spec, positions), []).append(i)
    allr = set(plain)
    dead = []
    for i, x in top:
        rs = regs(x, i)
        if not rs:
            dead.append(i)
        allr |= rs
    if len(allr) < 2:
        return lines, dict(driver=inst, depth=D, regions=len(allr), copies=0, loads=len(uses), note="one region: unchanged")
    names = {r: f"{inst}_r{k}" for k, r in enumerate(sorted(allr))}
    wire = {r: (names[r].replace("u_", "", 1) if names[r].startswith("u_") else names[r]) for r in names}
    src = f"{q}[0]" if D > 1 else dexpr
    kk = int(1 if spec.get("copy_depth") is None else spec["copy_depth"])           # FABLE-DIE-S81: stages of each region's private copy chain
    if kk < 1:
        raise ReplicateError(f"{inst}: copy_depth {kk} < 1")
    if rsync and D - 2 < 1:
        # the two stages are the synchroniser: nothing to take a copy from (stages come from reset_spines[].sink_stages)
        return lines, dict(driver=inst, form="rsync", depth=D, regions=len(allr), copies=0, loads=len(uses),
                           note="S = 2: no post-sync relay stage, unchanged")
    kk = min(kk, D - 2) if rsync else max(1, min(kk, D - 1))   # keep one common stage (D == 1: single copy, S feeds the copies)
    if rsync:
        src = f"{q}[0]"
    new, leaf, made, blank = [], {r: 0 for r in allr}, set(), set()

    def clone(x, r, xr, skip):
        """wire x is replaced by xr for region r: re-point its instance loads of r and clone its assign loads that reach r"""
        xu = re.compile(r"\b" + re.escape(x) + r"\b")
        for j in loads(x, skip):
            am = ASSIGN.match(orig[j])
            if am and am["lhs"] != x:
                y = am["lhs"]
                if r in regs(y, j):
                    yr = f"{y}_{wire[r]}"
                    if (y, r) not in made:
                        made.add((y, r))
                        new.append(f"    wire {width(y) + ' ' if width(y) else ''}{yr};")
                        new.append(f"    assign {yr} = {xu.sub(xr, am['rhs'])};  // S81-COLGEN-1 C2: {y} for region {r}")
                        clone(y, r, yr, j)
                    if "rest" not in regs(y, j):
                        blank.add(j)
            elif not am and encl[j] is not None and _region_of(encl[j], spec, positions) == r:
                lines[j] = xu.sub(xr, lines[j])
                leaf[r] += 1

    for r, js in plain.items():
        for j in js:
            lines[j] = use.sub(wire[r], lines[j])
        leaf[r] += len(js)
    for i, x in top:
        rs = regs(x, i)
        if not rs:
            blank.add(i)
            continue
        for r in sorted(rs):
            if r == "rest":
                lines[i] = use.sub(wire["rest"], orig[i])
                continue
            xr = f"{x}_{wire[r]}"
            new.append(f"    wire {width(x) + ' ' if width(x) else ''}{xr};")
            new.append(f"    assign {xr} = {use.sub(wire[r], ASSIGN.match(orig[i])['rhs'])};  // S81-COLGEN-1 C2: {x} for region {r}")
            clone(x, r, xr, i)
        if "rest" not in rs:
            blank.add(i)
    for j in blank:
        lines[j] = ""
    tail_clear = spec.get("tail_clear")
    cells = []
    for r in sorted(allr):
        cells.append(f"    wire [0:0] {wire[r]};")
        prev = src
        if rsync:
            sync_tail = tail_clear == "sync"
            aexpr = {"sync": "1'b1", "sync_output": src}.get(tail_clear, dexpr)
            cells.append(f"    {TAIL} #(.D({kk})) {names[r]} (.clk({clk}), .a({aexpr}), .d({prev}), "
                         f".q({wire[r]}[0]));  "
                         f"// landing pad tail copy for core {r}: reset spine relay ({leaf[r]} load(s)); {D} stage(s) total"
                         + (f"; synchronous copy: assert +{kk} clk, release unchanged" if sync_tail else ""))
            continue
        for j in range(kk - 1):
            cells.append(f"    wire {wire[r]}_s{j};")
            cells.append(f"    {CELL} {names[r]}_s{j} (.clk({clk}), .d({prev}), .q({wire[r]}_s{j}));  // FABLE-DIE-S81: chain"
                         f" stage {j + 1} of {kk}, region {r}")
            prev = f"{wire[r]}_s{j}"
        cells.append(f"    {CELL} {names[r]} (.clk({clk}), .d({prev}), .q({wire[r]}[0]));  // S81-COLGEN-1 C2: region {r}"
                     f" ({leaf[r]} load(s)); {D} stage(s) total")
    new = cells + new
    if rsync:
        lines[di] = (f"{m['ind']}ot_dp_rsync #(.W(1), .S({D - kk})) {inst} (.clk({clk}), .a({dexpr}), .q({q}));"
                     f"{m['tail']}  // KV-D23-REACH: synchroniser, {kk} relay stage(s) replicated per region")
    elif D > 1:
        lines[di] = (f"{m['ind']}ot_dp_dly #(.W(1), .D({D - kk})) {inst} (.clk({clk}), .d({dexpr}), .q({q}));"
                     f"{m['tail']}  // S81-COLGEN-1: common part, last stage replicated per region")
    else:
        lines[di] = f"{m['ind']}// S81-COLGEN-1: {inst} replaced by {len(allr)} region copies (1 stage, same d)"
        if di_decl is not None:
            lines[di_decl] = ""
    lines[di + 1:di + 1] = new
    row = dict(driver=inst, depth=D, common_depth=D - kk if D > 1 else 0, copy_depth=kk, regions=len(allr), copies=len(allr),
               **(dict(form="rsync") if rsync else {}),
               **(dict(tail_clear="sync", assert_delay_clk=kk) if tail_clear == "sync" else {}),
               **(dict(tail_clear="sync_output", assert_delay_clk=0) if tail_clear == "sync_output" else {}),
               chain_flops=len(allr) * kk,
               loads=len(uses), assign_splits=len(top) - len(dead), dead_assigns=len(dead), region_names=sorted(allr),
               loads_per_region=dict(sorted(leaf.items())), shared_rest=("rest" in allr))
    return lines, row


TAIL_COPY = re.compile(r"^\s*ot_dp_rtail\s*#\(\.D\(\d+\)\)\s+(?P<inst>\S+)\s*\(.*\.q\((?P<w>\w+)\[0\]\)\);\s*"
                       r"// landing pad tail copy for core (?P<region>\S+?): reset spine relay")
NK_LOCKUP_DQ = re.compile(r"^\s*ot_dp_lk\s*#\(\.W\(\d+\)\)\s+(?P<inst>u_lk_nk_\w+)\s*"
                          r"\(\.clk\([^()]*\),\s*\.d\((?P<d>[^()]*)\),\s*\.q\((?P<q>\w+)\)\);")


def lockup_region_check(text, specs, positions=None, type_name=""):
    """FABLE-FIX-KV-LOCKUP-INERT 11-25 (COORD): report-only read-back of the BOUND text of a type with a "lockup_regions" row.
    KV R6h strict binds of 11-22 wrote every hg / hgi type with the row present but without effect: the NK lockup latches of the
    even head cores stayed on the common "rest" copy (kv3_hgi_v2: 11 tail copies + rest with 40 loads instead of 18), found only
    by reading the bound text by hand.  Here, per row: every NK latch that reads a tail copy and feeds exactly one instance must
    read the copy of THAT instance, and no "rest" copy may be left.  The expected copy count is derived from the text (the cores
    behind the latches), not a constant; `positions` (plan hard cores) only says whether a missed core is known to the plan.
    -> list of warning lines (bind.py: bind_report.json warnings); never an error."""
    rows = [sp for sp in specs or [] if sp.get("form") == "rsync" and sp.get("lockup_regions")]
    if not rows:
        return []
    lines = text.split("\n")
    cur, encl, assigns, latches = None, {}, {}, []
    for i, ln in enumerate(lines):
        h = HDR.match(ln)
        if h and not ln.lstrip().startswith(("assign", "wire", "//", "ot_dp_")):
            cur = h["inst"]
        elif ln.strip().startswith(");"):
            cur = None
        encl[i] = None if ln.lstrip().startswith("assign") else cur
        am, lk = ASSIGN.match(ln), NK_LOCKUP_DQ.match(ln)
        if am:
            assigns[am["lhs"]] = am["rhs"]
        if lk:
            latches.append((i, lk["inst"], lk["d"], lk["q"]))
    qs = {q for _, _, _, q in latches}
    q_cores = {}
    for i, ln in enumerate(lines):
        port = CORE_PORT.match(ln)
        if port and encl[i] is not None:
            for sig in re.findall(r"\b\w+\b", port[1]):
                if sig in qs:
                    q_cores.setdefault(sig, set()).add(encl[i])
    out = []
    for sp in rows:
        pat = re.escape(sp["driver"]) if sp.get("driver") else sp.get("driver_re") or ""
        copies = {}                                                  # copy wire -> (driver instance, region)
        for ln in lines:
            m = TAIL_COPY.match(ln)
            if m and re.fullmatch(f"(?:{pat})_r\\d+", m["inst"]):
                copies[m["w"]] = (m["inst"].rsplit("_r", 1)[0], m["region"])

        def source(expr, depth=0):
            for sig in re.findall(r"\b\w+\b", expr):
                if sig in copies:
                    return sig
                if sig in assigns and depth < 16:
                    w = source(assigns[sig], depth + 1)
                    if w:
                        return w
            return None

        for drv in sorted({d for d, _ in copies.values()}):
            mine = {w: r for w, (d, r) in copies.items() if d == drv}
            wrong, wrong_lines = [], set()
            for i, inst, d, q in latches:
                w = source(d)
                cores = q_cores.get(q, set())
                if w in mine and len(cores) == 1 and mine[w] not in cores:
                    wrong.append((inst, mine[w], next(iter(cores))))
                    wrong_lines.add(i)
            regions = set(mine.values())
            rest_w = next((w for w, r in mine.items() if r == "rest"), None)
            rest_loads = []
            if rest_w:
                ru = re.compile(r"\b" + re.escape(rest_w) + r"\b")
                rest_loads = [i for i, ln in enumerate(lines) if ru.search(ln) and not TAIL_COPY.match(ln)
                              and not re.match(r"^\s*wire\b", ln)]
            if not wrong and not rest_w:
                continue
            want = {c for _, _, c in wrong}

            def only_wrong(w, depth=0):
                """True when every load of wire w is a mis-grouped latch, directly or through assigns (the copy would go away)"""
                wu = re.compile(r"\b" + re.escape(w) + r"\b")
                ls = [i for i, ln in enumerate(lines) if wu.search(ln) and not TAIL_COPY.match(ln) and not re.match(r"^\s*wire\b", ln)
                      and not (ASSIGN.match(ln) and ASSIGN.match(ln)["lhs"] == w)]
                return bool(ls) and all(i in wrong_lines or (depth < 16 and ASSIGN.match(lines[i]) is not None
                                                             and only_wrong(ASSIGN.match(lines[i])["lhs"], depth + 1)) for i in ls)

            keep_rest = bool(rest_w) and not only_wrong(rest_w)
            expected = len((regions - {"rest"}) | want) + (1 if keep_rest else 0)
            missed = sorted(want - regions)
            known = sum(1 for c in missed if c in (positions or {}))
            out.append(f"RESET_LOCKUP_REGIONS {type_name}: {drv}: lockup_regions row without full effect: {len(mine)} tail "
                       f"copies, {expected} expected; rest copy {'present, ' + str(len(rest_loads)) + ' load(s)' if rest_w else 'absent'}; "
                       f"{len(wrong)} NK lockup latch(es) read another region's copy; cores without their own copy "
                       f"({len(missed)}, {known} of them plan hard cores): {missed[:12]}; first: {wrong[:3]}")
    return out


def positions_from_plan(t):
    """{bound instance name: (x, y)} of a plan type's hard cores ('u_' + last component of the plan instance path)."""
    out = {}
    for c in (t.get("hard_cores") or []):
        o = c.get("origin_um")
        if o and c.get("inst"):
            out["u_u_" + c["inst"].split(".")[-1].replace("u_", "", 1)] = (o[0], o[1])
            out["u_" + c["inst"].split(".")[-1]] = (o[0], o[1])
    return out


def uses_rtail(plan):
    """True when a plan type carries a reset_replicate row of the rsync form (bind adds the ot_dp_rtail cell)"""
    return any(sp.get("form") == "rsync" for t in ((plan or {}).get("partition_types") or {}).values()
               for sp in (t.get("reset_replicate") or []))


def plan_keys(plan, type_re, spec):
    """set partition_types[T].reset_replicate = [spec] on every type whose name matches type_re; returns the names"""
    names = [tn for tn in sorted(plan["partition_types"]) if re.search(type_re, tn)]
    for tn in names:
        plan["partition_types"][tn]["reset_replicate"] = [dict(spec)]
    return names


def main(argv):
    if len(argv) > 1 and argv[1] == "plan":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("plan")
        ap.add_argument("out")
        ap.add_argument("type_re")
        ap.add_argument("--driver-re", required=True)
        ap.add_argument("--grid-um", type=float)
        ap.add_argument("--region-re")
        ap.add_argument("--optional", action="store_true")
        ap.add_argument("--min-loads", type=int)
        ap.add_argument("--copy-depth", type=int)
        a = ap.parse_args(argv[1:])
        spec = {"driver_re": a.driver_re}
        for k, v in (("grid_um", a.grid_um), ("region_re", a.region_re), ("optional", a.optional or None), ("min_loads", a.min_loads),
                     ("copy_depth", a.copy_depth)):
            if v is not None:
                spec[k] = v
        plan = json.load(open(a.plan))
        names = plan_keys(plan, a.type_re, spec)
        json.dump(plan, open(a.out, "w"), indent=1)
        print(f"reset_replicate: {len(names)} type(s) of {a.type_re}: {spec}")
        return 0
    if len(argv) < 3:
        print(__doc__)
        return 2
    txt = open(argv[1]).read()
    specs = json.load(open(argv[2]))
    pos = None
    if "--positions" in argv:
        pos = {k: tuple(v) for k, v in json.load(open(argv[argv.index("--positions") + 1])).items()}
    new, rep = apply(txt, specs, pos)
    if "-o" in argv:
        open(argv[argv.index("-o") + 1], "w").write(new)
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
