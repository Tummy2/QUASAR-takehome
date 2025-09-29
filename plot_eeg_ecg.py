import argparse
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import webbrowser
from pathlib import Path

# Channels that matter
EEG_CHANNELS = [
    "Fz", "Cz", "P3", "C3", "F3", "F4", "C4", "P4",
    "Fp1", "Fp2", "T3", "T4", "T5", "T6",
    "O1", "O2", "F7", "F8", "A1", "A2", "Pz"
]

ECG_CHANNELS = {
    "X1:LEOG": "ECG_Left",
    "X2:REOG": "ECG_Right"
}

# Stuff that doesn't matter
IGNORE_EXACT = {"Trigger", "Time_Offset", "ADC_Status", "ADC_Sequence", "Event", "Comments"}
IGNORE_PREFIXES = ("X3:",)

def filter_columns(df, tcol):
    # Keep time + other columns that we need
    keep = [tcol]
    for c in df.columns:
        if c == tcol:
            continue
        if c in IGNORE_EXACT:
            continue
        if any(c.startswith(pfx) for pfx in IGNORE_PREFIXES):
            continue
        keep.append(c)
    return df[keep]

def split_roles(cols):
    # Split into EEG, ECG, and CM
    eeg = [c for c in cols if c in EEG_CHANNELS]
    ecg_raw = [c for c in cols if c in ECG_CHANNELS]
    cm = [c for c in cols if c == "CM"]
    return eeg, ecg_raw, cm

def main():
    ap = argparse.ArgumentParser(description="Scrollable multichannel EEG+ECG plot")
    ap.add_argument("csv", help="Path to EEG and ECG data CSV")
    ap.add_argument("--html", default="viewer.html", help="Output HTML file")
    ap.add_argument("--title", default="EEG + ECG Viewer", help="Plot title")
    ap.add_argument("--open", action="store_true", help="Open the output HTML in your browser when done")
    args = ap.parse_args()

    # Read csv, ignore lines with #
    df = pd.read_csv(args.csv, comment="#")

    tcol = "Time"
    if tcol not in df.columns:
        raise SystemExit(f"Expected '{tcol}' column not found.")
    df[tcol] = pd.to_numeric(df[tcol], errors="coerce")
    df = df.dropna(subset=[tcol]).sort_values(tcol)

    df = filter_columns(df, tcol)

    data_cols = [c for c in df.columns if c != tcol]
    eeg_cols, ecg_raw_cols, cm_cols = split_roles(data_cols)

    if not eeg_cols and not ecg_raw_cols and not cm_cols:
        raise SystemExit("No EEG/ECG/CM columns found after filtering. Check headers.")

    # μV and mV
    ecg_uv = {} 
    ecg_mv = {}  
    for raw in ecg_raw_cols:
        nice = ECG_CHANNELS[raw]
        ecg_uv[nice + " (μV)"] = df[raw] * 1000.0
        ecg_mv[nice + " (mV)"] = df[raw]

    # Second y axis for ECG or CM
    use_secondary = (len(ecg_uv) + len(cm_cols)) > 0
    fig = make_subplots(specs=[[{"secondary_y": use_secondary}]])

    # Track indices for dropdowns
    trace_indices = {
        "EEG": [],
        "ECG_uV": [],
        "ECG_mV": [],
        "CM": []
    }

    # EEG -> left axis (μV)
    for ch in eeg_cols:
        fig.add_trace(
            go.Scatter(x=df[tcol], y=df[ch], name=ch, mode="lines"),
            secondary_y=False
        )
        trace_indices["EEG"].append(len(fig.data) - 1)

    # CM on right axis
    for ch in cm_cols:
        fig.add_trace(
            go.Scatter(
                x=df[tcol], y=df[ch],
                name="CM (μV, reference)", mode="lines",
                line=dict(dash="dot")
            ),
            secondary_y=True
        )
        trace_indices["CM"].append(len(fig.data) - 1)

    # ECG (mV) on right axis
    for label, series in ecg_mv.items():
        fig.add_trace(
            go.Scatter(x=df[tcol], y=series, name=label, mode="lines"),
            secondary_y=True
        )
        trace_indices["ECG_mV"].append(len(fig.data) - 1)

    # ECG (μV)
    for label, series in ecg_uv.items():
        fig.add_trace(
            go.Scatter(x=df[tcol], y=series, name=label, mode="lines", visible=False),
            secondary_y=True
        )
        trace_indices["ECG_uV"].append(len(fig.data) - 1)

    # Layout
    fig.update_layout(
        title=args.title,
        xaxis_title="Time (s)",
        legend_title="Channels (click to toggle)",
        hovermode="x unified",
        xaxis=dict(rangeslider=dict(visible=True)),
        template="plotly_white",
        margin=dict(l=60, r=60, t=80, b=40), 
    )
    # left axis label
    fig.update_yaxes(title_text="EEG & CM (μV)", secondary_y=False)
    # right axis label
    if use_secondary:
        fig.update_yaxes(title_text="ECG (mV) / CM (μV)", secondary_y=True, showgrid=False)

    total_traces = len(fig.data)
    visibility_all = [True] * total_traces

    # EEG only
    vis_eeg_only = [False] * total_traces
    for i in trace_indices["EEG"]:
        vis_eeg_only[i] = True

    # ECG + CM only
    vis_other_only = [False] * total_traces
    for grp in ("CM", "ECG_mV", "ECG_uV"):
        for i in trace_indices[grp]:
            if grp == "ECG_uV":
                continue
            vis_other_only[i] = True

     # swap ECG units
    def unit_mode_visibility(mode):
        vis = [trace.visible if trace.visible is not None else True for trace in fig.data]
        if mode == "mV":
            for i in trace_indices["ECG_mV"]:
                vis[i] = True
            for i in trace_indices["ECG_uV"]:
                vis[i] = False
        else:
            for i in trace_indices["ECG_mV"]:
                vis[i] = False
            for i in trace_indices["ECG_uV"]:
                vis[i] = True
        return vis

    # Add both dropdowns
    fig.update_layout(
        updatemenus=[
            # preset dropdown
            dict(
                type="dropdown",
                x=1.0, xanchor="right", y=1.20, yanchor="top",
                buttons=[
                    dict(label="All", method="update",
                         args=[{"visible": visibility_all}]),
                    dict(label="EEG only", method="update",
                         args=[{"visible": vis_eeg_only}]),
                    dict(label="ECG+CM only", method="update",
                         args=[{"visible": vis_other_only}]),
                ],
                showactive=True,
            ),
            # unit toggle just below
            dict(
                type="dropdown",
                x=1.0, xanchor="right", y=1.08, yanchor="top",
                buttons=[
                    dict(
                        label="ECG in mV",
                        method="update",
                        args=[
                            {"visible": unit_mode_visibility("mV")},
                            {"yaxis2": {"title": "ECG (mV) / CM (μV)", "overlaying": "y", "side": "right", "showgrid": False}},
                        ],
                    ),
                    dict(
                        label="ECG in μV",
                        method="update",
                        args=[
                            {"visible": unit_mode_visibility("uV")},
                            {"yaxis2": {"title": "ECG (μV) / CM (μV)", "overlaying": "y", "side": "right", "showgrid": False}},
                        ],
                    ),
                ],
                showactive=True,
            ),
        ]
    )

    # write html
    out = Path(args.html).resolve()
    fig.write_html(str(out), include_plotlyjs="cdn", full_html=True)
    print(f"Wrote {out}. Open it in a browser and explore!")
    if args.open:
        webbrowser.open(out.as_uri())

if __name__ == "__main__":
    main()
