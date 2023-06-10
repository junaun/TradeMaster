import os
import sys
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

ROOT = str(Path(__file__).resolve().parents[2])
sys.path.append(ROOT)

import torch
import argparse
import os.path as osp
from mmcv import Config
from trademaster.utils import replace_cfg_vals,create_radar_score_baseline, calculate_radar_score, plot_radar_chart
from trademaster.nets.builder import build_net
from trademaster.environments.builder import build_environment
from trademaster.datasets.builder import build_dataset
from trademaster.agents.builder import build_agent
from trademaster.optimizers.builder import build_optimizer
from trademaster.losses.builder import build_loss
from trademaster.trainers.builder import build_trainer
from trademaster.evaluation.market_dynamics_labeling.builder import build_market_dynamics_model

def parse_args():
    parser = argparse.ArgumentParser(description='Market_Dynamics_modeling args')

    parser.add_argument("--data_path", type=str,help="data path to read")
    parser.add_argument("--method", type=str, help='method to use: slice_and_merge')
    parser.add_argument("--slope_interval",  nargs="+", type=float,help='The low, high slope when labeling_method=slope')
    parser.add_argument('--dynamic_number',type=int,default=3,help='The number of dynamics to be modeled')
    parser.add_argument('--max_length_expectation',type=int,default=300,help='Slice longer than this number will not merge actively')
    parser.add_argument('--OE_BTC',type=bool,default=False,help='If dataset is OE_BTC')
    parser.add_argument('--PM',type=str,default='False',help='If dataset is PM')
    parser.add_argument("--config", default=osp.join(ROOT, "configs", "evaluation", "market_dynamics_modeling.py"),
                        help="deafult mdm config path")
    parser.add_argument("--key_indicator", type=str, default='adjcp',help='The column name of the feature in the data that will be used for dynamic modeling')
    parser.add_argument("--timestamp", type=str, default='timestamp',help='The column name of the feature in the data that is the timestamp')
    parser.add_argument("--tic", type=str, default='tic',help='The column name of the feature in the data that marks the tic')
    parser.add_argument("--labeling_method", type=str, default='slope', help='The method that is used for dynamic labeling:quantile/slope/DTW')
    parser.add_argument("--min_length_limit", type=int, default=-1,help='Every slice will have at least this length')
    parser.add_argument("--merging_metric", type=str, default='DTW_distance',help='The method that is used for slice merging')
    parser.add_argument("--merging_threshold", type=float, default=-1,help='The metric threshold that is used to decide whether a slice will be merged')
    parser.add_argument("--merging_dynamic_constraint", type=int, default=-1,help='Neighbor segment of dynamics spans greater than this number will not be merged(setting this to $-1$ will disable the constraint)')
    parser.add_argument("--filter_strength", type=int, default=1,help='The strength of the low-pass Butterworth filter, the bigger the lower cutoff frequency, "1" have the cutoff frequency of min_length_limit period')



    args = parser.parse_args()
    return args

class Tee(object):
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
    def flush(self):
        pass


def run_mdm():




    args = parse_args()

    cfg = Config.fromfile(args.config)




    # task_name = args.task_name
    # test_dynamic=args.test_dynamic

    cfg = replace_cfg_vals(cfg)
    print(cfg.pretty_text)


    #log to file
    # get the folder of args.data_path
    outputfolder = os.path.dirname(cfg.market_dynamics_model.data_path)
    f = open(f"{outputfolder}/res.log", 'a')
    backup = sys.stdout
    sys.stdout = Tee(sys.stdout, f)


    # if args.data_path is a folder, then we will run the experiment on all the files in the folder
    data_file_paths=[]
    if os.path.isdir(cfg.market_dynamics_model.data_path):
        original_data_path=cfg.market_dynamics_model.data_path
        for file in os.listdir(cfg.market_dynamics_model.data_path):
            # if the file is not a csv or feather file, then skip
            if not file.endswith('.csv') and not file.endswith('.feather'):
                continue
            data_file_paths.append(os.path.join(cfg.market_dynamics_model.data_path, file))
    else:
        data_file_paths.append(cfg.market_dynamics_model.data_path)

    for data_file_path in data_file_paths:
        # set cfg.tic to the file name
        cfg.market_dynamics_model.tic=os.path.basename(data_file_path).split('.')[0]
        print(f'now processing tic {cfg.market_dynamics_model.tic}')
        cfg.market_dynamics_model.data_path=data_file_path
        # update test style
        model = build_market_dynamics_model(cfg)

        process_datafile_path, market_dynamic_labeling_visualization_paths=model.run()
        print(f'The processed datafile is at {process_datafile_path}')
        plot_dir = os.path.dirname(os.path.realpath(market_dynamic_labeling_visualization_paths[0]))
        print(f'The visualizations are at {plot_dir}')
        print(f'The experiment log is at {outputfolder}/res.log')

    ## wirte path to cfg
    cfg.market_dynamics_model.data_path=original_data_path
    cfg.market_dynamics_model.process_datafile_path=process_datafile_path.replace("\\", "/")
    cfg.market_dynamics_model.market_dynamic_labeling_visualization_paths=market_dynamic_labeling_visualization_paths
    cfg.dump(args.config)



if __name__ == '__main__':
    run_mdm()