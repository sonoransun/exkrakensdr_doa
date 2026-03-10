# isort: off
from maindash import app, web_interface

# isort: on

from dash_devices.dependencies import Input, Output
from kraken_web_config import generate_config_page_layout
from kraken_web_doa import plot_doa
from variables import doa_fig
from views import generate_doa_page, generate_multi_doa_page, spectrum_page

INACTIVE = "header_inactive"
ACTIVE = "header_active"


@app.callback(
    [
        Output("page-content", "children"),
        Output("header_config", "className"),
        Output("header_spectrum", "className"),
        Output("header_doa", "className"),
        Output("header_multi_doa", "className"),
    ],
    [Input("url", "pathname")],
)
def display_page(pathname):
    global spectrum_fig
    web_interface.pathname = pathname

    if pathname == "/" or pathname == "/init":
        web_interface.module_signal_processor.en_spectrum = False
        return [generate_config_page_layout(web_interface), ACTIVE, INACTIVE, INACTIVE, INACTIVE]
    elif pathname == "/config":
        web_interface.module_signal_processor.en_spectrum = False
        return [generate_config_page_layout(web_interface), ACTIVE, INACTIVE, INACTIVE, INACTIVE]
    elif pathname == "/spectrum":
        web_interface.module_signal_processor.en_spectrum = True
        web_interface.reset_spectrum_graph_flag = True
        return [spectrum_page.layout, INACTIVE, ACTIVE, INACTIVE, INACTIVE]
    elif pathname == "/doa":
        web_interface.module_signal_processor.en_spectrum = False
        web_interface.reset_doa_graph_flag = True
        plot_doa(app, web_interface, doa_fig)
        return [generate_doa_page.layout, INACTIVE, INACTIVE, ACTIVE, INACTIVE]
    elif pathname == "/multi-doa":
        web_interface.module_signal_processor.en_spectrum = False
        web_interface.reset_multi_doa_graph_flag = True
        return [generate_multi_doa_page.layout, INACTIVE, INACTIVE, INACTIVE, ACTIVE]
    return Output("dummy_output", "children", "")
