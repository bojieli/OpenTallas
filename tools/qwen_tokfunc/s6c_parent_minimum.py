#!/usr/bin/env python3
"""Actual GEN cut replay. Missing current source/image/clock authority refuses before compilation.

No DUT output is forced. The emitted vehicle uses original GEN instance connections,
real source modules and SRAM models. It is a bounded parent proof, never a whole-die claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'opentallas.qwen.s6c-parent-inputs.v1'
ALLOWED = {'qkd_kvs_ctl', 'qkd_kvs_grp_s6c', 'qkd_kvs_grp_h_s6c', 'qkd_kvs_pc', 'qkd_kvs_pc_h',
           'qkd_kvs_emb', 'qkd_kvs_hroot', 'qkd_kvs_hroot_h',
           'qkd_kvn_ctx_ovl_rope', 'qkd_d2d_static_ovl_sfm3', 'qkd_d2d_cal_seq_pin_ovl_rope'}
PROFILE = dict(S6C=1, ROPE=1, ROPE_OVL=1, PC_SRAM=1, PC_RLAND=1, DOMSPLIT=1)


def need(ok, message):
    if not ok:
        raise ValueError('PARENT_INPUT_REFUSED: ' + message)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def artifact(root, entry):
    need(isinstance(entry, dict) and bool(entry.get('path')), 'missing artifact path')
    p = Path(entry['path'])
    if not p.is_absolute(): p = root / p
    need(p.is_file() and sha(p) == entry.get('sha256'), 'missing/changed artifact ' + str(p))
    return p


def source(revision, name):
    need(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_./+-]+', name) and '..' not in Path(name).parts,
         'invalid source name')
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', revision + ':' + name])


def module_ports(text, name):
    m = re.search(r'\bmodule\s+' + re.escape(name) + r'\b', text)
    need(m is not None, 'selected source omits master ' + name)
    end = text.index('endmodule', m.start())
    body = re.sub(r'//[^\n]*|/\*.*?\*/', '', text[m.start():end], flags=re.S)
    # Only the external header/declarations count, never a function/task input.
    pos = body.index(name) + len(name)
    while body[pos].isspace(): pos += 1
    if body[pos] == '#':
        pos = body.index('(', pos); depth = 1; pos += 1
        while depth:
            depth += (body[pos] == '(') - (body[pos] == ')'); pos += 1
    pos = body.index('(', pos); start = pos + 1; depth = 1; pos += 1
    while depth:
        depth += (body[pos] == '(') - (body[pos] == ')'); pos += 1
    header = body[start:pos-1]
    declarations = header if re.search(r'\b(?:input|output|inout)\b', header) else '\n'.join(
        re.findall(r'(?m)^\s*(?:input|output|inout)\b[^;]*;', body[pos:]))
    ports = {}
    pattern = (r'\b(input|output|inout)\s+(?:(?:wire|reg|logic)\s+)?'
               r'(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?'
               r'([A-Za-z_$][\w$]*(?:\s*,\s*(?!(?:input|output|inout)\b)[A-Za-z_$][\w$]*)*)')
    for d, hi, lo, ns in re.findall(pattern, declarations):
        need(d != 'inout', 'bidirectional cut port unsupported')
        for n in ns.split(','):
            ports[n.strip()] = (d, int(hi) - int(lo) + 1 if hi else 1)
    need(bool(ports), 'no literal source port declaration for ' + name)
    return ports


def parent_instance(die, name, master):
    # GEN emits named connections. A nested expression is retained byte for byte.
    pat = re.compile(r'(?m)^\s*' + re.escape(master) + r'\s+(?:#\([^;]*?\)\s*)?' + re.escape(name) + r'\s*\(')
    found = list(pat.finditer(die)); need(len(found) == 1, 'missing/ambiguous GEN instance ' + name)
    m = found[0]; i = m.end(); depth = 1; j = i
    while depth:
        need(j < len(die), 'unterminated GEN instance')
        depth += (die[j] == '(') - (die[j] == ')'); j += 1
    need(re.match(r'\s*;', die[j:]), 'GEN instance terminator')
    conns = {}; k = i
    while k < j - 1:
        q = re.match(r'\s*,?\s*\.([A-Za-z_$][\w$]*)\s*\(', die[k:j-1])
        need(q is not None, 'only explicit named GEN connections supported')
        start = k + q.end(); pos = start; dep = 1
        while dep:
            dep += (die[pos] == '(') - (die[pos] == ')'); pos += 1
        need(q.group(1) not in conns, 'duplicate GEN port')
        conns[q.group(1)] = die[start:pos-1].strip(); k = pos
        if not die[k:j-1].strip(): break
    return die[m.start():j] + ';', conns


def names(expr):
    need(re.fullmatch(r"[A-Za-z0-9_$'{}\[\]:,\s.+-]+", expr) is not None, 'unsupported GEN expression')
    return set(re.findall(r"(?<![\w$'])\b[A-Za-z_$][\w$]*\b", expr))


def load_inputs(path):
    path = Path(path).resolve(); root = path.parent; c = json.loads(path.read_text())
    need(c.get('schema') == SCHEMA and c.get('status') == 'QUALIFIED_SOURCE_GEN_INPUTS',
         'current qualified source/GEN input packet required; synthetic packets cannot run')
    need(c.get('profile') == PROFILE, 'actual S6C/RoPE/SRAM/RLAND profile required')
    rev = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', c.get('source_revision', '')], text=True).strip()
    need(rev == c.get('source_revision'), 'full exact source revision required')
    die_path = artifact(root, c.get('gen', {})); params = artifact(root, c.get('gen_params', {}))
    ages = artifact(root, c.get('gen_ages', {})); die = die_path.read_text()
    binding = dict(source_revision=rev, gen_sha256=sha(die_path), gen_params_sha256=sha(params),
                   gen_ages_sha256=sha(ages), profile=PROFILE, epoch=c.get('epoch'))
    need(type(c.get('epoch')) is int and 0 <= c['epoch'] < 65536, 'actual epoch required')
    authorities = {}
    for name in ('clock_authority', 'driver_authority'):
        p = artifact(root, c.get(name, {})); a = json.loads(p.read_text())
        need(a.get('schema') == 'opentallas.qwen.s6c-parent-authority.v1' and
             a.get('authority') == name and a.get('status') == 'QUALIFIED_SOURCE_GEN_INPUTS',
             'typed actual authority required: ' + name)
        need(all(a.get(k) == v for k, v in binding.items()), 'authority source/GEN/epoch mismatch: ' + name)
        authorities[name] = a
    need(authorities['clock_authority'].get('clocks') == c.get('clocks'), 'actual clocks differ')
    src = {}; masters = {}
    for entry in c.get('sources', []):
        data = source(rev, entry['path']); need(hashlib.sha256(data).hexdigest() == entry.get('sha256'),
                                              'selected source hash differs: ' + entry['path'])
        src[entry['path']] = data
        for master in re.findall(rb'(?m)^module\s+(\w+)\b', data):
            masters.setdefault(master.decode(), []).append(entry['path'])
    instances = []; selected = set(); seen = set()
    for row in c.get('instances', []):
        master, inst = row['master'], row['name']
        need(master in ALLOWED and re.fullmatch(r'[A-Za-z_$][\w$]*', inst) and inst not in seen,
             'unbounded, duplicate or invalid cut instance')
        need(len(masters.get(master, [])) == 1, 'missing/duplicate selected master source: ' + master)
        seen.add(inst); selected.add(master)
        p = module_ports(src[masters[master][0]].decode(), master)
        statement, conns = parent_instance(die, inst, master)
        need(set(conns) == set(p), 'GEN pin set differs from exact master ' + inst)
        instances.append(dict(master=master, name=inst, ports=p, connections=conns, statement=statement))
    need('qkd_kvs_ctl' in selected and bool(selected & {'qkd_kvs_grp_s6c', 'qkd_kvs_grp_h_s6c'}) and
         bool(selected & {'qkd_kvs_pc', 'qkd_kvs_pc_h'}) and
         {'qkd_kvn_ctx_ovl_rope', 'qkd_d2d_cal_seq_pin_ovl_rope'} <= selected,
         'real dispatcher/S6C group/SRAM PC/descriptor/admission hierarchy required')
    need(3 <= len(instances) <= 16, 'cut must remain bounded to selected parent, not whole die')
    widths = {}
    for hi, lo, name in re.findall(r'\b(?:wire|input\s+wire|output\s+wire)\s*'
                                  r'(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?([A-Za-z_$][\w$]*)', die):
        w = int(hi)-int(lo)+1 if hi else 1
        need(name not in widths or widths[name] == w, 'ambiguous GEN net width')
        widths[name] = w
    used, driven = set(), set()
    for row in instances:
        for port, expr in row['connections'].items():
            ns = names(expr); used |= ns
            if row['ports'][port][0] == 'output':
                need(re.fullmatch(r'[A-Za-z_$][\w$]*', expr) and widths.get(expr) == row['ports'][port][1],
                     'output cut requires exact whole-net GEN connection')
                need(expr not in driven, 'two actual cut outputs drive ' + expr)
                driven.add(expr)
    # Include original simple GEN aliases feeding this cut, recursively.
    aliases = dict(re.findall(r'\bassign\s+([A-Za-z_$][\w$]*)\s*=\s*([^;]+);', die))
    included = {}; pending = list(used)
    while pending:
        net = pending.pop()
        if net in aliases and net not in included:
            need(net not in driven, 'GEN alias and instance both drive cut net')
            included[net] = aliases[net]; ns = names(aliases[net]); pending += list(ns-used); used |= ns
    need(all(n in widths for n in used), 'GEN cut has unresolved net widths')
    external = used-driven-set(included)
    clocks = c.get('clocks', []); domains = {r['domain']: r for r in clocks}
    need(len(domains) == len(clocks) and bool(domains), 'unique actual clock domains required')
    for r in clocks:
        need(r['net'] in external and widths[r['net']] == 1 and type(r.get('half_period_fs')) is int and
             r['half_period_fs'] > 1 and type(r.get('phase_fs')) is int and r['phase_fs'] >= 0,
             'actual clock root/phase/period required')
    driver = authorities['driver_authority']
    need(driver.get('cut_instances') == c.get('instances'), 'driver names another actual cut')
    image_rows = []; events = list(driver.get('events', []))
    ctl = [r for r in instances if r['master'] == 'qkd_kvs_ctl']; need(len(ctl) == 1, 'one real boot consumer required')
    bp = ctl[0]['connections']
    boot_nets = {k: bp.get(v) for k, v in dict(pr='boot__boot_pr', target='boot__boot_image_target',
                                            ready='boot__boot_image_ready').items()}
    need(all(v in external for v in boot_nets.values()), 'boot must enter real dispatcher at external loader face')
    for row in driver.get('image_streams', []):
        p = artifact(root, row['image']); need(row['domain'] in domains and type(row.get('start_edge')) is int,
                                             'image actual clock/date missing')
        words = []; addr = 0
        for word in re.sub(r'//[^\n]*', '', p.read_text()).split():
            if word.startswith('@'): addr = int(word[1:], 16); continue
            value = int(word, 16); need(value < 1 << 64 and addr < 1024, 'actual dispatcher image word/address ABI')
            words.append((addr, value)); addr += 1
        need(words and 1 <= row['target'] <= 14, 'nonempty actual boot image target required')
        start = row['start_edge']; need(start >= 2, 'boot must follow real reset/release')
        for i, (address, value) in enumerate(words):
            events.append(dict(domain=row['domain'], edge=start+i,
                               values={boot_nets['pr']:hex((1<<74)|(address<<64)|value),
                                       boot_nets['target']:hex(row['target']), boot_nets['ready']:'0'},
                               boot_word=True))
        for ofs, ready in ((len(words), 0), (len(words)+1, 1), (len(words)+2, 0)):
            events.append(dict(domain=row['domain'], edge=start+ofs,
                               values={boot_nets['pr']:'0', boot_nets['ready']:str(ready)}))
        image_rows.append(dict(path=str(p), sha256=sha(p), target=row['target'], words=len(words), start_edge=start))
    need(image_rows, 'actual GEN boot images required')
    checks = driver.get('checks', []); metrics = driver.get('metrics', [])
    roles = {'boot_accepted', 'first_token_data', 'cold_sram_write', 'cold_sram_read'}
    need(roles <= {r.get('role') for r in metrics} and checks, 'nonzero real boot/token/SRAM observations required')
    for e in events:
        need(e['domain'] in domains and type(e['edge']) is int and e['edge'] >= 1, 'driver edge/domain missing')
        for net, value in e['values'].items():
            need(net in external and net not in {r['net'] for r in clocks}, 'cannot drive internal/output/clock net')
            need(0 <= int(str(value),0) < 1 << widths[net], 'driver value width')
    for r in checks:
        need(r['domain'] in domains and r['net'] in driven and type(r['edge']) is int and r['edge'] > 0,
             'expected check must observe actual cut output at actual edge')
        need(0 <= int(str(r['value']),0) < 1 << widths[r['net']], 'expected value width')
    for r in metrics:
        need(r['domain'] in domains and type(r.get('minimum')) is int and r['minimum'] > 0 and
             re.fullmatch(r'[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*|\[\d+\])*', r.get('signal','')),
             'source hierarchical activity monitor required')
        need(r['signal'].split('.')[0] in seen, 'activity outside actual cut')
    return c, src, instances, widths, used, driven, included, external, events, checks, metrics, image_rows


def emit(parsed, out):
    c, src, instances, widths, used, driven, aliases, external, events, checks, metrics, images = parsed
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    need(not any(out.iterdir()), 'new isolated output directory required')
    paths = []
    for name, data in src.items():
        p = out/'src'/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data); paths.append(str(p))
    lines = ['`timescale 1fs/1fs', 'module tb_s6c_parent;', 'integer mut=0;',
             'initial begin if ($value$plusargs("MUT=%d",mut)) begin end end']
    clock_nets = {r['net'] for r in c['clocks']}
    for n in sorted(used):
        w = widths[n]; typ = 'reg' if n in external else 'wire'
        lines.append(f'{typ} [{w-1}:0] {n}' + ('=0;' if typ=='reg' else ';'))
    for n, expr in aliases.items(): lines.append(f'assign {n} = {expr};')
    lines += [r['statement'] for r in instances]
    first_boot = next(e for e in events if e.get('boot_word'))
    grouped = {}
    for e in events:
        for net, value in e['values'].items():
            key=(e['domain'],e['edge'],net);need(key not in grouped, 'conflicting actual pin drivers')
            grouped[key]=(value, e is first_boot and net.endswith('boot_pr'))
    # Mutation changes the actual first boot word while preserving the DUT, binary and expected oracle.
    first_pr = next(n for n in first_boot['values'] if widths[n] == 143)
    grouped[(first_boot['domain'],first_boot['edge'],first_pr)]=(first_boot['values'][first_pr],True)
    for i, m in enumerate(metrics): lines.append(f'integer metric_{i}=0;')
    done=[]
    for i, clock in enumerate(c['clocks']):
        d,n=clock['domain'],clock['net'];ctr=f'edge_{i}';dn=f'done_{i}';done.append(dn)
        lines += [f'integer {ctr}=0; reg {dn}=0;', f'initial begin #{clock["phase_fs"]}; forever #{clock["half_period_fs"]} {n}=~{n}; end']
        ev = [(edge,net,value,mut) for (domain,edge,net),(value,mut) in grouped.items() if domain==d]
        for edge,net,value,mutation in ev:
            rhs=f"{widths[net]}'h{int(str(value),0):x}" + (" ^ (mut ? 1 : 0)" if mutation else '')
            if edge == 1: lines.append(f'initial {net}={rhs};')
        lines.append(f'always @(negedge {n}) begin')
        for edge,net,value,mutation in ev:
            if edge == 1: continue
            rhs=f"{widths[net]}'h{int(str(value),0):x}" + (" ^ (mut ? 1 : 0)" if mutation else '')
            lines.append(f'if ({ctr}+1=={edge}) {net}={rhs};')
        lines += ['end',f'always @(posedge {n}) begin #1; {ctr}={ctr}+1;']
        for r in checks:
            if r['domain']==d:
                lines.append(f'if ({ctr}=={r["edge"]} && {r["net"]} !== {widths[r["net"]]}\'h{int(str(r["value"]),0):x}) '
                             f'$fatal(1,"PARENT_CHECK_MISMATCH net={r["net"]} edge=%0d",{ctr});')
        for j,m in enumerate(metrics):
            if m['domain']==d: lines.append(f'if ({m["signal"]}) metric_{j}=metric_{j}+1;')
        limit=max([r['edge'] for r in checks if r['domain']==d]+[e for e,_,_,_ in ev]+[1])+10
        lines += [f'if ({ctr}>={limit}) {dn}=1;', 'end']
    lines += ['initial begin wait ('+' && '.join(done)+'); #2;']
    for i,m in enumerate(metrics):
        lines.append(f'if (metric_{i}<{m["minimum"]}) $fatal(1,"PARENT_ACTIVITY_MISSING role={m["role"]}");')
        lines.append(f'$display("PARENT_METRIC {m["role"]}=%0d",metric_{i});')
    lines += ['$display("S6C_PARENT_BOOT_TOKEN_COLD_SRAM_PASS"); $finish; end', 'endmodule']
    tb=out/'tb_s6c_parent.sv';tb.write_text('\n'.join(lines)+'\n')
    (out/'input_record.json').write_text(json.dumps(dict(source_revision=c['source_revision'],gen=c['gen'],
        instances=c['instances'],image_streams=images,sources=c['sources'],
        scope='Actual bounded selected parent only; no whole-die/physical/rate qualification'),indent=2)+'\n')
    return paths+[str(tb)]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--authority',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--threads',type=int,default=4);a=ap.parse_args()
    parsed=load_inputs(a.authority);out=Path(a.out).resolve();sources=emit(parsed,out)
    if a.prepare_only: print('PARENT_SOURCE_PREPARED_NO_SIMULATION');return
    vl=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator';obj=out/'obj'
    with (out/'build.log').open('w') as log:
        subprocess.run([str(vl),'--binary','--timing','-Wno-fatal','--top-module','tb_s6c_parent',
                        '-j',str(a.threads),'--Mdir',str(obj),*sources],stdout=log,stderr=subprocess.STDOUT,check=True,cwd=out/'src')
    results=[]
    for name,mut in [('positive',0),('boot_word_mutant',1)]:
        p=subprocess.run([str(obj/'Vtb_s6c_parent'),f'+MUT={mut}'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        (out/(name+'.log')).write_text(p.stdout)
        ok=(p.returncode==0 and 'S6C_PARENT_BOOT_TOKEN_COLD_SRAM_PASS' in p.stdout) if mut==0 else (
            p.returncode!=0 and ('PARENT_CHECK_MISMATCH' in p.stdout or 'PARENT_ACTIVITY_MISSING' in p.stdout))
        results.append(dict(name=name,returncode=p.returncode,ok=ok))
    (out/'result.json').write_text(json.dumps(dict(binary_sha256=sha(obj/'Vtb_s6c_parent'),cases=results),indent=2)+'\n')
    need(all(r['ok'] for r in results),'actual parent replay or causal negative failed')
    print('S6C_PARENT_MINIMUM_PASS_COMPONENT_ONLY')

if __name__=='__main__':main()
