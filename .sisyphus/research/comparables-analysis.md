# 3-Scheme Comparable Dossier (Task 2)

## Scope and scoring method

- Schemes compared: AI-first UGC, Hybrid OTT, FAST/CTV factory.
- Score scale is 1-5 where 5 is favorable (`quality`: better output quality, `compliance_risk`: lower operational/policy risk, `speed`: faster time-to-market, `cost`: better unit economics, `fit_en` and `fit_zh`: stronger track fit).
- This dossier is for strategy selection only (no implementation or deployment recommendations).

## Dual-track fit criteria (explicit EN + ZH)

### EN fit (`fit_en`)

- Breadth of language/variant support and subtitle throughput for global catalog scale.
- Turnaround speed for frequent publishing cadence.
- Channel/package flexibility across social, OTT, and CTV distribution shapes.

### ZH fit (`fit_zh`)

- Mandarin-first quality tolerance, including terminology consistency and subtitle readability.
- Need for stronger review controls in cases with culturally sensitive or context-heavy phrasing.
- Ability to support premium dubbing/subtitle workflows where monetization sensitivity is higher.

## Scheme-by-scheme analysis

### 1) AI-first UGC

- Strengths: fastest launch path and best cost score for high-volume creator catalogs.
- Trade-off: weakest compliance risk score due to thinner editorial controls and higher variance in localization quality.
- EN vs ZH fit: stronger for EN rapid distribution use cases than for ZH premium/sensitivity-heavy workflows.

### 2) Hybrid OTT

- Strengths: best quality and strongest ZH fit when automation is paired with targeted HITL review.
- Trade-off: slower and more expensive than AI-first UGC due to additional QA and governance overhead.
- EN vs ZH fit: balanced EN performance, strongest ZH resilience for policy-sensitive monetization contexts.

### 3) FAST/CTV factory

- Strengths: best EN fit for schedule-driven channel operations and repeatable packaging.
- Trade-off: middle-of-the-road compliance and quality without the deeper controls of Hybrid OTT.
- EN vs ZH fit: strong EN factory model; ZH fit is viable but may require selective review uplift on high-impact titles.

## Winner by context

- If the primary goal is speed plus low cost for large UGC throughput, pick **AI-first UGC**.
- If the primary goal is monetization-safe quality, especially for ZH-sensitive tracks, pick **Hybrid OTT**.
- If the primary goal is repeatable channel-scale throughput for EN distribution windows, pick **FAST/CTV factory**.

No single scheme dominates all criteria; choice should follow operating context and risk posture.

## Evidence anchors used for capability assumptions

- Google Cloud Speech-to-Text product page lists broad language coverage and both real-time and batch transcription capabilities: https://cloud.google.com/speech-to-text
- Azure Speech documentation hub enumerates speech-to-text, text-to-speech, and speech translation options that support enterprise localization pipelines: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/
- AWS media localization walkthrough and AWS solution material show subtitle localization workflow patterns and human-review-enhanced correction loops:
  - https://aws.amazon.com/blogs/media/media-content-localization-with-aws-ai-services-and-amazon-bedrock/
  - https://aws.amazon.com/solutions/implementations/content-localization-on-aws/

## Assumptions and limits

- Prior draft reference `.sisyphus/drafts/video-localization-research.md` was not present in workspace during Task 2 execution.
- Scores are relative strategic ratings, not absolute benchmark measurements; calibration is expected in Task 5 economics/SLO work.
- Compliance score represents expected operational risk exposure under a balanced-risk posture, not legal advice.
