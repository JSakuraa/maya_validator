from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Float,
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
    pass


class ValidationResult(Base):
    pass
