#!/usr/bin/env python3
"""STW-S81-LAND 10-21: pre-layout mapped synthesis + mandatory native census (tools/ref_tile/native_census.py, max 32)
for the elements the MU72 lane landing changes, at their die parameters:
  lnland   ot_s81_mu72_lnland (two ot_s81_mu72_land, 556 b K->N / 559 b N->K)
  lepa12   ot_s81sl_lep_mu_a  #(CRED 12, DR 12)                      (s_0S / s_7S u_lep)
  leph12   ot_s81sl_lep_mu_h  #(CRED 12, DR 12)                      (s_7N u_lep)
  lepab12  ot_s81sl_lep_mu_ab #(CRED 12, DR 12, RX_SRAM 1, IN_PIPE 1, NATIVE32 1)   (s_0N u_lep)
  lepa12n / leph12n  the same with RX_SRAM / IN_PIPE / NATIVE32 1 (the s_0N native options)
  and the same three leps at CRED / DR 8 (the current die) as the baseline, so a CRED12-only regression is visible.
The CRED12 lanes (dsfd_coll_lane_{w,e}_safe8_ntf #(CORE_CRED 12)) are the CLOSED/gated s12g kits (Codex f5bcbdfbe
native PASS 32/0) and are not re-run.  Usage (cwd = repo root): mu72_lnland_native.py OUTDIR NAME"""
import hashlib, json, subprocess, sys
from pathlib import Path

root = Path.cwd()
LEP_SRC = ['rtl/lib/ot_rst_relay_tree3.sv', 'rtl/lib/ot_sram_oldread_wreg.sv', 'rtl/lib/ot_sram_showahead_1r1w.sv',
           'rtl/lib/ot_rst_relay.sv', 'rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv', 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv']
LEP_MAC = ['physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1', 'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2',
           'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2']
LEP_KEEP = ['ot_sram_showahead_hit5', 'ot_s81sl_lep_rx_control', 'ot_s81sl_lep_host_event', 'ot_s81sl_lep_tx_push',
            'ot_s81sl_lep_stamp', 'ot_s81sl_lep_vcopy', 'ot_s81sl_lep_pair_ready', 'ot_s81sl_lep_return8',
            'ot_sram_showahead_readptr']
LAND_SRC = sorted(str(p.relative_to(root)) for p in (root / 'rtl/common/landed_parent').glob('*.sv')) + [
    'rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81_mu72_land.sv', 'rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81_mu72_lnland.sv']
AB = {'RX_SRAM': 1, 'IN_PIPE': 1, 'NATIVE32': 1}
JOBS = {
    'lnland': ('ot_s81_mu72_lnland', {}, LAND_SRC, [], []),
    'lepa12': ('ot_s81sl_lep_mu_a', {'CRED': 12, 'DR': 12}, LEP_SRC, LEP_MAC, LEP_KEEP),
    'leph12': ('ot_s81sl_lep_mu_h', {'CRED': 12, 'DR': 12}, LEP_SRC, LEP_MAC, LEP_KEEP),
    'lepab12': ('ot_s81sl_lep_mu_ab', {'CRED': 12, 'DR': 12, **AB}, LEP_SRC, LEP_MAC, LEP_KEEP),
    'lepa12n': ('ot_s81sl_lep_mu_a', {'CRED': 12, 'DR': 12, **AB}, LEP_SRC, LEP_MAC, LEP_KEEP),
    'leph12n': ('ot_s81sl_lep_mu_h', {'CRED': 12, 'DR': 12, **AB}, LEP_SRC, LEP_MAC, LEP_KEEP),
    'lepa8': ('ot_s81sl_lep_mu_a', {}, LEP_SRC, LEP_MAC, LEP_KEEP),
    'leph8': ('ot_s81sl_lep_mu_h', {}, LEP_SRC, LEP_MAC, LEP_KEEP),
    'lepab8': ('ot_s81sl_lep_mu_ab', AB, LEP_SRC, LEP_MAC, LEP_KEEP),
}
out = Path(sys.argv[1]).resolve() / sys.argv[2]; out.mkdir(parents=True, exist_ok=True)
top, params, srcs, macros, keep = JOBS[sys.argv[2]]
libs = sorted((Path.home() / '.local/opentallas-pdk-asap7/lib/NLDM').glob('*RVT_TT*.lib'))
assert len(libs) == 5, libs
dff = next(p for p in libs if '_SEQ_' in p.name)
srcs = [Path(p) for p in srcs] + [Path(m) / (Path(m).name + '_bb.v') for m in macros]
script = ['read_verilog -sv ' + str(root / p) for p in srcs]
script += ['hierarchy -top ' + top + ''.join(f' -chparam {k} {v}' for k, v in sorted(params.items())), 'hierarchy -check -top ' + top]
script += ['setattr -mod -set keep_hierarchy 1 ' + m for m in keep]
script += ['tcl ' + str(root / 'physical/common_flow/ot_keep_regs.tcl'), 'synth -top ' + top + ' -flatten',
           'dfflibmap -liberty ' + str(dff), 'abc ' + ' '.join('-liberty ' + str(p) for p in libs) + ' -D 833.333',
           'splitnets -ports', 'opt_clean -purge', 'write_verilog -noattr ' + str(out / 'mapped.v'),
           'tee -o ' + str(out / 'stat.txt') + ' stat ' + ' '.join('-liberty ' + str(p) for p in libs)]
(out / 'synth.ys').write_text('\n'.join(script) + '\n')
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
(out / 'inputs.json').write_text(json.dumps({'top': top, 'parameters': params, 'keep_modules': keep,
    'sources': {str(p): h(root / p) for p in srcs}, 'libs': {str(p): h(p) for p in libs}}, indent=1) + '\n')
with (out / 'synth.log').open('w') as f:
    subprocess.run([str(Path.home() / '.local/opentallas-tools/yosys-0.68/bin/yosys'), '-s', str(out / 'synth.ys')],
                   stdout=f, stderr=subprocess.STDOUT, check=True)
cmd = [sys.executable, 'tools/ref_tile/native_census.py', '--netlist', str(out / 'mapped.v'), '--top', top,
       '--out', str(out / 'native_census.json')]
for p in libs + [Path(m) / (Path(m).name + '_tt.lib') for m in macros]:
    cmd += ['--liberty', str(p)]
r = subprocess.run(cmd, capture_output=True, text=True)
(out / 'census.log').write_text(r.stdout + r.stderr)
print(r.stdout[-1500:])
print(('NATIVE_SYNTH_CENSUS_PASS ' if r.returncode == 0 else 'NATIVE_SYNTH_CENSUS_FAIL ') + sys.argv[2], flush=True)
sys.exit(r.returncode)
