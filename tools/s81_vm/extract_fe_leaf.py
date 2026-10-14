#!/usr/bin/env python3
"""Extract one VM FE hierarchy leaf (and the modules it instantiates) as a self-contained, preprocessed physical source,
the way physical/s81_fe_fcn_sumpipe/rtl/dsfd_vm_fcn.sv was made (claude s81-grpA r3, 2026-10-14; reproduces that file's
sha256 9375b9b7... bit-for-bit from its receipt commit 1cf582aee and defines).

    python3 tools/s81_vm/extract_fe_leaf.py --defines SYNTHESIS,OT_S81_ADAPTER_CMD_PIPE,OT_VMFE_FCN_SUM_PIPE,OT_SPVM_XGOS \
        --modules dsfd_vm_be_kreg,dsfd_vm_fob,dsfd_vm_fcn,ot_s81_engine_adapter,ot_s81_pulse_cdc,ot_async_fifo,ot_reset_sync,ot_dsrom_mtp_rstsync \
        --out physical/s81_fe_fcn_xgos

Method: Verilator 5.050 `-E -P` over the VM gate's source list (same order) with the given defines, then every listed module
cut verbatim (a preceding `(* ... *)` attribute line kept) and joined by one blank line.  Writes <out>/rtl/<leaf>.sv and
<out>/source_receipt.json (commit, defines, modules, sha256 of every source file and of the extraction)."""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
FILES = ['rtl/dsrom_sys/s81_ph/relays/dsfd_die_relays.sv', 'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv', 'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgq_sys.sv',
         'rtl/dsrom_sys/mtp/dsfd_vm_wfc_ep.sv', 'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_rtt.sv', 'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv',
         'rtl/dsrom_sys/mtp/rtt/ot_dsrom_mtp_rstsync.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv', 'rtl/lib/ot_async_fifo.sv',
         'rtl/lib/ot_reset_sync.sv', 'rtl/common/ot_ratio_cdc_fifo.sv', 'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_fe_h.sv']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--defines', required=True); ap.add_argument('--modules', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--leaf', default='dsfd_vm_fcn'); ap.add_argument('--verilator', default=str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
    a = ap.parse_args()
    defs, mods = a.defines.split(','), a.modules.split(',')
    cmd = [a.verilator, '-E', '-P'] + ['+define+' + d for d in defs] + ['-I' + str(ROOT / 'rtl/dsrom_sys/s81_ph/vm')] + [str(ROOT / f) for f in FILES]
    t = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    found = {}
    for m in re.finditer(r'^(?:\(\*[^\n]*\*\)[ \t]*\n)?module\s+(\w+).*?^endmodule', t, re.S | re.M):
        found.setdefault(m.group(1), m.group(0))
    miss = [n for n in mods if n not in found]
    if miss:
        sys.exit(f'modules not found after preprocessing: {miss}')
    txt = '\n\n'.join(found[n] for n in mods) + '\n'
    out = ROOT / a.out
    (out / 'rtl').mkdir(parents=True, exist_ok=True)
    (out / 'rtl' / f'{a.leaf}.sv').write_text(txt)
    commit = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    rec = {'schema': 'opentallas.physical-cpp-source.v1', 'commit': commit, 'tool': 'tools/s81_vm/extract_fe_leaf.py', 'defines': defs,
           'modules': mods, 'rtl_sources': {f: sha(ROOT / f) for f in FILES},
           'extracted_sha256': hashlib.sha256(txt.encode()).hexdigest(), 'mutant': any('MUT' in d for d in defs), 'reset_ack': 'OT_SPVM_RESET_ACK' in defs}
    (out / 'source_receipt.json').write_text(json.dumps(rec, indent=2) + '\n')
    print(rec['extracted_sha256'])


if __name__ == '__main__':
    main()
