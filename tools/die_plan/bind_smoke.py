#!/usr/bin/env python3
"""CAL-AUTO 10-23: bind smoke gate -- a short functional RTL simulation of ONE representative token stage on a BOUND
die top (tools/die_plan/bind.py output) plus ONE schedule mutant in the same binary.  Run after every bind; the verdict
goes into the bind directory (<bound>/smoke/smoke_report.json, schema opentallas.die_plan.bind_smoke.v1).

    bind_smoke.py --die qwen_compute --bound BIND_DIR --src-rev REV --work WORK [--constants REGEN.json] [--submit]

Gate = nominal run PASS and mutant run FAIL (the mutant proves the bench sees a one-cycle schedule error).

qwen_compute vehicle (= STEWARD-TOKh/TOKi xt1, made automatically here, never hand-edited):
  * carve of qwen_compute_bound_top: the 15 partitions of slice W5 (sl_W5_*) + the near cluster c16_W5_2 (c_W5_tn_*,
    cid 2) [+ the far cluster c16_W5_3 (c_W5_tf_*, cid 3) with --clusters both]
    measured 10-23 on BINDER3 bound_r8 @d4b946c05 (gold2): near 37 min (build 30.5 + sim 6.7, 43 GB) / both 64 min (76 GB), instance text byte-for-byte; the three
    tt_ctlm -> sl_W5_fw lane ends (cmd / hr / tl) are the XT1 bench event ports, every other open lane end idles at 0;
  * source closure: every module the carve instantiates, resolved from <bound>/rtl, then the bind.f files, then the
    source revision REV (git), with `include files and their incdirs; the file list is generated, not hand kept;
  * bench: xt1_bench.py gen (nominal lead 8 / gap 4) -> tb_smoke -> xt1n_bench.py check (near [+ far] words exact vs the
    TOKe-QWM record gold, ROM masks masks_fixed);
  * mutant: +SMOKE_MUT_SKEW=1 delays the hr lane end by one cycle against cmd/tl (models one schedule constant off by
    one), same binary;
  * build: Verilator 5.050, C++ at -O0 with real build parallelism, obj cached by the sha256 of carve + file list.
qwen_kvsys: static landed-depth audit only (no runnable KV bench vehicle on a bound top yet) -> verdict PENDING.
hbm / s81: no bound top yet -> PENDING.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCHEMA = "opentallas.die_plan.bind_smoke.v1"
REPO = Path(__file__).resolve().parents[2]
XT1_INPUTS = "ot-gold2:/srv/opentallas-scratch/claude/tokqwm-1023/xt1"     # TOKe-QWM record gold + masks
REMOTE_ROOT = "/srv/opentallas-scratch/claude/cal-auto-smoke"
VERILATOR = "$HOME/.local/opentallas-tools/verilator-5.050/bin"
SRC_ROOTS = ["rtl/*.sv", "rtl/*.v", "rtl/*.svh", "rtl/*.vh", "physical/asap7_memory_macros*/*.v",
             "physical/qwen_missing_phy/*.v", "physical/qwen_missing_phy/*.sv", "physical/qwen_kv_die_phy/*.v"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ QC carve (xt1)
# vendored from STEWARD-TOKh bound_carve.py (10-23), plus --clusters near (far cluster dropped, its lanes idle)
INST = re.compile(r'^\s*(\w+)\s*(#\(.*\))?\s+(\w+)\s*\($')
CONN = re.compile(r'^\s*\.(\w+)\((\w*)\),?$')
WIRE = re.compile(r'^\s*wire\s*(\[(\d+):(\d+)\])?\s*(\w+)\s*;\s*(//\s*lane\s+(\S+))?')
PORT = re.compile(r'^\s*(input|output)\s+wire\s*(\[(\d+):(\d+)\])?\s*(\w+)')
EVENT = {'tt_ctlm__cmd_cmd_wi': ('cmd0', 116), 'tt_ctlm__hr_hr_wi': ('hr0', 453), 'tt_ctlm__tl_st_wi': ('swi', 1088)}
SLOT = {(0, 0): 0, (0, 1): 2, (0, 2): 8, (0, 3): 10, (1, 0): 1, (1, 1): 3, (1, 2): 9, (1, 3): 11,
        (2, 0): 4, (2, 1): 6, (2, 2): 12, (2, 3): 14, (3, 0): 5, (3, 1): 7, (3, 2): 13, (3, 3): 15}


def parse_top(p: Path):
    wires, insts, cur = {}, [], None
    for ln in p.read_text().splitlines():
        if cur is not None:
            m = CONN.match(ln)
            if m:
                cur['conns'].append((m.group(1), m.group(2)))
                cur['text'].append(ln)
                continue
            if ln.strip() == ');':
                cur['text'].append(ln)
                insts.append(cur)
                cur = None
                continue
            raise SystemExit(f'unparsed instance line: {ln}')
        m = WIRE.match(ln)
        if m:
            w = int(m.group(2)) - int(m.group(3)) + 1 if m.group(1) else 1
            wires[m.group(4)] = dict(width=w, lane=m.group(6), decl=ln)
            continue
        m = INST.match(ln)
        if m and m.group(1) != 'module':
            cur = dict(module=m.group(1), name=m.group(3), conns=[], text=[ln])
    return wires, insts


def ports_of(rtl: Path, module: str, cache={}):
    if module not in cache:
        d = {}
        for ln in (rtl / f'{module}.sv').read_text().splitlines():
            m = PORT.match(ln)
            if m:
                d[m.group(5)] = m.group(1)
            if ln.startswith(');'):
                break
        cache[module] = d
    return cache[module]


def tiles_of(rtl: Path, module: str):
    out = []
    for ln in (rtl / f'{module}.sv').read_text().splitlines():
        m = re.match(r'^\s*(qfd_tile_\w+)\s+u_u_t_(\d)_(\d)\s*\(', ln)
        if m:
            out.append((int(m.group(2)), int(m.group(3))))
    return out


def qc_carve(top: Path, rtl: Path, out: Path, clusters: str):
    seed = re.compile(r'^(sl_W5_\w+|c_W5_tn_\d\d' + (r'|c_W5_tf_\d\d' if clusters == 'both' else '') + r')$')
    nseed = 23 if clusters == 'both' else 19
    out.mkdir(parents=True, exist_ok=True)
    wires, insts = parse_top(top)
    keep = [i for i in insts if seed.match(i['name'])]
    if len(keep) != nseed:
        raise SystemExit(f'carve: {len(keep)} seed partitions != {nseed}: {[i["name"] for i in keep]}')
    drv, rd = {}, {}
    for i in keep:
        pd = ports_of(rtl, i['module'])
        for p, n in i['conns']:
            if not n:
                continue
            dirn = pd.get(p)
            if not dirn:
                raise SystemExit(f'carve: {i["name"]}.{p} not a port of {i["module"]}')
            (drv if dirn == 'output' else rd).setdefault(n, []).append((i['name'], p))
    clocks = sorted({n for n in rd if n.startswith('clk_')})
    ext = sorted(n for n in rd if n not in drv and n not in clocks and n != 'rst_n')
    used = sorted((set(drv) | set(rd)) - set(clocks) - {'rst_n'})
    L = ['// GENERATED by tools/die_plan/bind_smoke.py (CAL-AUTO, from STEWARD-TOKh bound_carve.py): xt1 smoke carve',
         f'// source: {top} sha256 {sha256(top)}; seeds = sl_W5_* + c_W5_tn_*' + (' + c_W5_tf_*' if clusters == 'both' else ''),
         '`timescale 1ns/1ps',
         'module xt1b_carve (input wire ck, input wire rst_n, input wire [115:0] cmd0, input wire [452:0] hr0,',
         '    input wire [1087:0] swi, output wire [515:0] cw_n0, output wire [515:0] cw_n1, output wire [515:0] cw_n2,',
         '    output wire [515:0] cw_n3, output wire [513:0] rs, output wire [513:0] rs_o, output wire [513:0] rsc,',
         '    output wire [513:0] rsoc);']
    L += [f'    wire {c} = ck;' for c in clocks]
    L.append("    reg ep = 1'b0;  // epoch bit of the bench-driven lane ends (the driver boundary flop loads ea = rst_n)")
    L.append('    always @(posedge ck) ep <= rst_n;')
    L += [wires[n]['decl'] for n in used]
    rep = dict(seeds=[i['name'] for i in keep], clusters=clusters, clocks=clocks, event_lanes={}, zero_lanes=[])
    for n in ext:
        w, lane = wires[n]['width'], wires[n]['lane']
        if lane in EVENT:
            sig, dw = EVENT[lane]
            if w != dw + 1:
                raise SystemExit(f'carve: event lane {lane} width {w} != {dw + 1}')
            L.append(f'    assign {n} = {{ep, {sig}}};  // bench event port, lane {lane}')
            rep['event_lanes'][lane] = n
        else:
            L.append(f"    assign {n} = {w}'d0;  // idle lane end (outside the carve), lane {lane}")
            rep['zero_lanes'].append(dict(net=n, lane=lane, width=w, readers=rd[n]))
    if len(rep['event_lanes']) != 3:
        raise SystemExit(f'carve: event lanes {rep["event_lanes"]}')
    for i in keep:
        L += i['text']

    def seg(lane, end):
        c = [n for n in used if wires[n]['lane'] == lane]
        if end == 'src':
            c = [n for n in c if n in drv and any(x[0] == lane.split('__')[0] for x in drv[n])]
        else:
            c = [n for n in c if n in rd and any(x[0] == end for x in rd[n])]
        if len(c) != 1:
            raise SystemExit(f'carve: observation {lane} at {end}: {c}')
        return c[0]
    obs = {}
    for k in range(4):
        obs[f'cw_n{k}'] = seg(f'sl_W5_hc{k}__cwn{k}', 'src')
        L.append(f'    assign cw_n{k} = {obs[f"cw_n{k}"]}[515:0];')
    obs['rs'] = seg('c_W5_tn_00__rsn', 'sl_W5_hc1')
    obs['rsc'] = seg('c_W5_tn_00__rsn', 'src')
    if clusters == 'both':
        obs['rs_o'] = seg('c_W5_tf_00__rsf', 'sl_W5_hc1')
        obs['rsoc'] = seg('c_W5_tf_00__rsf', 'src')
    for k in ('rs', 'rs_o', 'rsc', 'rsoc'):
        L.append(f'    assign {k} = {obs[k]}[513:0];' if k in obs else f"    assign {k} = 514'd0;  // far cluster not carved")
    L.append('endmodule')
    (out / 'xt1b_carve.v').write_text('\n'.join(L) + '\n')
    rep['observe'] = obs
    B = ['// ROM_TILE binding of the carved cluster partitions (ROM_TILE = 16 cid + slot)']
    for i in keep:
        if not i['name'].startswith('c_W5_t'):
            continue
        cid = 2 if i['name'].startswith('c_W5_tn') else 3
        for (r, c) in tiles_of(rtl, i['module']):
            B.append(f'defparam `OT_ROM_BIND_TOP.{i["name"]}.u_u_t_{r}_{c}.ROM_TILE = {16 * cid + SLOT[(r, c)]};')
    rep['rom_tiles'] = len(B) - 1
    if rep['rom_tiles'] != (32 if clusters == 'both' else 16):
        raise SystemExit(f'carve: {rep["rom_tiles"]} ROM tiles')
    (out / 'rom_bind_xt1b.vh').write_text('\n'.join(B) + '\n')
    (out / 'carve.json').write_text(json.dumps(rep, indent=1) + '\n')
    return rep, sorted({i['module'] for i in keep})


# TB = STEWARD-TOKh tb_xt1b (log lines unchanged for xt1n_bench.py) + the schedule mutant (+SMOKE_MUT_SKEW=k delays the
# hr lane end k cycles vs cmd / tl; HRGO is still logged at the bench event time, so the check reference is unchanged).
TB = r'''`timescale 1ns/1ps
// GENERATED by tools/die_plan/bind_smoke.py (CAL-AUTO): tb_xt1b (STEWARD-TOKh) + schedule mutant +SMOKE_MUT_SKEW=k (hr lane k cycles late)
module tb_xt1b (input wire ck);
    reg rst_n = 1'b0;
    reg  [115:0]  cmd0;
    reg  [452:0]  hr0;
    reg  [1087:0] swi;
    reg  [452:0]  hr_dl [0:15];
    integer mut, k;
    wire [452:0]  hr_drv = (mut == 0) ? hr0 : hr_dl[mut];
    wire [515:0]  cw_n0, cw_n1, cw_n2, cw_n3;
    wire [513:0]  rs, rs_o, rsc, rsoc;
    xt1b_carve u_d (.ck(ck), .rst_n(rst_n), .cmd0(cmd0), .hr0(hr_drv), .swi(swi), .cw_n0(cw_n0), .cw_n1(cw_n1),
        .cw_n2(cw_n2), .cw_n3(cw_n3), .rs(rs), .rs_o(rs_o), .rsc(rsc), .rsoc(rsoc));
`define OT_ROM_BIND_TOP tb_xt1b.u_d
`include "rom_bind_xt1b.vh"
    integer fd, lg, cyc, ncyc, ec, ep, r, pre = 0, nrst;
    reg [1087:0] ev;
    reg have, hdf, stf, rsf, rof;
    reg [1023:0] evf, lgf;
    wire [3:0] cwgo = {cw_n3[0], cw_n2[0], cw_n1[0], cw_n0[0]};
    task automatic apply(input integer p, input [1087:0] v);
        begin
            if (p == 0) cmd0 = v[115:0];
            else if (p == 1) hr0 = v[452:0];
            else if (p == 2) swi = v;
            else $fatal(1, "bad port %0d", p);
        end
    endtask
    initial begin
        if (!$value$plusargs("EV=%s", evf)) $fatal(1, "+EV");
        if (!$value$plusargs("LOG=%s", lgf)) $fatal(1, "+LOG");
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 4000;
        if (!$value$plusargs("NRST=%d", nrst)) nrst = 16;
        if (!$value$plusargs("SMOKE_MUT_SKEW=%d", mut)) mut = 0;
        if (mut < 0 || mut > 15) $fatal(1, "SMOKE_MUT_SKEW 0..15");
        for (k = 0; k < 16; k = k + 1) hr_dl[k] = 0;
        fd = $fopen(evf, "r"); lg = $fopen(lgf, "w");
        cmd0 = 0; hr0 = 0; swi = 0; cyc = 0; hdf = 0; stf = 0; rsf = 0; rof = 0;
        r = $fscanf(fd, "%d %d %h\n", ec, ep, ev); have = (r == 3);
    end
    always @(negedge ck) begin
        if (pre < nrst) begin pre = pre + 1; if (pre == nrst) rst_n = 1'b1; end
        else begin
            if (hr0[452]) $fdisplay(lg, "%0d HRGO", cyc);
            if (hr0[1])   $fdisplay(lg, "%0d HRXPF", cyc);
            if (|cwgo)    $fdisplay(lg, "%0d CWGO %h", cyc, cwgo);
            if (rs[512] || rs[513]) $fdisplay(lg, "%0d RS %0d %h", cyc, rs[513], rs[511:0]);
            if (rs_o[512] || rs_o[513]) $fdisplay(lg, "%0d RSO %0d %h", cyc, rs_o[513], rs_o[511:0]);
            if (rsc[512] || rsc[513]) $fdisplay(lg, "%0d RSC %0d", cyc, rsc[513]);
            if (rsoc[512] || rsoc[513]) $fdisplay(lg, "%0d RSOC %0d", cyc, rsoc[513]);
            if (u_d.sl_W5_ctl.x_hc0_i_q[0] && !hdf) begin $fdisplay(lg, "%0d FAULT heads", cyc); hdf = 1; end
            if (u_d.sl_W5_stm.w_core_stm_fault && !stf) begin $fdisplay(lg, "%0d FAULT stream", cyc); stf = 1; end
            if (rs[513] && !rsf) begin $fdisplay(lg, "%0d FAULT near_cluster", cyc); rsf = 1; end
            if (rs_o[513] && !rof) begin $fdisplay(lg, "%0d FAULT far_cluster", cyc); rof = 1; end
            cmd0 = 0; hr0 = 0; swi = 0;
            while (have && ec == cyc) begin
                apply(ep, ev);
                r = $fscanf(fd, "%d %d %h\n", ec, ep, ev); have = (r == 3);
            end
            if (have && ec < cyc) $fatal(1, "event file not sorted at cycle %0d", ec);
            for (k = 15; k > 0; k = k - 1) hr_dl[k] = hr_dl[k - 1];
            hr_dl[0] = hr0;
            cyc = cyc + 1;
            if (cyc >= ncyc) begin
                $fdisplay(lg, "%0d END hd_fault %0d stm_fault %0d near_fault %0d far_fault %0d mut %0d", cyc,
                          u_d.sl_W5_ctl.x_hc0_i_q[0], u_d.sl_W5_stm.w_core_stm_fault, rsf, rof, mut);
                $fclose(lg);
                $finish;
            end
        end
    end
endmodule
'''


# --------------------------------------------------------------------------------------------- source closure
INCL = re.compile(r'^\s*`include\s+"([^"]+)"', re.M)
MACRO_DIRS = ['physical/asap7_memory_macros_v2', 'physical/asap7_memory_macros']


def src_tree(rev: str, repo: Path, roots) -> Path:
    """the as-built source revision as a file tree (git archive of the RTL roots, cached per commit)."""
    full = subprocess.run(['git', '-C', str(repo), 'rev-parse', rev + '^{commit}'], capture_output=True, text=True)
    if full.returncode:
        raise SystemExit(f'unknown --src-rev {rev}')
    d = Path(os.environ.get('CAL_SMOKE_CACHE_ROOT', '/home/ubuntu/scratch/cal-auto-smoke')) / f'src_{full.stdout.strip()[:12]}'
    if not (d / '.complete').exists():
        d.mkdir(parents=True, exist_ok=True)
        # HDL sources only (the macro dirs also hold LEF/LIB/GDS views)
        ls = subprocess.run(['git', '-C', str(repo), 'ls-tree', '-r', '--name-only', full.stdout.strip(), '--'] +
                            sorted({r.rstrip('/') for r in roots}), capture_output=True, text=True).stdout.split()
        ls = [f for f in ls if f.endswith(('.sv', '.v', '.svh', '.vh'))]
        lst = d / '.files'
        lst.write_text('\n'.join(ls) + '\n')
        r = subprocess.run(f'git -C {shlex.quote(str(repo))} archive {full.stdout.strip()} -- $(cat {lst}) | tar -x -C {d}',
                           shell=True, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f'git archive {rev}: {r.stderr[:300]}')
        (d / '.complete').write_text(full.stdout)
    return d


class Sources:
    """module -> file resolution with the BINDER's own resolver (tools/die_plan/bind_elab.py module_index / pick /
    closure, the index + preference list the bind verify lint used): <bound>/rtl first, then the as-built recipe's
    prefer / portbind_prefer files, then the hard-macro behavioural models (v2, v1), then the rtl_roots index."""

    def __init__(self, bound: Path, asbuilt: Path, rev: str, repo: Path):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import bind_elab as E
        self.E = E
        ab = json.loads(asbuilt.read_text())
        roots = ab.get('rtl_roots', ['rtl'])
        self.base = src_tree(rev, repo, roots + MACRO_DIRS + ab.get('files', []) + ab.get('prefer', []) +
                             ab.get('portbind_prefer', []))
        brtl = sorted(str(f) for f in (bound / 'rtl').glob('*.sv'))
        self.idx = E.module_index(roots, ab.get('files', []) + brtl, self.base)
        self.prefer = brtl + [str(self.base / f) for f in ab.get('prefer', []) + ab.get('portbind_prefer', [])] + \
            [str(self.base / d) for d in MACRO_DIRS]
        self.defines = ab.get('defines', [])
        self.bound = bound

    def bodies(self, f, cache={}):
        """{module: body} of one file, parsed once (bind_elab.closure re-strips the file per module: quadratic on the
        20 MB generated slice netlists)."""
        if f not in cache:
            t = self.E._strip(Path(f).read_text(errors='replace'))
            out = {}
            for m in re.finditer(r'^\s*(?:\(\*[^\n]*?\*\)\s*)?module\s+([A-Za-z_][A-Za-z0-9_$]*)\b(.*?)\bendmodule\b', t, re.S | re.M):
                out.setdefault(m.group(1), m.group(2))
            cache[f] = out
        return cache[f]

    def closure(self, mods):
        """= bind_elab.closure (same pick, same 'a tool reads the whole file' rule), with per-file parse caching."""
        E, seen, files, missing, todo = self.E, set(), [], set(), list(mods)
        while todo:
            n = todo.pop()
            if n in seen:
                continue
            seen.add(n)
            f, _ = E.pick(self.idx, n, self.prefer)
            if f is None:
                missing.add(n)
                continue
            b = self.bodies(f)
            if f not in files:
                files.append(f)
                for body in b.values():
                    todo += sorted(E.instantiated(body, self.idx))
            todo += sorted(E.instantiated(b.get(n, ''), self.idx))
        missing = sorted(missing)
        fs, amb = set(files), {}
        for m in seen:
            if len(self.idx.get(m, [])) > 1:
                f, a = self.E.pick(self.idx, m, self.prefer)
                if a and f in fs:
                    amb[m] = self.idx[m]
        return files, amb, missing

    def includes(self, files):
        inc, dirs, todo = [], set(), list(files)
        while todo:
            f = todo.pop()
            for m in INCL.finditer(Path(f).read_text(errors='replace')):
                name = m.group(1)
                if name == 'rom_bind_xt1b.vh':
                    continue
                cand = Path(f).parent / name
                if not cand.exists():
                    hit = sorted(self.base.rglob(name), key=lambda p: len(str(p)))
                    if not hit:
                        raise SystemExit(f'`include "{name}" (from {f}) not found under {self.base}')
                    cand = hit[0]
                d = str(cand)[:-len(name) - 1]
                dirs.add(d)
                if str(cand) not in inc:
                    inc.append(str(cand))
                    todo.append(str(cand))
        return inc, sorted(dirs)


def stage_sources(S: Sources, files, incs, incdirs, work: Path):
    def rel(f):
        f = Path(f)
        if f.is_relative_to(S.bound):
            return Path('src/bound') / f.relative_to(S.bound)
        return Path('src') / f.relative_to(S.base)
    if (work / 'src').exists():
        shutil.rmtree(work / 'src')
    for f in list(files) + list(incs):
        dst = work / rel(f)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, dst)
    return [str(rel(f)) for f in files], [str(rel(Path(d) / 'x').parent) for d in incdirs]


RUN_SH = r'''#!/bin/bash
# GENERATED by tools/die_plan/bind_smoke.py (CAL-AUTO): qwen_compute xt1 smoke = build (cached by carve sha) + nominal + mutant.
set -u
W=$(cd "$(dirname "$0")" && pwd); cd $W
export PATH=__VERILATOR__:$PATH
verilator --version | grep -q 5.050 || { echo "RESULT SMOKE BUILD_FAIL need verilator 5.050"; exit 2; }
KEY=$(cat carve/xt1b_carve.v carve/tb_smoke.sv carve/rom_bind_xt1b.vh build_files.f build_inc.f defines.f $(sed "s|^|$W/|" build_files.f) | sha256sum | cut -c1-16)
OBJ=$W/obj_$KEY
T0=$(date +%s)
if [ ! -x $OBJ/Vtb ]; then
  rm -rf $W/obj_*
  INC=$(sed "s|^|+incdir+$W/|" build_inc.f)
  FILES=$(sed "s|^|$W/|" build_files.f)
  /usr/bin/time -v -o build.time verilator --cc --exe --build -j __JOBS__ --build-jobs __BJOBS__ --output-groups __GROUPS__ \
    -CFLAGS -O0 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
    -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --x-assign 0 --x-initial 0 \
    $(cat defines.f) --top-module tb_xt1b --prefix Vtb -Mdir $OBJ +incdir+$W/carve $INC \
    $W/bench/main2.cpp $FILES carve/xt1b_carve.v carve/tb_smoke.sv > build.log 2>&1
  if [ ! -x $OBJ/Vtb ]; then echo "RESULT SMOKE BUILD_FAIL"; grep -m20 %Error build.log; exit 2; fi
  BUILT=1
else
  BUILT=0
fi
T1=$(date +%s)
python3 bench/xt1_bench.py gen --gold inputs/gold_near.json --out ev.txt --mode nominal --lead 8 --gap 4 > gen.out 2>&1 \
  || { echo "RESULT SMOKE GEN_FAIL"; tail -5 gen.out; exit 2; }
GF=inputs/gold_far.json; [ -f $GF ] || GF=inputs/gold_near.json
for m in 0 __MUT__; do
  /usr/bin/time -v -o sim_m$m.time $OBJ/Vtb +EV=$W/ev.txt +LOG=$W/log_m$m.txt +NCYC=__NCYC__ +OT_ROM_DIR=$W/inputs/masks \
     +SMOKE_MUT_SKEW=$m > sim_m$m.out 2>&1; echo "sim rc=$?" >> sim_m$m.out
  [ -f log_m$m.txt ] || : > log_m$m.txt
  python3 bench/xt1n_bench.py check --gold-near inputs/gold_near.json --gold-far $GF --log log_m$m.txt --mode nominal \
     --lead 8 --gap 4 > check_m$m.txt 2>&1
  echo "[mut=$m] $(grep -h '^RESULT' check_m$m.txt | tail -1)"
done
T2=$(date +%s)
echo "TIMES built=$BUILT build_s=$((T1-T0)) sim_s=$((T2-T1)) obj=$OBJ"
'''


def qc_prepare(a, work: Path):
    bound = a.bound
    top = bound / 'rtl' / 'qwen_compute_bound_top.sv'
    if not top.exists():
        raise SystemExit(f'no bound top {top}')
    rep, mods = qc_carve(top, bound / 'rtl', work / 'carve', a.clusters)
    (work / 'carve' / 'tb_smoke.sv').write_text(TB)
    S = Sources(bound, a.asbuilt, a.src_rev, a.repo)
    files, amb, missing = S.closure(mods)
    if missing:
        raise SystemExit(f'closure: modules without a source {missing[:10]}')
    incs, incdirs = S.includes(files)
    flist, ilist = stage_sources(S, files, incs, incdirs, work)
    (work / 'build_files.f').write_text('\n'.join(flist) + '\n')
    (work / 'build_inc.f').write_text(''.join(d + '\n' for d in ilist))
    (work / 'defines.f').write_text(''.join(f'+define+{d}\n' for d in S.defines))
    bench = work / 'bench'
    bench.mkdir(exist_ok=True)
    # bench scripts + C++ main from the same source revision (xhead helpers xt1_bench imports come along)
    ls = subprocess.run(['git', '-C', str(a.repo), 'ls-tree', '--name-only', a.src_rev, 'rtl/test/qwen_dv/xhead/'],
                        capture_output=True, text=True).stdout.split()
    for f in ['rtl/test/qwen_dv/main2.cpp'] + [x for x in ls if x.endswith('.py')]:
        r = subprocess.run(['git', '-C', str(a.repo), 'show', f'{a.src_rev}:{f}'], capture_output=True)
        if r.returncode:
            raise SystemExit(f'bench file {f} not in {a.src_rev}')
        (bench / Path(f).name).write_bytes(r.stdout)
    run = (RUN_SH.replace('__VERILATOR__', VERILATOR).replace('__JOBS__', str(a.jobs)).replace('__BJOBS__', str(a.build_jobs)).replace('__GROUPS__', str(a.output_groups))
           .replace('__NCYC__', str(a.ncyc)).replace('__MUT__', str(a.mut_skew)))
    (work / 'run_smoke.sh').write_text(run)
    (work / 'run_smoke.sh').chmod(0o755)
    meta = dict(carve=rep, closure_files=len(flist), files=flist, includes=[str(Path(i).relative_to(S.base)) for i in incs],
                incdirs=ilist, defines=S.defines, ambiguous={k: [str(x) for x in v] for k, v in amb.items()},
                unresolved_modules=missing, top_sha256=sha256(top), asbuilt=str(a.asbuilt), src_tree=str(S.base))
    (work / 'stage.json').write_text(json.dumps(meta, indent=1) + '\n')
    return meta


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, text=True, capture_output=True, **kw)


def qc_inputs(work: Path, clusters: str):
    """gold + masks of the TOKe-QWM xt1 record (gold2) -> work/inputs (cached locally)."""
    cache = Path(os.environ.get('CAL_SMOKE_CACHE', '/home/ubuntu/scratch/cal-auto-smoke/xt1_inputs'))
    if not (cache / 'gold_far.json').exists():
        cache.mkdir(parents=True, exist_ok=True)
        host, path = XT1_INPUTS.split(':')
        for src, dst in ((f'{path}/prep_c2/gold.json', 'gold_near.json'), (f'{path}/prep_c3/gold.json', 'gold_far.json'),
                         (f'{path}/masks_fixed/', 'masks/')):
            r = sh(f'rsync -aL -e "ssh -o ControlPath=none" {host}:{src} {cache}/{dst}')
            if r.returncode:
                raise SystemExit(f'fetch {src}: {r.stderr[:300]}')
    inp = work / 'inputs'
    if inp.exists():
        shutil.rmtree(inp)
    shutil.copytree(cache, inp)
    if clusters == 'near':
        (inp / 'gold_far.json').unlink()


def parse_run(out: str, clusters: str):
    res = {}
    for ln in out.splitlines():
        m = re.match(r'\[mut=(\d+)\] (.*)', ln)
        if m:
            res[int(m.group(1))] = m.group(2)
    tm = re.search(r'TIMES built=(\d) build_s=(\d+) sim_s=(\d+)', out)

    def ok(line):
        if not line or 'XT1N' not in line:
            return False
        mm = re.search(r'near=(\d+)/(\d+) far=(\d+)/(\d+)', line)
        if not mm:
            return False
        n, nt, f, ft = map(int, mm.groups())
        return n == nt and n > 0 and (clusters == 'near' or (f == ft and f > 0))
    return res, ok, tm


def run_qc(a):
    work = a.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    meta = qc_prepare(a, work)
    qc_inputs(work, a.clusters)
    tag = work.name
    remote = f'{REMOTE_ROOT}/{tag}'
    cmd = f'ot-run --mem {a.mem} --threads {a.jobs} --disk 30 --dir {remote} -- bash {remote}/run_smoke.sh'
    rep = dict(schema=SCHEMA, die='qwen_compute', bound=str(a.bound), bound_top_sha256=meta['top_sha256'],
               constants=str(a.constants) if a.constants else None,
               constants_sha256=sha256(a.constants) if a.constants else None,
               vehicle=dict(name='xt1 carve (STEWARD-TOKh/TOKi) generated by bind_smoke.py', clusters=a.clusters,
                            partitions=meta['carve']['seeds'], rom_tiles=meta['carve']['rom_tiles'],
                            closure_files=meta['closure_files'], unresolved_modules=meta['unresolved_modules'],
                            ambiguous_modules=sorted(meta['ambiguous']), src_rev=a.src_rev,
                            bench='xt1_bench gen nominal lead 8 gap 4 -> xt1n_bench check (record gold c2/c3, masks_fixed)',
                            mutant=f'+SMOKE_MUT_SKEW={a.mut_skew} (hr lane end {a.mut_skew} cycle late vs cmd/tl)'),
               cycles=a.ncyc, command=cmd)
    if a.constants:
        rep['constants_note'] = ('the bound top carries the regenerated RTL parameters (bind param_regen); xt1 uses no '
                                 'compiler constant beyond lead/gap, so the file is recorded, not consumed')
    if not a.submit:
        print(f'staged {work} ({meta["closure_files"]} files); submit with:\n  rsync -a {work}/ <host>:{remote}/ && {cmd}')
        return rep, None
    pick = sh(f'ot-run --pick --mem {a.mem} --threads {a.jobs} --disk 30 --dir /srv/opentallas-scratch -- true')
    m = re.search(r'->\s*(ot-\S+)', pick.stdout + pick.stderr)
    if not m:
        raise SystemExit(f'ot-run --pick: no host\n{pick.stdout[-800:]}{pick.stderr[-800:]}')
    host = m.group(1)
    r = sh(f'ssh -o ControlPath=none {host} mkdir -p {remote} && '
           f'rsync -a --delete --exclude "obj_*" -e "ssh -o ControlPath=none" {work}/ {host}:{remote}/')
    if r.returncode:
        raise SystemExit(f'stage to {host}: {r.stderr[:400]}')
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    out = p.stdout
    (work / 'otrun.log').write_text(p.stdout + '\n--- stderr\n' + p.stderr)
    sh(f'rsync -a -e "ssh -o ControlPath=none" --include "*.time" --include "*.out" --include "check_*" --include "log_*" '
       f'--include "build.log" --exclude "*" {host}:{remote}/ {work}/results/')
    res, ok, tm = parse_run(out, a.clusters)
    peak = None
    bt = work / 'results' / 'build.time'
    if bt.exists():
        mm = re.search(r'Maximum resident set size \(kbytes\): (\d+)', bt.read_text())
        peak = round(int(mm.group(1)) / 1048576, 1) if mm else None
    nominal, mutant = res.get(0), res.get(a.mut_skew)
    if 'BUILD_FAIL' in out or nominal is None:
        verdict = 'BUILD_FAIL'
    else:
        verdict = 'PASS' if ok(nominal) and not ok(mutant) else 'FAIL'
    rep.update(host=host, run_dir=f'{host}:{remote}', otrun_exit=p.returncode,
               runs=dict(nominal=nominal, mutant=mutant), verdict=verdict,
               gate_rule='nominal near (and far) words exact AND mutant not exact',
               build_cached=(tm.group(1) == '0') if tm else None,
               build_s=int(tm.group(2)) if tm else None, sim_s=int(tm.group(3)) if tm else None,
               wall_s=round(time.time() - t0), peak_build_gb=peak)
    if verdict == 'FAIL' and ok(mutant):
        rep['note'] = 'mutant PASSED: the bench does not see a one-cycle hr skew -> gate not sensitive (fix the mutant)'
    elif verdict == 'FAIL' and not ok(nominal):
        rep['note'] = 'nominal FAIL: the bound top (with its regenerated constants) does not compute the record stage'
    return rep, verdict


def run_kv(a):
    """KV: no runnable bench vehicle on a bound top yet.  Static: every ECTL K round trip lands at one depth (the guard
    of kv_regen36) and the bind's param_regen applied without error.  Verdict PENDING (not a functional smoke)."""
    rep = dict(schema=SCHEMA, die='qwen_kvsys', bound=str(a.bound), verdict='PENDING',
               note='no runnable KV token-stage bench on a bound top (STEWARD-TOKi kv2 = static audit only); static '
                    'checks below are recorded, they are NOT the functional gate')
    top = a.bound / 'rtl' / 'qwen_kvsys_bound_top.sv'
    if top.exists():
        rep['bound_top_sha256'] = sha256(top)
    pr = a.bound / 'param_regen.json'
    if pr.exists():
        d = json.loads(pr.read_text())
        rec = d.get('record', {})
        rep['static'] = dict(param_regen_changed=len(d.get('changed', [])), applied=rec.get('applied'),
                             measured_RT=rec.get('measured_RT'),
                             open_blockers=[b.get('param') for b in rec.get('open_blockers', [])])
    if a.constants:
        rep['constants_sha256'] = sha256(a.constants)
    return rep, 'PENDING'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--die', required=True, choices=('qwen_compute', 'qwen_kvsys', 'hbm', 's81'))
    ap.add_argument('--bound', required=True, type=Path, help='bind output dir (rtl/, bind.f, param_regen.json)')
    ap.add_argument('--constants', type=Path, help='regen_constants.py JSON for this bind (recorded with its sha)')
    ap.add_argument('--work', type=Path, help='local staging dir (default /home/ubuntu/scratch/cal-auto-smoke/<die>_<sha8>)')
    ap.add_argument('--src-rev', default=None, help='git revision of the as-built source tree the bind.f paths refer to')
    ap.add_argument('--repo', type=Path, default=REPO)
    ap.add_argument('--asbuilt', type=Path, help='the bind as-built recipe JSON (rtl_roots / files / prefer / defines); '
                    'default: the --asbuilt path named in <bound>/README.md, next to the bind dir')
    ap.add_argument('--clusters', choices=('near', 'both'), default='near',
                    help='near (default: 37 min, 43 GB measured) or both (64 min, 76 GB)')
    ap.add_argument('--ncyc', type=int, default=60 + 1600 * 4)
    ap.add_argument('--mut-skew', type=int, default=1)
    ap.add_argument('--mem', type=int, default=None, help='ot-run --mem GB (default: near 56 / both 90; measured peak 43.4 / 75.8 GB)')
    ap.add_argument('--jobs', type=int, default=32)
    ap.add_argument('--build-jobs', type=int, default=96)
    ap.add_argument('--output-groups', type=int, default=192,
                    help='Verilator C++ unity groups (default 5.050 made ~34 x ~100 MB units: 6 compiles at a time)')
    ap.add_argument('--submit', action='store_true', help='stage to an admitting host and run through ot-run')
    ap.add_argument('--no-report', action='store_true', help='do not write <bound>/smoke/smoke_report.json')
    a = ap.parse_args()
    if a.mem is None:
        a.mem = 56 if a.clusters == 'near' else 90
    a.bound = a.bound.resolve()
    if a.die == 'qwen_compute':
        if not a.src_rev:
            ap.error('--src-rev is required for qwen_compute (the as-built tree bind.f refers to)')
        if a.asbuilt is None:
            m = re.search(r'--asbuilt\s+(\S+\.json)|Recipe\s+(\S+\.json)', (a.bound / 'README.md').read_text()
                          if (a.bound / 'README.md').exists() else '')
            cand = [a.bound / Path(m.group(2)) if m and m.group(2) else None,
                    a.bound.parent / Path(m.group(1)).name if m and m.group(1) else None]
            cand = [c for c in cand if c and c.exists()]
            if not cand:
                ap.error('--asbuilt not given and not found from <bound>/README.md')
            a.asbuilt = cand[0]
        a.asbuilt = a.asbuilt.resolve()
        if a.work is None:
            a.work = Path(f'/home/ubuntu/scratch/cal-auto-smoke/qc_{sha256(a.bound / "rtl" / "qwen_compute_bound_top.sv")[:8]}')
        rep, verdict = run_qc(a)
    elif a.die == 'qwen_kvsys':
        rep, verdict = run_kv(a)
    else:
        rep, verdict = dict(schema=SCHEMA, die=a.die, bound=str(a.bound), verdict='PENDING',
                            note='no bound top / smoke vehicle for this die yet'), 'PENDING'
    if verdict is None:
        return 0
    rep['date'] = time.strftime('%Y-%m-%d %H:%M %Z')
    if not a.no_report:
        (a.bound / 'smoke').mkdir(exist_ok=True)
        (a.bound / 'smoke' / 'smoke_report.json').write_text(json.dumps(rep, indent=1) + '\n')
    runs = rep.get('runs', {})
    print(f'SMOKE {a.die} {verdict} nominal=[{runs.get("nominal")}] mutant=[{runs.get("mutant")}] '
          f'build_s={rep.get("build_s")} sim_s={rep.get("sim_s")} peak_gb={rep.get("peak_build_gb")}')
    return 0 if verdict in ('PASS', 'PENDING') else 1


if __name__ == '__main__':
    sys.exit(main())
