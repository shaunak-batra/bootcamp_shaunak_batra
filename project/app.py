"""Flask app serving the diversification monitor: a dashboard and a JSON API.

Stage 13. Two things load once at startup and never again per request: the fitted
regime model, and the current pipeline reading. A route that refits the model or
re-pulls nineteen years of prices on every call would take seconds per request and
would also be non-deterministic, since the fit is seed-dependent.

Run it with:  python app.py        then open http://127.0.0.1:5055
or:           python run.py --serve
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd
from flask import (Flask, jsonify, render_template, request,
                   send_from_directory)

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402
from src.pipeline import latest_reading, run_pipeline  # noqa: E402

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)

# --- loaded once, at import, not per request --------------------------------
log.info("warming up: running pipeline and loading regime model")
_RESULT = run_pipeline(save=False)
_REGIME = _RESULT["regime"]
_BAND = _REGIME["band"]
_READING = latest_reading(_RESULT)
log.info("ready. as of %s, correlation %.4f, regime %s",
         _READING["as_of"], _READING["correlation"], _READING["regime"])


# --- chart ------------------------------------------------------------------

def _line_chart_svg(series: pd.Series, threshold: float,
                    width: int = 1000, height: int = 300) -> str:
    """Hand-built SVG line chart.

    Drawn rather than embedded as a PNG so it scales, stays crisp, and picks up
    the page's colours through CSS classes instead of baking them into an image.
    The series is downsampled to weekly, which is well below the resolution any
    reader can perceive across nineteen years and keeps the path short.
    """
    s = series.resample("W").last().dropna()
    if s.empty:
        return "<p>no data</p>"

    pad_l, pad_r, pad_t, pad_b = 46, 12, 14, 26
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    y_min, y_max = -0.85, 0.55
    x0 = s.index[0].value
    x_span = max(s.index[-1].value - x0, 1)

    def px(ts) -> float:
        return pad_l + (ts.value - x0) / x_span * plot_w

    def py(v: float) -> float:
        v = min(max(v, y_min), y_max)
        return pad_t + (y_max - v) / (y_max - y_min) * plot_h

    parts: list[str] = [
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="SPY-TLT rolling correlation, 2007 to present">'
    ]

    # horizontal gridlines and y labels
    for v in (-0.75, -0.5, -0.25, 0.0, 0.25, 0.5):
        y = py(v)
        cls = "zero" if v == 0.0 else "grid"
        parts.append(f'<line class="{cls}" x1="{pad_l}" y1="{y:.1f}" '
                     f'x2="{width - pad_r}" y2="{y:.1f}"/>')
        parts.append(f'<text class="axis" x="{pad_l - 8}" y="{y + 3.5:.1f}" '
                     f'text-anchor="end">{v:+.2f}</text>')

    # regime threshold
    yt = py(threshold)
    parts.append(f'<line class="thr" x1="{pad_l}" y1="{yt:.1f}" '
                 f'x2="{width - pad_r}" y2="{yt:.1f}"/>')

    # year ticks, every third year to avoid crowding
    for year in range(s.index[0].year, s.index[-1].year + 1):
        if year % 3:
            continue
        ts = pd.Timestamp(year=year, month=1, day=1)
        if not (s.index[0] <= ts <= s.index[-1]):
            continue
        x = px(ts)
        parts.append(f'<line class="grid" x1="{x:.1f}" y1="{pad_t}" '
                     f'x2="{x:.1f}" y2="{pad_t + plot_h}"/>')
        parts.append(f'<text class="axis" x="{x:.1f}" y="{height - 8}" '
                     f'text-anchor="middle">{year}</text>')

    pts = " ".join(f"{px(t):.1f},{py(v):.1f}" for t, v in s.items())
    parts.append(f'<polyline class="series" points="{pts}"/>')
    parts.append("</svg>")
    return "".join(parts)


def _annual_rows() -> list[dict]:
    series = _RESULT["series"]
    flags = _RESULT["flags"]
    dr = _RESULT["features"]["diversification_ratio"]
    rows = []
    for year, grp in series.groupby(series.index.year):
        rows.append({
            "year": int(year),
            "corr": float(grp.mean()),
            "dr": float(dr.reindex(grp.index).mean()),
            "flagged": int(flags.reindex(grp.index).fillna(False).sum()),
            "days": int(len(grp)),
        })
    return rows


def _narrative() -> tuple[str, str]:
    """Headline and explanation, phrased for whoever opens the page cold."""
    r = _READING
    rho = r["correlation"]
    if r["regime"] == "elevated":
        headline = (f"Equities and Treasuries are moving together "
                    f"({rho:+.2f})")
        explanation = (
            "The correlation the portfolio's diversification depends on has risen above "
            "its regime threshold, so bonds are not currently offsetting equity moves. "
            f"Today's reading sits at the {r['percentile_vs_history']*100:.0f}th "
            "percentile of the last nineteen years. This has been the prevailing state "
            "since 2021.")
    else:
        headline = f"Equities and Treasuries are moving oppositely ({rho:+.2f})"
        explanation = (
            "The correlation sits below its regime threshold, so bonds are cushioning "
            "equity moves the way a diversified book assumes they will. "
            f"Today's reading is at the {r['percentile_vs_history']*100:.0f}th percentile "
            "of the last nineteen years.")
    return headline, explanation


# --- pages ------------------------------------------------------------------

@app.route("/", methods=["GET"])
def dashboard():
    headline, explanation = _narrative()
    return render_template(
        "dashboard.html",
        reading=_READING,
        band=_BAND,
        annual=_annual_rows(),
        chart_svg=_line_chart_svg(_RESULT["series"], _BAND["enter"]),
        headline=headline,
        explanation=explanation,
        family=config.SCC_FAMILY,
        alpha=config.SCC_ALPHA,
    )


@app.route("/report", methods=["GET"])
def report():
    """The written memo, rendered as plain text so no dependency is needed."""
    path = ROOT / "reports" / "final_report.md"
    if not path.exists():
        return jsonify({"error": "final_report.md not found. Run python run.py"}), 404
    body = path.read_text(encoding="utf-8")
    return (f"<!doctype html><meta charset='utf-8'><title>Risk memo</title>"
            f"<style>body{{background:#0d1117;color:#e8edf3;font:15px/1.65 "
            f"ui-monospace,Menlo,Consolas,monospace;max-width:80ch;margin:0 auto;"
            f"padding:40px 22px}}a{{color:#3fb9b2}}"
            f"@media(prefers-color-scheme:light){{body{{background:#f4f6f8;"
            f"color:#131820}}}}</style>"
            f"<p><a href='/'>&larr; dashboard</a></p><pre>{body}</pre>")


@app.route("/notebook", methods=["GET"])
def notebook():
    path = ROOT / "reports" / "project_pipeline.html"
    if not path.exists():
        return jsonify({"error": "notebook export not found. Run python run.py"}), 404
    return send_from_directory(path.parent, path.name)


# --- API --------------------------------------------------------------------

def _classify(rho: float) -> dict:
    elevated = rho > _BAND["enter"]
    return {
        "correlation": rho,
        "regime": "elevated" if elevated else "normal",
        "enter_threshold": round(_BAND["enter"], 4),
        "exit_threshold": round(_BAND["exit"], 4),
        "baseline_correlation": _READING["baseline_correlation"],
        "note": ("above the entry threshold, the diversifying relationship is "
                 "impaired" if elevated else
                 "below the entry threshold, the diversifying relationship holds"),
    }


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "as_of": _READING["as_of"],
                    "model_loaded": True})


@app.route("/reading", methods=["GET"])
def reading():
    return jsonify(_READING)


@app.route("/predict", methods=["POST"])
def predict_post():
    body = request.get_json(silent=True)
    if not body or "correlation" not in body:
        return jsonify({"error": "request body must be JSON with a 'correlation' key"}), 400
    try:
        rho = float(body["correlation"])
    except (TypeError, ValueError):
        return jsonify({"error": "'correlation' must be a number"}), 400
    if not -1.0 <= rho <= 1.0:
        return jsonify({"error": "'correlation' must lie between -1 and 1"}), 400
    return jsonify(_classify(rho))


@app.route("/predict/<rho>", methods=["GET"])
def predict_get(rho):
    try:
        value = float(rho)
    except ValueError:
        return jsonify({"error": "path parameter must be a number"}), 400
    if not -1.0 <= value <= 1.0:
        return jsonify({"error": "correlation must lie between -1 and 1"}), 400
    return jsonify(_classify(value))


@app.route("/history", methods=["GET"])
def history():
    try:
        rows = _annual_rows()
        start = int(request.args.get("start", rows[0]["year"]))
        end = int(request.args.get("end", rows[-1]["year"]))
    except ValueError:
        return jsonify({"error": "start and end must be four-digit years"}), 400

    annual = {
        r["year"]: {
            "mean_correlation": round(r["corr"], 4),
            "diversification_ratio": round(r["dr"], 4),
            "flagged_days": r["flagged"],
            "trading_days": r["days"],
        }
        for r in rows if start <= r["year"] <= end
    }
    if not annual:
        return jsonify({"error": f"no data in range {start}-{end}"}), 400
    return jsonify({"pair": _RESULT["pair"], "annual": annual})


if __name__ == "__main__":
    app.run(port=5055)
