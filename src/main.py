import os
import time
from enum import Enum
from jsonmerge import merge

from core_client import Client
from core_client.base.models.v3 import (
    ProcessConfig,
    ProcessConfigLimit,
    ProcessConfigIO
)

CORE_ADDRESS = os.getenv('CORE_ADDRESS', '')
CORE_USERNAME = os.getenv('CORE_USERNAME', '')
CORE_PASSWORD = os.getenv('CORE_PASSWORD', '')

PROCESS_REFERENCE = os.getenv('PROCESS_REFERENCE', 'streamfile')
PROCESS_OUTPUT_PROTOCOL = os.getenv('OUTPUT_PROTOCOL', 'hls')
PROCESS_OUTPUT_PROTOCOL = PROCESS_OUTPUT_PROTOCOL.split(",")

STREAMFILE_FOLDER = os.getenv('STREAMFILE_FOLDER', './streamfiles')
SYNC_INTERVAL_SECONDS = int(os.getenv('SYNC_INTERVAL_SECONDS', 10))

process_config = ProcessConfig(
    id="dummy",
    reference=PROCESS_REFERENCE,
    options=["-loglevel", "info"],
    input=[
        ProcessConfigIO(
            address="dummy",
            id="0",
            options=["-re"]
        )
    ],
    output=[
        ProcessConfigIO(
            address="{srt,name=dummy}",
            id="0",
            options=["-c", "copy", "-f", "hls"]
        )
    ],
    limits=ProcessConfigLimit(
        cpu_usage=0,
        memory_mbytes=0,
        waitfor_seconds=0
    ),
    reconnect=True,
    reconnect_delay_seconds=2,
    stale_timeout_seconds=20,
)


def config_is_uptodate(file_process_config: dict, core_process_config: dict):
    """ """
    compare_config = merge(core_process_config, file_process_config)
    if compare_config == core_process_config:
        return False
    return True


def set_input_file_output(stream_name: str, hls_path: str = ""):
    """generated output configs for a process"""
    hls = ProcessConfigIO(
        id="0",
        address=f"{{memfs}}/{hls_path}{stream_name}.m3u8",
        options=["-c", "copy", "-f", "hls"]
    )
    rtmp = ProcessConfigIO(
        id="0",
        address=f"{{rtmp,name={stream_name}}}",
        options=["-c", "copy", "-f", "flv"]
    )
    srt = ProcessConfigIO(
        id="0",
        address=f"{{srt,mode=publish,name={stream_name}}}",
        options=["-c", "copy", "-f", "mpegts"]
    )
    tee = ProcessConfigIO(
        id="0",
        address="",
        options=["-map", "0", "-c", "copy", "-flags", "+global_header",
                 "-tag:v", "7", "-tag:a", "10", "-f", "tee"]
    )
    available_outputs = {
        "hls": hls,
        "rtmp": rtmp,
        "srt": srt
    }
    if len(PROCESS_OUTPUT_PROTOCOL) == 1:
        output = available_outputs[PROCESS_OUTPUT_PROTOCOL[0]]
    else:
        output = tee
        endpoint = []
        if "hls" in PROCESS_OUTPUT_PROTOCOL:
            endpoint.append(f"[f=hls]{hls.address}")
        if "rtmp" in PROCESS_OUTPUT_PROTOCOL:
            if len(endpoint) != 0:
                endpoint.append("|")
            endpoint.append(f"[f=rtmp]{rtmp.address}")
        if "srt" in PROCESS_OUTPUT_PROTOCOL:
            if len(endpoint) != 0:
                endpoint.append("|")
            endpoint.append(f"[f=mpegts]{srt.address}")
        output.address = ''.join(endpoint)
    return output


class FileProcessConfigType(Enum):
    input = "input"
    output = "output"


def create_file_process_config(
    listdir: str, type: FileProcessConfigType
):
    """creates an process config for each stream file
    and return all conifg as a list.

    Args:
        listdir (str): folder with stream files

    Returns:
        _type_: list of stream file configs
    """
    file_process_list = []
    for stream_file in os.listdir(listdir):
        if stream_file.split(".")[1] == "stream":
            stream = open(f"{listdir}/{stream_file}", 'r')
            for line in stream.readlines():
                file_process_config = process_config
                file_process_config.id = stream_file.split(".")[0]
                file_process_config.input[0].address = f"{line.strip()}"
                if type == "input":
                    file_process_config.output[0] = set_input_file_output(
                        stream_name=stream_file.split(".")[0])
                file_process_list.append(file_process_config)
    return file_process_list


def create_file_processes(file_process_list: list):
    """creates or updates each stream file process
    on the assigned core url.

    Args:
        file_process_list (list): list of stream file configs.
    """
    for file_process in file_process_list:
        is_unknown = True
        for core_process in core_process_list:
            if (file_process.id == core_process.id
                    and core_process.reference == PROCESS_REFERENCE):
                is_unknown = False
                if config_is_uptodate(
                    file_process_config=file_process.dict(),
                    core_process_config=core_process.config.dict()
                ):
                    print(f'update process id "{file_process.id}"')
                    client.v3_process_put(
                        id=core_process.id, config=file_process)
        if is_unknown:
            print(f'create process id "{file_process.id}"')
            client.v3_process_post(config=file_process)


def clear_core_processes(file_process_list: list):
    """removes all processes with PROCESS_REFERENCE
    and if not exists in file_process_list.

    Args:
        file_process_list (list): list of stream file configs.
    """
    for core_process in core_process_list:
        if core_process.reference == PROCESS_REFERENCE:
            is_unknown = True
            for file_process in file_process_list:
                if (file_process.id == core_process.id
                        and core_process.reference == PROCESS_REFERENCE):
                    is_unknown = False
            if is_unknown:
                print(f'delete process id "{core_process.id}"')
                client.v3_process_delete(id=core_process.id)


# core connection and login
client = Client(
    base_url=CORE_ADDRESS,
    username=CORE_USERNAME,
    password=CORE_PASSWORD
)
client.login()

# start the loop
while True:

    try:
        # fetch all running core processes
        core_process_list = client.v3_process_get_list()

        # create a temp. list of stream file configs
        input_process_list = create_file_process_config(
            listdir=STREAMFILE_FOLDER, type="input")

        # create or update stream file processes
        create_file_processes(file_process_list=input_process_list)

        # remove dropped stream file on core
        clear_core_processes(file_process_list=input_process_list)

    except Exception as e:
        print(f"error: {e}")

    time.sleep(SYNC_INTERVAL_SECONDS)
