#!/usr/bin/env python3
"""KV-TOK 10-26: the native HOST loader takes its boot-image length table from the die dispatcher's ABI parameters.

COORD RULING KV-TOK boot (12:32): no hand-set constants at the instance.  The HOST rank-services loader
(qkd_host_program_loader_target u_program) gets MU = the MU root's own MU and AGES = BOOT_AGES; BOOT_AGES is threaded
through the OBSX rank services / root and the C45 HOST wrapper (default 0 = unchanged for every other user), and the
native mission preparation sets it at the HOST instance from the AGES parameter of the die's own native dispatcher
(qkd_static_kv_boot_dispatch_mu_* u_boot), the same value native_boot_ages.control writes.  tools/qwen_static_kv/
boot_abi.check then evaluates the dispatcher and the loader functions from the staged text and refuses any mismatch
with the image builder table.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'qwen_static_kv'))
import boot_abi  # noqa: E402

LOADER = 'qkd_host_program_loader_target u_program('
LOADER_NEW = 'qkd_host_program_loader_target #(.MU(MU),.AGES(BOOT_AGES)) u_program('
RANK = 'qkd_host_rank_services_admission_obsx #(.MU(1),'
RANK_NEW = 'qkd_host_rank_services_admission_obsx #(.BOOT_AGES(BOOT_AGES),.MU(1),'


def _module_span(text, name):
    i = text.index(f'module {name} ')
    return i, text.index('endmodule', i)


def _add_param(text, module, anchor=',parameter integer MU=1)('):
    i, j = _module_span(text, module)
    m = text[i:j]
    if 'parameter integer BOOT_AGES=0' in m[:m.index(')(') + 2]:
        return text
    k = m.index(')(') + 2
    head = m[:k]
    if head.count(anchor) != 1:
        raise ValueError(f'{module}: parameter anchor {anchor!r} found {head.count(anchor)}x')
    head = head.replace(anchor, anchor[:-2] + ',parameter integer BOOT_AGES=0)(')
    return text[:i] + head + m[k:] + text[j:]


def _once(text, module, old, new):
    i, j = _module_span(text, module)
    m = text[i:j]
    if new in m:
        return text
    if m.count(old) != 1:
        raise ValueError(f'{module}: anchor {old[:60]!r} found {m.count(old)}x')
    return text[:i] + m.replace(old, new) + text[j:]


def obsx(text):
    """rtl/qwen_sys/kv_host_obs_20261019/qkd_host_root_admission_obsx.sv"""
    text = _add_param(text, 'qkd_host_rank_services_admission_obsx')
    text = _once(text, 'qkd_host_rank_services_admission_obsx', LOADER, LOADER_NEW)
    text = _add_param(text, 'qkd_host_root_admission_obsx')
    return _once(text, 'qkd_host_root_admission_obsx', RANK, RANK_NEW)


def c45(text):
    """physical/die_plan/qwen_kvsys/bind/kv45/qkd_host_root_admission_obsx_bo1_c45.sv (after native_host_start_gate)"""
    a = 'parameter integer REQUIRE_MISSION_START=0)(' if 'REQUIRE_MISSION_START=0)(' in text else 'parameter integer D2D_BOOT_ORDER=0)('
    text = _add_param(text, 'qkd_host_root_admission_obsx_bo1_c45', anchor=a)
    return _once(text, 'qkd_host_root_admission_obsx_bo1_c45', RANK, RANK_NEW)


def dispatcher_ages(ctl_text):
    _, p = boot_abi.inst_params(ctl_text, r'qkd_static_kv_boot_dispatch_mu_\w+', 'u_boot')
    if 'AGES' not in p:
        raise ValueError('native dispatcher u_boot has no AGES parameter (run native_boot_ages.control first)')
    return p['AGES']


def host_instance_params(params_text, ages):
    """the parameter list text of the HOST instance -> with .BOOT_AGES(ages) (replaces an existing value)"""
    if re.search(r'\.BOOT_AGES\(\s*\d+\s*\)', params_text):
        return re.sub(r'\.BOOT_AGES\(\s*\d+\s*\)', f'.BOOT_AGES({ages})', params_text)
    return params_text + f', .BOOT_AGES({ages})'


def loader_params(obsx_text, c45_text, host_params):
    """Effective qkd_host_program_loader_target parameters at u_host...u_program, read from the staged HOST texts:
    an un-threaded loader keeps its defaults (MU 0 / AGES 0 = the legacy 327 / 77 table)."""
    i, j = _module_span(obsx_text, 'qkd_host_rank_services_admission_obsx')
    rank = obsx_text[i:j]
    m = re.search(r'qkd_host_program_loader_target\s*(#\s*\((.*?)\))?\s*u_program\s*\(', rank, re.S)
    if not m:
        raise ValueError('boot ABI: no loader u_program in the OBSX rank services')
    if not m.group(1):
        return {}
    bind = dict(re.findall(r'\.(\w+)\s*\(\s*(\w+)\s*\)', m.group(2)))
    i, j = _module_span(c45_text, 'qkd_host_root_admission_obsx_bo1_c45')
    c = c45_text[i:j]
    rk = re.search(r'qkd_host_rank_services_admission_obsx\s*#\s*\((.*?)\)\s*\w+\s*\(', c, re.S)
    rank_bind = dict(re.findall(r'\.(\w+)\s*\(\s*(\w+)\s*\)', rk.group(1))) if rk else {}
    rank_dflt = boot_abi.module_defaults(rank)
    c45_dflt = boot_abi.module_defaults(c)

    def at_rank(name):                       # value of a rank-services parameter as bound by the C45 wrapper
        v = rank_bind.get(name)
        if v is None:
            return rank_dflt.get(name, 0)
        if v.isdigit():
            return int(v)
        return int(host_params.get(v, c45_dflt.get(v, 0)))

    out = {}
    for k, v in bind.items():
        out[k] = int(v) if v.isdigit() else at_rank(v)
    return out


def check_texts(ctl, face, loader, lparams):
    eff, disp = boot_abi.dispatcher_table(ctl, face)
    ld = boot_abi.loader_table(loader, dict(lparams))
    img = boot_abi.image_words(mu=bool(eff.get('MU', 0)), ages=bool(eff.get('AGES', 0)))
    return eff, disp, ld, img, boot_abi.check(disp, ld, img)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('check', help='fail on dispatcher / loader / image length mismatch')
    c.add_argument('--ctl', type=Path, required=True, help='qkd_kvs_ctl_nc32.sv (native dispatcher instance u_boot)')
    c.add_argument('--face', type=Path, required=True, help='qkd_kv_ctl_nc32_face.sv (dispatcher modules)')
    c.add_argument('--loader', type=Path, required=True, help='qkd_host_program_loader_target.sv')
    c.add_argument('--obsx', type=Path, required=True, help='qkd_host_root_admission_obsx.sv (rank services + loader)')
    c.add_argument('--c45', type=Path, required=True, help='qkd_host_root_admission_obsx_bo1_c45.sv')
    c.add_argument('--host', type=Path, required=True, help='source holding the C45 HOST instance (u_host / host)')
    a = ap.parse_args()
    ht = a.host.read_text()
    m = re.search(r'qkd_host_root_admission_obsx_bo1_c45\s*#\s*\((.*?)\)\s*(?:u_host|host)\s*\(', ht, re.S)
    if not m:
        raise SystemExit('boot ABI check: no C45 HOST instance in ' + str(a.host))
    hp = {k: int(v) for k, v in re.findall(r'\.(\w+)\s*\(\s*(\d+)\s*\)', m.group(1))}
    lp = loader_params(a.obsx.read_text(), a.c45.read_text(), hp)
    eff, disp, ld, img, errs = check_texts(a.ctl.read_text(), a.face.read_text(), a.loader.read_text(), lp)
    print(f'dispatcher MU {eff.get("MU")} AGES {eff.get("AGES")} NRST {eff.get("NRST")} DIECAP {eff.get("DIECAP")}; '
          f'host BOOT_AGES {hp.get("BOOT_AGES", 0)}; loader params {lp or "defaults"}')
    for t in boot_abi.TARGETS:
        print(f' target {t:2d}: dispatcher {disp[t]:5d} loader {ld[t]:5d} image {img[t]:5d}')
    if errs:
        print('BOOT_ABI FAIL\n ' + '\n '.join(errs))
        sys.exit(1)
    print('BOOT_ABI PASS')
