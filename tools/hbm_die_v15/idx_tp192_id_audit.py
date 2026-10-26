# Exhaustive audit of ot_hbm_idx_score_static global key id (TP192, N_Q=2) for VALID lanes only (valid_keys gate).
TP, NQ, W = 192, 2, 1 << 20
seen = set(); wrap_valid = 0; wrap_invalid = 0; maxid = 0
for r in range(TP):
    nk = 5464 if r < 128 else 5456                       # audit split: 128*5464 + 64*5456 = 2^20
    for q in range(NQ):
        nq = 0 if nk <= q*2736 else min(2736, nk - q*2736)
        first_ord = q*342
        for beat in range(171):
            g0 = 8*TP*first_ord + 8*r + 16*TP*beat
            for e in range(4):
                first = g0 + (e//2)*8*TP + (e % 2)*4
                for l in range(4):
                    lane = 4*e + l; idf = first + l
                    valid = beat*16 + lane < nq
                    if idf >= W:
                        if valid: wrap_valid += 1
                        else: wrap_invalid += 1
                    if valid:
                        assert idf not in seen, (r, q, beat, e, l); seen.add(idf); maxid = max(maxid, idf)
print(f"TP192_ID_AUDIT valid_keys={len(seen)} unique={len(seen)} cover_all_2^20={seen == set(range(W))} max_id={maxid} "
      f"wrap_on_valid={wrap_valid} wrap_on_invalid_lanes={wrap_invalid}")
