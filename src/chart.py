# Created: 2026-10-09 22:09 JST
"""Render configurable OHLCV + EMA/RCI panels to one PNG per currency pair."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpecFromSubplotSpec
from matplotlib.ticker import MaxNLocator
import numpy as np
from .indicators import add_indicators

BG = '#131722'
GRID = '#2a2e39'
FG = '#d1d4dc'
UP = '#089981'
DOWN = '#f23645'
EMA_COLORS = ('#2962ff', '#ff9800', '#e91e63')
RCI_COLORS = ('#00bcd4', '#ffeb3b', '#ab47bc')


def _axes_style(ax, bg, grid, tick):
    ax.set_facecolor(bg)
    ax.tick_params(colors=tick, labelsize=6, length=2)
    for s in ax.spines.values():
        s.set_color(grid)
    ax.grid(True, color=grid, linewidth=0.6, alpha=0.8)
    ax.yaxis.tick_right()
    ax.set_axisbelow(True)


def render_pair(bars, pair, dest, cfg, timestamp, demo=False, source_label=None, eight_hour_label=None):
    chart = cfg['chart']
    timeframes = chart['timeframes']
    columns = chart['columns']
    rows = (len(timeframes) + 1 + columns - 1) // columns
    light = chart.get('theme', 'dark') == 'light'
    bg = '#ffffff' if light else BG
    grid = '#d4d9e1' if light else GRID
    fg = '#19212d' if light else FG
    up = '#16855a' if light else UP
    down = '#d13e43' if light else DOWN
    right_padding_bars = chart.get('right_padding_bars', 12)
    fig = plt.figure(figsize=tuple(chart['figsize']), facecolor=bg)
    outer = fig.add_gridspec(rows, columns, top=.965, bottom=.032, left=.025, right=.975,
                            hspace=.33, wspace=.15)
    fig.suptitle(f'{pair}  |  MULTI-TIMEFRAME  |  {timestamp} {cfg["output"]["timezone"]}' + ('  |  SYNTHETIC DEMO DATA' if demo else ''),
                 color=fg, size=17, y=.992)
    for idx, tf in enumerate(timeframes):
        data = add_indicators(bars[tf], chart['ema'], chart['rci']).tail(chart['bars'])
        pos = outer[idx // columns, idx % columns]
        nested = GridSpecFromSubplotSpec(2, 1, subplot_spec=pos,
                                         height_ratios=[3, 1], hspace=.05)
        ax = fig.add_subplot(nested[0]); osc = fig.add_subplot(nested[1], sharex=ax)
        for a in (ax, osc):
            _axes_style(a, bg, grid, '#687386' if light else '#a1a4ad')
        x = np.arange(len(data)); op = data['Open'].to_numpy(); cl = data['Close'].to_numpy()
        hi = data['High'].to_numpy(); lo = data['Low'].to_numpy()
        colors = np.where(cl >= op, up, down)
        ax.vlines(x, lo, hi, color=colors, linewidth=.65)
        ax.bar(x, np.maximum(abs(cl - op), 0.000001), bottom=np.minimum(cl, op),
               width=.65, color=colors, linewidth=0)
        for j, n in enumerate(chart['ema']):
            ax.plot(x, data[f'EMA{n}'].to_numpy(), linewidth=.95, color=EMA_COLORS[j] if j < len(EMA_COLORS) else plt.get_cmap('tab20')(j % 20), label=f'EMA {n}')
        for j, n in enumerate(chart['rci']):
            osc.plot(x, data[f'RCI{n}'].to_numpy(), linewidth=.88, color=RCI_COLORS[j] if j < len(RCI_COLORS) else plt.get_cmap('tab20')((j + 8) % 20), label=f'RCI {n}')
        osc.set_ylim(-108, 108)
        osc.set_yticks([-100, 0, 100])
        osc.axhline(80, color='#666b76', linewidth=.7, linestyle='--')
        osc.axhline(-80, color='#666b76', linewidth=.7, linestyle='--')
        ax.set_xlim(-1, (len(data) - 1) + right_padding_bars)
        ax.yaxis.set_major_locator(MaxNLocator(5))
        ax.set_title(f'{tf}  |  Close: {cl[-1]:.5f}', loc='left', color=fg, fontsize=10, pad=4)
        ax.legend(loc='upper left', fontsize=6, frameon=False, labelcolor=fg, ncol=min(3, len(chart['ema'])),
                  bbox_to_anchor=(.001, 1.0))
        osc.legend(loc='upper left', fontsize=6, frameon=False, labelcolor=fg, ncol=min(3, len(chart['rci'])))
        ticks = np.linspace(0, len(data)-1, num=4, dtype=int)
        tz = chart['timezone']
        osc.set_xticks(ticks)
        osc.set_xticklabels(data.index.tz_convert(tz)[ticks].strftime('%m/%d %H:%M'), fontsize=6)
        plt.setp(ax.get_xticklabels(), visible=False)
    info = fig.add_subplot(outer[len(timeframes) // columns, len(timeframes) % columns]); info.set_facecolor(bg); info.axis('off')
    details = [
        'CHART INFORMATION', '', f'PAIR                 {pair}',
        f'GENERATED       {timestamp} {cfg["output"]["timezone"]}', f'TIMEFRAMES       {len(timeframes)}',
        'EMA                   ' + ' / '.join(map(str, chart['ema'])),
        'RCI                      ' + ' / '.join(map(str, chart['rci'])),
        f'LAYOUT             {columns} columns / {rows} rows',
        f'RIGHT MARGIN   {right_padding_bars} bars',
        '8H BAR              ' + (eight_hour_label or 'UTC-anchored 4H aggregation'),
        'SOURCE             ' + ('SYNTHETIC DEMO (NOT MARKET DATA)' if demo else (source_label or 'TradingView MCP')),
        '', 'Times and calculations may differ from TradingView UI',
    ]
    info.text(.08, .88, '\n'.join(details), color=fg, fontsize=10, linespacing=1.7,
              ha='left', va='top', family='monospace')
    dst = Path(dest); dst.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(dst, dpi=chart['dpi'], facecolor=bg, bbox_inches=None)
    plt.close(fig)
    return dst
