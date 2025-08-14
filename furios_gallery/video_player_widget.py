# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>
# Bardia Moshiri <bardia@furilabs.com>
# Jesús Higueras <jesus@furilabs.com>
# Luis Garcia <git@luigi311.com>

import gi
import os
import time
gi.require_version("Gtk", "4.0")
gi.require_version("Gst", "1.0")
from gi.repository import Gtk, Gst, GLib, Adw
from .ui import create_video_player_css, create_video_controls, create_video_overlay_and_button

class VideoPlayerWidget(Gtk.Box):
    def __init__(self, file_path):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.file_path = file_path
        self.playbin = None
        self.control_box = None
        self.controls_visible = True
        self.controls_revealer = None
        self.init_ui()

    def init_ui(self):
        Gst.init(None)

        create_video_player_css()

        self.playbin = Gst.ElementFactory.make("playbin", None)
        gtk_sink = Gst.ElementFactory.make("gtk4paintablesink", None)
        if not gtk_sink:
            print("Error: gtk4paintablesink is not available.")
            return

        self.playbin.set_property("video-sink", gtk_sink)

        bus = self.playbin.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_bus_message)

        paintable = gtk_sink.get_property("paintable")
        video_widget = Gtk.Picture.new_for_paintable(paintable)
        video_widget.set_hexpand(True)
        video_widget.set_vexpand(True)

        # Create a clickable overlay just for the video area
        self.video_overlay = Gtk.Overlay()
        self.video_click_button = Gtk.Button()
        self.video_click_button.set_opacity(0)
        self.video_click_button.set_can_focus(False)
        self.video_click_button.connect("clicked", self.on_video_clicked)

        self.video_overlay.set_child(video_widget)
        self.video_overlay.add_overlay(self.video_click_button)

        # Add video to the main vertical box
        self.append(self.video_overlay)

        # Create controls and add them to a revealer
        (self.control_box, self.play_pause_button, self.play_pause_image,
         self.duration_label, self.mute_button, self.mute_image, self.seeker) = create_video_controls()

        # Add margins to the control box
        self.control_box.set_margin_bottom(10)
        self.control_box.set_margin_top(10)
        self.control_box.set_margin_start(10)
        self.control_box.set_margin_end(10)

        # Create a revealer
        self.controls_revealer = Gtk.Revealer()
        self.controls_revealer.set_reveal_child(True)
        self.controls_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.controls_revealer.set_transition_duration(300)  # 300ms animation
        self.controls_revealer.set_child(self.control_box)

        self.play_pause_button.connect("clicked", self.on_play_pause)
        self.mute_button.connect("clicked", self.on_mute_toggle)
        self.seeker.connect("value-changed", self.on_seek)

        # Add revealer containing controls, below the video
        self.append(self.controls_revealer)

        self.setup_video()

        GLib.timeout_add(1000, self.update_ui)

    def setup_video(self):
        if os.path.exists(self.file_path):
            self.playbin.set_property("uri", f"file://{self.file_path}")
            self.playbin.set_state(Gst.State.PAUSED)
        else:
            print(f"Error: File not found at {self.file_path}")

    def on_bus_message(self, bus, message):
        if message.type == Gst.MessageType.EOS:
            self.play_pause_image.set_from_icon_name("view-refresh-symbolic")
            self.play_pause_button.connect("clicked", self.restart_video)

    def stop_video(self):
        self.playbin.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 0)
        self.playbin.set_state(Gst.State.PAUSED)
        self.play_pause_image.set_from_icon_name("media-playback-start-symbolic")

    def restart_video(self, button):
        self.playbin.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 0)
        self.playbin.set_state(Gst.State.PLAYING)
        self.play_pause_image.set_from_icon_name("media-playback-pause-symbolic")
        self.play_pause_button.connect("clicked", self.on_play_pause)

    def toggle_controls_visibility(self):
        if self.controls_visible:
            # Hide controls
            self.controls_revealer.set_reveal_child(False)
            self.controls_visible = False
        else:
            # Show controls
            self.controls_revealer.set_reveal_child(True)
            self.controls_visible = True

    def on_video_clicked(self, button):
        self.toggle_controls_visibility()

    def on_play_pause(self, button):
        state = self.playbin.get_state(0).state
        if state != Gst.State.PLAYING:
            self.playbin.set_state(Gst.State.PLAYING)
            self.play_pause_image.set_from_icon_name("media-playback-pause-symbolic")
        else:
            self.playbin.set_state(Gst.State.PAUSED)
            self.play_pause_image.set_from_icon_name("media-playback-start-symbolic")

    def on_mute_toggle(self, button):
        current_volume = self.playbin.get_property("volume")
        if current_volume > 0:
            self.playbin.set_property("volume", 0)
            self.mute_image.set_from_icon_name("audio-volume-muted-symbolic")
        else:
            self.playbin.set_property("volume", 1)
            self.mute_image.set_from_icon_name("audio-volume-high-symbolic")

    def on_seek(self, slider):
        value = slider.get_value()
        self.playbin.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, int(value * Gst.SECOND))

    def update_ui(self):
        success, position = self.playbin.query_position(Gst.Format.TIME)
        success, duration = self.playbin.query_duration(Gst.Format.TIME)

        if success:
            self.seeker.handler_block_by_func(self.on_seek)
            self.seeker.set_range(0, duration / Gst.SECOND)
            self.seeker.set_value(position / Gst.SECOND)
            self.seeker.handler_unblock_by_func(self.on_seek)

            pos_seconds = int(position / Gst.SECOND)
            dur_seconds = int(duration / Gst.SECOND)

            pos_str = time.strftime("%M:%S", time.gmtime(pos_seconds))
            dur_str = time.strftime("%M:%S", time.gmtime(dur_seconds))

            self.duration_label.set_text(f"{pos_str}/{dur_str}")

        return True
