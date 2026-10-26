# Idle die-link framing checker, 2026-10-25

Fully reclocked fc31 r4all L0 traces: 10/10 end-slice lanes reproduce the compiled gearbox marker/idle/reverse-CRC stream. Wrong marker phase and wrong CRC controls are caught on10/10 lanes each. This closes the idle-framing part of unencoded strict-lane traffic; payload-bearing RD frames and the full token pass remain open.

The initial checker falsely failed4/10 lanes, each on one transition at the final bench cycle. dv_slice_tb closed the trace on the same final negedge as its trace monitor. Guaranteed observation ended at NCYC-2. The legacy reader checks that complete interval and separately rejects any wrong recorded terminal word. Future benches defer close by1ps and emit TRACE_END with the final cycle; that marker restores checking through the full terminal cycle and rejects shortened runs. No expected data word is dropped. Original pre-fix findings are retained.

Also fixed the recovered checker's Python dict construction: tuple framing keys cannot be passed through **kwargs; update accepts them. The runtime XRT source guard remains unchanged. These results validate the framing model against prior traces; new deskew full-cut qualification is still pending its HOST proof and live builds.
