# v14 main (8961-b rgx_c)

Model: `tools/hbm_r25gq_windows.py` (every die hop pin to pin as its two L shapes, half the bits each; wire length per direction per window against the die GRT's own track supply: M4 / M5 x 0.50, M6 / M7 x 0.95, M8 / M9 x 0.7744, blocks leave M8 / M9 only).

**FAIL**: 500-um windows 84 of 35938 over 0.90 (worst 1.517), 1000-um windows 24 of 8850 over 0.75 (worst 1.050), 2000-um windows 1 of 1600 over 0.60 (worst 0.617)

## 500-um windows (limit 0.90)

| util | dir | x um | y um | demand bit um | track um | largest families (share) |
|---:|---|---|---|---:|---:|---|
| **1.517** | V | 10,584-11,084 | 7,992-8,492 | 7,787,186 | 5,132,646 | coll_rgx_c 76%, xt_SW 17%, coll_injd_SW 5%, pr_cw_SW_SE 1%, coll_vma_SW 1% |
| **1.465** | V | 10,800-11,300 | 9,720-10,220 | 8,502,553 | 5,804,420 | coll_rgx_c 76%, xt_SW 10%, tr_SW# 6%, coll_rgx_xw 4%, coll_rgx_xr 3% |
| **1.399** | V | 10,584-11,084 | 9,936-10,436 | 7,179,686 | 5,132,646 | coll_rgx_c 72%, xt_SW 15%, coll_rgx_xw 4%, coll_rgx_vmq 2%, tr_SW# 2% |
| **1.394** | V | 10,800-11,300 | 9,936-10,436 | 8,092,915 | 5,804,420 | coll_rgx_c 68%, xt_SW 13%, tr_SW# 7%, coll_rgx_xw 4%, coll_rgx_xr 3% |
| **1.393** | V | 10,800-11,300 | 9,504-10,004 | 8,086,665 | 5,804,420 | coll_rgx_c 79%, xt_SW 10%, tr_SW# 4%, coll_rgx_xw 4%, coll_rgx_xr 2% |
| **1.378** | V | 10,584-11,084 | 9,720-10,220 | 7,070,453 | 5,132,646 | coll_rgx_c 74%, xt_SW 14%, coll_rgx_xw 5%, coll_rgx_xr 3%, tr_SW# 2% |
| **1.357** | V | 12,960-13,460 | 9,288-9,788 | 7,725,339 | 5,692,457 | coll_rgx_c 67%, hgi_lgsw_wup 11%, hgi_lgsw_tap_wup_su_SW 10%, hgi_lgsw_rdn_# 7%, hgi_lgsw_tap_rdn_su_SW 2% |
| **1.357** | V | 13,176-13,676 | 9,288-9,788 | 7,725,339 | 5,692,457 | coll_rgx_c 69%, hgi_lgsw_wup 11%, hgi_lgsw_tap_wup_su_SW 10%, hgi_lgsw_rdn_# 6%, hgi_lgsw_tap_rdn_su_SW 2% |
| **1.349** | V | 13,176-13,676 | 9,072-9,572 | 7,681,805 | 5,692,457 | coll_rgx_c 62%, hgi_lgsw_tap_rdn_su_SW 10%, hgi_lgsw_tap_wup_su_SW 10%, hgi_lgsw_wup 8%, hgi_lgsw_rdn 7% |
| **1.349** | V | 12,960-13,460 | 9,072-9,572 | 7,681,805 | 5,692,457 | coll_rgx_c 61%, hgi_lgsw_tap_rdn_su_SW 10%, hgi_lgsw_tap_wup_su_SW 10%, hgi_lgsw_wup 8%, hgi_lgsw_rdn 7% |
| **1.348** | V | 10,800-11,300 | 7,992-8,492 | 7,823,479 | 5,804,419 | coll_rgx_c 83%, xt_SW 11%, coll_injd_SW 5%, coll_inja_SW 1%, pr_cw_SW_SE 0% |
| **1.336** | V | 10,800-11,300 | 9,288-9,788 | 7,756,417 | 5,804,420 | coll_rgx_c 79%, xt_SW 12%, tr_SW# 5%, coll_rgx_xw 2%, coll_rgx_xr 1% |

## 1000-um windows (limit 0.75)

| util | dir | x um | y um | demand bit um | track um | largest families (share) |
|---:|---|---|---|---:|---:|---|
| **1.050** | V | 10,368-11,368 | 9,504-10,504 | 15,239,189 | 14,512,626 | coll_rgx_c 75%, xt_SW 11%, tr_SW# 5%, coll_rgx_xw 3%, coll_rgx_xr 3% |
| **1.028** | V | 10,368-11,368 | 9,072-10,072 | 14,911,947 | 14,512,626 | coll_rgx_c 80%, xt_SW 10%, tr_SW# 4%, coll_rgx_xw 2%, coll_del_SW 2% |
| **0.988** | V | 10,368-11,368 | 8,208-9,208 | 14,342,438 | 14,512,626 | coll_rgx_c 77%, xt_SW 11%, coll_injd_SW 6%, coll_del_SW 4%, coll_rc_SW 2% |
| **0.975** | V | 10,800-11,800 | 9,504-10,504 | 14,144,867 | 14,512,626 | coll_rgx_c 73%, xt_SW 12%, tr_SW# 6%, coll_rgx_xw 4%, coll_rgx_xr 3% |
| **0.966** | V | 10,368-11,368 | 8,640-9,640 | 14,021,339 | 14,512,626 | coll_rgx_c 79%, xt_SW 11%, coll_del_SW 4%, coll_injd_SW 2%, tr_SW# 2% |
| **0.951** | V | 10,800-11,800 | 9,072-10,072 | 13,807,755 | 14,512,626 | coll_rgx_c 78%, xt_SW 11%, tr_SW# 4%, coll_rgx_xw 2%, coll_del_SW 2% |
| **0.936** | V | 12,960-13,960 | 9,072-10,072 | 13,399,718 | 14,311,094 | coll_rgx_c 69%, hgi_lgsw_rdn_# 6%, hgi_lgsw_wup 6%, hgi_lgsw_tap_wup_su_SW 5%, hgi_lgsw_tap_rdn_su_SW 4% |
| **0.936** | V | 12,528-13,528 | 9,072-10,072 | 13,399,718 | 14,311,094 | coll_rgx_c 66%, hgi_lgsw_rdn_# 7%, hgi_lgsw_wup 7%, hgi_lgsw_tap_wup_su_SW 6%, hgi_lgsw_tap_rdn_su_SW 5% |
| **0.912** | V | 10,800-11,800 | 8,208-9,208 | 13,238,246 | 14,512,626 | coll_rgx_c 76%, xt_SW 11%, coll_injd_SW 6%, coll_del_SW 4%, coll_rc_SW 2% |
| **0.890** | V | 10,800-11,800 | 8,640-9,640 | 12,917,147 | 14,512,626 | coll_rgx_c 77%, xt_SW 12%, coll_del_SW 4%, coll_injd_SW 2%, tr_SW# 2% |
| **0.844** | V | 10,368-11,368 | 7,776-8,776 | 14,866,185 | 17,620,599 | coll_rgx_c 74%, xt_SW 12%, coll_injd_SW 5%, xh_SW 4%, lkq_S# 2% |
| **0.810** | V | 12,528-13,528 | 8,640-9,640 | 12,320,947 | 15,218,860 | coll_rgx_c 66%, hgi_lgsw_tap_rdn_su_SW 12%, hgi_lgsw_tap_wup_su_SW 7%, hgi_lgsw_wup 6%, hgi_lgsw_rdn 4% |

## 2000-um windows (limit 0.60)

| util | dir | x um | y um | demand bit um | track um | largest families (share) |
|---:|---|---|---|---:|---:|---|
| **0.617** | V | 12,636-14,636 | 8,748-10,748 | 47,316,229 | 76,663,834 | coll_rgx_c 60%, vring_SE_SW 6%, hgi_lgsw_rdn_# 5%, vring_SW_SE 5%, hgi_lgsw_wup_# 4% |
| 0.563 | V | 9,720-11,720 | 7,776-9,776 | 32,968,298 | 58,573,404 | coll_rgx_c 74%, xt_SW 13%, xh_SW 3%, coll_injd_SW 2%, lkq_S# 2% |
| 0.557 | V | 9,720-11,720 | 8,748-10,748 | 31,643,051 | 56,765,031 | coll_rgx_c 72%, xt_SW 14%, tr_SW# 4%, coll_rgx_xw 2%, coll_del_SW 2% |
| 0.544 | V | 10,692-12,692 | 8,748-10,748 | 29,153,055 | 53,635,981 | coll_rgx_c 71%, xt_SW 13%, tr_SW# 4%, coll_rgx_xw 2%, coll_del_SW 2% |
| 0.533 | V | 9,720-11,720 | 6,804-8,804 | 47,101,441 | 88,354,428 | coll_rgx_c 66%, xh_SW 10%, lkq_S# 8%, xt_SW 5%, rt_SW 4% |
| 0.513 | V | 10,692-12,692 | 7,776-9,776 | 31,410,960 | 61,207,174 | coll_rgx_c 66%, xt_SW 19%, rt_SW 3%, xh_SW 3%, coll_injd_SW 2% |
| 0.507 | H | 9,720-11,720 | 6,804-8,804 | 44,796,285 | 88,354,428 | coll_rgx_c 66%, xh_SW 10%, lkq_S# 8%, xt_SW 5%, rt_SW 4% |
| 0.502 | H | 10,692-12,692 | 6,804-8,804 | 52,683,177 | 104,886,752 | coll_rgx_c 67%, xt_SW 8%, xh_SW 6%, rt_SW 5%, lw_SW 4% |
| 0.474 | V | 12,636-14,636 | 9,720-11,720 | 46,642,343 | 98,330,604 | coll_rgx_c 32%, hgi_lgsw_wup_# 9%, hb_vm_su_SW 8%, hgi_lgsw_rdn_# 8%, hb_su_SW_vm 7% |
| 0.468 | H | 10,692-12,692 | 5,832-7,832 | 54,114,537 | 115,543,138 | coll_rgx_c 68%, lw_SW 8%, rt_SW 7%, xh_SW 5%, lkq_S# 4% |
| 0.452 | H | 9,720-11,720 | 5,832-7,832 | 48,489,919 | 107,200,377 | coll_rgx_c 59%, xh_SW 13%, rt_SW 8%, lkq_S# 7%, lw_SW 4% |
| 0.452 | V | 11,664-13,664 | 8,748-10,748 | 24,934,934 | 55,180,518 | coll_rgx_c 57%, hgi_lgsw_rdn_# 9%, hgi_lgsw_wup_# 7%, hgi_lgsw_tap_rdn_su_SW 5%, hb_vm_su_SW 4% |

