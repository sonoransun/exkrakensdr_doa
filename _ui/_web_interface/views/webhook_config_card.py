import dash_core_components as dcc
import dash_html_components as html

# isort: off
from maindash import web_interface

# isort: on
from variables import dsp_settings, option


def get_webhook_config_card_layout():
    en_webhook = [1] if dsp_settings.get("webhook_enabled", False) else []
    en_evt_signal_appear = [1] if dsp_settings.get("webhook_evt_signal_appear", True) else []
    en_evt_signal_disappear = [1] if dsp_settings.get("webhook_evt_signal_disappear", True) else []
    en_evt_novel_freq = [1] if dsp_settings.get("webhook_evt_novel_freq", True) else []
    en_evt_doa_change = [1] if dsp_settings.get("webhook_evt_doa_change", True) else []
    en_evt_power_alert = [1] if dsp_settings.get("webhook_evt_power_alert", True) else []
    en_autolearn = [1] if dsp_settings.get("webhook_autolearn_enabled", False) else []

    return html.Div(
        [
            html.H2("Webhook Configuration", id="webhook_conf_title"),
            html.Div(
                [
                    html.Div("Enable Webhooks:", className="field-label"),
                    dcc.Checklist(options=option, id="webhook_enabled", className="field-body", value=en_webhook),
                ],
                className="field",
            ),
            html.Div(
                [
                    html.Div("Webhook URL(s):", className="field-label"),
                    dcc.Input(
                        id="webhook_urls",
                        value=dsp_settings.get("webhook_urls", ""),
                        type="text",
                        className="field-body-textbox",
                        debounce=True,
                    ),
                ],
                className="field",
            ),
            html.H4("Event Types"),
            html.Div(
                [
                    html.Div("Signal Appear:", className="field-label"),
                    dcc.Checklist(
                        options=option, id="webhook_evt_signal_appear", className="field-body", value=en_evt_signal_appear
                    ),
                ],
                className="field",
            ),
            html.Div(
                [
                    html.Div("Signal Disappear:", className="field-label"),
                    dcc.Checklist(
                        options=option,
                        id="webhook_evt_signal_disappear",
                        className="field-body",
                        value=en_evt_signal_disappear,
                    ),
                ],
                className="field",
            ),
            html.Div(
                [
                    html.Div("Novel Frequency:", className="field-label"),
                    dcc.Checklist(
                        options=option, id="webhook_evt_novel_freq", className="field-body", value=en_evt_novel_freq
                    ),
                ],
                className="field",
            ),
            html.Div(
                [
                    html.Div("DoA Change:", className="field-label"),
                    dcc.Checklist(
                        options=option, id="webhook_evt_doa_change", className="field-body", value=en_evt_doa_change
                    ),
                ],
                className="field",
            ),
            html.Div(
                [
                    html.Div("Power Level Alert:", className="field-label"),
                    dcc.Checklist(
                        options=option, id="webhook_evt_power_alert", className="field-body", value=en_evt_power_alert
                    ),
                ],
                className="field",
            ),
            html.H4("Thresholds"),
            html.Div(
                [
                    html.Div("DoA Change Threshold [deg]:", className="field-label"),
                    dcc.Input(
                        id="webhook_doa_change_threshold_deg",
                        value=dsp_settings.get("webhook_doa_change_threshold_deg", 10),
                        type="number",
                        min=1,
                        max=180,
                        className="field-body-textbox",
                        debounce=True,
                    ),
                ],
                className="field",
            ),
            html.Div(
                [
                    html.Div("Power High Threshold [dBm]:", className="field-label"),
                    dcc.Input(
                        id="webhook_power_high_threshold_dbm",
                        value=dsp_settings.get("webhook_power_high_threshold_dbm", -30),
                        type="number",
                        className="field-body-textbox",
                        debounce=True,
                    ),
                ],
                className="field",
            ),
            html.Div(
                [
                    html.Div("Power Low Threshold [dBm]:", className="field-label"),
                    dcc.Input(
                        id="webhook_power_low_threshold_dbm",
                        value=dsp_settings.get("webhook_power_low_threshold_dbm", -90),
                        type="number",
                        className="field-body-textbox",
                        debounce=True,
                    ),
                ],
                className="field",
            ),
            html.H4("Frequency Classification"),
            html.Div(
                [
                    html.Div("Known Frequencies [Hz]:", className="field-label"),
                    dcc.Input(
                        id="webhook_known_frequencies",
                        value=dsp_settings.get("webhook_known_frequencies", ""),
                        type="text",
                        className="field-body-textbox",
                        debounce=True,
                    ),
                ],
                className="field",
            ),
            html.Div(
                [
                    html.Div("Frequency Match Tolerance [Hz]:", className="field-label"),
                    dcc.Input(
                        id="webhook_freq_tolerance_hz",
                        value=dsp_settings.get("webhook_freq_tolerance_hz", 5000),
                        type="number",
                        min=100,
                        className="field-body-textbox",
                        debounce=True,
                    ),
                ],
                className="field",
            ),
            html.Div(
                [
                    html.Div("Enable Auto-learn:", className="field-label"),
                    dcc.Checklist(
                        options=option, id="webhook_autolearn_enabled", className="field-body", value=en_autolearn
                    ),
                ],
                className="field",
            ),
            html.Div(
                [
                    html.Div("Auto-learn Window [sec]:", className="field-label"),
                    dcc.Input(
                        id="webhook_autolearn_window_sec",
                        value=dsp_settings.get("webhook_autolearn_window_sec", 3600),
                        type="number",
                        min=60,
                        className="field-body-textbox",
                        debounce=True,
                    ),
                ],
                className="field",
            ),
            html.H4("Retry Settings"),
            html.Div(
                [
                    html.Div("Retry Count:", className="field-label"),
                    dcc.Input(
                        id="webhook_retry_count",
                        value=dsp_settings.get("webhook_retry_count", 3),
                        type="number",
                        min=0,
                        max=10,
                        className="field-body-textbox",
                        debounce=True,
                    ),
                ],
                className="field",
            ),
            html.Div(
                [
                    html.Div("Retry Delay [ms]:", className="field-label"),
                    dcc.Input(
                        id="webhook_retry_delay_ms",
                        value=dsp_settings.get("webhook_retry_delay_ms", 1000),
                        type="number",
                        min=100,
                        className="field-body-textbox",
                        debounce=True,
                    ),
                ],
                className="field",
            ),
        ],
        className="card",
    )
