"""Elaborate the extracted actual controller wiring only, without the array."""
import json
import re
import subprocess
from pathlib import Path
import dsrom_wavefront_install as W

ROOT = W.ROOT


def check(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    original = (ROOT/'rtl/dsrom_sys/s81_capture_parent'/W.ROLES[0]).read_text()
    die = W.wire_die(original)
    begin = die.index('    assign wf_request =')
    end = die.index('.users_done(users_done), .proto_fault(proto_fault));', begin)
    block = die[begin:end+len('.users_done(users_done), .proto_fault(proto_fault));')]
    ctrl = W.controller_adapter(W.CONTROLLER.read_text())
    declarations = []
    # Infer the widths of every simple actual connection from the real ABI.
    ports = re.findall(r'^\s*(?:input|output)\s+(?:wire|reg)\s*(\[[^\n]*?\])?\s*(\w+)\s*[,\n]', ctrl, re.M)
    for width, port in ports:
        match = re.search(r'\.'+port+r'\((\w+)\)', block)
        if match:
            declarations.append('wire '+width+' '+match[1]+';')
    for line in W.COMMON_PORTS.splitlines():
        if re.match(r'\s*(input|output) wire', line):
            declarations.append(re.sub(r'\b(input|output) wire', 'wire', line.strip())[:-1]+';')
    declarations += ['wire host_mode,core_done,c8_write_quiet,c8_write_quarantine,c8_write_fault,coll_busy;',
                     'wire [NW-1:0] core_next_token;', 'wire [31:0] core_next_val;']
    # Common ABI and controller-derived declarations overlap; remove exact duplicates
    # and omit controller-derived names already declared by COMMON_PORTS.
    clean = []
    seen = set()
    for d in reversed(declarations):
        names = re.findall(r'\b(?:wf_\w+|\w+)\b', d.split(']')[-1])[1:] if ']' not in d else re.findall(r'\b\w+\b', d.split(']')[-1])
        if any(n in seen for n in names):
            continue
        clean.append(d)
        seen.update(names)
    values = dict(W.PKG_DEFAULTS, FULL_SHAPE=1, NW=21, AW=30, VWA=15, FLIT=512,
                  USER_W=10, KVW=32768, XWORDS=1, RXWORDS=1, RXB=0, TXB=0,
                  PKG_WAVE_WIN=6)
    values['SOURCE']=1
    params = '\n'.join('localparam integer '+k+'='+str(v)+';' for k,v in values.items())
    tb = out/'controller_abi.sv'
    tb.write_text('module wf_abi #(parameter integer PKG_WAVE=0);\n'+params+'\n'+'\n'.join(reversed(clean))+'\n'+block+'\nendmodule\n')
    adapter = out/'ot_rom_pkg_ctrl_wf_s81.sv'
    adapter.write_text(ctrl)
    runs = []
    for wave in (0,1):
        cmd = ['iverilog','-g2012','-tnull','-s','wf_abi','-Pwf_abi.PKG_WAVE='+str(wave), str(tb), str(adapter)]
        run = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out/('wave'+str(wave)+'.log')).write_text(run.stdout)
        runs.append(dict(wave=wave, returncode=run.returncode, command=cmd))
    result = dict(scope='extracted actual controller ABI only; no stage/system behavior qualification',
                  controller_sha256=W.CONTROLLER_SHA, runs=runs, PASS=all(r['returncode']==0 for r in runs),
                  measured_system_result=False, SS_FF_claim=False)
    (out/'abi_result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output')
    print(json.dumps(check(parser.parse_args().output), indent=2))
