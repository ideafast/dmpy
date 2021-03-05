import argparse
import itertools
import re
import sys
from getpass import getpass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import colorama
import pandas as pd
from colorama import Fore, Style
from pandas.core.groupby.generic import DataFrameGroupBy

from .core.connection import DmpConnection
from .core.data_cache import DmpDataCache
from .core.file_db import DmpFileDb, DmpFileInfo
from .core.user_info import DmpUserInfo
from .core.utils import FileTransaction, save_json_with_backup


def _run_dmp_state():
    cache = DmpDataCache(None)
    cache_folder_name = cache.data_folder_raw
    if cache_folder_name is None or cache_folder_name == "":
        print(f"Data folder: {Fore.LIGHTRED_EX}Not Configured{Fore.RESET}")
        print(
            f'{Fore.LIGHTYELLOW_EX}Please run "dmpapp configure <datafolder>"{Fore.RESET}'
        )
    else:
        print(f"Data folder: {Fore.LIGHTGREEN_EX}{cache_folder_name}{Fore.RESET}")
    with DmpConnection("dmpapp") as dc:
        login_state = dc.login_state
        print(
            f"{Fore.LIGHTBLACK_EX}State file: {login_state.appstate.state_file_name}{Fore.RESET}"
        )
        if login_state.username is None:
            print(f"  User name: {Fore.LIGHTRED_EX}Not Specified{Fore.RESET}")
        else:
            print(
                f"  User name: {Fore.LIGHTGREEN_EX}{login_state.username}{Fore.RESET}"
            )
        if not dc.is_logged_in:
            print(f"{Fore.LIGHTRED_EX}You are not logged in{Fore.RESET}")
        else:
            info = login_state.user_info
            print(
                f'  Name: {Fore.LIGHTGREEN_EX}{info.firstname or ""} {info.lastname or ""}{Fore.RESET}'
            )
            print(f'  Email: {Fore.LIGHTGREEN_EX}{info.email or ""}{Fore.RESET}')
            print(
                f'Account Created: {Fore.LIGHTGREEN_EX}{info.created or ""}{Fore.RESET}'
            )
            print(
                f'Account Expires: {Fore.LIGHTGREEN_EX}{info.expires or ""}{Fore.RESET}'
            )
            dstd = login_state.default_study
            if dstd is None:
                print(f"  Default Study: {Fore.LIGHTRED_EX}Not selected!{Fore.RESET}")
            else:
                print(f"  Default Study: {Fore.LIGHTCYAN_EX}{dstd}{Fore.RESET}")
            studies = info.studies
            if studies is not None:
                if len(studies) == 0:
                    print(
                        f"{Fore.LIGHTRED_EX}You do not have access to any studies!{Fore.RESET}"
                    )
                else:
                    print(f"You have access to {len(studies)} studies:")
                    for study_id, study_name in studies.items():
                        print(
                            f"{Fore.LIGHTCYAN_EX}{study_id}{Fore.RESET} = "
                            f"{Fore.YELLOW}{study_name}{Fore.RESET}"
                        )
            pass
    pass


def _run_dmp_study(study_prefix: str):
    ccy = Fore.LIGHTCYAN_EX
    crd = Fore.LIGHTRED_EX
    cor = Fore.YELLOW
    cyw = Fore.LIGHTYELLOW_EX
    c0 = Fore.RESET
    ok = False
    with DmpConnection("dmpapp") as dc:
        login_state = dc.login_state
        if not dc.is_logged_in:
            print(f"{crd}You are not logged in{c0} (Cannot validate study IDs)")
        else:
            if study_prefix is None or study_prefix == "":
                login_state.change_study(None)
            else:
                info = login_state.user_info
                ids = info.matching_study_ids(study_prefix)
                if len(ids) == 0:
                    print(
                        f'{crd}No known study IDs matching "{ccy}{study_prefix}{crd}" found{c0}'
                    )
                elif len(ids) > 1:
                    print(
                        f'{cyw}Prefix "{ccy}{study_prefix}{cyw}" is ambiguous.{c0} Matches:'
                    )
                    for stid in ids:
                        print(f"      {cor}{stid}{c0}")
                else:
                    login_state.change_study(ids[0])
                    ok = True
    if ok:
        _run_dmp_state()
    pass


def _run_dmp_login(username: Optional[str]):
    crd = Fore.LIGHTRED_EX
    cgn = Fore.LIGHTGREEN_EX
    c0 = Fore.RESET
    with DmpConnection("dmpapp") as dc:
        login_state = dc.login_state
        username = username or login_state.username

        if username is None or username == "":
            print(f"{crd}No user name known - please specify{c0}")
            username = input("User Name: ")
            if username is None or username == "":
                raise ValueError("No user name specified nor archived")
        password = getpass(
            f'Password for user "{username}": '
        )  # cannot use color in that string

        if len(password) == 0:
            print(f"{crd}No password provided - aborting{c0}")
            exit(1)

        code = input("Six-digit authentication code: ")
        if not re.match(r"^\d{6}$", code):
            print(f'{crd}"{code}" is not a six-digit number...{c0}')
            exit(1)
        response = dc.login_request(username, password, code)

        info = response.content
        cookie = response.cookies["connect.sid"]
        login_state.change_user(username, cookie, info)

        pass
    print(f"{cgn}Login Succesful!{c0}. New login state:")
    _run_dmp_state()
    pass


def _run_dmp_refresh():
    crd = Fore.LIGHTRED_EX
    cor = Fore.YELLOW
    c0 = Fore.RESET
    with DmpConnection("dmpapp") as dc:
        login_state = dc.login_state
        if not dc.is_logged_in:
            print(f"{crd}You are not logged in{c0}")
        else:
            print(f"{cor}Refreshing information from server...{c0}")
            uinf = dc.user_info_request()
            info = uinf.content
            dui = DmpUserInfo(info)
            if dui.username != login_state.username:
                raise ValueError(
                    f"User name ({dui.username}) does not match state ({login_state.username})"
                )
            if dui.studies is None:
                raise ValueError("No study information present in response - aborting")
            print(f"{cor}Updating user state...{c0}")
            login_state.change_user(login_state.username, login_state.cookie, info)
    _run_dmp_state()
    pass


def _save_files_as_csv(csv_name: Union[str, Path], files: List[Dict[str, Any]]):
    """
    Save a list of file info records to a CSV file
    :param csv_name: The name of the file to write
    :param files: The list of file info records (in the same form as is saved to JSON)
    """
    with FileTransaction.start(csv_name) as trx:
        with trx.tmp_name.open("w") as csv:

            def write_line(fields: List[Any]):
                texts = [str(x) for x in fields]  # assumption: no quotes needed
                line = ",".join(texts)
                csv.write(line)
                csv.write("\n")
                pass

            write_line(
                [
                    "participant",
                    "devicekind",
                    "device",
                    "file_name",
                    "t_start",
                    "t_end",
                    "t_upload",
                    "file_size",
                    "file_id",
                ]
            )
            for finf in files:
                write_line(
                    [
                        finf["participantId"],
                        finf["deviceKind"],
                        finf["deviceId"],
                        finf["fileName"],
                        finf["timeStart"],
                        finf["timeEnd"],
                        finf["timeUpload"],
                        finf["fileSize"],
                        finf["fileId"],
                    ]
                )
                pass
            pass
        trx.commit()
    pass


def _run_dmp_files(study_id_keys: List[str]):
    ccy = Fore.LIGHTCYAN_EX
    crd = Fore.LIGHTRED_EX
    cgn = Fore.LIGHTGREEN_EX
    cor = Fore.YELLOW
    cyw = Fore.LIGHTYELLOW_EX
    cbl = Fore.LIGHTBLUE_EX
    c0 = Fore.RESET
    cache = DmpDataCache(None)
    if not cache.is_configured:
        print(
            f'{crd}No data folder configured. Run "dmpapp configure <your-data-folder>" first{c0}'
        )
        exit(1)
    datafolder = cache.data_folder
    with DmpConnection("dmpapp") as dc:
        login_state = dc.login_state
        if not dc.is_logged_in:
            print(f"{crd}You are not logged in{c0}")
        else:
            info = login_state.user_info
            studies = info and info.studies
            if studies is None:
                print(f"{crd}Study information is not available{c0}")
            else:
                if study_id_keys is None or len(study_id_keys) == 0:
                    defstudy = login_state.default_study
                    if defstudy is None:
                        print(
                            f"{crd}No study IDs provided and no default study selected{c0}"
                        )
                        print(
                            f"Consider using {cgn}dmpapp study{c0} to establish a default study"
                        )
                        return
                    print(f"Using the selected default study: {ccy}{defstudy}{c0}")
                    study_id_keys = [defstudy]
                study_map = info.get_study_map()
                study_ids: List[str] = []
                for key in study_id_keys:
                    sids = info.matching_study_ids(key)
                    if len(sids) == 0:
                        print(f'{cyw}Warning{c0}: "{key}" did not match any studies')
                    study_ids.extend(sids)
                if len(study_ids) == 0:
                    print(f"{crd}Error{c0}: no matching studies found")
                print(f"(Saving information to folder {cyw}{datafolder}{c0})")
                for study_id in study_ids:
                    study_name = study_map[study_id]
                    print(
                        f'Processing study "{cgn}{study_id}{c0}" ("{cbl}{study_name}{c0}"):'
                    )
                    files = dc.study_files_request(study_id)
                    onm = f"study.{study_id}.files.json"
                    count = len(files)
                    print(f'  Saving {cor}{count}{c0} entries to "{ccy}{onm}{c0}":')
                    save_json_with_backup(datafolder / onm, files)
                    csvnm = f"study.{study_id}.files.csv"
                    print(f'  Saving {cor}{count}{c0} entries to "{cor}{csvnm}{c0}":')
                    _save_files_as_csv(datafolder / csvnm, files)
                pass
            pass
    pass


def _run_dmp_configure(folder: str):
    folder = Path(folder)
    if not folder.is_absolute():
        raise ValueError(f'Expecting an absolute path but got "{folder}"')
    cache = DmpDataCache(None)
    cache.configure_data_folder(folder)
    cgn = Fore.LIGHTGREEN_EX
    c0 = Fore.RESET
    print(f"Data folder now is {cgn}{cache.data_folder_raw}{c0}")
    pass


def _vlen(x: Optional[List[str]]) -> int:
    if x is None:
        return -1
    else:
        return len(x)


def _norm_list(x: Optional[List[str]]) -> Optional[Union[str, List[str]]]:
    if x is None:
        return None
    else:
        n = len(x)
        if n == 0:
            return None
        elif n == 1:
            return x[0]
        else:
            return x


def _get_filtered_list(
    study: Optional[str],
    participants: Optional[List[str]],
    kinds: Optional[List[str]],
    devices: Optional[List[str]],
    fids: Optional[List[str]],
) -> Optional[DataFrameGroupBy]:
    crd = Fore.LIGHTRED_EX
    cor = Fore.YELLOW
    c0 = Fore.RESET
    study0 = study
    if study is None or study == "":
        with DmpConnection("dmpapp") as dc:
            login_state = dc.login_state
            study = login_state.default_study
            if study is None:
                print(
                    f'{crd}No default study ID configured{c0} (use "dmpapp study" to do so)'
                )
                return None

    cache = DmpDataCache(None)
    db = DmpFileDb(cache)
    allfiles = db.study_files(study)
    if allfiles is None:
        print(f"{crd}Study file list is missing!{c0}")
        if study0 is None:
            print(f'Use "{cor}dmpapp files{c0}" to download it')
        else:
            print(f'Use "{cor}dmpapp files {study}{c0}" to download it')
        return None

    n_p = _vlen(participants)
    n_k = _vlen(kinds)
    n_d = _vlen(devices)
    n_id = _vlen(fids)

    if n_p < 0 and n_k < 0 and n_d < 0 and n_id < 0:
        print(f"{cor}Warning: No filters or groupings specified{c0}")
        selection = allfiles
    else:
        x_p = _norm_list(participants)
        x_k = _norm_list(kinds)
        x_d = _norm_list(devices)
        x_id = _norm_list(fids)
        selection = db.filter(allfiles, x_p, x_k, x_d, x_id)

    renamed = selection.rename(
        columns={
            "fileId": "file_id",
            "fileName": "file_name",
            "fileSize": "size",
            "participantId": "subject",
            "deviceKind": "kind",
            "deviceId": "device_id",
            "timeStart": "t_from",
            "timeEnd": "t_to",
            "timeUpload": "t_up",
            "studyId": "study_id",
        }
    )

    groupkeys = []
    if n_p >= 0:
        groupkeys.extend(["subject"])
    if n_k >= 0:
        groupkeys.extend(["kind"])
    if n_d >= 0:
        groupkeys.extend(["device_id"])
    if n_id >= 0:
        groupkeys.extend(["file_id"])
    if len(groupkeys) == 0:
        # Just a trick to make everything work in case no filters/groups were
        # given:
        groupkeys.extend(["study_id"])
    grouped = renamed.groupby(groupkeys)

    return grouped


def _run_dmp_list(
    study: Optional[str],
    participants: Optional[List[str]],
    kinds: Optional[List[str]],
    devices: Optional[List[str]],
    fids: Optional[List[str]],
):
    """
    Implements "dmpapp list"
    :param study: The study ID or None to use the default
    :param participants: The list of participant IDs to select, or an empty list
    to select all and group by participants, or None to not select or group by participant
    :param kinds: The list of device kinds to select, or an empty list
    to select all and group by device kind, or None to not select or group by device kind
    :param devices: The list of device IDs to select, or an empty list
    to select all and group by device ID, or None to not select or group by device ID
    :param fids: The list of file ID prefixes to select, or an empty list
    to select all files, or None to exclude file details (and use file counts instead)
    """
    n_id = _vlen(fids)
    grouped = _get_filtered_list(study, participants, kinds, devices, fids)
    if grouped is None:
        # an error was printed already
        return

    if n_id >= 0:
        # details mode
        frames = [frame for idx, frame in grouped]
        combo = pd.concat(frames)
        combo["t_from_utc"] = combo.apply(lambda df: (df["t_from"])[0:23], axis=1)
        combo["file_id_prefix"] = combo.apply(lambda df: (df["file_id"])[0:14], axis=1)
        combo = combo[
            [
                "subject",
                "kind",
                "device_id",
                "t_from_utc",
                "size",
                "file_name",
                "file_id_prefix",
            ]
        ]
        print(combo.to_string(index=False))

    else:
        # group mode
        summary = grouped.agg(file_cnt=("file_id", "count"), size_total=("size", "sum"))
        # summary2 = summary.reset_index()
        print(summary)
    pass


def _run_dmp_sync(
    study: Optional[str],
    participants: Optional[List[str]],
    kinds: Optional[List[str]],
    devices: Optional[List[str]],
    fids: Optional[List[str]],
    cap: int,
):
    crd = Fore.LIGHTRED_EX
    cgn = Fore.LIGHTGREEN_EX
    cor = Fore.YELLOW
    cyw = Fore.LIGHTYELLOW_EX
    cbl = Fore.LIGHTBLUE_EX
    c0 = Fore.RESET
    cache = DmpDataCache(None)
    if not cache.is_configured:
        print(
            f'{crd}No data folder configured. Run "dmpapp configure <your-data-folder>" first{c0}'
        )
        exit(1)
    db = DmpFileDb(cache)
    with DmpConnection("dmpapp") as dc:
        login_state = dc.login_state
        if not dc.is_logged_in:
            print(f"{crd}You are not logged in{c0}")
            return
        if study is None or study == "":
            study = login_state.default_study
            if study is None:
                print(
                    f'{crd}No default study ID configured{c0} (use "dmpapp study" to do so)'
                )
                return None

        grouped = _get_filtered_list(study, participants, kinds, devices, fids)
        if grouped is None:
            # an error was printed already
            return

        frames = [frame for idx, frame in grouped]
        combo: pd.DataFrame = pd.concat(frames)

        print(f"Synchronizing {cgn}{len(combo)}{c0} selected files")

        study_files = db.study_file_set(study)
        selected_files = study_files.project_ids(
            DmpFileDb.extract_ids(combo, "file_id")
        )

        # Check for duplicate names
        accepted_files: List[DmpFileInfo] = []
        rejected_files: Dict[str, List[DmpFileInfo]] = {}
        sorted_by_path = sorted(selected_files.all(), key=lambda x: str(x.path_name()))
        for fpath, group in itertools.groupby(
            sorted_by_path, key=lambda x: str(x.path_name())
        ):
            files = [dfi for dfi in group]
            if len(files) != 1:
                rejected_files[fpath] = files
                print(
                    f"{crd}Skipping ambiguous files!{c0} "
                    + f'There are {cgn}{len(files)}{c0} distinct files named "{cyw}{fpath}{c0}"'
                )
            else:
                accepted_files.append(files[0])

        outdated_files = [dfi for dfi in accepted_files if not db.is_up_to_date(dfi)]
        # smallest files first
        outdated_files.sort(key=lambda dfi: dfi.file_size)

        print(f"Found {cgn}{len(outdated_files)}{c0} missing our outdated files.")
        remaining = 0
        if cap < len(outdated_files):
            print(
                f"More outdated files than cap! {crd}Capping download count to {cap}{c0}"
            )
            remaining = len(outdated_files) - cap
            outdated_files = outdated_files[0:cap]
        print(
            f"Files selected for download ({cgn}{len(outdated_files)}{c0}, smallest files first):"
        )
        for dfi in outdated_files:
            p = dfi.path_name()
            print(
                f"{cbl}{dfi.file_id}{c0}: {cor}{dfi.file_size:10}{c0} {cgn}{str(p)}{c0}"
            )

        if len(outdated_files) == 0:
            print(f"{cgn}No files to download - all selected files are up to date!{c0}")
        else:
            print(f"Files will be saved as subfolders of {cor}{cache.data_folder}{c0}")
            for dfi in outdated_files:
                print(
                    f"Downloading {cgn}{dfi.path_name()}{c0} ({cbl}{dfi.file_id}{c0})"
                )

                def progress(sz: int) -> None:
                    # TODO: note change
                    filesize = dfi.file_size if dfi.file_size > 0 else sz
                    percent = int(100 * sz / (filesize))
                    print(
                        f"\r{cyw}{sz:10}{c0} / {cbl}{dfi.file_size:10}{c0} / {cor}{percent:3}%{c0}  ",
                        end="",
                    )

                full_name = cache.data_folder / dfi.path_name()
                status = dc.download_file(dfi.file_id, full_name, progress)
                if status == 200:
                    print(f" {cgn}{status} - OK{c0}")
                else:
                    print(f" {crd}{status} - FAIL{c0}")

        if len(rejected_files) > 0:
            print(f"{cbl}Some files were skipped because their name is ambiguous{c0}:")
            for fpath, files in rejected_files.items():
                print(
                    f"  Skipped {crd}{len(files)}{c0} distinct files named {cor}{fpath}{c0}"
                )

        if remaining > 0:
            print(
                f"{cbl}Some files were skipped because there were more than the download cap{c0}:"
            )
            print(
                f"There are {crd}{remaining}{c0} more files to download. Consider using the -cap option"
            )

    pass


def _run_dmp_onefile(study: Optional[str], file_id: str, file_name: Optional[str]):
    ccy = Fore.LIGHTCYAN_EX
    crd = Fore.LIGHTRED_EX
    cgn = Fore.LIGHTGREEN_EX
    cor = Fore.YELLOW
    cyw = Fore.LIGHTYELLOW_EX
    cbl = Fore.LIGHTBLUE_EX
    c0 = Fore.RESET
    cache = DmpDataCache(None)
    if not cache.is_configured:
        print(
            f'{crd}No data folder configured. Run "dmpapp configure <your-data-folder>" first{c0}'
        )
        exit(1)
    db = DmpFileDb(cache)
    with DmpConnection("dmpapp") as dc:
        login_state = dc.login_state
        if not dc.is_logged_in:
            print(f"{crd}You are not logged in{c0}")
            return

        if study is None or study == "":
            study = login_state.default_study
            if study is None:
                print(
                    f'{crd}No default study ID configured{c0} (use "dmpapp study" to do so)'
                )
                return None
        allfiles = db.study_file_set(study)
        files = [record for record in allfiles.matching_id(file_id)]
        if len(files) == 0:
            print(f"{crd}No matches for id prefix {cyw}{file_id}{c0}")
            return
        if len(files) > 1:
            print(
                f"{crd}File prefix {cyw}{file_id}{crd} is ambiguous: {len(files)} matches{c0}"
            )
            return
        dfi = files[0]
        print(
            f"Processing file "
            f"{ccy}{dfi.file_id}{c0} / "
            f"{cgn}{dfi.file_name}{c0} / "
            f"{cyw}{dfi.file_size}{c0} bytes"
        )
        if file_name is None or file_name == "":
            file_name = f"{dfi.participant_id}-{dfi.device_id}-{dfi.file_name}"
        full_name = cache.data_folder / file_name
        print(f"Downloading to {cgn}{full_name}{c0}")

        def progress(sz: int) -> None:
            percent = int(100 * sz / dfi.file_size)
            print(
                f"\r{cyw}{sz:10}{c0} / {cbl}{dfi.file_size:10}{c0} / {cor}{percent:3}%{c0}  ",
                end="",
            )

        status = dc.download_file(dfi.file_id, full_name, progress)
        if status == 200:
            print(f"Status:  {cgn}{status} - OK{c0}")
        else:
            print(f"Status:  {crd}{status} - FAIL{c0}")
    pass


def dmp_app_full_help():
    print(
        """
This is a tool for retrieving data from the IDEA-FAST Data Management Platform (DMP).
The following provides an overview of each arguments for the Command Line Interface (CLI).

state
    Check your current login state, and (cached) study access rights.

configure <data_path>
    Configure (or reconfigure) the folder where downloaded data and metadata will be
    stored

login <username>
    Log in into the server. If 'username' is given, that user will be logged in,
    otherwise the most recent user will be re-logged. This command will ask
    for your password and authentication code.

refresh
    Refresh your cached login information and access rights. This can also be useful
    to test if your login information is still valid

study <study_id>
    Select the default study to be used by other commands. You only need to provide
    the first few characters of the study id, as long as it uniquely identifies a
    study. Valid study IDs that you have access to are listed in the output of
    'dmpapp state' (and, by extension, 'dmpapp refresh' and 'dmpapp login')

files <study_id>
    Download the current list of available files from the server for the given study
    or studies. If you do not provide any study IDs, the default study ID configured
    with 'dmpapp study' is used.
    The lists are saved in the data folder in both JSON and CSV formats. The JSON
    version is used by other commands, so don't modify it directly.

list [-p <participant>*] [-k <devicekind>*] [-d <deviceid>*] [-id <fileid>*]
    List or aggregate file information for the current study, as filtered by the
    arguments. Use the '-p', '-k', '-d', '-id' flags without any arguments to include
    that field in the output without filtering.
    In particular, use '-id' to include file details instead of grouping.
    <fileid> can be a prefix, other selectors must be exact

sync [-p <participant>*] [-k <devicekind>*] [-d <deviceid>*] [-id <fileid>*] [-cap <n>]
    Download files selected by the filter options that were not yet downloaded (or were
    updated)
    The filters are the same as the 'list' command - use that to preview your selection.
    Files are downloaded into subfolders of your working folder as
      <participant>/<device>/<original-file-name>
    If there are multiple files with the same name, those files are skipped.
    By default only 1 file is downloaded pr invocation, equivalent to -cap 1. Set
    the -cap option to a higher number to download multiple files in one go

onefile -id <fileid> -out <filename>
    Download one file. This command is intended for testing only
"""
    )
    pass


def run_dmp_app(*arguments: str):
    arguments = [arg for arg in arguments]  # normalize to a list (not: tuple)
    if len(arguments) == 0:
        dmp_app_full_help()
        exit(0)

    parser = argparse.ArgumentParser(prog="dmpapp")
    subparsers = parser.add_subparsers(dest="command", title="Commands")
    subparsers.required = True

    parser_state = subparsers.add_parser(  # noqa
        "state", help="Print your current login state and accessible studies"
    )

    parser_login = subparsers.add_parser(
        "login", help="Log the named user in (and log out the current user, if any)"
    )
    parser_login.add_argument(
        "username",
        nargs="?",
        type=str,
        help="The user name. If omitted the previously used user name is reused",
    )

    parser_refresh = subparsers.add_parser(  # noqa
        "refresh", help="Refresh your login information from the server"
    )

    parser_files = subparsers.add_parser(
        "files",
        help="Refresh the list of available files from the server for the study (or studies)",
    )
    parser_files.add_argument(
        "studyid",
        nargs="*",
        type=str,
        help='The first few characters of the study ID, repeatable (as listed by the "state" command)',
    )

    parser_configure = subparsers.add_parser(
        "configure",
        help="(re-)configure the folder where data files and metadata will be saved to",
    )
    parser_configure.add_argument(
        "datafolder",
        type=str,
        help="The full path to the data folder, where downloaded data will be stored",
    )

    parser_study = subparsers.add_parser(
        "study", help="(re-)configure the default study id"
    )
    parser_study.add_argument(
        "studyprefix",
        type=str,
        help='The first few characters of a study ID (as listed by the "state" command)',
    )

    parser_list = subparsers.add_parser(
        "list", help="List or aggregate file information for the current study"
    )
    parser_list.add_argument(
        "-p",
        nargs="*",
        type=str,
        dest="list_p",
        help="Select one or more participants, or no arguments to summarize all",
    )
    parser_list.add_argument(
        "-k",
        nargs="*",
        type=str,
        dest="list_k",
        help="Select one or more device kinds (three letter codes), or no arguments to summarize all",
    )
    parser_list.add_argument(
        "-d",
        nargs="*",
        type=str,
        dest="list_d",
        help="Select one or more devices (full ids), or no arguments to summarize all",
    )
    parser_list.add_argument(
        "-id",
        nargs="*",
        type=str,
        dest="list_id",
        help="Select >= 1 file id prefixes, or no arguments to list details for all selected files",
    )

    parser_sync = subparsers.add_parser("sync", help="Download missing files")
    parser_sync.add_argument(
        "-p", nargs="+", type=str, dest="sync_p", help="Select one or more participants"
    )
    parser_sync.add_argument(
        "-k",
        nargs="+",
        type=str,
        dest="sync_k",
        help="Select one or more device kinds (three letter codes)",
    )
    parser_sync.add_argument(
        "-d",
        nargs="+",
        type=str,
        dest="sync_d",
        help="Select one or more devices (full ids)",
    )
    parser_sync.add_argument(
        "-id",
        nargs="+",
        type=str,
        dest="sync_id",
        help="Select one or more file id prefixes",
    )
    parser_sync.add_argument(
        "-cap",
        type=int,
        dest="sync_cap",
        default=1,
        help="Set the maximum number of files to download (default 1)",
    )

    parser_onefile = subparsers.add_parser("onefile", help="Download a single file")
    parser_onefile.add_argument(
        "-id",
        type=str,
        dest="onefile_id",
        required=True,
        help="The file id (or prefix)",
    )
    parser_onefile.add_argument(
        "-out",
        type=str,
        dest="onefile_out",
        help="The output file name, to be saved in the root of the data folder",
    )

    args = parser.parse_args(arguments)

    # print(repr(args))

    cmd: str = args.command
    try:
        colorama.init()  # enable support for colored console output
        if cmd == "state":
            _run_dmp_state()
        elif cmd == "login":
            _run_dmp_login(args.username)
        elif cmd == "refresh":
            _run_dmp_refresh()
        elif cmd == "files":
            _run_dmp_files(args.studyid)
        elif cmd == "configure":
            _run_dmp_configure(args.datafolder)
        elif cmd == "study":
            _run_dmp_study(args.studyprefix)
        elif cmd == "list":
            _run_dmp_list(None, args.list_p, args.list_k, args.list_d, args.list_id)
        elif cmd == "sync":
            cap = args.sync_cap
            if cap < 0:
                cap = 100000
            _run_dmp_sync(
                None, args.sync_p, args.sync_k, args.sync_d, args.sync_id, cap
            )
        elif cmd == "onefile":
            _run_dmp_onefile(None, args.onefile_id, args.onefile_out)
        else:
            print(repr(args))
            raise ValueError(f'Internal error: no handler for command "{cmd}"')
    finally:
        print(f"{Style.RESET_ALL}", end="")
        colorama.deinit()
    pass


def main():
    args = sys.argv
    args = args[1:]
    run_dmp_app(*args)
