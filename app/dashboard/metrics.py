"""Display API KPIs without recalculating simulation results."""

import streamlit as st

from app.models.simulation import MetricsResponse


def render_metrics(metrics: MetricsResponse) -> None:
    st.subheader("Manufacturing KPIs")
    st.caption(
        f"Observation window: minute 0 to {metrics.observation_minutes:g}. "
        "Times are minutes; throughput is lots/hour; rates are percentages."
    )
    cycle, p95, throughput, otd = st.columns(4)
    cycle.metric("Average cycle time (min)", f"{metrics.average_cycle_time:.2f}")
    p95.metric("P95 cycle time (min)", f"{metrics.p95_cycle_time:.2f}")
    throughput.metric("Throughput (lots/hour)", f"{metrics.throughput_per_hour:.2f}")
    otd.metric("On-time delivery", f"{metrics.on_time_delivery_rate:.1%}")
    st.dataframe(
        [
            {"Metric": "Average WIP", "Value": metrics.average_wip, "Unit": "lots"},
            {"Metric": "Average queue depth", "Value": metrics.average_queue_depth, "Unit": "lots"},
            {"Metric": "Peak queue depth", "Value": metrics.max_queue_depth, "Unit": "lots"},
            {
                "Metric": "Average queue wait per lot",
                "Value": metrics.average_waiting_time,
                "Unit": "min",
            },
            {"Metric": "Average tardiness", "Value": metrics.average_tardiness, "Unit": "min"},
        ],
        hide_index=True,
    )
    st.subheader("Equipment")
    st.caption("Utilization excludes downtime; availability measures time without machine outages.")
    machines = [
        {
            "Machine": machine.machine_id,
            "Utilization (%)": machine.utilization * 100,
            "Availability (%)": machine.availability * 100,
            "Downtime (min)": machine.downtime,
        }
        for machine in metrics.machines
    ]
    if machines:
        utilization, availability = st.columns(2)
        with utilization:
            st.bar_chart(machines, x="Machine", y="Utilization (%)", y_label="Utilization (%)")
        with availability:
            st.bar_chart(machines, x="Machine", y="Availability (%)", y_label="Availability (%)")
        st.dataframe(machines, hide_index=True)
    else:
        st.info("No equipment metrics are available for this run.")

    st.subheader("AMHS transport")
    if metrics.transport_job_count == 0:
        st.info("This run contains no transport jobs; transport charts are not applicable.")
        return
    jobs, vehicles = st.columns(2)
    jobs.metric("Transport jobs", metrics.transport_job_count)
    vehicles.metric("Vehicle utilization", f"{metrics.vehicle_utilization:.1%}")
    st.caption("Transport times below are averages per transport job.")
    transport = [
        {
            "Component": "Waiting for vehicle",
            "Minutes per job": metrics.average_transport_waiting_time,
        },
        {"Component": "Travel", "Minutes per job": metrics.average_transport_time},
    ]
    st.bar_chart(transport, x="Component", y="Minutes per job", y_label="Minutes per job")
    st.dataframe(transport, hide_index=True)
