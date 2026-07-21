"""Logistics endpoints: tracking-number allocation + shipping-document (AWB) flow.

Mirrors the Shopee v2 surface consumed by OSI's api/shopee/logistics.py and
api/sync.py generate_shipping_label_job:

    GET  /api/v2/logistics/get_tracking_number
    POST /api/v2/logistics/get_shipping_document_parameter
    POST /api/v2/logistics/create_shipping_document
    POST /api/v2/logistics/get_shipping_document_result
    POST /api/v2/logistics/download_shipping_document   (binary PDF on success)

Behavior notes:
* Tracking numbers are allocated lazily on the first get_tracking_number call,
  only once an order is READY_TO_SHIP or later ("MOCKTRK" + zero-padded counter).
  Orders that have not reached READY_TO_SHIP return an empty tracking_number
  (Shopee does the same pre-allocation) so OSI's waiting_allocation path runs.
* create_shipping_document records the request; get_shipping_document_result
  returns PROCESSING on the first poll after create, READY afterwards.
* download returns a real one-page PDF (valid xref, parses under pypdf) so
  OSI's SKU overlay + crop pipeline can run against it.
"""

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel

from mockshopee.envelope import err, ok
from mockshopee.state import STATE

router = APIRouter()

SELECTABLE_DOCUMENT_TYPES = ["THERMAL_AIR_WAYBILL", "NORMAL_AIR_WAYBILL"]
SUGGESTED_DOCUMENT_TYPE = "THERMAL_AIR_WAYBILL"

# reason -> (fail_error, fail_message) for per-order failure rows. Messages for
# pre-allocation states intentionally contain "ready to ship"/"tracking number"
# so OSI's _shipping_label_failure_state maps them to waiting_allocation.
_FAIL_ROWS = {
    "not_found": ("logistics.package_not_exist", "order does not exist"),
    "cancelled": ("logistics.order_cancelled", "order has been cancelled"),
    "not_ready": (
        "logistics.package_can_not_print",
        "order is not ready to ship; tracking number not yet allocated",
    ),
    "no_tracking": (
        "logistics.tracking_number_not_allocated",
        "tracking number has not been allocated for this order yet",
    ),
    "not_created": (
        "logistics.shipping_document_not_created",
        "create_shipping_document has not been requested for this order",
    ),
}


class OrderListBody(BaseModel):
    order_list: list[dict] = []


class DownloadBody(OrderListBody):
    shipping_document_type: str = "THERMAL_AIR_WAYBILL"


def _fail_row(order_sn: str, reason: str) -> dict:
    fail_error, fail_message = _FAIL_ROWS.get(reason, ("logistics.error", reason))
    return {"order_sn": order_sn, "fail_error": fail_error, "fail_message": fail_message}


# -- tracking number ----------------------------------------------------------

@router.get("/api/v2/logistics/get_tracking_number")
def get_tracking_number(
    shop_id: int = Query(0),
    order_sn: str = Query(...),
    package_number: str = Query(""),
):
    result = STATE.allocate_tracking_number(order_sn)
    if result["ok"]:
        return ok({
            "order_sn": order_sn,
            "package_number": result.get("package_number") or "",
            "tracking_number": result["tracking_number"],
        })
    reason = result["reason"]
    if reason == "not_found":
        return err("error_not_found", f"order {order_sn} not found")
    if reason == "cancelled":
        return err("logistics.order_cancelled", f"order {order_sn} has been cancelled")
    # not_ready: Shopee answers success with an empty tracking_number until the
    # carrier allocates one — OSI treats empty as not_ready / waiting_allocation.
    return ok({
        "order_sn": order_sn,
        "package_number": result.get("package_number") or "",
        "tracking_number": "",
    })


# -- shipping document flow ----------------------------------------------------

@router.post("/api/v2/logistics/get_shipping_document_parameter")
def get_shipping_document_parameter(body: OrderListBody, shop_id: int = Query(0)):
    if not body.order_list:
        return err("error_param", "order_list required")
    rows = []
    for entry in body.order_list:
        order_sn = str(entry.get("order_sn") or "")
        reason = STATE.check_logistics_eligibility(order_sn)
        if reason:
            rows.append(_fail_row(order_sn, reason))
            continue
        rows.append({
            "order_sn": order_sn,
            "suggest_shipping_document_type": SUGGESTED_DOCUMENT_TYPE,
            "selectable_shipping_document_type": list(SELECTABLE_DOCUMENT_TYPES),
        })
    return ok({"result_list": rows})


@router.post("/api/v2/logistics/create_shipping_document")
def create_shipping_document(body: OrderListBody, shop_id: int = Query(0)):
    if not body.order_list:
        return err("error_param", "order_list required")
    rows = []
    for entry in body.order_list:
        order_sn = str(entry.get("order_sn") or "")
        result = STATE.create_shipping_doc(
            order_sn,
            str(entry.get("shipping_document_type") or "THERMAL_AIR_WAYBILL"),
            tracking_number=str(entry.get("tracking_number") or ""),
        )
        if result["ok"]:
            rows.append({"order_sn": order_sn})
        else:
            rows.append(_fail_row(order_sn, result["reason"]))
    return ok({"result_list": rows})


@router.post("/api/v2/logistics/get_shipping_document_result")
def get_shipping_document_result(body: OrderListBody, shop_id: int = Query(0)):
    if not body.order_list:
        return err("error_param", "order_list required")
    rows = []
    for entry in body.order_list:
        order_sn = str(entry.get("order_sn") or "")
        # Live Shopee rejects result polls without a per-item document type —
        # mirror it so untyped polls can't pass in dev (regressed silently once).
        if not entry.get("shipping_document_type"):
            rows.append({
                "order_sn": order_sn,
                "fail_error": "logistics.shipping_document_should_print_first",
                "fail_message": "The package can not print now, please create shipping document first.Detail: shipping_document_type",
            })
            continue
        result = STATE.shipping_doc_status(order_sn)
        if result["ok"]:
            rows.append({
                "order_sn": order_sn,
                "status": result["status"],  # PROCESSING (first poll) then READY
                "shipping_document_type": result["document_type"],
            })
        else:
            row = _fail_row(order_sn, result["reason"])
            row["status"] = "FAILED"
            rows.append(row)
    return ok({"result_list": rows, "file_type": "PDF"})


@router.post("/api/v2/logistics/download_shipping_document")
def download_shipping_document(body: DownloadBody, shop_id: int = Query(0)):
    if not body.order_list:
        return err("error_param", "order_list required")
    order_sns = [str(entry.get("order_sn") or "") for entry in body.order_list]
    for order_sn in order_sns:
        result = STATE.shipping_doc_for_download(order_sn)
        if not result["ok"]:
            fail_error, fail_message = _FAIL_ROWS[result["reason"]]
            return err(fail_error, f"{order_sn}: {fail_message}")
    pdf = _build_label_pdf(order_sns, body.shipping_document_type)
    filename = f"mock-awb-{order_sns[0]}.pdf" if len(order_sns) == 1 else "mock-awb-batch.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# -- minimal-but-valid PDF -----------------------------------------------------

def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_label_pdf(order_sns: list[str], document_type: str) -> bytes:
    """One-page 4x6" (288x432pt) PDF with correct byte-offset xref.

    Hand-rolled but genuinely valid: OSI parses the download with pypdf
    (SKU overlay + crop), so a bare "%PDF" prefix is not enough.
    """
    lines = ["MOCK SHOPEE AWB", _pdf_escape(document_type or "THERMAL_AIR_WAYBILL")]
    lines += [_pdf_escape(sn) for sn in order_sns[:8]]
    if len(order_sns) > 8:
        lines.append(f"+{len(order_sns) - 8} more orders")

    ops = ["BT", "/F1 12 Tf", "20 400 Td"]
    for index, line in enumerate(lines):
        if index:
            ops.append("0 -18 Td")
        ops.append(f"({line}) Tj")
    ops.append("ET")
    content_stream = "\n".join(ops).encode("latin-1", "replace")

    bodies = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 288 432] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        5: b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content_stream), content_stream),
    }

    buf = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(bodies):
        offsets[num] = len(buf)
        buf += f"{num} 0 obj\n".encode("ascii")
        buf += bodies[num]
        buf += b"\nendobj\n"

    xref_offset = len(buf)
    count = len(bodies) + 1
    buf += f"xref\n0 {count}\n".encode("ascii")
    buf += b"0000000000 65535 f \n"
    for num in range(1, count):
        buf += f"{offsets[num]:010d} 00000 n \n".encode("ascii")
    buf += b"trailer\n"
    buf += f"<< /Size {count} /Root 1 0 R >>\n".encode("ascii")
    buf += b"startxref\n"
    buf += f"{xref_offset}\n".encode("ascii")
    buf += b"%%EOF"
    return bytes(buf)
