"""Conversational risk-assessment engine for Citizen Fraud Shield.

Prompt 6.1 & 6.2:
- Free-text description + structured Q&A.
- Verdicts: 'likely_safe' | 'suspicious_verify_first' | 'high_risk_stop_now'.
- Plain-language explanation + next steps (NCRB cybercrime.gov.in & 1930 helpline).
- English + Hindi translation support stub.
- Biased toward caution: false negatives are costly.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from app.models.scam_detection.predictor import ScamDetectionModel

_scam_model = ScamDetectionModel()

VerdictType = Literal["likely_safe", "suspicious_verify_first", "high_risk_stop_now"]


TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "high_risk_explanation": "CRITICAL SCAM RISK: Signs of digital arrest, government authority impersonation, or immediate payment pressure detected.",
        "suspicious_explanation": "SUSPICIOUS: Features resemble known scam patterns. Verify independently before taking any action.",
        "safe_explanation": "LOW RISK DETECTED: No strong scam indicators found, but remain cautious. Never share OTPs or passwords.",
        "step_1": "Do NOT transfer any money or share OTPs / passwords.",
        "step_2": "Disconnect the call or stop messaging immediately.",
        "step_3": "Report this incident on the National Cyber Crime Reporting Portal (cybercrime.gov.in) or call 1930.",
        "helpline_text": "National Cyber Crime Helpline: Call 1930",
    },
    "hi": {
        "high_risk_explanation": "अत्यंत जोखिम (स्कैम की आशंका): डिजिटल अरेस्ट, सरकारी अधिकारी के नाम पर धोखाधड़ी या तुरंत पैसे मांगने के संकेत मिले हैं।",
        "suspicious_explanation": "संदिग्ध: यह पैटर्न धोखाधड़ी से मिलता-जुलता है। कोई भी कदम उठाने से पहले स्वतंत्र रूप से जांच करें।",
        "safe_explanation": "कम जोखिम: धोखाधड़ी का कोई स्पष्ट संकेत नहीं मिला, फिर भी सावधान रहें। OTP या पासवर्ड कभी साझा न करें।",
        "step_1": "कोई भी पैसा ट्रांसफर न करें और OTP या पासवर्ड शेयर न करें।",
        "step_2": "कॉल तुरंत काट दें या मैसेज करना बंद करें।",
        "step_3": "राष्ट्रीय साइबर अपराध पोर्टल (cybercrime.gov.in) पर रिपोर्ट करें या 1930 पर कॉल करें।",
        "helpline_text": "राष्ट्रीय साइबर अपराध हेल्पलाइन: 1930 पर कॉल करें",
    },
}


class AssessmentResult(TypedDict):
    verdict: VerdictType
    confidence_score: float
    plain_explanation: str
    next_steps: list[str]
    helpline: str
    report_url: str
    language: str
    matched_signals: list[str]
    model_version: str


class CitizenShieldConversationEngine:
    version = "citizen-shield-0.2.0"

    def assess(
        self,
        description: str,
        answers: dict[str, Any] | None = None,
        language: str = "en",
    ) -> AssessmentResult:
        answers = answers or {}
        lang_key = "hi" if language.lower() in {"hi", "hindi"} else "en"
        t = TRANSLATIONS.get(lang_key, TRANSLATIONS["en"])

        # 1. Base prediction from ScamDetectionModel
        scam_pred = _scam_model.predict(description)
        base_score = float(scam_pred.get("risk_score", 0.0))

        # 2. Q&A boosts
        video_hold = bool(answers.get("video_hold") or answers.get("stay_on_video"))
        authority_mentioned = bool(
            answers.get("authority_mentioned")
            or answers.get("mentioned_cbi_customs")
            or answers.get("mentioned_arrest")
        )
        payment_requested = bool(
            answers.get("payment_requested")
            or answers.get("asked_money")
            or answers.get("asked_otp")
        )

        boosts = 0.0
        signals = list(scam_pred.get("signals", []))

        if video_hold:
            boosts += 0.35
            signals.append("q_a:video_hold")
        if authority_mentioned:
            boosts += 0.35
            signals.append("q_a:authority_impersonation")
        if payment_requested:
            boosts += 0.30
            signals.append("q_a:payment_or_otp_requested")

        # Use the full ML base score — no longer halved.
        # Q&A answers add on top. Cap at 1.0.
        total_score = min(1.0, base_score + boosts)

        # 3. Verdict selection (biased toward caution: threshold for 'safe' is strict < 0.20)
        if total_score >= 0.40 or video_hold or (authority_mentioned and payment_requested):
            verdict: VerdictType = "high_risk_stop_now"
            explanation = t["high_risk_explanation"]
        elif total_score >= 0.15 or authority_mentioned or payment_requested:
            verdict = "suspicious_verify_first"
            explanation = t["suspicious_explanation"]
        else:
            verdict = "likely_safe"
            explanation = t["safe_explanation"]

        next_steps = [t["step_1"], t["step_2"], t["step_3"]]

        return {
            "verdict": verdict,
            "confidence_score": round(total_score, 3),
            "plain_explanation": explanation,
            "next_steps": next_steps,
            "helpline": "1930",
            "report_url": "https://cybercrime.gov.in",
            "language": lang_key,
            "matched_signals": signals,
            "model_version": self.version,
        }
