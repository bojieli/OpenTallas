# S81 SerDes t4 early encoder scope review

Reviewed the retained SerDes t4 placement and density for the independent d0–d2 scope. This arm keeps the reviewed placed checkpoint, PMA walls and reset selection used in the previous two CTS screens. The new candidates remain in the encoder region beneath the north macro channels. Baseline placed endpoints and tap anchors show a legal shared root for the five witnessed early hold paths, each under 85 µm between registers and 200 µm to a shared root. Existing root loads provide headroom for the 109 modeled extra short crossings.

Release CTS only with global 60 µm and the extended 85 µm distance for the same encoder instance and bit in d0–d2. Leave full route held for placement and timing review.
