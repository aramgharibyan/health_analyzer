from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class LabTest(Base):
    __tablename__ = "lab_tests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    test_name = Column(String, nullable=False)
    lab_name = Column(String)
    ordered_by = Column(String)  # doctor name
    test_date = Column(DateTime(timezone=True))
    received_date = Column(DateTime(timezone=True))
    file_path = Column(String)  # stored PDF/image path
    file_name = Column(String)

    notes = Column(Text)
    parsed_summary = Column(Text)  # AI-generated summary
    status = Column(String, default="pending")  # pending, processed, error
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="lab_tests")
    results = relationship("LabTestResult", back_populates="lab_test", cascade="all, delete-orphan")


class LabTestResult(Base):
    __tablename__ = "lab_test_results"

    id = Column(Integer, primary_key=True, index=True)
    lab_test_id = Column(Integer, ForeignKey("lab_tests.id"), nullable=False)

    biomarker_name = Column(String, nullable=False)
    value = Column(Float)
    unit = Column(String)
    reference_min = Column(Float)
    reference_max = Column(Float)
    reference_text = Column(String)
    status = Column(String)  # normal, low, high, critical_low, critical_high

    category = Column(String)  # metabolic, lipid, thyroid, cbc, etc.
    interpretation = Column(Text)  # AI-generated interpretation

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lab_test = relationship("LabTest", back_populates="results")
