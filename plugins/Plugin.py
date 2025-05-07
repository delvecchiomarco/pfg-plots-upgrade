import os, sys, urllib.request, urllib.error, urllib.parse, http.client
import ROOT
import json
import cppyy
import pandas as pd
import numpy as np

from json_handler import dqm_get_json

palette_inverted = False

class Plugin:
    def __init__(self, buildopener, folder=None, plot_name=None):
        self._data = {}
        self.buildopener = buildopener
        self.folder = folder  #given in the specific class
        self.plot_name = plot_name  #given in the specific class
        self.serverurl_online = " " #given in the specific class

        with open(f"{os.path.dirname(os.path.realpath(__file__))}/../conf.json", "r") as file:
          data = json.load(file)
        self.ecal_channels_csv_path = data["ChannelsCsvPath"]

    #take the json from the DQM and converting into a root object
    def get_root_object(self, run_info):
        json_str = dqm_get_json(self.buildopener, run_info["run"], run_info["dataset"], self.folder, self.plot_name)
        try:
            obj = ROOT.TBufferJSON.ConvertFromJSON(str(json_str))
        except cppyy.gbl.nlohmann.detail.out_of_range:
            json_object = json.loads(json_str)
            json_object["fZmax"] = 1e+10
            json_object["fZmin"] = 0
            obj = ROOT.TBufferJSON.ConvertFromJSON(json.dumps(json_object))
        filename = "/tmp/"+f"plot_{run_info['run']}-{self.folder}-{self.plot_name}.root".replace(' ', '.').replace('/', '.')
        obj.SaveAs(filename)
        return obj

    #fill the _data dict with the one run data
    def fill_data_one_run(self, run_info, one_run_data):
        self._data[run_info["run"]] = one_run_data


    #get the one run data giving the run number
    def get_data_one_run(self, run):
        return self._data[run]

    
    #list of all the available runs
    def get_available_runs(self):
        return self._data.keys()


    def color_scale_settings(self, n_contours):
        global palette_inverted
        ROOT.gStyle.SetNumberContours(n_contours)
        ROOT.gStyle.SetPalette(ROOT.kBeach)
        #switch color palette for the first time
        if not palette_inverted:
            ROOT.TColor.InvertPalette()
            palette_inverted = True


    #filling the history plot with the information in the run_df
    def df_to_hist(self, row, hist, tower_list, run_list):
        hist.Fill(run_list.index(row["run"])+1, tower_list.index(row["label"])+1, row["value"])


    #graphic options for the summary plot
    def hist_config(self, run_list, tower_list, hist, ybin_start, ybin_end, name, save_path, hist_min=0, hist_max=1):
        #axis labels
        for ix, run in enumerate(run_list, start=1):
            hist.GetXaxis().SetBinLabel(ix, str(run))
        for iy in range(ybin_end-ybin_start):
            try:
              hist.GetYaxis().SetBinLabel(iy+1, str(tower_list[ybin_start+iy]))
            except:
              continue
        #canva settings
        canva = ROOT.TCanvas(f"canva_{name}", "", 3600, 2250)
        canva.SetGrid()
        ROOT.gStyle.SetLineColor(ROOT.kGray+1)
        ROOT.gStyle.SetLineStyle(3)
        canva.SetLeftMargin(0.18)
        canva.SetRightMargin(0.12)
        canva.SetTopMargin(0.05)
        canva.SetBottomMargin(0.12)
        #hist settings
        hist.SetStats(False)
        hist.GetXaxis().LabelsOption("v")
        hist.GetXaxis().SetLabelSize(0.04)
        hist.GetYaxis().SetLabelSize(0.04)
        hist.GetZaxis().SetLabelSize(0.04)
        hist.GetXaxis().SetTickLength(0.03)
        hist.GetYaxis().SetTickLength(0.02)
        hist.GetZaxis().SetTickLength(0.02)
        hist.SetMinimum(hist_min)
        hist.SetMaximum(hist_max)
        if len(run_list) <= 10:
            ROOT.gStyle.SetPaintTextFormat(".1e")
            hist.SetMarkerSize(1.5)
            hist.Draw("text COLZ")
        elif len(run_list) <= 20:
            ROOT.gStyle.SetPaintTextFormat(".1e")
            hist.SetMarkerSize(0.8)
            hist.Draw("text COLZ")
        elif len(run_list) <= 25:
            ROOT.gStyle.SetPaintTextFormat(".1e")
            hist.SetMarkerSize(0.5)
            hist.Draw("text COLZ")
        else:
            ROOT.gStyle.SetPaintTextFormat(".1e")
            hist.Draw("COLZ")
        canva.Modified()
        canva.Update()
        #saving
        canva.SaveAs(f"{save_path}{name}.pdf")
        canva.SaveAs(f"{save_path}{name}.png")
        canva.SaveAs(f"{save_path}{name}.root")


    #fill the history plot and divide in subplots
    def fill_history_subplots(self, run_df, available_runs, name, save_path, change_hist_limits=False):
        tower_list = list(pd.unique(run_df.label))
        run_list = list(available_runs)
        hist = ROOT.TH2F(f"{name}", "", len(run_list), 0., len(run_list)+1, len(tower_list), 0., len(tower_list)+1)
        run_df.to_csv(f"{save_path}{name}.csv", index=None)
        run_df.apply(lambda row: self.df_to_hist(row, hist, tower_list, run_list), axis=1)
        #subhistograms if n_rows > 15
        nbinsy = hist.GetNbinsY()
        max_bins = 25
        n_subhist = nbinsy // max_bins + (1 if nbinsy % max_bins > 0 else 0)
        for i in range(n_subhist):
            ybin_start = i * max_bins
            ybin_end = min((i+1) * max_bins, nbinsy)
            subhist = ROOT.TH2F(f"{name}_part{i+1}", "", len(run_list), 0., len(run_list)+1, ybin_end-ybin_start, ybin_start, ybin_end+1)
            for ix in range(len(run_list)):
                for iy in range(ybin_end-ybin_start):
                    subhist.SetBinContent(ix+1, iy+1, hist.GetBinContent(ix+1, ybin_start+iy+1))
            if n_subhist == 1:
                if change_hist_limits:
                    self.hist_config(run_list, tower_list, subhist, ybin_start, ybin_end, f"{name}", f"{save_path}", hist_min=subhist.GetMinimum(), hist_max=subhist.GetMaximum())
                else:
                    self.hist_config(run_list, tower_list, subhist, ybin_start, ybin_end, f"{name}", f"{save_path}")
            else:
                if change_hist_limits:
                    self.hist_config(run_list, tower_list, subhist, ybin_start, ybin_end, f"{name}_part{i+1}", f"{save_path}", hist_min=subhist.GetMinimum(), hist_max=subhist.GetMaximum())
                else:
                    self.hist_config(run_list, tower_list, subhist, ybin_start, ybin_end, f"{name}_part{i+1}", f"{save_path}")
