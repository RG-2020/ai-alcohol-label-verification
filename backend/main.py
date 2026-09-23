import time

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ocr import extract_text_from_image
from verifier import verify_fields, extract_scan_fields


app = FastAPI(
    title="LabelGuard AI",
    version="1.0.0",
    description="Alcohol Label Verification Prototype"
)


# Let the local React app talk to the FastAPI backend during development.
# I include 5173 and 5174 because Vite can move to 5174 if 5173 is busy.
app.add_middleware(
    CORSMiddleware,


    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "https://labelguard-ai-k2f2.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {
        "message": "LabelGuard AI backend is running"
    }


def calculate_combined_confidence(
    front_confidence,
    back_confidence,
    back_text
):
    """
    Average front and back confidence when both labels were read.
    If there is no usable back text, just use the front confidence.
    """
    if back_text and back_text.strip():
        return round(
            (
                float(front_confidence)
                + float(back_confidence)
            )
            / 2,
            1
        )

    return round(
        float(front_confidence),
        1
    )


@app.post("/verify")
async def verify_label(
    front_image: UploadFile = File(...),
    back_image: UploadFile | None = File(None),
    brand_name: str = Form(...),
    class_type: str = Form(...),
    alcohol_content: str = Form(...),
    net_contents: str = Form(...),
    producer_name: str = Form(...),
    producer_address: str = Form(...),
    use_center_crop: bool = Form(False),
):
    start_time = time.perf_counter()

    # Read the front label first because brand and class/type usually live there.
    front_bytes = await front_image.read()

    front_text, front_confidence = extract_text_from_image(
        front_bytes,
        use_center_crop=use_center_crop,
        label_side="front"
    )

    # The back label is optional, but it usually contains ABV, volume,
    # producer information, origin, and government-warning text.
    back_text = ""
    back_confidence = 0

    if back_image is not None:
        back_bytes = await back_image.read()

        if back_bytes:
            back_text, back_confidence = extract_text_from_image(
                back_bytes,
                use_center_crop=use_center_crop,
                label_side="back"
            )

    extracted_text = (
        front_text
        + "\n"
        + back_text
    ).strip()

    confidence = calculate_combined_confidence(
        front_confidence,
        back_confidence,
        back_text
    )

    # Keep front and back OCR separate during verification.
    # This prevents a back label from making the wrong front label look correct.
    verification_results = verify_fields(
        front_text,
        back_text,
        brand_name,
        class_type,
        alcohol_content,
        net_contents,
        producer_name,
        producer_address
    )

    statuses = [
        result.get("status", "REVIEW")
        for result in verification_results.values()
    ]

    if "MISMATCH" in statuses:
        overall_result = "POTENTIAL MISMATCH"
    elif "REVIEW" in statuses:
        overall_result = "MANUAL REVIEW REQUIRED"
    else:
        overall_result = "PASS"

    processing_time = round(
        time.perf_counter() - start_time,
        2
    )

    return {
        "front_filename": front_image.filename,
        "back_filename": (
            back_image.filename
            if back_image is not None
            else None
        ),
        "status": "processed",
        "message": "Label image processed successfully",
        "overall_result": overall_result,
        "ocr_confidence": confidence,
        "processing_time_seconds": processing_time,
        "application_data": {
            "brand_name": brand_name,
            "class_type": class_type,
            "alcohol_content": alcohol_content,
            "net_contents": net_contents,
            "producer_name": producer_name,
            "producer_address": producer_address,
        },
        "verification_results": verification_results,
        "front_ocr_text": front_text,
        "back_ocr_text": back_text,
        "extracted_text": extracted_text,
    }


@app.post("/scan")
async def scan_label(
    front_image: UploadFile = File(...),
    back_image: UploadFile | None = File(None),
    use_center_crop: bool = Form(False),
):
    start_time = time.perf_counter()

    front_bytes = await front_image.read()

    front_text, front_confidence = extract_text_from_image(
        front_bytes,
        use_center_crop=use_center_crop,
        label_side="front"
    )

    back_text = ""
    back_confidence = 0

    if back_image is not None:
        back_bytes = await back_image.read()

        if back_bytes:
            back_text, back_confidence = extract_text_from_image(
                back_bytes,
                use_center_crop=use_center_crop,
                label_side="back"
            )

    extracted_text = (
        front_text
        + "\n"
        + back_text
    ).strip()

    confidence = calculate_combined_confidence(
        front_confidence,
        back_confidence,
        back_text
    )

    scan_data = extract_scan_fields(
        extracted_text
    )

    processing_time = round(
        time.perf_counter() - start_time,
        2
    )

    return {
        "front_filename": front_image.filename,
        "back_filename": (
            back_image.filename
            if back_image is not None
            else None
        ),
        "status": "processed",
        "message": "Label image processed successfully",
        "ocr_confidence": confidence,
        "processing_time_seconds": processing_time,
        "front_ocr_text": front_text,
        "back_ocr_text": back_text,
        "extracted_text": extracted_text,
        "scan_data": scan_data,
    }
