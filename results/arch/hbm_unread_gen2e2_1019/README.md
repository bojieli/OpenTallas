# GEN2e2 unread manifest candidate (LH-UNREAD, 10-19)

Die: GEN2e2 S1 strict bind die `artifacts/hdie-d4/d4g_gen2e2/pb0/die.v` (sha e953ed7c...), contract `net/pre_relay.json` (fd7492f2...), source 6f783d0a1.
Default strict bind (main tools/die_port_bind.py): all structural classes 0, unread 70,320 FAIL (`default_bind.log`).

Exact re-derivation against the ROOT-admitted d517 review (reviews/hbm_unread_scoped_root_1019.json, manifest 2beccb8e...):
- die.v differs from the reviewed d517 die by ONE line: `col_idx` master ot_hbm_static_cfg_collar -> ot_hbm_static_cfg_collar_idx256 (same params).
- contract differs only in instances.col_idx (master/source/note/rtl_deps, l19) and the col_idx strap master name.
- exact unread map (782 nets / 70,320 bits) and consumer map identical (`unread_gen2e2_exact.json`).
- all 216 pinned/selected source files byte-identical at 6f783d0a1; added pin = collar_idx256 (adds only install-depth sticky-fault guards; `rec`/`prm` drivers unchanged).
=> all 309 entries / 65,066 bits match exactly per instance/port/range; only the col_idx `rec` entry is re-pointed to the idx256 master (renewed review note in its evidence).

`review_gen2e2_candidate.json` (sha 40ac1823...) -> API proposal `manifest_proposal_gen2e2.json` sha **da78841d70e295c26c4c38a261b36b8be22813e1317218e83fb38af7e9cfd537**.
Replay with that digest: 65,066 admitted, unread 5,254 -> strict FAIL remains (`replay_manifest.log`). CANDIDATE: needs ROOT digest admission; not admitted by this lane.

Negatives (`tools/hbm_die_v16/unread_gen2e2_negatives.py`, `negatives.json`): P0 positive 5254; N1 stale d517 die REFUSED; N2 real fault
consumer dropped (hleaf_NE.t_fault loses calendar_NE__fault), re-stamped -> FAIL 5255; N3 relay payload hidxr_NE_rr2__o[0] dropped,
re-stamped -> FAIL 5255; N4 range widened onto consumed payload bit -> REFUSED occupied; N5 one-byte selected-source drift -> REFUSED; N6 d517 digest -> REFUSED.
