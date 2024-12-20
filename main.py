import os, sys, urllib.request, urllib.error, urllib.parse, http.client, json
import array
import ROOT

from json_handler import dqm_get_json


serverurl = 'https://cmsweb.cern.ch/dqm/offline'


run = '387474'
dataset = '/StreamExpress/Run2024J-Express-v1/DQMIO/'
folder = 'EcalBarrel/EBSummaryClient/'
plotname = "EBTMT timing mean 1D summary"
data = dqm_get_json(serverurl, run, dataset, folder, plotname)

h = ROOT.TBufferJSON.ConvertFromJSON(str(data))
h.Print()
h.Draw()
