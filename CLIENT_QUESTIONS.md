# MALACA ERP 1.0 — Questions for Client

Questions to confirm scope before building. Grouped by topic. Each has a short "why" so the answer comes back usable.

---

## A. User accounts & permissions  *(most important — currently undefined)*

We need to know **how many people use the system and what each is allowed to see/do**, so we can set up roles and data access correctly.

1. **How many user accounts** in total at launch? Roughly how many do you expect within a year?
2. **What job roles** will use the system? (e.g. order reviewer, warehouse/picking staff, finance, procurement, store/account manager, system admin.) Please list each role and roughly how many people per role.
3. **Data scope per user — what should each person be limited to?** Pick all that apply, or describe:
   - by **country/site** (e.g. a Vietnam operator sees only Vietnam orders)?
   - by **warehouse** (warehouse-A staff see only warehouse-A stock)?
   - by **platform** (Shopee team vs Lazada team)?
   - by **store/shop** (one operator owns specific shops)?
   - by **company/legal entity** (if more than one entity sells)?
4. **Cross-visibility:** should a seller/operator in one country be able to see other countries' orders or stock — yes (full visibility) or no (isolated)?
5. **Who is allowed to do each of these?** (role name is enough)
   - approve/reject orders
   - edit inventory / stock master data
   - view finance / profit numbers
   - manage procurement / purchase orders
   - change system settings & connect marketplace accounts
6. **Order approval:** single approver enough, or does it need **multi-level** sign-off (e.g. operator → supervisor) for some orders (high value, special orders)?
7. Any **external users** needing limited access — suppliers, logistics partners, accountants? If yes, what should they see?
8. Any **audit / accountability** requirement — do you need a record of who approved/edited/shipped each order?

> Note: how many *marketplace accounts* (Shopee/Lazada shops) you connect is separate from how many *人 (people/login accounts)* use the app — please answer both: number of **shops/stores** to connect, and number of **people** logging in.

---

## B. Order review workflow

9. Should **every order wait for manual approval** before it moves forward, or only **some** orders (e.g. flagged/high-value/out-of-stock) while the rest auto-process?
10. For **special orders / 刷单 (brushing)** — at launch, is it enough to let staff **manually flag** them, or do you want the system to **auto-detect** suspicious orders from day one? (Auto-detection is a larger build.)

---

## C. Inventory & warehouse

11. **Bin/shelf location (库位):** do you need **specific shelf/pick-face locations** inside each warehouse, or is **warehouse-level** stock tracking enough to start?
12. **Failed deliveries / returns:** when goods come back, do staff need to record the condition — **re-shelf (good)** vs **damaged** vs **scrap** — so stock and finance update correctly? (We recommend yes.)
13. **Summary reports (发货汇总表 / 退货汇总表):** confirm the breakdowns you want — by **day / month / year**, and split by **site** and **warehouse**? Any other grouping (by platform, by SKU)?

---

## D. Finance

14. **Marketplace fees (Shopee):** commission, service fee, shipping subsidy and net payout can be pulled **automatically from your already-connected Shopee account — no extra credentials or action needed from you.** Just confirm: do you want profit shown **net of these fees** (recommended), and are there any fee types Shopee doesn't report that you track separately?
15. **Product cost (COGS):** where do unit costs come from — will you **provide a cost per SKU**, or should the system derive it from purchase records?
16. **Other costs** in the P&L (advertising spend, company operating costs): will these be **entered manually**, or imported from somewhere? If imported, from where?

---

## E. Platforms

17. **Phase 1 priority order** — after Shopee, which next: **Lazada or TikTok Shop first?**
18. Do you have **live seller API access** for Lazada / TikTok now (so we can build and test against real data), or should we build to the documented API and connect later?

---

## F. Languages / translation

19. Confirm the **launch languages** (you listed ZH/EN/Filipino/Thai/Vietnamese/Malay/Hindi/JP/Spanish) — which are needed **at launch** vs **later**?
20. **"AI self-evolving" translation:** do you want the system to **auto-translate new text** as we add features (then spot-checked by a person), or will translations be **provided/reviewed manually**? (Auto is a bigger build; affects cost.)
