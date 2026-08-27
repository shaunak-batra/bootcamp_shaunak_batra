from __future__ import annotations

import numpy as np


def mean_impute(a: np.ndarray) -> np.ndarray:
    m = np.nanmean(a)
    out = a.copy()
    out[np.isnan(out)] = m
    return out


def median_impute(a: np.ndarray) -> np.ndarray:
    m = np.nanmedian(a)
    out = a.copy()
    out[np.isnan(out)] = m
    return out


class SimpleLinReg:
    """Minimal OLS via the pseudoinverse, no external dependency."""

    def fit(self, X, y):
        X1 = np.c_[np.ones(len(X)), X.ravel()]
        beta = np.linalg.pinv(X1) @ y
        self.intercept_, self.coef_ = float(beta[0]), np.array([float(beta[1])])
        return self

    def predict(self, X):
        return self.intercept_ + self.coef_[0] * X.ravel()


def mae(y_true, y_pred) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def fit_fn(X, y) -> SimpleLinReg:
    return SimpleLinReg().fit(X, y)


def pred_fn(model, X):
    return model.predict(X)


def bootstrap_metric(y_true, y_pred, fn, n_boot: int = 500, seed: int = 111, alpha: float = 0.05) -> dict:
    """Percentile bootstrap CI for a metric fn(y_true, y_pred), resampling rows jointly."""
    rng = np.random.default_rng(seed)
    idx = np.arange(len(y_true))
    stats = []
    for _ in range(n_boot):
        b = rng.choice(idx, size=len(idx), replace=True)
        stats.append(fn(y_true[b], y_pred[b]))
    lo, hi = np.percentile(stats, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {"mean": float(np.mean(stats)), "lo": float(lo), "hi": float(hi)}


def bootstrap_predictions(X, y, x_grid, n_boot: int = 500, seed: int = 111):
    """Refit on n_boot resamples of (X, y) and return the mean/2.5%/97.5% predicted line over x_grid."""
    rng = np.random.default_rng(seed)
    preds = []
    idx = np.arange(len(y))
    for _ in range(n_boot):
        b = rng.choice(idx, size=len(idx), replace=True)
        m = fit_fn(X[b].reshape(-1, 1), y[b])
        preds.append(m.predict(x_grid))
    P = np.vstack(preds)
    return P.mean(axis=0), np.percentile(P, 2.5, axis=0), np.percentile(P, 97.5, axis=0)
