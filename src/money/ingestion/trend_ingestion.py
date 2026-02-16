from hashlib import sha1
from typing import Any, Dict, List, Optional, Tuple

from money.contracts.validate_task1 import validate_contract


FORBIDDEN_SOURCE_MEDIA_FIELDS = {
    "media_blob",
    "media_bytes",
    "media_url",
    "source_clip_uri",
    "source_media_path",
    "source_media_url",
}


class IngestionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class TrendCandidate:
    def __init__(
        self,
        candidate_id: str,
        source_platform: str,
        external_id: str,
        topic: str,
        signal_score: float,
        captured_at: str,
        monetization_score: float,
        analysis_only: bool,
        beat_map_artifact: str,
        pacing_map_artifact: str,
    ) -> None:
        self.candidate_id = candidate_id
        self.source_platform = source_platform
        self.external_id = external_id
        self.topic = topic
        self.signal_score = signal_score
        self.captured_at = captured_at
        self.monetization_score = monetization_score
        self.analysis_only = analysis_only
        self.beat_map_artifact = beat_map_artifact
        self.pacing_map_artifact = pacing_map_artifact


class IngestionResult:
    def __init__(self, created: bool, candidate: TrendCandidate) -> None:
        self.created = created
        self.candidate = candidate


class TrendIngestionService:
    def __init__(
        self,
        max_new_candidates: int = 100,
        backoff_base_seconds: int = 2,
    ) -> None:
        self._candidates_by_source_id = {}  # type: Dict[Tuple[str, str], TrendCandidate]
        self._candidates_by_id = {}  # type: Dict[str, TrendCandidate]
        self._max_new_candidates = max_new_candidates
        self._backoff_base_seconds = backoff_base_seconds
        self._new_candidate_count = 0

    def ingest(
        self,
        *,
        source_platform: str,
        external_id: str,
        topic: str,
        signal_score: float,
        captured_at: str,
        analysis_only: bool,
        metadata: Optional[Dict[str, Any]] = None,
        engagement_velocity: float = 0.0,
        advertiser_fit: float = 0.5,
        region_match: float = 0.5,
        backoff_attempt: int = 0,
    ) -> IngestionResult:
        self._assert_metadata_only(metadata or {})

        key = (source_platform, external_id)
        if key in self._candidates_by_source_id:
            return IngestionResult(False, self._candidates_by_source_id[key])

        self._enforce_rate_limit(backoff_attempt)

        candidate_id = self._candidate_id(source_platform, external_id)
        contract_payload = {
            "candidate_id": candidate_id,
            "source_platform": source_platform,
            "external_id": external_id,
            "topic": topic,
            "signal_score": signal_score,
            "captured_at": captured_at,
        }
        validate_contract("trend_candidate", contract_payload)

        monetization_score = self._rank_monetization(
            signal_score=signal_score,
            engagement_velocity=engagement_velocity,
            advertiser_fit=advertiser_fit,
            region_match=region_match,
        )

        candidate = TrendCandidate(
            candidate_id,
            source_platform,
            external_id,
            topic,
            signal_score,
            captured_at,
            monetization_score,
            analysis_only,
            "artifacts/{0}/beat_map.json".format(candidate_id),
            "artifacts/{0}/pacing_map.json".format(candidate_id),
        )
        self._candidates_by_source_id[key] = candidate
        self._candidates_by_id[candidate_id] = candidate
        self._new_candidate_count += 1
        return IngestionResult(True, candidate)

    def list_ranked_candidates(self) -> List[TrendCandidate]:
        candidates = list(self._candidates_by_id.values())
        candidates.sort(
            key=lambda item: (
                -item.monetization_score,
                item.captured_at,
                item.candidate_id,
            )
        )
        return candidates

    def candidate_count(self) -> int:
        return len(self._candidates_by_id)

    def build_publish_manifest(self, candidate_ids: List[str]) -> List[Dict[str, Any]]:
        manifest = []  # type: List[Dict[str, Any]]
        for candidate_id in candidate_ids:
            candidate = self._candidates_by_id[candidate_id]
            if candidate.analysis_only:
                raise IngestionError(
                    code="ANALYSIS_ONLY_BLOCKED_FROM_PUBLISH_MANIFEST",
                    message="analysis_only candidates cannot be included in publish manifests",
                )
            manifest.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "source_platform": candidate.source_platform,
                    "external_id": candidate.external_id,
                    "topic": candidate.topic,
                    "signal_score": candidate.signal_score,
                    "analysis_only": candidate.analysis_only,
                }
            )
        return manifest

    def list_publishable_candidates(self) -> List[TrendCandidate]:
        return [candidate for candidate in self.list_ranked_candidates() if not candidate.analysis_only]

    def _assert_metadata_only(self, metadata: Dict[str, Any]) -> None:
        for field in sorted(FORBIDDEN_SOURCE_MEDIA_FIELDS):
            if field in metadata:
                raise IngestionError(
                    code="SOURCE_MEDIA_REUSE_FORBIDDEN",
                    message="source media reuse is forbidden for trend ingestion",
                )

    def _enforce_rate_limit(self, backoff_attempt: int) -> None:
        if self._new_candidate_count < self._max_new_candidates:
            return
        retry_after = self._backoff_base_seconds * (2 ** max(0, int(backoff_attempt)))
        raise IngestionError(
            code="RATE_LIMIT_BACKOFF_REQUIRED",
            message="rate limit exceeded; retry_after_seconds={0}".format(retry_after),
        )

    def _candidate_id(self, source_platform: str, external_id: str) -> str:
        digest = sha1("{0}:{1}".format(source_platform, external_id).encode("utf-8")).hexdigest()
        return "trend-{0}".format(digest[:12])

    def _rank_monetization(
        self,
        *,
        signal_score: float,
        engagement_velocity: float,
        advertiser_fit: float,
        region_match: float,
    ) -> float:
        bounded_signal = self._clamp01(signal_score)
        bounded_velocity = self._clamp01(engagement_velocity)
        bounded_advertiser_fit = self._clamp01(advertiser_fit)
        bounded_region_match = self._clamp01(region_match)
        weighted_sum = (
            (0.55 * bounded_signal)
            + (0.25 * bounded_velocity)
            + (0.15 * bounded_advertiser_fit)
            + (0.05 * bounded_region_match)
        )
        return round(weighted_sum, 6)

    def _clamp01(self, value: float) -> float:
        if value < 0:
            return 0.0
        if value > 1:
            return 1.0
        return float(value)
