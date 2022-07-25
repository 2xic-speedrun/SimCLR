from regex import P
from torch import optim, nn
import pytorch_lightning as pl
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchmetrics.functional import pairwise_cosine_similarity

# just using the example model from https://pytorch.org/tutorials/beginner/blitz/cifar10_tutorial.html


class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 6, 5)
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(6, 16, 5)
        self.fc1 = nn.Linear(16 * 5 * 5, 120)
        self.fc2 = nn.Linear(120, 84)
        self.fc3 = nn.Linear(84, 100)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = torch.flatten(x, 1)
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.softmax(self.fc3(x), dim=1)
        return x


class Projection(nn.Module):
    def __init__(self):
        super().__init__()
        self.projection = nn.Linear(100, 10)

    def forward(self, x):
        x = torch.sigmoid(self.projection(x))
        return x


class SimpleModel(pl.LightningModule):
    def __init__(self, model, projection):
        super().__init__()
        self.model = model
        self.projection = projection

    def forward(self, X):
        return self.model(X)

    def training_step(self, batch, batch_idx):
        x, y = batch
#        print(x.shape)
#        print(y.shape)
#        z = self.model(x)
        z_k_1 = self.projection(self.model(x))
        z_k_2 = self.projection(self.model(y))

        N = len(batch)
        
 #       print(z_k_1)
#        print(z_k_2)

        z = sum([(z_k_1[i], z_k_2[i]) for i in range(N)], ())
        assert len(z) == 2*N

        s = torch.zeros((2*N, 2*N))
        for i in range(N * 2):
            for j in range(2*N):
                results: torch.Tensor = (
                    z[i].T * z[j]) / (torch.norm(z[i]) * torch.norm(z[j]))
#                print(results.sum(dim=-1))
                s[i][j] = results.sum(dim=-1)

                #(z[i] - z[j]).sum(0)

            #    pairwise_cosine_similarity(z[i].reshape(1,-1), z[j].reshape(1,-1))
          #      print(s[i][j])

        temperature = 0.5
        #torch.autograd.set_detect_anomaly(True)

        def loss(i, j):
            return torch.log(
                torch.exp(s[i][j]) / temperature
            ) / (
                torch.sum(
                    torch.tensor([
                        torch.exp(s[i][k] / temperature) for k in range(N) if k != i
                    ])
                )
            )

        # loss_value =
        loss_value = None
        for k in range(1, N):
            if loss_value is None:
                loss_value = loss(2 * k - 1, 2*k) + loss(2*k, 2 * k - 1)
            else:
                loss_value += loss(2 * k - 1, 2*k) + loss(2*k, 2 * k - 1)
#        print(loss_value)

        self.log("train_loss", loss_value)
        return loss_value

    """
    def test_step(self, batch, batch_idx):
        x, y = batch
        z = self.model(x)
        loss = nn.functional.cross_entropy(z, y)
        batch_size = x.shape[0] 
        predictions = torch.argmax(z, dim=1)
        # if all are non zero accuracy = batch size
        accuracy = batch_size - torch.count_nonzero(predictions - y)

        self.log("test_loss", loss)
        self.log("test_accuracy", accuracy / float(batch_size))
    """

    def configure_optimizers(self):
        optimizer = optim.Adam(self.parameters(), lr=1e-3)
        return optimizer
