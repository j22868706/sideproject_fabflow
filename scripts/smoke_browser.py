"""Verify the running Compose dashboard through a real headless browser."""

import argparse
import json
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import Page, expect, sync_playwright


def metric(page: Page, label: str, value: str) -> None:
    card = page.get_by_test_id("stMetric").filter(has=page.get_by_text(label, exact=True))
    expect(card.get_by_test_id("stMetricValue")).to_have_text(value)


def select(page: Page, label: str, value: str) -> None:
    control = page.get_by_role("combobox", name=label, exact=True)
    if control.input_value() == value:
        return
    control.fill(value)
    page.get_by_role("option", name=value, exact=True).click()
    expect(control).to_have_value(value)


def verify(page: Page, api_url: str, output: Path) -> None:
    expect(page.get_by_role("heading", name="FabFlow", exact=True)).to_be_visible()
    page.get_by_role("button", name="Check connection", exact=True).click()
    expect(page.get_by_text("API is ready to accept simulations.", exact=True)).to_be_visible()

    previous_id = None
    for preset, scenario_id, finish, cycle, charts in (
        ("Three-stage baseline", "three-stage-baseline", "175", "70.50", 2),
        ("AMHS bottleneck", "amhs-bottleneck", "203", "142.75", 3),
    ):
        for policy in ("FIFO", "SPT", "CR"):
            select(page, "Scenario", preset)
            select(page, "Dispatch policy", policy)
            page.get_by_role("spinbutton", name="Normal lot aging threshold (minutes)").fill("30")
            page.get_by_role("button", name="Run simulation", exact=True).click()
            expect(page.get_by_role("button", name="Load KPIs", exact=True)).to_be_visible()
            run_code = page.get_by_test_id("stCode").locator("code")
            expect(run_code).not_to_have_text(previous_id or "")
            run_id = run_code.inner_text().strip()
            with urlopen(f"{api_url}/api/v1/runs/{run_id}", timeout=10) as response:
                summary = json.load(response)
            assert summary["policy"] == policy
            assert summary["scenario_id"] == scenario_id
            assert summary["normal_wait_threshold"] == 30
            metric(page, "Completed lots", "20")
            metric(page, "Simulation finish time (minutes)", finish)
            page.get_by_role("button", name="Load KPIs", exact=True).click()
            metric(page, "Average cycle time (min)", cycle)
            metric(page, "Throughput (lots/hour)", "6.86" if charts == 2 else "5.91")
            chart = page.get_by_test_id("stVegaLiteChart")
            expect(chart).to_have_count(charts)
            for index in range(charts):
                expect(chart.nth(index).locator("canvas, svg").first).to_be_visible()
            if charts == 3:
                metric(page, "Transport jobs", "40")
            else:
                expect(
                    page.get_by_text(
                        "This run contains no transport jobs; transport charts are not applicable.",
                        exact=True,
                    )
                ).to_be_visible()
            if policy == "FIFO":
                page.get_by_role("heading", name="Manufacturing KPIs", exact=True).evaluate(
                    "element => element.scrollIntoView({block: 'start'})"
                )
                page.screenshot(path=str(output / f"{scenario_id}-kpis.png"))
                chart.last.screenshot(path=str(output / f"{scenario_id}-chart.png"))
            page.get_by_role("button", name="Refresh KPIs", exact=True).click()
            metric(page, "Average cycle time (min)", cycle)
            expect(run_code).to_have_text(run_id)
            expect(page.get_by_test_id("stApp")).to_have_attribute(
                "data-test-script-state", "notRunning"
            )
            assert page.get_by_test_id("stException").count() == 0
            previous_id = run_id
            print(f"PASS: {preset}, {policy}, aging=30, run={run_id}", flush=True)

    # Exercise a real widget rerun and recover from an invalid server address.
    address = page.get_by_role("textbox", name="API base URL", exact=True)
    original_url = address.input_value()
    address.fill("invalid-url")
    address.press("Enter")
    expect(page.get_by_role("heading", name="Last completed run", exact=True)).to_have_count(0)
    page.get_by_role("button", name="Check connection", exact=True).click()
    expect(
        page.get_by_text("Enter an HTTP or HTTPS base URL without a query or fragment.", exact=True)
    ).to_be_visible()
    address.fill(original_url)
    address.press("Enter")
    expect(page.get_by_test_id("stCode").locator("code")).to_have_text(previous_id)
    metric(page, "Average cycle time (min)", "142.75")
    print(
        "PASS: KPI refresh, saved results, address isolation, and validation recovery", flush=True
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--channel", default=None, help="Use chrome for an installed Google Chrome")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/browser"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.channel)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        context.tracing.start(screenshots=True, snapshots=True)
        page = context.new_page()
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.set_default_timeout(30_000)
        expect.set_options(timeout=30_000)
        try:
            page.goto(args.url)
            verify(page, args.api_url.rstrip("/"), args.output_dir)
            assert not page_errors, page_errors
            print(f"PASS: browser acceptance; browser={browser.version}", flush=True)
        except Exception:
            page.screenshot(path=str(args.output_dir / "failure.png"))
            raise
        finally:
            context.tracing.stop(path=str(args.output_dir / "trace.zip"))
            browser.close()


if __name__ == "__main__":
    main()
