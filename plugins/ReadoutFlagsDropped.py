import os, sys, urllib.request, urllib.error, urllib.parse, http.client
import ROOT
import json
import pandas as pd
import numpy as np
from array import array

from Plugin import Plugin



class ReadoutFlagsDropped(Plugin):
    def __init__(self, buildopener):
        Plugin.__init__(self, buildopener, folder="", plot_name="")

    #process single run, all the supermodules for both barrel and endcap
    def process_one_run(self, run_info):
        df = pd.read_csv("/eos/user/d/delvecch/www/PFG/ecalchannels.csv")
        
        
