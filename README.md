# datarhei Core - Streamfile importer
A demonstration of how to make a Python application interact with the datarhei Core.

## Function:
Local files generate FFmpeg processes that take into account the file name and file content (stream URL) and make the corresponding stream URL available as HLS, RTMP and/or SRT stream.

The application is responsive to new files, file changes, and file deletions.

**Limitations:**
H.264 and AAC live-streams.

## Installation steps (Linux/OSX example)

1. Start the Core and enable the built-in RTMP and SRT servers    
    ```sh
    docker run -d --name core \
        --security-opt seccomp=unconfined \
        -p 8080:8080 -p 1935:1935 -p 6000:6000/udp \
        -e CORE_RTMP_ENABLE=true -e CORE_SRT_ENABLE=true \
        datarhei/core:latest
    ```

2. Get the internal `CORE_ADDRESS`   
    ```sh
    docker inspect -f '{{ .NetworkSettings.IPAddress }}' core
    ```

    Example: 172.17.0.2

    *This allows the application to communicate with the Core. As an alternative, you can also use the IP address of the host system.*

3. Build and start the Streamfile-Importer
    ```sh
    git clone github.com/datarhei/core-streamfile
    cd core-streamfile
    docker build -t core-streamfile .
    docker run -d --name core-streamfile \
        -v $PWD/streamfiles:/streamfiles \
        -e CORE_ADDRESS=http://172.17.0.2:8080 \
        -e PROCESS_OUTPUT_PROTOCOL="hls,rtmp,srt" \
        core-streamfile
    ```

4. Create a streamfile in the `streamfiles` directory   
    ```sh
    echo 'https://demo.datarhei.com/memfs/1f33d538-d714-4c7e-9559-46ddb8118f03.m3u8' > mystream.stream
    ```

    The file content (stream url) can be any streaming url such as HTTP, RTSP, RTMP, SRT.

    *The default `SYNC_INTERVAL_SECONDS` is 10.*

5. Check the stream is running
    - `Core API`: http://127.0.0.1:8080/api/v3/process/mystream
    - `HLS` Stream: http://127.0.0.1:8080/memfs/mystream.m3u8
    - `RTMP` Stream: rtmp://127.0.0.1/mystream
    - `SRT` Stream: srt://127.0.0.1:6000/?streamid=mystream

## Enviroments

- `CORE_ADDRESS` (default: unset)
- `CORE_USERNMAE` (default: unset)
- `CORE_PASSWORD` (default: unset)
- `PROCESS_OUTPUT_PROTOCOL` (default: hls, max: hls,rtmp,srt)
- `PROCESS_REFERENCE` (default: streamfile)
- `STREAMFILE_FOLDER` (default: /streamfiles)
- `SYNC_INTERVAL_SECONDS` (default: 10)

## Feature requests

Feel free to clone the repository and do your own customizations.

# Licence
MIT