"""Shared matplotlib style for the DRIFT plots (serif font, colour-blind palette, vector PDF)."""
import os

import matplotlib
import matplotlib.pyplot as plt

FONT_SIZE = 9                     # printed size: the figure is drawn at column width
DPI = 300
FORMAT = "pdf"
COL_W = 3.5                       # IEEE single column, inches (= 0.48\textwidth)
HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.normpath(os.path.join(HERE, "..", "figures"))
os.makedirs(FIG_DIR, exist_ok=True)
DATA = os.path.normpath(os.path.join(HERE, "..", "data"))

matplotlib.rcParams.update({
    "font.size": FONT_SIZE,
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "STIXGeneral", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "axes.labelsize": FONT_SIZE,
    "axes.titlesize": FONT_SIZE + 1,
    "xtick.labelsize": FONT_SIZE - 1,
    "ytick.labelsize": FONT_SIZE - 1,
    "legend.fontsize": FONT_SIZE - 1,
    "legend.frameon": False,
    "figure.dpi": DPI,
    "savefig.dpi": DPI,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
    "axes.grid": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "lines.linewidth": 1.2,
    "pdf.fonttype": 42,           # embed TrueType: passes IEEE PDF font checks
    "ps.fonttype": 42,
    "text.usetex": False,
})

# Colorblind-safe (Tableau colorblind 10); 0 and 1 also differ in lightness,
# so they stay distinct in grayscale. Pair with distinct markers/line styles.
plt.style.use("tableau-colorblind10")
COLORS = plt.rcParams["axes.prop_cycle"].by_key()["color"]
BLUE, ORANGE, GRAY, DARK = COLORS[0], COLORS[1], COLORS[2], COLORS[3]
SHADE = "#d9d9d9"                 # neutral shading for events (freezes, congestion)


def save_fig(fig, name, fmt=FORMAT):
    """Save to FIG_DIR as vector PDF (plus a PNG preview for checking)."""
    path = os.path.join(FIG_DIR, f"{name}.{fmt}")
    fig.savefig(path)
    fig.savefig(os.path.join(FIG_DIR, f"{name}.png"))
    print(f"Saved: {path}")
