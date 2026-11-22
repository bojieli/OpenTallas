#!/usr/bin/env python3
"""HEAD-PLAN-1 (H8): bound-depth transport bench for the S81 HEAD die.

  head_transport_depth.py gen PLAN RTL_DIR REPO OUT [--mutant NAME] [--cycles N]
  head_transport_depth.py report PLAN OUT RUN_LOG [--expect-fail]

RTL_DIR is `gen.py rtl PLAN --clock-landing SIDECAR` output (25 type wrappers + s81_head_top.sv): the HEAD bound RTL.
The bench keeps that RTL and every real ot_dp_* / landing cell, and replaces only the LEAF cores (the plan's
`partition_types.<t>.contents[].inst`) by generated stubs:
  * every leaf output bus (plan bus with `leaf` = inst.port, dir out) drives a keyed PRNG word W(puid, bus, cycle);
  * every leaf input bus checks every bit, every cycle in the check window, against W(src_puid, src_bus, cycle - L),
    L = the lane's depth from the plan (latency.lanes[lane].cycles, cross-checked with schema.Plan.lane_latency);
    on a miss the stub searches offsets L-8..L+8 and reports the one that matches (the measured depth).
All clock taps / forwarded clocks / region clocks are one TB clock; reset is the real wavefront (rst_n), START is the
real broadcast (start + every pst_* START-stage input at the same edge). Leaf observer inputs of hd_ctl (start_i =
landing ready AND, lep_fault_i = landing fault OR) are printed at the end.
Mutants (each must FAIL): st_bypass (one ft station of hd_turn_b removed: its 12 lanes -1), st_double (one extra
station in hd_turn_a: +1), k_plus1 (one count-strap K literal +1 in the die top), bit_swap (two data bits of the
hd_tile out boundary swapped), oracle (the checker expects lane chE0_b0 at L+1).
"""
import argparse
import json
import re
import sys
from pathlib import Path

WMAX_ALIGN = 64
# a clock port shared by several partitions (gen top region nets, e.g. clk_region_host: host_nstrip/e/w, 39 ps apart)
# takes their mean phase when they lie within this spread (crossing margins >= 100 ps); wider fails closed
SHARED_PHASE_SPREAD_PS = 60.0


def load_plan(p):
    return json.loads(Path(p).read_text())


def lane_table(plan, repo):
    """lane id -> (src part, src bus, dst part, dst bus, cycles). Cross-check with schema.Plan when importable."""
    ports = {p['id']: p for p in plan['ports']}
    lat = plan['latency']['lanes']
    sch = None
    try:
        sys.path.insert(0, str(Path(repo) / 'tools/die_plan'))
        from schema import Plan  # noqa
        sch = Plan(plan)
    except Exception as e:  # report, never silently skip
        print('WARN schema.Plan not importable:', repr(e)[:200])
    rows, mism = [], []
    pt = plan['partition_types']; ptype = {p['name']: p['type'] for p in plan['partitions']}

    def live_regs(part, bus):
        # a type with realize_internal_stations builds its internal_stations rows in the WRAPPER (gen.py), outside the
        # stubbed leaf: the regs of the row on this leaf bus are live in the bench
        t = pt[ptype[part]]
        if not t.get('realize_internal_stations'):
            return 0
        return sum(len(x.get('regs_um', [])) for x in t.get('internal_stations', []) if x.get('conn') == 'bus:' + bus)
    for li, l in enumerate(plan['lanes']):
        s = ports[l['ports'][0]]['src']; d = ports[l['ports'][-1]]['dst']
        cyc = lat[l['id']]['cycles']
        if sch is not None:
            try:
                c2 = sch.lane_latency(l['id'])
                c2 = c2['cycles'] if isinstance(c2, dict) else c2
                if c2 != cyc:
                    mism.append((l['id'], cyc, c2))
            except Exception as e:
                mism.append((l['id'], cyc, 'ERR ' + repr(e)[:80]))
        # fixed_cycles are realized inside the source/dest CORE (e.g. CTL_PRE x_o +1), which this bench stubs, EXCEPT
        # the part the plan realizes as wrapper stations on the lane's end buses (live_regs; r16 p6: 38 lanes, spine
        # b / x, ch*_r / _h, host / mesh rx-tx at hd_ctl, kd).  The bench transport must equal cycles - fixed + live;
        # the core part has its own proof (listed in the switch).  live > fixed is a plan error (fail closed).
        fx = int(l.get('fixed_cycles', 0))
        lv = live_regs(s['part'], s['bus']) + live_regs(d['part'], d['bus'])
        if lv > fx:
            raise SystemExit('lane %s: %d realized wrapper stations on its end buses > fixed_cycles %d' % (l['id'], lv, fx))
        rows.append(dict(idx=li, id=l['id'], src=s['part'], sbus=s['bus'], dst=d['part'], dbus=d['bus'],
                         cycles=cyc - fx + lv, plan_cycles_total=cyc, fixed=fx, live_stations=lv,
                         width=ports[l['ports'][-1]]['width']))
    return rows, mism


INST_RE = r'^    (?P<mod>[A-Za-z_]\w*)\s*(?P<par>#\([^\n]*\))?\s+(?P<inst>%s)\s*\(\n(?P<body>.*?)\n    \);'
CONN_RE = re.compile(r'^\s*\.(\w+)\s*\((.*?)\)\s*,?\s*(?://.*)?$', re.M)


def find_inst(text, inst):
    m = re.search(INST_RE % re.escape(inst), text, re.S | re.M)
    return m


def gen(args):
    plan = load_plan(args.plan)
    rtl = Path(args.rtl_dir); out = Path(args.out); out.mkdir(parents=True, exist_ok=False)
    pt = plan['partition_types']; parts = plan['partitions']
    puid = {p['name']: i for i, p in enumerate(parts)}
    lanes, mism = lane_table(plan, args.repo)
    if args.mutant == 'oracle':
        for r in lanes:
            if r['id'] == 'chE0_b0':
                r['cycles'] += 1
    # global bus ids per (type, bus)
    busid, businfo = {}, {}
    for tn in sorted(pt):
        for b in pt[tn].get('buses', []):
            busid[(tn, b['name'])] = len(busid)
            businfo[(tn, b['name'])] = b
    wmax = max(b['width'] for b in businfo.values())
    wmax = (wmax + WMAX_ALIGN - 1) // WMAX_ALIGN * WMAX_ALIGN
    nchunk = wmax // 64
    # dst (part, bus) -> lane row
    by_dst = {}
    for r in lanes:
        k = (r['dst'], r['dbus'])
        if k in by_dst:
            raise SystemExit('two lanes end at one bus: %s %s' % (k, r['id']))
        by_dst[k] = r
    emitted = json.loads((rtl / 'gen_clock_landings.json').read_text()).get('emitted_modules', {})
    PH = json.loads(Path(args.phases).read_text()) if getattr(args, 'phases', None) else None
    CHKC = max(1500, args.cycles // 3)
    # FRAME (count_align_plan / ot_dp_clk_landing_ca): region v's edge k is at k T + phase_v, its count origin a_v and
    # the bind's n_nominal are indices of its OWN edges, a ring's lag is L = (K + a_dst - a_src) T + d and a lane's plan
    # cycles are counts in that frame.  So in a phased bench every stub counts its own clock edges (all generators start
    # at edge 0 = 1000 + D ps).  --stub-root keeps the tb root counter (diagnostic only: wrong by (phase_dst -
    # phase_src) / T; the tr25 'root frame' reading was the folded-phase artefact, see tb_text).
    LOC = bool(PH) and not getattr(args, 'stub_root', False)
    CYC, CLK, CHK = ('lc', 'ck', 'lchk') if LOC else ('$root.tb.cyc', '$root.tb.clk', '$root.tb.chk')
    files, stubs, cover = [], [], dict(types={}, lanes=len(lanes))
    pkg = ['package ot_tb_pkg;',
           '  function automatic [63:0] smix(input [63:0] z0);',
           '    reg [63:0] z; begin z = z0 + 64\'h9E3779B97F4A7C15; z = (z ^ (z >> 30)) * 64\'hBF58476D1CE4E5B9;',
           '    z = (z ^ (z >> 27)) * 64\'h94D049BB133111EB; smix = z ^ (z >> 31); end',
           '  endfunction',
           '  function automatic [%d:0] word(input integer p, input integer b, input integer t);' % (wmax - 1),
           '    integer c; reg [%d:0] w; begin' % (wmax - 1),
           '    for (c = 0; c < %d; c = c + 1) w[c*64 +: 64] = smix({16\'(p), 16\'(b), 8\'(c), 24\'(t)});' % nchunk,
           '    word = w; end',
           '  endfunction',
           'endpackage']
    (out / 'ot_tb_pkg.sv').write_text('\n'.join(pkg) + '\n')
    files.append(out / 'ot_tb_pkg.sv')
    for tn, t in sorted(pt.items()):
        if t.get('hard'):
            continue
        mod = emitted.get(tn, t['module'])
        src = rtl / (mod + '.sv')
        if not src.is_file():
            continue
        text = src.read_text()
        if re.search(r'module\s+%s\s*#' % re.escape(mod), text):
            raise SystemExit('wrapper already parameterised: ' + mod)
        text = re.sub(r'module\s+%s\s*\(' % re.escape(mod), 'module %s #(parameter integer PUID = 0) (' % mod, text, count=1)
        my_parts = [p['name'] for p in parts if p['type'] == tn]
        leafs = [c['inst'] for c in t.get('contents', []) if c.get('inst')]
        cover['types'][tn] = dict(module=mod, leaves=[], parts=len(my_parts))
        for inst in leafs:
            m = find_inst(text, inst)
            if not m:
                cover['types'][tn]['leaves'].append(dict(inst=inst, found=False))
                continue
            conns = CONN_RE.findall(m.group('body'))
            sname = 'stub__%s__%s' % (tn, inst)
            leafbus = {b['leaf'].split('.', 1)[1]: b for b in t.get('buses', [])
                       if b.get('leaf', '').split('.', 1)[0] == inst}
            decl, body, nchk = [], [], 0
            for pname, net in conns:
                b = leafbus.get(pname)
                if b is None:
                    d = 'output' if (pname.endswith('_o') or net.startswith('ftspare')) else 'input'
                    decl.append('    %s wire %s' % (d, pname))
                    continue
                W = b['width']; bid = busid[(tn, b['name'])]
                if b['dir'] == 'out':
                    decl.append('    output wire [%d:0] %s' % (W - 1, pname))
                    body.append('    wire [%d:0] w_%s = ot_tb_pkg::word(PUID, %d, %s);' % (wmax - 1, pname, bid, CYC))
                    body.append('    assign %s = w_%s[%d:0];' % (pname, pname, W - 1))
                    continue
                decl.append('    input wire [%d:0] %s' % (W - 1, pname))
                cases = []
                for pn in my_parts:
                    r = by_dst.get((pn, b['name']))
                    if r is None:
                        continue
                    st = parts[puid[r['src']]]['type']
                    cases.append('      %d: si = {16\'d%d, 16\'d%d, 16\'d%d, 16\'d%d};' % (
                        puid[pn], puid[r['src']], busid[(st, r['sbus'])], r['cycles'], r['idx']))
                if not cases:
                    continue
                nchk += 1
                v = 'c_' + pname
                body += [
                    '    function automatic [63:0] si_%s(input integer p); reg [63:0] si; begin' % pname,
                    '      case (p)'] + cases + [
                    '      default: si = 64\'hFFFF_FFFF_FFFF_FFFF;', '      endcase', '      si_%s = si; end' % pname,
                    '    endfunction',
                    '    localparam [63:0] SI_%s = si_%s(PUID);' % (pname, pname),
                    '    integer %s_err = 0, %s_ok = 0, %s_first = -1, %s_off = 99, %s_d;' % (v, v, v, v, v),
                    '    reg %s_hit; reg [%d:0] %s_x;' % (v, wmax - 1, v),
                    '    always @(posedge %s) if (SI_%s[15:0] != 16\'hFFFF && %s) begin' % (CLK, pname, CHK),
                    '      %s_x = ot_tb_pkg::word(SI_%s[63:48], SI_%s[47:32], %s - SI_%s[31:16]);' % (v, pname, pname, CYC, pname),
                    '      if (%s === %s_x[%d:0])' % (pname, v, W - 1),
                    '        %s_ok = %s_ok + 1;' % (v, v),
                    '      else begin',
                    '        if (%s_err == 0) begin %s_first = %s; %s_hit = 0;' % (v, v, CYC, v),
                    '          for (%s_d = -8; %s_d <= 8; %s_d = %s_d + 1) begin' % (v, v, v, v),
                    '            %s_x = ot_tb_pkg::word(SI_%s[63:48], SI_%s[47:32], %s - SI_%s[31:16] - %s_d);' % (v, pname, pname, CYC, pname, v),
                    '            if (!%s_hit && %s === %s_x[%d:0]) begin %s_off = %s_d; %s_hit = 1; end' % (v, pname, v, W - 1, v, v, v),
                    '          end',
                    '        end',
                    '        %s_err = %s_err + 1;' % (v, v),
                    '      end',
                    '    end',
                    '    final if (SI_%s[15:0] != 16\'hFFFF) $display("LANE %%0d dst_puid %%0d ok %%0d err %%0d first %%0d off %%0d",'
                    ' SI_%s[15:0], PUID, %s_ok, %s_err, %s_first, %s_off);' % (pname, pname, v, v, v, v)]
            if tn == 'hd_ctl' and inst == 'u_core':
                body.append('    final $display("OBSERVER ctl start_i %0d lep_fault_i %0d", start_i, lep_fault_i);')
            if LOC:  # every stub counts its OWN clock edges (region edge k = k T + phase, planner frame)
                body = ['    integer lc = 0; reg lchk = 0;',
                        '    always @(posedge ck) begin lc <= lc + 1; lchk <= (lc >= %d); end' % CHKC] + body
            stubs.append('module %s #(parameter integer PUID = 0) (\n%s\n);\n%s\nendmodule\n' % (
                sname, ',\n'.join(decl), '\n'.join(body)))
            text = text[:m.start()] + '    %s #(.PUID(PUID)) %s (\n%s\n    );' % (sname, inst, m.group('body')) + text[m.end():]
            cover['types'][tn]['leaves'].append(dict(inst=inst, found=True, module=m.group('mod'), checked_buses=nchk))
        text = mutate_wrapper(args.mutant, tn, text)
        (out / src.name).write_text(text)
        files.append(out / src.name)
    # --top: the COMPLETED die top (gen top + head_start_sources.complete_top + START stages), the die as built;
    # the bare gen.py top leaves pst_* START inputs open and is not a valid transport model.
    top = read_any(args.top) if args.top else (rtl / 's81_head_top.sv').read_text()
    for p in parts:
        mod = emitted.get(p['type'], pt[p['type']]['module'])
        top, n = re.subn(r'^(    %s) (%s) \(' % (re.escape(mod), re.escape(p['name'])),
                         r'\1 #(.PUID(%d)) \2 (' % puid[p['name']], top, count=1, flags=re.M)
        if n != 1 and not pt[p['type']].get('hard'):
            raise SystemExit('top instance not found: ' + p['name'])
    top = mutate_top(args.mutant, top)
    (out / 's81_head_top.sv').write_text(top)
    files.append(out / 's81_head_top.sv')
    (out / 'stubs.sv').write_text('\n'.join(stubs))
    files.append(out / 'stubs.sv')
    files.append(rtl / 'ot_dp_cells.sv')
    for i, x in enumerate(args.extra or []):
        dst = out / ('extra%d_%s' % (i, Path(x).name.replace('.gz', '')))
        dst.write_text(read_any(x)); files.append(dst)
    # library cells the generated RTL instantiates
    for f in ('rtl/common/ot_dp_clk_landing.sv', 'rtl/common/ot_dp_clk_landing_ca.sv', 'rtl/common/ot_meso_fifo.sv'):
        files.append(Path(args.repo) / f)
    extra = Path(args.repo) / 'rtl/common'
    used = set(re.findall(r'^\s{4}(ot_dp_\w+)\s', '\n'.join(Path(f).read_text() for f in files if Path(f).suffix == '.sv'), re.M))
    have = set()
    for f in files:
        have |= set(re.findall(r'^module\s+(\w+)', Path(f).read_text(), re.M))
    miss = sorted(used - have)
    for mname in miss:
        hit = None
        for cand in sorted((Path(args.repo) / 'rtl').rglob('*.sv')):
            try:
                if re.search(r'^module\s+%s\b' % mname, cand.read_text(errors='replace'), re.M):
                    hit = cand; break
            except OSError:
                pass
        if hit is None:
            raise SystemExit('cell module not found: ' + mname)
        files.append(hit)
    tb = tb_text(plan, top, args.cycles, wmax, PH)
    (out / 'tb.sv').write_text(tb)
    files.append(out / 'tb.sv')
    names = []
    for f in dict.fromkeys(files):
        f = Path(f)
        if f.resolve().parent != out.resolve():
            dst = out / ('lib_' + f.name)
            dst.write_bytes(f.read_bytes())
            f = dst
        names.append(f.name)
    (out / 'files.f').write_text('\n'.join(names) + '\n')
    (out / 'lanes.json').write_text(json.dumps(dict(lanes=lanes, plan_vs_schema_mismatch=mism, cover=cover,
                                                     mutant=args.mutant, wmax=wmax), indent=1))
    (out / 'run.sh').write_text(RUN_SH)
    print('GEN', out, 'lanes', len(lanes), 'schema_mismatch', len(mism), 'mutant', args.mutant)


def read_any(p):
    import gzip
    p = Path(p)
    return gzip.open(p, 'rt').read() if p.suffix == '.gz' else p.read_text()


def mutate_wrapper(mut, tn, text):
    if mut == 'st_bypass' and tn == 'hd_turn_b':
        m = re.search(r'^    ot_dp_st #\(\.W\((\d+)\)\) (u_ft_t_s1) \(.*?\.d\((\w+)\), \.ea\((\w+)\), \.q\(([^)]*)\), \.eq\(([^)]*)\)\);$',
                      text, re.M)
        assert m, 'st_bypass target'
        text = text[:m.start()] + '    assign %s = %s; assign %s = %s;  // MUTANT st_bypass' % (
            m.group(5), m.group(3), m.group(6), m.group(4)) + text[m.end():]
    if mut == 'st_double' and tn == 'hd_turn_a':
        m = re.search(r'^    ot_dp_st #\(\.W\((\d+)\)\) (u_ft_\w+) \(\.clk\((\w+)\), \.rst_n\((\w+)\), \.d\(([^)]*)\), \.ea\(([^)]*)\), (.*)$',
                      text, re.M)
        assert m, 'st_double target'
        W = m.group(1)
        ins = ('    wire [%s-1:0] mut_dq; wire mut_de;  // MUTANT st_double\n'
               '    ot_dp_st #(.W(%s)) u_mut_st (.clk(%s), .rst_n(%s), .d(%s), .ea(%s), .q(mut_dq), .eq(mut_de));\n'
               % (W, W, m.group(3), m.group(4), m.group(5), m.group(6)))
        line = '    ot_dp_st #(.W(%s)) %s (.clk(%s), .rst_n(%s), .d(mut_dq), .ea(mut_de), %s' % (
            W, m.group(2), m.group(3), m.group(4), m.group(7))
        text = text[:m.start()] + ins + line + text[m.end():]
    if mut == 'bit_swap' and tn == 'hd_tile':
        m = re.search(r'^    (ot_dp_ste #\(\.W\(565\)\) u_bout_o \(.*?\.d\()(o_d)(\).*)$', text, re.M)
        assert m, 'bit_swap target'
        text = text[:m.start()] + m.group(1) + '{o_d[564:302], o_d[300], o_d[301], o_d[299:0]}' + m.group(3) + text[m.end():]
    return text


def mutate_top(mut, top):
    if mut == 'k_plus1':
        m = re.search(r"^(    ot_s81hd_tile_p #\(\.PUID\(\d+\)\) tE0o1 \((?:.|\n)*?\.strap_ca_k_i\()(\d+)'b([01]+)(\))", top, re.M)
        assert m, 'k_plus1 target'
        w = int(m.group(2)); v = (int(m.group(3), 2) + 1) % (1 << w)
        top = top[:m.start()] + m.group(1) + "%d'b%s" % (w, format(v, '0%db' % w)) + m.group(4) + top[m.end():]
    return top


def tb_text(plan, top, cycles, WMAXH, PH=None):
    hdr = re.search(r'module s81_head_top \((.*?)\);', top, re.S).group(1)
    ios = re.findall(r'^\s*(input|output)\s+wire\s*(?:\[(\d+):0\])?\s*(\w+)\s*;', top, re.M)  # non-ANSI top: port decls are in the body
    decl, conn, drive = [], [], []
    for d, w, n in ios:
        W = int(w) + 1 if w else 1
        decl.append('  wire [%d:0] %s;' % (W - 1, n) if d == 'output' else '  reg [%d:0] %s;' % (W - 1, n))
        conn.append('    .%s(%s)' % (n, n))
        if d == 'input':
            if n.startswith('clk_region') or n.endswith('_rck') or n.startswith('clk') or n.endswith('__clk'):  # __clk: START-stage tap ports of the completed top
                ps = None
                if PH:
                    ps = PH['clocks'].get(n)
                    if ps is None and n.endswith('_rck'):  # <part>_*_rck: the part's own phase
                        ps = PH['clocks'].get('clk_region_' + n.split('_pma_')[0])
                    if ps is None:  # a region clock port named for another region: the phase of the partitions it clocks
                        pat = r'(?m)^    \w+ (?:#\([^\n]*\) )?(\w+) \((?:(?!\n    \);).)*?\.clk\(%s\)' % re.escape(n)
                        vals = {PH['clocks'].get('clk_region_' + u) for u in re.findall(pat, top, re.S)} - {None}
                        if vals and max(vals) - min(vals) <= SHARED_PHASE_SPREAD_PS:  # one shared region net: mean
                            ps = sum(vals) / len(vals)
                    if ps is None:
                        raise SystemExit('phased bench: no single phase for clock port ' + n)
                if ps:
                    # a free-running generator per phased clock, integer ps under `timescale 1ps/1ps.  Verilator 5.050
                    # (a) rounds a fractional delay to whole time units (#(0.4) under 1ns/1ps = 0, #(6.6) = 7) and
                    # (b) folds `always @(clk) x <= #(D) clk` to D mod T/2 once D >= T/2 (the always block waits out
                    # the delay and misses clk events: D = 1055 and 2055 both rise at 3055, 3811 rises at 5811; HEAD-
                    # START-R18 dly test 11-21).  Either one quantises / folds every phase, so tr11-tr27 are void.
                    # tb clk rises at 1000 + 2000 k; this port rises at 1000 + D + 2000 k (edge k of the region).
                    drive.append('  initial begin %s = 0; #(%d); forever begin %s = 1; #1000; %s = 0; #1000; end end' % (
                        n, 1000 + round(ps * 2000.0 / PH['period_ps']), n, n))
                else:
                    drive.append('  always @* %s = clk;' % n)
            elif n == 'rst_n':
                drive.append('  always @* rst_n = (cyc >= 40);')
            elif n == 'start' or n.startswith('pst_'):
                drive.append('  always @* %s = (cyc >= 400);' % n)
            else:
                drive.append('  wire [%d:0] wd_%s = ot_tb_pkg::word(%d, 0, cyc); always @* %s = wd_%s[%d:0];' % (WMAXH - 1, n, 4000 + len(drive), n, n, W - 1))
    decl = [x for x in decl if not re.search(r'\b(clk)\b;', x)]
    return '\n'.join([
        '`timescale 1ps/1ps' if PH else '`timescale 1ns/1ps', 'module tb;',
        '  reg clk = 0; integer cyc = 0; reg chk = 0;',
        '  always #1000 clk = ~clk;' if PH else '  always #1 clk = ~clk;',
        '  always @(posedge clk) begin cyc <= cyc + 1; chk <= (cyc >= %d); if (cyc == %d) $finish; end' % (
            max(1500, cycles // 3), cycles)] + decl + drive + [
        '  s81_head_top dut (', ',\n'.join(conn), '  );',
        '  final $display("TB_DONE cyc %0d", cyc);',
        'endmodule'])


RUN_SH = r'''#!/bin/bash
# build + run: run.sh BENCH_DIR (inside ot-run; verilator from ~/.local/opentallas-tools/bin)
set -u
D=$(cd "$1" && pwd); cd "$D"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
O=$D/obj; rm -rf "$O"; mkdir -p "$O"
verilator --binary --timing -j ${BUILD_THREADS:-16} -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT \
  -Wno-WIDTH -Wno-PINMISSING -Wno-UNDRIVEN -Wno-IMPLICIT --x-assign 0 --x-initial 0 --top-module tb -Mdir "$O" -o sim \
  --output-split 4000 --output-split-cfuncs 1000 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
  -f "$D/files.f" > "$O/build.log" 2>&1
rc=$?
if [ $rc -ne 0 ]; then echo "BUILD_FAIL rc=$rc"; grep -m20 -E "%Error" "$O/build.log"; exit 2; fi
"$O/sim" > "$D/run.log" 2>&1
echo "RUN rc=$?"; grep -c "^LANE" "$D/run.log"; tail -3 "$D/run.log"
'''


def phases(args):
    """HEAD-START-R17 phase model (count-aligned HEAD needs it): the plan's K straps, START steps PAD + 2 + J(d) and ring
    windows are derived from the REAL clock difference d of every START tree edge and crossing, so a single ideal clock
    is not a model of the die (19 r16 p6 rings are outside their window at d = 0, every rise START edge is 1 count
    late).  The phase of every region = the sum of the bind's START-edge d along its tree path (root 0), so every tree
    edge gets exactly its planned d; each crossing's bench d (phase dst - phase src) is checked against its derated
    [d_lo, d_hi].  Clock ports: START stage taps (stage region) and clk_region_<part> / <part>_*_rck (part region).
    usage: phases BIND STAGES OUT.json"""
    bd = json.loads(Path(args.bind).read_text())
    st = json.loads(read_any(args.stages))
    R, SP = bd['regions'], bd['start_ports']
    ph = {}

    def phase(r):
        if r in ph:
            return ph[r]
        v = R[r]
        ph[r] = 0.0 if v['parent'] is None else phase(v['parent']) + float(SP[v['tree_port']]['d_ps'])
        return ph[r]
    sys.setrecursionlimit(100000)
    for r in R:
        phase(r)
    lo = min(ph.values())
    clocks, dev, bad = {}, [], []
    for s in st['stages']:
        clocks[s['clock_port']] = ph[s['region']] - lo
    for pn, pv in bd['parts'].items():
        clocks['clk_region_' + pn] = ph[pv['region']] - lo
    for k, v in bd['ports'].items():
        ra, rb = bd['parts'][v['src_part']]['region'], bd['parts'][v['dst_part']]['region']
        d = ph[rb] - ph[ra]
        dev.append(abs(d - 0.5 * (v['d_lo_ps'] + v['d_hi_ps'])))
        if not (v['d_lo_ps'] <= d <= v['d_hi_ps']):
            bad.append((k, round(d, 1), v['d_lo_ps'], v['d_hi_ps']))
    out = dict(schema='ot_head_bench_phases/1', period_ps=float(bd.get('period_ps', 833.0)), clocks=clocks,
               check=dict(regions=len(ph), crossings=len(dev), crossing_d_outside_interval=len(bad),
                          outside=bad[:40], max_dev_from_mid_ps=round(max(dev), 1) if dev else 0.0,
                          max_phase_ps=round(max(clocks.values()), 1)))
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out['check']))
    return 1 if bad else 0


def report(args):
    plan = load_plan(args.plan)
    meta = json.loads((Path(args.out) / 'lanes.json').read_text())
    lanes = {r['idx']: r for r in meta['lanes']}
    seen, bad, rows = set(), [], []
    obs = None
    for line in Path(args.run_log).read_text().splitlines():
        m = re.match(r'LANE (\d+) dst_puid (\d+) ok (\d+) err (\d+) first (-?\d+) off (-?\d+)', line)
        if m:
            i, ok, err, first, off = int(m.group(1)), int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6))
            seen.add(i); r = lanes[i]
            row = dict(lane=r['id'], src='%s.%s' % (r['src'], r['sbus']), dst='%s.%s' % (r['dst'], r['dbus']),
                       plan_cycles=r['cycles'], ok=ok, err=err, first=first,
                       measured=(r['cycles'] + off) if off != 99 else None)
            rows.append(row)
            if err or ok == 0:
                bad.append(row)
        if line.startswith('OBSERVER'):
            obs = line
    missing = sorted(set(lanes) - seen)
    verdict = 'PASS' if not bad and not missing else 'FAIL'
    res = dict(verdict=verdict, mutant=meta['mutant'], lanes=len(lanes), checked=len(seen), failing=len(bad),
               missing=[lanes[i]['id'] for i in missing], observer=obs, bad=bad[:60],
               plan_vs_schema_mismatch=meta['plan_vs_schema_mismatch'], measured=rows)
    Path(args.out, 'verdict.json').write_text(json.dumps(res, indent=1))
    print('VERDICT', verdict, 'mutant', meta['mutant'], 'checked', len(seen), '/', len(lanes), 'failing', len(bad),
          'missing', len(missing), obs or '')
    for b in bad[:12]:
        print('  BAD', b)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    g = sp.add_parser('gen'); g.add_argument('plan'); g.add_argument('rtl_dir'); g.add_argument('repo'); g.add_argument('out')
    g.add_argument('--mutant', default='none', choices=['none', 'st_bypass', 'st_double', 'k_plus1', 'bit_swap', 'oracle'])
    g.add_argument('--cycles', type=int, default=4000)
    g.add_argument('--top', help='completed die top (.sv or .sv.gz) instead of RTL_DIR/s81_head_top.sv')
    g.add_argument('--extra', action='append', help='extra RTL (e.g. start_stages.sv[.gz]), repeatable')
    g.add_argument('--phases', help='phases OUT.json: per-clock-port planned phase (count-aligned die model); stubs count own edges')
    g.add_argument('--stub-root', action='store_true', help='phased: stubs use the tb root counter (diagnostic, not the plan frame)')
    q = sp.add_parser('phases'); q.add_argument('bind'); q.add_argument('stages'); q.add_argument('out')
    r = sp.add_parser('report'); r.add_argument('plan'); r.add_argument('out'); r.add_argument('run_log')
    a = ap.parse_args()
    if a.cmd == 'phases':
        sys.exit(phases(a))
    gen(a) if a.cmd == 'gen' else report(a)


if __name__ == '__main__':
    main()
