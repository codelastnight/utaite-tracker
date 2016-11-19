from __future__ import unicode_literals

import re
import os
import sys
import ConfigParser
import logging
import subprocess
import getpass
import warnings
import codecs
from HTMLParser import HTMLParser

import youtube_dl
import requests
config_path = "config.cfg"
utaites_path = "utaites.txt"

# Disable console logging.
warnings.filterwarnings("ignore")

# Get configuration file.
config = ConfigParser.RawConfigParser()
config.read(config_path)

# Directory to download songs to.
utaiteBaseDir = config.get("Settings", "BaseDir")

# Utaite page to fetch
utaitePageUrlBase = "http://utaite.wikia.com/wiki/"

# Known groups that should be downloaded seperately.
knownGroups = [["After the Rain"], ["Mafumafu", "Soraru"], ["Soralon"],
               ["Soraru", "Lon"], ["Urata", "Shima", "Aho no Sakata", "Senra"],
               ["96Neko", "Kogeinu", "vipTenchou"], ["Team Pet Shop"], ["USSS"]]

# Regex and fetch from wikia by Stephen Chen.

# CREATE REGEX.
# Pulls out each bulleted item that has an nicovideo reference in it.
listItemRegex = r'<li>.+?href="http://www.youtube.com/(.+?)"(?:.|[\n\r])+?</li>'

unavailableRegex = re.compile(r'<b>(.*?)</b>')

# Titles are a bit weird
titleRegex = []
# Captures the case with no YouTube link
# e.g.    <li> "Attakain Dakara" <a href...
titleRegex.append(re.compile(r'<li>\s*"([^<>]+?)"\s*'))
titleRegex.append(re.compile(r'<li>\s*\'([^<>]+?)\'\s*'))
# Captures the case with YouTube link
# e.g.    <li> "<a... href="https://www.youtube.com/...">Flower Rail</a>" ...
titleRegex.append(re.compile(r'<li>\s*"<a.+?>(.+?)</a>"'))
titleRegex.append(re.compile(r'<li>\s*\'<a.+?>(.+?)</a>\''))

# Regex for capturing other artists on the song.
# e.g.    ... -Arrange ver.- (English Name) feat. Reol and kradness (Date) </li>
extraTitlesRegex = re.compile(r'</a>\s*(-.*-|)\s*(\(.*?\)|)\s*(.+|)\s*\(.*?\)\s*(<b>.*</b>\s*|)</li>')
subtitleRegex = re.compile(r'</a>(\s*|\s*\(.*?\)\s*)(-.*?-)')

# Featured artist list regex.
# e.g.    feat. Reol, Mafumafu, luz, and Soraru
featuredSingerRegex = re.compile(r'feat\. (.*)$')
singerRegex = []
singerRegex.append(re.compile(r'^(.*?)(, | and )(.*)$'))
# Capture artists with links
singerRegex.append(re.compile(r'^<a.*?>(.*?)</a>(, and |, | and |)(.*)$'))
# Capture the last artist in the list.
finalSingerRegex = re.compile(r'<a.*>(.*?)</a>')

# Used to remove links in featured artists or subtitles.
a_href_regex = re.compile(r'^(.*)<a.*>(.*?)</a>(.*)$')

# Used to extract the number of a numbered file to check whether or not a
# particular song has been downloaded already.
numberedFileRegex = re.compile(r'^(\d*) .*?')

# Used to get the audio encoding format of the video file determined by ffmpeg.
# Origin stream number is allowed to be anything because of strange encoding
# in one Hanatan song.
AudioEncodingRegex = re.compile(r'Stream #0:\d -> #0:1 \((.*?) \(')

def progress_indicator(item, total_bytes, bytes_read, bytes_per_second):
    bar_length = 40
    bar_fill = int((float(bytes_read) / float(total_bytes)) * float(bar_length))
    print("\r{0}: [{1}] {2}/{3} kB ({4} kB/s)".format(
        item,
        "=" * bar_fill + "-" * (bar_length - bar_fill),
        int(bytes_read / 1024),
        int(total_bytes / 1024),
        int(bytes_per_second / 1024)).ljust(80)),
    sys.stdout.flush()

# Remove disallowed characters from the given string so that it
# obeys Windows file and folder name conventions.
def fileSafe(s):
    s = s.replace("<", " ")
    s = s.replace(">", " ")
    s = s.replace(":", " ")
    s = s.replace("\"", " ")
    s = s.replace("/", " ")
    s = s.replace("\\", " ")
    s = s.replace("|", " ")
    s = s.replace("?", " ")
    s = s.replace("*", " ")
    while(s.endswith(" ") or s.endswith(".")):
        s = s[:-1]
    return s

artistsDone = []

print ""



# MAIN LOOP
# Loop over all the artists in the utaite file.
with codecs.open(utaites_path, 'r', 'utf-8') as utaites:

    for utaite in utaites:
        utaite = utaite.rstrip()
        if not utaite: continue

        utaiteDir = utaiteBaseDir + fileSafe(utaite) + "/" + fileSafe(utaite) + " Youtube/"

        utaitePageUrl = utaitePageUrlBase + utaite.replace(" ", "_")
        r = requests.get(utaitePageUrl)
        h = HTMLParser()

        if r.status_code == requests.codes.ok:
            # Section off the area that has is in the "List of Covered Songs" box
            s = r.text
            s = s[s.find("List_of_Covered_Songs"):]
            s = s[:s.find(r'<div style="clear:both; margin:0; padding:0;"></div>')]

            # Handle each bulleted item
            track = 0
            for match in re.finditer(listItemRegex, s):
                track = track + 1

                item = match.group(0)

                # DETERMINE IF THE TRACK IS UNAVAILABLE ON NND.
                #doesnt apply to youtube
                #avail_match = unavailableRegex.search(item)
                #if avail_match is not None:
                #    if ("Private" in avail_match.group(1)) or ("Taken down on NND" in avail_match.group(1)):
                #       continue

                # CHECK IF THE TRACK HAS ALREADY BEEN DOWNLOADED.
                # Create folders if they do not exist.
                if not os.path.isdir(utaiteBaseDir + fileSafe(utaite)):
                    os.mkdir(utaiteBaseDir + fileSafe(utaite))
                if not os.path.isdir(utaiteDir):
                    os.mkdir(utaiteDir)

                # Loop through the files in the utaite directory. A song is
                # uniquely identified by its artist and track number.
                found = False
                for filepath in os.listdir(utaiteDir):
                    file_match = numberedFileRegex.search(filepath)
                    if file_match is not None:
                        if track == int(file_match.group(1)):
                            found = True
                            break

                if found: continue

                title = None
                # Match the title.
                for tRegex in titleRegex:
                    tm = tRegex.search(item)
                    if tm is not None:
                        title = tm.group(1)
                        break

                if title is None:
                    title = "<Unknown>"
                else:
                    title = h.unescape(title)

                artists = []

                # Match extra parts of the title and featured singers.
                st = subtitleRegex.search(item)
                if st is not None:
                    title = title + " " + st.group(2)

                # Remove links in the title.
                st = a_href_regex.search(title)
                while st is not None:
                    title = st.group(1) + st.group(2) + st.group(3)
                    st = a_href_regex.search(title)

                # EXTRACT FEATURED ARTISTS AND EXTRA TITLE PARTS.
                fm = extraTitlesRegex.search(item)
                if fm is not None:
                    # Extract artists from extra title.
                    featuredArtists = fm.group(3)
                    fs = featuredSingerRegex.search(featuredArtists)
                    if fs is not None:
                        featuredSingers = fs.group(1)
                        for sRegex in singerRegex:
                            sm = sRegex.search(featuredSingers)
                            if sm is not None:
                                artist = sm.group(1)
                                separator = sm.group(2)
                                newRest = sm.group(3)
                        artists.append(artist)
                        rest = newRest

                        change = False

                        while separator == ", ":
                            for sRegex in singerRegex:
                                sm = sRegex.search(rest)
                                if sm is not None:
                                    artist = sm.group(1)
                                    separator = sm.group(2)
                                    newRest = sm.group(3)
                                    change = True
                            if not change:
                                break
                            artists.append(artist)
                            rest = newRest
                            change = False

                        fs = finalSingerRegex.search(rest)
                        if fs is None:
                            if not rest.isspace():
                                artists.append(rest.lstrip().rstrip())
                        else:
                            artists.append(fs.group(1))

                # DETERMINE IF THE SONG SHOULD BE DOWNLOADED.
                downloadSong = True

                # Determine if the artists fit a known group.
                for group in knownGroups:
                    if set(group) == set(artists):
                        downloadSong = False
                        break

                # Determine if the collaboration has been downloaded already.
                for artist in artists:
                    if artist.lower() in artistsDone:
                        downloadSong = False

                nicoUrl = match.group(1)

                if downloadSong:
                    asksks = raw_input()
                    if asksks =="n":

                        sys.exit(0)
                    else:
                        pass
                    # DOWNLOAD VIDEO.
                    print utaite.replace("_", " ") + " - " + title
                    if True:
                        # Download the video.
                        #filename of audio file
                        audio_dir = utaiteDir + str(track) + " " + fileSafe(title)
                        urlFull = "http://www.youtube.com/"+ nicoUrl
                        #youtube_dl options
                        ydl_opts = {
                            'format': 'bestaudio/best',
                            'postprocessors': [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'mp3',
                                'preferredquality': '192',
                            }],
                            'outtmpl': audio_dir,
                        }
                        try:
                            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                                ydl.download([urlFull])
                        except:
                            print "Could not download the video"
                            continue

                        print ""
                        # Build featured artists string.
                        featured = ""
                        for artist in artists:
                            featured = featured + artist + ", "
                        # Remove trailing comma and space.
                        featured = featured[:-2]
                        # Build the tags for the audio file.
                        artist_tag = utaite
                        title_tag = title
                        if featured is not "":
                            title_tag = title_tag + " (feat. " + featured + ")"
                        album_tag = utaite + "YT"
                        genre_tag = "Utaite"
                        track_tag = str(track)

                        # Direct output to null to avoid crowding the
                        # terminal window.
                        FNULL = open(os.devnull, 'w')
                        subprocess.call(['ffmpeg', '-i',audio_dir , '-vn',
                            '-acodec', 'copy', '-metadata', 'title=' + title_tag,
                            '-metadata', 'artist=' + artist_tag, '-metadata',
                            'album=' + album_tag, '-metadata', 'track=' + track_tag,
                            '-metadata', 'genre=' + genre_tag, '-metadata',
                            'album_artist=' + utaite.replace("_", " "),
                            '-id3v2_version', '3',
                            audio_dir + output_format],
                            stdout=FNULL, stderr=subprocess.STDOUT)
                        print " Done!"
                        print ""

                            # CLEAN UP UNNEEDED FILES.
                            #pretty sure there is none

        # Mark the artist as having been completed to avoid downloading copies
        # of collaborations.
        artistsDone.append(utaite.lower())
