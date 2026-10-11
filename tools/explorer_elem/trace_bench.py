#!/usr/bin/env python3
"""Element activity replay, host side (anim-1011 Phase 1; owner decisions 2026-10-10/11: gate-level, everything automatic).

    python3 trace_bench.py --spec spec.json --out <dir>

spec.json (written by tools/explorer_elem/trace_local.py): job, element, block, commit, bench {mode cmd|workdir, ...},
ports / top_params / tree / modules (the element's rtl.json), flops (DB clock-tree leaf names), netlist (the routed
6_final.v on this host), cell_models / cell_kinds (lib2v.py output), mem limits.

  1. capture: run the bench's positive case under strace until its first simulator compile that defines the closed
     block (or a renamed copy) starts its model; stop the bench (workdir mode: the compile line of a prior build's
     V*__verFiles.dat).  An Icarus compile is translated to Verilator (--binary --timing).
  2. RTL pass (whole bench): bind probe on the block, instance chosen by the closure's top parameters; logs every port
     transaction (auto-detected handshake groups) and the RTL parameters of every macro model instance.  From it:
     L (first input -> first output), II (median input spacing), the work unit (first input .. last output of the first
     output burst) and the window: reset-settle + max(ceil(L/II)+1 items, one work unit), floor 32, cap 8192, above
     the cap the first work unit then sampled steady-state segments with marked jumps.
  3. gate-level pass (whole bench): the selected instance is swapped for the routed netlist (top renamed ot_gl_<block>),
     standard cells from lib2v.py (zero delay), macros from the bench's own model with per-instance string parameters
     looked up by path (+OT_ANIM_MTAB).  The probe logs the same transactions (netlist exactness vs the RTL pass and the
     bench's verdict lines) and, over the window, the exact state of every placed flop and ICG enable latch each cycle
     through DPI: flop-xor-rle chunks of 256 cycles, zlib.
Writes <out>/elem_trace.json (opentallas.elem_trace.v1) and <out>/chunks/c*.bin; logs in <out>.
"""
import argparse, base64, collections, hashlib, json, math, os, re, shlex, signal, subprocess, sys, threading, time
from pathlib import Path

LOG = None


def log(*a):
    s = '[trace %s] %s' % (time.strftime('%H:%M:%S'), ' '.join(str(x) for x in a))
    print(s, flush=True)
    if LOG:
        with open(LOG, 'a') as f: f.write(s + '\n')


# ---------------------------------------------------------------------------------------------- port classification
CLOCK_RE = re.compile(r'^(clk|clock|aclk|ck|clk_i|i_clk|core_clk)$|(^|_)clk$', re.I)
RESET_RE = re.compile(r'(^|_)(rst|reset|rstn|resetn|arst|srst|nrst)(_|$|n|b)', re.I)
RESET_LOW_RE = re.compile(r'(rst|reset)_?n|(^|_)n_?rst|_n(_|$)|(rst|reset)_?b(_|$)', re.I)
VALID_STRONG = re.compile(r'^(?P<s>.*?)_?(valid|vld)$|^(?P<t>.+?)_v$', re.I)
READY_SUF = ('_ready', '_rdy', '_r', 'ready', 'rdy')
CREDIT_SUF = ('_credit', '_cr', 'credit', 'cr', '_crd')
CONFIG_RE = re.compile(r'^(cfg|csr|conf|config|prog|init|ld|load|wr_cfg)(_|$)', re.I)


def classify_ports(ports, clock_port=None):
    """handshake groups of a port list [[name, dir, bits]]: valid by name (stem_v / *_valid / *_vld), or by structure
    (stem + 'v' with >= 2 other same-direction ports starting with stem); ready / credit by stem + suffix in the other
    direction; every other 1-bit non-clock, non-reset port is a 'level' lane.  Returns (clock, reset, groups, levels)."""
    byname = {p[0]: p for p in ports}
    clock = clock_port if clock_port in byname else next((p[0] for p in ports if p[1] == 'i' and p[2] == 1 and CLOCK_RE.search(p[0])), None)
    reset = next((p[0] for p in ports if p[1] == 'i' and p[2] == 1 and p[0] != clock and RESET_RE.search(p[0])), None)
    used = {clock, reset}
    groups = []
    for name, d, w in ports:
        if name in used: continue
        stem, how = None, None
        m = VALID_STRONG.match(name)
        if m:
            stem = m.group('s') if m.group('s') is not None else m.group('t'); how = 'name'
        elif len(name) >= 2 and name.endswith('v') and not name.endswith('_v'):
            st = name[:-1]
            peers = [p for p in ports if p[0] != name and p[1] == d and p[0].startswith(st)]
            if len(peers) >= 2: stem, how = st, 'structure'
        if stem is None: continue
        other = 'o' if d == 'i' else 'i'
        ready = next((stem + s for s in READY_SUF if stem + s in byname and byname[stem + s][1] == other and stem + s != name), None)
        credit = next((stem + s for s in CREDIT_SUF if stem + s in byname and byname[stem + s][1] == other), None)
        pre = stem + ('_' if how == 'name' and stem and (stem + '_') in name else '')
        payload = [p[0] for p in ports if p[1] == d and p[0] != name and p[0].startswith(pre) and pre and p[0] not in (ready, credit)]
        groups.append(dict(name=stem or name, valid=name, valid_bits=w, ready=ready, credit=credit, dir=d, how=how, payload=payload,
                           config=bool(CONFIG_RE.match(name))))
        used.update([name, ready, credit] + payload)
    levels = [dict(name=p[0], dir=p[1]) for p in ports if p[2] == 1 and p[0] not in used]
    return clock, reset, groups, levels


# ---------------------------------------------------------------------------------------------- strace capture
def c_unescape(s):
    out = bytearray(); i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            n = s[i + 1]
            if n in 'nrtvfab':
                out += {'n': b'\n', 'r': b'\r', 't': b'\t', 'v': b'\v', 'f': b'\f', 'a': b'\a', 'b': b'\b'}[n]; i += 2
            elif n == 'x':
                out.append(int(s[i + 2:i + 4], 16)); i += 4
            elif n.isdigit():
                j = i + 1
                while j < len(s) and j < i + 4 and s[j] in '01234567': j += 1
                out.append(int(s[i + 1:j], 8) & 255); i = j
            else:
                out += n.encode(); i += 2
        else:
            out += c.encode(); i += 1
    return out.decode('utf-8', 'replace')


STR_RE = re.compile(r'"((?:[^"\\]|\\.)*)"(\.\.\.)?')


def parse_str_array(s, start):
    """['"a", "b"'] starting at s[start] == '[' -> (list, end index)"""
    assert s[start] == '['
    i = start + 1; items = []
    while i < len(s):
        if s[i] == ']': return items, i + 1
        if s[i] == '"':
            m = STR_RE.match(s, i)
            items.append(c_unescape(m.group(1))); i = m.end()
        else:
            i += 1
    return items, i


EXEC_RE = re.compile(r'^(\d+)\s+execve\("((?:[^"\\]|\\.)*)", ')
CHDIR_RE = re.compile(r'^(\d+)\s+chdir\("((?:[^"\\]|\\.)*)"\)\s+=\s+0')
CLONE_RE = re.compile(r'^(\d+)\s+(?:clone3?|vfork|fork)\(.*\)\s+=\s+(\d+)')


class Tracker:
    def __init__(self, cwd0):
        self.cwd = {}; self.cwd0 = cwd0; self.execs = []; self.pending = {}

    def feed(self, ln):
        m = re.match(r'^(\d+)\s+<\.\.\. (\w+) resumed>(.*)$', ln)
        if m:   # an interleaved call finishes: rebuild the full line
            pid, call = int(m.group(1)), m.group(2)
            head = self.pending.pop((pid, call), None)
            if head is None: return None
            ln = head + m.group(3)
        m = re.match(r'^(\d+)\s+(\w+)\((.*) <unfinished \.\.\.>$', ln)
        if m:
            self.pending[(int(m.group(1)), m.group(2))] = ln[:ln.rindex(' <unfinished ...>')]; return None
        m = CLONE_RE.match(ln)
        if m:
            self.cwd[int(m.group(2))] = self.cwd.get(int(m.group(1)), self.cwd0); return None
        m = CHDIR_RE.match(ln)
        if m:
            pid = int(m.group(1)); p = c_unescape(m.group(2))
            self.cwd[pid] = os.path.normpath(os.path.join(self.cwd.get(pid, self.cwd0), p)); return None
        m = EXEC_RE.match(ln)
        if m and re.search(r'\)\s+=\s+0\s*$', ln):
            pid = int(m.group(1)); path = c_unescape(m.group(2))
            argv, j = parse_str_array(ln, m.end())
            env = []
            k = ln.find('[', j)
            if k >= 0: env, _ = parse_str_array(ln, k)
            e = dict(pid=pid, path=path, argv=argv, env=env, cwd=self.cwd.get(pid, self.cwd0))
            self.execs.append(e); return e
        return None


SIMC = ('verilator', 'iverilog')


def defined_modules(files, cwd):
    mods = {}
    for f in files:
        p = f if os.path.isabs(f) else os.path.join(cwd, f)
        try: t = open(p, errors='replace').read()
        except OSError: continue
        for m in re.finditer(r'^\s*module\s+(?:automatic\s+)?([A-Za-z_]\w*)', t, re.M):
            mods.setdefault(m.group(1), p)
    return mods


def compile_sources(argv, cwd):
    """source files (sv/v) of a verilator or iverilog argv, following -f / -F / -c command files"""
    out = []
    def walk(args, base):
        i = 0
        while i < len(args):
            a = args[i]
            if a in ('-f', '-F', '-c') and i + 1 < len(args):
                fp = args[i + 1] if os.path.isabs(args[i + 1]) else os.path.join(base, args[i + 1])
                try:
                    toks = shlex.split(open(fp).read(), comments=True)
                    walk(toks, os.path.dirname(fp) if a == '-F' else base)
                except OSError: pass
                i += 2; continue
            if re.search(r'\.(sv|v|svh|vh)$', a) and not a.startswith(('-', '+')):
                out.append(a if os.path.isabs(a) else os.path.join(base, a))
            i += 1
    walk(argv, cwd)
    return out


def block_variants(mods, block):
    """modules that are the block or a renamed copy (prefix_block) the bench compiles"""
    return [m for m in mods if m == block or (m.endswith('_' + block) and len(m) - len(block) <= 12)]


def capture(spec, out):
    b = spec['bench']; block = spec['block']
    cwd = b.get('cwd') or spec['src']
    st = out / 'strace.log'
    cmd = ['strace', '-f', '-qq', '-v', '-s', '1000000', '-e', 'trace=execve,chdir,clone,clone3,vfork,fork',
           '-o', str(st), 'bash', '-c', b['cmd']]
    cmd = ['ot-heavy', '--mem', str(spec.get('capture_mem_gb') or spec.get('mem_gb') or 31), '--'] + cmd
    log('capture: bench', b['label'], 'cwd', cwd); log('  cmd', b['cmd'][:600])
    lf = open(out / 'bench.log', 'w')
    p = subprocess.Popen(cmd, cwd=cwd, stdout=lf, stderr=subprocess.STDOUT, start_new_session=True)
    tr = Tracker(cwd); comp = None; run = None; pos = 0; buf = ''
    t0 = time.time()
    while True:
        alive = p.poll() is None
        if st.exists():
            with open(st, errors='replace') as f:
                f.seek(pos); chunk = f.read(); pos = f.tell()
            buf += chunk
            lines = buf.split('\n'); buf = lines.pop()
            for ln in lines:
                e = tr.feed(ln)
                if not e: continue
                base = os.path.basename(e['path'])
                if comp is None and base in SIMC + ('verilator_bin',) and not (base == 'verilator_bin' and any(
                        os.path.basename(x['path']) == 'verilator' for x in tr.execs[:-1])):
                    srcs = compile_sources(e['argv'][1:], e['cwd'])
                    mods = defined_modules(srcs, e['cwd'])
                    v = block_variants(mods, block)
                    if v:
                        comp = dict(e, tool='iverilog' if base == 'iverilog' else 'verilator', sources=srcs, variants=v,
                                    variant_files={m: mods[m] for m in v})
                        log('capture: compile', base, 'in', e['cwd'], 'block variants', v)
                    else:
                        log('capture: compile without the block (%d sources) skipped' % len(srcs))
                elif comp is not None and run is None and is_run(e, comp):
                    run = e; log('capture: run', e['path'], e['argv'][1:8])
        if run is not None or not alive:
            break
        time.sleep(1.0)
    if alive:
        try: os.killpg(p.pid, signal.SIGTERM)
        except OSError: pass
        try: p.wait(60)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL); p.wait()
    log('capture: done in %.0f s (bench %s)' % (time.time() - t0, 'stopped at the simulation start' if alive else 'exited rc %s' % p.returncode))
    if comp is None: raise SystemExit('NO_SIM: the bench ran no simulator compile that defines %s' % block)
    if run is None: raise SystemExit('NO_RUN: the compile was seen but the bench never ran the model')
    return comp, run


def mdir_of(argv, cwd):
    for i, a in enumerate(argv):
        if a == '--Mdir' and i + 1 < len(argv): return os.path.normpath(os.path.join(cwd, argv[i + 1]))
        if a.startswith('--Mdir='): return os.path.normpath(os.path.join(cwd, a.split('=', 1)[1]))
    return os.path.join(cwd, 'obj_dir')


def is_run(e, comp):
    base = os.path.basename(e['path'])
    if comp['tool'] == 'iverilog': return base == 'vvp'
    md = mdir_of(comp['argv'][1:], comp['cwd'])
    return os.path.dirname(os.path.normpath(e['path'])) == md and base.startswith('V')


def from_workdir(spec, out):
    """mode workdir: a prior bench build on this host; the compile argv is the 'C' line of its V*__verFiles.dat"""
    wd = Path(spec['bench']['workdir']); block = spec['block']
    cands = sorted(wd.glob('**/V*__verFiles.dat'), key=lambda p: (0 if re.search(r'(^|/)(positive|pass|pos)(/|$)', str(p.relative_to(wd))) else 1, len(str(p))))
    for vf in cands:
        line = next((l for l in vf.read_text(errors='replace').splitlines() if l.startswith('C ')), None)
        if not line: continue
        args = shlex.split(line[2:].strip().strip('"')) if line[2:].strip().startswith('"') else shlex.split(line[2:])
        if len(args) == 1: args = shlex.split(args[0])
        ar, pr = spec['bench'].get('absroot'), spec['bench'].get('prior_root')
        def remap(x):   # a relocated prior build: absolute inputs copied under absroot, the prior directory itself under workdir
            if not x.startswith('/') or os.path.exists(x): return x
            if pr and x.startswith(pr.rstrip('/') + '/'): return str(wd) + x[len(pr.rstrip('/')):]
            if ar and os.path.exists(ar + x): return ar + x
            return x
        args = [remap(x) for x in args]
        md = vf.parent
        # cwd: the directory against which --Mdir resolves to the verFiles directory
        mrel = next((args[i + 1] for i, a in enumerate(args) if a == '--Mdir' and i + 1 < len(args)), 'obj_dir')
        cwd = str(md.parent) if os.path.basename(mrel.rstrip('/')) == md.name else str(md.parent)
        srcs = compile_sources(args, cwd); mods = defined_modules(srcs, cwd); v = block_variants(mods, block)
        if not v: continue
        top = next((args[i + 1] for i, a in enumerate(args) if a == '--top-module' and i + 1 < len(args)), None)
        exe = md / ('V' + top) if top else next(iter(sorted(md.glob('V*[!.]*'))), None)
        # work on a copy (sources and inputs, not the build): the prior bench directory belongs to another stream
        wcopy = out / 'workdir'
        subprocess.run(['rsync', '-a', '--delete', '--exclude', '/' + md.name, cwd + '/', str(wcopy) + '/'], check=True)
        srcs = [str(wcopy / os.path.relpath(s, cwd)) if s.startswith(cwd + '/') else s for s in srcs]
        vfiles = {m: (str(wcopy / os.path.relpath(mods[m], cwd)) if mods[m].startswith(cwd + '/') else mods[m]) for m in v}
        comp = dict(path='verilator', argv=['verilator'] + args, env=list('%s=%s' % kv for kv in os.environ.items()), cwd=str(wcopy), tool='verilator',
                    sources=srcs, variants=v, variant_files=vfiles, verfiles=str(vf), prior_cwd=cwd)
        run = dict(path=str(exe), argv=[str(exe)], env=comp['env'], cwd=str(wcopy))
        log('workdir: compile from', vf, 'variants', v)
        return comp, run
    raise SystemExit('NO_SIM: no Verilator build of %s under %s' % (block, wd))


IV_DROP1 = {'-o', '-T', '-W', '-M', '-m', '-N', '-L', '-p', '-B', '-t'}


def iverilog_to_verilator(argv, cwd):
    """iverilog argv -> verilator --binary --timing argv (top params via -G)"""
    out = ['--binary', '--timing']; top = None
    def walk(args, base):
        nonlocal top
        i = 0
        while i < len(args):
            a = args[i]
            if a in ('-c', '-f') and i + 1 < len(args):
                fp = args[i + 1] if os.path.isabs(args[i + 1]) else os.path.join(base, args[i + 1])
                walk(shlex.split(open(fp).read(), comments=True), base); i += 2; continue
            if a == '-s' and i + 1 < len(args): top = args[i + 1]; out.extend(['--top-module', top]); i += 2; continue
            if a.startswith('-s') and len(a) > 2: top = a[2:]; out.extend(['--top-module', top]); i += 1; continue
            if a == '-D' and i + 1 < len(args): out.append('+define+' + args[i + 1]); i += 2; continue
            if a.startswith('-D'): out.append('+define+' + a[2:]); i += 1; continue
            if a == '-I' and i + 1 < len(args): out.append('+incdir+' + os.path.join(base, args[i + 1])); i += 2; continue
            if a.startswith('-I'): out.append('+incdir+' + os.path.join(base, a[2:])); i += 1; continue
            if a == '-P' and i + 1 < len(args) or a.startswith('-P'):
                v = args[i + 1] if a == '-P' else a[2:]; i += 2 if a == '-P' else 1
                k, _, val = v.partition('='); out.append('-G%s=%s' % (k.split('.')[-1], val)); continue
            if a == '-y' and i + 1 < len(args): out.extend(['-y', os.path.join(base, args[i + 1])]); i += 2; continue
            if a == '-Y' and i + 1 < len(args): out.append('+libext+' + args[i + 1]); i += 2; continue
            if a == '-l' and i + 1 < len(args): out.extend(['-v', os.path.join(base, args[i + 1])]); i += 2; continue
            if a in IV_DROP1 and i + 1 < len(args): i += 2; continue
            if a.startswith(('+define+', '+incdir+', '+libext+')): out.append(a); i += 1; continue
            if a.startswith('-'): i += 1; continue   # -g2012, -Wall, -o<x>, ...
            out.append(a if os.path.isabs(a) else os.path.join(base, a)); i += 1
    walk(argv, cwd)
    return out, top


SUFFIX_RE = re.compile(r'\$_[A-Za-z0-9_]+$|\$\w+$')


def flop_vector(name):
    """placed flop instance name -> (RTL vector path, bit) under the same name mapping the RTL tab uses"""
    n = name.replace('\\', '').strip()
    n = SUFFIX_RE.sub('', n).replace('/', '.')
    n = re.sub(r'_reg$', '', n)
    m = re.match(r'^(.*?)\[(\d+)\]$', n)
    if m and m.group(1): return m.group(1), int(m.group(2))
    return n, 0


def tree_index(tree):
    idx = {}
    def walk(nd):
        idx[nd.get('p', '')] = nd.get('k')
        for c in nd.get('c') or []: walk(c)
    if tree: walk(tree)
    return idx


# ---------------------------------------------------------------------------------------------- probes
DPI_CPP = r'''// GENERATED by tools/explorer_elem/trace_bench.py: activity replay DPI (flop-xor-rle chunks, zlib)
#include "verilated.h"
#include "svdpi.h"
#include <zlib.h>
#include <cstdio>
#include <cstdint>
#include <string>
#include <vector>
extern "C" int ot_anim_trace_on() { Verilated::threadContextp()->traceEverOn(true); return 0; }
static std::string g_dir; static int g_n = 0, g_c0 = -1, g_nc = 0, g_id = 0, g_last = -2; static long g_chg = 0;
static std::vector<uint32_t> g_prev; static std::vector<uint8_t> g_buf; static FILE* g_idx = nullptr;
static void put32(std::vector<uint8_t>& b, uint32_t v) { for (int i = 0; i < 4; i++) b.push_back((v >> (8 * i)) & 255); }
static void varint(uint32_t v) { while (v >= 128) { g_buf.push_back((v & 127) | 128); v >>= 7; } g_buf.push_back(v); }
static void flush() {
    if (g_nc == 0) return;
    std::vector<uint8_t> raw; raw.push_back('O'); raw.push_back('T'); raw.push_back('F'); raw.push_back('1');
    put32(raw, g_n); put32(raw, g_c0); put32(raw, g_nc); raw.insert(raw.end(), g_buf.begin(), g_buf.end());
    uLongf zl = compressBound(raw.size()); std::vector<uint8_t> z(zl);
    compress2(z.data(), &zl, raw.data(), raw.size(), 6);
    char fn[64]; snprintf(fn, sizeof fn, "/c%05d.bin", g_id);
    FILE* f = fopen((g_dir + fn).c_str(), "wb"); fwrite(z.data(), 1, zl, f); fclose(f);
    fprintf(g_idx, "%d %d %d %zu %lu %ld\n", g_id, g_c0, g_nc, raw.size(), (unsigned long)zl, g_chg); fflush(g_idx);
    g_id++; g_nc = 0; g_buf.clear(); g_chg = 0;
}
extern "C" void ot_anim_open(const char* dir, int n) {
    g_dir = dir; g_n = n; g_prev.assign((n + 31) / 32, 0);
    g_idx = fopen((g_dir + "/index.txt").c_str(), "w");
}
extern "C" void ot_anim_sample(int cyc, const svBitVecVal* st, int jump) {
    int W = (g_n + 31) / 32;
    if (g_nc == 256 || jump || cyc != g_last + 1) flush();
    if (g_nc == 0) {   // chunk start: full state bitmap (LSB = flop 0)
        g_c0 = cyc;
        for (int b = 0; b < (g_n + 7) / 8; b++) g_buf.push_back((st[b / 4] >> (8 * (b % 4))) & 255);
    } else {           // changed flops: count, then index gaps
        std::vector<uint32_t> ch;
        for (int w = 0; w < W; w++) {
            uint32_t x = st[w] ^ g_prev[w];
            if (w == W - 1 && (g_n % 32)) x &= (1u << (g_n % 32)) - 1;
            while (x) { int k = __builtin_ctz(x); ch.push_back(32 * w + k); x &= x - 1; }
        }
        varint(ch.size()); uint32_t p = 0; bool first = true;
        for (uint32_t i : ch) { varint(first ? i : i - p - 1); p = i; first = false; }
        g_chg += ch.size();
    }
    for (int w = 0; w < W; w++) g_prev[w] = st[w];
    g_nc++; g_last = cyc;
}
extern "C" void ot_anim_close() { flush(); if (g_idx) fclose(g_idx); g_idx = nullptr; }
'''


def _uncomment(text):
    return re.sub(r'//[^\n]*', '', re.sub(r'/\*.*?\*/', '', text, flags=re.S))


def _balanced(s, i):
    """s[i] == '(' -> index after the matching ')'"""
    d = 0
    for j in range(i, len(s)):
        if s[j] == '(': d += 1
        elif s[j] == ')':
            d -= 1
            if d == 0: return j + 1
    return len(s)


def module_header(text, mod):
    """(parameter block text, port list text) of module <mod>"""
    t = _uncomment(text)
    m = re.search(r'\bmodule\s+(?:automatic\s+)?' + re.escape(mod) + r'\b', t)
    if not m: return '', ''
    i = m.end()
    while i < len(t) and t[i].isspace(): i += 1
    pb = ''
    if t.startswith('#', i):
        j = t.index('(', i); k = _balanced(t, j); pb = t[j + 1:k - 1]; i = k
        while i < len(t) and t[i].isspace(): i += 1
    pl = ''
    if i < len(t) and t[i] == '(':
        k = _balanced(t, i); pl = t[i + 1:k - 1]
        if not re.search(r'\b(input|output|inout)\b', pl):   # non-ANSI: declarations follow in the body
            body = t[k:t.find('endmodule', k)]
            pl = ' '.join(re.findall(r'\b(?:input|output|inout)\b[^;]*;', body)).replace(';', ',')
    return pb, pl


def module_params(text, mod):
    pb, pl = module_header(text, mod)
    names = set(re.findall(r'\bparameter\b(?:\s+(?:integer|int|logic|bit|signed|unsigned|string|real|\[[^\]]*\]))*\s+([A-Za-z_]\w*)', pb))
    names |= set(re.findall(r'(?:,|^)\s*([A-Za-z_]\w*)\s*=', pb))   # parameter lists continued without the keyword
    return names


def module_ports(text, mod):
    pb, pl = module_header(text, mod)
    out = set()
    for part in pl.split(','):
        ids = re.findall(r'[A-Za-z_]\w*', re.sub(r'\[[^\]]*\]', ' ', part))
        ids = [x for x in ids if x not in ('input', 'output', 'inout', 'wire', 'reg', 'logic', 'signed', 'unsigned', 'var', 'bit', 'integer', 'int')]
        if ids: out.add(ids[-1])
    return out


def gen_probe(spec, comp, out, mode, dut_path=None, segments=None, gate=None):
    """mode 'rtl': bind on every block variant, select the instance by the closure's top parameters, log every port
    transaction of the whole run; mode 'gate': bind on ot_gl_<block>, select the instance the RTL pass chose, log the
    same transactions plus handshake lanes and the flop / ICG state vector over the window segments (DPI chunks)."""
    ports = spec['ports']; clock, reset, groups, levels = classify_ports(ports, spec.get('clock_port'))
    if not clock: raise SystemExit('NO_CLOCK: no clock port among %s' % [p[0] for p in ports][:20])
    bits = {p[0]: p[2] for p in ports}
    tp = [(k, str(v)) for k, v in spec.get('top_params') or [] if re.fullmatch(r'-?\d+', str(v))]
    rst = "1'b0" if not reset else ('!%s' if RESET_LOW_RE.search(reset) else '%s') % reset
    fv = []; layout = []
    for g in groups:
        fv.append('(%s%s)' % (g['valid'], (' & {%d{%s}}' % (g['valid_bits'], g['ready'])) if g['ready'] else ''))
        layout.append((g['name'], g['dir'], g['valid_bits'], bool(g['config'])))
    outs = [p for g in groups if g['dir'] == 'o' for p in [g['valid']] + g['payload']]
    hsn = []
    for g in groups:
        for n in (g['valid'], g['ready'], g['credit']):
            if n: hsn.append(n)
    hsn += [l['name'] for l in levels]
    NF = sum(x[2] for x in layout) or 1; NP = sum(bits[p] for p in outs) or 1; NH = sum(bits[n] for n in hsn) or 1
    NST = len(gate['state_expr']) if gate else 1
    segs = segments or []
    seg_cond = ' || '.join('(cyc >= %d && cyc <= %d)' % (a, b) for a, b in segs) or '0'
    seg_start = ' || '.join('(cyc == %d)' % a for a, b in segs) or '0'
    L = ['// GENERATED by tools/explorer_elem/trace_bench.py (%s pass) for %s / %s; do not edit' % (mode, spec['element'], spec['job']),
         'package ot_anim_pkg;',
         '  string owner = "";',
         '  string mtab [string];',
         '  bit mtab_loaded = 0;',
         '  function automatic string norm(input string s); string r = ""; for (int i = 0; i < s.len(); i++) if (s[i] != "\\\\" && s[i] != " ") r = {r, s.substr(i, i)}; return r; endfunction',
         '  function automatic string mparam(input string path, input string key, input string dflt);',
         '    if (!mtab_loaded) begin string fn, p, k, v; int fd; mtab_loaded = 1;',
         '      if ($value$plusargs("OT_ANIM_MTAB=%s", fn)) begin fd = $fopen(fn, "r");',
         '        while (fd != 0 && !$feof(fd)) begin if ($fscanf(fd, "%s %s %s\\n", p, k, v) == 3) mtab[{p, " ", k}] = v; end',
         '        if (fd != 0) $fclose(fd); end',
         '    end',
         '    begin string q = {norm(path), " ", key}; if (mtab.exists(q)) return (mtab[q] == "-" ? "" : mtab[q]); end',
         '    $display("OT_ANIM_MPARAM_MISS %s %s", norm(path), key); return dflt;',
         '  endfunction',
         'endpackage',
         'import "DPI-C" function int ot_anim_trace_on();',
         'import "DPI-C" function void ot_anim_open(input string dir, input int n);',
         'import "DPI-C" function void ot_anim_sample(input int cyc, input bit [%d:0] st, input int jump);' % (NST - 1),
         'import "DPI-C" function void ot_anim_close();',
         'module ot_anim_probe #(parameter int PSEL = 1) (input clk, input rst_act, input [%d:0] fv, input [%d:0] pay, input [%d:0] hs, input [%d:0] st);' % (NF - 1, NP - 1, NH - 1, NST - 1),
         '  int cyc = 0; int rst_seen = -1; bit sel = 0; int ft = 0, fh = 0; logic [%d:0] hs_q;' % (NH - 1),
         '  initial begin',
         '    $display("OT_ANIM_INST %m PSEL=%0d", PSEL);',
    ]
    if mode == 'rtl':
        L += ['    if (PSEL != 0 && ot_anim_pkg::owner == "") begin ot_anim_pkg::owner = $sformatf("%m"); sel = 1; end']
    else:
        L += ['    if (ot_anim_pkg::norm($sformatf("%%m")) == ot_anim_pkg::norm("%s.u_ot_anim_probe")) begin sel = 1; ot_anim_pkg::owner = $sformatf("%%m"); end' % dut_path]
    L += ['    if (sel) begin $display("OT_ANIM_SEL %%m"); ft = $fopen("%s"); fh = $fopen("%s"); %s end' % (
              out / ('txn_%s.log' % mode), out / ('hs_%s.log' % mode), ('ot_anim_open("%s", %d);' % (out / 'chunks', NST)) if mode == 'gate' else ''),
          '  end',
          '  always @(posedge clk) cyc <= cyc + 1;',
          '  always @(negedge clk) if (sel) begin',
          '    if (rst_seen < 0 && !rst_act) begin rst_seen = cyc; $fwrite(ft, "R %0d\\n", cyc); end',
          '    if (|fv) $fwrite(ft, "%0d %h %h\\n", cyc, fv, pay);']
    if mode == 'gate':
        L += ['    if (%s) begin' % seg_cond,
              '      if (hs !== hs_q || (%s)) begin $fwrite(fh, "%%0d %%h\\n", cyc, hs); hs_q = hs; end' % seg_start,
              '      ot_anim_sample(cyc, st, (%s) ? 1 : 0);' % seg_start,
              '    end']
    L += ['  end',
          '  final if (sel) begin $fwrite(ft, "E %%0d\\n", cyc); $fclose(ft); $fclose(fh); %s end' % ('ot_anim_close();' if mode == 'gate' else ''),
          'endmodule']
    cat = lambda xs: '{%s}' % ', '.join(xs) if xs else "1'b0"
    binds = []
    targets = comp['variant_files'].items() if mode == 'rtl' else [('ot_gl_' + spec['block'], None)]
    for mod, path in targets:
        if path:
            text = open(path, errors='replace').read()
            params = module_params(text, mod); mports = module_ports(text, mod)
            if clock not in mports: log('probe: %s lacks clock port %s, not bound' % (mod, clock)); continue
            psel = ' && '.join('(%s == %s)' % (k, v) for k, v in tp if k in params) or '1'
        else:
            psel = '1'
        st = cat(list(reversed(gate['state_expr']))) if gate else "1'b0"
        binds.append('bind %s ot_anim_probe #(.PSEL(%s)) u_ot_anim_probe (.clk(%s), .rst_act(%s), .fv(%s), .pay(%s), .hs(%s), .st(%s));'
                     % (mod, psel, clock, rst, cat(fv), cat(outs), cat(hsn), st))
    if not binds: raise SystemExit('NO_BIND: no block variant carries the clock port')
    pf = out / ('ot_anim_probe_%s.sv' % mode); pf.write_text('\n'.join(L + binds) + '\n')
    cf = out / 'ot_anim_dpi.cpp'; cf.write_text(DPI_CPP)
    meta = dict(clock=clock, reset=reset, groups=groups, levels=levels, layout=layout, outs=[(p, bits[p]) for p in outs],
                hs=[(n, bits[n]) for n in hsn])
    return pf, cf, meta


def macro_probe(spec, comp, masters, out):
    """RTL pass: bind a parameter-printing probe on every bench module that models a macro master of the netlist"""
    mods = defined_modules(comp['sources'], comp['cwd'])
    L = []; B = []; found = {}
    for M in masters:
        for v in [m for m in mods if m == M or m.endswith('_' + M)]:
            text = open(mods[v], errors='replace').read()
            hm = re.search(r'^\s*module\s+' + re.escape(v) + r'\s*#\s*\((.*?)\)\s*\(', text, re.M | re.S)
            ps = re.findall(r'parameter\s+(string|integer|int)?\s*([A-Za-z_]\w*)\s*=', hm.group(1)) if hm else []
            if not ps: continue
            pm = 'ot_anim_mprobe_' + v
            decl = ', '.join('parameter %s %s = %s' % ('string' if t == 'string' else 'int', n, '""' if t == 'string' else '0') for t, n in ps)
            fmt = ' '.join('%s=%s' % (n, '%s' if t == 'string' else '%0d') for t, n in ps)
            L.append('module %s #(%s) (); initial $display("OT_ANIM_MACRO %s %%m %s", %s); endmodule' % (pm, decl, v, fmt, ', '.join(n for t, n in ps)))
            B.append('bind %s %s #(%s) u_ot_anim_mprobe ();' % (v, pm, ', '.join('.%s(%s)' % (n, n) for t, n in ps)))
            found[v] = dict(master=M, file=mods[v], params=ps)
    if not L: return None, found
    pf = out / 'ot_anim_mprobe.sv'; pf.write_text('\n'.join(L + B) + '\n')
    return pf, found


# ---------------------------------------------------------------------------------------------- builds
def verilator_args(spec, comp, out, mdir, extra_files, replace=None, gate=False):
    replace = replace or {}
    G = spec.get('gtkwave_inc') or '/usr/share/verilator/include/gtkwave'
    lib = out / 'lib'; lib.mkdir(exist_ok=True)
    if not (lib / 'liblz4.so').exists(): (lib / 'liblz4.so').symlink_to('/usr/lib/x86_64-linux-gnu/liblz4.so.1')
    if comp['tool'] == 'verilator':
        args = comp['argv'][1:]; a2 = []; i = 0
        while i < len(args):
            x = args[i]
            if x == '--Mdir' and i + 1 < len(args): i += 2; continue
            if x in ('-j', '--build-jobs') and i + 1 < len(args): i += 2; continue
            if x.startswith(('--Mdir=', '--trace')): i += 1; continue
            a2.append(x); i += 1
        if '--build' not in a2 and '--binary' not in a2: a2.append('--build')
    else:
        a2, _ = iverilog_to_verilator(comp['argv'][1:], comp['cwd'])
    a2 = [replace.get(os.path.normpath(os.path.join(comp['cwd'], x)), replace.get(x, x)) if re.search(r'\.(sv|v)$', x) else x for x in a2]
    jobs = str(spec.get('gate_jobs', 32) if gate else spec.get('jobs', 16))
    return ['-Wno-fatal', '-Wno-TIMESCALEMOD', '-Wno-MULTITOP', '-Wno-PINNOTFOUND', '-Wno-PINMISSING', '--Mdir', str(mdir),
            '-CFLAGS', '-I' + G, '-LDFLAGS', '-L%s -lz' % lib, '-j', jobs] + a2 + [str(f) for f in extra_files]


def build_and_run(spec, comp, run, out, tag, vargs, mem_build, mem_run, plusargs=()):
    V = comp['path'] if (os.path.isabs(comp['path']) and os.path.basename(comp['path']) == 'verilator') else (spec.get('verilator') or 'verilator')
    env = dict(x.split('=', 1) for x in comp['env'] if '=' in x) if comp.get('env') else dict(os.environ)
    vcmd = [V] + vargs
    log('%s build: %s' % (tag, ' '.join(shlex.quote(x) for x in vcmd)[:1200]))
    t = time.time()
    r = subprocess.run(['ot-heavy', '--mem', str(mem_build), '--'] + vcmd, cwd=comp['cwd'], env=env,
                       stdout=open(out / ('build_%s.log' % tag), 'w'), stderr=subprocess.STDOUT)
    tb = time.time() - t
    log('%s build: rc %d in %.0f s' % (tag, r.returncode, tb))
    if r.returncode: raise SystemExit('BUILD_FAILED (%s): %s' % (tag, open(out / ('build_%s.log' % tag), errors='replace').read()[-800:]))
    md = Path(vargs[vargs.index('--Mdir') + 1])
    oname = next((vargs[i + 1] for i, x in enumerate(vargs) if x == '-o' and i + 1 < len(vargs)), None)
    exe = [md / oname] if oname and (md / oname).exists() else []
    exe += sorted((p for p in md.glob('V*') if p.is_file() and os.access(p, os.X_OK) and '.' not in p.name), key=lambda p: len(p.name))
    if not exe: raise SystemExit('BUILD_FAILED (%s): no model executable in %s' % (tag, md))
    if comp['tool'] == 'verilator':
        rargv = [str(exe[0])] + run['argv'][1:]
    else:
        vv = run['argv'][1:]; k = next((i for i, x in enumerate(vv) if not x.startswith('-')), len(vv))
        rargv = [str(exe[0])] + [x for x in vv[k + 1:] if x.startswith('+')]
    rargv += list(plusargs)
    renv = dict(x.split('=', 1) for x in run['env'] if '=' in x) if run.get('env') else dict(os.environ)
    log('%s run: %s (cwd %s)' % (tag, ' '.join(shlex.quote(x) for x in rargv)[:500], run['cwd']))
    t = time.time()
    r = subprocess.run(['ot-heavy', '--mem', str(mem_run), '--'] + rargv, cwd=run['cwd'], env=renv,
                       stdout=open(out / ('run_%s.log' % tag), 'w'), stderr=subprocess.STDOUT)
    tr = time.time() - t
    log('%s run: rc %d in %.0f s' % (tag, r.returncode, tr))
    return dict(rc=r.returncode, build_s=round(tb), run_s=round(tr), build_cmd=vcmd, run_cmd=rargv, log=out / ('run_%s.log' % tag), verilator=V)


MARK_RE = re.compile(r'PASS|FAIL|MATCH|DIFF|MISMATCH|ERROR|Error|Fatal|fatal|mismatch|assert', re.I)


def markers(path):
    out = []
    for ln in open(path, errors='replace'):
        if ln.startswith(('OT_ANIM', '- ', '%Warning')) or 'walltime' in ln or 'Verilator:' in ln: continue
        if MARK_RE.search(ln): out.append(ln.rstrip()[:300])
    return out


def read_txn(path, layout):
    """txn log -> reset release cycle, end cycle, per group list of (cycle, beats), output (cycle, payload) list"""
    rst = None; end = None; per = collections.defaultdict(list); pay = []
    widths = [w for _, _, w, _ in layout]; NF = sum(widths) or 1
    for ln in open(path):
        p = ln.split()
        if not p: continue
        if p[0] == 'R': rst = int(p[1]); continue
        if p[0] == 'E': end = int(p[1]); continue
        c = int(p[0]); fv = int(p[1], 16); pv = p[2]
        sh = NF
        for name, d, w, cfg in layout:   # concatenation order: first group = most significant
            sh -= w
            m = (fv >> sh) & ((1 << w) - 1)
            if m: per[name].append((c, bin(m).count('1')))
        if any(d == 'o' and per[n] and per[n][-1][0] == c for n, d, w, cfg in layout): pay.append((c, pv))
    return rst, end, per, pay


def derive_window(spec, layout, rst, end, per, cap=8192, floor=32, settle=8):
    ins = [n for n, d, w, cfg in layout if d == 'i' and not cfg] or [n for n, d, w, cfg in layout if d == 'i']
    outs = [n for n, d, w, cfg in layout if d == 'o']
    fin = sorted(c for n in ins for c, b in per.get(n, []))
    fout = sorted(c for n in outs for c, b in per.get(n, []))
    w = dict(rule='window = reset-settle + max(ceil(L/II)+1 items, one work unit), floor %d, cap %d (owner 2026-10-11)' % (floor, cap),
             reset_release=rst, input_groups=ins, output_groups=outs, inputs=len(fin), outputs=len(fout), sim_end=end)
    if not fin:
        t0 = (rst or 0); w.update(L=None, II=None, work_unit=None, note='no accepted input transaction: window from reset release')
        return [[t0, t0 + floor - 1]], w
    t_in0 = fin[0]
    o0 = next((c for c in fout if c >= t_in0), None)
    L = (o0 - t_in0) if o0 is not None else None
    sp = [b - a for a, b in zip(fin[:65], fin[1:65]) if b > a]
    II = sorted(sp)[len(sp) // 2] if sp else (L or 1)
    # work unit: first input .. last output of the first output burst (a burst ends at a gap > max(2L, 64) cycles)
    wu_end = None
    if o0 is not None:
        gap = max(2 * (L or 0), 64); last = o0
        for c in fout:
            if c < o0: continue
            if c - last > gap: break
            last = c
        wu_end = last
    wu = [t_in0, wu_end] if wu_end is not None else None
    items = math.ceil((L or 0) / max(1, II)) + 1
    need_items = items * II + (L or 0)
    need = max(need_items, (wu_end - t_in0 + 1) if wu_end is not None else 0)
    start = max(rst if rst is not None else 0, t_in0 - settle)
    length = max(floor, (t_in0 - start) + need + settle)
    w.update(L=L, II=II, items_needed=items, work_unit=wu, work_unit_cycles=(wu_end - t_in0 + 1) if wu_end is not None else None,
             first_input=t_in0, first_output=o0, cycles_needed=length)
    if end is not None: length = min(length, end - start + 1)
    if length <= cap:
        w['choice'] = 'single window of %d cycles' % length
        return [[start, start + length - 1]], w
    # above the cap: the first full work unit (if it fits in half the cap), then 4 sampled steady-state segments
    first = min(length, cap // 2) if wu_end is None or (wu_end - start + 1) > cap // 2 else (wu_end - start + 1 + settle)
    segs = [[start, start + first - 1]]
    rest = cap - first; nseg = 4; sl = max(floor, rest // nseg)
    lo = segs[0][1] + 1; hi = (fout[-1] if fout else (end or lo)) - sl
    for k in range(nseg):
        a = lo + (hi - lo) * (k + 1) // (nseg + 1) if hi > lo else lo + k * sl
        if a <= segs[-1][1]: a = segs[-1][1] + 1
        segs.append([a, a + sl - 1])
    w['choice'] = 'capped at %d: first %s %d cycles, then %d sampled steady-state segments of %d cycles (jumps marked)' % (
        cap, 'work unit' if wu_end is not None and (wu_end - start + 1) <= cap // 2 else 'segment', first, nseg, sl)
    return segs, w


# ---------------------------------------------------------------------------------------------- gate-level preparation
INST_RE = re.compile(r'^\s*([A-Za-z_][\w$]*)\s+(\\\S+\s|[A-Za-z_][\w$]*)\s*\(')


def prep_netlist(spec, kinds, out):
    """the routed netlist with its top renamed ot_gl_<block>; sequential / ICG / macro instances (names as in the DB)"""
    src = spec['netlist']; dst = out / 'netlist_gl.v'
    seq = []; icg = []; macros = collections.Counter(); minst = []; modules = set(); renamed = False; masters = collections.Counter(); physical = set()
    with open(src, errors='replace') as f, open(dst, 'w') as g:
        for ln in f:
            if ln.startswith('module '):
                nm = ln.split()[1].split('(')[0]
                modules.add(nm)
                if nm == spec['block']:
                    ln = ln.replace('module ' + nm, 'module ot_gl_' + nm, 1); renamed = True
            else:
                m = INST_RE.match(ln)
                if m and m.group(1) not in ('module', 'input', 'output', 'wire', 'assign', 'inout', 'reg'):
                    master, nm = m.group(1), m.group(2)
                    k = kinds.get(master)
                    masters[master] += 1
                    if k is None and re.search(r'\(\s*\)\s*;', ln[m.end() - 1:]): physical.add(master)
                    elif k is None: macros[master] += 1; minst.append((master, nm.strip()))
                    elif k['kind'] in ('ff', 'latch'): seq.append((nm, master))
                    elif k['kind'] == 'icg': icg.append((nm, master))
            g.write(ln)
    if not renamed: raise SystemExit('NETLIST: module %s not in %s' % (spec['block'], src))
    macros = {m: n for m, n in macros.items() if m not in modules and m not in physical}
    if physical:   # fillers / taps / decaps instantiated without ports: empty modules
        with open(dst, 'a') as g:
            for p in sorted(physical): g.write('\n/*verilator tracing_off*/\nmodule %s (); endmodule\n' % p)
    return dst, seq, icg, macros, [x for x in minst if x[0] in macros], masters


def macro_model(found, variant, master, out):
    """the bench's model of a macro, renamed to the master and with its string parameters turned into run-time values
    looked up by instance path (table from the RTL pass): a netlist macro instance carries no parameters"""
    text = open(found[variant]['file'], errors='replace').read()
    m = re.search(r'^\s*module\s+' + re.escape(variant) + r'\b.*?^\s*endmodule\b', text, re.M | re.S)
    body = m.group(0)
    hm = re.search(r'module\s+' + re.escape(variant) + r'\s*#\s*\((.*?)\)\s*\(', body, re.S)
    strs = [n for t, n in found[variant]['params'] if t == 'string']
    ints = [(t, n) for t, n in found[variant]['params'] if t != 'string']
    hdr = 'module %s %s(' % (master, ('#(' + ', '.join('parameter %s %s = 0' % (t or 'int', n) for t, n in ints) + ') ') if ints else '')
    body = body[:hm.start()] + hdr + body[hm.end():]
    k = body.index(');', body.index(hdr)) + 2
    decl = '\n    string %s;\n    initial begin\n%s\n    end\n' % (', '.join(strs), '\n'.join(
        '        %s = ot_anim_pkg::mparam($sformatf("%%m"), "%s", "");' % (n, n) for n in strs)) if strs else ''
    body = body[:k] + decl + body[k:]
    # whole file context: keep `timescale and DPI imports defined outside the module
    pre = '\n'.join(l for l in text[:m.start()].splitlines() if l.startswith('`timescale') or 'import' in l)
    p = out / ('ot_anim_macro_%s.sv' % master); p.write_text(pre + '\n' + body + '\n')
    return p


def swap_instance(text, variant, inst, newmod):
    """replace '<variant> [#(...)] <inst> (' by '<newmod> <inst> (' (balanced parameter list)"""
    n = 0; i = 0; out = []
    pat = re.compile(r'\b' + re.escape(variant) + r'\b')
    while True:
        m = pat.search(text, i)
        if not m: break
        j = m.end()
        while j < len(text) and text[j].isspace(): j += 1
        k = j
        if text.startswith('#', j):
            j += 1
            while text[j].isspace(): j += 1
            if text[j] == '(':
                d = 0
                while True:
                    if text[j] == '(': d += 1
                    elif text[j] == ')':
                        d -= 1
                        if d == 0: j += 1; break
                    j += 1
        while j < len(text) and text[j].isspace(): j += 1
        mm = re.match(re.escape(inst) + r'\s*\(', text[j:])
        if mm:
            out.append(text[i:m.start()]); out.append(newmod + ' '); i = j; n += 1
        else:
            out.append(text[i:m.end()]); i = m.end()
    out.append(text[i:])
    return ''.join(out), n


def cell_models(spec, out):
    cm = spec['cell_models']; kinds = json.loads(open(spec['cell_kinds']).read())
    return cm, kinds


# ---------------------------------------------------------------------------------------------- main flow
def main():
    global LOG
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--spec', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    spec = json.loads(open(a.spec).read()); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    LOG = out / 'trace.log'
    T0 = time.time()
    if spec['bench']['mode'] == 'workdir': comp, run = from_workdir(spec, out)
    else: comp, run = capture(spec, out)
    (out / 'capture.json').write_text(json.dumps(dict(compile={k: v for k, v in comp.items() if k != 'env'}, run={k: v for k, v in run.items() if k != 'env'}), indent=1))
    cm, kinds = cell_models(spec, out)
    netlist, seq, icg, macros, minst, masters = prep_netlist(spec, kinds, out)
    log('netlist: %d sequential, %d ICG, macros %s, %d masters' % (len(seq), len(icg), dict(macros), len(masters)))
    # ---- pass R: RTL, whole bench, every port transaction (L, II, work unit -> window; golden transactions)
    pr, cfr, meta = gen_probe(spec, comp, out, 'rtl')
    mp, found = macro_probe(spec, comp, list(macros), out)
    rv = verilator_args(spec, comp, out, out / 'obj_rtl', [pr, cfr] + ([mp] if mp else []))
    R = build_and_run(spec, comp, run, out, 'rtl', rv, spec.get('mem_gb', 32), spec.get('mem_gb', 32))
    rl = open(R['log'], errors='replace').read()
    sel = re.search(r'OT_ANIM_SEL (\S+)', rl)
    if not sel: raise SystemExit('NO_INSTANCE: no block instance matched the closure parameters: %s' % re.findall(r'OT_ANIM_INST .*', rl)[:6])
    dut = sel.group(1).rsplit('.', 1)[0]
    rst, end, per, pay_r = read_txn(out / 'txn_rtl.log', meta['layout'])
    segs, win = derive_window(spec, meta['layout'], rst, end, per, cap=int(spec.get('cap', 8192)))
    log('window', segs, json.dumps({k: v for k, v in win.items() if k != 'rule'}))
    # macro parameter table: RTL macro instances under the selected DUT
    mrows = []; mvariant = {}
    for ln in rl.splitlines():
        if not ln.startswith('OT_ANIM_MACRO '): continue
        _, v, path, *kv = ln.split(' ')
        if not path.startswith(dut + '.'): continue
        mvariant[found[v]['master']] = v
        np_ = path.rsplit('.', 1)[0]   # the probe's own scope is <macro>.u_ot_anim_mprobe
        for x in kv:
            k_, _, val = x.partition('=')
            mrows.append('%s %s %s' % (np_.replace('\\', '').replace(' ', ''), k_, val or '-'))
    (out / 'mtab.txt').write_text('\n'.join(mrows) + '\n')
    missing_models = [m for m in macros if m not in mvariant]
    if missing_models: raise SystemExit('NO_MACRO_MODEL: the bench has no model of %s under %s' % (missing_models, dut))
    mfiles = [macro_model(found, mvariant[m], m, out) for m in macros]
    # ---- gate-level: state vector in DB-leaf order (flops), then ICGs
    leaves = spec['flops']; lidx = {n: i for i, n in enumerate(leaves) if n}
    nl = {nm.replace('\\', '').strip(): (nm, master) for nm, master in seq}
    order = []; unplaced = []
    for i, n in enumerate(leaves):
        if n and n in nl: order.append((n, i))
    for n in nl:
        if n not in lidx: unplaced.append(n)
    flop_missing = [n for n in leaves if n and n not in nl]
    st_expr = []; flops = []
    for n, i in order:
        raw, master = nl[n]; k = kinds[master]
        st_expr.append('%s%s.%s' % ('~' if k.get('inv') else '', raw if raw.endswith(' ') else raw + ' ', k['state']))
        flops.append(dict(name=n, leaf=i, master=master))
    icgs = []
    for raw, master in icg:
        st_expr.append('%s.%s' % (raw if raw.endswith(' ') else raw + ' ', kinds[master]['state']))
        icgs.append(dict(name=raw.replace('\\', '').strip(), master=master))
    gate = dict(state_expr=st_expr)
    pg, cfg_, gmeta = gen_probe(spec, comp, out, 'gate', dut_path=dut, segments=segs, gate=gate)
    (out / 'chunks').mkdir(exist_ok=True)
    # swap the selected instance's module for the netlist
    inst = dut.rsplit('.', 1)[1]
    repl = {}; nsw = 0
    for v in comp['variants']:
        for f in comp['sources']:
            try: text = open(f, errors='replace').read()
            except OSError: continue
            if inst not in text: continue
            t2, n = swap_instance(text, v, inst, 'ot_gl_' + spec['block'])
            if n:
                p = out / ('swap_' + os.path.basename(f)); p.write_text(t2); repl[f] = str(p); nsw += n
    if nsw != 1: raise SystemExit('SWAP: %d instantiations of %s named %s' % (nsw, comp['variants'], inst))
    gv = verilator_args(spec, comp, out, out / 'obj_gate', [cm, netlist] + mfiles + [pg, cfg_], replace=repl, gate=True)
    G = build_and_run(spec, comp, run, out, 'gate', gv, spec.get('gate_mem_gb', 160), spec.get('gate_run_mem_gb', 64),
                      plusargs=['+OT_ANIM_MTAB=%s' % (out / 'mtab.txt')])
    gl = open(G['log'], errors='replace').read()
    if 'OT_ANIM_SEL' not in gl: raise SystemExit('GATE_NO_INSTANCE: %s' % gl[-600:])
    rst_g, end_g, per_g, pay_g = read_txn(out / 'txn_gate.log', meta['layout'])
    # ---- exactness: the gate-level run reproduces the RTL run's transactions and the bench's own verdict lines
    mr, mg = markers(R['log']), markers(G['log'])
    seq_r = {n: [b for c, b in v] for n, v in per.items()}; seq_g = {n: [b for c, b in v] for n, v in per_g.items()}
    ex = dict(rtl_rc=R['rc'], gate_rc=G['rc'], outputs_rtl=len(pay_r), outputs_gate=len(pay_g),
              output_payloads_equal=[p for c, p in pay_r] == [p for c, p in pay_g],
              output_cycles_equal=[c for c, p in pay_r] == [c for c, p in pay_g],
              transactions_equal=seq_r == seq_g, bench_markers_equal=mr == mg, bench_markers_gate=mg[:12],
              mparam_misses=len(re.findall('OT_ANIM_MPARAM_MISS', gl)))
    ex['pass'] = bool(ex['output_payloads_equal'] and ex['transactions_equal'] and ex['bench_markers_equal'] and R['rc'] == G['rc'] and pay_r)
    log('exactness', json.dumps(ex)[:800])
    # ---- chunks
    idx = []
    for ln in open(out / 'chunks' / 'index.txt'):
        i_, c0, n, rawb, zb, chg = [int(x) for x in ln.split()]
        idx.append(dict(file='c%05d.bin' % i_, c0=c0, n=n, raw_bytes=rawb, bytes=zb, changes=chg))
    ncyc = sum(c['n'] for c in idx); zbytes = sum(c['bytes'] for c in idx)
    # ---- lanes: flops grouped by their synthesis register name
    lanes = collections.OrderedDict()
    for k, f in enumerate(flops):
        v, b = flop_vector(f['name']); lanes.setdefault(v, []).append((b, k))
    tix = tree_index(spec.get('tree')); mods = spec.get('modules') or {}
    lane_out = []
    for v, bl in lanes.items():
        bl.sort(); fl = None; parts = v.split('.')
        for cut in range(len(parts) - 1, -1, -1):
            kk = tix.get('.'.join(parts[:cut]))
            if kk is not None:
                net = (mods.get(kk) or {}).get('.'.join(parts[cut:])); fl = net if net else None; break
        lane_out.append(dict(name=v, bits=[b for b, k in bl], flops=[k for b, k in bl], file=fl[0] if fl else None, line=fl[1] if fl else None))
    # handshake lanes and transactions inside the window
    inwin = lambda c: any(a_ <= c <= b_ for a_, b_ in segs)
    hs = [dict(name=n, bits=w, kind=('level' if n in [l['name'] for l in gmeta['levels']] else
                                     'valid' if any(g['valid'] == n for g in gmeta['groups']) else
                                     'ready' if any(g['ready'] == n for g in gmeta['groups']) else 'credit'), events=[]) for n, w in gmeta['hs']]
    NH = sum(w for n, w in gmeta['hs']) or 1
    for ln in open(out / 'hs_gate.log'):
        c, h = ln.split(); c = int(c); h = int(h.replace('x', '0').replace('z', '0'), 16); sh = NH
        for e in hs:
            sh -= e['bits']; v = (h >> sh) & ((1 << e['bits']) - 1)
            if not e['events'] or e['events'][-1][1] != v or c - 1 not in range(e['events'][-1][0], c): e['events'].append([c, v])
    for e in hs:   # keep changes only
        ev = []; last = None
        for c, v in e['events']:
            if v != last: ev.append([c, v]); last = v
        e['events'] = ev
    txn = sorted([c, n, b] for n, v in per_g.items() for c, b in v if inwin(c))
    doc = dict(schema='opentallas.elem_trace.v1', element=spec['element'], job=spec['job'], bench=spec['bench']['label'],
               bench_why=spec['bench'].get('why'), source_commit=spec.get('commit'), source_commit_verified=spec['bench'].get('commit_verified', True),
               netlist=spec['netlist_ref'], simulator='verilator %s (gate-level, zero-delay, cycle-based)' % subprocess.run(
                   [G['verilator'], '--version'], capture_output=True, text=True).stdout.split()[1],
               cell_models=spec.get('cell_models_ref'), clock=gmeta['clock'], clock_ps=spec.get('clock_ps'), dut_scope=dut,
               window=dict(win, segments=segs, cycles=ncyc, jumps=[[segs[i][1], segs[i + 1][0]] for i in range(len(segs) - 1)]),
               exactness=ex,
               state=dict(encoding='flop-xor-rle', n=len(st_expr), flops=len(flops), icgs=len(icgs), chunk_cycles=256,
                          format='zlib( "OTF1" | u32 N | u32 c0 | u32 ncyc | bitmap(N) of cycle c0, LSB = state 0 | per later cycle: varint k, '
                                 'k varint gaps (first = index, then index - previous - 1) of the states that changed ) ; state i < flops: '
                                 'flops[i] (logical Q, QN cells inverted), then icgs (enable latch)',
                          chunks=idx, bytes=zbytes, bytes_per_1000_cycles=round(1000.0 * zbytes / max(1, ncyc))),
               flops=[[f['leaf'], f['master']] for f in flops], icgs=icgs,
               mapping=dict(flops_netlist=len(nl), flops_db_leaves=sum(1 for n in leaves if n), mapped=len(flops),
                            netlist_not_in_db=unplaced[:20], netlist_not_in_db_n=len(unplaced), db_not_in_netlist=flop_missing[:20],
                            db_not_in_netlist_n=len(flop_missing), note='flops matched by instance name: netlist (6_final.v) = DB clock-tree leaves'),
               lanes=lane_out, handshakes=hs, transactions=txn,
               ports=dict(groups=gmeta['groups'], levels=gmeta['levels'], reset=gmeta['reset']),
               stats=dict(lanes=len(lane_out), rtl_build_s=R['build_s'], rtl_run_s=R['run_s'], gate_build_s=G['build_s'], gate_run_s=G['run_s'],
                          wall_s=round(time.time() - T0), sim_cycles=end_g),
               provenance=dict(source='gate-sim', rtl_pass='rtl-sim (window derivation, golden transactions)',
                               chunks_sha256=hashlib.sha256(b''.join(open(out / 'chunks' / c['file'], 'rb').read() for c in idx)).hexdigest(),
                               cmd=dict(bench=spec['bench'].get('cmd'), rtl_build=' '.join(shlex.quote(x) for x in R['build_cmd']),
                                        gate_build=' '.join(shlex.quote(x) for x in G['build_cmd']), gate_run=' '.join(shlex.quote(x) for x in G['run_cmd']),
                                        cwd=comp['cwd'])))
    (out / 'elem_trace.json').write_text(json.dumps(doc, separators=(',', ':')))
    log('DONE elem_trace.json %d bytes; %d chunks %d bytes for %d cycles (%d B/1000 cyc); exact %s' % (
        (out / 'elem_trace.json').stat().st_size, len(idx), zbytes, ncyc, doc['state']['bytes_per_1000_cycles'], ex['pass']))


if __name__ == '__main__':
    main()
