# Created: 2026-10-10 JST
"""Read-only Saxo chart API adapter. Never call trading/order endpoints."""
import pandas as pd
import requests
from .providers import validate_bars
from .saxo_auth import SaxoSession

BASE = {'sim':'https://gateway.saxobank.com/sim/openapi/',
        'live':'https://gateway.saxobank.com/openapi/'}
HORIZONS = {'1M': 1, '5M':5, '15M':15, '1H':60,
            '4H':240, '8H':480, '1D':1440, '1W':10080, '1Mn':43200}


def parse_saxo_chart(payload, side='bid'):
    if side not in ('bid','ask'):
        raise ValueError('saxo.price_side must be bid or ask')
    data=payload.get('Data') if isinstance(payload,dict) else None
    if not isinstance(data,list) or not data:
        raise ValueError('Saxo chart response has no Data samples')
    suffix='Bid' if side == 'bid' else 'Ask'
    rows=[]
    for sample in data:
        try:
            dt=pd.to_datetime(sample['Time'], utc=True)
            rows.append({'Time':dt,'Open':float(sample['Open'+suffix]),
                         'High':float(sample['High'+suffix]),
                         'Low':float(sample['Low'+suffix]),
                         'Close':float(sample['Close'+suffix]),
                         'Volume':float(sample.get('Volume') or 0)})
        except (KeyError,TypeError,ValueError) as exc:
            raise ValueError('Saxo chart is missing required Bid/Ask OHLC values') from exc
    return validate_bars(pd.DataFrame(rows).set_index('Time'))


def select_uic(payload, pair):
    rows=payload.get('Data',[]) if isinstance(payload,dict) else []
    matches=[i for i in rows if i.get('AssetType')=='FxSpot' and
             str(i.get('Symbol','')).replace('/','').upper() == pair.upper()]
    if len(matches)!=1:
        raise ValueError(f'Saxo FxSpot {pair} instrument not uniquely found; check account market access')
    return int(matches[0]['Identifier'])


class SaxoProvider:
    """Fetches chart samples and resolves per-account FX instrument IDs."""
    def __init__(self, cfg, session=None, http=None):
        if cfg['saxo']['environment'] not in BASE:
            raise ValueError('Saxo environment must be sim or live')
        self.environment=cfg['saxo']['environment']
        self.base=BASE[self.environment]
        self.side=cfg['saxo'].get('price_side','bid')
        self.session=session or SaxoSession(cfg)
        self.http=http or requests.Session()
        self.uics={}

    def _get(self,endpoint, params):
        token=self.session.access_token()
        res=self.http.get(self.base+endpoint,params=params,
                          headers={'Authorization': 'Bearer '+token,
                                   'Accept':'application/json'},timeout=30)
        res.raise_for_status()
        return res.json()

    def resolve(self,pair):
        if pair not in self.uics:
            payload=self._get('ref/v1/instruments',
                              {'Keywords':pair, 'AssetTypes':'FxSpot', '$top':100})
            self.uics[pair]=select_uic(payload,pair)
        return self.uics[pair]

    def get(self,pair,timeframe,count):
        if timeframe not in HORIZONS:
            raise ValueError('Unsupported Saxo timeframe')
        if not 1<=count<=1200:
            raise ValueError('Saxo chart count must be within 1..1200')
        payload=self._get('chart/v3/charts',{'AssetType':'FxSpot',
                             'Uic':self.resolve(pair),'Horizon':HORIZONS[timeframe],
                             'Count':count, 'FieldGroups':'Data'})
        return parse_saxo_chart(payload,self.side)
