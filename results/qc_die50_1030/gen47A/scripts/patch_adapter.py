"""DIE-QC-50/gen47A: die-local patch of the copied DIE-QC-41/42 adapter (channel clock cells without a partition host)."""
import sys
p=sys.argv[1];s=open(p).read()
if '_G47A_CHANNEL' in s: print('already patched'); sys.exit(0)
old="""        if len(matches)!=1:raise ValueError(f'clock cell host is not unique: {name} {matches}')
        host=matches[0];r=rects[host]"""
new="""        if len(matches)>1:raise ValueError(f'clock cell host is not unique: {name} {matches}')
        # DIE-QC-50/gen47A: gen47 has clock cells on die channel rows (no partition host): no host outline clip,
        # every partition keep-out (+ io) still checked with the same halo
        if matches:host=matches[0];r=rects[host];own=byhost[host]
        else:host=None;r=(-1e9,-1e9,1e9,1e9);own=[row for v in byhost.values() for row in v];_G47A_CHANNEL.append(name)"""
assert s.count(old)==1;s=s.replace(old,new)
old2="            for x0,y0,x1,y1,tag in byhost[host]+io:"
assert s.count(old2)==1;s=s.replace(old2,"            for x0,y0,x1,y1,tag in own+io:")
old3="    return windows,net_windows,dict(radius_um=radius,host_and_macro_clipped=clipped,pins=len(windows),macro_halo_um=2.16)"
assert s.count(old3)==1;s=s.replace(old3,"    return windows,net_windows,dict(radius_um=radius,host_and_macro_clipped=clipped,pins=len(windows),macro_halo_um=2.16,channel_cells_no_host=sorted(_G47A_CHANNEL))")
old4="def access_windows(P,cells,nets,access,radius):"
assert s.count(old4)==1;s=s.replace(old4,"_G47A_CHANNEL=[]\n"+old4)
s=s.replace('"""Materialize an existing clock topology','"""[DIE-QC-50/gen47A copy of DIE-QC-41/42 fixed_tree_prov_f1d_r3.py; die-local patches by patch_adapter.py]\nMaterialize an existing clock topology',1)
open(p,'w').write(s);print('patched')
