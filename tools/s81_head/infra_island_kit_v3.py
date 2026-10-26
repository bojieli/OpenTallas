#!/usr/bin/env python3
"""HEAD-CORE-LAT-R2 v3 kit (METHODOLOGY 12.3/12.8b): derive from a v2 kit dir (no run data copied).

Root cause of the v2 miss (elemB_c2 295.0 TT / 236.6 FF intrinsic vs 250 / 202.5): TritonCTS clustered 12920 register
sinks at 16 sinks / 20 um into 836 leaves, so the tree depth (10 BUFx24 stages, ~28 ps each TT) followed the cluster
COUNT, not the core geometry.  v3 sizes the leaf clusters from geometry (SIZE sinks / DIAM um, equal-load leaves), which
removes whole tree levels for every instance of the type; no padding, no trim, no clock ECO.

Contract fix (12.3, no early taps): the die delivers clk at the common latency T to the centre pin, so the kit SDC clk
source latency is 0 (was the CP2 early-tap -120) and the gate bound is T (250 TT / 202.5 FF).  postcts_gate.tcl parses
only '^export OT_VCLK_*', so the v2 'override export' lines were ignored and the stale 401.36/299.29 bound was used;
v3 rewrites the plain export lines.
usage: infra_island_kit_v3.py SRC_V2_KIT DST SIZE DIAM
"""
import os, re, shutil, sys

src, dst, size, diam = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
os.makedirs(dst, exist_ok=True)
for f in os.listdir(src):
    if f in ('run', 'trial.log') or f.startswith(('gate', 'cts_gate', 'sta_', '4_')):
        continue
    p = os.path.join(src, f)
    (shutil.copytree(p, os.path.join(dst, f), dirs_exist_ok=True) if os.path.isdir(p) else shutil.copy2(p, dst))

c = open(dst + '/config.mk').read()
c = re.sub(r'^(override )?export OT_VCLK_TT\s*\??=.*$', 'export OT_VCLK_TT = 250', c, flags=re.M)
c = re.sub(r'^(override )?export OT_VCLK_FF\s*\??=.*$', 'export OT_VCLK_FF = 202.5', c, flags=re.M)
c = re.sub(r'^override export CTS_ARGS\s*=.*$', '', c, flags=re.M)
c += f'''
# HEAD-CORE-LAT-R2 v3 (12.8b): leaf clusters sized from geometry ({size} sinks / {diam:g} um) -> tree depth set by
# geometry, not by the 16/20 cluster count; same structure every instance; no padding / trim / clock ECO.
override export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.5 -sink_clustering_max_diameter {diam:g} -sink_clustering_size {size} -balance_levels -dont_use_dummy_load
'''
open(dst + '/config.mk', 'w').write(c)

s = open(dst + '/constraint.sdc').read()
s, n = re.subn(r'^# CP2 early core tap.*\n', '# 12.3 common latency: die delivers clk at T to the centre pin, no early tap\n', s, flags=re.M)
s, m = re.subn(r'^set_clock_latency -source -clock clk -?[0-9.]+ \[get_ports \{clk\}\]$',
               'set_clock_latency -source -clock clk 0.0 [get_ports {clk}]', s, flags=re.M)
assert m == 1, 'clk source latency line not found'
open(dst + '/constraint.sdc', 'w').write(s)
print('v3 kit', dst, 'cluster', size, diam)
