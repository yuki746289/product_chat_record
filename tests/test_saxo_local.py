# Created: 2026-10-10 JST
"""Network-free Saxo SIM contract / OAuth / scheduling tests."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pandas as pd
import pytest
from src.saxo_auth import SaxoSession, SaxoLoginRequired, make_authorize_url, save_credentials, local_redirect_uri
from src.saxo_provider import HORIZONS, parse_saxo_chart, select_uic, SaxoProvider
from src.saxo_local import tick_once
from src.config import load_settings
from src.providers import DemoProvider

ROOT=Path(__file__).resolve().parents[1]


class Vault:
    def __init__(self):self.data={}
    def set_password(self, service,user,password):self.data[(service,user)]=password
    def get_password(self,service,user):return self.data.get((service,user))


class Response:
    def __init__(self,json_result,status=200):self.payload=json_result;self.status_code=status
    def json(self):return self.payload
    def raise_for_status(self):
        if self.status_code >=400:
            from requests import HTTPError
            raise HTTPError('HTTP error', response=self)


def cfg():
    a=load_settings(ROOT/'setting.yaml')
    assert a['saxo']['environment']=='sim'
    return a


def test_saxo_timeframes_and_8h_native():
    assert [HORIZONS[x] for x in ('1M','5M','15M','1H','4H','8H','1D','1W','1Mn')]==[1,5,15,60,240,480,1440,10080,43200]


def test_saxo_chart_bid_and_ask():
    data={'Data': [{'Time':'2026-10-09T13:00:00Z','OpenBid':150,'HighBid':151,'LowBid':149,'CloseBid':150.5,
                   'OpenAsk':150.1,'HighAsk':151.1,'LowAsk':149.1,'CloseAsk':150.6},
                  {'Time':'2026-10-09T13:01:00Z','OpenBid':150.5,'HighBid':152,'LowBid':150,'CloseBid':151.5,
                   'OpenAsk':150.6,'HighAsk':152.1,'LowAsk':150.1,'CloseAsk':151.6}]}
    bid=parse_saxo_chart(data,'bid')
    ask=parse_saxo_chart(data,'ask')
    assert len(bid)==2 and bid.iloc[0].Open==150
    assert ask.iloc[0].Open==150.1
    assert (bid.Volume==0).all()
    assert str(bid.index.tz)=='UTC'


def test_saxo_reject_missing_side_fields():
    with pytest.raises(ValueError,match='required'):
        parse_saxo_chart({'Data':[{'Time':'2026-10-09T13:00:00Z','Open':1,'High':2,'Low':0,'Close':1}]},'bid')


def test_fxspot_instrument_matching():
    data={'Data':[{'Symbol':'USDJPY','Identifier':17,'AssetType':'FxSpot'},
                  {'Symbol':'USDJPY','Identifier':18,'AssetType':'FxForwards'}]}
    assert select_uic(data,'USDJPY')==17
    with pytest.raises(ValueError,match='not uniquely'):
        select_uic({'Data':[]},'USDJPY')


def test_authorization_code_url_and_local_redirect():
    c=cfg();c['saxo']['redirect_uri']='http://localhost:8765/callback'
    uri=local_redirect_uri(c)
    url=make_authorize_url('sim','APP_KEY',uri,'CSRF_STATE')
    assert 'client_id=APP_KEY' in url and 'state=CSRF_STATE' in url and 'response_type=code' in url
    c['saxo']['redirect_uri']='https://example.com/callback'
    with pytest.raises(ValueError):local_redirect_uri(c)


def test_oauth_exchange_and_rotation():
    vault=Vault(); save_credentials('sim','TEST_ID','TEST_SECRET',vault)
    http=Mock()
    http.post.side_effect=[Response({'access_token':'ACCESS_A','refresh_token':'REFRESH_A','expires_in':100,'refresh_token_expires_in':2400}),
                           Response({'access_token':'ACCESS_B','refresh_token':'REFRESH_B','expires_in':1200,'refresh_token_expires_in':2400})]
    now=[100000]
    session=SaxoSession(cfg(),vault=vault,http=http,clock=lambda:now[0])
    session.exchange_code('authorization-code')
    assert session.access_token()=='ACCESS_B'  # access A expires in 100s, refreshes proactively
    assert session.read_tokens()['refresh_token']=='REFRESH_B'
    now[0]+=10
    assert session.access_token()=='ACCESS_B'
    assert http.post.call_count==2
    assert http.post.call_args_list[1].kwargs['data']['refresh_token']=='REFRESH_A'
    assert vault.get_password(session.service,'app_secret')=='TEST_SECRET'


def test_refresh_token_expiry_requires_manual_login():
    vault=Vault();save_credentials('sim','KEY','SECRET',vault)
    session=SaxoSession(cfg(),vault=vault,clock=lambda:1000)
    vault.set_password(session.service,'tokens',json.dumps({'access_token':'OLD','refresh_token':'OLD_R',
        'access_expires_at':900,'refresh_expires_at':999}))
    with pytest.raises(SaxoLoginRequired,match='browser login'):
        session.access_token()


def _stub_source(now,has_new=True):
    class Source:
        def __init__(self):
            self.calls=[]
            self.session=SimpleNamespace(access_token=lambda:'FAKE')
        def get(self,pair,tf,count):
            self.calls.append((pair,tf))
            from src.providers import FREQUENCIES
            df=DemoProvider().get('FX:'+pair,tf,count)
            # Only newest minute candle freshness is used in this gate.
            if tf=='1M':
                end=now-timedelta(minutes=2 if has_new else 200)
                df.index=pd.date_range(end=end,periods=len(df),freq='min',tz='UTC')
            return df
    return Source()


def test_local_halfhour_generation_and_dedupe(tmp_path,monkeypatch):
    import yaml
    from src import saxo_local
    setting=cfg();setting['saxo']['enabled']=True
    setting['symbols']=setting['symbols'][:1]
    setting['output']['local_dir']=str(tmp_path/'output')
    cp=tmp_path/'setting.yaml';cp.write_text(yaml.safe_dump(setting),encoding='utf-8')
    now=datetime(2026,10,9,6,2,tzinfo=timezone.utc)
    provider=_stub_source(now)
    calls=[]
    def fake_render(frames,pair,dest,cfg,timestamp,**kwargs):
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(b'\x89PNG\r\n\x1a\n1234')
        calls.append((pair,timestamp,kwargs))
        return dest
    monkeypatch.setattr(saxo_local,'render_pair',fake_render)
    a=tick_once(cp,now,provider)
    assert len(a)==1 and a[0].is_file() and a[0].parent.parent.name=='20261009_1500'
    assert len(provider.calls)==9 and ('GBPAUD','8H') in provider.calls
    assert calls[0][2]['source_label']=='Saxo SIM BID'
    assert tick_once(cp,now+timedelta(minutes=1),provider)==[]
    assert len(provider.calls)==9  # no extra market requests on same slot
    assert len(tick_once(cp,now+timedelta(minutes=31),_stub_source(now+timedelta(minutes=31))))==1


def test_local_closed_market_makes_no_png(tmp_path):
    import yaml
    conf=cfg();conf['saxo']['enabled']=True;conf['symbols']=conf['symbols'][:1]
    conf['output']['local_dir']=str(tmp_path/'output')
    cp=tmp_path/'setting.yaml';cp.write_text(yaml.safe_dump(conf),encoding='utf-8')
    now=datetime(2026,10,10,6,2,tzinfo=timezone.utc)
    src=_stub_source(now,has_new=False)
    assert tick_once(cp,now,src)==[]
    assert not list((tmp_path/'output').rglob('*.png'))
    assert src.calls==[('GBPAUD','1M')]


def test_full_saxo_snapshot_creates_valid_png(tmp_path):
    import yaml
    from PIL import Image
    settings=cfg();settings['saxo']['enabled']=True;settings['symbols']=settings['symbols'][:1]
    settings['output']['local_dir']=str(tmp_path/'images')
    settings['chart']['figsize']=[12,16]
    settings['chart']['dpi']=50
    cp=tmp_path/'settings.yaml'
    cp.write_text(yaml.safe_dump(settings),encoding='utf-8')
    now=datetime(2026,10,9,6,2,tzinfo=timezone.utc)
    images=tick_once(cp,now,_stub_source(now))
    assert len(images)==1
    with Image.open(images[0]) as png:
        assert png.format=='PNG' and png.width>400 and png.height>400
