import gzip, json, os
from io import BytesIO
from typing import Any, TypeVar

from helpers.models.sonolus.item import (
    EngineItem,
    SkinItem,
    BackgroundItem,
    EffectItem,
    ParticleItem,
    PostItem,
    PlaylistItem,
)
from helpers.models.sonolus.misc import SRL

from helpers.repository_map import repo

from locales.locale import Locale

cached: dict[str, Any] = {
    "skins": None,
    "effects": None,
    "particles": None,
    "banner": None,
    "static_posts": None,
    "BACKGROUND_NO_SCOPE_SRL": None,
}


def clear_compile_cache(specific: str | None = None):
    global cached
    if specific:
        cached[specific] = None
    else:
        new_cached: dict[str, Any] = {}
        for k in cached.keys():
            new_cached[k] = None
        cached = new_cached.copy()


def compile_banner() -> SRL | None:
    if cached["banner"]:
        return cached["banner"]
    path = "files/banner/banner.png"
    if os.path.exists(path):
        hash = repo.add_file(path)
        return repo.get_srl(hash)
    return None


def compile_playlists_list(
    source: str | None = None, locale: str = "en"
) -> list[PlaylistItem]:
    def replace_values(k_value):
        return (
            k_value.replace("#YOU", loc.you)
            .replace("#UPLOADEDSUB", loc.playlist.UPLOADEDSUB)
            .replace("#UPLOADED", loc.playlist.UPLOADED)
        )

    loc, locale = Locale.get_messages(locale)
    if cached.get(f"playlists_{locale}"):
        return cached[f"playlists_{locale}"]
    compiled_data_list = []
    for playlist in os.listdir("files/playlists"):
        if not os.path.isdir(os.path.join("files", "playlists", playlist)):
            continue

        with open(
            f"files/playlists/{playlist}/playlist.json", "r", encoding="utf8"
        ) as f:
            post_data: dict = json.load(f)
        if not post_data.get("enabled", True):
            continue

        compiled_data = PlaylistItem(
            name=playlist,
            source=source,
            version=post_data["version"],
            title=replace_values(post_data["title"]),
            subtitle=replace_values(post_data["subtitle"]),
            author=replace_values(post_data["author"]),
            tags=[],
            levels=[],
            thumbnail=repo.get_srl(
                repo.add_file(
                    f"files/playlists/{playlist}/thumbnail.png",
                    error_on_file_nonexistent=False,
                )
            ),
        )

        compiled_data_list.append(compiled_data)
    cached[f"playlists_{locale}"] = compiled_data_list
    return compiled_data_list


class ExtendedPostItem(PostItem):
    description: str

    def to_post_item(self) -> PostItem:
        return PostItem.model_validate(self.model_dump())


def compile_static_posts_list(source: str = None) -> list[ExtendedPostItem]:
    if cached["static_posts"]:
        return cached["static_posts"]

    compiled_data_list = []
    for post in os.listdir("files/posts"):
        if not os.path.isdir(os.path.join("files", "posts", post)):
            continue

        with open(f"files/posts/{post}/post.json", "r", encoding="utf8") as f:
            post_data: dict = json.load(f)
        if not post_data.get("enabled", True):
            continue

        thumbnail: SRL | None = None
        hash = repo.add_file(
            f"files/posts/{post}/thumbnail.png", error_on_file_nonexistent=False
        )
        if hash:
            thumbnail = repo.get_srl(hash)

        compiled_data = ExtendedPostItem(
            name=post,
            source=source,
            version=post_data["version"],
            title=post_data["title"],
            time=post_data["time"],
            author=post_data["author"],
            tags=[],
            thumbnail=thumbnail,
            description=post_data["description"],
        )
        compiled_data_list.append(compiled_data)

    cached["static_posts"] = compiled_data_list
    return compiled_data_list


def sort_posts_by_newest(posts: list[ExtendedPostItem]) -> list[ExtendedPostItem]:
    return sorted(posts, key=lambda post: post.time, reverse=True)


def compile_effects_list(source: str = None) -> list[EffectItem]:
    if cached["effects"]:
        return cached["effects"]
    compiled_data_list = []
    for effect in os.listdir("files/effects"):
        if not os.path.isdir(os.path.join("files", "effects", effect)):
            continue

        with open(f"files/effects/{effect}/effect.json", "r", encoding="utf8") as f:
            effect_data: dict = json.load(f)
        if not effect_data.get("enabled", True):
            continue

        compiled_data = EffectItem(
            name=effect,
            source=source,
            version=effect_data["version"],
            title=effect_data["title"],
            subtitle=effect_data["subtitle"],
            author=effect_data["author"],
            tags=[],
            thumbnail=repo.get_srl(
                repo.add_file(f"files/effects/{effect}/thumbnail.png")
            ),
            data=repo.get_srl(repo.add_file(f"files/effects/{effect}/data")),
            audio=repo.get_srl(repo.add_file(f"files/effects/{effect}/audio")),
        )
        compiled_data_list.append(compiled_data)
    cached["effects"] = compiled_data_list
    return compiled_data_list


def compile_backgrounds_list(
    source: str = None,
    locale: str = "en",
) -> list[BackgroundItem]:
    def replace_values(d_value: str):
        return d_value.replace(
            "#BACKGROUNDSELECTSUB", loc.background.BACKGROUNDSELECTSUB
        ).replace("#BACKGROUNDSELECT", loc.background.BACKGROUNDSELECT)

    loc, locale = Locale.get_messages(locale)
    if cached.get(f"backgrounds_{locale}"):
        return cached[f"backgrounds_{locale}"]
    compiled_data_list = []
    for background in os.listdir("files/backgrounds"):
        if not os.path.isdir(os.path.join("files", "backgrounds", background)):
            continue
        compiled_data: BackgroundItem = {"tags": []}
        compiled_data["name"] = background
        if source:
            compiled_data["source"] = source
        with open(
            f"files/backgrounds/{background}/background.json", "r", encoding="utf8"
        ) as f:
            background_data: dict = json.load(f)
        if not background_data.get("enabled", True):
            continue

        if background == "PLEASE-SELECT" and not cached["BACKGROUND_NO_SCOPE_SRL"]:
            with gzip.open(
                f"files/backgrounds/{background}/configuration.json.gz"
            ) as f:
                data = json.load(f)

            if "scope" in data:
                del data["scope"]

            output_buffer = BytesIO()
            with gzip.GzipFile(fileobj=output_buffer, mode="wb") as gz_out:
                gz_out.write(json.dumps(data).encode("utf-8"))

            gzipped_bytes = output_buffer.getvalue()
            no_scope_hash = repo.add_bytes(gzipped_bytes)
            cached["BACKGROUND_NO_SCOPE_SRL"] = repo.get_srl(no_scope_hash)

        compiled_data = BackgroundItem(
            name=background,
            source=source,
            version=background_data["version"],
            title=replace_values(background_data["title"]),
            subtitle=replace_values(background_data["subtitle"]),
            author=replace_values(background_data["author"]),
            tags=[],
            thumbnail=repo.get_srl(
                repo.add_file(f"files/backgrounds/{background}/thumbnail.png")
            ),
            data=repo.get_srl(repo.add_file(f"files/backgrounds/{background}/data")),
            image=repo.get_srl(
                repo.add_file(f"files/backgrounds/{background}/image.png")
            ),
            configuration=(
                cached["BACKGROUND_NO_SCOPE_SRL"]
                if background == "PLEASE-SELECT"
                else repo.get_srl(
                    repo.add_file(
                        f"files/backgrounds/{background}/configuration.json.gz"
                    )
                )
            ),
        )

        compiled_data_list.append(compiled_data)
    cached[f"backgrounds_{locale}"] = compiled_data_list
    return compiled_data_list


class ExtendedParticleItem(ParticleItem):
    engine_specific: bool

    def to_particle_item(self) -> ParticleItem:
        return ParticleItem.model_validate(self.model_dump())


def compile_particles_list(source: str = None) -> list[ExtendedParticleItem]:
    if cached["particles"]:
        return cached["particles"]
    compiled_data_list = []
    for particle in os.listdir("files/particles"):
        if not os.path.isdir(os.path.join("files", "particles", particle)):
            continue

        with open(
            f"files/particles/{particle}/particle.json", "r", encoding="utf8"
        ) as f:
            particle_data: dict = json.load(f)
        if not particle_data.get("enabled", True):
            continue

        compiled_data = ExtendedParticleItem(
            name=particle,
            source=source,
            version=particle_data["version"],
            title=particle_data["title"],
            subtitle=particle_data["subtitle"],
            author=particle_data["author"],
            tags=[],
            thumbnail=repo.get_srl(
                repo.add_file(f"files/particles/{particle}/thumbnail.png")
            ),
            data=repo.get_srl(repo.add_file(f"files/particles/{particle}/data")),
            texture=repo.get_srl(repo.add_file(f"files/particles/{particle}/texture")),
            engine_specific=particle_data["engine_specific"],
        )

        compiled_data_list.append(compiled_data)
    cached["particles"] = compiled_data_list
    return compiled_data_list


class ExtendedSkinItem(SkinItem):
    engines: list[str]
    themes: list[str] | None
    locale: str | None

    def to_skin_item(self) -> SkinItem:
        return SkinItem.model_validate(self.model_dump())


def compile_skins_list(source: str = None) -> list[ExtendedSkinItem]:
    if cached["skins"]:
        return cached["skins"]
    compiled_data_list: list[ExtendedSkinItem] = []
    for skin in os.listdir("files/skins"):
        if not os.path.isdir(os.path.join("files", "skins", skin)):
            continue

        with open(f"files/skins/{skin}/skin.json", "r", encoding="utf8") as f:
            skin_data: dict = json.load(f)
        if not skin_data.get("enabled", True):
            continue

        compiled_data = ExtendedSkinItem(
            name=skin,
            source=source,
            version=skin_data["version"],
            title=skin_data["title"],
            subtitle=skin_data["subtitle"],
            author=skin_data["author"],
            tags=[],
            thumbnail=repo.get_srl(repo.add_file(f"files/skins/{skin}/thumbnail.png")),
            data=repo.get_srl(repo.add_file(f"files/skins/{skin}/data")),
            texture=repo.get_srl(repo.add_file(f"files/skins/{skin}/texture")),
            engines=skin_data.get("engines", []),
            themes=skin_data.get("themes", []),
            locale=skin_data.get("locale"),
        )
        compiled_data_list.append(compiled_data)
    compiled_data_list = sorted(compiled_data_list, key=lambda d: d.title)
    cached["skins"] = compiled_data_list
    return compiled_data_list


class ExtendedEngineItem(EngineItem):
    engine_sort_order: int | float

    def to_engine_item(self) -> EngineItem:
        return EngineItem.model_validate(self.model_dump())


def compile_engines_list(
    source: str = None, locale: str = "en"
) -> list[ExtendedEngineItem]:
    if cached.get(f"engines_{locale}"):
        return cached[f"engines_{locale}"]
    compiled_data_list: list[ExtendedEngineItem] = []
    for engine in os.listdir("files/engines"):
        if not os.path.isdir(os.path.join("files", "engines", engine)):
            continue

        with open(f"files/engines/{engine}/engine.json", "r", encoding="utf8") as f:
            engine_data: dict = json.load(f)
        if not engine_data.get("enabled", True):
            continue

        config_overrides: dict[str, dict[str, Any]] = engine_data.get(
            "config_overrides", {}
        )
        if config_overrides:
            with gzip.open(
                f"files/engines/{engine}/EngineConfiguration", "rt", encoding="utf-8"
            ) as f:
                data = json.load(f)

            for option in data.get("options", []):
                name = option.get("name")

                if name in config_overrides:
                    for opt_key, value in config_overrides[name].items():
                        option[opt_key] = value

                bytes_io = BytesIO()
                with gzip.GzipFile(fileobj=bytes_io, mode="wb") as gzipped_file:
                    json_data = json.dumps(data, ensure_ascii=False).encode("utf-8")
                    gzipped_file.write(json_data)

            config_hash = repo.add_bytes(bytes_io.getvalue())
        else:
            config_hash = repo.add_file(f"files/engines/{engine}/EngineConfiguration")

        def get_skin_name(engine_data: dict, locale: str) -> str:
            if engine_data.get("skin_name_locale", {}).get(locale):
                return engine_data["skin_name_locale"][locale]
            return engine_data["skin_name"]

        try:
            skins = compile_skins_list(source)
            skin_data = next(
                skin
                for skin in skins
                if skin.name == get_skin_name(engine_data, locale)
            )
            effects = compile_effects_list(source)
            effect_data = next(
                effect
                for effect in effects
                if effect.name == engine_data["effect_name"]
            )
            particles = compile_particles_list(source)
            particle_data = next(
                particle
                for particle in particles
                if particle.name == engine_data["particle_name"]
            )
            backgrounds = compile_backgrounds_list(source, locale)
            background_data = next(
                background
                for background in backgrounds
                if background.name == engine_data["background_name"]
            )
        except StopIteration:
            raise KeyError(
                "StopIteration raised: incorrect key name! Make sure your engine file names and resource file names match."
            )

        compiled_data = ExtendedEngineItem(
            name=engine,
            title=engine_data.get("title"),
            subtitle=engine_data.get("subtitle"),
            source=source,
            author=engine_data.get("author"),
            tags=[],
            description=engine_data.get("description"),
            skin=skin_data.to_skin_item(),
            background=background_data,
            effect=effect_data,
            particle=particle_data.to_particle_item(),
            thumbnail=repo.get_srl(
                repo.add_file(f"files/engines/{engine}/thumbnail.png")
            ),
            playData=repo.get_srl(
                repo.add_file(f"files/engines/{engine}/EnginePlayData")
            ),
            watchData=repo.get_srl(
                repo.add_file(f"files/engines/{engine}/EngineWatchData")
            ),
            previewData=repo.get_srl(
                repo.add_file(f"files/engines/{engine}/EnginePreviewData")
            ),
            tutorialData=repo.get_srl(
                repo.add_file(f"files/engines/{engine}/EngineTutorialData")
            ),
            rom=repo.get_srl(
                repo.add_file(
                    f"files/engines/{engine}/EngineRom", error_on_file_nonexistent=False
                )
            ),
            configuration=repo.get_srl(config_hash),
            engine_sort_order=engine_data.get(
                "engine_sort_order", float("inf")
            ),  # last, if no sort order
        )

        compiled_data_list.append(compiled_data)
    compiled_data_list = sorted(
        compiled_data_list,
        key=lambda item: (
            item.engine_sort_order,
            item.title.lower(),  # abc
        ),
    )
    cached[f"engines_{locale}"] = compiled_data_list
    return compiled_data_list
