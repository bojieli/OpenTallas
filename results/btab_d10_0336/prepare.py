from pathlib import Path
import sys,json,shutil
w=Path('/srv/opentallas-scratch2/claude/wt/codex-btab-0336');k=Path('/srv/opentallas-scratch2/claude/codex-btab-0336/variantB')
sys.path.insert(0,str(w/'tools/die_plan'));import core_infra as C
sl=json.loads((w/'results/qc_die43_1030/btab/D10_kit_ko_m/qfd_dv_s8x_btab/slice/qfd_dv_s8x_btab.json').read_text())
sl.pop('cell_placements',None)
sl['core_tree']['install_stage']='pre_cts'
(k/'D10_slice.json').write_text(json.dumps(sl,indent=2)+'\n')
C.install(k,sl)
cfg=(k/'config.mk').read_text().splitlines()
# Existing H13 has no clock tree installed; install D10 on its actual unchanged placement.
# Exact D10 cell placements are FIRM; check_placement rejects any occupancy conflict.
(k/'hold_budget_d10.tcl').write_text('source /work/hold_budget.tcl\nsource /work/master_core_infra.tcl\n')
cfg.append('override export PRE_CTS_TCL = /work/hold_budget_d10.tcl')
C.kit_cts_hook(k,cfg)
(k/'config.mk').write_text('\n'.join(cfg)+'\n')
r=w/'results/geom_review/btab_d10B_0336';r.mkdir(parents=True,exist_ok=True)
shutil.copy(w/'results/qc_die43_1030/btab/D10_kit_ko_m/qfd_dv_s8x_btab/qfd_dv_s8x_btab_r13.png',r/'tree.png')
(r/'review.json').write_text(json.dumps({'verdict':'PASS-COND','scope':'D10 CTS trial only','picture':'tree.png','viewed':True,'findings':['Centre entry fans out through open N/S/centre SRAM corridors. Four reserved islands avoid SRAM body keepouts; same H13 actual placement census 4536 sinks.','199 short leaf groups, max 25.64 um sink spread; all 273 branch legs within model reach, max first leg 170.1 um.','Wide data interfaces retain H13 placement and macro anchors; no data cycles or RTL edits. Variant A fixed-clock install failed 398 padding overlaps with data FFs. Variant B uses shared late incremental DPL, holding data logic FIRM and moving only new clock cells up to 20um; topology and sink membership unchanged.','Macro pin corridor M4 DRC history remains open and requires routed check; actual TT/FF timing and PDN continuity not inferred from model.'],'predicted_TT_mean_ps':259.58,'predicted_FF_mean_ps':199.93},indent=2)+'\n')
