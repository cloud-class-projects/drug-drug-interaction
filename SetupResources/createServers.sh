nova boot --flavor m1.medium --image "futuresystems/ubuntu-14.04" --key_name ibwood-india-key ibwood_4
nova boot --flavor m1.medium --image "futuresystems/ubuntu-14.04" --key_name ibwood-india-key ibwood_5
nova boot --flavor m1.medium --image "futuresystems/ubuntu-14.04" --key_name ibwood-india-key ibwood_6
nova floating_ip_associate ibwood_4 149.165.158.121
nova floating_ip_associate ibwood_5 149.165.158.122
nova floating_ip_associate ibwood_6 149.165.158.123
rm ~/.ssh/known_hosts
