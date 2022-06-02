Rem FIX WSL2 network
sc stop cmservice
sc stop hns
sc stop vmcompute
sc stop lxssmanager

sc start cmservice
sc start hns
sc start vmcompute
sc start lxssmanager

net stop winnat
net start winnat