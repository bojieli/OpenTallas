# DS-ROM wavefront verify, RTL (claude/dsrom-wavefront-rtl-20261004)
Vehicle: reduced V4.1 (40 layers, dim 160), all-unit core, KV and index keys in modelled HBM.
One stage in isolation: package = layer 20 (CSA producer + index scan) of the split [0..19][20][21..39].
```
python3 tools/dsrom_wavefront_rtl_campaign.py prepare --scratch D            # local: golden.json (+ whole-array images)
python3 tools/dsrom_wavefront_rtl_campaign.py prepare-stage --scratch S --gold D/golden.json
python3 tools/dsrom_wavefront_rtl_campaign.py run-stage --scratch S           # Verilator 5.050; OT_WF_STAGE_WAVE=0 = control
python3 tools/dsrom_wavefront_rtl_campaign.py compose --scratch S --output record.json
```
Jobs fed back to back: positions 0, 1, 2, 3 (corrupted input), 3 (re-issue), 4. record.json: per-job busy/entry gap/handoff,
K/V and index-key write-to-visible, exactness, the S81 composition and the verdict. out_*_killed_prefix.txt: the
whole-array 5-package runs, stopped by owner decision (prefix only).
