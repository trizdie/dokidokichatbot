label start:

    $ anticheat = persistent.anticheat
    $ chapter = 0
    $ _dismiss_pause = config.developer

    $ s_name = "???"
    $ m_name = "Girl 3"
    $ n_name = "Girl 2"
    $ y_name = "Girl 1"

    $ quick_menu = True
    $ style.say_dialogue = style.normal
    $ in_sayori_kill = None
    $ allow_skipping = True
    $ config.allow_skipping = True

    # Show name input on first run, otherwise go straight to character selection
    if persistent.playername == "":
        call screen chatbot_name_input
        if player:
            $ persistent.playername = player
            $ renpy.save_persistent()
    else:
        $ player = persistent.playername

    call screen character_select

    return

label endgame (pause_length=4.0):
    $ quick_menu = False
    stop music fadeout 2.0
    scene black
    show end
    with dissolve_scene_full
    pause pause_length
    $ quick_menu = True
    return
