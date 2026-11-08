# Private TX feedback placement form

Actual vC TT placed WNS is -57.38 ps on rem_q[211] to rem_q[160]. HOLD before CTS. This new form groups the measured backward recurrence cone during global placement, then releases the fence before detailed legalization. This is a structural feedback-locality change, with no RTL or calendar change.

The exact vC cone contains 300 parity registers, 304 boundary registers, and 18,710 combinational cells: 19,314 cells, 3091.82022 square microns. The 90.72 square region has 37.57% fill. Dynamic membership is rebuilt from parity D-pin fanin in each mapped DB, with count/fill/status guards; it does not copy anonymous mapped cell names.

Reviewed actual vC floorplan/density images: compact no-macro layout, several small east IO bins above 70%, and 897 long-span nets. Reviewed pre_place.png for new 181.44 square outline: centered feedback fence, clock at north midpoint, existing east/west input/output face ordering, ample exterior area for remaining logic, no macro channels. This image shows a placement constraint, not a new hard macro. Actual placed images and timing are required before CTS. Parent slot top is 648 um and remains below shore keepout. Private form only; no POR changes.
