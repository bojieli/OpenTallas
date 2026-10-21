# IDXTX R3 source-bound admission model

Actual changed-source R2d05 native refused6cones/max256/0roles (original100cones/max290 -> R1 36cones/max41, R2six). Full reports retainedr2_refusal; production baseline and all3causalsPASS/caughtd05 immutable. No unchanged retry.

Mapped 60/61load cones _18607/_18622 are shared priority selectors from lvl_index into the20bit index mux. New independent lvl_memory created duplicated upstreampriority optimization but did not bound downstream mux bits. Replace two16bit copies with four16bit same-edge copies inside kept consumer-local mux masters: two10bit payload halves, two8bit memory-address halves. Each module captures actual lvl_next at the existing edge and computes identical lowest-set-bit priority and its own <=10bit data mux; originaliw register and control ne/ne_v remain. Net+32FF overR2, no edge/arrival restriction.

Mapped253/256load roots _24917/_25684 derive accept/window-buffer write selects and now span scorefeedback muxes. Keeping onlyonebit perfield allowed ABC to refactor remaining15bit+valid banks into wide shared consumers. Move each complete16bit scorefield into a unique kept source master with local accept&&onehot compute and existing16FF. No added state; parentaccept drives16field inputports instead of hundreds of gate pins, helperpredicate<=32mappedmuxcontacts.

Mapped33/34root pair _26851/_26871 shares remaining window-open/accumulate state controls. Localize the existing wlvb16 and w0b20 perbank into kept four4bit valid-field masters and two10bit window-address masters, preserving open-before-accumulate priority at actual preedge. Parentcontrol has at most16score+4valid+2address helper contacts perbank; each localpredicate bounded by <=10data bits. No added state/reset, no persistentarray>2kb, no extra edge. Original8score+2IDX SRAM unchanged.

R2threeCTL copies and all existingresetleafages remain unchanged. Publicports/VMUX/timing/calendar remain unchanged provisionally until exact existing sixdie SRAM DIEM production andMUT1/2/3 proofs repeat on changed source. Then changed-source nativeMAIN/FB required; no parentphysical/viewadoption beforecausal/native.
