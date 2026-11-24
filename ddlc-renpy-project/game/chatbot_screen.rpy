# chatbot_screen.rpy — DDLC Chatbot interface

init python:
    import sys
    import os
    import time

    # How long the player's own line stays before her answer takes over.
    MIN_LINE_TIME = 1.3
    if config.gamedir not in sys.path:
        sys.path.insert(0, config.gamedir)
    import chatbot as _chatbot_module

    class ChatbotState(object):
        def __init__(self):
            self.input_text = ""
            self.log = []
            self.selected_character = None
            self._prev_quick_menu = None
            self.emotion = "neutral"
            self.dialogue_text = ""
            self.dialogue_speaker = ""
            self.waiting_for_user = True
            self.awaiting_reply = False
            self.fetching_reply = False
            self.pending_reply = None
            self.last_user_message = ""
            self.fetch_started = 0.0

    chatbot_state = ChatbotState()

    # Smiling sprites used when the player makes her happy (compliments etc.).
    # Same 960x960 canvas and alignment as the originals, so she doesn't jump.
    HAPPY_SPRITES = {
        "sayori": "chatbot_happy_sayori",
        "natsuki": "chatbot_happy_natsuki",
        "yuri": "chatbot_happy_yuri",
        "monika": "chatbot_happy_monika",
    }

    # Small per-sprite zoom on top of the shared 0.80. Measured against the
    # composites in definitions.rpy (head width and neck line at the same
    # canvas position), so she keeps the same on-screen size when the
    # expression switches to the smiling artwork and back.
    SPRITE_ZOOM = {
        "chatbot_happy_sayori": 1.000,
        "chatbot_happy_natsuki": 1.000,
        "chatbot_happy_yuri": 1.013,
        "chatbot_happy_monika": 1.000,
    }

    # Vertical nudge in screen pixels, same idea (0 keeps the feet planted).
    SPRITE_YOFFSET = {
        "chatbot_happy_sayori": 0,
        "chatbot_happy_natsuki": 0,
        "chatbot_happy_yuri": 0,
        "chatbot_happy_monika": 0,
    }

    def get_sprite_zoom(sprite):
        return SPRITE_ZOOM.get(sprite, 1.0)

    def get_sprite_yoffset(sprite):
        return SPRITE_YOFFSET.get(sprite, 0)

    # One expression per emotion, taken from each girl's own sprite set
    # (see definitions.rpy). Expressions match the original artwork/scripts:
    # Sayori's pout for anger, Yuri's 1n/1o distress, Natsuki's >_< glare, etc.
    EMOTION_POSES = {
        "sayori": {
            "neutral": "sayori 1a", "happy": HAPPY_SPRITES["sayori"], "excited": "sayori 1s",
            "sad": "sayori 1f", "crying": "sayori 1w", "angry": "sayori 1p",
            "annoyed": "sayori 1b", "surprised": "sayori 1m", "shy": "sayori 1e",
            "worried": "sayori 1u",
        },
        "natsuki": {
            "neutral": "natsuki 1a", "happy": HAPPY_SPRITES["natsuki"], "excited": "natsuki 1y",
            "sad": "natsuki 1x", "crying": "natsuki 1w", "angry": "natsuki 1v",
            "annoyed": "natsuki 1r", "surprised": "natsuki 1h", "shy": "natsuki 1j",
            "worried": "natsuki 1f",
        },
        "yuri": {
            "neutral": "yuri 1a", "happy": HAPPY_SPRITES["yuri"], "excited": "yuri 1d",
            "sad": "yuri 1k", "crying": "yuri 1p", "angry": "yuri 1n",
            "annoyed": "yuri 1o", "surprised": "yuri 1h", "shy": "yuri 1i",
            "worried": "yuri 1v",
        },
        "monika": {
            "neutral": "monika 1a", "happy": HAPPY_SPRITES["monika"], "excited": "monika 1l",
            "sad": "monika 1q", "crying": "monika 1r", "angry": "monika 1f",
            "annoyed": "monika 1g", "surprised": "monika 1i", "shy": "monika 1m",
            "worried": "monika 1c",
        },
    }

    CHARACTERS = {
        "sayori":  {"name": "Sayori",  "color": "#fcacce", "emotions": EMOTION_POSES["sayori"]},
        "natsuki": {"name": "Natsuki", "color": "#ffaacc", "emotions": EMOTION_POSES["natsuki"]},
        "yuri":    {"name": "Yuri",    "color": "#9999ff", "emotions": EMOTION_POSES["yuri"]},
        "monika":  {"name": "Monika",  "color": "#7fba5c", "emotions": EMOTION_POSES["monika"]},
    }

    def get_player_name():
        try:
            name = renpy.store.player
            if name:
                return name
        except:
            pass
        return "You"

    def show_dialogue(speaker, text):
        chatbot_state.dialogue_speaker = speaker
        chatbot_state.dialogue_text = text
        renpy.restart_interaction()

    def on_ctc_click():
        if chatbot_state.awaiting_reply and chatbot_state.pending_reply is not None:
            # The reply was fetched while the player read their own line, so it
            # is already in hand: show it without waiting on the network.
            chatbot_state.awaiting_reply = False
            _show_pending_reply()
        elif not chatbot_state.fetching_reply and not chatbot_state.awaiting_reply:
            # The reply has been read: give the input back to the player and let
            # her face settle back to neutral instead of holding one mood.
            chatbot_state.dialogue_text = ""
            chatbot_state.dialogue_speaker = ""
            chatbot_state.waiting_for_user = True
            chatbot_state.emotion = "neutral"
        renpy.restart_interaction()

    def _start_fetch(msg):
        # Start right after sending: her answer follows the player's line on its
        # own, no extra click needed.
        chatbot_state.fetching_reply = True
        chatbot_state.pending_reply = None
        chatbot_state.fetch_started = time.time()
        renpy.invoke_in_thread(_fetch_reply, msg)

    def _fetch_reply(msg):
        # Runs off the UI thread: the box keeps animating while she answers.
        reply = _chatbot_module.send_message(msg)
        if not chatbot_state.fetching_reply:
            return  # chat was cleared / left before the answer arrived
        # Let the player's own line sit on screen for a moment before her
        # answer replaces it, even when the backend replies instantly.
        remaining = MIN_LINE_TIME - (time.time() - chatbot_state.fetch_started)
        if remaining > 0:
            time.sleep(remaining)
        if not chatbot_state.fetching_reply:
            return
        chatbot_state.pending_reply = reply
        chatbot_state.fetching_reply = False
        # Auto-advance: the reply appears as soon as it is here. The next arrow
        # then clears it and gives the input back.
        chatbot_state.awaiting_reply = False
        _show_pending_reply()

    def _show_pending_reply():
        reply = chatbot_state.pending_reply
        if reply is None:
            return
        chatbot_state.pending_reply = None
        char_name = CHARACTERS.get(chatbot_state.selected_character, {}).get("name", "Bot")
        chatbot_state.log.append((char_name, reply))
        # If the player's own line had no clear mood, react to the reply instead
        # so the sprite still answers something rather than staying blank.
        if chatbot_state.emotion == "neutral":
            reply_emotion = _chatbot_module.detect_emotion(reply)
            if reply_emotion:
                chatbot_state.emotion = reply_emotion
        show_dialogue(char_name, reply)

    def chatbot_send():
        msg = chatbot_state.input_text.strip()
        if not msg or not chatbot_state.waiting_for_user:
            return
        chatbot_state.waiting_for_user = False
        chatbot_state.awaiting_reply = True
        chatbot_state.last_user_message = msg
        chatbot_state.input_text = ""
        # Her face reacts to what the player just wrote.
        emotion = _chatbot_module.detect_emotion(msg)
        if emotion:
            chatbot_state.emotion = emotion
        player_name = get_player_name()
        chatbot_state.log.append((player_name, msg))
        show_dialogue(player_name, msg)
        _start_fetch(msg)

    def chatbot_clear():
        chatbot_state.log = []
        chatbot_state.emotion = "neutral"
        chatbot_state.dialogue_text = ""
        chatbot_state.dialogue_speaker = ""
        chatbot_state.waiting_for_user = True
        chatbot_state.awaiting_reply = False
        chatbot_state.fetching_reply = False
        chatbot_state.pending_reply = None
        chatbot_state.last_user_message = ""
        _chatbot_module.reset_conversation()
        renpy.restart_interaction()

    def select_character(char_key):
        chatbot_state.selected_character = char_key
        chatbot_state.log = []
        chatbot_state.input_text = ""
        chatbot_state.emotion = "neutral"
        chatbot_state.waiting_for_user = True
        chatbot_state.awaiting_reply = False
        chatbot_state.fetching_reply = False
        chatbot_state.pending_reply = None
        chatbot_state.last_user_message = ""
        chatbot_state.dialogue_text = ""
        chatbot_state.dialogue_speaker = ""
        _chatbot_module.set_character(char_key)
        # Bring the local Flask backend up so the character can always answer.
        _chatbot_module.ensure_backend(wait=1.5)
        chatbot_state._prev_quick_menu = renpy.store.quick_menu
        renpy.store.quick_menu = False
        renpy.hide_screen("chatbot_name_input")
        renpy.hide_screen("character_select")
        renpy.show_screen("chatbot_screen")
        renpy.restart_interaction()

    def go_back_to_selection():
        _chatbot_module.reset_conversation()
        chatbot_state.log = []
        chatbot_state.input_text = ""
        chatbot_state.selected_character = None
        chatbot_state.emotion = "neutral"
        chatbot_state.dialogue_text = ""
        chatbot_state.dialogue_speaker = ""
        chatbot_state.waiting_for_user = True
        chatbot_state.awaiting_reply = False
        chatbot_state.fetching_reply = False
        chatbot_state.pending_reply = None
        chatbot_state.last_user_message = ""
        if chatbot_state._prev_quick_menu is not None:
            renpy.store.quick_menu = chatbot_state._prev_quick_menu
            chatbot_state._prev_quick_menu = None
        renpy.hide_screen("chatbot_screen")
        renpy.show_screen("character_select")
        renpy.restart_interaction()

    def get_current_sprite():
        char_data = CHARACTERS.get(chatbot_state.selected_character, {})
        emotions = char_data.get("emotions", {})
        return emotions.get(chatbot_state.emotion) or emotions.get("neutral", "sayori 1a")


# ===================================================================
# HAPPY SPRITES — the smiling artwork per girl (960x960, same framing as
# the original composites in definitions.rpy).
# ===================================================================
image chatbot_happy_sayori = "chatbot/happy_sayori.png"
image chatbot_happy_natsuki = "chatbot/happy_natsuki.png"
image chatbot_happy_yuri = "chatbot/happy_yuri.png"
image chatbot_happy_monika = "chatbot/happy_monika.png"


# ===================================================================
# TRANSFORMS
# ===================================================================

transform ctc_pulse:
    # Starts visible so the next arrow shows up the instant a reply lands.
    alpha 0.6
    block:
        easeout 0.4 alpha 1.0
        easein 0.4 alpha 0.6
        repeat


# Real gui/textbox.png artwork size — the say window is 1280x182, but the
# visible panel is this 816x146 image, centred horizontally and bottom-aligned.
define TEXTBOX_ART_WIDTH = 816
define TEXTBOX_ART_HEIGHT = 146

# Input style — original game text font/colors, top-left of the chat box
style chatbot_input is input:
    xalign 0.0
    text_align 0.0
    xmaximum 640
    font gui.text_font
    size gui.text_size
    color gui.text_color
    outlines [(2, "#000000aa", 0, 0)]
    caret "input_caret"


# Chat-box controls — original game button colours, no pill containers
style chatbot_control_button is button:
    background None
    hover_background None
    padding (12, 2, 12, 2)
    hover_sound gui.hover_sound
    activate_sound gui.activate_sound

# Idle black on the pink panel; hover uses the game's namebox look so it stays
# readable against the light-pink box.
style chatbot_control_button_text is choice_button_text:
    size 22
    yalign 0.5
    hover_color "#ffffff"
    hover_outlines [(2, "#b59", 0, 0)]

# Dialogue inside the panel: scrollable, never wider than the textbox
style chatbot_dialogue is say_dialogue:
    xpos 0
    ypos 0
    xsize 730
    text_align 0.0

# Chat-log author names: the say_label text (white RifficFree-Bold with the
# #b59 outline) with no namebox strip behind it, flush with the message text.
style chatbot_log_namebox is namebox:
    xsize None
    ysize None
    xpos 0
    ypos 0
    xanchor 0.0
    background None
    padding (0, 0, 0, 2)


# ===================================================================
# NAME INPUT SCREEN — polka dots background
# ===================================================================
screen chatbot_name_input():
    modal True
    zorder 200

    add "gui/overlay/confirm.png"

    key "K_RETURN" action Return(True)

    frame:
        background Solid("#fff5f8")
        padding (60, 50, 60, 50)
        xalign 0.5
        yalign 0.5

        has vbox:
            xalign 0.5
            yalign 0.5
            spacing 30

        label "Please enter your name":
            style "confirm_prompt"
            xalign 0.5

        input default "" value VariableInputValue("player") length 15 allow "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

        hbox:
            xalign 0.5
            spacing 100
            textbutton _("OK"):
                action Return(True)
                style "confirm_button"
                text_style "confirm_button_text"


# ===================================================================
# CHARACTER SELECTION — polka dots background
# ===================================================================
screen character_select():
    modal True
    zorder 200

    # Original game HUD — polka-dot menu background + choice buttons
    add "menu_bg"

    vbox:
        xalign 0.5
        yalign 0.5
        spacing gui.choice_spacing

        # Original game menu-title look: RifficFree-Bold, white with #b59 outline
        text "Who do you want to talk to?":
            font "gui/font/RifficFree-Bold.ttf"
            size gui.title_text_size
            color "#fff"
            outlines [(6, "#b59", 0, 0), (3, "#b59", 2, 2)]
            xalign 0.5

        textbutton "Sayori":
            style "choice_button"
            text_style "choice_button_text"
            xalign 0.5
            action Function(select_character, "sayori")

        textbutton "Natsuki":
            style "choice_button"
            text_style "choice_button_text"
            xalign 0.5
            action Function(select_character, "natsuki")

        textbutton "Yuri":
            style "choice_button"
            text_style "choice_button_text"
            xalign 0.5
            action Function(select_character, "yuri")

        textbutton "Monika":
            style "choice_button"
            text_style "choice_button_text"
            xalign 0.5
            action Function(select_character, "monika")

        textbutton "Back":
            style "choice_button"
            text_style "choice_button_text"
            xalign 0.5
            action ShowMenu("main_menu")

    key "K_ESCAPE" action ShowMenu("main_menu")


# ===================================================================
# CHATBOT SCREEN
# ===================================================================
screen chatbot_screen():
    zorder 50

    add "bg club_day"

    if chatbot_state.selected_character:
        $ _current_sprite = get_current_sprite()
        add _current_sprite:
            xcenter 640
            yanchor 1.0
            ypos 1.03
            yoffset get_sprite_yoffset(_current_sprite)
            zoom 0.80 * get_sprite_zoom(_current_sprite)
            subpixel True

    # Textbox — always visible
    window:
        style "window"
        xfill True
        yalign gui.textbox_yalign
        ysize gui.textbox_height

        # Namebox
        if chatbot_state.dialogue_speaker:
            window:
                style "namebox"
                text chatbot_state.dialogue_speaker:
                    style "say_label"

        # Dialogue — clipped and scrollable inside the visible panel, so long
        # replies are fully readable without spilling over the textbox.
        if chatbot_state.dialogue_text and not chatbot_state.waiting_for_user:
            frame:
                background None
                padding (0, 0, 0, 0)
                xpos gui.text_xpos
                ypos gui.text_ypos
                xsize gui.text_width
                ysize 96

                viewport:
                    xsize gui.text_width
                    ysize 96
                    scrollbars "vertical"
                    mousewheel True
                    draggable True

                    vbox:
                        xsize 730
                        add Text(chatbot_state.dialogue_text, style="chatbot_dialogue", substitute=False)

    add SideImage() xalign 0.0 yalign 1.0

    # Input field — top-left aligned inside the visible textbox panel (816x146)
    if chatbot_state.waiting_for_user:
        frame:
            background None
            padding (0, 0, 0, 0)
            xalign 0.5
            yalign gui.textbox_yalign
            xsize TEXTBOX_ART_WIDTH
            ysize TEXTBOX_ART_HEIGHT

            input:
                value FieldInputValue(chatbot_state, "input_text")
                length 200
                style "chatbot_input"
                yalign 0.0
                xoffset 24
                yoffset 10

    key "K_RETURN" action Function(chatbot_send)
    key "K_KP_ENTER" action Function(chatbot_send)

    # Chat controls — inside the bottom-right of the same panel
    frame:
        background None
        padding (0, 0, 0, 0)
        xalign 0.5
        yalign gui.textbox_yalign
        xsize TEXTBOX_ART_WIDTH
        ysize TEXTBOX_ART_HEIGHT

        hbox:
            xalign 1.0
            xoffset -14
            yalign 1.0
            yoffset -10
            spacing 10
            # CTC arrow sits in the control row, so it never covers the reply.
            if chatbot_state.dialogue_text and not chatbot_state.waiting_for_user and not chatbot_state.fetching_reply:
                button:
                    background None
                    xsize 34
                    ysize 30
                    action Function(on_ctc_click)
                    add "gui/ctc.png" at ctc_pulse:
                        align (0.5, 0.5)
            textbutton "Log":
                style "chatbot_control_button"
                text_style "chatbot_control_button_text"
                # Show (not ShowMenu): the log is an overlay on the chat, so
                # closing it returns to the chat instead of an empty menu screen.
                action Show("chatbot_history")
            textbutton "Clear":
                style "chatbot_control_button"
                text_style "chatbot_control_button_text"
                action Function(chatbot_clear)
            textbutton "Send":
                style "chatbot_control_button"
                text_style "chatbot_control_button_text"
                action Function(chatbot_send)
            textbutton "Back":
                style "chatbot_control_button"
                text_style "chatbot_control_button_text"
                action Function(go_back_to_selection)


# ===================================================================
# CHAT HISTORY — polka dots background, text constrained to fit
# ===================================================================
screen chatbot_history():
    modal True
    zorder 200

    # Original game HUD — same polka-dot menu background as the selection page
    add "menu_bg"

    vbox:
        xalign 0.5
        yalign 0.5
        spacing gui.choice_spacing

        # Original game menu-title look
        text "Chat Log":
            font "gui/font/RifficFree-Bold.ttf"
            size gui.title_text_size
            color "#fff"
            outlines [(6, "#b59", 0, 0), (3, "#b59", 2, 2)]
            xalign 0.5

        # Original game container: gui/confirm_frame.png over gui/frame.png,
        # the same pink-bordered box the game uses for its dialogs.
        frame:
            style "confirm_frame"
            xalign 0.5

            has vbox
            xalign 0.5
            spacing 16

            viewport:
                xsize 760
                ysize 360
                scrollbars "vertical"
                mousewheel True
                draggable True

                vbox:
                    spacing 14
                    xsize 725

                    if not chatbot_state.log:
                        text "No messages yet.":
                            font gui.text_font
                            size gui.text_size
                            color "#000"
                            outlines []

                    for autor, mensagem in chatbot_state.log:
                        vbox:
                            spacing 2
                            xsize 725
                            # Name — original game name text, no background strip
                            window:
                                style "chatbot_log_namebox"
                                text autor:
                                    style "say_label"
                            # Message — Aller, black on the light-pink panel
                            text mensagem:
                                substitute False
                                font gui.text_font
                                size gui.text_size
                                color "#000"
                                outlines []
                                xsize 725
                                layout "subtitle"
                                text_align 0.0

            textbutton _("Close"):
                style "choice_button"
                text_style "choice_button_text"
                action Hide("chatbot_history")
                xalign 0.5

    key "K_RETURN" action Hide("chatbot_history")
    key "K_ESCAPE" action Hide("chatbot_history")
