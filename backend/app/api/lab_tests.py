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

ALLOWED_TYPES = {
    "application/pdf", "image/jpeg", "image/png", "image/jpg",
    "text/plain", "application/json"
}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


# ── Storage helpers ────────────────────────────────────────────────────────────

def _blob_client():
    """Return an Azure BlobServiceClient (only called when use_azure_storage=True)."""
    from azure.storage.blob import BlobServiceClient
    return BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)


def _save_file_local(content: bytes, stored_filename: str) -> str:
    """Write bytes to local disk and return the stored path."""
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, stored_filename)
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


def _save_file_azure(content: bytes, stored_filename: str, content_type: str) -> str:
    """Upload bytes to Azure Blob Storage and return the blob URL."""
    client = _blob_client()
    container = client.get_container_client(settings.azure_storage_container)
    blob_path = f"lab_tests/{stored_filename}"
    container.upload_blob(
        name=blob_path,
        data=content,
        content_settings={"content_type": content_type},
        overwrite=True,
    )
    return f"azure://{settings.azure_storage_container}/{blob_path}"


def _delete_file(file_path: Optional[str]):
    """Delete a file from local disk or Azure Blob Storage."""
    if not file_path:
        return
    if file_path.startswith("azure://"):
        try:
            # Parse azure://<container>/<blob_path>
            rest = file_path[len("azure://"):]
            container_name, blob_path = rest.split("/", 1)
            client = _blob_client()
            client.get_blob_client(container=container_name, blob=blob_path).delete_blob()
        except Exception:
            pass
    elif os.path.exists(file_path):
        os.remove(file_path)


# ── Endpoints ──────────────────────────────────────────────────────────────────

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
            detail="File type not supported. Allowed: PDF, JPEG, PNG, TXT, JSON"
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")

    file_ext = os.path.splitext(file.filename or "upload")[1]
    stored_filename = f"{uuid.uuid4()}{file_ext}"

    if settings.use_azure_storage:
        file_path = _save_file_azure(content, stored_filename, file.content_type or "application/octet-stream")
    else:
        file_path = _save_file_local(content, stored_filename)

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

    await _process_lab_test(lab_test, content, file.content_type or "", db)

    return lab_test


async def _process_lab_test(lab_test: LabTest, content: bytes, content_type: str, db: Session):
    """Extract text and parse lab results using AI."""
    from app.services.ai_service import parse_lab_test

    user = db.query(User).filter_by(id=lab_test.user_id).first()

    try:
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
            import base64
            b64 = base64.standard_b64encode(content).decode()
            text_content = f"[IMAGE:{content_type}:{b64[:100]}...]"
        else:
            text_content = content.decode("utf-8", errors="replace")

        parsed = await parse_lab_test(text_content, content_type, user, db)

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
    _delete_file(test.file_path)
    db.delete(test)
    db.commit()
    return {"status": "deleted"}
