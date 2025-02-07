import argparse
import os
from pathlib import Path

import GPUtil
import numpy as np
import torch

from model.smooth_cross_entropy import smooth_crossentropy
from model.wide_res_net import WideResNet
from sam import SAM
from utility.bypass_bn import disable_running_stats, enable_running_stats
from utility.initialize import initialize
from utility.log import Log
from utility.step_lr import StepLR
from utility.cutout import Cutout
from torchvision import transforms
import torchvision
from torch.utils.data import DataLoader, Dataset

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


def get_project_path() -> Path:
    return Path(__file__).parent.parent

dataset_path = get_project_path() / 'data'

def cifar100_stats(root=str(get_project_path() / "datasets")):
    _data_set = torchvision.datasets.CIFAR100(
        root=root, train=True, download=True, transform=transforms.ToTensor(),
    )

    _data_tensors = torch.cat([d[0] for d in DataLoader(_data_set)])
    mean, std = _data_tensors.mean(dim=[0, 2, 3]), _data_tensors.std(dim=[0, 2, 3])
    return mean, std


def get_dataset(train:bool):
    mean, std = cifar100_stats(root=str(dataset_path))
    if train:
        transform = transforms.Compose(
            [
                transforms.RandomCrop(size=32),
                transforms.RandomHorizontalFlip(),
                transforms.ToTensor(),
                transforms.Normalize(mean, std),
                Cutout()
            ]
        )
    else:
        transform = transforms.Compose(
            [
                transforms.ToTensor(),
                transforms.Normalize(mean, std),
            ]
        )
    dataset = CIFAR100Indexed(
        root=str(dataset_path), train=train, download=False, transform=transform,
    )

    return dataset


def set_crop_size(dataloader, crop_size: int):
    """
    takes in a dataloader containing dataset CIFAR100Indexed and sets size of the RandomCrop
    """
    for i, t in enumerate(dataloader.dataset.cifar100.transforms.transform.transforms):
        if type(t) == torchvision.transforms.transforms.RandomCrop:
            dataloader.dataset.cifar100.transforms.transform.transforms[i].size = (
                crop_size,
                crop_size,
            )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gpu", default=-1, type=int, help="Index value for the GPU to use",
    )
    parser.add_argument(
        "--crop_size",
        default=24,
        type=int,
        help="Crop size used in data transformations.",
    )
    parser.add_argument(
        "--kernel_size",
        default=6,
        type=int,
        help="Kernel size for max pooling layer in WideResNet",
    )
    parser.add_argument(
        "--width_factor",
        default=8,
        type=int,
        help="How many times wider compared to normal ResNet.",
    )
    parser.add_argument("--depth", default=16, type=int, help="Number of layers.")
    parser.add_argument(
        "--adaptive",
        default=True,
        type=bool,
        help="True if you want to use the Adaptive SAM.",
    )
    parser.add_argument(
        "--batch_size",
        default=128,
        type=int,
        help="Batch size used in the training and validation loop.",
    )
    parser.add_argument("--dropout", default=0.0, type=float, help="Dropout rate.")
    parser.add_argument(
        "--epochs", default=200, type=int, help="Total number of epochs."
    )
    parser.add_argument(
        "--label_smoothing",
        default=0.1,
        type=float,
        help="Use 0.0 for no label smoothing.",
    )
    parser.add_argument(
        "--learning_rate",
        default=0.1,
        type=float,
        help="Base learning rate at the start of the training.",
    )
    parser.add_argument("--momentum", default=0.9, type=float, help="SGD Momentum.")
    parser.add_argument(
        "--threads", default=2, type=int, help="Number of CPU threads for dataloaders."
    )
    parser.add_argument("--rho", default=2.0, type=int, help="Rho parameter for SAM.")
    parser.add_argument(
        "--weight_decay", default=0.0005, type=float, help="L2 weight decay."
    )
    args = parser.parse_args()

    print(args)

    initialize(args, seed=42)

    if args.gpu == -1:
        # Set CUDA_DEVICE_ORDER so the IDs assigned by CUDA match those from nvidia-smi
        os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
        # Get the first available GPU
        DEVICE_ID_LIST = GPUtil.getFirstAvailable()
        DEVICE_ID = DEVICE_ID_LIST[0]  # grab first element from list
        device = torch.device(
            f"cuda:{DEVICE_ID}" if torch.cuda.is_available() else "cpu"
        )
        # # Set CUDA_VISIBLE_DEVICES to mask out all other GPUs than the first available device id
        # os.environ["CUDA_VISIBLE_DEVICES"] = str(DEVICE_ID)
        # # Since all other GPUs are masked out, the first available GPU will now be identified as GPU:0
        # print('Device ID (unmasked): ' + str(DEVICE_ID))
        # print('Device ID (masked): ' + str(0))
        # device = torch.device(f"cuda:0" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(
            f"cuda:{args.gpu}" if torch.cuda.is_available() else "cpu"
        )

    dataset_train = get_dataset(train=True)
    dataset_test = get_dataset(train=False)

    train_set = torch.utils.data.DataLoader(
        dataset_train,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.threads,
    )
    test_set = torch.utils.data.DataLoader(
        dataset_test,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.threads,
    )
    set_crop_size(train_set, args.crop_size)
    print(train_set.dataset.cifar100.transforms.transform.transforms)
    set_crop_size(test_set, args.crop_size)
    print(test_set.dataset.cifar100.transforms.transform.transforms)

    fp = (
            get_project_path()
            / "models"
            / "last_minute"
            / f"wrn100class_crop{args.crop_size}_width{args.width_factor}_depth{args.depth}.pt"
    )
    fp.parent.mkdir(parents=True, exist_ok=True)

    log = Log(log_each=10)

    model = WideResNet(
        depth=args.depth,
        width_factor=args.width_factor,
        dropout=args.dropout,
        kernel_size=6,
        in_channels=3,
        labels=100,
    ).to(device)

    base_optimizer = torch.optim.SGD
    optimizer = SAM(
        model.parameters(),
        base_optimizer,
        rho=args.rho,
        adaptive=args.adaptive,
        lr=args.learning_rate,
        momentum=args.momentum,
        weight_decay=args.weight_decay,
    )
    scheduler = StepLR(optimizer, args.learning_rate, args.epochs)

    lowest_loss = np.inf
    for epoch in range(args.epochs):
        model.train()
        log.train(len_dataset=len(train_set))

        for inputs, targets, idx in train_set:
            inputs = inputs.to(device)
            targets = targets.to(device)

            # first forward-backward step
            enable_running_stats(model)
            predictions, _ = model(inputs)  # Ignore the embedding output
            loss = smooth_crossentropy(predictions, targets)
            loss.mean().backward()
            optimizer.first_step(zero_grad=True)

            # second forward-backward step
            disable_running_stats(model)
            predictions_2nd, _ = model(inputs)  # Ignore the embedding output
            smooth_crossentropy(predictions_2nd, targets).mean().backward()
            optimizer.second_step(zero_grad=True)

            with torch.no_grad():
                correct = torch.argmax(predictions.data, 1) == targets
                log(model, loss.cpu(), correct.cpu(), scheduler.lr())
                scheduler(epoch)

        model.eval()
        log.eval(len_dataset=len(test_set))
        epoch_loss = 0.0
        epoch_correct = 0.0
        epoch_count = 0.0
        with torch.no_grad():
            for inputs, targets, idx in test_set:
                inputs = inputs.to(device)
                targets = targets.to(device)

                predictions, _ = model(inputs)  # XXXXX add embedding outputs
                loss = smooth_crossentropy(predictions, targets)
                batch_loss = loss.sum().item()
                epoch_loss += batch_loss
                correct = torch.argmax(predictions, 1) == targets
                batch_correct = correct.sum().item()
                epoch_correct += batch_correct
                epoch_count += len(targets)
                log(model, loss.cpu(), correct.cpu())

        log.flush()

        if epoch_loss < lowest_loss:
            print(
                f"Epoch {epoch} achieved a new lowest_loss of {epoch_loss}. Saving model to disk."
            )
            lowest_loss = epoch_loss
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "loss": epoch_loss,
                    "correct": epoch_correct,
                    "size": epoch_count,
                    "accuracy": epoch_correct / epoch_count,
                },
                str(fp),
            )
