# HEAD hd_spn exact global-placement status reseat (11-24)

Opened revised r18gw status reseat global placement `a83140f086b8`. E10 `oth-ubuntu-2753333-1795531290` produced it. The completed file and generated kit were copied to E9 as E10 scratch filled. E2 `oth-ubuntu-3291830-1795533941` read and rendered the copy without route.

The two original BW ready/fault captures above 405 µm are gone. The actual globally placed maximum R2R is 382.32 µm, below the initial 550.071 µm. The complete placed scan has zero above-reach bits, and there are zero unregistered pins, partial faces or relay collapses. Peak modeled column usage is 0.460.

**Hold.** The tall outline still packs clock demand at the upper and lower edges. The exact image and metrics show 2,588 sinks at t37, 2,104 at t34, and nearest clock reach up to 252.92 µm. Pin capture p90/max are 46.23/184.0 µm. The status reseat addresses the former local data-hop failure. The separate clock/pin issues and a completed detailed-placement review remain due before any route decision.

- [Viewed exact global placement](hd_spn_reseat_actual_gp_1124.png)
- [Original status hold and seat draft](head_hd_spn_r18gw_a2_reseat_1124.md)
