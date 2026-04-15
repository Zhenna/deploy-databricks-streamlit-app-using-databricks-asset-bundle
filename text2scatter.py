import io
import re
from dataclasses import dataclass
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd


@dataclass
class PlotSpec:
    chart_type: str
    x: str
    y: str
    color: Optional[str] = None
    title: Optional[str] = None


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _build_column_aliases(df: pd.DataFrame) -> dict[str, str]:
    aliases: dict[str, str] = {}

    for col in df.columns:
        aliases[_normalize(col)] = col
        aliases[_normalize(col.replace("_", " "))] = col
        aliases[_normalize(col.replace("_", ""))] = col

    return aliases


def _match_column(text: str, aliases: dict[str, str]) -> Optional[str]:
    if not text:
        return None

    normalized = _normalize(text)

    if normalized in aliases:
        return aliases[normalized]

    matches = [
        actual
        for alias, actual in aliases.items()
        if normalized in alias or alias in normalized
    ]

    matches = list(dict.fromkeys(matches))

    if len(matches) == 1:
        return matches[0]

    return None


def parse_instruction(instruction: str, df: pd.DataFrame) -> PlotSpec:
    if not instruction.strip():
        raise ValueError("Instruction cannot be empty.")

    aliases = _build_column_aliases(df)

    cleaned = re.sub(
        r"^(please\s+)?(make|create|draw|show|plot)?\s*(a\s+)?(scatter\s*plot|scatter|plot|chart)?\s*(of\s+)?",
        "",
        instruction,
        flags=re.IGNORECASE,
    ).strip()

    color_text = None
    color_match = re.search(r"\bcolor\s+by\b(.+)$", cleaned, flags=re.IGNORECASE)
    if color_match:
        color_text = color_match.group(1).strip()
        cleaned = re.sub(
            r"\bcolor\s+by\b(.+)$", "", cleaned, flags=re.IGNORECASE
        ).strip()

    x_text = None
    y_text = None

    patterns = [
        r"^(?P<x>.+?)\s+(vs|versus|against)\s+(?P<y>.+)$",
        r"^(?P<y>.+?)\s+by\s+(?P<x>.+)$",
    ]

    for p in patterns:
        m = re.match(p, cleaned, flags=re.IGNORECASE)
        if m:
            x_text = m.group("x").strip()
            y_text = m.group("y").strip()
            break

    if not x_text or not y_text:
        raise ValueError("Use format like 'A vs B' or 'A against B'.")

    x_col = _match_column(x_text, aliases)
    y_col = _match_column(y_text, aliases)
    color_col = _match_column(color_text, aliases) if color_text else None

    if x_col is None:
        raise ValueError(f"Cannot match x column: {x_text}")
    if y_col is None:
        raise ValueError(f"Cannot match y column: {y_text}")
    if color_text and color_col is None:
        raise ValueError(f"Cannot match color column: {color_text}")

    if not pd.api.types.is_numeric_dtype(df[x_col]):
        raise ValueError(f"{x_col} must be numeric.")
    if not pd.api.types.is_numeric_dtype(df[y_col]):
        raise ValueError(f"{y_col} must be numeric.")

    title = f"{y_col} vs {x_col}"
    if color_col:
        title += f" (color by {color_col})"

    return PlotSpec(
        chart_type="scatter",
        x=x_col,
        y=y_col,
        color=color_col,
        title=title,
    )


def build_scatterplot(df: pd.DataFrame, spec: PlotSpec):
    cols = [spec.x, spec.y] + ([spec.color] if spec.color else [])
    plot_df = df[cols].dropna()

    fig, ax = plt.subplots(figsize=(8, 5))

    if spec.color:
        if pd.api.types.is_numeric_dtype(plot_df[spec.color]):
            scatter = ax.scatter(
                plot_df[spec.x], plot_df[spec.y], c=plot_df[spec.color]
            )
            fig.colorbar(scatter, ax=ax)
        else:
            for v, g in plot_df.groupby(spec.color):
                ax.scatter(g[spec.x], g[spec.y], label=str(v))
            ax.legend()
    else:
        ax.scatter(plot_df[spec.x], plot_df[spec.y])

    ax.set_xlabel(spec.x)
    ax.set_ylabel(spec.y)
    ax.set_title(spec.title)
    ax.grid(True)

    return fig


def figure_to_png_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf.getvalue()
