from datetime import time

import math
import os
import time
import xml.etree.ElementTree as ElementTree
from html import unescape
from typing import List

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import SRTFormatter

import boto3
from pytube import YouTube, Caption

bucket = os.getenv("BUCKET", "")
video_ids = os.getenv("VIDEO_IDS", "tYTwz0Cr9cA")
caption_names = os.getenv("CAPTION_NAMES", "Chinese,auto-generated")
auto_translation_languages = os.getenv("AUTO_TRANSLATION_LANGUAGES", "en")
languages_to_translate_to = os.getenv("LANGUAGES_TO_TRANSLATE_TO", "zh-Hant")


def float_to_srt_time_format(d: float) -> str:
    """Convert decimal durations into proper srt format.

    :rtype: str
    :returns:
        SubRip Subtitle (str) formatted time duration.

    float_to_srt_time_format(3.89) -> '00:00:03,890'
    """
    fraction, whole = math.modf(d)
    time_fmt = time.strftime("%H:%M:%S,", time.gmtime(whole))
    ms = f"{fraction:.3f}".replace("0.", "")
    return time_fmt + ms


def get_transcript(video_id, language):
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

    for transcript in transcript_list:

        # the Transcript object provides metadata properties
        # print(
        #     transcript.video_id,
        #     transcript.language,
        #     transcript.language_code,
        #     # whether it has been manually created or generated by YouTube
        #     transcript.is_generated,
        #     # whether this transcript can be translated or not
        #     transcript.is_translatable,
        #     # a list of languages the transcript can be translated to
        #     transcript.translation_languages,
        # )

        if language in transcript.language:
            return transcript

    return None


def xml_caption_to_srt(xml_captions: str) -> str:
    """Convert xml caption tracks to "SubRip Subtitle (srt)".

        :param str xml_captions:
        XML formatted caption tracks.
    """
    segments = []
    root = ElementTree.fromstring(xml_captions)
    i = 0
    for child in list(root.iter("body"))[0]:
        if child.tag == 'p':
            caption = ''
            if len(list(child)) == 0:
                # instead of 'continue'
                caption = child.text
            for s in list(child):
                if s.tag == 's':
                    caption += ' ' + s.text
            caption = unescape(caption.replace("\n", " ").replace("  ", " "), )
            try:
                duration = float(child.attrib["d"]) / 1000.0
            except KeyError:
                duration = 0.0
            start = float(child.attrib["t"]) / 1000.0
            end = start + duration
            sequence_number = i + 1  # convert from 0-indexed to 1.
            line = "{seq}\n{start} --> {end}\n{text}\n".format(
                seq=sequence_number,
                start=float_to_srt_time_format(start),
                end=float_to_srt_time_format(end),
                text=caption,
            )
            segments.append(line)
            i += 1
    return "\n".join(segments).strip()


def is_translation_lang(translation_languages, lang_to_translate):

    for translation_language in translation_languages:
        if translation_language['language_code'] in lang_to_translate:
            return True

    return False


def is_present(item, source):
    for source_item in source:
        if item in source_item:
            return True

    return False


def format_caption_path(video_id, title, caption_code):
    return "{video_id}/{title}.{caption_code}.srt".format(
        video_id=video_id,
        title=title,
        caption_code=caption_code)


def download_video(video_id):
    yt = YouTube("https://youtube.com/watch?v={video_id}".format(
        video_id=video_id))
    streams = yt.streams.filter(progressive=True)

    stream_to_download = streams.get_highest_resolution()
    stream_to_download.download()

    s3 = boto3.client('s3')
    default_filename = stream_to_download.default_filename

    s3.upload_file(default_filename, bucket,
                   "{video_id}/{filename}".format(
                       video_id=video_id,
                       filename=default_filename))

    captions: List[Caption] = yt.caption_tracks
    for caption in captions:
        if is_present(caption.name, caption_names):
            srt_caption = xml_caption_to_srt(caption.xml_captions)
            s3.put_object(
                Bucket=bucket,
                Body=srt_caption,
                Key=format_caption_path(
                    video_id,
                    stream_to_download.title,
                    caption.code)
            )

    for lang in auto_translation_languages.split(","):
        transcript = get_transcript(video_id, lang)
        if transcript and transcript.is_translatable:
            for lang_to_translate in languages_to_translate_to.split(","):
                if is_translation_lang(transcript.translation_languages,
                                       lang_to_translate):
                    formatter = SRTFormatter()
                    srt_formatted = formatter.format_transcript(
                        transcript.translate(lang_to_translate).fetch())
                    s3.put_object(
                        Bucket=bucket,
                        Body=srt_formatted,
                        Key=format_caption_path(video_id,
                                                stream_to_download.title,
                                                lang_to_translate))


def download_videos():
    video_ids_split = video_ids.split(",")
    if len(video_ids_split) == 0:
        print("Please supply videos ids delimited "
              "by comma as VIDEO_IDS env property")
        return

    for video_id in video_ids_split:
        print("Video is being downloaded {video_id}".format(video_id=video_id))
        download_video(video_id)


download_videos()