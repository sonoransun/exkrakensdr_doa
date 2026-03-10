import dash_core_components as dcc
import dash_html_components as html

# isort: off
from maindash import multi_doa_fig, multi_doa_history_fig

# isort: on

layout = html.Div(
    [
        html.Div(
            [
                html.Div(
                    [
                        dcc.Graph(id="multi-doa-compass", figure=multi_doa_fig, style={"height": "100%"}),
                    ],
                    style={"width": "60%"},
                ),
                html.Div(
                    [
                        html.H3(
                            "Active VFO Summary",
                            style={"color": "white", "textAlign": "center"},
                        ),
                        html.Table(
                            [
                                html.Thead(
                                    html.Tr(
                                        [
                                            html.Th(
                                                col,
                                                style={
                                                    "background": "#1a1a1a",
                                                    "border": "1px solid #666",
                                                    "padding": "6px",
                                                },
                                            )
                                            for col in ["VFO", "Freq (MHz)", "Bearing", "Power (dB)", "Confidence", "Status"]
                                        ]
                                    )
                                ),
                                html.Tbody(id="multi-doa-table-body"),
                            ],
                            style={
                                "width": "100%",
                                "color": "white",
                                "borderCollapse": "collapse",
                                "fontSize": "14px",
                            },
                        ),
                        html.Div(
                            "Warning: Multi-VFO DoA view requires output_vfo=-1 (ALL mode) to be set.",
                            id="multi-doa-warning",
                            style={"color": "#f39c12", "marginTop": "10px", "textAlign": "center"},
                        ),
                    ],
                    style={"width": "38%", "padding": "10px"},
                ),
            ],
            style={"display": "flex", "height": "80vh"},
        ),
        html.Div(
            [
                dcc.Graph(
                    id="multi-doa-history",
                    figure=multi_doa_history_fig,
                    style={"height": "100%", "width": "100%"},
                ),
            ],
            style={"height": "20vh"},
        ),
    ]
)
