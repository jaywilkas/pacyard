#!/usr/bin/bash

# Ceates files for pacyard
# with the list of installed packages
# of every repo (used on this pc)


# define the list of repositories which are activated in /etc/pacman.conf
REPO_LIST=(core extra community multilib herecura)


echo "creating files in /tmp"

for repo in ${REPO_LIST[@]}; do
  echo $repo
  paclist $repo  | cut -d ' ' -f 1 > /tmp/packages_${repo}_$(hostname).txt
done



