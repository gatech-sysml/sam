from pathlib import Path

import numpy as np
import torch
import torchvision
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Dataset


def get_project_path() -> Path:
    return Path(__file__).parent.parent.parent


def cifar100_stats(root=str(get_project_path() / "datasets")):
    _data_set = torchvision.datasets.CIFAR100(
        root=root, train=True, download=True, transform=transforms.ToTensor(),
    )

    _data_tensors = torch.cat([d[0] for d in DataLoader(_data_set)])
    mean, std = _data_tensors.mean(dim=[0, 2, 3]), _data_tensors.std(dim=[0, 2, 3])
    return mean, std


def load_dataset(split: str, _args):
    if split not in ["train", "test"]:
        raise ValueError("split must be 'train' or 'test'")
    fp = (
        get_project_path()
        / "datasets"
        / split
        / _args.granularity
        / _args.superclass
        / f"crop_size{str(_args.crop_size)}"
        / f"dataset_{split}_{_args.granularity}_{_args.superclass}_crop{str(_args.crop_size)}.pt"
    )
    dataset = torch.load(fp)
    return dataset


def save_dataset(data: torchvision.datasets, split: str, _args):
    if split not in ["train", "test"]:
        raise ValueError("split must be 'train' or 'test'")
    output_path = (
        get_project_path()
        / "datasets"
        / split
        / _args.granularity
        / _args.superclass
        / f"crop_size{str(_args.crop_size)}"
        / f"dataset_{split}_{_args.granularity}_{_args.superclass}_crop{str(_args.crop_size)}.pt"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Saving: {output_path}")
    torch.save(data, output_path)


fine_classes = (  # Strict order DO NOT CHANGE
    "apple",
    "aquarium_fish",
    "baby",
    "bear",
    "beaver",
    "bed",
    "bee",
    "beetle",
    "bicycle",
    "bottle",
    "bowl",
    "boy",
    "bridge",
    "bus",
    "butterfly",
    "camel",
    "can",
    "castle",
    "caterpillar",
    "cattle",
    "chair",
    "chimpanzee",
    "clock",
    "cloud",
    "cockroach",
    "couch",
    "crab",
    "crocodile",
    "cup",
    "dinosaur",
    "dolphin",
    "elephant",
    "flatfish",
    "forest",
    "fox",
    "girl",
    "hamster",
    "house",
    "kangaroo",
    "keyboard",
    "lamp",
    "lawn_mower",
    "leopard",
    "lion",
    "lizard",
    "lobster",
    "man",
    "maple_tree",
    "motorcycle",
    "mountain",
    "mouse",
    "mushroom",
    "oak_tree",
    "orange",
    "orchid",
    "otter",
    "palm_tree",
    "pear",
    "pickup_truck",
    "pine_tree",
    "plain",
    "plate",
    "poppy",
    "porcupine",
    "possum",
    "rabbit",
    "raccoon",
    "ray",
    "road",
    "rocket",
    "rose",
    "sea",
    "seal",
    "shark",
    "shrew",
    "skunk",
    "skyscraper",
    "snail",
    "snake",
    "spider",
    "squirrel",
    "streetcar",
    "sunflower",
    "sweet_pepper",
    "table",
    "tank",
    "telephone",
    "television",
    "tiger",
    "tractor",
    "train",
    "trout",
    "tulip",
    "turtle",
    "wardrobe",
    "whale",
    "willow_tree",
    "wolf",
    "woman",
    "worm",
)

coarse_classes = (  # Strict order DO NOT CHANGE
    "aquatic_mammals",
    "fish",
    "flowers",
    "food_containers",
    "fruit_and_vegetables",
    "household_electrical_devices",
    "household_furniture",
    "insects",
    "large_carnivores",
    "large_man-made_outdoor_things",
    "large_natural_outdoor_scenes",
    "large_omnivores_and_herbivores",
    "medium_mammals",
    "non-insect_invertebrates",
    "people",
    "reptiles",
    "small_mammals",
    "trees",
    "vehicles_1",
    "vehicles_2",
)

coarse_idx_to_class = {  # Strict order DO NOT CHANGE
    0: "aquatic_mammals",
    1: "fish",
    2: "flowers",
    3: "food_containers",
    4: "fruit_and_vegetables",
    5: "household_electrical_devices",
    6: "household_furniture",
    7: "insects",
    8: "large_carnivores",
    9: "large_man-made_outdoor_things",
    10: "large_natural_outdoor_scenes",
    11: "large_omnivores_and_herbivores",
    12: "medium_mammals",
    13: "non-insect_invertebrates",
    14: "people",
    15: "reptiles",
    16: "small_mammals",
    17: "trees",
    18: "vehicles_1",
    19: "vehicles_2",
}

coarse_class_to_idx = {  # Strict order DO NOT CHANGE
    "aquatic_mammals": 0,
    "fish": 1,
    "flowers": 2,
    "food_containers": 3,
    "fruit_and_vegetables": 4,
    "household_electrical_devices": 5,
    "household_furniture": 6,
    "insects": 7,
    "large_carnivores": 8,
    "large_man-made_outdoor_things": 9,
    "large_natural_outdoor_scenes": 10,
    "large_omnivores_and_herbivores": 11,
    "medium_mammals": 12,
    "non-insect_invertebrates": 13,
    "people": 14,
    "reptiles": 15,
    "small_mammals": 16,
    "trees": 17,
    "vehicles_1": 18,
    "vehicles_2": 19,
}

coarse_idxs = dict([L[::-1] for L in enumerate(coarse_classes)])

fine_idx_to_coarse = np.array(  # Strict order DO NOT CHANGE
    [
        4,
        1,
        14,
        8,
        0,
        6,
        7,
        7,
        18,
        3,
        3,
        14,
        9,
        18,
        7,
        11,
        3,
        9,
        7,
        11,
        6,
        11,
        5,
        10,
        7,
        6,
        13,
        15,
        3,
        15,
        0,
        11,
        1,
        10,
        12,
        14,
        16,
        9,
        11,
        5,
        5,
        19,
        8,
        8,
        15,
        13,
        14,
        17,
        18,
        10,
        16,
        4,
        17,
        4,
        2,
        0,
        17,
        4,
        18,
        17,
        10,
        3,
        2,
        12,
        12,
        16,
        12,
        1,
        9,
        19,
        2,
        10,
        0,
        1,
        16,
        12,
        9,
        13,
        15,
        13,
        16,
        19,
        2,
        4,
        6,
        19,
        5,
        5,
        8,
        19,
        18,
        1,
        2,
        15,
        6,
        0,
        17,
        8,
        14,
        13,
    ]
)

fine_to_coarse_idxs = dict(enumerate(fine_idx_to_coarse))  # Strict order DO NOT CHANGE
