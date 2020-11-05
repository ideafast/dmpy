
This file contains some notes as a reminder on how to run these apps. Python
code can be run in a few different ways, so this is only one of the possible
ways.

*** This file is a work in progress an may not be up to date ***

- Make sure you have a python interpreter installed. I recommend Anaconda

- If you haven't done so already, create a virtual environment for this
  IdeaFast project. Install the necessary packages in that environment
*** (TBD: figure out which those are ...) ***.
  Make sure to use Python 3.8 or newer in this environment.
  Below I assume you named your environment 'ideafast'

- Download and unpack our python code somewhere. Make sure you unpack
  it in a folder that does not include spaces in its name.

- If you have not already done so, decide on a folder where you want to
  download the data to. This will be called the 'data folder' below; data
  files will be downloaded to subfolders of that folder.

- Start a command prompt and change the current directory to the 'src' subfolder
  of the folder where you unpacked our code

- Activate the python environment you created before in this prompt. Using
  anaconda that would be:

    conda activate ideafast

- You can now run the apps in that prompt. For instance to run dmpapp, use

    python -m dmpapp

  Without further arguments that will print a usage message


Notes specific to dmpapp:

- You can check your login state with:

    python -m dmpapp state

- If you are not logged in yet, do so first. Use "python -m dmpapp login" (or
  "python -m dmpapp login <username>" if you never logged in before on this
  computer). You will be asked for your password and authentication code for the
  DMP site (Data Management Platform - i.e. https://data.ideafast.eu/ )

- After a succesful login, 'dmpapp state' tells you your are logged in
  and gives a list of 'studies' you have access to.
  If you don't see any accessable studies listed, or the login failed
  (or you don't have a user name and password for
  https://data.ideafast.eu/ ), contact the site's administrator

- The first thing you want to do after logging in is to configure dmpapp:

  - Use "python -m dmpapp configure <data-folder>" to tell dmpapp where your
    data folder is (the folder where data will be downloaded to). For example:

      python -m dmpapp configure c:\data\idea-fast


  - Use "python -m dmpapp study <study-id>" to tell dmpapp what your default
    study ID is. You don't need to type the full study ID, just a few
    characters is enough. For instance, for the "IDEA-FAST Feasibility study"
    (ID 7b6aac1c-366b-4259-ab05-9c6f47f956e5), you can use

      python -m dmpapp study 7b6

- To ensure your login is still valid and to update the list of studies you have
  access to, type

      python -m dmpapp refresh

- To retrieve the current list of files for your default study type

      python -m dmpapp files

    This will download the list of available files and save it in both CSV
    and JSON format in your data folder. The JSON version will be used by
    the "list", "sync", and "onfile" commands described below, so don't
    delete or edit it,

- To summarize or list information from the file list you just downloaded,
  use the 'dmpapp list' command.
    dmpapp list [-p <participant>*] [-k <devicekind>*] [-d <deviceid>*] [-id <fileid>*]

  Use the -p, -k, -d, and/or -id options to select participants, device kinds
  device ids or file ids. If you pass one of those flags but no values, the output
  will include information for each of the available values. If you do not pass
  one one of those options, the output will aggregate over that parameter instead.

  For example:

    python -m dmpapp list -p
    python -m dmpapp list -k
    python -m dmpapp list -p -k


  The first will print a list of all participants, the second a list of all
  device kinds and the third a list of all participant-device kind combinations.
  At the moment of writing, that last command prints:

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

  You can filter output by passing arguments to the options. For example

    python -m dmpapp list -p -k BED MMM

  prints:

                    file_cnt  size_total
      subject kind
      KS4YJHD MMM          1   602982400
      KV4XTG4 MMM          2  1203525632
      KZH4ZYY BED         32   627823124

  If you include the '-id' parameter the output will include details per file:

      python -m dmpapp list -k AX6 -id

      subject kind  device_id                         t_from                                file_name                               file_id
      KV4XTG4  AX6  AX646ZRDQ  2020-09-02T09:27:00.299+00:00                   6011458_0000000002.cwa  0c072d53-438a-449f-a96e-3022737e75ab
      KV4XTG4  AX6  AX6YACHK2  2020-08-26T09:26:34.504+00:00                   6011503_0000000001.cwa  12af910e-3cb3-483e-922f-f395ea8ab014
      KS4YJHD  AX6  AX656JZRH  2020-09-10T22:00:00.000+00:00  KS4YJHD-AX656JZRH-20200911-20200916.zip  20fad84f-fdff-4bc3-81c5-8b69f31fd1a5
      KS4YJHD  AX6  AX6X4XSE7  2020-09-03T22:00:00.000+00:00  KS4YJHD-AX6X4XSE7-20200904-20200909.zip  9651de9d-e7ac-46ec-9f70-b19e63f1bca4
      KZH4ZYY  AX6  AX656JZRH  2020-07-17T10:48:43.874+00:00                   6011061_0000000001.cwa  e41f1873-6030-4ac0-8931-16f5ae71b921
      KZH4ZYY  AX6  AX6VSZYG5  2020-07-09T10:41:29.499+00:00                   6011809_0000000001.cwa  fbdf21ac-4fd6-4db5-bb55-cf14f14f10b6

  For the -p, -k and -d options you need to fully specify the arguments. For the -id
  option a prefix of the file_id is enough.

  If you want a more detailed list, consider opening the CSV or JSON version of the
  file list downloaded by the 'files' command

- To download files from the server that you haven't downloaded yet,
  use the 'dmpapp sync' command.
    dmpapp sync [-p <participant>*] [-k <devicekind>*] [-d <deviceid>*] [-id <fileid>*] [-cap <n>]

  The argument (except '-cap') work similar to how they work in the -list command,
  except that now you must provide at least one argument for each option you specify.
  This command will download matching files that you haven't downloaded yet. The files
  are downloaded into subfolders of your data folder, as <participant>/<deviceid>/<filename>
  (where <filename> is the original file name).

  The number of downloads per invocation is capped to the maximum you specify with the -cap
  option. The default is '-cap 1'; you will probably want to pass a higher cap if you want
  to download data in bulk.

  Note that there are a few cases where the generated download path is not unique. These
  cases will be skipped and a warning will be printed. If you run into this, you can specify
  an explicit file ID to select and download the version you want.

