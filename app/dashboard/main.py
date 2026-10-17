"""Launch with python -m streamlit run app/dashboard/main.py."""

import os

import httpx
import streamlit as st

from app.dashboard.client import PRESETS, build_request, validate_api_url
from app.dashboard.metrics import render_metrics
from app.models.simulation import MetricsResponse, RunResponse

st.set_page_config(page_title="FabFlow", page_icon="🏭", layout="wide")
st.title("FabFlow")
st.caption("Synthetic semiconductor manufacturing simulator")

with st.sidebar:
    st.header("API connection")
    api_url = (
        st.text_input(
            "API base URL",
            value=os.environ.get("FABFLOW_API_URL", "http://127.0.0.1:8000"),
            help="Address reachable from the dashboard server.",
        )
        .strip()
        .rstrip("/")
    )
    check_connection = st.button("Check connection", type="primary")

st.subheader("Service status")
if check_connection:
    try:
        validate_api_url(api_url)
        with st.spinner("Checking API readiness…"):
            response = httpx.get(f"{api_url}/health/ready", timeout=5.0)
        if response.status_code == 503:
            st.warning("The API is reachable but is not ready. Try again shortly.")
        else:
            response.raise_for_status()
            if response.json() != {"status": "ready"}:
                raise ValueError("The server did not return a FabFlow readiness response.")
            st.success("API is ready to accept simulations.")
    except httpx.TimeoutException:
        st.error("The API did not respond within 5 seconds. Check the address and try again.")
    except httpx.HTTPStatusError as exc:
        st.error(f"Readiness check failed (HTTP {exc.response.status_code}).")
    except (httpx.RequestError, httpx.InvalidURL):
        st.error("Cannot connect to the API. Check its address and confirm it is running.")
    except ValueError as exc:
        st.error(str(exc))
else:
    st.info("Set the API address and select Check connection to verify service readiness.")

st.subheader("Run a simulation")
st.caption(
    "Both presets contain 20 lots and three processing stages. The baseline has no transport "
    "delay; AMHS bottleneck uses one vehicle with five-minute transfers. "
    "These fixed-time presets may produce identical results across dispatch policies."
)
with st.form("simulation"):
    preset = st.selectbox("Scenario", PRESETS)
    policy = st.selectbox("Dispatch policy", ("FIFO", "SPT", "CR"))
    threshold = st.number_input(
        "Normal lot aging threshold (minutes)",
        min_value=0.1,
        value=60.0,
        step=1.0,
        help="Normal lots waiting this long receive dispatch precedence at each station.",
    )
    submitted = st.form_submit_button("Run simulation", type="primary")

if submitted:
    try:
        validate_api_url(api_url)
        payload = build_request(preset, policy, threshold)
        with st.spinner("Running simulation…"):
            response = httpx.post(
                f"{api_url}/api/v1/runs", json=payload.model_dump(mode="json"), timeout=60.0
            )
        response.raise_for_status()
        summary = RunResponse.model_validate(response.json())
        st.session_state["last_run"] = {"api_url": api_url, "summary": summary.model_dump()}
    except httpx.TimeoutException:
        st.error(
            "The simulation request timed out. It may still finish on the server. "
            "No automatic retry was sent; submitting again creates a new run."
        )
    except httpx.HTTPStatusError as exc:
        st.error(f"Simulation request failed (HTTP {exc.response.status_code}).")
        if exc.response.status_code == 422:
            try:
                st.json(exc.response.json())
            except ValueError:
                st.caption("The API did not return validation details as JSON.")
    except (httpx.RequestError, httpx.InvalidURL):
        st.error("Cannot connect to the API. Check its address and confirm it is running.")
    except ValueError:
        st.error(
            "Invalid API address, simulation settings, or run response. Check the API and inputs."
        )

last_run = st.session_state.get("last_run")
if last_run and last_run["api_url"] == api_url:
    summary = last_run["summary"]
    st.subheader("Last completed run")
    st.caption("Saved result from the last successful submission; settings are recorded below.")
    st.code(summary["run_id"], language=None)
    st.write(
        f"Scenario: {summary['scenario_id']} · Policy: {summary['policy']} · "
        f"Aging threshold: {summary['normal_wait_threshold']:g} min · Seed: {summary['seed']}"
    )
    lots, finish = st.columns(2)
    lots.metric("Completed lots", summary["completed_lots"])
    finish.metric("Simulation finish time (minutes)", f"{summary['finished_at']:g}")

    if st.button("Load KPIs" if "metrics" not in last_run else "Refresh KPIs"):
        try:
            with st.spinner("Loading run KPIs…"):
                response = httpx.get(
                    f"{api_url}/api/v1/runs/{summary['run_id']}/metrics", timeout=10.0
                )
            response.raise_for_status()
            metrics = MetricsResponse.model_validate(response.json())
            if (
                metrics.completed_lots != summary["completed_lots"]
                or metrics.observation_minutes != summary["finished_at"]
            ):
                raise ValueError("Metrics do not match the completed run.")
            last_run["metrics"] = metrics.model_dump()
            st.rerun()
        except httpx.TimeoutException:
            st.error("KPI request timed out. Select Load/Refresh KPIs to try again.")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                st.error("Run not found. API results are cleared when the server restarts.")
            else:
                st.error(f"KPI request failed (HTTP {exc.response.status_code}).")
        except (httpx.RequestError, httpx.InvalidURL):
            st.error("Cannot connect to the API to load KPIs.")
        except ValueError:
            st.error("The API returned invalid KPIs or metrics that do not match this run.")

    if "metrics" in last_run:
        st.caption("Saved KPIs for the run above. Refresh KPIs queries the API again.")
        render_metrics(MetricsResponse.model_validate(last_run["metrics"]))
