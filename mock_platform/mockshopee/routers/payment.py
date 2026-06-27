"""Payment endpoints: get_escrow_detail.

Emulates Shopee v2 /api/v2/payment/get_escrow_detail — returns the settlement
breakdown (order_income) for an order so OSI's escrow/fee ingest can be built and
tested offline. Fees are derived from the order's gross with plausible rates.
"""

from fastapi import APIRouter, Query

from mockshopee.envelope import err, ok
from mockshopee.state import STATE

router = APIRouter()

# Plausible Shopee-style rates (mock only; real values come from Shopee).
COMMISSION_RATE = 0.06
SERVICE_RATE = 0.02
TXN_RATE = 0.01


@router.get("/api/v2/payment/get_escrow_detail")
def get_escrow_detail(shop_id: int = Query(...), order_sn: str = Query(...)):
    order = STATE.orders.get(order_sn)
    if not order:
        return err("error_not_found", f"order {order_sn} not found")

    buyer_total = round(float(order.get("total_amount") or 0), 2)
    commission = round(buyer_total * COMMISSION_RATE, 2)
    service = round(buyer_total * SERVICE_RATE, 2)
    txn = round(buyer_total * TXN_RATE, 2)
    escrow = round(buyer_total - commission - service - txn, 2)

    order_income = {
        "escrow_amount": escrow,
        "buyer_total_amount": buyer_total,
        "original_price": buyer_total,
        "order_selling_price": buyer_total,
        "commission_fee": commission,
        "service_fee": service,
        "seller_transaction_fee": txn,
        "voucher_from_seller": 0,
        "voucher_from_shopee": 0,
        "actual_shipping_fee": 0,
        "shopee_shipping_rebate": 0,
        "buyer_paid_shipping_fee": 0,
    }
    return ok({
        "order_sn": order_sn,
        "buyer_user_name": (order.get("recipient_address") or {}).get("name", ""),
        "order_income": order_income,
    })
