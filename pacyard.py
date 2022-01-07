#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
import glob
import sqlite3
# from six.moves import urllib
from six.moves import configparser
import tarfile
import hashlib
import time
import requests
import datetime
import inspect


# -----------------------------------------------------------------------------------
def debug_print(txt, end='\n'):
    """
    Print  txt  in case the globale variable  verbose  is True
    or if this is an error message

    :param  txt:   text to print
    """

    global verbose
    if not verbose  and  not txt.startswith('Error'):
        return

    if not hasattr(debug_print, "last_len"):
        debug_print.last_len = 0

    space = ' ' * (len(inspect.stack(0)) - 1)
    txt = space + txt

    delta_len = max(0, debug_print.last_len - len(txt))
    debug_print.last_len = len(txt)
    print(txt + ' ' * delta_len, end=end)
    sys.stdout.flush()
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def try_unlink(file_path):
    """
    tries to unlink a file

    :param file_path:  path to the file
    """

    try:
        os.unlink(file_path)
    except:
        pass
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def open_sqlite_db(db_file):
    """
    create a database connection to the SQLite database, specified by db_file
    and create the tables if they don't happen to exist

    :param db_file:  database file
    :return:         Connection object
    """

    sqliteConnection = create_db_connection(db_file)
    create_tables(sqliteConnection)

    return sqliteConnection
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def create_db_connection(db_file):
    """
    create a connection to the SQLite database, specified by db_file

    :param db_file:  database file
    :return:         Connection object
    """

    try:
        debug_print('connecting DB ' + db_file)
        sqliteConnection = sqlite3.connect(db_file)
        return sqliteConnection
    except:
        debug_print("Error:  Can't connect DB")
        sys.exit(1)
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def create_tables(sqliteConnection):
    """
    create tables if they don't yet exist
    first check, if table(s) have the correct (newest) format

    :param   sqliteConnection:  SQLite3 connection object
    :return:
    """

    debug_print("creating DB-tables (if they don't exist)")

    sql_inst_packages = 'CREATE TABLE IF NOT EXISTS '                       +\
                        'installed_packages '                               +\
                        '(name TEXT PRIMARY KEY, repo TEXT NOT NULL);'

    sql_local_mirror  = 'CREATE TABLE IF NOT EXISTS '                       +\
                        'local_mirror '                                     +\
                        '(name TEXT, filename TEXT NOT NULL PRIMARY KEY, '  +\
                        'repo TEXT NOT NULL, builddate INTEGER);'

    sql_db_hashes     = 'CREATE TABLE IF NOT EXISTS '                       +\
                        'db_hashes '                                        +\
                        '(epoch_day INTEGER, hash TEXT);'

    sql_db_downloads  = 'CREATE TABLE IF NOT EXISTS '                       +\
                        'db_downloads '                                     +\
                        '(db_timestamp TEXT, epoch_day INTEGER, '           +\
                        'db_url TEXT PRIMARY KEY);'


    # if table db_hashes doesn't have the new format (3 columns): drop table
    cursor = sqliteConnection.cursor()
    try:
        cursor.execute('SELECT * from db_downloads LIMIT 0')
        if len(cursor.description) != 3:
            sqliteConnection.execute('DROP TABLE db_downloads')
    except:
        pass
    cursor.close()


    try:
        sqliteConnection.execute(sql_inst_packages)
        sqliteConnection.execute(sql_local_mirror)
        sqliteConnection.execute(sql_db_hashes)
        sqliteConnection.execute(sql_db_downloads)
        sqliteConnection.commit()
    except:
        debug_print("Error: Can't create DB-tables")
        sys.exit(1)
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def import_packages_files(sqliteConnection):
    """
    (re-)import the list of installed packages,
    contained in the files   packages_<REPO>_<HOSTNAME>.txt

    remove packages from table  local_mirror  which aren't installed (anymore)

    :param   sqliteConnection:  SQLite3 connection object
    :return:
    """

    debug_print('importing lists of installed packages')

    sql_empty  = 'DELETE FROM installed_packages;'
    sql_insert = 'INSERT OR IGNORE INTO installed_packages '  +\
                 '(name, repo) VALUES(?,?);'
    sql_delete = 'DELETE FROM local_mirror ' +\
                 'WHERE name NOT IN (SELECT name FROM installed_packages);'

    sqliteConnection.execute(sql_empty)
    pkg_files = glob.glob('packages_*.txt')
    for p_file in pkg_files:
        debug_print('  ' + p_file)
        repo = p_file.split('_')[1]

        if not os.path.exists(repo):
            try:
                os.mkdir(repo)
            except:
                debug_print("Error: Can't create directory  " + repo)
                sys.exit(1)

        with open(p_file, 'r') as f:
            lines = f.read().splitlines()
            for entry in lines:
                try:
                    entry = (entry.strip(), repo)
                    sqliteConnection.execute(sql_insert, entry)
                except:
                    debug_print("Error: Can't write into DB")
                    sys.exit(1)

    sqliteConnection.commit()

    # remove packages from table  local_mirror  which aren't installed (anymore)
    sqliteConnection.execute(sql_delete)

    sqliteConnection.commit()
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def get_repo_list(sqliteConnection):
    """
    read the list of repos from the installed_packages table

    :param   sqliteConnection:  SQLite3 connection object
    :return: list of repos
    """

    debug_print("reading list of repos form the DB-table 'installed_packages'")

    repo_list = list()
    sql = 'SELECT DISTINCT repo FROM installed_packages;'
    cursor = sqliteConnection.cursor()
    cursor.execute(sql)
    for row in cursor.fetchall():
        debug_print(('  ' + row[0]))
        repo_list.append(row[0])

    cursor.close()
    return repo_list
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def read_config(repo_list, file_name='config.ini'):
    """
    read the config file
    ( since python's configparser can't handle duplicate keys,
      a small workaround is needed )

    :param:   file_name:  name of the config-file
    :param:   repo_list:  list repos (of installed packages)
    :return:  dict with the parsed content
    """

    debug_print('reading ' + file_name)
    config_dict = dict()

    with open(file_name, 'r') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if line.startswith('['):
            suffix = 1
        if line.startswith('Server ='):
            lines[i] = line.replace('Server', '_server_' + str(suffix))
            suffix += 1
    s_config = ''.join(lines)

    config = configparser.ConfigParser()

    try:
        config.read_string(s_config)
    except:
        try:
            import StringIO
            buf = StringIO.StringIO(s_config)
            config.readfp(buf)
        except:
            debug_print("Error: Can't parse config-file")
            sys.exit(1)

    try:
        config_dict['num_versions_to_keep'] = \
                      config.getint('options', 'NumVersionsToKeep')
    except:
        config_dict['num_versions_to_keep'] = 3
    config_dict['Arch'] = config.get('options', 'Arch')

    mirrorlist = list()
    if 'mirrorlist' in config.sections():
        mirrorlist_section = config.options('mirrorlist')
        for key in mirrorlist_section:
            if key.startswith('_server_'):
                mirrorlist.append(config.get('mirrorlist', key))
        mirrorlist = list(set(mirrorlist))

    for repo in repo_list:
        config_dict[repo] = list()
        repo_section = config.options(repo)
        for key in repo_section:
            if key.startswith('_server_'):
                config_dict[repo].append(config.get(repo, key))
            if key == 'include'  and  config.get(repo, key) == 'mirrorlist':
                config_dict[repo] += mirrorlist
        config_dict[repo] = list(set(config_dict[repo]))

    arch = config.get('options', 'Arch')
    for repo in repo_list:
        for i, mirror in enumerate(config_dict[repo]):
            config_dict[repo][i] = \
                    mirror.replace('$repo', repo).replace('$arch', arch)

    return config_dict
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def remove_old_packages(sqliteConnection, config):
    """
    delete older packages from DB and HDD

    :param  sqliteConnection:  SQLite3 connection object
    :param  config:            dict with the parsed content of the config-file
    """

    debug_print("removing older packages from HDD")

    sql_select = 'SELECT name, filename, repo, builddate ' +\
                 'FROM local_mirror '                      +\
                 'ORDER BY name ASC, builddate DESC;'

    remove_dict = dict()
    num_versions_to_keep = config['num_versions_to_keep']
    last_name = None
    cursor = sqliteConnection.cursor()
    cursor.execute(sql_select)

    for row in cursor.fetchall():
        if row[0] != last_name:
            last_name = row[0]
            num_version = 1
        else:
            num_version += 1
            if num_version > num_versions_to_keep:
                remove_dict[row[1]] = row[2]
                debug_print('  ' + row[1])

    for filename in remove_dict.keys():
        sql_delete = "DELETE FROM local_mirror " +\
                     "WHERE filename=?;"
        sqliteConnection.execute(sql_delete, (filename,))
        repo = remove_dict[filename]
        file_path = os.path.join(repo, filename)
        try_unlink(file_path)
        try_unlink(file_path + '.sig')

    sqliteConnection.commit()
    cursor.close()
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def remove_old_dbhashes(sqliteConnection):
    """
    delete db-file - hashes from DB which are older than 60 days

    :param  sqliteConnection:  SQLite3 connection object
    """

    debug_print("removing older DB-file - hashes from DB")

    seconds = time.time()
    epoch_day = int(seconds / 24 / 3600)
    limit = str(epoch_day - 60)
    sql_delete = "DELETE FROM db_hashes " + \
                 "WHERE epoch_day < " + limit + ";"

    sqliteConnection.execute(sql_delete)
    sqliteConnection.commit()
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def remove_old_dbdownloads(sqliteConnection):
    """
    delete db-download entries from DB which are older than 60 days

    :param  sqliteConnection:  SQLite3 connection object
    """

    seconds = time.time()
    epoch_day = int(seconds / 24 / 3600)
    limit = str(epoch_day - 60)
    debug_print("removing older DB-file - download entries from DB")

    sql_delete = "DELETE FROM db_downloads " + \
                 "WHERE epoch_day < " + limit + ";"

    sqliteConnection.execute(sql_delete)
    sqliteConnection.commit()
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def remove_package_files_not_in_db(sqliteConnection, repo_list):
    """
    remove packages files from HDD which are not listed in the DB

    :param   sqliteConnection:  SQLite3 connection object
    :param   repo_list:         list of repositories
    """

    debug_print("removing package-files from HDD which are not in DB")

    for repo in repo_list:
        file_path_list = glob.glob(repo + '/*.pkg.*')

        # remove .sig - files from listing
        for i, file_path in enumerate(file_path_list):
            if file_path.endswith('.sig'):
                file_path_list[i] = file_path[:-4]
        file_path_list = set(file_path_list)

        for file_path in file_path_list:
            filename = os.path.basename(file_path)
            if not is_in_localmirror(sqliteConnection, filename):
                debug_print(' removing package ' + filename)
                try_unlink(file_path)
                try_unlink(file_path + '.sig')
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def cleanup_table_localmirror(sqliteConnection):
    """
    remove entries from table  local_mirror
    when the package-file doesn't exist (anymore) on harddrive

    :param   sqliteConnection:  SQLite3 connection object
    :return: list of repos
    """

    debug_print("cleaning up DB-table 'local_mirror'")

    sql_select = 'SELECT filename, repo FROM local_mirror;'
    cursor = sqliteConnection.cursor()
    cursor.execute(sql_select)

    for row in cursor.fetchall():
        file_path = os.path.join(row[1], row[0])
        if not os.path.exists(file_path):
            debug_print('removing package ' + \
                         os.path.basename(file_path) + ' from DB')
            sql_delete = "DELETE FROM local_mirror " +\
                         "WHERE filename=?;"
            sqliteConnection.execute(sql_delete, (row[0],))

    sqliteConnection.commit()
    cursor.close()
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def update_table_localmirror(sqliteConnection, name, filename, repo, builddate):
    """
    insert record (in case it doesn't exist) into table local_mirror

    :param   sqliteConnection:  SQLite3 connection object
    :param name:      name of the package
    :param filename:  filename of the package
    :param repo:      repository
    :param builddate: builddate of the package file
    """

    debug_print('-> DB-table "local_mirror": ' + filename)

    sql_insert = 'INSERT OR IGNORE INTO local_mirror '  +\
                 '(name, filename, repo, builddate) VALUES(?,?,?,?);'

    values = (name, filename, repo, builddate)
    sqliteConnection.execute(sql_insert, values)
    sqliteConnection.commit()
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def download(url, file_path):
    """
    download the file and save it under file_path

    :param  url:   url to the file
    :file_path:    path/filename where to save the file
    :return:       True on success, otherwise False
    """

    if os.path.exists(file_path):
        debug_print('[already exists ] ' + os.path.basename(file_path), end='\r')
        return True
    else:
        debug_print('[downloading ] ' + os.path.basename(file_path))

    cmd = "wget -c -T 5 -O '" + file_path + "' " + url
    if not verbose:
        cmd += ' > /dev/null 2>&1'

    try:
        return_value = os.system(cmd)
        if return_value == 0:
            return True
        else:
            raise
    except:
        debug_print("Error: Can't download file")
        try_unlink(file_path)
        return False
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def download_db(sqliteConnection, mirror, repo, arch):
    """
    download the <repo>.db.tar.gz - file from the mirror
    and calculate it's md5-hash
    if the repo-DB is unknown (i.e. wasn't already downloaded before)

    :param  sqliteConnection  SQlite3 connection
    :param  mirror            url of the mirror (containing $repo and $arch)
    :param  repo:             name of the repository
    :param  arch:             architecture
    :return:                  path of the downloaded file, md5sum
    """

    db_file_name = repo + '.db.tar.gz'
    db_url = mirror.replace('$repo', repo).replace('$arch', arch)
    db_url = os.path.join(db_url, db_file_name)

    #request_headers = requests.head(db_url, verify=False)
    #db_last_modified = request_headers['last-modified']

    try:
        from subprocess import Popen, PIPE
        response = Popen('curl -kI ' + db_url + ' 2>&1',
                          shell=True, stdout=PIPE).stdout.read()
        for val in response.split('\r\n'):
            if val.lower().startswith('last-modified'):
                db_timestamp = val[15:]
        if is_db_known(sqliteConnection, db_url, db_timestamp):
            debug_print('skipping download of repo DB-file (known database)')
            return None, None
    except:
        debug_print("no Last-Modified entry in request headers")
        db_timestamp = None

    file_path = os.path.join('tmp', db_file_name)
    try_unlink(file_path)

    status = download(db_url, file_path)
    if status is False:
        return None, None

    add_known_db(sqliteConnection, db_url, db_timestamp)

    with open(file_path, 'rb') as f:
        md5sum = hashlib.md5(f.read()).hexdigest()

    return file_path, md5sum
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def is_db_known(sqliteConnection, db_url, db_timestamp):
    """
    check, whether the repo-DB is known, i.e. was already downloaded

    :param  sqliteConnection     SQlite3 connection
    :param  db_url:              URL of the repo-DB
                                 (like https://somearch.mirror.org/core.db.tar.gz)
    :param  db_timestamp:        creation time of the repo-DB
    :return
    """

    sql = "SELECT COUNT() "              +\
          "FROM db_downloads "     +\
          "WHERE db_url=? AND db_timestamp=?;"

    cursor = sqliteConnection.cursor()
    cursor.execute(sql, (db_url, db_timestamp))
    numberOfRows = cursor.fetchone()[0]
    cursor.close()

    if numberOfRows == 0:
        return False
    else:
        return True
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def add_known_db(sqliteConnection, db_url, db_timestamp):
    """
    add the db_url and its creation time to the database of known,
    (i.e. already downloaded) repo DBs

    :param  sqliteConnection     SQlite3 connection
    :param  db_url:              URL of the repo-DB
                                 (like https://somearch.mirror.org/core.db)
    :param  db_timestamp:        creation time of the repo-DB
    :return
    """

    if db_timestamp is None:
        return

    sql_insert = 'INSERT OR REPLACE INTO db_downloads '  +\
                 '(db_timestamp, epoch_day, db_url) VALUES(?,?,?);'

    seconds = time.time()
    epoch_day = int(seconds / 24 / 3600)

    sqliteConnection.execute(sql_insert, (db_timestamp, epoch_day, db_url))
    sqliteConnection.commit()
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def get_repo_content(file_path):
    """
    get the content of the downloaded <repo>.db.tar.gz - file
    and delete the file

    :param   file_path   path of the repo.db - file
    :return:             dict with the content of the repo
                         (%FILENAME% , %FILE% , %BUILDDATE%)
    """

    repo_content = dict()
    debug_print('extracting repo DB-file ...')
    with tarfile.open(file_path, "r:gz") as tar:
        debug_print('collecting package info ...')

        for member in tar.getmembers():
            if not member.name.endswith("/desc"):
                continue
            debug_print(member.name[:-5], end='\r')
            f = tar.extractfile(member)
            lines = f.readlines()
            f.close()

            file_name = name = builddate = None
            lines[0] = lines[0].decode('utf-8').strip()
            for i, line in enumerate(lines[1:]):
                try:
                    lines[i+1] = line.decode('utf-8').strip()
                    if lines[i] == '%FILENAME%':
                        filename = lines[i+1]
                    elif lines[i] == '%NAME%':
                        name = lines[i+1]
                    elif lines[i] == '%BUILDDATE%':
                        builddate = int(lines[i+1])
                    if filename and name and builddate:
                        repo_content[filename] = [name, builddate]
                        debug_print("Error: in get_repo_content() " +\
                               file_path + " " + member)
                        sys.exit(1)
                except:
                    pass

    debug_print(' ', end='\r')
    try_unlink(file_path)

    return repo_content
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def is_installed(sqliteConnection, name):
    """
    check, whether the package  name  is in the list of installed packages

    :param  sqliteConnection     SQlite3 connection
    :param  name:                name of the package
    :return
    """

    sql = "SELECT COUNT() "              +\
          "FROM installed_packages "     +\
          "WHERE name=?;"

    cursor = sqliteConnection.cursor()
    cursor.execute(sql, (name,))
    numberOfRows = cursor.fetchone()[0]
    cursor.close()

    if numberOfRows == 0:
        return False
    else:
        return True
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def is_in_localmirror(sqliteConnection, filename):
    """
    check, whether the package  filename  is in table  local_mirror

    :param  sqliteConnection     SQlite3 connection
    :param  filename:            filename of the paackage
    :return
    """

    sql = "SELECT COUNT() FROM local_mirror " +\
          "WHERE filename=?;"

    cursor = sqliteConnection.cursor()
    cursor.execute(sql, (filename,))
    numberOfRows = cursor.fetchone()[0]
    cursor.close()

    if numberOfRows == 0:
        return False
    else:
        return True
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def is_hash_known(sqliteConnection, hash_dbfile):
    """
    check, whether the hash exists in table  db_hashes

    :param  sqliteConnection     SQlite3 connection
    :param  hash_dbfile:         hash of the downloaded db file
    :return
    """

    sql = "SELECT COUNT() FROM db_hashes " +\
          "WHERE hash=?;"

    cursor = sqliteConnection.cursor()
    cursor.execute(sql, (hash_dbfile,))
    numberOfRows = cursor.fetchone()[0]
    cursor.close()

    if numberOfRows >= 1:
        return True
    else:
        return False
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def add_hash(sqliteConnection, hash_dbfile):
    """
    add  hash_dbfile  to table  db_hashes

    :param  sqliteConnection     SQlite3 connection
    :param  hash_dbfile:         hash of the downloaded db-file
    :return
    """

    sql_insert = 'INSERT OR IGNORE INTO db_hashes '  +\
                 '(epoch_day, hash) VALUES(?,?);'

    seconds = time.time()
    epoch_day = int(seconds / 24 / 3600)
    entry = (epoch_day, hash_dbfile)
    sqliteConnection.execute(sql_insert, entry)
    sqliteConnection.commit()
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def get_num_of_new_packages(sqliteConnection, name, filename, builddate):
    """
    return the number of packages 'already in the local mirror
    with a newer or equally new builddate

    :param  sqliteConnection     SQlite3 connection
    :param  name:                name of the paackage
    :param  filename:            filename of the package
    :return
    """

    sql = "SELECT COUNT() FROM local_mirror"    + \
          " WHERE name=?"                       + \
          " AND builddate >= " + str(builddate) + ";"

    cursor = sqliteConnection.cursor()
    cursor.execute(sql, (name,))
    numberOfRows = cursor.fetchone()[0]
    cursor.close()

    return numberOfRows
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def update_localmirror(sqliteConnection, repo_list, config):
    """
    update the local mirror:
      for every repo and every mirror for this repo:
        download newer versions of the installed packages
        and update DB

    :param   sqliteConnection:  SQLite3 connection object
    :param   repo_list:         list of repositories
    :param   config:            dict with the parsed content of the config-file
    :return:
    """

    debug_print('updating local mirror')

    arch = config['Arch']

    for repo in repo_list:
        for mirror in config[repo]:
            file_path, hash_dbfile = download_db(sqliteConnection, mirror, repo, arch)

            if hash_dbfile is None:
                continue
            if is_hash_known(sqliteConnection, hash_dbfile):
                debug_print('skipping repo DB-file (known hash of database)')
                continue
            add_hash(sqliteConnection, hash_dbfile)

            repo_content = get_repo_content(file_path)
            for filename in repo_content.keys():
                name, builddate = repo_content[filename]

                if not is_installed(sqliteConnection, name):
                    debug_print(' [not installed  ] ' + filename, end='\r')
                    continue
                num = get_num_of_new_packages(sqliteConnection,
                                              name, filename, builddate)
                if num >= config['num_versions_to_keep']:
                    debug_print(' [version too old] ' + filename, end='\r')
                    continue

                file_path = os.path.join(repo, filename)
                url = mirror.replace('$repo', repo).replace('$arch', arch)
                url = os.path.join(url, filename)
                debug_print(' ', end='\r')
                download(url, file_path)
                url += '.sig'
                file_path += '.sig'
                download(url, file_path)
                update_table_localmirror(sqliteConnection, name,
                                         filename, repo, builddate)
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def create_sub_dirs(repo_list):
    """
    Create the sub-dirs (if they don't exist)
    one for each resp, for the package-files
    plus a tmp-dir (for the <reponame>.db.tar.gz - files)

    :param   repo_list:    list of repositories
    """

    def create_sub_dir(sub_dir):
        if not os.path.exists(sub_dir):
            try:
                os.mkdir(sub_dir)
            except:
                print("Error:  Can't create sub-dir " + sub_dir)
                sys.exit(1)

    for sub_dir in repo_list:
        create_sub_dir(sub_dir)
    create_sub_dir('tmp')
# -----------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------
def main(work_dir, database_file, config_file):
    """
    - update the local mirror, or
    - (re-)import the list of installed packages

    :param work_dir:        working directory (with database and config-file)
    :param database_file:   SQLite3 - dataabase
    :param config_file:     configuration-file
    :return:
    """

    global verbose
    if "-v" in sys.argv:
        verbose = True

    os.chdir(work_dir)
    sqliteConnection = open_sqlite_db(database_file)

    if '-i' in sys.argv:
        import_packages_files(sqliteConnection)
        sys.exit(0)

    cleanup_table_localmirror(sqliteConnection)
    repo_list = get_repo_list(sqliteConnection)
    config = read_config(repo_list, config_file)
    create_sub_dirs(repo_list)

    update_localmirror(sqliteConnection, repo_list, config)

    remove_old_dbhashes(sqliteConnection)
    remove_old_dbdownloads(sqliteConnection)
    remove_old_packages(sqliteConnection, config)
    remove_package_files_not_in_db(sqliteConnection, repo_list)

    sqliteConnection.close()
    sys.exit(0)
# -----------------------------------------------------------------------------------

if __name__ == '__main__':
    verbose = False
    main( '/hdd/ArchLinux',   # working directory
          'pacyard.db',       # database file
          'pacyard.conf')     # config file
