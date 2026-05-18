import os
import io
import boto3
import uuid
from datetime import datetime, timezone
from botocore.client import Config
import hashlib

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY

VINAFCO_BLUE = colors.HexColor("#0A3D7C")
LIGHT_GRAY = colors.HexColor("#F5F5F5")
MID_GRAY = colors.HexColor("#CCCCCC")
DARK_GRAY = colors.HexColor("#444444")

# Schema
BOOKING = {
    "booking_ref": "VFC-2026-0042",
    "issue_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    "customer": {
        "name": "VinFast Trading Co. Ltd",
        "address": "Km 3+500, Nguyen Trai, Ha Dong, Ha Noi",
        "tax_id": "0109168234",
        "contact": "Nguyen Van A",
        "phone": "+84 912 345 678",
        "email": "logistics@vinfast.vn",
    },
    "shipment": {
        "vessel": "VINAFCO 26",
        "voyage": "0949",
        "pol": "Tan Thuan Port, Ho Chi Minh City",
        "pod": "Hai Phong Port",
        "etd": "2026-01-05 10:00",
        "eta": "2026-01-08 08:00",
        "cargo_type": "Motor Vehicles (RoRo)",
        "quantity": 26,
        "unit": "units",
        "description": "VinFast VF8 2024, mixed colours",
        "gross_weight": "62,400 KG",
        "incoterm": "CFR",
    },
    "charges": {
        "freight": "37,440,000",
        "extra_fees": "450,000",
        "total": "40,885,200",
        "currency": "VND",
        "payment": "Prepaid",
    },
    "deadlines": {
        "booking_confirm": "2026-01-02 17:00",
        "customs": "2026-01-03 10:00",
        "si_cutoff": "2026-01-04 10:00",
        "docs_cutoff": "2026-01-03 17:00",
        "cargo_cutoff": "2026-01-04 22:00",
    },
}

BUCKET_ENDPOINT = os.getenv(
    "RAILWAY_BUCKET_ENDPOINT", "https://your-bucket-endpoint.railway.app"
)
ACCESS_KEY_ID = os.getenv("RAILWAY_ACCESS_KEY_ID", "your-access-key-id")
SECRET_ACCESS_KEY = os.getenv("RAILWAY_SECRET_ACCESS_KEY", "your-secret-access-key")
BUCKET_NAME = os.getenv("RAILWAY_BUCKET_NAME", "vinafco-contracts")
PRESIGN_EXPIRY = int(os.getenv("PRESIGN_EXPIRY_SECONDS", 604800))  # 24 hours default


def generate_pdf(booking: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
    )

    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    sTitle = S(
        "sTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=VINAFCO_BLUE,
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    sSub = S(
        "sSub",
        fontName="Helvetica",
        fontSize=9,
        textColor=DARK_GRAY,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    sSection = S(
        "sSection",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=VINAFCO_BLUE,
        spaceBefore=8,
        spaceAfter=4,
    )
    sBody = S(
        "sBody", fontName="Helvetica", fontSize=8, textColor=DARK_GRAY, leading=13
    )
    sBodyBold = S(
        "sBodyBold", fontName="Helvetica-Bold", fontSize=8, textColor=DARK_GRAY
    )
    sSmall = S(
        "sSmall",
        fontName="Helvetica-Oblique",
        fontSize=7,
        textColor=colors.gray,
        alignment=TA_JUSTIFY,
        leading=11,
    )
    sRef = S(
        "sRef",
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=VINAFCO_BLUE,
        alignment=TA_RIGHT,
    )

    b = booking
    s = b["shipment"]
    c = b["customer"]
    ch = b["charges"]
    dl = b["deadlines"]

    story = []

    # Header
    header_data = [
        [
            Paragraph(
                "<b>VINAFCO</b>",
                ParagraphStyle(
                    "h", fontName="Helvetica-Bold", fontSize=22, textColor=VINAFCO_BLUE
                ),
            ),
            Paragraph(
                "VINAFCO Joint Stock Corporation<br/>"
                "Tu Khoat Village, Thanh Tri, Ha Noi<br/>"
                "Tel: 1900 255 516 | info@vinafco.com.vn<br/>"
                "www.vinafco.com.vn",
                ParagraphStyle(
                    "hd",
                    fontName="Helvetica",
                    fontSize=7.5,
                    textColor=DARK_GRAY,
                    alignment=TA_RIGHT,
                    leading=12,
                ),
            ),
        ]
    ]
    header_tbl = Table(header_data, colWidths=["40%", "60%"])
    header_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(header_tbl)
    story.append(
        HRFlowable(width="100%", thickness=2, color=VINAFCO_BLUE, spaceAfter=6)
    )
    story.append(Paragraph("SHIPPING BOOKING CONFIRMATION", sTitle))
    story.append(
        Paragraph(
            "This document constitutes a binding contract between Vinafco and the Shipper named below.",
            sSub,
        )
    )
    story.append(Spacer(1, 2 * mm))

    ref_data = [
        [
            Paragraph(f"Booking Ref: <b>{b['booking_ref']}</b>", sBodyBold),
            Paragraph(f"Issue Date: {b['issue_date']}", sRef),
        ]
    ]
    ref_tbl = Table(ref_data, colWidths=["50%", "50%"])
    ref_tbl.setStyle(TableStyle([("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(ref_tbl)
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY, spaceAfter=6))

    # Parties
    story.append(Paragraph("1. PARTIES", sSection))
    parties_data = [
        ["CARRIER", "SHIPPER"],
        [
            "Vinafco Shipping JSC\n33C Cat Linh, Dong Da, Ha Noi\nTax ID: 0100107517",
            f"{c['name']}\n{c['address']}\nTax ID: {c['tax_id']}",
        ],
        [
            "Contact: Vinafco Operations\nPhone: 1900 255 516",
            f"Contact: {c['contact']}\nPhone: {c['phone']}\nEmail: {c['email']}",
        ],
    ]
    parties_tbl = Table(parties_data, colWidths=["50%", "50%"])
    parties_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), VINAFCO_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("TEXTCOLOR", (0, 1), (-1, -1), DARK_GRAY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, MID_GRAY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GRAY, colors.white]),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(parties_tbl)

    # Shipment
    story.append(Paragraph("2. SHIPMENT DETAILS", sSection))
    ship_data = [
        ["FIELD", "DETAILS", "FIELD", "DETAILS"],
        ["Vessel", s["vessel"], "Voyage No.", s["voyage"]],
        ["Port of Loading", s["pol"], "Port of Discharge", s["pod"]],
        ["ETD", s["etd"], "ETA", s["eta"]],
        ["Cargo Type", s["cargo_type"], "Incoterm", s["incoterm"]],
        ["Quantity", f"{s['quantity']} {s['unit']}", "Gross Weight", s["gross_weight"]],
        ["Description", s["description"], "", ""],
    ]
    ship_tbl = Table(ship_data, colWidths=["22%", "28%", "22%", "28%"])
    ship_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), VINAFCO_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 1), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TEXTCOLOR", (0, 1), (-1, -1), DARK_GRAY),
                ("GRID", (0, 0), (-1, -1), 0.5, MID_GRAY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GRAY, colors.white]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("SPAN", (1, 6), (3, 6)),
            ]
        )
    )
    story.append(ship_tbl)

    # Charges
    story.append(Paragraph("3. FREIGHT CHARGES", sSection))
    charge_data = [
        ["DESCRIPTION", "AMOUNT (VND)"],
        ["Ocean Freight", ch["freight"]],
        ["Cargo Type Surcharge", ch["extra_fees"]],
        [
            Paragraph("<b>TOTAL</b>", sBodyBold),
            Paragraph(
                f"<b>{ch['total']} {ch['currency']}</b>",
                ParagraphStyle(
                    "tot", fontName="Helvetica-Bold", fontSize=8, textColor=VINAFCO_BLUE
                ),
            ),
        ],
        ["Payment Terms", ch["payment"]],
    ]
    charge_tbl = Table(charge_data, colWidths=["70%", "30%"])
    charge_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), VINAFCO_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("TEXTCOLOR", (0, 1), (-1, -1), DARK_GRAY),
                ("GRID", (0, 0), (-1, -1), 0.5, MID_GRAY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GRAY, colors.white, LIGHT_GRAY, colors.white]),
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#E8F0FB")),  # row 3 = TOTAL
                ("LINEABOVE", (0, 3), (-1, 3), 1, VINAFCO_BLUE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]
        )
    )
    story.append(charge_tbl)

    # Deadlines
    story.append(Paragraph("4. CRITICAL DEADLINES", sSection))
    dl_data = [
        ["MILESTONE", "DEADLINE", "STATUS"],
        ["Booking Confirmation + Deposit", dl["booking_confirm"], "Pending"],
        ["Customs Export Declaration", dl["customs"], "Pending"],
        ["Shipping Instructions (SI)", dl["si_cutoff"], "Pending"],
        ["Document Submission Cutoff", dl["docs_cutoff"], "Pending"],
        ["Cargo Cutoff (Gate-in)", dl["cargo_cutoff"], "Pending"],
    ]
    dl_tbl = Table(dl_data, colWidths=["50%", "30%", "20%"])
    dl_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), VINAFCO_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("TEXTCOLOR", (0, 1), (-1, -1), DARK_GRAY),
                ("GRID", (0, 0), (-1, -1), 0.5, MID_GRAY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_GRAY, colors.white]),
                ("BACKGROUND", (2, 1), (2, -1), colors.HexColor("#FFF3CD")),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(dl_tbl)

    # Terms
    story.append(Paragraph("5. TERMS & CONDITIONS", sSection))
    for t in [
        "1. This booking is subject to space and equipment availability at time of confirmation.",
        "2. The Shipper warrants that all cargo descriptions, weights, and measurements are accurate.",
        "3. Cargo must be properly packed and labelled in accordance with applicable regulations.",
        "4. Vinafco shall not be liable for loss or damage arising from inherent vice, improper packing, or force majeure.",
        "5. All disputes shall be subject to Vietnamese maritime law and the jurisdiction of Vietnamese courts.",
        "6. Freight charges are non-refundable once the vessel has departed.",
        "7. The Shipper is responsible for obtaining all necessary export licences and customs clearances.",
        "8. Late delivery of cargo after the cargo cutoff time may result in rolling to the next available sailing.",
    ]:
        story.append(Paragraph(t, sSmall))
        story.append(Spacer(1, 1 * mm))

    # Signatures
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY, spaceAfter=6))
    story.append(Paragraph("6. SIGNATURES", sSection))
    story.append(
        Paragraph(
            "By signing below, both parties agree to the terms and conditions set forth in this booking confirmation.",
            sSmall,
        )
    )
    story.append(Spacer(1, 4 * mm))

    sig_data = [
        [
            Paragraph(
                "<b>FOR VINAFCO SHIPPING JSC</b>",
                ParagraphStyle(
                    "sl", fontName="Helvetica-Bold", fontSize=8, textColor=VINAFCO_BLUE
                ),
            ),
            Paragraph(
                f"<b>FOR {c['name'].upper()}</b>",
                ParagraphStyle(
                    "sr", fontName="Helvetica-Bold", fontSize=8, textColor=VINAFCO_BLUE
                ),
            ),
        ],
        [Paragraph("<br/><br/><br/>", sBody), Paragraph("<br/><br/><br/>", sBody)],
        [
            Paragraph("Signature: ___________________________", sBody),
            Paragraph("Signature: ___________________________", sBody),
        ],
        [
            Paragraph("Name:      ___________________________", sBody),
            Paragraph("Name:      ___________________________", sBody),
        ],
        [
            Paragraph("Title:     ___________________________", sBody),
            Paragraph("Title:     ___________________________", sBody),
        ],
        [
            Paragraph("Date:      ___________________________", sBody),
            Paragraph("Date:      ___________________________", sBody),
        ],
        [Paragraph("Stamp:", sBody), Paragraph("Stamp:", sBody)],
    ]
    sig_tbl = Table(sig_data, colWidths=["50%", "50%"])
    sig_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("LINEBEFORE", (1, 0), (1, -1), 0.5, MID_GRAY),
            ]
        )
    )
    story.append(sig_tbl)

    # Footer
    story.append(Spacer(1, 4 * mm))
    story.append(
        HRFlowable(width="100%", thickness=1, color=VINAFCO_BLUE, spaceAfter=3)
    )
    story.append(
        Paragraph(
            f"Document generated by Vinafco AI Booking System | {b['booking_ref']} | {b['issue_date']} | "
            "This document is system-generated. Final contract subject to Vinafco operations approval.",
            ParagraphStyle(
                "ft",
                fontName="Helvetica-Oblique",
                fontSize=6.5,
                textColor=colors.gray,
                alignment=TA_CENTER,
            ),
        )
    )

    doc.build(story)
    buf.seek(0)
    return buf.read()

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=BUCKET_ENDPOINT,
        aws_access_key_id=ACCESS_KEY_ID,
        aws_secret_access_key=SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            s3={
                "addressing_style": "path"
            }
        ),
    )


def upload_pdf(pdf_bytes: bytes, booking_ref: str) -> dict:
    s3 = get_s3_client()

    unique_id = uuid.uuid4().hex[:8]
    s3_key = f"contracts/{booking_ref}/{booking_ref}_{unique_id}.pdf"

    print(f"Uploading to s3://{BUCKET_NAME}/{s3_key} ...")

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=pdf_bytes,
        ContentType="application/pdf",
        Metadata={
            "booking-ref": booking_ref,
            "generated-at": datetime.now(timezone.utc).isoformat(),
            "generated-by": "vinafco-ai-booking",
        },
    )

    # Presigned URL — customer can open/download without credentials
    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET_NAME, "Key": s3_key},
        ExpiresIn=PRESIGN_EXPIRY,
    )

    print(f"Upload successful.")
    print(f"Presigned URL (expires in {PRESIGN_EXPIRY//3600}h):\n{presigned_url}")

    return {
        "s3_key": s3_key,
        "bucket": BUCKET_NAME,
        "presigned_url": presigned_url,
        "expires_in": PRESIGN_EXPIRY,
    }


def get_pdf_url(booking_ref: str) -> str:
    """Retrieve the presigned URL for an existing booking PDF."""
    s3 = get_s3_client()
    prefix = f"contracts/{booking_ref}/"
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
        if "Contents" in response and len(response["Contents"]) > 0:
            # Get the most recent one if multiple exist
            sorted_contents = sorted(response["Contents"], key=lambda x: x["LastModified"], reverse=True)
            s3_key = sorted_contents[0]["Key"]
            return s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": BUCKET_NAME, "Key": s3_key},
                ExpiresIn=PRESIGN_EXPIRY,
            )
    except Exception as e:
        print(f"Error fetching PDF URL for {booking_ref}: {str(e)}")
    return None


def run(booking: dict = BOOKING) -> dict:
    print("Generating PDF...")
    pdf_bytes = generate_pdf(booking)
    print(f"PDF generated: {len(pdf_bytes):,} bytes")
    original_hash = hashlib.sha256(pdf_bytes).hexdigest()
    print(f"PDF hash (SHA-256): {original_hash}")

    print("Uploading to Railway bucket...")
    result = upload_pdf(pdf_bytes, booking["booking_ref"])

    return {"pdf_size_bytes": len(pdf_bytes), "original_hash": original_hash, **result}
