# Created: 2026-10-09 22:09 JST
"""Render nine OHLCV + EMA/RCI panels to one dark PNG per currency pair."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpecFromSubplotSpec
from matplotlib.ticker import MaxNLocator
import numpy as np
from .indicators import add_indicators
from .config import EXPECTED_TIMEFRAMES

BG = '#131722'
GRID = '#2a2e39'
FG = '#d1d4dc'
UP = '#089981'
DOWN = '#f23645'
EMA_COLORS = ('#2962ff', '#ff9800', '#e91e63')
RCI_COLORS = ('#00bcd4', '#ffeb3b', '#ab47bc')


def _axes_style(ax):
    ax.set_facecolor(BG)
    ax.tick_params(colors='#a1a4ad', labelsize=6, length=2)
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.grid(True, color=GRID, linewidth=0.6, alpha=0.8)
    ax.yaxis.tick_right()
    ax.set_axisbelow(True)


def render_pair(bars, pair, dest, cfg, timestamp, demo=False):
    chart = cfg['chart']
    fig = plt.figure(figsize=tuple(chart['figsize']), facecolor=BG)
    outer = fig.add_gridspec(5, 2, top=.965, bottom=.032, left=.025, right=.975,
                            hspace=.33, wspace=.15)
    fig.suptitle(f'{pair}  |  MULTI-TIMEFRAME  |  {timestamp} JST' + ('  |  SYNTHETIC DEMO DATA' if demo else ''),
                 color=FG, size=17, y=.992)
    for idx, tf in enumerate(EXPECTED_TIMEFRAMES):
        data = add_indicators(bars[tf], chart['ema'], chart['rci']).tail(chart['bars'])
        pos = outer[idx // 2, idx % 2]
        nested = GridSpecFromSubplotSpec(2, 1, subplot_spec=pos,
                                         height_ratios=[3, 1], hspace=.05)
        ax = fig.add_subplot(nested[0]); osc = fig.add_subplot(nested[1], sharex=ax)
        for a in (ax, osc):
            _axes_style(a)
        x = np.arange(len(data)); op = data['Open'].to_numpy(); cl = data['Close'].to_numpy()
        hi = data['High'].to_numpy(); lo = data['Low'].to_numpy()
        colors = np.where(cl >= op, UP, DOWN)
        ax.vlines(x, lo, hi, color=colors, linewidth=.65)
        ax.bar(x, np.maximum(abs(cl - op), 0.000001), bottom=np.minimum(cl, op),
               width=.65, color=colors, linewidth=0)
        for j, n in enumerate(chart['ema']):
            ax.plot(x, data[f'EMA{n}'].to_numpy(), linewidth=.95, color=EMA_COLORS[j], label=f'EMA {n}')
        for j, n in enumerate(chart['rci']):
            osc.plot(x, data[f'RCI{n}'].to_numpy(), linewidth=.88, color=RCI_COLORS[j], label=f'RCI {n}')
        osc.set_ylim(-108, 108)
        osc.set_yticks([-100, 0, 100])
        osc.axhline(80, color='#666b76', linewidth=.7, linestyle='--')
        osc.axhline(-80, color='#666b76', linewidth=.7, linestyle='--')
        ax.set_xlim(-1, len(data))
        ax.yaxis.set_major_locator(MaxNLocator(5))
        ax.set_title(f'{tf}  |  Close: {cl[-1]:.5f}', loc='left', color=FG, fontsize=10, pad=4)
        ax.legend(loc='upper left', fontsize=6, frameon=False, labelcolor=FG, ncol=3,
                  bbox_to_anchor=(.001, 1.0))
        osc.legend(loc='upper left', fontsize=6, frameon=False, labelcolor=FG, ncol=3)
        ticks = np.linspace(0, len(data)-1, num=4, dtype=int)
        tz = chart['timezone']
        osc.set_xticks(ticks)
        osc.set_xticklabels(data.index.tz_convert(tz)[ticks].strftime('%m/%d %H:%M'), fontsize=6)
        plt.setp(ax.get_xticklabels(), visible=False)
    info = fig.add_subplot(outer[4, 1]); info.set_facecolor(BG); info.axis('off')
    details = [
        'CHART INFORMATION', '', f'PAIR                 {pair}',
        f'GENERATED       {timestamp} JST', 'TIMEFRAMES       9',
        'EMA                   20 / 30 / 40', 'RCI                      9 / 14 / 26',
        'LAYOUT             2 columns / 5 rows',
        '8H BAR              UTC-anchored 4H aggregation',
        'SOURCE             ' + ('SYNTHETIC DEMO (NOT MARKET DATA)' if demo else 'TradingView MCP'),
        '', 'Times and calculations may differ from TradingView UI',
    ]
    info.text(.08, .88, '\n'.join(details), color=FG, fontsize=10, linespacing=1.7,
              ha='left', va='top', family='monospace')
    dst = Path(dest); dst.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(dst, dpi=chart['dpi'], facecolor=BG, bbox_inches=None)
    plt.close(fig)
    return dst
