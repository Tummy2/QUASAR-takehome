# QUASAR-takehome

How to run:
1. python -m venv .venv  
2. source .venv/bin/activate for Linux/Mac
    .venv\Scripts\Activate for Windows
3. pip install -r requirements.txt
4. python plot_eeg_ecg.py "EEG and ECG data_02_raw.csv"
5. open viewer.html in the browser

Design Choices
- Ignoring metadata (#)
- Filtering out columns that are not needed
- Scaling
    - EEG + CM are in μV
    - ECG is mV by default but option to switch to μV
    - CM is separate
- Usability
    - Slider for panning and zooming
    - Dropdowns for ALL / EEG only / ECG + CM only
    - Dropdown toggle for units
    - Legend to toggle specific channel

AI Assistance
- Background knowledge on what was actually being plotted (EEG vs ECG vs CM).
- Refining the overall approach that I came up with, making sure my plan covered requirements.
- Polish details like dropdown handling, dual y-axis scaling, and visibility toggles.
- Syntax help (Plotly/Pandas/argparse) so I could move faster.
- Code commenting and readability improvements.