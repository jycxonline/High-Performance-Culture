"""
Chart generation for the HPC Diagnostic Tool.
All charts return either a matplotlib Figure (for Streamlit display)
or a BytesIO PNG buffer (for PDF embedding).
"""
from __future__ import annotations
import io
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

from .config_loader import PILLARS

# Palette
HEX_NAVY = "#1F3864"
HEX_GOLD = "#BF9000"
HEX_LNAVY = "#4472C4"


def _to_png(fig) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Radar chart
# ---------------------------------------------------------------------------
def radar_chart(focus_pillar_means: dict[str, float],
                company_pillar_means: dict[str, float],
                focus_label: str = "Selected department"):
    labels = PILLARS
    n = len(labels)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]

    dept_vals = [focus_pillar_means[p] for p in labels]
    comp_vals = [company_pillar_means[p] for p in labels]
    dept_vals += dept_vals[:1]
    comp_vals += comp_vals[:1]

    fig, ax = plt.subplots(figsize=(6.2, 5.2), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("white")
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    ax.plot(angles, comp_vals, color=HEX_GOLD, linewidth=2.2, label="Company-wide average")
    ax.fill(angles, comp_vals, color=HEX_GOLD, alpha=0.10)
    ax.plot(angles, dept_vals, color=HEX_NAVY, linewidth=2.6, label=focus_label)
    ax.fill(angles, dept_vals, color=HEX_NAVY, alpha=0.28)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11, fontweight="bold", color="#333333")
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], fontsize=8, color="#666666")
    ax.set_ylim(0, 10)
    ax.grid(color="#CCCCCC", linewidth=0.7)
    ax.spines["polar"].set_color("#CCCCCC")
    ax.set_title("Strategic Vector Performance Radar",
                 fontsize=13, fontweight="bold", color=HEX_NAVY, pad=22)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08),
              ncol=2, frameon=False, fontsize=10)
    plt.tight_layout()
    return fig


def radar_chart_multi(dept_pillar_means: dict[str, dict[str, float]],
                      company_pillar_means: dict[str, float]):
    """Overlay multiple departments on the radar plus company avg."""
    labels = PILLARS
    n = len(labels)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6.5, 5.5), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("white")
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Company average as gold reference
    comp_vals = [company_pillar_means[p] for p in labels] + [company_pillar_means[labels[0]]]
    ax.plot(angles, comp_vals, color=HEX_GOLD, linewidth=2.4, linestyle="--",
            label="Company-wide average")

    palette = ["#1F3864", "#548235", "#C00000", "#7030A0", "#ED7D31", "#2E75B6"]
    for i, (dept, means) in enumerate(dept_pillar_means.items()):
        vals = [means[p] for p in labels] + [means[labels[0]]]
        c = palette[i % len(palette)]
        ax.plot(angles, vals, color=c, linewidth=2.2, label=dept)
        ax.fill(angles, vals, color=c, alpha=0.10)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11, fontweight="bold", color="#333333")
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_ylim(0, 10)
    ax.grid(color="#CCCCCC", linewidth=0.7)
    ax.spines["polar"].set_color("#CCCCCC")
    ax.set_title("Strategic Vector Performance Radar — multi-department",
                 fontsize=12, fontweight="bold", color=HEX_NAVY, pad=22)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncol=2, frameon=False, fontsize=9)
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Correlation heatmap
# ---------------------------------------------------------------------------
def correlation_heatmap(corr):
    fig, ax = plt.subplots(figsize=(6.0, 4.8))
    fig.patch.set_facecolor("white")
    cmap = mpl.colors.LinearSegmentedColormap.from_list("hpc", ["#C00000", "#FFFFFF", "#1F3864"])
    im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1)
    ax.set_xticks(range(len(PILLARS)))
    ax.set_yticks(range(len(PILLARS)))
    ax.set_xticklabels(PILLARS, fontsize=10, fontweight="bold", color="#333333")
    ax.set_yticklabels(PILLARS, fontsize=10, fontweight="bold", color="#333333")

    for i in range(len(PILLARS)):
        for j in range(len(PILLARS)):
            v = corr.values[i, j]
            txt_col = "white" if abs(v) > 0.55 else "#222222"
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    fontsize=11, fontweight="bold", color=txt_col)

    ax.set_title("Strategic Pillar Inter-Correlation Heatmap",
                 fontsize=13, fontweight="bold", color=HEX_NAVY, pad=14)
    cb = plt.colorbar(im, ax=ax, shrink=0.75)
    cb.set_label("Pearson correlation", fontsize=9)
    cb.ax.tick_params(labelsize=8)
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Department ranking
# ---------------------------------------------------------------------------
def ranking_bar(all_departments, company_overall: float, focus_dept: str = None):
    ordered = all_departments["Overall"].sort_values()
    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    fig.patch.set_facecolor("white")
    bar_colors = [HEX_NAVY if d == focus_dept else "#B4C7E7" for d in ordered.index]
    bars = ax.barh(ordered.index, ordered.values, color=bar_colors, edgecolor="white")
    ax.axvline(company_overall, color=HEX_GOLD, linestyle="--", linewidth=2,
               label=f"Company avg ({company_overall:.2f})")
    for bar, val in zip(bars, ordered.values):
        ax.text(val + 0.06, bar.get_y() + bar.get_height() / 2,
                f"{val:.2f}", va="center", fontsize=9, color="#333333")

    ax.set_xlim(0, 10)
    ax.set_xlabel("Overall HPC Score", fontsize=10)
    ax.set_title("Overall HPC Score by Department",
                 fontsize=13, fontweight="bold", color=HEX_NAVY, pad=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=9)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Public: return PNGs for PDF embedding
# ---------------------------------------------------------------------------
def radar_png(focus_pillar_means, company_pillar_means, focus_label):
    return _to_png(radar_chart(focus_pillar_means, company_pillar_means, focus_label))


def heatmap_png(corr):
    return _to_png(correlation_heatmap(corr))


def ranking_png(all_departments, company_overall, focus_dept=None):
    return _to_png(ranking_bar(all_departments, company_overall, focus_dept))
