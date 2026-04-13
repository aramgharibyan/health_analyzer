from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class LabTestResultResponse(BaseModel):
    id: int
    biomarker_name: str
    value: Optional[float]
    unit: Optional[str]
    reference_min: Optional[float]
    reference_max: Optional[float]
    reference_text: Optional[str]
    status: Optional[str]
    category: Optional[str]
    interpretation: Optional[str]

    model_config = {"from_attributes": True}


class LabTestCreate(BaseModel):
    test_name: str
    lab_name: Optional[str] = None
    ordered_by: Optional[str] = None
    test_date: Optional[datetime] = None
    notes: Optional[str] = None


class LabTestResponse(BaseModel):
    id: int
    test_name: str
    lab_name: Optional[str]
    ordered_by: Optional[str]
    test_date: Optional[datetime]
    file_name: Optional[str]
    notes: Optional[str]
    parsed_summary: Optional[str]
    status: str
    results: List[LabTestResultResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}
