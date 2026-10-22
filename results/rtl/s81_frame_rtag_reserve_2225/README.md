# RTAG frame reservation

The larger exact RTAG request is 116.64 by 246.24 um. Its 1,025 north pins move up 47.52 um; 2,247 other local coordinates stay unchanged. This packet reserves its body in future h9 and h10 successors. It does not replace any current frame source or CLOSED view.

Keeping existing origins causes 4.32 um overlaps with two raw ROMs at each interior front. Moving only these ROMs up 43.2 um causes a 2.472 um overlap with the next Q child, so that local repair was rejected. Instead, each interior front inserts a full 43.2 um row above it. Every body whose old origin is on or above the listed cut moves up one row, cumulatively. One additional top row retains clearance for the last front. Every move is listed in reservation.json.

The conservative reservation is h9 1436.832 by 3499.2 um; h10 MAIN 1782.432 by 3844.8 um; h10 fallback 1609.632 by 3844.8 um. The widths remain unchanged. These are sufficient reserved outlines, not a proof of mathematical minimum. All 220 h9 bodies and 235 bodies in each h10 case have no pairwise bounding-box overlap and remain in bounds.

Source authority and SHA256 are pinned in authority.json. The check reads the actual source LEFs, including 38.04 by 62.352 um ROMs, and applies orientation before checking. The new child remains a request without qualification. New parent ABI/source composition, exact pin projection, clock and reset paths, 405 um data reach, GEN, CTS and route must be measured before qualification. Parent pin identities must retain their logical link index; no uniform face reprojection is authorized by this packet. No RTL or registered edge changed here.
