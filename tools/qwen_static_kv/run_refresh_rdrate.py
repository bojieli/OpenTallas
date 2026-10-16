#!/usr/bin/env python3
"""Source-pinned actual-controller discovery, compiled replay and hardware mutant."""
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = 'rtl/qwen_sys/static_kv_20261014/ot_qkd_static_kv_timing.sv'
TB = 'rtl/test/qwen_static_kv/tb_kv_refresh_rdrate.sv'
WRAPPER = 'rtl/qwen_sys/static_kv_20261014/ot_qkd_static_ctrl_pc_emb.sv'


def main():
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('out')
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    src = out/'source'
    src.mkdir(exist_ok=True)
    manifest = {}
    for name in (CORE, TB, WRAPPER):
        data = (ROOT/name).read_bytes()
        (src/Path(name).name).write_bytes(data)
        manifest[name] = hashlib.sha256(data).hexdigest()
    text = (src/Path(CORE).name).read_text()
    old = 'assign rd_ok = legal_rd && (PROFILE == 1 || reserved_rd);'
    assert text.count(old) == 1
    mut = src/'mutant_timing.sv'
    mut.write_text(text.replace(old, old.replace(';', ' && (ref_c > 8);')))
    vlt = src/'hier.vlt'
    vlt.write_text('`verilator_config\nhier_block -module "ot_qkd_static_kv_timing"\n')
    def build(tag, profile, mutated=False):
        obj = out/('obj_'+tag)
        compiler = os.environ.get('VERILATOR', str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
        cmd = [compiler, '--binary', '--timing', '--hierarchical', '-j', '2',
               '--build-jobs', '16', '--output-groups', '16', '-Wno-fatal',
               '--top-module', 'tb_kv_refresh_rdrate', f'-GPROFILE={profile}',
               '--Mdir', str(obj), str(vlt),
               str(mut if mutated else src/Path(CORE).name), str(src/Path(TB).name)]
        with (out/(tag+'.build.log')).open('w') as f:
            subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=True)
        return obj/'Vtb_kv_refresh_rdrate'
    def run(tag, binary, *args):
        r = subprocess.run([str(binary), *args], text=True, capture_output=True)
        (out/(tag+'.log')).write_text(r.stdout+r.stderr)
        (out/(tag+'.exit')).write_text(str(r.returncode)+'\n')
        return r
    discovery = run('discovery', build('discovery', 1))
    assert discovery.returncode == 0, 'actual discovery bench failed'
    records = re.findall(r'INST pc(\d+) off(\d+) first_after_go (-?\d+) span (\d+) lost (-?\d+)', discovery.stdout)
    assert len(records) == 236, len(records)
    slots = [0]*2118
    for pc, off, first, span, lost in records:
        pc, off, first, span, lost = map(int, (pc, off, first, span, lost))
        if span != 256 or lost != 0:
            raise RuntimeError(f'zero-RD-block refresh model falsified: pc{pc} phase{off} span{span} lost{lost}')
        for cycle in range(600+off+first, 600+off+first+256):
            slots[cycle] |= 1 << (pc*118+off)
    image = out/'compiled_slots.hex'
    image.write_text(''.join(f'{x:059x}\n' for x in slots))
    production = run('production', build('production', 0), '+SLOTS='+str(image))
    assert production.returncode == 0 and 'PASS kv refresh rdrate' in production.stdout
    negative = run('mutant', build('mutant', 0, True), '+SLOTS='+str(image))
    assert negative.returncode != 0 and 'FAIL kv refresh rdrate' in negative.stdout, 'hardware mutant escaped'
    receipt = dict(scope='actual timing-controller 118 phases x two PC parities; compiled strict PROFILE0 replay',
                   source_sha256=manifest, contexts=236, sectors_each=256,
                   parameters=dict(SROW=1,READY_CUT=1,WR_EN=1,AQ_RD=0,PULLIN=0,REF_MODE=1),
                   static_and_write_queue_stimulus="idle during pure K read pass",
                   refresh_rd_block_hbm=0, first_read_after_go_hbm=sorted({int(x[2]) for x in records}), compiled_image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
                   production_exit=production.returncode, mutant_exit=negative.returncode,
                   mutant='extra ref_c<=8 read blocker; actual RTL permission differs from reserved slots',
                   full_memory_data_path=False, native_full_layer=False, native_full_token=False)
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
