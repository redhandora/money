import json
from pathlib import Path

import pytest

from money.ingestion import IngestionError, TrendIngestionService


def test_duplicate_trend_ingestion_is_idempotent_and_writes_evidence() -> None:
    service = TrendIngestionService()

    first = service.ingest(
        source_platform="youtube",
        external_id="trend-777",
        topic="personal finance",
        signal_score=0.74,
        captured_at="2026-02-16T01:00:00Z",
        analysis_only=False,
        engagement_velocity=0.80,
        advertiser_fit=0.60,
        region_match=0.70,
    )
    second = service.ingest(
        source_platform="youtube",
        external_id="trend-777",
        topic="personal finance updated",
        signal_score=0.20,
        captured_at="2026-02-16T02:00:00Z",
        analysis_only=True,
        engagement_velocity=0.10,
        advertiser_fit=0.10,
        region_match=0.10,
    )

    assert first.created is True
    assert second.created is False
    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert first.candidate.external_id == "trend-777"
    assert service.candidate_count() == 1

    ranked = service.list_ranked_candidates()
    assert len(ranked) == 1
    assert ranked[0].monetization_score == pytest.approx(0.732)

    root_dir = Path(__file__).resolve().parents[1]
    evidence_path = root_dir / ".sisyphus" / "evidence" / "task-2-idempotent.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "scenario": "duplicate_trend_ingestion_is_idempotent",
        "result": {
            "status": "pass",
            "record_count": service.candidate_count(),
            "source_platform": first.candidate.source_platform,
            "external_id": first.candidate.external_id,
            "candidate_id": first.candidate.candidate_id,
            "analysis_only": first.candidate.analysis_only,
            "monetization_score": first.candidate.monetization_score,
        },
    }
    evidence_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_analysis_only_candidate_is_blocked_from_publish_manifest() -> None:
    service = TrendIngestionService()
    analysis_result = service.ingest(
        source_platform="tiktok",
        external_id="tt-42",
        topic="budget hacks",
        signal_score=0.51,
        captured_at="2026-02-16T03:00:00Z",
        analysis_only=True,
        engagement_velocity=0.50,
        advertiser_fit=0.40,
        region_match=0.60,
    )
    publish_result = service.ingest(
        source_platform="youtube",
        external_id="yt-42",
        topic="index fund basics",
        signal_score=0.70,
        captured_at="2026-02-16T04:00:00Z",
        analysis_only=False,
        engagement_velocity=0.60,
        advertiser_fit=0.75,
        region_match=0.80,
    )

    assert analysis_result.candidate.analysis_only is True
    assert analysis_result.candidate.beat_map_artifact.endswith("beat_map.json")
    assert analysis_result.candidate.pacing_map_artifact.endswith("pacing_map.json")

    with pytest.raises(IngestionError) as exc:
        service.build_publish_manifest(
            [analysis_result.candidate.candidate_id, publish_result.candidate.candidate_id]
        )
    assert exc.value.code == "ANALYSIS_ONLY_BLOCKED_FROM_PUBLISH_MANIFEST"

    publishable = service.list_publishable_candidates()
    assert [item.candidate_id for item in publishable] == [publish_result.candidate.candidate_id]


def test_ingestion_rejects_source_media_reuse_fields() -> None:
    service = TrendIngestionService()

    with pytest.raises(IngestionError) as exc:
        service.ingest(
            source_platform="youtube",
            external_id="rejected-1",
            topic="frugal meals",
            signal_score=0.45,
            captured_at="2026-02-16T05:00:00Z",
            analysis_only=False,
            metadata={"source_media_url": "https://example.com/source.mp4"},
        )

    assert exc.value.code == "SOURCE_MEDIA_REUSE_FORBIDDEN"


def test_rate_limit_enforces_backoff_for_new_candidates() -> None:
    service = TrendIngestionService(max_new_candidates=1, backoff_base_seconds=3)

    created = service.ingest(
        source_platform="youtube",
        external_id="quota-ok",
        topic="credit score basics",
        signal_score=0.62,
        captured_at="2026-02-16T06:00:00Z",
        analysis_only=False,
    )
    assert created.created is True

    with pytest.raises(IngestionError) as exc:
        service.ingest(
            source_platform="tiktok",
            external_id="quota-blocked",
            topic="debt snowball",
            signal_score=0.63,
            captured_at="2026-02-16T06:01:00Z",
            analysis_only=False,
            backoff_attempt=2,
        )

    assert exc.value.code == "RATE_LIMIT_BACKOFF_REQUIRED"
    assert "retry_after_seconds=12" in str(exc.value)
