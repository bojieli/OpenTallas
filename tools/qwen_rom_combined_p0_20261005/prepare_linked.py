#!/usr/bin/env python3
"""Prepare one released P8191 linked case; no image creation or frontend run."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(job, objects, source, output, prefix="Vtb_qwen_rt_kv_stream4"):
    if prefix not in ("Vtb_qwen_rt_kv_stream4","Vjoin"):
        raise ValueError("unsupported actual model ABI")
    job, objects, source, output = map(Path, (job, objects, source, output))
    argv = json.loads((job/'runtime.command.json').read_text())
    if argv[argv.index('--pos')+1]!='8191' or argv[argv.index('--kv-ideal')+1]!='0':
        raise ValueError('actual released real-KV P8191 source required')
    history = Path(argv[argv.index('--kv-dir')+1])/'L0_die0.bin'
    token = job/'run/L0_die0_kvP.hex'
    if history.stat().st_size != 4194304*4:
        raise ValueError('wrong actual one-layer history extent')
    if len(token.read_text().splitlines()) != 512:
        raise ValueError('actual complete K/V token source required')
    header = objects/(prefix+'.h')
    archive = objects/(prefix+'__ALL.a')
    if not archive.is_file():
        raise ValueError('existing complete model archive absent; no frontend fallback')
    raw_header = header.read_text()
    # Probe only common original callable ports; missing seam ports are a real
    # dependency. Never force internal state or claim a constant pin is warm.
    seam_exports = {k:('&'+k+',') in raw_header for k in
                    ('warm_rst_n','hold_rows','bad_ack_tag','join_debt','join_row_sec','join_row_layer','join_row_data','join_ack_valid','join_write_accepted','join_desc_committed','join_go_committed')}
    model_make = objects/(prefix+'.mk')
    match = re.search(r'^VERILATOR_ROOT\s*=\s*(\S+)\s*$',model_make.read_text(),re.M)
    if not match:
        raise ValueError('actual generated model runtime root absent')
    include = Path(match.group(1))/'include'
    if not (include/'verilated.h').is_file():
        raise ValueError('actual model runtime headers absent')
    driver = source/'tools/qwen_rom_combined_p0_20261005/linked_driver.cpp'
    compiler = ['g++', '-std=c++20', '-O2', '-pthread', '-DP0_REUSE_HEADER='+str(int(prefix!='Vjoin')),
                '-I'+str(objects), '-I'+str(include), '-I'+str(include/'vltstd'),
                '-I'+str(driver.parent), '-c', str(driver), '-o', str(output/'driver.o')]
    link = ['g++','-pthread',str(output/'driver.o'),str(archive),
            *[str(objects/name) for name in ('verilated.o','verilated_threads.o','verilated_dpi.o')],
            '-o',str(output/'linked_driver_tu_probe')]
    output.mkdir(parents=True, exist_ok=False)
    record = dict(status='PREPARED_ACTUAL_DRIVER_TU_ONLY', history=dict(path=str(history),sha256=sha(history)),
                  token_fixture=dict(path=str(token),sha256=sha(token),scope='actual released-checkpoint token K/V, linked protocol operands only'),
                  original_runtime_command_sha256=sha(job/'runtime.command.json'),
                  existing_model=dict(prefix=prefix,objects=str(objects),archive_sha256=sha(archive),header_sha256=sha(header),seam_exports=seam_exports),
                  actual_runtime_root=str(include.parent),actual_model_make_sha256=sha(model_make),
                  new_frontend_launched=False,force_internal_state=False,producer32case_replay=False,
                  command=compiler,link=link,source_sha256=sha(driver),
                  required_runtime_ABI='actual public warm admission + held row valid/pop + consumer ACK tag seam; old constant warm pin is not equivalent',
                  runtime_ready=all(seam_exports.values()),full_token=False,
                  linked_case='one released L0/rank0 P8191 actual consumer+protected simulation provider: real command/GO, held rows, 136 ACKs, warm admission, final actual debt0; negative tag preserves accepted debt')
    (output/'prepared.json').write_text(json.dumps(record,indent=2)+'\n')
    (output/'tu.command.json').write_text(json.dumps(compiler,indent=2)+'\n')
    (output/'link.command.json').write_text(json.dumps(link,indent=2)+'\n')
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('job','objects','source','output'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--prefix',choices=['Vtb_qwen_rt_kv_stream4','Vjoin'],default='Vtb_qwen_rt_kv_stream4')
    a=parser.parse_args()
    print(json.dumps(prepare(a.job,a.objects,a.source,a.output,a.prefix)))
