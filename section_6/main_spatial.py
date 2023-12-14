from section_6.rate_rnn_with_io import ReluRateRNNWithIO
from section_6.utils import generate_batch_of_wm_targets, generate_sensory_input_spatial, generate_blank_sensory_input, loss_function_spatial, errors_spatial

from tqdm import tqdm
import matplotlib.pyplot as plt

import torch
from torch.optim import Adam
from torch import randn


## Define our task
n_a = 20    # number of possible angles

T_prestim = 0.1     # in seconds
T_stim = 0.5
T_delay = 1.0
T_resp = 0.1

A = 1.0
kappa = 3.0


## Define our system
dt = 0.01
tau = 0.1
N = 10
batch_size = 32
rnn = ReluRateRNNWithIO(dt, N, n_a + 1, 2, tau)    # Refer to notes to understand why the i/o are these sizes!


## Define training machinery
lr = 1e-3
opt = Adam(rnn.parameters(), lr)
num_batches = 5000
losses = [] # Store for loss curve plotting
angle_errors = [] # Store for angle error curve plotting
magnitude_errors = [] # Store for magnitude error curve plotting


## Define simulation parameters
T_prestim = 0.2     # in seconds
T_stim = 0.5
T_delay = 0.0
T_resp = 0.1

prestim_timesteps = int(T_prestim / dt)
stim_timesteps = int(T_stim / dt)
delay_timesteps = int(T_delay / dt)
resp_timesteps = int(T_resp / dt)

eps1 = 0.9
eps2 = (1 - eps1**2) ** 0.5
C = 0.


## Initialise simulation, including the first noise term
eta_tilde = randn(batch_size, N)


### Begin training
for b in tqdm(range(num_batches)):

    opt.zero_grad()

    target_indices = generate_batch_of_wm_targets(n_a, batch_size)
    rnn.initialise_u(batch_size)

    prestim_sensory_input = generate_blank_sensory_input(n_a, True, batch_size)
    for ts in range(prestim_timesteps):
        eta_tilde = (eps1 * eta_tilde) + (eps2 * randn(batch_size, N))
        eta = eta_tilde * C
        rnn.step_dynamics(prestim_sensory_input, eta, False)

    stim_sensory_input = generate_sensory_input_spatial(target_indices, True, n_a, A, kappa)
    for ts in range(stim_timesteps):
        eta_tilde = (eps1 * eta_tilde) + (eps2 * randn(batch_size, N))
        eta = eta_tilde * C
        rnn.step_dynamics(stim_sensory_input, eta, False)

    delay_sensory_input = generate_blank_sensory_input(n_a, True, batch_size)
    for ts in range(delay_timesteps):
        eta_tilde = (eps1 * eta_tilde) + (eps2 * randn(batch_size, N))
        eta = eta_tilde * C
        rnn.step_dynamics(delay_sensory_input, eta, False)

    batch_network_outputs = []

    resp_sensory_input = generate_blank_sensory_input(n_a, False, batch_size)
    for ts in range(resp_timesteps):
        eta_tilde = (eps1 * eta_tilde) + (eps2 * randn(batch_size, N))
        eta = eta_tilde * C
        voltage, network_output = rnn.step_dynamics(resp_sensory_input, eta, return_output=True)
        batch_network_outputs.append(network_output)

    all_network_outputs = torch.stack(batch_network_outputs, 1)
    loss = loss_function_spatial(target_indices, all_network_outputs, n_a)
    angle_error, magnitude_error = errors_spatial(target_indices, all_network_outputs.detach(), n_a)
    loss.backward()
    opt.step()

    losses.append(loss.item())
    angle_errors.append(angle_error.item())
    magnitude_errors.append(magnitude_error.item())

    if b % 200 == 0:
        plt.close('all')
        fig, axes = plt.subplots(3)
        
        axes[0].plot(losses)
        axes[1].plot(angle_errors)
        axes[2].plot(magnitude_errors)

        print(losses[-10:])
        plt.savefig('section_6/spatial_losses.png')

