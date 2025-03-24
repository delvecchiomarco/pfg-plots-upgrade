import os, sys, urllib.request, urllib.error, urllib.parse, http.client
import ROOT
import json
import pandas as pd
import numpy as np

from Plugin import Plugin
import ECAL


def read_hist_EB(one_run_root_object, supermodule, Ichannels, Lchannels):
    nbinsx = one_run_root_object.GetNbinsX()
    nbinsy = one_run_root_object.GetNbinsY()
    sm = int(supermodule[2:])
    if sm < 0:
        for iy in range(1, nbinsy+1):
            for ix in range(1, nbinsx+1):
                x = int(one_run_root_object.GetXaxis().GetBinUpEdge(ix))
                y = int(one_run_root_object.GetYaxis().GetBinUpEdge(iy))
                if isIBlock(sm, one_run_root_object, ix, iy):
                    Ichannels["label"].append(f"{supermodule} [+{y}, -{x}]")
                    Ichannels["value"].append(one_run_root_object.GetBinContent(ix, iy))
                elif isLBlock(sm, one_run_root_object, ix, iy):
                    Lchannels["label"].append(f"{supermodule} [+{y}, -{x}]")
                    Lchannels["value"].append(one_run_root_object.GetBinContent(ix, iy))
    elif sm > 0:
        for iy in range(1, nbinsy+1):
            for ix in range(1, nbinsx+1):
                x = int(one_run_root_object.GetXaxis().GetBinUpEdge(ix))
                y = int(-one_run_root_object.GetYaxis().GetBinLowEdge(iy))
                if isIBlock(sm, one_run_root_object, ix, iy):
                    Ichannels["label"].append(f"{supermodule} [+{y}, +{x}]")
                    Ichannels["value"].append(one_run_root_object.GetBinContent(ix, iy))
                elif isLBlock(sm, one_run_root_object, ix, iy):
                    Lchannels["label"].append(f"{supermodule} [+{y}, +{x}]")
                    Lchannels["value"].append(one_run_root_object.GetBinContent(ix, iy))


def read_hist_EE(one_run_root_object, supermodule, EEchannels):
    nbinsx = one_run_root_object.GetNbinsX()
    nbinsy = one_run_root_object.GetNbinsY()
    for iy in range(1, nbinsy+1):
        for ix in range(1, nbinsx+1):
            if abs(one_run_root_object.GetBinContent(ix, iy)) != 0:
                x = int(one_run_root_object.GetXaxis().GetBinUpEdge(ix))
                y = int(one_run_root_object.GetYaxis().GetBinUpEdge(iy))
                EEchannels["label"].append(f"{supermodule} [+{x}, +{y}]")
                EEchannels["value"].append(one_run_root_object.GetBinContent(ix, iy))
                EEchannels["LightMR"].append(ECAL.EELightMR(x, y))


#check if the channel is in the I region
def isIBlock(sm_num, one_run_root_object, ix, iy):
    a = abs(int(one_run_root_object.GetXaxis().GetBinUpEdge(ix))) > 5
    l1 = abs(sm_num) * 20
    l2 = l1 - 20
    low = l1 if sm_num > 0 else l2
    b = abs(int(-one_run_root_object.GetYaxis().GetBinLowEdge(iy)) - low) < 10 if sm_num > 0 else abs(int(one_run_root_object.GetYaxis().GetBinUpEdge(iy)) - low) <= 10
    block = a and b
    return block


#check if the channel is in the L region
def isLBlock(sm_num, one_run_root_object, ix, iy):
    return not isIBlock(sm_num, one_run_root_object, ix, iy)


def dividebymedian_EB(Ichannels, Lchannels):
    #I region
    Ichannels_array = np.array(Ichannels["value"])
    Imedian = np.median(Ichannels_array)
    if Imedian != 0:
        Ichannels_val_over_median = Ichannels_array / Imedian
        Ichannels["value"] = Ichannels_val_over_median.tolist()
    #L region
    Lchannels_array = np.array(Lchannels["value"])
    Lmedian = np.median(Lchannels_array)
    if Lmedian != 0:
        Lchannels_val_over_median = Lchannels_array / Lmedian
        Lchannels["value"] = Lchannels_val_over_median.tolist()


def dividebymedian_EE(EEchannels):
    df = pd.DataFrame(EEchannels)
    medians_by_region = df.groupby("LightMR")["value"].transform("median")
    df["normalized_value"] = df["value"] / medians_by_region
    EEchannels["value"] = df["normalized_value"].tolist()


#delete runs with all 0 values and those channels which are not present in every run (because of a different mask probably)
def check_common_channels(run_dict_temp):
    runs_to_remove = [run for run, data in run_dict_temp.items() if all(abs(val) == 0 for val in data["value"])]
    for run in runs_to_remove:
        del run_dict_temp[run]
    if not run_dict_temp:
        return
    common_channels = set(run_dict_temp[next(iter(run_dict_temp))]["label"])
    for run_data in run_dict_temp.values():
        common_channels &= set(run_data["label"])
    for run, data in run_dict_temp.items():
        filtered_SM_ch = []
        filtered_value = []
        for ch, val in zip(data["label"], data["value"]):
            if ch in common_channels:
                filtered_SM_ch.append(ch)
                filtered_value.append(val)
        data["label"] = filtered_SM_ch
        data["value"] = filtered_value
    return run_dict_temp.keys()


#check the channels with values outside a range centered in medians_over_runs
def getBadXY(available_runs, run_dict_temp, run_dict):
    channels_array = np.array([run_dict_temp[run]["label"] for run in available_runs])
    values_array = np.array([run_dict_temp[run]["value"] for run in available_runs])
    values_array[values_array == -0] = 0
    zero_cols = np.any(abs(values_array) == 0, axis=0)
    mask_keep_cols = ~zero_cols
    channels_filtered = channels_array[:, mask_keep_cols]
    values_filtered = values_array[:, mask_keep_cols]
    MEDIANUP_EB = 2
    MEDIANLOW_EB = 0.1
    MEDIANUP_EE = 3
    MEDIANLOW_EE = 0.003
    num_channels = values_filtered.shape[1]
    for i in range(num_channels):
        values_column = values_filtered[:, i]
        channels = channels_filtered[:, i]
        for j, run in enumerate(available_runs):
            if "EB" in channels[0]:
                #if "EB+10" in channels[0]: print("ch: ", channels, "values: ", values_column)
                if values_column[j] < MEDIANLOW_EB or values_column[j] > MEDIANUP_EB:
                    run_dict["label"].extend(channels.tolist())
                    run_dict["value"].extend(values_column.tolist())
                    run_dict["run"].extend(list(available_runs))
                    break
            elif "EE" in channels[0]:
                if values_column[j] < MEDIANLOW_EE or values_column[j] > MEDIANUP_EE:
                    run_dict["label"].extend(channels.tolist())
                    run_dict["value"].extend(values_column.tolist())
                    run_dict["run"].extend(list(available_runs))
                    break
    print("finished filtering laser channels")


class Laser3Amplitude(Plugin):
    def __init__(self, buildopener):
        Plugin.__init__(self, buildopener, folder="", plot_name="")


    def process_one_run(self, run_info):
        run_dict = {"label": [], "value":[]}

        #EB
        EBsupermodules_list = ECAL.EBsupermodules_list
        for i, EBsupermodule in enumerate(EBsupermodules_list):
            self.folder = "EcalBarrel/EBLaserTask/Laser3/"
            self.plot_name = f"EBLT amplitude {EBsupermodule} L3"
            Ichannels = {"label": [], "value": []}
            Lchannels = {"label": [], "value": []}
            one_run_root_object = self.get_root_object(run_info)
            read_hist_EB(one_run_root_object, EBsupermodule, Ichannels, Lchannels)
            dividebymedian_EB(Ichannels, Lchannels)
            run_dict["label"].extend(Ichannels["label"] + Lchannels["label"])
            run_dict["value"].extend(Ichannels["value"] + Lchannels["value"])
        
        #EE
        EEsupermodules_list = ECAL.EEsupermodules_list
        for i, EEsupermodule in enumerate(EEsupermodules_list):
            self.folder = "EcalEndcap/EELaserTask/Laser3/"
            self.plot_name = f"EELT amplitude {EEsupermodule} L3"
            EEchannels = {"label": [], "value": [], "LightMR": []}
            one_run_root_object = self.get_root_object(run_info)
            read_hist_EE(one_run_root_object, EEsupermodule, EEchannels)
            dividebymedian_EE(EEchannels)
            run_dict["label"].extend(EEchannels["label"])
            run_dict["value"].extend(EEchannels["value"])
        
        #fill _data inside generic Plugin class
        self.fill_data_one_run(run_info, run_dict)

    def create_history_plots(self, save_path):
        self.color_scale_settings(255)
        available_runs = self.get_available_runs()
        run_dict_temp = {}
        for i, run in enumerate(available_runs):
            data_one_run = self.get_data_one_run(run)
            run_dict_temp[run] = data_one_run
        available_runs_filtered = check_common_channels(run_dict_temp)
        run_dict = {"label": [], "value": [], "run": []}
        getBadXY(available_runs_filtered, run_dict_temp, run_dict)

        #ordering
        run_df = pd.DataFrame(run_dict)
        if run_df.empty:
            print("Dataframe is empty, no info to plot")
            return
        run_df[["detector", "sm_ch", "iphi_ix", "ieta_iy"]] = run_df["label"].str.extract(r'(EB|EE)([+-]?\d+)\s+\[([+-]?\d+),\s*([+-]?\d+)\]')
        run_df["sm_ch"] = run_df["sm_ch"].astype(int)
        run_df["iphi_ix"] = run_df["iphi_ix"].astype(int)
        run_df["ieta_iy"] = run_df["ieta_iy"].astype(int)
        run_df["detector_priority"] = run_df["detector"].map({"EB": 0, "EE": 1})
        run_df = run_df.sort_values(by=["detector_priority", "sm_ch", "iphi_ix", "ieta_iy"]).drop(columns=["detector_priority",
        "detector", "sm_ch", "iphi_ix", "ieta_iy"])
        df_EB = run_df.loc[run_df["label"].str.contains("EB", case=False)]
        df_EE = run_df.loc[run_df["label"].str.contains("EE", case=False)]

        #fillingEB history plot
        self.fill_history_subplots(df_EB, available_runs, f"L3Amp_EB_gt_medianx{MEDIANUP_EB}_lt_medianx{MEDIANLOW_EB}", f"{save_path}", change_hist_limits=True)
        #filling EE history plot
        self.fill_history_subplots(df_EE, available_runs, f"L3Amp_EE_gt_medianx{MEDIANUP_EE}_lt_medianx{MEDIANLOW_EE}", f"{save_path}", change_hist_limits=True)
