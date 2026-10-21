# Qwen class frontier placement candidate

Source parent bfba39243. Opt in with OT_SPLIT_FWD_CLASS_PACK_FRONTIER=1 alongside OT_SPLIT_FWD_CLASS_PACK=1. Default behavior is unchanged.

The provisional compact class install can overlap its own unplaced classes. The candidate indexes only fixed outlines and already selected classes. For each movable outline it intersects every matching-bit Manhattan <=405um diamond, using exact bounds on x+y and x-y. It searches every legal 2.16um y row and sweeps obstacle x intervals to find a 0.432um lattice site. The normal final overlap and matching-bit reach checks remain mandatory.

The existing source composition/calendar and actual geometry tests plus a stranded exact-width corridor regression pass on ot-gold1 (unit oth-ubuntu-1558843-1792600907, exit0, seven tests). The corridor's unique legal x origin101.952 is invisible to a4.32um ring search from provisional99.792.

This is an unqualified placement candidate. Full die c129/c173 diagnostic geometry and actual GEN/bind/calendar/reset/reach/native outcomes remain required. No closed view, release claim, or timing waiver is implied. The same closed classes, widths, station count, E/K/n and die outline are retained; added token cycles and planned area are zero. Failed d129/d173 infrastructure runs and original packing failures are preserved separately.
