# Pacyard - a selective local mirror for pacman (Arch Linux):

pacyard is a local mirror for Arch Linux packages.

This local mirror downloads, via cron-job, **not all** Arch **packages**, but **only** those for which it has been **configured**.

It is meant to run on a *(small)* local server and do its work there – so to speak – in the backyard *(hence the name)*.

There is no need to have ArchLinux installed on the server. *In principle, the script should also run on Windows, but I haven't tested that.*

The script `pacyard.py` operating on the local mirror may run under Python2 as well as Python3 *(in my case on a Linux based videorecorder 'vuduo2' with Python 2.79)*. As the actual download workhorse the script makes use of `wget`.

## Usecase
If several devices in your LAN run ArchLinux, pacyard can significantly **reduce the download data volume** for package updates.

In addition, the faster your LAN is compared to your internet connection, the **faster** the **update process** runs, because pacyard does not download the packages on-demand, but in advance – via cron-job.
 

## Installation and configuration:
### mirror:
On the server, the Python script `pacyard.py` should be called via cron-job. The first parameter of the `main()` - function *(in line 785)* specifies the working directory and must be adjusted accordingly. The corresponding configuration file `pacyard.conf` *(see ReadMe_ConfigFile.txt)* must be located in the working directory.

 In order to tell the program which packages to download, invoke `./pacyard.py -i` . Thereby all files *(in the same directory)* with the pattern `packages_<REPO>_<HOSTNAME>.txt` are read and the included package names are stored in the *(if necessary newly created)* SQLite-DB `pacyard.db`. These txt files can for example be generated with the script `gen_package_lists.sh`. After the import these txt-files can be deleted.

`pacyard.py -v` prints many debug messages. This can be used to check if everything works well when called manually.

### Client machines:
On the Arch client-machines, the Python script `pacman_xfer.py` must be configured as pacman's `XferCommand` in `/etc/pacman.conf`:

    XferCommand = /path/to/script/pacman_xfer.py %o %u

Edit the script `pacman_xfer.py` and configure the address to your local mirror in the definitions section (e.g.: `local_mirror = ftp://192.168.0.90`).

For 'cosmetic' reasons, in `/etc/pacman.conf` you should set
`SigLevel = Required DatabaseNever`. (*Some context*: https://wiki.archlinux.org/index.php/Pacman/Package_signing , https://bbs.archlinux.org/viewtopic.php?pid=1503389#p1503389)

## Notes on `pacyard.py`:

The script, which may run under Python2 and Python3, requires the modules os, sys, glob, sqlite3, six, tarfile, hashlib, time, and inspect.

It iterates over all servers which are configured for each repository and downloads the `NumVersionsToKeep` latest versions of packages – available in total.

Outdated packages or packages that are not configured for download *(anymore)* are automatically deleted. Existing versions of package files will not be downloaded again.

## Notes on pacman_xfer.py:

The Python script requires the os, sys, wget, urllib and progressbar modules.
The script extracts the name of the repository as well as the filename from the input parameter with the download URL. *(If a URL of a repository you are using has an 'exotic' structure, it might be necessary to slightly adjust the logic implemented in lines 115 - 118).*

If the local mirror cannot be reached or the file in question is not *(yet)* available there, the package will be downloaded from the original URL. An asterisk * in front of the dowload progress bar indicates that the package exists on the local mirror and is being loaded from there.

 ## License:
 GPL v3

