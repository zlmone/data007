#!/usr/bin/env python
# -*- coding: utf-8 -*-
from models import db
from aggregator.indexes import BrandIndex
from aggregator.processes import Process
from aggregator.esindex import index_brand
from settings import ENV

from datetime import datetime, timedelta

import json
import traceback

defaultdate = (datetime.utcnow()+timedelta(hours=-16)).strftime("%Y-%m-%d")

def es_brands(brands, date=None):
    try:
        if date is None:
            date = defaultdate
        bi = BrandIndex(date)
        for brand in brands:
            try:
                es_brand(bi, date, brand)
            except:
                traceback.print_exc()
    except:
        traceback.print_exc()

def es_brand(bi, date, brand):
    if brand == '':
        brand = '其他'
    
    d0 = (datetime.strptime(date, '%Y-%m-%d')-timedelta(days=1)).strftime('%Y-%m-%d')
    cates = bi.getcates(brand)
    c1s = list(set([c[0] for c in cates]))
    c2s = list(set([c[1] for c in cates]))
    shops = items = deals = sales = delta = 0
    for c1 in c1s:
        brandinfo = bi.getinfo(brand, c1, 'all')
        shops += int(brandinfo.get('shops', 0))
        items += int(brandinfo.get('items', 0))
        deals += int(brandinfo.get('deals', 0))
        sales += float(brandinfo.get('sales', 0))
        delta += float(brandinfo.get('delta_sales', 0))
    cate1 = [str(c) for c in c1s]
    cate2 = [str(c) for c in c2s]
    r = db.execute('select logo from ataobao2.brand where name=:name', dict(name=brand), result=True)
    try:
        logo = r.results[0][0]
    except:
        logo = ''

    info = {
        'title': brand,
        'cate1': cate1,
        'cate2': cate2,
        'logo': logo,
        'shops': shops,
        'items': items,
        'deals': deals,
        'sales': sales,
        'delta': delta,
    }

    index_brand(brand, info)


class BrandESProcess(Process):
    def __init__(self, date=None):
        super(BrandESProcess, self).__init__('brandes')
        if ENV == 'DEV':
            self.step = 100
        else:
            self.step = 1000
        self.date = date

    def generate_tasks(self):
        self.clear_redis()
        bi = BrandIndex(self.date)
        from aggregator.brands import brands as brands1
        brands2 = set(b.decode('utf-8') for b in bi.getbrands())
        brands = list(brands1 & brands2)
        for i in range(len(brands)/self.step):
            self.add_task('aggregator.brandes.es_brands', brands[self.step*i:self.step*(i+1)], date=self.date)
        self.finish_generation()

bep = BrandESProcess()

if __name__ == '__main__':
    bep.date = '2013-12-04'
    bep.start()