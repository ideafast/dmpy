# Setup: Installing Dependencies

Follow the [local development setup](./README.md) by downloading and using 
[poetry](https://python-poetry.org/) to install dependencies, then activate the
virtual environment poetry creates via `poetry shell`.

## Running CLI

From the root folder run `poetry run cli` to view the help page and associated commands. An overview of each is presented below. On first use, you should run the `login` and `configure` commands documented below.

### Login: Logging in

Before logging in, please ensure you have an account on the [Data Management Platform (DMP)](https://data.ideafast.eu/), then run:

```sh
$ poetry run cli login
```

You will be prompted for your username, password, and authentication code. 

### State: Overview

Once successfully authenticated, a dotfile folder is created in your home directory (i.e. `~/.dmpapp/`) that stores `state` of the application, such your username, a cookie, location of file database, etc. You can view this state, including the list of `studies` that you have access to by running:

```sh
$ poetry run cli state
```

Outputs:

```
Data folder: /Users/jawrainey/code/ideafast/ideafast-dmp/data
State file: /Users/jawrainey/.dmpapp/login.json
  User name: your_username_
  Name: Jay Rainey
  Email: your_email_
Account Created: 2020-07-21 16:00:33+00:00
Account Expires: 2020-12-02 17:00:33+00:00
  Default Study: f4d96235-4c62-4910-a182-73836554036c
You have access to 2 studies:
8f223906-809c-41aa-8e58-3d4ee1f694b1 = IDEA_Test
72b7492a-f03a-4c57-86ef-879510f36a3d = Hackathon_test
f4d96235-4c62-4910-a182-73836554036c = Hackathon_test2
```

### Configure: File Store Location

To downloaded data you must configure the location where you want to store it by providing a full (_absolute_) path. This folder _must_ exist before running the command:

```sh
$ poetry run cli configure /Users/jawrainey/data/idea-fast/DMP/
```

### Study: Default ID

As the DMP allows multiple studies, you must specify which one to use as a default by either using the few characters of the ID or the complete ID:

```sh
$ poetry run cli study <ID>
```

### Refresh: Keeping Login Validate

Your login will expire after a set period of time. To keep it updated use the `refresh` parameter:

```sh
$ poetry run cli refresh
```

### Files: Current List for Study

To retrieve the current list of files for your default study type. This will download the list of available files and save it in both CSV and JSON format in your data folder (specified above). The JSON version will be used by the `list`, `sync`, and `onfile` commands described below, so please do not delete or edit it the created CSV/JSON database:

```sh
$ poetry run cli files
```

### List: Summarise File Information

To summarize or list information from the downloaded file list, use the `list` command:

```sh
$ poetry run cli list
```

This has a range of optional paramters: `-p` will print a list of all participants, `-k` list of all 
device kinds and `-d` a list of all participant-device kind combinations. 

```sh
$ poetry run cli list [-p <participant>] [-k <devicekind>] [-d <deviceid>] [-id <fileid>]
```

The `-id` command will group and summarise files as follows:

```
              file_cnt   size_total
subject kind
KS4YJHD AX6          2    832598884
        BTF         83  16950931746
        MMM          1    602982400
        VTP          1   1792896117
        YSM          1       395060
KV4XTG4 AX6          2   1108727296
        MMM          2   1203525632
        VTP          2   1695576106
        YSM          2       279130
KZH4ZYY AX6          2    938792960
        BED         32    627823124
        VTP         67   1992363610
```

You can filter output by passing arguments, such as by device (`-k`):

```sh
$ poetry run cli list -p -k BED MMM
```

Outputs:

```sh
              file_cnt  size_total
subject kind
KS4YJHD MMM          1   602982400
KV4XTG4 MMM          2  1203525632
KZH4ZYY BED         32   627823124
```

If you include the '-id' parameter the output will include details per file:

```sh
$ poetry run cli list -k AX6 -id
```

Outputs:

```sh
subject kind  device_id                     t_from_utc                                file_name                               file_id
KV4XTG4  AX6  AX646ZRDQ  2020-09-02T09:27:00.299+00:00                   6011458_0000000002.cwa  0c072d53-438a-449f-a96e-3022737e75ab
KV4XTG4  AX6  AX6YACHK2  2020-08-26T09:26:34.504+00:00                   6011503_0000000001.cwa  12af910e-3cb3-483e-922f-f395ea8ab014
KS4YJHD  AX6  AX656JZRH  2020-09-10T22:00:00.000+00:00  KS4YJHD-AX656JZRH-20200911-20200916.zip  20fad84f-fdff-4bc3-81c5-8b69f31fd1a5
KS4YJHD  AX6  AX6X4XSE7  2020-09-03T22:00:00.000+00:00  KS4YJHD-AX6X4XSE7-20200904-20200909.zip  9651de9d-e7ac-46ec-9f70-b19e63f1bca4
KZH4ZYY  AX6  AX656JZRH  2020-07-17T10:48:43.874+00:00                   6011061_0000000001.cwa  e41f1873-6030-4ac0-8931-16f5ae71b921
KZH4ZYY  AX6  AX6VSZYG5  2020-07-09T10:41:29.499+00:00                   6011809_0000000001.cwa  fbdf21ac-4fd6-4db5-bb55-cf14f14f10b6
```

### Sync: Download Files

To download files from the server that you haven't downloaded yet:

```sh
$ poetry run cli sync
```

Similar to `list` this command has a range of arguments. One difference is the `-cap` option, which is the 
limit on the number of downloads per invocation of the script. This should be overridden when downloading 
files in bulk:

```sh
$ poetry run cli sync [-p <participant>] [-k <devicekind>] [-d <deviceid>] [-id <fileid>] [-cap <n>]
```

### Onefile: Downloading One file

To download a single file for testing you must specify the ID of the file to download and the name that you want to use when saving the file:

```sh
$ poetry run cli onefile [-id <id>] [-out <filename>]
```