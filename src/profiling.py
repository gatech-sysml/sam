import argparse
import csv
from pathlib import Path

import pandas as pd
import torch
from ptflops import get_model_complexity_info
from tqdm.auto import tqdm

from model.wide_res_net import WideResNet

torch.multiprocessing.set_sharing_strategy("file_system")
from collections import namedtuple


def main(_args):
    """
    from the training set, get 100 images for each superclass
    export as validation set
    """
    device = torch.device(f"cuda:{_args.gpu}" if torch.cuda.is_available() else "cpu")

    project_path = Path(__file__).parent.parent
    project_path = Path.cwd()

    dataset_path = project_path / "datasets"
    dataset_path.mkdir(parents=True, exist_ok=True)
    evaluations_path = project_path / "evaluations"
    evaluations_path.mkdir(parents=True, exist_ok=True)
    profiles_path = evaluations_path / f"{_args.filename}.csv"

    profile_fields = [
        "granularity",
        "superclass",
        "crop_size",
        "kernel_size",
        "width_factor",
        "depth",
        "accuracy",
        "macs",
        "flops",
        "params",
    ]
    Profile = namedtuple("Profile", profile_fields,)

    with open(profiles_path, "w", encoding="UTF8") as f:
        writer = csv.writer(f)
        writer.writerow(profile_fields)

    model_parameter_space = []
    for granularity in ["coarse"]:
        for crop_size, kernel_size in [(32, 8)]:
            for width_factor in [2, 4, 6, 8, 10]:
                for depth in [8, 12, 16, 20, 22, 24, 28]:
                    model_parameter_space.append(
                        (granularity, crop_size, kernel_size, width_factor, depth,)
                    )

    for model_parameters in tqdm(
        model_parameter_space, desc="Model profiling", leave=False
    ):
        print(f"Profiling: {model_parameters}")
        (granularity, crop_size, kernel_size, width_factor, depth,) = model_parameters

        if granularity == "coarse":
            n_labels = 20
        elif granularity == "fine":
            n_labels = 100
        else:
            raise ValueError("model filename does not contain granularity")

        model = WideResNet(
            kernel_size=kernel_size,
            width_factor=width_factor,
            depth=depth,
            dropout=0.0,
            in_channels=3,
            labels=n_labels,
        )

        # model_state_dict = torch.load(model_path, map_location=f"cuda:{_args.gpu}")[
        #     "model_state_dict"
        # ]
        # model.load_state_dict(model_state_dict)
        model.cuda(device)
        model.eval()

        macs, params = get_model_complexity_info(
            model,
            (3, crop_size, crop_size),
            as_strings=True,
            print_per_layer_stat=False,
            verbose=False,
        )
        flops = f"{2*float(macs.split(' ')[0])} GFLOPs"
        profile_ = Profile(
            *(
                [
                    granularity,
                    "N/A",
                    crop_size,
                    kernel_size,
                    width_factor,
                    depth,
                    "N/A",
                    macs,
                    flops,
                    params,
                ]
            )
        )
        profile_df = pd.DataFrame([profile_], columns=profile_fields)
        profile_df.to_csv(profiles_path, mode="a", header=False, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gpu", default=6, type=int, help="Index of GPU to use",
    )
    parser.add_argument(
        "--filename",
        default="model_profiles_crop32",
        type=str,
        help="name of the csv file you want to generate",
    )
    args = parser.parse_args()
    print("Getting computational profile of models in the model pararmeter space")
    main(args)
