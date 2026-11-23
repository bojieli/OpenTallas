# S81 J8 station t30 exact placement review

BAD. Keep this exact attempt at WAIT-FORM.

- Event 891100ef774, type `slice_station__t30__cl6a190133`, attempt 1 on epyc8. I viewed actual `run/layout_review/place/layout.png`, `place/density.png` and `geom/auto_geom.png` from the kit below.
- The place is a sparse station-only tile with separate west and center strips. Its low whole-tile occupancy is expected for that family. Two west side `cland_dn_{fault,ready}_0[0]` pins are 254.86 and 253.2 µm from their first capture. The isolated southeast reset-collector ready register is driven by central `clk`, a 1483.45 µm leg to `u_bound.u_cland_collect_rst_root_n/ready_o`. The nearest-tap coverage statistic of 257.62 µm does not qualify this assigned clock leg. One separate real data hop `u_bound.u_rrl_70/q -> u_bound.u_ft_ft2_o_5/eq` is 408.56 µm against 405.
- A practical same-age successor moves the west capturers into their landing band, assigns the southeast ready register to a legal equivalent local clock branch, and brings the single data hop below 405 µm. Prove native reset island phase and bind for the retap before using the new geometry. Fresh placed images required.
- The already-running old diagnostic ran read-only GRT with reported zero overflow. This is a transport and pin capture hold. No route or CTS release for the attempt.

Kit `epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t30__cl6a190133/gen/slice_station__t30__cl6a190133`.

## Clock assignment follow-up

The real west monitor capture issue keeps t30 held. The existing exact tap assignment, applied to a copy of the actual placed ODB on E8, preserves all 12,057 FF clock ancestries and moves the root ready register to clk_t2 at 20.708 µm. The preceding ready register uses clk_t16 at 140.538 µm. The near-409 µm leg originates from reset relay u_rrl_70, so handle it under reset reach and recovery. No extra clock group is required for the root. The private J9 geometry patch moves only west monitor_0 next to its physical ready, fault and forwarded clock pins, preserving its footprint dimensions and all logic.
