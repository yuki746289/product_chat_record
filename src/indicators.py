# Created: 2026-10-09 22:09 JST
"""Technical studies; RCI uses Spearman's rank correlation with tie handling."""
import numpy as np
import pandas as pd


def add_indicators(data, ema_periods=(20, 30, 40), rci_periods=(9, 14, 26)):
    df = data.copy()
    close = df['Close'].astype(float)
    for n in ema_periods:
        df[f'EMA{n}'] = close.ewm(span=n, adjust=False, min_periods=n).mean()
    for n in rci_periods:
        x = np.arange(1, n + 1, dtype=float)
        def rci(values):
            rank = pd.Series(values).rank(method='average').to_numpy(dtype=float)
            if np.ptp(rank) == 0:
                return 0.0
            return float(np.corrcoef(x, rank)[0, 1] * 100)
        df[f'RCI{n}'] = close.rolling(n, min_periods=n).apply(rci, raw=True)
    return df
