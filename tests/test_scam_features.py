"""Unit tests for scam feature extraction."""

from app.models.scam_detection.feature_extractor import extract_features


def test_impersonation_and_urgency_features():
    text = (
        "This is CBI and Enforcement Directorate. You are under digital arrest. "
        "Your Aadhaar linked to crime. Act now immediately. Do not disconnect "
        "or tell anyone. Stay on video call and share OTP for KYC."
    )
    feats = extract_features(text)
    assert feats.impersonation_keyword_count >= 2
    assert feats.urgency_score > 0
    assert feats.isolation_score > 0
    assert feats.request_for_video_hold is True
    assert feats.payment_otp_request is True


def test_benign_message_low_signals():
    feats = extract_features("Hey, want to grab lunch tomorrow near the office?")
    assert feats.impersonation_keyword_count == 0
    assert feats.request_for_video_hold is False
    assert feats.payment_otp_request is False
