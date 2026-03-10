# db/repository.py

from sqlalchemy.orm import Session
from sqlalchemy import desc
from db.models import Asset, ValidationRun, ValidationResult
from typing import Optional


# ─── Asset functions ──────────────────


def get_or_create_asset(db: Session, name: str, source_tool: str) -> Asset:
    """
    Returns the existing asset with this name, or creates a new one.
    This prevents duplicate asset records for the same file.
    """
    asset = db.query(Asset).filter(Asset.name == name).first()
    if asset:
        return asset

    asset = Asset(name=name, source_tool=source_tool)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def get_asset_by_id(db: Session, asset_id: int) -> Optional[Asset]:
    return db.query(Asset).filter(Asset.id == asset_id).first()


def get_all_assets(db: Session, skip: int = 0, limit: int = 100) -> list[Asset]:
    return db.query(Asset).offset(skip).limit(limit).all()


# ─── ValidationRun functions ────────────────────


def create_validation_run(
    db: Session,
    asset_id: int,
    source_tool: str,
    stage: str,
    passed: bool,
    frame_start: int,
    frame_end: int,
    fps: int,
    submitted_by: str = "",
) -> ValidationRun:
    """
    Creates a new ValidationRun record.
    Results are added separately via create_validation_result().
    """
    run = ValidationRun(
        asset_id=asset_id,
        source_tool=source_tool,
        stage=stage,
        passed=passed,
        frame_start=frame_start,
        frame_end=frame_end,
        fps=fps,
        submitted_by=submitted_by,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_run_by_id(db: Session, run_id: int) -> Optional[ValidationRun]:
    return db.query(ValidationRun).filter(ValidationRun.id == run_id).first()


def get_runs_for_asset(
    db: Session, asset_id: int, limit: int = 20
) -> list[ValidationRun]:
    """Returns the most recent runs for an asset, newest first."""
    return (
        db.query(ValidationRun)
        .filter(ValidationRun.asset_id == asset_id)
        .order_by(desc(ValidationRun.created_at))
        .limit(limit)
        .all()
    )


def get_recent_failures(db: Session, limit: int = 50) -> list[ValidationRun]:
    """Returns recent failed runs across all assets."""
    return (
        db.query(ValidationRun)
        .filter(ValidationRun.passed == False)
        .order_by(desc(ValidationRun.created_at))
        .limit(limit)
        .all()
    )


# ─── ValidationResult functions ────────────────


def create_validation_result(
    db: Session,
    run_id: int,
    rule_name: str,
    status: str,
    severity: str,
    message: str,
    context: dict = {},
) -> ValidationResult:
    result = ValidationResult(
        run_id=run_id,
        rule_name=rule_name,
        status=status,
        severity=severity,
        message=message,
        context=context or {},
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def create_validation_results_bulk(
    db: Session,
    run_id: int,
    results: list[dict],
) -> list[ValidationResult]:
    """
    Creates multiple result records in a single transaction.
    More efficient than calling create_validation_result() in a loop
    because it uses one commit rather than one per result.
    """
    db_results = [
        ValidationResult(
            run_id=run_id,
            rule_name=r["rule_name"],
            status=r["status"],
            severity=r["severity"],
            message=r["message"],
            context=r.get("context", {}),
        )
        for r in results
    ]
    db.add_all(db_results)
    db.commit()
    return db_results


def get_results_for_run(db: Session, run_id: int) -> list[ValidationResult]:
    return db.query(ValidationResult).filter(ValidationResult.run_id == run_id).all()
