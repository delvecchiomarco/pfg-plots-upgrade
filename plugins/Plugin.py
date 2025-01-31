import os, sys, urllib.request, urllib.error, urllib.parse, http.client
import ROOT
import json

from json_handler import dqm_get_json



class Plugin:
    def __init__(self, buildopener, folder=None, plot_name=None):
        self._data = {}
        self.buildopener = buildopener
        self.folder = folder  #given in the specific class
        self.plot_name = plot_name  #given in the specific class
        self.serverurl_online = " " #given in the specific class
        
    #take the json from the DQM and converting into a root object
    def get_root_object(self, run_info, serverurl_online):
        json_object = dqm_get_json(self.buildopener, run_info["run"], run_info["dataset"], self.folder, self.plot_name, serverurl_online)
        return ROOT.TBufferJSON.ConvertFromJSON(str(json_object))

    
    #fill the _data dict with the one run data
    def fill_data_one_run(self, run_info, one_run_data):
        self._data[run_info["run"]] = one_run_data

        
    #get the one run data giving the run number
    def get_data_one_run(self, run):
        return self._data[run]

    
    #list of all the available runs
    def get_available_runs(self):
        return self._data.keys()
