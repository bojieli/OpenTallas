Opt-in t16 CLAND local controls, no added cycles

The vJ placed failure was a single on signal spanning the pin column and a two-bit writer slot copy driving four banks of 64 bits per chunk. OT_S81_CLAND_LOCAL_ON uses the existing ring ONV interface with per-reader-chunk registers computed from on/align NEXT state on the same edge. The align next state includes rst_n because the existing local rst_l captures rst_n on that edge. Writer chunks become 16 bits through the appended WCCB parameter; the default remains 64.

Positive miter: reference vJ WCHK versus the new local controls, explicit W=515 / WNEG=1, six forwarded-clock phases (0.03, 0.17, 0.29, 0.41, 0.59, 0.79 ns), five warm reset epochs each. Each phase has 2,895 valid payload comparisons, zero errors, no reference fault. The miter also checks local on/align copies against the reference state on every live cycle and compares ready/fault on the same edge.

Negative controls at 0.29 ns: old on copy caught 2,900 errors, old align copy caught 10, wrong write-slot copy caught 2,895. Mutations apply only to the new temporary source.

The inherited RCK-10 cland bench declared 513-bit data but omitted the W override (default W=1), and omitted WNEG (default 0). Its result is a narrow legacy check, not production multi-chunk evidence. This explicit W=515 / WNEG=1 miter covers the current t16 landing form.

Physical integration remains pending: activate only in the private t16 parent, place the on/align and slot copies beside their data chunks, render, review, then a PLACE pilot. No parent plan-of-record or wave release is authorized by this proof. The compact extracted core pilot must finish first.
