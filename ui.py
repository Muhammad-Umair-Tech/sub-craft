import gradio as gr
import os
import subprocess

from backend import (
    model,
    add_ass_subtitle,
    add_srt_subtitle,
    extract_audio,
    hex_to_abgr,
)


def toggle_subtitle_options(choice):
    style_panel_update, preview_button_update = False, False
    if choice == "Plain":
        style_panel_update = gr.update(visible=False)
        preview_button_update = gr.update(visible=False)
    elif choice == "Stylized":
        style_panel_update = gr.update(visible=True)
        preview_button_update = gr.update(visible=True)
    return style_panel_update, preview_button_update


def show_panel():
    return gr.update(visible=True)


def hide_panel():
    return gr.update(visible=False)


def clear_video():
    return None


def load_sample_video():
    return "media/samples/sample_video.mp4"


def add_captions_helper(
    video_path,
    subtitle_choice,
    fontname,
    fontsize,
    primary_color,
    back_color,
    border_style,
    outline,
    shadow,
    alignment,
):
    if video_path is None:
        return

    output_video_path = ""

    temp_audio_file_path = "media/audios/temp_audio.mp3"
    extract_audio(video_path, temp_audio_file_path)
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

    if subtitle_choice == "Plain":
        output_video_path = "media/outputs/srt_sub_output.mp4"
        output_subtitle_path = "media/subtitles/subtitle.srt"
        add_srt_subtitle(
            transcription, output_subtitle_path, video_path, output_video_path
        )
    elif subtitle_choice == "Stylized":
        output_video_path = "media/outputs/stylized_sub_output.mp4"
        output_subtitle_path = "media/subtitles/stylized_subtitle.ass"

        # Map alignment strings to ASS integers (Numpad layout)
        alignment_map = {
            "Bottom left": "1",
            "Bottom center": "2",
            "Bottom right": "3",
            "Middle left": "4",
            "Middle center": "5",
            "Middle right": "6",
            "Top left": "7",
            "Top middle": "8",
            "Top right": "9",
        }
        ass_alignment = alignment_map.get(alignment, "2")

        # Map border
        border_map = {"No border": "3", "Transparent": "3", "Opaque": "1"}
        ass_border = border_map.get(border_style, "1")

        add_ass_subtitle(
            video_path,
            output_subtitle_path,
            transcription,
            fontname,
            fontsize,
            primary_color,
            back_color,
            ass_border,
            outline,
            shadow,
            ass_alignment,
            output_video_path,
        )

    return output_video_path


def disable_sample_caption_buttons():
    add_subtitle_button_update = gr.update(interactive=False)
    sample_video_button_update = gr.update(interactive=False)
    return add_subtitle_button_update, sample_video_button_update


def enable_sample_caption_buttons():
    add_subtitle_button_update = gr.update(interactive=True)
    sample_video_button_update = gr.update(interactive=True)
    return add_subtitle_button_update, sample_video_button_update


def download_subtitle_video():
    file_path = "media/outputs/srt_sub_output.mp4"
    if not os.path.exists(file_path):
        raise gr.Error("No video subtitle to generated.")
    return file_path


def download_subtitle_file(sub_choice):
    file_path = ""
    if sub_choice == "Plain":
        file_path = "media/subtitles/subtitle.srt"
        if not os.path.exists(file_path):
            raise gr.Error("No SRT subtitle to download.")
    elif sub_choice == "Stylized":
        file_path = "media/subtitles/stylized_subtitle.ass"
        if not os.path.exists(file_path):
            raise gr.Error("No stylized subtitle to download.")
    return file_path


def check_uploaded_video_size(video_path):
    if not os.path.exists(video_path):
        raise gr.Error("No video found. Please upload a video.")
    size_in_bytes = os.path.getsize(video_path)
    size_in_mbs = size_in_bytes / (1024 * 1024)
    if size_in_mbs > 25:
        raise gr.Error("Video size greater than 25 MBs not supported.")


def disable_button():
    return gr.update(interactive=False)


def enable_button():
    return gr.update(interactive=True)


def toggle_clear_button_interactivity(video_path):
    if video_path is None:
        return gr.update(interactive=False)
    if os.path.exists(video_path):
        return gr.update(interactive=True)
    else:
        return gr.update(interactive=False)


def generate_preview_subtitle(
    fontname,
    fontsize,
    primary_color,
    back_color,
    border_style,
    outline,
    shadow,
    alignment,
):
    ass_primary = hex_to_abgr(primary_color)
    ass_back = hex_to_abgr(back_color)

    # Map alignment strings to ASS integers (Numpad layout)
    alignment_map = {
        "Bottom left": "1",
        "Bottom center": "2",
        "Bottom right": "3",
        "Middle left": "4",
        "Middle center": "5",
        "Middle right": "6",
        "Top left": "7",
        "Top middle": "8",
        "Top right": "9",
    }
    ass_alignment = alignment_map.get(alignment, "2")

    # Map border
    border_map = {"No border": "3", "Transparent": "3", "Opaque": "1"}
    ass_border = border_map.get(border_style, "1")

    header = f"""[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, BackColour, BorderStyle, Outline, Shadow, Alignment
Style: Default,{fontname},{fontsize},{ass_primary},{ass_back},{ass_border},{outline},{shadow},{ass_alignment}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    with open("media/previews/preview_subtitle.ass", "w", encoding="utf-8") as file:
        file.write(header)
        file.write(
            "Dialogue: 0, 00:00:00.00, 00:00:03.00, Default,,0,0,0,, This is what the subtitle will look like."
        )

    command = [
        "ffmpeg",
        "-y",
        "-i",
        "media/previews/preview_input_video.mp4",
        "-vf",
        f"ass=media/previews/preview_subtitle.ass",
        "-c:a",
        "copy",
        "media/previews/preview_output_video.mp4",
    ]

    subprocess.run(command, check=True)
    return "media/previews/preview_output_video.mp4"


# gr.Blocks() acts as a low-level layout engine that allows you to web-design using Python.
with gr.Blocks() as demo:
    gr.Markdown("<h1 align='center'>Video Captioner</h1>")

    with gr.Row():

        with gr.Column():
            gr.Markdown("### Upload Video for Captioning (Not More Than 25 MBs)")

            video_field = gr.Video(label="Video")

        with gr.Column():
            gr.Markdown("### Controls")

            with gr.Row():
                sub_type = gr.Radio(
                    ["Plain", "Stylized"],
                    value="Plain",
                    label="Choose Subtitle Type",
                )

            with gr.Row():
                add_subtitle_button = gr.Button("Generate Subtitle", interactive=False)

            with gr.Row():
                clear_button = gr.Button("Clear", interactive=False)
                sample_video_button = gr.Button("Use Sample Video")

            with gr.Row(visible=False) as outputs_panel:
                download_video_button = gr.DownloadButton("Download Video")
                download_subtitle_button = gr.DownloadButton("Download Subtitle")

            with gr.Row():
                preview_subtitle_button = gr.Button("Preview Subtitle", visible=False)

        # Hidden by default
        with gr.Column(visible=False) as styling_panel:
            gr.Markdown("### Styling Options")

            font_name = gr.Dropdown(
                interactive=True,
                label="Font",
                choices=[
                    "Times New Roman",
                    "Arial",
                    "Helvetica",
                    "Tahoma",
                    "Verdana",
                    "Georgia",
                    "Garamond",
                    "Courier New",
                    "Impact",
                    "Comic Sans MS",
                ],
                value="Arial",
                allow_custom_value=False,
            )
            font_size = gr.Slider(
                label="Font Size",
                interactive=True,
                minimum=8,
                maximum=24,
                step=1,
                value=12,
            )
            primary_color = gr.ColorPicker(
                interactive=True, label="Primary Color", value="#FFFFFF"
            )
            back_color = gr.ColorPicker(
                interactive=True, label="Back Color", value="#000000"
            )
            border_style = gr.Dropdown(
                interactive=True,
                label="Border Style",
                choices=["No border", "Transparent", "Opaque"],
                allow_custom_value=False,
            )
            outline = gr.Slider(
                label="Outline",
                interactive=True,
                minimum=0,
                maximum=2,
                step=0.5,
                value=1,
            )
            shadow = gr.Slider(
                label="Shadow",
                interactive=True,
                minimum=0,
                maximum=2,
                step=0.5,
                value=1,
            )
            alignment = gr.Dropdown(
                interactive=True,
                label="Alignment",
                choices=[
                    "Bottom left",
                    "Bottom center",
                    "Bottom right",
                    "Middle left",
                    "Middle center",
                    "Middle right",
                    "Top left",
                    "Top middle",
                    "Top right",
                ],
                value="Bottom center",
                allow_custom_value=False,
            )

            gr.Markdown("### Preview")

            preview_video_field = gr.Video(
                label="Subtitle Preview",
                value="media/previews/preview_input_video.mp4",
                loop=True,
                autoplay=True,
            )

    # An onChange event handler which is triggered whenever the radio buttons are changed.
    sub_type.change(
        fn=toggle_subtitle_options,
        inputs=sub_type,
        outputs=[styling_panel, preview_subtitle_button],
    )

    add_subtitle_button.click(
        fn=disable_sample_caption_buttons,
        inputs=None,
        outputs=[add_subtitle_button, sample_video_button],
    ).then(
        fn=add_captions_helper,
        inputs=[
            video_field,
            sub_type,
            font_name,
            font_size,
            primary_color,
            back_color,
            border_style,
            outline,
            shadow,
            alignment,
        ],
        outputs=video_field,
    ).then(
        fn=show_panel,
        inputs=None,
        outputs=outputs_panel,
    ).then(
        fn=enable_sample_caption_buttons,
        inputs=None,
        outputs=[add_subtitle_button, sample_video_button],
    )

    sample_video_button.click(
        fn=load_sample_video, inputs=None, outputs=video_field
    ).then(fn=enable_button, inputs=None, outputs=add_subtitle_button)

    clear_button.click(
        fn=disable_button, inputs=None, outputs=add_subtitle_button
    ).then(fn=enable_button, inputs=None, outputs=sample_video_button).then(
        fn=clear_video, inputs=None, outputs=video_field
    ).then(
        fn=hide_panel, inputs=None, outputs=outputs_panel
    )

    # The output must be the DownloadButton itself
    download_video_button.click(
        fn=download_subtitle_video, inputs=None, outputs=download_video_button
    )

    download_subtitle_button.click(
        fn=download_subtitle_file, inputs=sub_type, outputs=download_subtitle_button
    )

    video_field.upload(
        fn=check_uploaded_video_size, inputs=video_field, outputs=video_field
    )

    video_field.change(
        fn=toggle_clear_button_interactivity, inputs=video_field, outputs=clear_button
    )

    preview_subtitle_button.click(
        fn=generate_preview_subtitle,
        inputs=[
            font_name,
            font_size,
            primary_color,
            back_color,
            border_style,
            outline,
            shadow,
            alignment,
        ],
        outputs=preview_video_field,
    )

# demo.launch(theme=gr.Theme.from_hub("JohnSmith9982/small_and_pretty"))
demo.launch()
