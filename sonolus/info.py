from fastapi import APIRouter
from itertools import chain

from core import SonolusRequest
from helpers.data_compilers import (
    compile_banner,
    compile_particles_list,
    compile_engines_list,
    compile_skins_list,
)
from helpers.models.sonolus.misc import ServerInfoItemButton
from helpers.models.sonolus.options import (
    ServerSelectOption,
    ServerOption_Value,
    ServerToggleOption,
)
from helpers.models.sonolus.response import ServerInfo, ServerConfiguration

from helpers.owoify import handle_uwu

router = APIRouter()


@router.get("/", response_model=ServerInfo)
async def main(request: SonolusRequest):
    locale = request.state.loc
    uwu_level = request.state.uwu
    # Assume logged in
    # We only need to validate the session
    # If it's a request that updates something, or access something private
    logged_in = False
    if request.headers.get("Sonolus-Session"):
        logged_in = True

    uwu_supported = ["en", "tr"]

    banner_srl = await request.app.run_blocking(compile_banner)
    button_list = [
        ServerInfoItemButton(type="authentication"),
        ServerInfoItemButton(
            type="post",
            title=locale.announcements,
            icon="announcement",
            infoType="announcements",
        ),
        *(
            [
                ServerInfoItemButton(
                    type="post",
                    title=locale.notification.NOTIFICATION,
                    icon="comment",
                    infoType="notifications",
                )
            ]
            if logged_in
            else ()
        ),
        ServerInfoItemButton(type="level"),
        ServerInfoItemButton(type="replay"),
        ServerInfoItemButton(type="configuration"),
    ]

    if logged_in:
        button_list.append(ServerInfoItemButton(type="playlist"))

    if request.state.showresourcebuttons == "1":
        button_list.extend(
            [
                ServerInfoItemButton(type="skin"),
                ServerInfoItemButton(type="background"),
                ServerInfoItemButton(type="effect"),
                ServerInfoItemButton(type="particle"),
                ServerInfoItemButton(type="engine"),
            ]
        )
    options = []
    if request.state.localization in uwu_supported:
        options.append(
            ServerSelectOption(
                query="uwu",
                name=locale.uwu,
                description=handle_uwu(
                    locale.uwu_desc, request.state.localization, request.state.uwu
                ),
                required=False,
                default="off",
                values=[
                    ServerOption_Value(name="off", title=locale.off),
                    ServerOption_Value(name="owo", title=locale.slightly),
                    ServerOption_Value(name="uwu", title=locale.a_lot),
                    ServerOption_Value(name="uvu", title=locale.extreme),
                    ServerOption_Value(name="max", title=locale.max_uwu),
                ],
            )
        )
    options.append(
        ServerSelectOption(
            query="levelbg",
            name=locale.background.USEBACKGROUND,
            description=handle_uwu(
                locale.background.USEBACKGROUNDDESC,
                request.state.localization,
                uwu_level,
            ),
            required=False,
            default="default_or_v3",
            values=[
                ServerOption_Value(
                    name="default_or_v3", title=locale.background.DEF_OR_V3
                ),
                ServerOption_Value(name="v3", title=locale.background.V3),
                ServerOption_Value(
                    name="default_or_v1", title=locale.background.DEF_OR_V1
                ),
                ServerOption_Value(name="v1", title=locale.background.V1),
            ],
        ),
    )
    engines = await request.app.run_blocking(
        compile_engines_list, request.app.base_url, request.state.localization
    )

    options.append(
        ServerSelectOption(
            query="defaultengine",
            name=locale.default_engine,
            description=handle_uwu(
                locale.default_engine_desc, request.state.localization, uwu_level
            ),
            required=False,
            default=engines[0].name,
            values=[
                ServerOption_Value(name=item.name, title=item.title) for item in engines
            ],
        )
    )

    skins = await request.app.run_blocking(compile_skins_list, request.app.base_url)

    unique_themes = sorted(set(chain.from_iterable([item.themes for item in skins])))

    options.append(
        ServerSelectOption(
            query="defaultskin",
            name=locale.default_skin,
            descriptiion=handle_uwu(
                locale.default_skin_desc, request.state.localization, uwu_level
            ),
            required=False,
            default="engine_default",
            values=[ServerOption_Value(name="engine_default", title="#DEFAULT")]
            + [ServerOption_Value(name=theme, title=theme) for theme in unique_themes],
        )
    )

    particles = await request.app.run_blocking(
        compile_particles_list, request.app.base_url
    )
    options.append(
        ServerSelectOption(
            query="defaultparticle",
            name=locale.default_particle,
            description=handle_uwu(
                locale.default_particle_desc, request.state.localization, uwu_level
            ),
            required=False,
            default="engine_default",
            values=[ServerOption_Value(name="engine_default", title="#DEFAULT")]
            + [
                ServerOption_Value(name=item.name, title=item.title)
                for item in particles
                if not item.engine_specific
            ],
        )
    )

    options.append(
        ServerSelectOption(
            query="stpickconfig",
            name=locale.staff_pick,
            description=handle_uwu(
                locale.search.STAFF_PICK_CONFIG_DESC + "\n" + locale.staff_pick_desc,
                request.state.localization,
                uwu_level,
            ),
            required=False,
            default="off",
            values=[
                ServerOption_Value(name="off", title=locale.search.STAFF_PICK_OFF),
                ServerOption_Value(name="true", title=locale.search.STAFF_PICK_TRUE),
                ServerOption_Value(name="false", title=locale.search.STAFF_PICK_FALSE),
            ],
        )
    )
    options.append(
        ServerToggleOption(
            query="showresourcebuttons",
            name=locale.show_resource_buttons,
            required=False,
            default=False,
        )
    )
    desc = locale.server_description or request.app.config["description"]

    auth = request.headers.get("Sonolus-Session")
    login_message = False
    if auth:
        try:
            response = await request.app.api.get_account().send(auth)

            desc += "\n\n" + ("-" * 40) + "\n"
            desc += "\n" + locale.welcome(response.data.sonolus_username)
            notifications = response.data.unread_notifications
            desc += "\n\n" + (
                locale.notifications_singular(notifications)
                if notifications == 1
                else (
                    locale.notifications_plural(notifications)
                    if notifications > 0
                    else locale.notification.none
                )
            )
            if notifications > 0:
                button_list = [
                    ServerInfoItemButton(
                        type="post",
                        title=locale.notification.NOTIFICATION,
                        icon="comment",
                        badgeCount=notifications,
                        infoType="notifications",
                    )
                ]

            desc += "\n\n" + ("-" * 40) + "\n"
            desc += f"\n{locale.find_in_playlists}"
            if response.data.mod or response.data.admin:
                desc += "\n\n" + ("-" * 40) + "\n"
                if response.data.admin:
                    desc += f"\n{locale.is_admin}\n\n{locale.admin_powers}\n{locale.mod_powers}"
                else:
                    desc += f"\n{locale.is_mod}\n\n{locale.mod_powers}"
            login_message = True
        except:
            pass
    if not login_message:
        desc = locale.server_description or request.app.config["description"]
        desc += "\n\n" + ("-" * 40) + "\n"
        desc += "\n" + locale.not_logged_in

    return ServerInfo(
        title=request.app.config["name"],
        description=handle_uwu(
            desc,
            request.state.localization,
            uwu_level,
        ),
        buttons=button_list,
        configuration=ServerConfiguration(options=options),
        banner=banner_srl if banner_srl else None,
    )
