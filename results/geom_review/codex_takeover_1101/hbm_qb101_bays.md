# HBM Q_B101 clock-bay proposal — independent review

Verdict: FAIL structural for the full proposal; clock-contact-only geometry is conditionally reasonable.

Image personally viewed: `/home/ubuntu/coord/tmp/codex-hbm-d44r-2039/latF_tracks_review.png`. Its Q_B101 and Q_B101_NW panels show the proposed horizontal gaps and 89 named clock contacts; the root panel explicitly retains 88 failing contacts and is not qualified. Read the actual `q_b101_bays_types.json` partition types and compare their unchanged native `ft_slots[].bit_sites_um` against the shifted hard-core rectangles. The prior `latA.json` has zero sites inside hard cores for both types.

The proposed row-pitch change creates 673 overlaps among 12,832 Q_B101 native FT sites and 2,195 among 12,276 Q_B101_NW sites. Example Q_B101 L12x1 bank 0 bit 1723 at (520.56,793.53) is inside `u_hb_idx__s_Q_r0c3_k1h1`; Q_B101_NW bank 0 bit 398 at (516.24,594.81) is inside `u_hb_idx__s_Q_r0c3_k0h0`. See `hbm_qb101_ft_overlap.json` for counts and samples.

Cause: moving the hard-core rows to create clock bays leaves the existing native FT banks in place, so the moved footprints consume their sites. Revise those banks with actual per-bit hops <=405 um and legal macro/halo clearance, including source/destination entry/exit checks, or use another bay scheme. Review the revised image and actual coordinates before routing. Clock load/radius results cannot qualify this data geometry.
