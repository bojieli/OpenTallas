#!/bin/bash
# HBM-FORM-SPLIT-13-TOPK: build vA / vB kit dirs from the SPLIT-12 copy of the Codex fresh_plane_v5 kit.
set -euo pipefail
SRC=/srv/opentallas-scratch2/claude/hbm-form-split-12/topk/fresh_plane_v5/ot_hbm_idx_topk_link_static_fa4a6c51ad35
REPO=/srv/opentallas-scratch3/claude/hbm-form-split-13-topk/repo
GQ=/srv/opentallas-scratch3/claude/hbm-form-split-13/gq/ot_hgi_gq_aq_tile_vC
TOP=/srv/opentallas-scratch2/claude/hbm-form-split-13/topk
RT=$REPO/rtl/hbm_accel/cores_split/reform_1105s/topk
for V in vA vB; do
  K=$TOP/ot_hbm_idx_topk_link_static_$V
  [ ! -e "$K" ] || { echo "exists $K"; exit 1; }
  mkdir -p "$K"
  rsync -a --exclude run/ --exclude lec/ --exclude lec_kit_failed24g/ --exclude physical_completion/ --exclude __pycache__/ \
    --exclude 'lec_async.done' --exclude 'lec_async.identity' --exclude 'lec_async.lock' --exclude 'lec_async.log' \
    --exclude 'lec_async.on' --exclude 'lec_async.owner' --exclude 'lec_async.rc' --exclude 'lec_async.ready' \
    --exclude 'lec_async.runs/' --exclude 'lec_async.source_identity' --exclude 'lec_run.log' --exclude 'run_*.log' \
    --exclude 'face_guard.json' --exclude 'face_guard.log' --exclude 'port_bind.json' --exclude 'port_bind.log' \
    --exclude 'rtl_lint.json' --exclude 'rtl_lint.log' --exclude 'rtl_lint.ys' --exclude 'selrange.json' --exclude 'selrange.log' \
    --exclude 'selrange.rc' --exclude 'sdc_lint.log' --exclude 'hold_census.txt' --exclude 'orfs_hold_mm.log' --exclude 'orfs_metrics.log' \
    --exclude 'FORM_SPLIT12_TOPK.txt' --exclude '.keep' --exclude 'macro_reg_guide*' "$SRC"/ "$K"/
  cp "$RT/ot_hbm_idx_topk_tiles.sv" "$RT/ot_hbm_idx_topk_link_pd3.sv" "$K/rtl/"
  sed -i 's/ot_hbm_idx_topk_link_pd3 #(.FILL_GROUPS(8)) u_core (/ot_hbm_idx_topk_link_pd3 #(.FILL_GROUPS(8), .WPIPE(1)) u_core (/' "$K/rtl/ot_hbm_idx_topk_link_static__wrap.sv"
  grep -q 'WPIPE(1)' "$K/rtl/ot_hbm_idx_topk_link_static__wrap.sv"
  # no reg guides in either form (the v5 guide boxes sat in the centre channel; released before DPL)
  sed -i 's|^source /work/macro_reg_guide.tcl$|# HBM-FORM-SPLIT-13-TOPK: no reg guides (source /work/macro_reg_guide.tcl removed)|' "$K/face_flops.tcl"
  sed -i 's|^source /work/macro_reg_guide_release.tcl$|# HBM-FORM-SPLIT-13-TOPK: no reg guides (source /work/macro_reg_guide_release.tcl removed)|' "$K/face_flops_release.tcl"
  ! grep -q '^source /work/macro_reg_guide' "$K/face_flops.tcl" "$K/face_flops_release.tcl"
  # face column pitch env override (default 40 unchanged), as HBM-FORM-SPLIT-13 gq_aq_tile vC
  sed -i 's/^set ff_cpitch \[expr {\$ff_sw \* 40}\]$/set ff_cpitch [expr {$ff_sw * ([info exists ::env(OT_FF_CPITCH_SITES)] ? $::env(OT_FF_CPITCH_SITES) : 40)}]/' "$K/face_flops.tcl"
  grep -q 'OT_FF_CPITCH_SITES' "$K/face_flops.tcl"
  # main orfs_hold_mm (reg2reg scope support), as gq_aq_tile vB/vC
  cp "$K/orfs_hold_mm.tcl" "$K/orfs_hold_mm.tcl.pre_hfs13topk"; cp "$K/orfs_hold_mm.py" "$K/orfs_hold_mm.py.pre_hfs13topk"
  cp "$GQ/orfs_hold_mm.tcl" "$GQ/orfs_hold_mm.py" "$K/"
  touch "$K/.keep"
done
python3 -I - "$TOP" <<'EOF'
import sys
top = sys.argv[1]
# y on the M4 pin track grid (0.048k + 0.012, as gen_core_kit_hbm snap); 4 rows, bottom band / 3 streets / top band ~43.2 um each
ys = [47.484, 168.444, 289.404, 410.364]
forms = {
 # vA (targeted): column x as before; uniform 43.2-um streets (were 11.7/22.7/11.7 um, the DPL pile-up); W column mirrored (MY)
 # so its rd_out + 266 wd_in pins face the centre channel with column E's read pins (tx lanes pair gm[l] with gm[4+l]).
 'vA': dict(xw=81.81, xe=397.17, ow='MY'),
 # vB (conservative): same streets + MY, both columns moved east: W band 4.3 -> 134.3 um (was 77) for the ingest logic beside the
 # 2,368-pin W face, centre channel 90 um, E band 79 um.
 'vB': dict(xw=134.298, xe=395.604, ow='MY'),
}
for v, f in forms.items():
    rows = []
    # west column gm[4..7], east column gm[0..3]; order bottom->top as before (6,7,5,4 / 2,3,1,0)
    for k, y in zip((6, 7, 5, 4), ys):
        rows.append('  {u_fcore.u_core.u_sto.gm\\[%d\\].mem} ot_sram_1r1w_64x512_m1_r2c2 %.3f %.3f %s' % (k, f['xw'], y, f['ow']))
    for k, y in zip((2, 3, 1, 0), ys):
        rows.append('  {u_fcore.u_core.u_sto.gm\\[%d\\].mem} ot_sram_1r1w_64x512_m1_r2c2 %.3f %.3f R0' % (k, f['xe'], y))
    txt = ('# HBM-FORM-SPLIT-13-TOPK %s macro placement (hand form; y on the M4 pin track grid 0.048k+0.012, x on the 0.054 site grid)\n'
           'foreach {inst master x y orient} {\n%s\n} {\n  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact\n}\n') % (v, '\n'.join(rows))
    open('%s/ot_hbm_idx_topk_link_static_%s/macro_placement.tcl' % (top, v), 'w').write(txt)
    for y in ys:
        assert abs(((y - 0.012) / 0.048) - round((y - 0.012) / 0.048)) < 1e-6
    for x in (f['xw'], f['xe']):
        assert abs(x / 0.054 - round(x / 0.054)) < 1e-6, x
print('macro placements written')
EOF
for V in vA vB; do
  K=$TOP/ot_hbm_idx_topk_link_static_$V
  {
    echo ""
    echo "# HBM-FORM-SPLIT-13-TOPK $V: port hold not padded at the dense W pin face (port I2R hold = NEEDS_PARENT class); reg2reg hold repaired."
    echo "export OT_HOLD_REPAIR_SCOPE = reg2reg"
    if [ $V = vB ]; then echo "export OT_FF_CPITCH_SITES = 64"; fi
  } >> "$K/config.mk"
done
echo done
