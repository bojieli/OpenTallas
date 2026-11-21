# qkd_ahub clock-pin ECO review, 21 November 2026

Viewed candidate B on the actual retained routing geometry near ck[5]. The M5 pin extends 0.20 µm on the same track under the adjacent M6 PG stripes. Pin access produced zero macro pins without an access point for this probe. The local DRC check found zero violations, and its positive control found seven. The full raw DRC reports match between the comparison arms.

Fresh finishing of the edited filled database kept TT setup +7.91 ps and FF hold +2.47 ps. Signoff reported DRC and antenna zero, 631 out of 631 pin audits, and retained exact routed LEC. The clock gate remains incomplete for ot_nhb_zh and ot_qkh_recip_leaf in both timing corners. The original parent has the same incomplete clock gate, and its old aggregate timing models do not supply the missing descendant clock evidence. This geometry review applies to the private candidate. A parent route requires a qualified view and a review of the new consuming kit.

[Actual clock pin geometry](qkd-ahub-ck5-1121.png)
