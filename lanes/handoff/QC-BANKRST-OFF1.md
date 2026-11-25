# QC-BANKRST-OFF1 handoff (parent QC-ALLFIX), updated 2026-11-25 06:3x PST
- Finding: bank_reset_delta.bank_xy put ft station k at regs_um[k]; landed slots seat station k at plan stage k+1 (last = out face). Proof V4 sle_su_l1__cl5ea486db cws0 lst<i> = bit_sites_um[i].
- Tool fix pushed main aac2fa2ef5 (ft_station_xy + tests). Lane clone epyc12 /srv/opentallas-scratch2/claude/QC-BANKRST-OFF1/repo.
- CENSUS posted 06:18: excl sle_su_l1 x2, 38 types / 364 landed banks, 255 over 275 um in 32 types. Table epyc12 /srv/opentallas-scratch2/claude/QC-BANKRST-OFF1/out/census4_v13.json.
- Row BANKRST-LAND (C1p) base C1o v13 aa3a14fb7484 -> 93fa00b39e96, 32 types, 258 banks moved, worst after 183.4 um, 0 still over, idempotent. Row json 2c63b156d8a7 (hub lanes/handoff/QC-BANKRST-OFF1-row_bankrst_land.json), script hub QC-BANKRST-OFF1-bankrst_land.py.
- PRE: epyc12 /srv/opentallas-scratch2/claude/QC-BANKRST-OFF1/pre.sh -> pre.ot, out/pre.log (launch_b716_sul1). Scoped strict bind: /srv/opentallas-scratch2/claude/QC-BANKRST-OFF1/pre_bind_full.sh, run after "BIND-PASS C1o v13 aa3a14fb7484".
- Not done: KV / S81 census of the same offset (tool is die-agnostic; ft_xtap.station_sites has the same landed offset, advisory).
