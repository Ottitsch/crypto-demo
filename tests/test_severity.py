from pof.severity import SEVERITY, severity_for


def test_abuse_wins_over_category():
    # malware category + ransomware abuse -> ransomware (1.0), not malware (0.8)
    assert severity_for(category="malware", abuse="ransomware") == 1.0


def test_unknown_falls_back_to_zero():
    assert severity_for(category="not_a_real_category") == 0.0
    assert severity_for(category=None, abuse=None) == 0.0


def test_case_and_whitespace_normalization():
    assert severity_for(category="  Darknet_Market ") == SEVERITY["darknet_market"]
    assert severity_for(category="Mixing Service") == SEVERITY["mixing_service"]
