[options]
NumVersionsToKeep: number of max. versions per package    
Arch: architecture, currently only x86_64 is supported

[mirrorlist]
Server:  address of 1st mirror (i.e.: https://mirror.f4st.host/archlinux/$repo/os/$arch)
Server:  address of 2nd mirror (i.e.: https://mirror.chaoticum.net/arch/$repo/os/$arch)
Server:  etc
Server:  etc
# as many entries as you like,
# pacyard visits all of them and downloads the NumVersionsToKeep most recent package versions


# definition of all needed repos (typically core, extra, community - and often also multilib)
[core]
Include:  list of servers defined in section mirrorlist
Server:   some other mirror (if needed)
Server:   some other mirror (if needed)
Server:   etc.

[extra]
Include:  list of servers defined in section mirrorlist
Server:   some other mirror (if needed)

[community]
Include:  list of servers defined in section mirrorlist
Server:   some other mirror (if needed)

[multilib]
Include:  list of servers defined in section mirrorlist
Server:   some other mirror (if needed)

# example for another repo (in my case needed for double-commander)
[herecura]
Server = https://repo.herecura.be/herecura/x86_64


