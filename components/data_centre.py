"""SMARTSCAN Data Intelligence Centre dashboard."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any

import streamlit as st

from data_manager import DataManager
from data_analytics import analyze_records, evaluate_model, trend_insights


def _csv_text(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    fields = list(dict.fromkeys(field for row in rows for field in row
                                if not str(field).startswith("_")))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fields})
    return output.getvalue()


def _metric(label: str, value: Any) -> None:
    st.metric(label, value)


def render_data_centre() -> None:
    st.markdown(
        '<div class="ss-anchor" id="data-centre">'
        '<div class="ss-section-head"><div>'
        '<div class="ss-h2" role="heading" aria-level="2">'
        'SMARTSCAN AI — DATA INTELLIGENCE CENTRE</div>'
        '<div class="ss-sub">Validated records, experiment storage and honest model evaluation</div>'
        '</div><span class="ss-chip-cyan">SQLite Persistent</span></div></div>',
        unsafe_allow_html=True,
    )

    manager = DataManager()
    experiments = manager.database.list_experiments()
    st.session_state.setdefault("data_centre_experiment", None)

    if experiments:
        ids = [item["Experiment_ID"] for item in experiments]
        selected = st.session_state.get("data_centre_experiment")
        if selected not in ids:
            selected = ids[0]
            st.session_state["data_centre_experiment"] = selected
        selected = st.selectbox(
            "Selected experiment",
            ids,
            index=ids.index(selected),
            format_func=lambda eid: next(
                (f'{item["Name"]} · {item["Experiment_ID"]}' for item in experiments
                 if item["Experiment_ID"] == eid),
                eid,
            ),
            key="data_centre_experiment",
        )
    else:
        st.info("No experiments are stored yet. Complete a simulation round or import a CSV.")
        selected = None

    overview_tab, feed_tab, quality_tab, analytics_tab, evaluation_tab, history_tab, import_tab = st.tabs([
        "Data Overview", "Live Feed", "Quality", "Analytics",
        "Model Evaluation", "History", "CSV Import",
    ])

    if selected:
        all_rows = manager.database.get_records(selected)
        valid_rows = [row for row in all_rows
                      if str(row.get("Processing_Status", "VALID")).upper() in ("VALID", "WARNING")]
        rejected_rows = [row for row in all_rows
                         if str(row.get("Processing_Status", "")).upper() == "REJECTED"]
        missing = sum(
            value is None or (isinstance(value, str) and not value.strip())
            for row in all_rows for value in row.values()
        )
        quality = round(100 * len(valid_rows) / len(all_rows), 2) if all_rows else 100.0
        duplicate_count = len(all_rows) - len({row["Record_ID"] for row in all_rows})
        last_updated = max(
            (str(row["Timestamp"]) for row in all_rows if row.get("Timestamp")),
            default="—",
        )

        with overview_tab:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Received Records", len(all_rows))
            c2.metric("Valid Records", len(valid_rows))
            c3.metric("Rejected Records", len(rejected_rows))
            c4, c5, c6 = st.columns(3)
            c4.metric("Data Quality", f"{quality:.1f}%")
            c5.metric("Stored Experiments", len(experiments))
            c6.metric("Last Updated", last_updated)
            st.caption(
                "Data quality = valid plus warning records divided by all received records "
                "(100 × (VALID + WARNING) / received). It is not prediction accuracy."
            )

        with feed_tab:
            st.markdown("**Latest received records**")
            if all_rows:
                display = [{
                    "Record ID": row["Record_ID"],
                    "Timestamp": row["Timestamp"],
                    "Experiment ID": row["Experiment_ID"],
                    "Data source": row["Source"],
                    "Round": row["Round"],
                    "Processing status": row["Processing_Status"],
                } for row in all_rows[:100]]
                st.dataframe(display, use_container_width=True, hide_index=True)
            else:
                st.info("No records have been received for this experiment.")

        with quality_tab:
            c1, c2, c3 = st.columns(3)
            c1.metric("Valid records percentage", f"{quality:.1f}%")
            c2.metric("Missing values", missing)
            c3.metric("Duplicate records", duplicate_count)
            c4, c5 = st.columns(2)
            c4.metric("Invalid records", len(rejected_rows))
            c5.metric("Validation status", "REJECTED" if rejected_rows else "WARNING" if not valid_rows else "VALID")
            trend = analyze_records(valid_rows)["time_trend"]
            if trend:
                st.line_chart(
                    [{"Date": item["date"], "Record count": item["record_count"]} for item in trend],
                    x="Date", y="Record count",
                )
            else:
                st.info("No data-quality trend is available yet.")
            st.download_button(
                "Download validation report",
                data=_csv_text([{
                    "Experiment_ID": selected,
                    "Status": row["Processing_Status"],
                    "Record_ID": row["Record_ID"],
                    "Source": row["Source"],
                } for row in all_rows]),
                file_name=f"validation_{selected}.csv",
                mime="text/csv",
            )
            st.download_button(
                "Download rejected records",
                data=_csv_text(rejected_rows),
                file_name=f"rejected_{selected}.csv",
                mime="text/csv",
                disabled=not rejected_rows,
            )

        with analytics_tab:
            if valid_rows:
                summary = analyze_records(valid_rows)
                st.markdown("**Statistical summaries**")
                st.dataframe([
                    {
                        "Field": field,
                        "Count": values["count"],
                        "Average": round(values["average"], 4),
                        "Minimum": round(values["min"], 4),
                        "Maximum": round(values["max"], 4),
                        "Standard deviation": round(values["stddev"], 4),
                    }
                    for field, values in summary["numeric"].items()
                ], use_container_width=True, hide_index=True)

                if summary["time_trend"]:
                    st.markdown("**Record count over time**")
                    st.line_chart(
                        [{"Date": item["date"], "Records": item["record_count"]}
                         for item in summary["time_trend"]],
                        x="Date", y="Records",
                    )
                if summary["sector_distribution"]:
                    st.markdown("**Data distribution: selected sector**")
                    st.bar_chart(
                        [{"Sector": key, "Records": value}
                         for key, value in summary["sector_distribution"].items()],
                        x="Sector", y="Records",
                    )
                st.markdown("**Labelled synthetic metrics**")
                evaluation = summary["evaluation"]
                if evaluation["labelled"]:
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Accuracy", f"{evaluation['accuracy'] * 100:.1f}%" if evaluation["accuracy"] is not None else "N/A")
                    m2.metric("Precision", f"{evaluation['precision'] * 100:.1f}%" if evaluation["precision"] is not None else "N/A")
                    m3.metric("Recall", f"{evaluation['recall'] * 100:.1f}%" if evaluation["recall"] is not None else "N/A")
                    m4.metric("F1", f"{evaluation['f1'] * 100:.1f}%" if evaluation["f1"] is not None else "N/A")
                else:
                    st.info("Ground-truth labels are unavailable; accuracy is N/A.")
            else:
                st.info("No valid records are available for analytics.")

        with evaluation_tab:
            evaluation = evaluate_model(valid_rows)
            if evaluation["status"] == "INSUFFICIENT DATA":
                st.warning("INSUFFICIENT DATA")
                st.caption(f"Labelled records: {evaluation['sample_size']}. At least 4 are required for this evaluation.")
            else:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Test accuracy", f"{evaluation['accuracy'] * 100:.1f}%"
                          if evaluation["accuracy"] is not None else "N/A")
                c2.metric("Precision", f"{evaluation['precision'] * 100:.1f}%"
                          if evaluation["precision"] is not None else "N/A")
                c3.metric("Recall", f"{evaluation['recall'] * 100:.1f}%"
                          if evaluation["recall"] is not None else "N/A")
                c4.metric("F1-score", f"{evaluation['f1'] * 100:.1f}%"
                          if evaluation["f1"] is not None else "N/A")
                st.caption(
                    f"Reproducible seed {evaluation['seed']}; "
                    f"{evaluation['test_sample_size']} unseen test records "
                    f"from {evaluation['sample_size']} labelled records."
                )
                matrix = evaluation["confusion_matrix"]
                st.dataframe([{
                    "True positive": matrix["TP"], "True negative": matrix["TN"],
                    "False positive": matrix["FP"], "False negative": matrix["FN"],
                }], use_container_width=True, hide_index=True)
                st.write("Class distribution:", evaluation["class_distribution"])
                st.metric("Majority-class baseline",
                          f"{evaluation['baseline'] * 100:.1f}%"
                          if evaluation["baseline"] is not None else "N/A")
                if not evaluation["meaningful"]:
                    st.warning("The test split is too small or has one class only for meaningful evaluation.")

            st.markdown("**Transparent insights**")
            for insight in trend_insights(valid_rows, missing, duplicate_count):
                st.write("• " + insight)

        with history_tab:
            date_from = st.text_input("Start date (YYYY-MM-DD)", key="dc_date_from")
            date_to = st.text_input("End date (YYYY-MM-DD)", key="dc_date_to")
            source_options = ["All"] + sorted({row["Source"] for row in all_rows})
            source = st.selectbox("Data source", source_options, key="dc_source_filter")
            filtered = manager.database.get_records(
                selected,
                date_from if date_from else "",
                date_to if date_to else "",
                "" if source == "All" else source,
            )
            st.dataframe(filtered, use_container_width=True, hide_index=True)
            st.download_button(
                "Export selected experiment",
                data=_csv_text(filtered),
                file_name=f"experiment_{selected}.csv",
                mime="text/csv",
                disabled=not filtered,
            )

            compare_ids = st.multiselect(
                "Compare experiments",
                [item["Experiment_ID"] for item in experiments],
                max_selections=2,
                default=[],
            )
            if len(compare_ids) == 2:
                comparison = []
                for eid in compare_ids:
                    rows = manager.database.get_records(eid)
                    summary = analyze_records([
                        row for row in rows
                        if str(row.get("Processing_Status", "")).upper() in ("VALID", "WARNING")
                    ])
                    comparison.append({
                        "Experiment": eid,
                        "Records": summary["total_records"],
                        "Average reward": (
                            summary["numeric"].get("Cumulative_Reward", {}).get("average")
                            if summary["numeric"].get("Cumulative_Reward") else None
                        ),
                        "Missing values": sum(
                            value is None or (isinstance(value, str) and not value.strip())
                            for row in rows for value in row.values()
                        ),
                    })
                st.dataframe(comparison, use_container_width=True, hide_index=True)

            st.markdown("**Delete experiment**")
            confirm = st.checkbox("I confirm permanent deletion")
            if st.button("Delete selected experiment", disabled=not confirm, type="secondary"):
                manager.database.delete_experiment(selected)
                st.session_state["data_centre_experiment"] = None
                st.rerun()

    with import_tab:
        uploaded = st.file_uploader("Upload educational simulation CSV",
                                    type=["csv"], key="dc_csv_upload")
        if uploaded is not None:
            try:
                csv_text = uploaded.getvalue().decode("utf-8-sig")
            except UnicodeDecodeError:
                st.error("The uploaded file must be UTF-8 encoded.")
            else:
                import io as _io
                import csv as _csv
                reader = _csv.DictReader(_io.StringIO(csv_text))
                preview = list(reader)
                if not preview:
                    st.warning("The CSV is empty.")
                else:
                    st.markdown("**Preview (first 20 rows)**")
                    st.dataframe(preview[:20], use_container_width=True, hide_index=True)
                    if st.button("Validate and import valid records", type="primary"):
                        with st.spinner("Validating and storing CSV records…"):
                            result = manager.import_csv(
                                csv_text,
                                experiment_name=uploaded.name,
                            )
                        st.success(
                            f"Received {result['total_received']}: "
                            f"{result['valid']} valid, {result['warning']} warning, "
                            f"{result['rejected']} rejected."
                        )
                        st.write("Missing values:", result["missing_values"])
                        st.write("Duplicate records:", result["duplicate_records"])
                        st.caption(result["method"])
                        if result["rejected_records"]:
                            st.download_button(
                                "Download rejected records",
                                data=_csv_text(result["rejected_records"]),
                                file_name="rejected_csv_records.csv",
                                mime="text/csv",
                            )
                        st.download_button(
                            "Download validation report",
                            data=_csv_text(result["report"]),
                            file_name="csv_validation_report.csv",
                            mime="text/csv",
                        )
