from database import (
    get_recent_events,
    get_statistics,
    initialize_database,
    save_security_event,
)


def create_analysis_result(
    *,
    is_malicious=False,
    risk_level="low",
    risk_score=0,
    category="safe",
    recommended_action="allow",
    contains_sensitive_data=False,
    matched_patterns=None,
    sensitive_findings=None,
):
    return {
        "is_malicious": is_malicious,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "category": category,
        "recommended_action": recommended_action,
        "contains_sensitive_data": contains_sensitive_data,
        "matched_patterns": matched_patterns or [],
        "sensitive_findings": sensitive_findings or [],
    }


def test_database_is_initialized(tmp_path):
    database_path = tmp_path / "test.db"

    initialize_database(database_path)

    assert database_path.exists()
    assert get_recent_events(
        database_path=database_path
    ) == []


def test_security_event_is_saved_and_retrieved(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    analysis_result = create_analysis_result(
        is_malicious=True,
        risk_level="high",
        risk_score=80,
        category="prompt_injection",
        recommended_action="block",
        matched_patterns=["previous-instruction override"],
    )

    event_id = save_security_event(
        analysis_result=analysis_result,
        prompt_length=41,
        database_path=database_path,
    )

    events = get_recent_events(
        database_path=database_path
    )

    assert event_id == 1
    assert len(events) == 1
    assert events[0]["is_malicious"] is True
    assert events[0]["risk_score"] == 80
    assert events[0]["recommended_action"] == "block"
    assert events[0]["prompt_length"] == 41
    assert events[0]["matched_patterns"] == [
        "previous-instruction override"
    ]


def test_sensitive_types_are_stored_without_values(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    analysis_result = create_analysis_result(
        risk_level="medium",
        risk_score=60,
        category="sensitive_data_exposure",
        recommended_action="redact",
        contains_sensitive_data=True,
        sensitive_findings=[
            {
                "type": "email_address",
                "redacted_value": "st***************om",
                "start": 0,
                "end": 19,
                "detection_method": "pattern",
            }
        ],
    )

    save_security_event(
        analysis_result=analysis_result,
        prompt_length=19,
        database_path=database_path,
    )

    event = get_recent_events(
        database_path=database_path
    )[0]

    assert event["contains_sensitive_data"] is True
    assert event["sensitive_data_types"] == [
        "email_address"
    ]
    assert "sensitive_findings" not in event
    assert "redacted_value" not in event


def test_statistics_are_calculated(tmp_path):
    database_path = tmp_path / "test.db"
    initialize_database(database_path)

    safe_result = create_analysis_result()

    sensitive_result = create_analysis_result(
        risk_level="medium",
        risk_score=60,
        category="sensitive_data_exposure",
        recommended_action="redact",
        contains_sensitive_data=True,
        sensitive_findings=[
            {
                "type": "email_address",
            }
        ],
    )

    malicious_result = create_analysis_result(
        is_malicious=True,
        risk_level="high",
        risk_score=80,
        category="prompt_injection",
        recommended_action="block",
        matched_patterns=["previous-instruction override"],
    )

    for result in [
        safe_result,
        sensitive_result,
        malicious_result,
    ]:
        save_security_event(
            analysis_result=result,
            prompt_length=25,
            database_path=database_path,
        )

    statistics = get_statistics(
        database_path=database_path
    )

    assert statistics["total_scans"] == 3
    assert statistics["malicious_prompts"] == 1
    assert statistics["sensitive_prompts"] == 1
    assert statistics["actions"] == {
        "allow": 1,
        "redact": 1,
        "block": 1,
    }