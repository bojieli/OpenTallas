KW46 INCIDENT README -- qc-s28a/src28ap is RETIRED (do not use as a source for any row)

2026-11-12 (COORD ruling 08:1x PST): this tree is a link-overlay private src (DIE-QC-99 s28a, built by KW-FIX-45).
On 2026-11-12 15:58-15:59 UTC KW-FIX-46 ran `rsync -aH --ignore-existing <s28 base>/ src28ap/` on epyc8 and epyc9.
Because src28ap holds directory symlinks, rsync also wrote THROUGH them into
/srv/opentallas-scratch2/claude/kw43/src_qcsw2_hc0_por15c (155 new files, all byte-identical to the s28 base
/srv/opentallas-scratch2/claude/kw45/src_qc_s28_88018018ef; no existing file overwritten; ~13.6k dir mtimes reset).
Inside src28ap, ~86k (epyc8) / ~184k (epyc9) s28 base files were added where it had none; the 29.7k original files are
unchanged (sha256 -c). physical/common_flow became a real dir (77 link-target files + failfast_rules.py from the s28 base);
the old link is kept as physical/common_flow.link-kw46-1112.

COORD: LEAVE all added files in place. Delete nothing. No autoclean removal. The tree is RETIRED: cfg src_retired lists
it and kit_wave refuses any launch whose src/plan/kit_rtl is under it (SRC_RETIRED -> LAUNCH-SKIP). Its 22 QC items were
moved to dies.qwen_compute.item_inputs_retired_kw46 and build from the die s28 event src.

Exact lists (also in ~/coord/lanes/handoff/KW-FIX-46-28ap/ on intel2):
  KW46_28ap_before.txt      original src28ap file list (before the rsync)
  KW46_28ap_before.sha      sha256 of every original src28ap file
  KW46_28ap_newfiles.txt    the 155 files added in kw43/src_qcsw2_hc0_por15c
  KW46_28ap_wrote.txt       every entry (f/d) under link targets whose ctime changed 15:58-16:00 UTC
