#!/usr/bin/env python3
"""Generate the Grover diffusion operator (reflection) diagram.

Produces `grover_reflection.jpg` — a 2D matplotlib illustration showing
the reflection of the state vector about the average amplitude,
which is the geometric interpretation of the Grover diffuser.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "diagrams" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    fig, ax = plt.subplots(1, 1, figsize=(7, 7))

    # Draw unit circle
    theta = np.linspace(0, 2 * np.pi, 200)
    ax.plot(np.cos(theta), np.sin(theta), "k-", linewidth=0.5, alpha=0.3)

    # Draw |s> (uniform superposition) at angle alpha from |u>
    alpha = 0.35  # angle of |s> from x-axis
    s = np.array([np.cos(alpha), np.sin(alpha)])
    ax.annotate("", xy=s, xytext=(0, 0),
                arrowprops=dict(arrowstyle="->", color="blue", lw=2))
    ax.text(s[0] + 0.05, s[1] + 0.05, r"$|s\rangle$", fontsize=16, color="blue")

    # Draw |w> (target/marked state) — close to y-axis
    beta = np.pi / 2 - 0.15
    w = np.array([np.cos(beta), np.sin(beta)])
    ax.annotate("", xy=w, xytext=(0, 0),
                arrowprops=dict(arrowstyle="->", color="red", lw=2))
    ax.text(w[0] + 0.05, w[1] + 0.05, r"$|w\rangle$", fontsize=16, color="red")

    # Draw average amplitude direction (bisector)
    avg_angle = (alpha + beta) / 2
    avg = np.array([np.cos(avg_angle), np.sin(avg_angle)])
    ax.annotate("", xy=avg * 0.8, xytext=(0, 0),
                arrowprops=dict(arrowstyle="->", color="gray", lw=1.5, linestyle="--"))
    ax.text(avg[0] * 0.85 - 0.15, avg[1] * 0.85, "avg", fontsize=12, color="gray")

    # Draw reflected |s'> (reflection of |s> about avg)
    # Reflection formula: s' = 2*(s.avg)*avg - s
    dot = np.dot(s, avg)
    s_reflected = 2 * dot * avg - s
    ax.annotate("", xy=s_reflected, xytext=(0, 0),
                arrowprops=dict(arrowstyle="->", color="green", lw=2))
    ax.text(s_reflected[0] + 0.05, s_reflected[1] - 0.1, r"$|s'\rangle$", fontsize=16, color="green")

    # Draw reflection arc
    arc_angles = np.linspace(alpha, 2 * avg_angle - alpha, 50)
    ax.plot(0.3 * np.cos(arc_angles), 0.3 * np.sin(arc_angles), "k-", linewidth=1)
    mid_angle = avg_angle
    ax.text(0.4 * np.cos(mid_angle), 0.4 * np.sin(mid_angle), r"$2\theta$", fontsize=14, ha="center")

    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-1.3, 1.3)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Grover Diffusion Operator\n(Reflection about Average Amplitude)", fontsize=14, pad=20)

    output_path = OUTPUT_DIR / "grover_reflection.jpg"
    fig.savefig(output_path, dpi=200, bbox_inches="tight", format="jpg")
    plt.close(fig)
    print(f"Saved: {output_path}")

    # Also save to repo root
    root_path = Path(__file__).resolve().parent.parent / "grover_reflection.jpg"
    fig2, ax2 = plt.subplots(1, 1, figsize=(7, 7))
    ax2.plot(np.cos(theta), np.sin(theta), "k-", linewidth=0.5, alpha=0.3)
    ax2.annotate("", xy=s, xytext=(0, 0), arrowprops=dict(arrowstyle="->", color="blue", lw=2))
    ax2.text(s[0] + 0.05, s[1] + 0.05, r"$|s\rangle$", fontsize=16, color="blue")
    ax2.annotate("", xy=w, xytext=(0, 0), arrowprops=dict(arrowstyle="->", color="red", lw=2))
    ax2.text(w[0] + 0.05, w[1] + 0.05, r"$|w\rangle$", fontsize=16, color="red")
    ax2.annotate("", xy=avg * 0.8, xytext=(0, 0), arrowprops=dict(arrowstyle="->", color="gray", lw=1.5, linestyle="--"))
    ax2.text(avg[0] * 0.85 - 0.15, avg[1] * 0.85, "avg", fontsize=12, color="gray")
    ax2.annotate("", xy=s_reflected, xytext=(0, 0), arrowprops=dict(arrowstyle="->", color="green", lw=2))
    ax2.text(s_reflected[0] + 0.05, s_reflected[1] - 0.1, r"$|s'\rangle$", fontsize=16, color="green")
    ax2.plot(0.3 * np.cos(arc_angles), 0.3 * np.sin(arc_angles), "k-", linewidth=1)
    ax2.text(0.4 * np.cos(mid_angle), 0.4 * np.sin(mid_angle), r"$2\theta$", fontsize=14, ha="center")
    ax2.set_xlim(-1.3, 1.3)
    ax2.set_ylim(-1.3, 1.3)
    ax2.set_aspect("equal")
    ax2.axis("off")
    ax2.set_title("Grover Diffusion Operator\n(Reflection about Average Amplitude)", fontsize=14, pad=20)
    fig2.savefig(root_path, dpi=200, bbox_inches="tight", format="jpg")
    plt.close(fig2)
    print(f"Saved: {root_path}")


if __name__ == "__main__":
    main()
