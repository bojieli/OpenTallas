# QC-RRDRV-FIX handoff (11-25 00:45 PST)
Lane: fix the C1n "START raw reset rr_tN has no registered wavefront driver" class (child of QC-ALLFIX).
- ROOT CAUSE: CB-TAPBINS row 44c9f56d9edc (QC-CB-SPREAD-R2 apply_c1k.py -> retap.repoint) numbered START raws on the tap census
  at its apply time (cbf_q00 cl1b 145 taps). The bound C1m/C1n census is 101 for the same plan and bins (current tools), and 46/48 types differ.
- REVIEW C1n-r c26a5b81029d: FAIL. 2,288 kept raws had hops over 300 um and 34 sat on out/core points (list epyc2 QC-RRDRV-FIX/c1nr_far_raws.tsv 80bb77b49e5c).
- ROW RRDRV-FAR b6140412608d -> C1n-r2 a372ae84fa2a (epyc2 QC-RRDRV-FIX/far/). QC-CB-C1L built the same plan (row 4eb637e02688) and owns compose and bind.
- PRE: derived_drop.rrdrv_type (RSTREACH RRDRV), committed in intel1 lane clone 49ef68c307; validation in epyc2 QC-RRDRV-FIX/val/ (c1n / c1nr / c1nr2); then ot-push-main.
