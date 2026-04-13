import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.lab_test import LabTest, LabTestResult
from app.schemas.lab_test import LabTestResponse, LabTestCreate
from app.config import get_settings

router = APIRouter(prefix="/lab-tests", tags=["Lab Tests"])
settings = get_settings()

UPLOAD_DIR = "uploads/lab_tests"
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_TYPES = {
    "application/pdf", "image/jpeg", "image/png", "image/jpg",
    "text/plain", "application/json"
}


@router.post("/upload", response_model=LabTestResponse)
async def upload_lab_test(
    file: UploadFile = File(...),
    test_name: str = Form(...),
    lab_name: Optional[str] = Form(None),
    ordered_by: Optional[str] = Form(None),
    test_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: PDF, JPEG, PNG, TXT, JSON"
        )

    # Save file
    file_ext = os.path.splitext(file.filename)[1]
    stored_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Parse test_date
    parsed_date = None
    if test_date:
        try:
            parsed_date = datetime.fromisoformat(test_date)
        except Exception:
            pass

    lab_test = LabTest(
        user_id=current_user.id,
        test_name=test_name,
        lab_name=lab_name,
        ordered_by=ordered_by,
        test_date=parsed_date,
        file_path=file_path,
        file_name=file.filename,
        notes=notes,
        status="pending",
    )
    db.add(lab_test)
    db.commit()
    db.refresh(lab_test)

    # Process asynchronously
    await _process_lab_test(lab_test, content, file.content_type, db)

    return lab_test


async def _process_lab_test(lab_test: LabTest, content: bytes, content_type: str, db: Session):
    """Extract text and parse lab results using AI."""
    from app.services.ai_service import parse_lab_test
    from app.models.user import User

    user = db.query(User).filter_by(id=lab_test.user_id).first()

    try:
        # Extract text content
        text_content = ""
        if content_type == "application/pdf":
            try:
                import PyPDF2
                import io
                reader = PyPDF2.PdfReader(io.BytesIO(content))
                for page in reader.pages:
                    text_content += page.extract_text() + "\n"
            except Exception as e:
                text_content = f"[PDF extraction failed: {e}]"
        elif content_type.startswith("image/"):
            # For images, pass base64 encoded content to Claude vision
            import base64
            b64 = base64.standard_b64encode(content).decode()
            text_content = f"[IMAGE:{content_type}:{b64[:100]}...]"  # placeholder
        else:
            text_content = content.decode("utf-8", errors="replace")

        # Use AI to parse
        parsed = await parse_lab_test(text_content, content_type, user, db)

        # Update lab test with parsed data
        lab_test.parsed_summary = parsed.get("summary", "")
        if not lab_test.lab_name and parsed.get("lab_name"):
            lab_test.lab_name = parsed["lab_name"]
        if not lab_test.ordered_by and parsed.get("ordered_by"):
            lab_test.ordered_by = parsed["ordered_by"]
        if not lab_test.test_date and parsed.get("test_date"):
            try:
                lab_test.test_date = datetime.fromisoformat(parsed["test_date"])
            except Exception:
                pass

        # Save individual results
        for result_data in parsed.get("results", []):
            result = LabTestResult(
                lab_test_id=lab_test.id,
                biomarker_name=result_data.get("biomarker_name", "Unknown"),
                value=result_data.get("value"),
                unit=result_data.get("unit"),
                reference_min=result_data.get("reference_min"),
                reference_max=result_data.get("reference_max"),
                reference_text=result_data.get("reference_text"),
                status=result_data.get("status", "normal"),
                category=result_data.get("category", "other"),
                interpretation=result_data.get("interpretation"),
            )
            db.add(result)

        lab_test.status = "processed"
    except Exception as e:
        lab_test.status = "error"
        lab_test.parsed_summary = f"Processing error: {str(e)}"

    db.commit()


@router.get("/", response_model=List[LabTestResponse])
def list_lab_tests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return (
        db.query(LabTest)
        .filter_by(user_id=current_user.id)
        .order_by(LabTest.created_at.desc())
        .all()
    )


@router.get("/{test_id}", response_model=LabTestResponse)
def get_lab_test(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    test = db.query(LabTest).filter_by(id=test_id, user_id=current_user.id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Lab test not found")
    return test


@router.delete("/{test_id}")
def delete_lab_test(
    test_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    test = db.query(LabTest).filter_by(id=test_id, user_id=current_user.id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Lab test not found")
    if test.file_path and os.path.exists(test.file_path):
        os.remove(test.file_path)
    db.delete(test)
    db.commit()
    return {"status": "deleted"}
