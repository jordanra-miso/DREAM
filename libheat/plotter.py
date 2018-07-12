#!/usr/bin/env python3

"""
Analyses and plots the old space-separated data files.
"""

import argparse
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def main():
    args = parse_args()
    full_df = None
    for f in args.file:
        if full_df is None:
            full_df = pd.read_csv(f, header=0)
        else:
            df = pd.read_csv(f, header=0)
            full_df = full_df.append(df, ignore_index=True)

    # Filter the samples
    full_df = framefilters(full_df)
    robustness_v_synchrony(full_df, errorbars=False)
    return
    #robustness_v_sd(full_df)
    if args.robustness:
        clinic_si_threshold(full_df)
        clinic_ar_threshold(full_df)
        #plot_robustness(full_df, plot_type=args.type)
    elif args.reschedules:
        plot_reschedule(full_df, plot_type=args.type)


def framefilters(df):
    # Add the synchrony column, extracted from the file name.
    sync_column = []
    for i, row in df.iterrows():
        foldername = row["stn_path"].split("/")[-2]
        synchrony = float(foldername.split("_")[4][1:])*0.001
        sync_column.append(synchrony)
    df = df.assign(sync_deg=pd.Series(sync_column))
    # Remove zeros present in the data.
    df = clearzero(df)
    return df[df.samples >= 100]


def clearzero(df):
    unique_stns = df.drop_duplicates(subset="stn_path")
    to_remove = []
    for _, row in unique_stns.iterrows():
        stn_path = row["stn_path"]
        runs = df.loc[df["stn_path"] == stn_path]
        all_zero = True
        for _, run in runs.iterrows():
            if not all_zero:
                break
            all_zero = run["robustness"] <= 0.0
        if all_zero:
            to_remove.append(stn_path)
    for path in to_remove:
        indices = df.loc[df["stn_path"] == path]
        common = df.merge(indices, on=['stn_path'])
        df = df[~df.stn_path.isin(common.stn_path)]
    return df


def plot_robustness(df, plot_type="box"):
    early = df.loc[df['execution'] == "early"]
    srea = df.loc[df['execution'] == "srea"]
    drea = df.loc[df['execution'] == "drea"]
    drea_alp = df.loc[df['execution'] == "drea-alp"]
    drea_si = df.loc[df['execution'] == "drea-si"]
    drea_ar = df.loc[df['execution'] == "drea-ar"]

    early_rob = early["robustness"]
    srea_rob = srea["robustness"]
    drea_rob = drea["robustness"]
    drea_alp_rob = drea_alp["robustness"]
    drea_si_rob = drea_si["robustness"]
    drea_ar_rob = drea_ar["robustness"]

    if plot_type == "box":
        plt.boxplot((early_rob.tolist(), srea_rob.tolist(), drea_rob.tolist()))
    elif plot_type == "bar":
        plt.bar(range(3), early_rob.mean(), srea_rob.mean(), drea_rob.mean())
    elif plot_type == "line":
        thresholds = [0.0, 0.25, 0.5, 0.75, 1.0]
        # SI
        rob_means = []
        rob_sd = []
        for i in thresholds:
            i_drea_si = drea_si.loc[drea_si["threshold"] == i]
            n = sum(i_drea_si["samples"])
            p = sum(i_drea_si["samples"] * i_drea_si["robustness"])\
                    / n
            sem = (p*(1-p)/n)**0.5

            rob_means.append(p)
            rob_sd.append(sem)
        plt.errorbar(thresholds, rob_means, yerr=rob_sd, capsize=4,
                     linewidth=1)
        # ALP
        rob_means = []
        rob_sd = []
        for i in thresholds:
            i_drea_alp = drea_alp.loc[drea_si["threshold"] == i]
            n = sum(i_drea_alp["samples"])
            p = sum(i_drea_alp["samples"] * i_drea_alp["robustness"])\
                    / n
            sem = (p*(1-p)/n)**0.5

            rob_means.append(p)
            rob_sd.append(sem)
        plt.errorbar(thresholds, rob_means, yerr=rob_sd, capsize=4,
                     linewidth=1)
        # AR
        rob_means = []
        rob_sd = []
        for i in thresholds:
            i_drea_ar = drea_ar.loc[drea_si["threshold"] == i]
            n = sum(i_drea_ar["samples"])
            p = sum(i_drea_ar["samples"] * i_drea_ar["robustness"])\
                    / n
            sem = (p*(1-p)/n)**0.5

            rob_means.append(p)
            rob_sd.append(sem)
        plt.errorbar(thresholds, rob_means, yerr=rob_sd, capsize=3,
                     linewidth=0)

        plt.plot(thresholds, np.full(4, drea_rob.mean()))
        plt.plot(thresholds, np.full(5, srea_rob.mean()))
    plt.show()


def sd_v_robust(df):
    """Plot Standard Deviation of Contingent Edges vs. Performance
        Produces a scatterplot.

    X axis: Mean of the standard deviations of the edges present.
    Y axis: Robustness

    Args:
        df (DataFrame): DataFrame of results to be passed. Must have a
            "sd_avg" column.
    """
    early = df.loc[df['execution'] == "early"]
    srea = df.loc[df['execution'] == "srea"]
    drea = df.loc[df['execution'] == "drea"]

    early_rob = early["robustness"]
    srea_rob = srea["robustness"]
    drea_rob = drea["robustness"]

    plt.scatter(early["sd_avg"].tolist(), early_rob.tolist(),
                alpha=0.2,
                label="Early")
    plt.scatter(srea["sd_avg"].tolist(), srea_rob.tolist(),
                alpha=0.2,
                label="SREA")
    plt.scatter(drea["sd_avg"].tolist(), drea_rob.tolist(),
                alpha=0.2,
                label="DREA")
    plt.legend()
    plt.ylabel("Robustness")
    plt.xlabel("Standard Deviation of Contingent Edges")
    plt.title("Edge Standard Deviation vs. Performance")
    plt.show()


def synch_v_robust(df, errorbars=True, executions=None, thresholds=None):
    """Plot Sychronisation vs. Performance

    X axis: Degree of Synchronisation
    Y axis: Robustness (in percent)

    Error bars: Standard error extracted from the robustnesses of the STNs.
        Each STN is considered a datum.

    Args:
        df (DataFrame): DataFrame of results to be passed. Must have a
            "sync_deg" column.
        errorbars (boolean, optional): Should the plot have error bars? Default
            True
        executions (list, optional): List of strings of execution strats to
            plot. Default ["early", "srea", "drea"]
        thresholds (list, optional): List of floats of threshold values to
            plot. Default [0.0, 0.5, 1.0]
    """
    # Executions we care about.
    if executions is None:
        executions = ["early", "srea", "drea"]
    if thresholds is None:
        thresholds = [0.0, 0.5, 1.0]
    # Make use of that degree of synchrony we added in framefilters()
    x_values = sorted(df["sync_deg"].unique().tolist())
    # Store y values. Is of the format {execution: list of y values}
    data_y = {}
    # Store error bars. Is of the format {execution: list of error bars}
    data_err = {}
    # Iterate through every execution strategy we care about.
    for ex in executions:
        runs = df.loc[df["execution"] == ex]
        for x in x_values:
            run_deg = runs.loc[runs["sync_deg"] == x]
            if ex != "drea-si" and ex != "drea-ar":
                run_series = run_deg["robustness"]  # Get robustness.
                mean = run_series.mean()
                err = run_series.sem()  # Standard error bar.
                if ex in data_y:
                    data_y[ex].append(mean*100)
                    data_err[ex].append(err*100)
                else:
                    data_y[ex] = [mean*100]
                    data_err[ex] = [err*100]
            else:
                for t in thresholds:
                    thresh_series = run_deg.loc[run_deg["threshold"]
                                                == t]["robustness"]
                    mean = thresh_series.mean()
                    err = thresh_series.sem()
                    label = ex + "_" + str(t)  # Make a unique label for each
                    if label in data_y:
                        data_y[label].append(mean*100)
                        data_err[label].append(err*100)
                    else:
                        data_y[label] = [mean*100]
                        data_err[label] = [err*100]
    linestyles = ["-", "--", ":", "-."]
    for i, label in enumerate(data_y.keys()):
        if errorbars:
            plt.errorbar(x_values, data_y[label], yerr=data_err[label],
                         linewidth=1, label=label, capsize=3,
                         linestyle=linestyles[i % len(linestyles)])
        else:
            plt.plot(x_values, data_y[label], linewidth=1, label=label,
                         linestyle=linestyles[i % len(linestyles)])
    plt.ylim(0, 100)
    plt.xlim(0, 25)
    plt.legend()
    plt.ylabel("Robustness (%)")
    plt.xlabel("Degree of Synchronization (sec)")
    plt.title("Degree of Synchronization vs. Performance")
    plt.show()


def clinic_si_threshold(df):
    srea = df.loc[df['execution'] == "srea"]
    drea = df.loc[df['execution'] == "drea"]
    drea_alp = df.loc[df['execution'] == "drea-alp"]
    drea_si = df.loc[df['execution'] == "drea-si"]
    drea_ar = df.loc[df['execution'] == "drea-ar"]
    early = df.loc[df['execution'] == 'early']

    srea_rob = srea["robustness"]
    early_rob = early["robustness"]
    drea_rob = drea["robustness"]
    drea_alp_rob = drea_alp["robustness"]
    drea_si_rob = drea_si["robustness"]
    drea_ar_rob = drea_ar["robustness"]

    thresholds = [0.0, 0.25, 0.5, 0.75, 1.0]
    drea_p = sum(drea["samples"]*drea["robustness"]) / sum(drea["samples"])
    drea_res = drea["reschedule_freq"].mean()
    drea_run = drea["runtime"].mean()

    # SI
    rob_means = []
    rob_sd = []
    res = []
    runs = []
    for i in thresholds:
        i_drea_si = drea_si.loc[drea_si["threshold"] == i]
        n = sum(i_drea_si["samples"])
        p = sum(i_drea_si["samples"] * i_drea_si["robustness"])\
                / n
        sem = (p*(1-p)/n)**0.5
        rob_means.append((1 - p/drea_p)*100)
        rob_sd.append(sem)
        res.append((1 - i_drea_si["reschedule_freq"].mean()/drea_res)*100)
        runs.append((1 - i_drea_si["runtime"].mean()/drea_run)*100)

    plt.errorbar(thresholds, rob_means, yerr=rob_sd, linestyle='-', capsize=4,
                 linewidth=1, label="SI Empirical Success Rate (%)")
    plt.plot(thresholds, res, linestyle='-.', linewidth=1,
             label="SI Number of Reschedules")
    plt.plot(thresholds, runs, linestyle=':', linewidth=1,
             label="SI Runtime")

    # ALP
    rob_means = []
    rob_sd = []
    res = []
    runs = []
    for i in thresholds:
        i_drea_alp = drea_alp.loc[drea_alp["threshold"] == i]
        n = sum(i_drea_alp["samples"])
        p = sum(i_drea_alp["samples"] * i_drea_alp["robustness"])\
                / n
        sem = (p*(1-p)/n)**0.5
        rob_means.append((1 - p/drea_p)*100)
        rob_sd.append(sem)
        res.append((1 - i_drea_alp["reschedule_freq"].mean()/drea_res)*100)
        runs.append((1 - i_drea_alp["runtime"].mean()/drea_run)*100)

    plt.errorbar(thresholds, rob_means, yerr=rob_sd, linestyle='-', capsize=4,
                 linewidth=1, label="ALPHA Empirical Success Rate (%)")
    plt.plot(thresholds, res, linestyle='-.', linewidth=1,
             label="ALPHA Number of Reschedules")
    plt.plot(thresholds, runs, linestyle=':', linewidth=1,
             label="ALPHA Runtime")

    plt.ylim(-40, 100)
    plt.xlim(0, 1)
    plt.legend(loc="lower center")
    plt.xlabel("Sufficient Improvement Threshold")
    plt.ylabel("Percent Reduction from DREA")
    plt.title("Trade-offs Between Communication and Performance in SI")
    #plt.plot(thresholds, np.full(5, drea_rob.mean()))
    #plt.plot(thresholds, np.full(5, srea_rob.mean()))

    plt.show()


def clinic_ar_threshold(df):
    srea = df.loc[df['execution'] == "srea"]
    drea = df.loc[df['execution'] == "drea"]
    drea_ar = df.loc[df['execution'] == "drea-ar"]
    early = df.loc[df['execution'] == 'early']

    srea_rob = srea["robustness"]
    early_rob = early["robustness"]
    drea_rob = drea["robustness"]
    drea_ar_rob = drea_ar["robustness"]

    thresholds = [0.0, 0.25, 0.5, 0.75, 1.0]
    drea_p = sum(drea["samples"]*drea["robustness"]) / sum(drea["samples"])
    drea_res = drea["reschedule_freq"].mean()
    drea_run = drea["runtime"].mean()

    # AR
    rob_means = []
    rob_e = []
    res = []
    res_e = []
    runs = []
    runs_e = []
    for i in thresholds:
        i_drea_ar = drea_ar.loc[drea_ar["threshold"] == i]
        n = sum(i_drea_ar["samples"])
        p = sum(i_drea_ar["samples"] * i_drea_ar["robustness"])\
                / n
        sem = ((p*(1-p)/n)**0.5)*100
        rob_means.append((1-i_drea_ar["robustness"].mean()/drea_rob.mean())
                         *100)
        #rob_means.append((1 - p/drea_p)*100)
        rob_e.append(i_drea_ar["robustness"].sem()*100)
        res.append((1 - i_drea_ar["reschedule_freq"].mean()/drea_res)*100)
        res_e.append(i_drea_ar["reschedule_freq"].sem()*100)
        runs.append((1 - i_drea_ar["runtime"].mean()/drea_run)*100)
        runs_e.append(i_drea_ar["runtime"].sem()*100)

    plt.errorbar(thresholds, rob_means, yerr=rob_e, linestyle='-', capsize=3,
                 linewidth=1, label="Empirical Success Rate (%)")
    plt.plot(thresholds, res, linestyle='-.', linewidth=1,
             label="Number of Reschedules")
    plt.plot(thresholds, runs, linestyle=':', linewidth=1, label="Runtime")

    plt.ylim(-40, 100)
    plt.xlim(0, 1)
    plt.legend(loc="lower center")
    plt.xlabel("Allowable Risk Threshold")
    plt.ylabel("Percent Reduction from DREA")
    plt.title("Trade-offs Between Communication and Performance in AR")

    plt.show()


def plot_reschedule(df, plot_type="box"):
    drea = df.loc[df['execution'] == "drea"]
    drea_alp = df.loc[df['execution'] == "drea-alp"]
    drea_si = df.loc[df['execution'] == "drea-si"]
    drea_ar = df.loc[df['execution'] == "drea-ar"]

    ax = plt.axes()

    x_d = np.arange(0.0, 1.1, 0.1)
    res = drea["reschedule_freq"].median()
    y_d = [res]*len(x_d)
    ax.plot(x_d, y_d, "k--")

    thresholds = (0.0, 0.25, 0.5, 0.75, 1.0)
    # boxplot offsets
    plot_off = 0.035

    y_si = []
    y_alp = []
    for i, j in enumerate(thresholds):
        y_si = (drea_si.loc[drea_si["threshold"] == j]["reschedule_freq"]
                .tolist())
        y_si = [i for i in y_si if i > 0.0]
        y_alp = (drea_alp.loc[drea_alp["threshold"] == j]["reschedule_freq"]
                 .tolist())
        y_alp = [i for i in y_alp if i > 0.0]
        y_ar = (drea_ar.loc[drea_alp["threshold"] == j]["reschedule_freq"]
                .tolist())
        y_ar = [i for i in y_ar if i > 0.0]

        bp = ax.boxplot([y_si, y_alp, y_ar], positions=(j-plot_off, j,
                                                        j+plot_off),
                        widths=0.03)
        color_boxes(bp)

    ax.set_xlabel("Thresholds")
    ax.set_ylabel("Reschedules per STN")
    ax.set_xlim(min(thresholds)-plot_off*2, max(thresholds)+plot_off*2)
    ax.set_xticks(thresholds)
    ax.set_xticklabels(thresholds)

    plt.show()


def color_boxes(bp):
    plt.setp(bp["boxes"][0], color="red")
    plt.setp(bp["boxes"][1], color="blue")
    plt.setp(bp["boxes"][2], color="green")

    plt.setp(bp["medians"][0], color="red")
    plt.setp(bp["medians"][1], color="blue")
    plt.setp(bp["medians"][2], color="green")

    plt.setp(bp["caps"][0], color="red")
    plt.setp(bp["caps"][1], color="red")
    plt.setp(bp["caps"][2], color="blue")
    plt.setp(bp["caps"][3], color="blue")
    plt.setp(bp["caps"][4], color="green")
    plt.setp(bp["caps"][5], color="green")

    plt.setp(bp["whiskers"][0], color="red")
    plt.setp(bp["whiskers"][1], color="red")
    plt.setp(bp["whiskers"][2], color="blue")
    plt.setp(bp["whiskers"][3], color="blue")
    plt.setp(bp["whiskers"][4], color="green")
    plt.setp(bp["whiskers"][5], color="green")


def parse_args():
    """Parse arguments provided.
    """
    parser = argparse.ArgumentParser(prog='Plotter')
    parser.add_argument('file', nargs="+", type=str, help='Files to plot')
    parser.add_argument("-r", "--robustness", action="store_true")
    parser.add_argument("-s", "--reschedules", action="store_true")
    parser.add_argument("--type", type=str, help="Plot type, (e.g. line, box)")
    return parser.parse_args()


def analyze_data_tightness(frame, columns, executions, interagent_tightnesses):
    """Retrieve a frame of the means

    Args:
        frame (DataFrame): Frame object of the data.
        columns (tuple): Tuple of strings holding the columns we want to
            find the means of.
        executions (tuple): Which execution strategies to look at?
        interagent_tightnesses (tuple): Integers of tightnesses.
    """
    mean_frame = pd.DataFrame(columns=['tght']+list(columns))
    for tght in interagent_tightnesses:

        tight_frame = frame.loc[frame['tght'] == tght]
        # Remove complete failure rows.
        remove_zeroed(tight_frame, executions)

        means = {'tght': tght}
        for execution in columns:
            execution_col = tight_frame[execution]
            count = execution_col.shape[0]
            means[execution] = (sum(execution_col)/float(count))
        mean_frame = mean_frame.append(means, ignore_index=True)
    print(mean_frame[TO_SHOW])


def remove_zeroed(frame, cols) -> None:
    """Remove rows which have all zeros in the provided columns

    Args:
        frame (DataFrame): Frame to clean from
        cols (tuple): Strings to check for zeros in simultaneously.

    Post:
        Modifies the frame in-place. Note it's a pass-by-reference.
    """
    to_drop = []
    for index, row in frame.iterrows():
        drop = True
        for col in cols:
            drop = (row[col] == 0.0 and drop)
        if drop:
            to_drop.append(index)
    frame.drop(to_drop)


if __name__ == "__main__":
    main()
