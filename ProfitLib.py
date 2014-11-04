#!/usr/bin/env python
# coding=iso-8859-1

# ProfitLib.py: mining profitability library
#
# Copyright © 2014 Scott Alfter
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import bitcoinrpc
import jsonrpc
import sys
from decimal import *
sys.path.insert(0, './PyCryptsy/')
from PyCryptsy import PyCryptsy

class ProfitLib:

  # store config dictionary, init output dictionary, and initialize PyCryptsy

  def __init__(self, daemons, credentials):
    self.daemons=daemons
    self.out={}
    self.api=PyCryptsy(str(credentials["cryptsy"]["pubkey"]), str(credentials["cryptsy"]["privkey"]))

  # get latest profitability info

  def Calculate(self):
    self.mkts=self.api.GetMarketIDs("BTC") # update market rates
    for i, coin in enumerate(self.daemons):
      print coin
      if (self.daemons[coin]["active"]==1): # only check active configs
        url="http://"+self.daemons[coin]["username"]+":"+self.daemons[coin]["passwd"]+"@"+self.daemons[coin]["host"]+":"+str(self.daemons[coin]["port"])
        hashrate=Decimal(self.daemons[coin]["hashespersec"]) # our hashrate
        self.out[coin]={}
      
        # connect to coind
         
        b=jsonrpc.ServiceProxy(url)
    
        # get block reward, including transaction fees
        # note #1: Novacoin (and coins derived from it?) report
        #          1% of actual value here
        # note #2: Namecoin doesn't support getblocktemplate, so get 
        #          coinbase value from last block
        # note #3: PPCoin doesn't want any parameters passed to
        #          getblocktemplate.  Bitcoin requires at least 
        #          an empty dictionary to be passed.  Others don't
        #          care.
    
        reward=Decimal(0)
        try:
          reward=Decimal(b.getblocktemplate()["coinbasevalue"])
        except:
          pass
          
        if (reward==0):
          try:
            reward=Decimal(b.getblocktemplate({})["coinbasevalue"])
          except:
            pass

        if (reward==0):            
          try:
            vouts=b.decoderawtransaction(b.getrawtransaction(b.getblock(b.getblockhash(b.getblockcount()))["tx"][0]))["vout"]
            for j, vout in enumerate(vouts):
              reward+=vout["value"]
          except:
            pass
              
        if (coin=="NVC" or coin=="DEM" or coin=="OSC"):
          reward*=100
    
        # get proof-of-work difficulty
        # try getmininginfo first to minimize RPC calls; only use
        # getdifficulty if we must (as with NMC)
    
        algo=self.daemons[coin]["algo"]
        if (algo=="sha256"):
          algo="sha256d"
        try:
          mining_info=b.getmininginfo()
          diff=mining_info["difficulty_"+algo] # for MYR & other multi-algo coins
        except:
          try:
            diff=mining_info["difficulty"]
          except:
            diff=b.getdifficulty()
            if (type(diff) is dict):
              diff=diff["proof-of-work"]
    
        # get network hashrate
        # note 1: Novacoin reports this in MH/s, not H/s
        # note 2: Namecoin and Unobtanium don't report network hashrate, so 
        #         return 0 (it's only informational anyway)
                    
        try:
          nethashrate=mining_info["networkhashps"]
        except:
          try:
            nethashrate=int(mining_info["netmhashps"]*1000000)
          except:
            nethashrate=0
    
        # ported from my C# implementation at
        # https://github.com/salfter/CoinProfitability/blob/master/CoinProfitabilityLibrary/Profitability.cs

        interval=Decimal(86400) # 1 day
        target=Decimal(((65535<<208)*100000000000)/(diff*100000000000))
        revenue=Decimal(interval*target*hashrate*reward/(1<<256))

        # write to output dictionary

        self.out[coin]["reward"]=int(reward)
        self.out[coin]["difficulty"]=float(diff.quantize(Decimal("1.00000000")))
        self.out[coin]["nethashespersec"]=int(nethashrate)
        self.out[coin]["daily_revenue"]=int(revenue)
 
        # if not Bitcoin, get exchange rate and BTC equivalent
 
        if (coin!="BTC"):
          exch=self.api.GetBuyPriceByID(self.mkts[coin])
          self.out[coin]["exchrate"]=float(Decimal(exch).quantize(Decimal("1.00000000")))
          self.out[coin]["daily_revenue_btc"]=int(Decimal(revenue*Decimal(exch)))
        else:
          self.out[coin]["exchrate"]=float(Decimal(100000000).quantize(Decimal("1.00000000")))
          self.out[coin]["daily_revenue_btc"]=int(revenue)

        # copy these informational values from config dictionary

        self.out[coin]["algo"]=self.daemons[coin]["algo"]
        self.out[coin]["merged"]=self.daemons[coin]["merged"]
          
    return self.out

