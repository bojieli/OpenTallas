# S81 SerDes t16 J5 a17 placement review

Viewed the actual retained epyc7 layout, density and AUTO-GEOM images from event 224567138ab. Source picture root is /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/224567138ab/items/serdes__t16/attempt_17. Images are geom/auto_geom.png and gen/serdes__t16/run/layout_review/place/{layout,density}.png.

The two PMAs occupy a north band. Logic and pins cluster at the west and east faces and around the central hard macros. The macro pair has a continuous horizontal channel. AUTO-GEOM reports global-route preview overflow 0, a 553.89 µm nearest-clock entry distance and clock concentration at the PMA. Actual placement shows the eastern face register banks separate vertically. The centre density and long register legs still need measured post-CTS timing. Prior CTS was interrupted by missing declarations for tb_cdirect and tb_cdmax after RCK STB reached a 47 ps span.

PASS-COND for a private CTS-only recovery from the exact retained 3_place checkpoint with the two missing globals restored. Route remains blocked pending a new layout review and terminal timing. No geometry, netlist, constraints, or phase changes in this recovery. The original a17 files stay intact.
