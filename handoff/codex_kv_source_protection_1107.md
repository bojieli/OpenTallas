# KV captured-source protection — 2026-11-07 02:04 PST

Added 258 standard tab-format host/path/purpose rows to PROTECTED-DBS.txt. Each intel1/intel2 closure has 129 existing paths:10 restored indirect preferred HDL inputs,117 unique bind.f inputs (118 lines), the active bind_kv_q directory and asbuilt_kv_7da.json.

All paths were present on both hosts before protection. These are the current captured bind inputs used by the wave; no tentative output kits or whole checkout are protected by this addition.

Recovery source/hash manifest: /tmp/codex-watch-kv-1107/preferred_source_manifest.json. Full protection manifest: /tmp/codex-watch-kv-1107/protection_manifest.json. No source bytes, plan, gate, or failed verdict changed.

## Fixed PHY input continuation — 2026-11-07 02:10 PST

Restored the four declared w521 PHY BB/LEF/TT/FF files from the intact epyc5 captured source into intel1/intel2, and added eight exact source-input protection rows. Files total202659 bytes per host; no existing input overwritten, no PHY view fabricated. Epyc2 has no captured source root and was skipped after rsync refused the missing parent; no partial checkout created. Manifest: /tmp/codex-watch-kv-1107/phy_view_source_manifest.json.
