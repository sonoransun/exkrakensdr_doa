import time

import dash_html_components as html
import numpy as np
import plotly.graph_objects as go

VFO_COLORS = [
    "#636EFA",
    "#EF553B",
    "#00CC96",
    "#AB63FA",
    "#FFA15A",
    "#19D3F3",
    "#FF6692",
    "#B6E880",
    "#FF97FF",
    "#FECB52",
    "#1F77B4",
    "#FF7F0E",
    "#2CA02C",
    "#D62728",
    "#9467BD",
    "#8C564B",
]

MAX_VFOS = 16


def init_multi_doa_fig(web_interface, fig_layout):
    """Create the multi-VFO polar DoA compass figure with pre-allocated traces."""
    multi_doa_fig = go.Figure(layout=fig_layout)

    for i in range(MAX_VFOS):
        color = VFO_COLORS[i]

        # Even index: filled area trace for DoA result curve
        multi_doa_fig.add_trace(
            go.Scatterpolargl(
                theta=[],
                r=[],
                name=f"VFO-{i}",
                fill="toself",
                fillcolor=color,
                line=dict(color=color),
                opacity=0.4,
                visible=False,
            )
        )

        # Odd index: line+markers trace for peak bearing indicator
        multi_doa_fig.add_trace(
            go.Scatterpolargl(
                theta=[],
                r=[],
                name=f"VFO-{i} Peak",
                mode="lines+markers",
                line=dict(color=color, width=3),
                marker=dict(color=color),
                visible=False,
                showlegend=False,
            )
        )

    multi_doa_fig.update_layout(
        polar=dict(
            angularaxis=dict(rotation=90, direction="clockwise"),
            radialaxis=dict(showticklabels=False),
        ),
        legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
        margin=go.layout.Margin(t=0, b=50, l=0, r=0),
    )

    return multi_doa_fig


def init_multi_doa_history_fig(fig_layout):
    """Create the multi-VFO bearing vs time history chart with pre-allocated traces."""
    multi_doa_history_fig = go.Figure(layout=fig_layout)

    for i in range(MAX_VFOS):
        color = VFO_COLORS[i]

        multi_doa_history_fig.add_trace(
            go.Scattergl(
                x=[],
                y=[],
                name=f"VFO-{i}",
                mode="lines+markers",
                line=dict(color=color),
                marker=dict(color=color, size=4),
                visible=False,
            )
        )

    multi_doa_history_fig.update_xaxes(title_text="Time (s ago)")
    multi_doa_history_fig.update_yaxes(title_text="Bearing (deg)", range=[0, 360])
    multi_doa_history_fig.update_layout(
        margin=go.layout.Margin(t=10, b=30, l=50, r=10),
    )

    return multi_doa_history_fig


def plot_multi_doa(app, web_interface, multi_doa_fig, multi_doa_history_fig):
    """Update all multi-VFO DoA visualizations and push to connected clients."""
    results = web_interface.multi_doa_all_results
    if not results or "results" not in results:
        return

    compass_offset = web_interface.compass_offset
    max_vfos = MAX_VFOS

    # -----------------------------------------------------------------------
    # Update compass polar traces
    # -----------------------------------------------------------------------
    for i in range(max_vfos):
        trace_curve = i * 2
        trace_peak = i * 2 + 1

        if i < len(results.get("results", [])) and i < len(results.get("squelch_active", [])) and results["squelch_active"][i]:
            try:
                thetas = results.get("thetas")
                if thetas is None or len(thetas) == 0:
                    multi_doa_fig.data[trace_curve]["visible"] = False
                    multi_doa_fig.data[trace_peak]["visible"] = False
                    continue
                result = results["results"][i]
                angle = results["angles"][i]

                # Close the polar loop by appending the first element
                display_thetas = (360 - np.append(thetas, thetas[0]) + compass_offset) % 360
                display_result = np.append(result, result[0])
                display_angle = (360 - angle + compass_offset) % 360

                # Update curve trace
                multi_doa_fig.data[trace_curve]["theta"] = display_thetas
                multi_doa_fig.data[trace_curve]["r"] = display_result
                multi_doa_fig.data[trace_curve]["visible"] = True

                # Update peak bearing trace
                peak_r = np.max(display_result) if display_result.size > 0 else 0
                multi_doa_fig.data[trace_peak]["theta"] = [display_angle, display_angle]
                multi_doa_fig.data[trace_peak]["r"] = [0, peak_r]
                multi_doa_fig.data[trace_peak]["visible"] = True
            except (KeyError, IndexError):
                multi_doa_fig.data[trace_curve]["visible"] = False
                multi_doa_fig.data[trace_peak]["visible"] = False
        else:
            multi_doa_fig.data[trace_curve]["visible"] = False
            multi_doa_fig.data[trace_peak]["visible"] = False

    # -----------------------------------------------------------------------
    # Build summary table HTML
    # -----------------------------------------------------------------------
    table_children = []
    for i in range(max_vfos):
        if i >= len(results["results"]):
            break

        freq_mhz = (results["freqs"][i] / 1e6) if i < len(results["freqs"]) else 0
        angle = results["angles"][i] if i < len(results["angles"]) else 0
        display_angle = (360 - angle + compass_offset) % 360
        power = results["powers"][i] if i < len(results["powers"]) else 0
        confidence = results["confidences"][i] if i < len(results["confidences"]) else 0
        is_active = results["squelch_active"][i] if i < len(results["squelch_active"]) else False

        if is_active:
            status_cell = html.Td("Active", style={"color": "green"})
        else:
            status_cell = html.Td("Below", style={"color": "red"})

        row = html.Tr(
            [
                html.Td(f"{i}"),
                html.Td(f"{freq_mhz:.3f}"),
                html.Td(f"{display_angle:.1f}"),
                html.Td(f"{power:.1f}"),
                html.Td(f"{confidence:.1f}"),
                status_cell,
            ]
        )
        table_children.append(row)

    # -----------------------------------------------------------------------
    # Update history chart
    # -----------------------------------------------------------------------
    history = web_interface.multi_doa_history
    if history:
        now = history[-1].get("timestamp", time.time())
        for i in range(max_vfos):
            x_vals = []
            y_vals = []
            for entry in history:
                ts = entry.get("timestamp", now)
                seconds_ago = now - ts
                angles = entry.get("angles", [])
                active = entry.get("squelch_active", [])
                if i < len(angles) and i < len(active) and active[i]:
                    bearing = (360 - angles[i] + compass_offset) % 360
                    x_vals.append(seconds_ago)
                    y_vals.append(bearing)

            if x_vals:
                multi_doa_history_fig.data[i]["x"] = x_vals
                multi_doa_history_fig.data[i]["y"] = y_vals
                multi_doa_history_fig.data[i]["visible"] = True
            else:
                multi_doa_history_fig.data[i]["visible"] = False

    # -----------------------------------------------------------------------
    # Push all updates to connected clients
    # -----------------------------------------------------------------------
    app.push_mods(
        {
            "multi-doa-compass": {"figure": multi_doa_fig},
            "multi-doa-table-body": {"children": table_children},
            "multi-doa-history": {"figure": multi_doa_history_fig},
        }
    )
