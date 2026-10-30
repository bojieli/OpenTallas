"""Install explicit die-local hd_tile native8 packing into OWN generated kit."""
from pathlib import Path
import argparse,shutil,re
p=argparse.ArgumentParser();p.add_argument('--private-write-comb',action='store_true');p.add_argument('kit',type=Path);p.add_argument('--geom-tools',type=Path,required=True);p.add_argument('--core-hook',type=Path);a=p.parse_args();here=Path(__file__).parent;k=a.kit
for f in ['head_native_pack.py','head_native_hook.tcl']:shutil.copy2(here/f,k/f)
shutil.copytree(a.geom_tools,k/'head_native_tools',dirs_exist_ok=True)
f=k/'landing_placement.tcl';s=f.read_text();marker='# FLOW-KITFAIL-3'
m=re.search(r'\{u_cland_i\s+\{([^}]+)\}',s);assert m, 'requires explicit hd_tile u_cland_i band'
actual=list(map(float,m[1].split()));assert len(actual)==4 and all(abs(x-y)<1e-5 for x,y in zip(actual,[12.96,708.48,47.52,1008.512])), 'source-generated band.i must already be native8 candidate'
assert marker in s and 'source /work/head_native_hook.tcl' not in s
s=s.replace(marker,'source /work/head_native_hook.tcl\n'+marker,1)
# Own old copied kits need shared hard-block occupancy backport; current fixed helpers retain theirs.
if 'foreach hb $cland_hard {cland_occupy' not in s and 'cland_occupy {*}$hr' not in s:
 anchor='foreach spec $cland_groups {'
 at=s.index(anchor,s.index('set cland_hard'))
 s=s[:at]+'foreach hb $cland_hard {lassign $hb hx0 hy0 hx1 hy1;cland_occupy $hx0 $hy0 [expr {$hx1-$hx0}] [expr {$hy1-$hy0}]}\n'+s[at:]
f.write_text(s)
if a.private_write_comb:(k/'head_native_private_write_comb.enabled').write_text('typed exclusive-bit writer feedback placement\n')
if a.core_hook:
 shutil.copy2(a.core_hook,k/'head_tile_core.tcl')
 if 'source /work/tile6_repack.tcl' in a.core_hook.read_text():
  dep=a.core_hook.with_name('tile6_repack.tcl');assert dep.is_file(), 'tile6 core attachment requires sibling tile6_repack.tcl'
  shutil.copy2(dep,k/'tile6_repack.tcl')
 f=k/'face_flops.tcl';f.write_text(f.read_text()+'\nuplevel #0 {source /work/head_tile_core.tcl}\n')
print('Installed explicit HEAD native8 profile; generated band.i MUST already equal [12.96,708.48,47.52,1008.512].')
