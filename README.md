## YouTube video downloader

The project is a set of scripts to download videos from YouTube. The script has integration with AWS S3 to upload downloaded videos to AWS S3 bucket.

## Pre-prerequisite

Install python library used by the project. You could find the list of library in requirements.txt.
```
pip install requirements.txt
```

## Download videos

```
export BUCKET=YOUR_S3_BUCKET_NAME
export VIDEO_IDS=VIDEO_ID_1,VIDEO_ID_2

# Specify captions names to download 
export CAPTION_NAMES=Chinese,auto-generated
# Specify auto translation language to download 
export AUTO_TRANSLATION_LANGUAGES=en
# Specify language for auto translation
export LANGUAGES_TO_TRANSLATE_TO=zh-Hant

# This script downloads videos and captions
python3 dowload_videos.py
```