def _sample_payload():
    return {
        "blend_components": {
            "lgo": 0.6,
            "hgo": 0.15,
            "lco": 0.1,
            "kero": 0.12,
            "biodiesel": 0.03,
        },
        "key_metrics": {
            "density_15c": 840.0,
            "n_paraffin_c10_c15": 10.0,
            "n_paraffin_c16_c20": 9.0,
            "n_paraffin_c21_plus": 2.0,
            "aromatic_content": 24.0,
            "sulfur_ppm": 8.0,
            "cetane_index": 49.0,
            "wafi_type": "A",
            "wafi_ppm": 0.0,
        },
        "target_cfpp": -8.0,
        "season": "winter",
        "tank_history_flag": "clean",
        "priority": "balance",
    }


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "Blending Master API"


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_judge_returns_three_scenarios(client):
    r = client.post("/judge", json=_sample_payload())
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["decision"] in ("normal", "caution", "risk")
    assert isinstance(body["predicted_cfpp_baseline"], float)
    assert isinstance(body["confidence"], float)

    scenarios = body["scenarios"]
    assert len(scenarios) == 3
    labels = {s["label"] for s in scenarios}
    assert labels == {"min_cost", "balanced", "safe"}
    for s in scenarios:
        assert 0 <= s["wafi_ppm"] <= 600
        assert "rationale" in s

    assert isinstance(body["similar_cases"], list)


def test_judge_validation_error(client):
    bad = _sample_payload()
    bad["blend_components"]["lgo"] = -0.1
    r = client.post("/judge", json=bad)
    assert r.status_code == 422


def test_cases_list_and_detail(client):
    r = client.get("/cases")
    assert r.status_code == 200
    rows = r.json()
    assert any(row["case_id"] == "TEST-001" for row in rows)

    r2 = client.get("/cases/TEST-001")
    assert r2.status_code == 200
    assert r2.json()["case_id"] == "TEST-001"

    r3 = client.get("/cases/NONEXISTENT")
    assert r3.status_code == 404
