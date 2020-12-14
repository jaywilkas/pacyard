#!/usr/bin/python3

# Xfer-script for pacman
#   Tries to download the package from a local mirror.
#   If the mirror in't up or the file is not present, 
#   the package gets downloaded from the original server.

# Script arguments:
#   1st:  represents the local filename(s) as specified by pacman
#   2nd:  represents the download URL as specified by pacman


import os
import sys
import wget
import urllib
import progressbar as pb



# ------ Definitions -------
local_mirror = 'ftp://192.168.0.95/'



#------------------------------------------------------------------------------------
def pbar(downloaded_size, total_size, not_needed):
  """
  Define the layout of the progress bar

  :param downloaded_size:  currently downloaded size [bytes]
  :param total_size:       file size [bytes]
  :param not_needed:       not needed
  """

  if not hasattr(pbar, "bar"):
      pbar.bar = pb.ProgressBar(maxval=total_size,
                                widgets = [ bar_msg_prefix,
                                            pb.Percentage(),
                                            '  ',
                                            pb.Bar(left='[', right=']'),
                                            '  ',
                                            pb.FileTransferSpeed(),
                                            ' | ',
                                            pb.AdaptiveETA() ])
      pbar.bar.start()

  if downloaded_size < total_size:
      pbar.bar.update(downloaded_size)
  else:
      pbar.bar.finish()
#------------------------------------------------------------------------------------



#------------------------------------------------------------------------------------
def download_from_mirror(url_mirror, file_name):
  """
  Download from the original mirror

  :param url_mirror:       original download address as specified by pacman
  :param file_name:        local filename as specified by pacman
  """

  global bar_msg_prefix
  # print(f'url_mirror: {url_mirror}  file_name: {file_name}')

  try:
      bar_msg_prefix = '   '
      wget.download(url_mirror, file_name, bar=pbar)
  except urllib.error.HTTPError as err:
      print(f'   HTTP-Error {err.code}')
      if err.code != 404:
        print(f'     {err.read()}')
  except:
      print('   Unexpected error')
#------------------------------------------------------------------------------------



#------------------------------------------------------------------------------------
def download(url_localmirror, url_mirror, file_name):
  """
  If the file is a package, try to download the package from the local mirror.
  If the package is not present, (or in case of an error) download it from the
  original server.

  :param url_localmirror:  (presumed) download address of local mirror
  :param url_mirror:       original download address as specified by pacmn
  :param file_name:        local filename as specified by pacman
  """

  global bar_msg_prefix

  if  '.pkg.tar.' in url_localmirror:
      try:
          bar_msg_prefix = ' * '
          wget.download(url_localmirror, file_name, bar=pbar)
      except:
          download_from_mirror(url_mirror, file_name)
  else:
      download_from_mirror(url_mirror, file_name)
#------------------------------------------------------------------------------------



#------------------------------------------------------------------------------------
def main():
  file_name = sys.argv[1]
  url_mirror = sys.argv[2]

  # Carve  repo  and  file-name  from the url, so that this works for the urls
  # of the standard-mirrors and as well for the other mirrors configured in
  # /etc/pacman.conf.
  url_tmp = url_mirror.replace('/os/', '/').replace('/x86_64/', '/')
  url_parts  = url_tmp.split('/')
  repo = url_parts[-2]
  file = url_parts[-1]

  url_localmirror = os.path.join(local_mirror, repo, file)

  print(file_name)
  download(url_localmirror, url_mirror, file_name)
#------------------------------------------------------------------------------------



if __name__ == '__main__':
    main()
