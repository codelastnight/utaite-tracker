# Utaite Tracker

### Requirements

[Python 2.7.12](https://www.python.org/downloads/release/python-2712/)
```
wget --no-check-certificate https://www.python.org/ftp/python/2.7.11/Python-2.7.11.tgz
tar -xzf Python-2.7.11.tgz  
cd Python-2.7.11
./configure  
make  
sudo make install  
```

Requests Module

```
pip install requests
```
[ffmpeg](https://www.ffmpeg.org/download.html)

[Add the location of ffmpeg.exe to your **PATH** environment variable (.../ffmpeg/bin)](http://askubuntu.com/questions/60218/how-to-add-a-directory-to-the-path)

### Usage

1. Update the BaseDir in config.cfg to the directory that you would like to download to
2. Update the list of utaite in utaites.txt with the utaites that you would like to fetch
    a. Be sure to leave the first line empty
    b. Utaite names entered should be as they appear in address of the utaite wikia, with
         underscores (_) replaced with spaces
         (utaite.wikia.com/wiki/UTAITE_NAME => UTAITE NAME in utaites.txt)
3. Open a command prompt in the directory that Utaite.py was extracted to
     (Shift + right click in windows explorer)
4. Run the script with "python utaite-tracker.py"
5. You will be prompted for your NicoNicoDouga email login and password
6. Watch your utaite collection grow!

#### Notes

For now, all .swf files cannot be downloaded, though since there are very few
of them, this is being left for now. Sometimes non-swf files also have
permissions issues. Usually these resolve when the download is retried on
the next execution of the script.

Since NND throttles speeds for non-premium users, the downloads will probably be
pretty slow. I recommend running this script on the side while doing other things
or overnight. If NND goes into low-economy mode, the script will stop to avoid
downloading very low-quality files.

To stop the script, press Ctrl + C twice in quick succession. This must be done
because the download is wrapped in a try-except block, so the first Ctrl + C
will only make the script think that the current download failed.

The script keeps track of which files have been downloaded based on the file
structure and filenames that it downloads files to. In order to not lose
progress and redownload files, leave the downloaded files where they are
downloaded to.

If an error is encountered that is not explained, please let the developer know!
Send the utaite name and track that encountered the error as well as the error
itself, and the developer will investigate.
