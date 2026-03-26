import json, sys
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

FILE = sys.argv[1] if len(sys.argv) > 1 else "computo_snapshots.json"

with open(FILE, encoding='utf-8') as f:
    snaps = json.load(f)

times   = [s["server_fecha"][-8:-3] for s in snaps]
actas   = [s["pct_actas"] for s in snaps]
aupp    = [s["partidos"]["A-UPP"]["pct"] for s in snaps]
apb     = [s["partidos"]["APB-SUMATE"]["pct"] for s in snaps]
mts     = [s["partidos"]["MTS"]["pct"] for s in snaps]
margs   = [s["delta"].get("A-UPP", {}).get("marginal_pct") for s in snaps]

valid_margs = [m for m in margs if m is not None]
avg_marg  = sum(valid_margs) / len(valid_margs) if valid_margs else 0
avg_rec4  = sum(valid_margs[-4:]) / min(4, len(valid_margs)) if valid_margs else 0

last = snaps[-1]
last_votos = last["votos_validos"]
last_actas = last["actas_computadas"]
last_aupp  = last["partidos"]["A-UPP"]["votos"]
total_actas = last["actas_habilitadas"]
vpa = last_votos / last_actas
rem = (total_actas - last_actas) * vpa
needed    = (0.40 * (last_votos + rem) - last_aupp) / rem * 100
proj_avg  = (last_aupp + avg_marg/100 * rem) / (last_votos + rem) * 100
proj_rec  = (last_aupp + avg_rec4/100 * rem) / (last_votos + rem) * 100

# ── layout ──────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 10), facecolor="#0f0f0f")
gs  = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.3)

GOLD   = "#EDC948"
RED    = "#E24B4A"
GREEN  = "#1D9E75"
PURPLE = "#7570B3"
GRAY   = "#BAB0AC"
PINK   = "#D45087"
BG     = "#0f0f0f"
PANEL  = "#1a1a1a"
TEXT   = "#e0e0e0"
MUTED  = "#888888"

def ax_style(ax, title):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.spines[:].set_color("#333333")
    ax.set_title(title, color=TEXT, fontsize=9, pad=6)
    ax.yaxis.label.set_color(MUTED)
    ax.xaxis.label.set_color(MUTED)

x = np.arange(len(times))

# ── 1. Acumulado A-UPP vs APB vs MTS ────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, :])
ax_style(ax1, "% acumulado por partido")
ax1.plot(x, aupp, color=GOLD,   lw=2.5, marker="o", ms=4, label="A-UPP")
ax1.plot(x, apb,  color=GRAY,   lw=1.5, marker="o", ms=3, label="APB-SUMATE")
ax1.plot(x, mts,  color=PINK,   lw=1.5, marker="o", ms=3, label="MTS")
ax1.axhline(40, color=GREEN, lw=1, ls="--", label="40%")
ax1.set_ylim(13, 42)
ax1.set_xticks(x); ax1.set_xticklabels(times, rotation=45, ha="right")
ax1.legend(fontsize=8, facecolor=PANEL, labelcolor=TEXT, framealpha=0.8)
ax1.set_ylabel("%")

# Projection annotation
ax1.annotate(f"proj (media): {proj_avg:.2f}%", xy=(x[-1], aupp[-1]),
             xytext=(x[-1]-1.5, aupp[-1]+0.6),
             color=GOLD, fontsize=8,
             arrowprops=dict(arrowstyle="->", color=GOLD, lw=0.8))

# ── 2. Tasa marginal A-UPP ───────────────────────────────────────────────────
ax2 = fig.add_subplot(gs[1, :])
ax_style(ax2, "tasa marginal A-UPP por intervalo")
bar_colors = [GREEN if (m and m >= needed) else RED for m in margs]
bars = ax2.bar(x, [m or 0 for m in margs], color=bar_colors, alpha=0.8, width=0.6)
ax2.axhline(needed,   color=PURPLE, lw=1.2, ls="--", label=f"necesaria {needed:.2f}%")
ax2.axhline(avg_marg, color=GOLD,   lw=1,   ls=":",  label=f"media {avg_marg:.2f}%")
ax2.axhline(avg_rec4, color=GRAY,   lw=1,   ls=":",  label=f"media últ.4 {avg_rec4:.2f}%")
ax2.set_ylim(0, 70)
ax2.set_xticks(x); ax2.set_xticklabels(times, rotation=45, ha="right")
ax2.legend(fontsize=8, facecolor=PANEL, labelcolor=TEXT, framealpha=0.8)
ax2.set_ylabel("%")
for bar, m in zip(bars, margs):
    if m:
        ax2.text(bar.get_x()+bar.get_width()/2, m+1, f"{m:.1f}", ha="center",
                 va="bottom", fontsize=7, color=TEXT)

# ── 3. % actas computadas ────────────────────────────────────────────────────
ax3 = fig.add_subplot(gs[2, 0])
ax_style(ax3, "% actas computadas")
ax3.fill_between(x, actas, alpha=0.3, color=GOLD)
ax3.plot(x, actas, color=GOLD, lw=1.5, marker="o", ms=3)
ax3.set_ylim(60, 105)
ax3.set_xticks(x[::2]); ax3.set_xticklabels(times[::2], rotation=45, ha="right")
ax3.set_ylabel("%")

# ── 4. Proyecciones ──────────────────────────────────────────────────────────
ax4 = fig.add_subplot(gs[2, 1])
ax_style(ax4, "proyecciones finales A-UPP")
scenarios = ["actual", "proj\nmedia", "proj\núlt. 4", "umbral"]
vals      = [aupp[-1], proj_avg, proj_rec, 40.0]
colors    = [GOLD, GREEN if proj_avg>=40 else RED,
             GREEN if proj_rec>=40 else RED, GREEN]
bars4 = ax4.bar(scenarios, vals, color=colors, alpha=0.85, width=0.5)
ax4.axhline(40, color=GREEN, lw=1, ls="--")
ax4.set_ylim(38.5, 41.5)
for bar, v in zip(bars4, vals):
    ax4.text(bar.get_x()+bar.get_width()/2, v+0.03, f"{v:.3f}%",
             ha="center", va="bottom", fontsize=8, color=TEXT)
ax4.set_ylabel("%")

# ── title ────────────────────────────────────────────────────────────────────
fig.suptitle(
    f"Cómputo Oficial — Gobernador Cochabamba  |  "
    f"{last['server_fecha']}  |  {last['pct_actas']:.2f}% actas",
    color=TEXT, fontsize=11, y=0.98
)

out = FILE.replace(".json", "_dashboard.png")
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
print(f"Saved: {out}")
plt.show()