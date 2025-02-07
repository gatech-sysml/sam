import argparse
import os
import pickle
from pathlib import Path

import torch
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Dataset
from tqdm.auto import tqdm

from evaluations import set_crop_size
from model.wide_res_net import WideResNet_Embeds
from utility.cifar_utils import (
    cifar100_stats,
    coarse_classes,
    coarse_idxs,
    fine_to_coarse_idxs,
)

torch.multiprocessing.set_sharing_strategy("file_system")
from collections import namedtuple
from itertools import compress

from utility.cifar_utils import coarse_class_to_idx

project_path = Path(__file__).parent.parent

dataset_path = project_path / "datasets"
dataset_path.mkdir(parents=True, exist_ok=True)

evaluations_path = project_path / "evaluations"
evaluations_path.mkdir(parents=True, exist_ok=True)

predictions_path = evaluations_path / "predictions"
predictions_path.mkdir(exist_ok=True, parents=True)

embeddings_path = evaluations_path / "embeddings"
embeddings_path.mkdir(exist_ok=True, parents=True)

Result = namedtuple("Result", ["idx", "prediction", "target", "correct", "outputs"])
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


def get_granularity(name: str) -> str:
    if "coarse" in name:
        return "coarse"
    elif "fine" in name:
        return "fine"
    else:
        raise ValueError("granularity not found")


def get_parameter(name: str, param: str) -> int:
    extension = "." + name.split(".")[-1]
    if param not in ["class", "crop", "kernel", "width", "depth"]:
        raise ValueError("invalid parameter input")
    for element in name.split("_"):
        if param in element:
            return int(element.replace(param, "").replace(extension, ""))


def get_parameters(model_filename):
    granularity = get_granularity(model_filename)
    class_id = int(get_parameter(model_filename, "class"))
    crop_size = int(get_parameter(model_filename, "crop"))
    kernel_size = int(get_parameter(model_filename, "kernel"))
    width_factor = int(get_parameter(model_filename, "width"))
    depth = int(get_parameter(model_filename, "depth"))
    return granularity, class_id, crop_size, kernel_size, width_factor, depth


def parse_model_path(model_path):
    model_name = str(model_path.split("/")[-1])
    model_name = model_name.replace(".pt", "").replace("model_", "")
    model_name = superclass_to_idx(model_name)
    return model_name


def superclass_to_idx(filename: str):
    """
    input a model filename
    output is model filename with the superclass label name replaced with index
    coarse granularity models have their generic term removed
    """
    if "_all_" in filename:  # if coarse just removes the superclass placeholder
        return filename.replace("_all_", "_class-1_")
    keys = coarse_class_to_idx.keys()
    superclass = next(compress(keys, [k in filename for k in keys]))
    superclass_idx = coarse_class_to_idx[superclass]
    return filename.replace(superclass, "class" + str(superclass_idx))


class CIFAR100Indexed(Dataset):
    def __init__(self, root, download, train, transform):
        self.cifar100 = torchvision.datasets.CIFAR100(
            root=root, download=download, train=train, transform=transform
        )

    def __getitem__(self, index):
        data, target = self.cifar100[index]
        return data, target, index

    def __len__(self):
        return len(self.cifar100)


def find_model_files(model_path=(project_path / "models")):
    model_files = []
    for root, directories, files in os.walk(model_path):
        for file in files:
            if file.startswith("model_") and file.endswith(".pt"):
                model_files.append(os.path.join(root, file))
    return model_files


def get_model_embedding(dataloader, model, device, dataset_type: str):
    """

    :param dataloader: Dataloader containing CIFAR100Indexed
    :param model: WideResNet model object
    :param device: CUDA device
    :param dataset_type: Text string with the data split (train, test, validate, etc)
    :return:
    """
    model_embeddings = {}
    with torch.no_grad():
        for inputs, targets, idxs in tqdm(
            dataloader, desc=f"Evaluating {dataset_type} data", leave=False
        ):
            inputs, targets = inputs.to(device), targets.to(device)
            _, embeds = model(inputs)  # ignore model output only need the embedding

            # Data munging for embeddings
            embeds_zip = zip(idxs, embeds.cpu())
            for idx, embed in embeds_zip:
                model_embeddings[idx.tolist()] = embed.tolist()
    return model_embeddings


def get_test_dataloader(coarse=False):
    mean, std = cifar100_stats(root=str(dataset_path))
    test_transform = transforms.Compose(
        [
            transforms.RandomCrop(size=32),
            transforms.ToTensor(),
            transforms.Normalize(mean, std),
        ]
    )
    test_dataset = CIFAR100Indexed(
        root=str(dataset_path), train=False, download=False, transform=test_transform,
    )

    test_dataset.cifar100.meta["type"] = "test"

    if coarse:
        test_dataset.cifar100.classes = coarse_classes
        test_dataset.cifar100.class_to_idx = coarse_idxs
        test_dataset.cifar100.targets = list(
            map(fine_to_coarse_idxs.get, test_dataset.cifar100.targets)
        )

    test_dataloader = torch.utils.data.DataLoader(
        test_dataset, batch_size=1024, shuffle=False, num_workers=2,
    )

    return test_dataloader


def get_validation_dataloader(coarse=False):
    validation_dataset = torch.load(
        dataset_path / "validation" / "validation_dataset.pt"
    )
    validation_dataset.cifar100.meta["type"] = "validation"

    if coarse:
        validation_dataset.cifar100.classes = coarse_classes
        validation_dataset.cifar100.class_to_idx = coarse_idxs
        validation_dataset.cifar100.targets = list(
            map(fine_to_coarse_idxs.get, validation_dataset.cifar100.targets)
        )

    validation_dataloader = torch.utils.data.DataLoader(
        validation_dataset, batch_size=1024, shuffle=False, num_workers=2,
    )
    return validation_dataloader


def main(_args):
    """
    from the training set, get 100 images for each superclass
    export as validation set
    """
    device = torch.device(f"cuda:{_args.gpu}" if torch.cuda.is_available() else "cpu")

    test_fine_dataloader = get_test_dataloader(coarse=False)
    test_coarse_dataloader = get_test_dataloader(coarse=True)
    validation_fine_dataloader = get_validation_dataloader(coarse=False)
    validation_coarse_dataloader = get_validation_dataloader(coarse=True)

    # Find the model path based on the input model name
    model_paths = find_model_files()
    for mp in model_paths:
        if _args.model_pattern in mp:
            model_filename = parse_model_path(str(mp))
            print(model_filename)

            (
                granularity,
                class_id,
                crop_size,
                kernel_size,
                width_factor,
                depth,
            ) = get_parameters(model_filename)

            model_info = [
                granularity,
                class_id,
                crop_size,
                kernel_size,
                width_factor,
                depth,
            ]
            print(model_info)

            if granularity == "coarse":
                n_labels = 20
                test_dataloader = test_coarse_dataloader
                validation_dataloader = validation_coarse_dataloader
            elif granularity == "fine":
                n_labels = 100
                test_dataloader = test_fine_dataloader
                validation_dataloader = validation_fine_dataloader
            else:
                raise ValueError("model filename does not contain granularity")

            # Sets the crop size on the RandomCrop transform to fit the model
            set_crop_size(test_dataloader, crop_size)
            set_crop_size(validation_dataloader, crop_size)

            # TODO: [OPTIONAL] Set the dataloader's batch size based on the crop size to increase evaluation speed

            model = WideResNet_Embeds(
                kernel_size=kernel_size,
                width_factor=width_factor,
                depth=depth,
                dropout=0.0,
                in_channels=3,
                labels=n_labels,
            )

            model_state_dict = torch.load(mp, map_location=f"cuda:{_args.gpu}")[
                "model_state_dict"
            ]
            model.load_state_dict(model_state_dict)
            model.cuda(device)
            model.eval()

            print("TEST DATA: Getting model embeddings")
            test_embeddings = get_model_embedding(  # test_results, test_accuracy,
                test_dataloader, model, device, "test"
            )
            test_embeds_pkl = open(
                str(embeddings_path / f"test_embeds__{model_filename}.pkl"), "wb",
            )
            pickle.dump(test_embeddings, test_embeds_pkl)
            test_embeds_pkl.close()
            print("TEST DATA: Embeddings saved")

            print("VALIDATION DATA: Getting model embeddings")
            validation_embeddings = get_model_embedding(  # validation_results, validation_accuracy,
                validation_dataloader, model, device, "validation"
            )
            validation_embeds_pkl = open(
                str(embeddings_path / f"validation_embeds__{model_filename}.pkl"), "wb",
            )
            pickle.dump(validation_embeddings, validation_embeds_pkl)
            validation_embeds_pkl.close()
            print("VALIDATION DATA: Embeddings saved")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gpu", default=3, type=int, help="Index of GPU to use",
    )
    parser.add_argument(
        "--model_pattern",
        default=None,
        type=str,
        help="Name of the model we want to evaluate",
    )
    args = parser.parse_args()
    print("Getting model results")
    main(args)
