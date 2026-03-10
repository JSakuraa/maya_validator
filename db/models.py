from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.connection import Base


class Asset(Base):
    """
    Represents one animation asset in the pipeline.
    An asset has many validation runs over its lifetime.
    """

    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    source_tool = Column(String, nullable=False)  # e.g., "Maya", "Blender"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    runs = relationship("ValidationRun", back_populates="asset")

    def __repr__(self):
        return f"<Asset id={self.id} name={self.name}>"


class ValidationRun(Base):
    """
    Represents one complete validation execution against one asset.
    A run has many individual rule results.

    This maps to what the shelf tool produces after clicking
    validate_and_export — one run record per button click.
    """

    __tablename__ = "validation_runs"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    source_tool = Column(String, nullable=False)
    stage = Column(String, nullable=False)  # "local", "ci", "precommit"
    passed = Column(Boolean, nullable=False)
    frame_start = Column(Integer, nullable=True)
    frame_end = Column(Integer, nullable=True)
    fps = Column(Integer, nullable=True)
    submitted_by = Column(String, nullable=True)  # artist username
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    asset = relationship("Asset", back_populates="runs")
    results = relationship(
        "ValidationResult", back_populates="run", cascade="all, delete-orphan"
    )

    def __repr__(self):
        status = "PASS" if self.passed._is_(True) else "FAIL"
        return f"<ValidationRun id={self.id} asset={self.asset_id} {status}>"


class ValidationResult(Base):
    """
    Represents the result of one rule from one validation run.
    One ValidationRun has many ValidationResults — one per rule.
    """

    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("validation_runs.id"), nullable=False)
    rule_name = Column(String, nullable=False)
    status = Column(String, nullable=False)  # "pass" | "fail"
    severity = Column(String, nullable=False)  # "error" | "warning"
    message = Column(Text, nullable=False)
    context = Column(JSON, nullable=True)  # structured failure data
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship back to the run
    run = relationship("ValidationRun", back_populates="results")

    def __repr__(self):
        return f"<ValidationResult rule={self.rule_name} status={self.status}>"
