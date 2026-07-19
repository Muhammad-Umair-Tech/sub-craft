from moviepy import VideoFileClip
from faster_whisper import WhisperModel
import subprocess

import os

os.makedirs("media/audios", exist_ok=True)
os.makedirs("media/outputs", exist_ok=True)
os.makedirs("media/subtitles", exist_ok=True)
os.makedirs("media/previews", exist_ok=True)


def srt_format_time(seconds_time):
    # Extract the decimal part and shift it three places to the left
    # so that we can convert it to an int later on.
    milliseconds = (seconds_time % 1) * 1000
    hours, leftover_seconds = divmod(seconds_time, 3600)
    minutes, seconds = divmod(leftover_seconds, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{int(milliseconds):03d}"


def ass_format_time(seconds_time):
    centiseconds = (seconds_time % 1) * 100
    hours, leftover_seconds = divmod(seconds_time, 3600)
    minutes, seconds = divmod(leftover_seconds, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.{int(centiseconds):02d}"


def hex_to_abgr(hex_str):
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 6:
        r, g, b = hex_str[0:2], hex_str[2:4], hex_str[4:6]
        return f"&H00{b}{g}{r}&"
    return "&H00FFFFFF&"  # Default fallback


def write_srt_file(subtitle_segments, srt_path):
    """
    An srt file has a strict format:
    1
    00:00:01,000 --> 00:00:04,500
    This is the first caption string.

    2
    00:00:04,500 --> 00:00:07,200
    This is the second caption string.

    An SRT timestamp strictly follows this structure: HH:MM:SS,mmm
    """
    with open(srt_path, "w", encoding="utf-8") as file:
        for segment in subtitle_segments:
            file.write(f"{segment['number']}\n")
            file.write(
                f"{srt_format_time(segment['start'])} --> {srt_format_time(segment['end'])}\n"
            )
            file.write(f"{segment['text']}\n\n")


def extract_audio(video_input_path, audio_dest_path):
    # The "with" clause locks the VideoFileClip object, executes the block
    # then releases it once the block is executed. It is important here
    # because a video is a system resource and must be released to
    # aviod memory leaks.
    with VideoFileClip(video_input_path) as video:
        video.audio.write_audiofile(
            audio_dest_path, logger=None
        )  # logger=None keeps the terminal clean


def burn_srt_subtitle(input_video_path, srt_path, output_video_path):
    # subprocess handles commands best when they are passed as
    # a list of individual string arguments rather than one long string.

    # Here, we use the built-in FFmpeg tool to burn our subtitles.

    # 1. -i: Specify the input original video path
    # 2. -vf: Call the "video filter" engine, and explicitly pass
    #         the subtitles=your_temp_file.srt filter.
    # 3. -c:a copy: Tell it to stream/copy the audio track directly without re-encoding it
    #               (this saves immense processing time and CPU memory).
    # 4. output_video.mp4: The final string in the list should be your destination path.
    # 5. -y: Automatically overwrite the output file if it exists.
    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_video_path,
        "-vf",
        f"subtitles={srt_path}",
        "-c:a",
        "copy",
        output_video_path,
    ]
    subprocess.run(
        command, check=True
    )  # check=True to get an exception if FFmpeg fails.


def add_srt_subtitle(
    subtitle_segment,
    srt_path,
    input_video_path,
    output_video_path="media/srt_sub_output.mp4",
):
    write_srt_file(subtitle_segment, srt_path)
    burn_srt_subtitle(input_video_path, srt_path, output_video_path)


def write_ass_file(
    subtitle_segments,
    ass_path,
    fontname,
    fontsize,
    primary_color,
    back_color,
    border_style,
    outline,
    shadow,
    alignment=2,
):
    """
    ASS (SubStation Alpha) File Style Header Format:
    [V4+ Styles]
    Format: Name, Fontname, Fontsize, PrimaryColour, BackColour, BorderStyle, Outline, Shadow, Alignment
    Style: Default, Arial, 24, &H00FFFFFF, &H80000000, 1, 1, 0, 2

    [Events]
    Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
    Dialogue: 0,0:00:01.00,0:00:04.50,Default,,0,0,0,,This is the caption text.

    --------------------------------------------------------------------------------
    Color Parameters:
    ASS files require color arguments in ABGR (Alpha Blue Green Red) format prefixed with &H. Each of the parts from ABGR take a two-digit hexa number. E.g. &H00FFFFFF
    PrimaryColor: The main fill color of the text characters.
    BackColor: The background color block behind the text, or the color of the text shadow if a box is not used.
    BorderStyle: 1 (an outline around the outer edge of each character) - 3 (opaque background box)
    Outline: The thickness boundary wrapped around each letter stroke. A decimal float or integer representing pixel width (e.g., 1, 2.5). Set to 0 for no outline.
    Shadow: The offset distance of a drop shadow drawn beneath the text layer. A decimal float or integer representing pixel displacement (e.g., 0, 2). Set to 0 for a flat look.
    Alignment: Determines where the text settles on the video frame container based on a standard numpad grid mapping.
               Input values: An integer from 1 - 9
               1, 2, 3: Bottom region (Left, Centered, Right).
               4, 5, 6: Middle region (Left, Centered, Right).
               7, 8, 9: Top region (Left, Centered, Right).
               Tip: Standard subtitles almost universally use 2.

    """

    header = f"""
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, BackColour, BorderStyle, Outline, Shadow, Alignment
Style: Default,{fontname},{fontsize},{hex_to_abgr(primary_color)},{hex_to_abgr(back_color)},{border_style},{outline},{shadow},{alignment}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    with open(ass_path, "w", encoding="utf-8") as file:
        file.write(header)
        for segment in subtitle_segments:
            file.write(
                f"Dialogue: 0, {ass_format_time(segment['start'])}, {ass_format_time(segment['end'])}, Default,,0,0,0,, {segment['text']}\n"
            )


def burn_ass_subtitle(input_video_path, ass_path, output_video_path):
    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_video_path,
        "-vf",
        f"ass={ass_path}",
        "-c:a",
        "copy",
        output_video_path,
    ]
    subprocess.run(command, check=True)


def add_ass_subtitle(
    input_video_path,
    ass_path,
    subtitle_segment,
    fontname,
    fontsize,
    primary_color,
    back_color,
    border_style,
    outline,
    shadow,
    alignment,
    output_video_path="media/outputs/custom_sub_output.mp4",
):
    write_ass_file(
        subtitle_segment,
        ass_path,
        fontname,
        fontsize,
        primary_color,
        back_color,
        border_style,
        outline,
        shadow,
        alignment,
    )
    burn_ass_subtitle(input_video_path, ass_path, output_video_path)


# We need to load the model into memory, pass it the audio file, and call the transcribe method.
# Instead of processing the entire audio file, Whisper breaks into semantic chunks (e.g. pauses).
# It then returns an object for each chunk containing metadata and the transcription.
# These objects are returned in a "generator" (like a list).

# The model type is defined as "tiny" to keep it lightweight.
# The device is set as CPU because free hosting tiers do not provide a GPU.
# compute_type="int8" quantizes the model and reduces its memory footprint.
model = WhisperModel("tiny", device="cpu", compute_type="int8")

if __name__ == "__main__":
    temp_audio_file_path = "media/audios/temp_audio.mp3"

    input_video_path = "media/samples/sample_video.mp4"

    srt_output_video_path = "media/outputs/"
    srt_path = "media/subtitles/"

    ass_output_video_path = "media/outputs/mobile_custom_video.mp4"
    ass_path = "media/subtitles/mobile_custom_sub.ass"

    extract_audio(input_video_path, temp_audio_file_path)

    # We need to call the transcribe method on the model by passing the path of the temporary audio file.
    # beam_sizes=1 forces a greedy search, which makes transciption significantly faster.
    # .transcribe() returns a tuple of two things:
    # 1. An iterator generator of speech segments.
    # 2. A transcription object containing metadata (e.g. detected language, language probability, etc.).
    segments, info = model.transcribe(temp_audio_file_path, beam_size=1)

    transcription = []
    number = 1
    for segment in segments:
        segment_data = {
            "number": number,
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
        }
        number += 1
        transcription.append(segment_data)

    # add_srt_subtitle(transcription, srt_path, input_video_path, output_video_path)

    add_ass_subtitle(
        input_video_path,
        ass_path,
        transcription,
        "Arial",
        12,
        "#FFFFFF",
        "#FFFF00",
        3,
        2,
        2,
        5,
        ass_output_video_path,
    )
