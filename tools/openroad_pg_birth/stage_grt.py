#!/usr/bin/env python3
"""Install opt-in PG callback wrappers in an OWNED fresh kit copy, never a live kit.

The native module still validates the executable ABI and initial native PG state.
This staging step grants no physical release or sign-off credit.
"""
import argparse, hashlib, json, re, shutil
from pathlib import Path

DRIVER = '''# Run this driver with the normal GRT make target's loaded environment.
# PRE installs after load_design; this outer body also cleans up failed hooks.
set ot_pg_grt_code [catch {
  source $::env(SCRIPTS_DIR)/global_route.tcl
} ot_pg_grt_result ot_pg_grt_options]
set ot_pg_grt_cleanup_code 0
if {[info commands ot_native_pg_status] ne ""} {
  set ot_pg_grt_cleanup_code [catch {
    if {[dict get [ot_native_pg_status] active]} {ot_pg_native_birth_end}
  } ot_pg_grt_cleanup ot_pg_grt_cleanup_options]
}
if {$ot_pg_grt_code} {
  if {$ot_pg_grt_cleanup_code} {puts stderr "OT_PG_GRT_CLEANUP_REFUSED $ot_pg_grt_cleanup"}
  return -options $ot_pg_grt_options $ot_pg_grt_result
}
if {$ot_pg_grt_cleanup_code} {
  return -options $ot_pg_grt_cleanup_options $ot_pg_grt_cleanup
}
'''


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def hook(text, key, kit):
    values = re.findall(rf'^(?:override\s+)?export\s+{key}\s*(?:\?=|:=|=)\s*([^\n]*)$', text, re.M)
    value = values[-1].strip().split(' #', 1)[0].strip() if values else ''
    if not value:
        return None
    if not value.startswith('/work/') or any(c in value for c in '$[]{}\r\n \t'):
        raise ValueError('unsupported resolved hook: ' + key + '=' + value)
    path = kit / value.removeprefix('/work/')
    if not path.is_file() or not path.resolve().is_relative_to(kit):
        raise ValueError('missing/nonlocal original hook: ' + value)
    return dict(path=value, sha256=sha(path))


def stage(kit, module, helper):
    kit, module, helper = kit.resolve(), module.resolve(), helper.resolve()
    config = kit / 'config.mk'
    before = config.read_bytes()
    hooks = {k: hook(before.decode(), k, kit) for k in ('PRE_GLOBAL_ROUTE_TCL', 'POST_GLOBAL_ROUTE_TCL')}
    names = ['nativepgbirth.so', 'native_pg_birth_pre.tcl', 'native_pg_birth_post.tcl',
             'NATIVE_PG_BIRTH_ADAPTER.json', 'native_pg_binding.before_birth.tcl']
    names += ['native_pg_birth_global_route.tcl']
    if any((kit/n).exists() for n in names):
        raise ValueError('refuse existing PG callback adapter/output')
    if not module.is_file() or not helper.is_file():
        raise ValueError('missing native module/helper')
    pre = ('source /work/native_pg_binding.tcl\n'
           'if {![ot_pg_strict_enabled]} {error OT_PG_GRT_REQUIRES_STRICT_MODE}\n'
           'ot_pg_native_birth_begin /work/nativepgbirth.so\n')
    if hooks['PRE_GLOBAL_ROUTE_TCL']:
        pre += 'source {' + hooks['PRE_GLOBAL_ROUTE_TCL']['path'] + '}\n'
    post = ''
    if hooks['POST_GLOBAL_ROUTE_TCL']:
        post += 'source {' + hooks['POST_GLOBAL_ROUTE_TCL']['path'] + '}\n'
    post += 'ot_pg_native_birth_end\n'
    old_helper = kit / 'native_pg_binding.tcl'
    old_helper_sha = sha(old_helper) if old_helper.exists() else None
    if old_helper.exists():
        shutil.copy2(old_helper, kit/'native_pg_binding.before_birth.tcl')
    shutil.copy2(helper, old_helper)
    shutil.copy2(module, kit/'nativepgbirth.so')
    (kit/'native_pg_birth_pre.tcl').write_text(pre)
    (kit/'native_pg_birth_post.tcl').write_text(post)
    (kit/'native_pg_birth_global_route.tcl').write_text(DRIVER)
    config.write_bytes(before + b'\n# Explicit native PG birth callback adapter; original hook bodies retained.\n'
        b'override export PRE_GLOBAL_ROUTE_TCL = /work/native_pg_birth_pre.tcl\n'
        b'override export POST_GLOBAL_ROUTE_TCL = /work/native_pg_birth_post.tcl\n')
    receipt = dict(schema='opentallas.native-pg-grt-adapter.v1', status='STAGED_NOT_RUN',
        config_before_sha256=hashlib.sha256(before).hexdigest(), config_after_sha256=sha(config),
        original_hooks=hooks, original_helper_sha256=old_helper_sha,
        files={n:sha(kit/n) for n in names[:3] + ['native_pg_binding.tcl', 'native_pg_birth_global_route.tcl']},
        required_driver='/work/native_pg_birth_global_route.tcl', required_env={'OT_PG_STRICT':'1'},
        dispatch_ready=False,
        scope='Opt-in fresh-copy GRT/MM process only; no CTS/detail-route/child-process coverage claim',
        source_rtl_changed=False, original_provenance_overwritten=False, physical_release=False)
    (kit/'NATIVE_PG_BIRTH_ADAPTER.json').write_text(json.dumps(receipt, indent=1)+'\n')
    return receipt


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kit',type=Path,required=True);p.add_argument('--module',type=Path,required=True)
    p.add_argument('--helper',type=Path,default=Path(__file__).parents[2]/'physical/common_flow/native_pg_binding.tcl')
    a=p.parse_args();print(json.dumps(stage(a.kit,a.module,a.helper),indent=1))
