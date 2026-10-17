"""Exercise the dashboard's HTTP readiness states through Streamlit widgets."""

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.dashboard.client import PRESETS, build_request
from app.main import create_app

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

DASHBOARD = Path(__file__).resolve().parents[1] / "app" / "dashboard" / "main.py"


def test_dashboard_waits_for_connection_check(monkeypatch):
    monkeypatch.setenv("FABFLOW_API_URL", "http://api:8000")
    with patch("httpx.get") as get:
        page = AppTest.from_file(str(DASHBOARD)).run()
    assert not page.exception
    assert page.text_input[0].value == "http://api:8000"
    assert page.info
    get.assert_not_called()


@pytest.mark.parametrize(("preset", "finish"), [(PRESETS[0], 175), (PRESETS[1], 203)])
@pytest.mark.parametrize("policy", ["FIFO", "SPT", "CR"])
def test_dashboard_submits_to_api_and_retains_summary(preset, finish, policy):
    page = AppTest.from_file(str(DASHBOARD)).run()
    page.selectbox[0].select(preset)
    page.selectbox[1].select(policy)
    page.number_input[0].set_value(30.0)
    with TestClient(create_app()) as client:
        with patch(
            "httpx.post", side_effect=lambda url, **kw: client.post(url, json=kw["json"])
        ) as post:
            next(button for button in page.button if button.label == "Run simulation").click().run()
        assert not page.exception
        post.assert_called_once()
        submitted = post.call_args.kwargs["json"]
        assert submitted["policy"] == policy
        assert submitted["normal_wait_threshold"] == 30
        result = page.session_state["last_run"]["summary"]
        assert result["completed_lots"] == 20
        assert result["finished_at"] == finish
        assert result["policy"] == policy
        assert result["normal_wait_threshold"] == 30
        assert client.get(f"/api/v1/runs/{result['run_id']}").json() == result
    assert [metric.value for metric in page.metric] == ["20", str(finish)]
    with patch("httpx.post") as post:
        page.run()
        assert page.code[0].value == result["run_id"]
        page.text_input[0].set_value("http://another-api:8000").run()
        assert not page.metric
        post.assert_not_called()


@pytest.mark.parametrize(
    ("response", "error", "message"),
    [
        (None, httpx.ReadTimeout("slow"), "may still finish"),
        (None, httpx.ConnectError("offline"), "Cannot connect"),
        (422, None, "HTTP 422"),
        (500, None, "HTTP 500"),
        (201, None, "run response"),
    ],
)
def test_dashboard_failed_submission_does_not_publish_result(response, error, message):
    page = AppTest.from_file(str(DASHBOARD)).run()
    returned = (
        httpx.Response(
            response,
            json={"detail": "invalid"},
            request=httpx.Request("POST", "http://api:8000/api/v1/runs"),
        )
        if response
        else None
    )
    with patch("httpx.post", return_value=returned, side_effect=error) as post:
        next(button for button in page.button if button.label == "Run simulation").click().run()
        assert post.call_count == 1
    assert not page.exception
    assert message in page.error[0].value
    assert not page.metric


def test_dashboard_presets_match_documented_requests():
    import json

    examples = DASHBOARD.parents[2] / "docs" / "examples"
    for preset, name in zip(PRESETS, ["baseline", "amhs_bottleneck"], strict=True):
        expected = json.loads((examples / f"{name}.json").read_text())
        assert build_request(preset, "FIFO", 60).model_dump(mode="json") == expected


def test_dashboard_keeps_previous_success_after_failed_request():
    page = AppTest.from_file(str(DASHBOARD)).run()
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/runs", json=build_request(PRESETS[0], "FIFO", 60).model_dump(mode="json")
        )
    with patch("httpx.post", return_value=response):
        next(button for button in page.button if button.label == "Run simulation").click().run()
    run_id = page.code[0].value
    with patch("httpx.post", side_effect=httpx.ConnectError("offline")):
        next(button for button in page.button if button.label == "Run simulation").click().run()
    assert not page.exception
    assert page.error
    assert page.code[0].value == run_id


@pytest.mark.parametrize(
    ("status", "body", "element", "message"),
    [
        (200, {"status": "ready"}, "success", "API is ready"),
        (503, {"detail": "Service not ready"}, "warning", "not ready"),
        (500, {"detail": "Internal server error"}, "error", "HTTP 500"),
        (200, {"status": "alive"}, "error", "readiness response"),
    ],
)
def test_dashboard_readiness_responses(status, body, element, message):
    response = httpx.Response(
        status, json=body, request=httpx.Request("GET", "http://api:8000/health/ready")
    )
    page = AppTest.from_file(str(DASHBOARD)).run()
    page.text_input[0].set_value("http://api:8000/")
    with patch("httpx.get", return_value=response) as get:
        next(button for button in page.button if button.label == "Check connection").click().run()
    assert not page.exception
    assert message in getattr(page, element)[0].value
    get.assert_called_once_with("http://api:8000/health/ready", timeout=5.0)


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (httpx.ConnectError("offline"), "Cannot connect"),
        (httpx.ReadTimeout("slow"), "within 5 seconds"),
    ],
)
def test_dashboard_connection_errors(error, message):
    page = AppTest.from_file(str(DASHBOARD)).run()
    with patch("httpx.get", side_effect=error):
        next(button for button in page.button if button.label == "Check connection").click().run()
    assert not page.exception
    assert message in page.error[0].value


def test_dashboard_rejects_invalid_url():
    page = AppTest.from_file(str(DASHBOARD)).run()
    page.text_input[0].set_value("not-a-url")
    with patch("httpx.get") as get:
        next(button for button in page.button if button.label == "Check connection").click().run()
    assert not page.exception
    assert "HTTP or HTTPS" in page.error[0].value
    get.assert_not_called()


@pytest.mark.parametrize(
    ("preset", "cycle", "finish", "jobs"),
    [(PRESETS[0], "70.50", 175, 0), (PRESETS[1], "142.75", 203, 40)],
)
def test_dashboard_loads_kpis_from_api_and_caches_them(preset, cycle, finish, jobs):
    with TestClient(create_app()) as client:
        created = client.post(
            "/api/v1/runs", json=build_request(preset, "FIFO", 60).model_dump(mode="json")
        ).json()
        expected = client.get(f"/api/v1/runs/{created['run_id']}/metrics").json()
        page = AppTest.from_file(str(DASHBOARD), default_timeout=30)
        page.session_state["last_run"] = {
            "api_url": "http://127.0.0.1:8000",
            "summary": created,
        }
        with patch("httpx.get", side_effect=lambda url, **kw: client.get(url)) as get:
            page.run()
            get.assert_not_called()
            next(button for button in page.button if button.label == "Load KPIs").click().run()
        assert not page.exception
        get.assert_called_once_with(
            f"http://127.0.0.1:8000/api/v1/runs/{created['run_id']}/metrics", timeout=10.0
        )
        values = {metric.label: metric.value for metric in page.metric}
        assert values["Average cycle time (min)"] == cycle
        assert values["Throughput (lots/hour)"] == f"{20 * 60 / finish:.2f}"
        assert values["On-time delivery"] == f"{expected['on_time_delivery_rate']:.1%}"
        assert page.session_state["last_run"]["metrics"] == expected
        assert any(button.label == "Refresh KPIs" for button in page.button)
        assert not any(button.label == "Load KPIs" for button in page.button)
        equipment = page.dataframe[1].value
        assert equipment["Machine"].tolist() == [m["machine_id"] for m in expected["machines"]]
        assert equipment["Utilization (%)"].tolist() == pytest.approx(
            [m["utilization"] * 100 for m in expected["machines"]]
        )
        if jobs:
            assert values["Transport jobs"] == "40"
            assert page.dataframe[2].value["Minutes per job"].tolist() == pytest.approx(
                [53.375, 5.0]
            )
        else:
            assert "Transport jobs" not in values
            assert any("no transport jobs" in info.value for info in page.info)
        assert len(page.get("vega_lite_chart")) == (3 if jobs else 2)
        with patch("httpx.get") as get:
            page.run()
            assert not page.exception
            get.assert_not_called()
        with patch("httpx.get", side_effect=httpx.ReadTimeout("slow")):
            next(button for button in page.button if button.label == "Refresh KPIs").click().run()
        assert not page.exception
        assert page.error
        assert page.session_state["last_run"]["metrics"] == expected
        with patch(
            "httpx.post",
            return_value=httpx.Response(
                201, json=created, request=httpx.Request("POST", "http://api/runs")
            ),
        ):
            next(button for button in page.button if button.label == "Run simulation").click().run()
        assert "metrics" not in page.session_state["last_run"]
        assert len(page.metric) == 2


@pytest.mark.parametrize(
    ("status", "body", "error", "message"),
    [
        (404, {}, None, "Run not found"),
        (503, {}, None, "HTTP 503"),
        (200, {}, None, "invalid KPIs"),
        (200, {"mismatched": True}, None, "do not match"),
        (200, {}, httpx.ConnectError("offline"), "Cannot connect"),
        (200, {}, httpx.ReadTimeout("slow"), "timed out"),
    ],
)
def test_dashboard_kpi_failures_preserve_summary(status, body, error, message):
    with TestClient(create_app()) as client:
        summary = client.post(
            "/api/v1/runs", json=build_request(PRESETS[0], "FIFO", 60).model_dump(mode="json")
        ).json()
        if body.get("mismatched"):
            body = client.get(f"/api/v1/runs/{summary['run_id']}/metrics").json()
            body["completed_lots"] = 999
    page = AppTest.from_file(str(DASHBOARD))
    page.session_state["last_run"] = {"api_url": "http://127.0.0.1:8000", "summary": summary}
    page.run()
    response = httpx.Response(status, json=body, request=httpx.Request("GET", "http://api/metrics"))
    with patch("httpx.get", return_value=response, side_effect=error):
        next(button for button in page.button if button.label == "Load KPIs").click().run()
    assert not page.exception
    assert message in page.error[0].value
    assert page.code[0].value == summary["run_id"]
    assert "metrics" not in page.session_state["last_run"]
