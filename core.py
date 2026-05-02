import asyncio
from ecdsa import VerifyingKey
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.datastructures import State
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from helpers.repository_map import repo
from helpers.api import API
from locales.locale import Loc, Locale
from helpers.config_loader import get_config
from concurrent.futures import ThreadPoolExecutor
from typing import Literal, TypeVar, ParamSpec, Callable

from helpers.data_compilers import (
    compile_particles_list,
    compile_engines_list,
    compile_skins_list,
)

config = get_config()

R = TypeVar("R")
P = ParamSpec("P")


class SonolusFastAPI(FastAPI):
    sono_pub_key: VerifyingKey

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.debug = kwargs["debug"]

        self.executor = ThreadPoolExecutor(max_workers=16)

        self.config = config["sonolus"]
        self.api_config = config["api"]
        self.base_url = kwargs["base_url"]

        self.auth = self.api_config["auth"]
        self.auth_header = self.api_config["auth-header"]

        self.remove_config_queries = [
            "localization",
            "uwu",
            "levelbg",
            "stpickconfig",
            "defaultparticle",
            "defaultengine",
            "defaultskin",
        ]

        self.repository = repo

        self.exception_handlers.setdefault(HTTPException, self.http_exception_handler)

        self.api: API

    async def run_blocking(
        self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs
    ) -> R:
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, lambda: func(*args, **kwargs)
        )

    def get_items_per_page(self, route: str) -> int:
        return self.config["items-per-page"].get(
            route, self.config["items-per-page"].get("default")
        )

    async def http_exception_handler(self, request: Request, exc: HTTPException):
        if exc.status_code < 500:
            return JSONResponse(
                content={"message": exc.detail}, status_code=exc.status_code
            )
        else:
            print(
                "-" * 1000
                + f"\nerror 500: {request.method} {str(request.url)}\n"
                + "-" * 1000
            )
            return JSONResponse(content={}, status_code=exc.status_code)

    def include_router(self, router, *args, **kwargs):
        for route in router.routes:
            if isinstance(route, APIRoute):
                route.response_model_exclude_none = True

        return super().include_router(router, *args, **kwargs)


class _RequestState(State):
    localization: str
    uwu: Literal["off", "uwu", "owo", "uvu", "max"]
    levelbg: Literal["default_or_v3", "default_or_v1", "v1", "v3"]
    staff_pick: Literal["off", "true", "false"]
    particle: str
    showresourcebuttons: Literal["0", "1"]
    skin: str
    engine: str
    loc: Loc
    localization: str


class SonolusRequest(Request):
    state: _RequestState
    app: SonolusFastAPI


class SonolusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: SonolusRequest, call_next):
        request.state.localization = request.query_params.get(
            "localization", "en"
        ).lower()
        uwu_supported = ["tr", "en"]
        request.state.uwu = (
            request.query_params.get("uwu", "off").lower()
            if request.state.localization in uwu_supported
            else "off"
        )
        request.state.levelbg = request.query_params.get(
            "levelbg", "default_or_v3"
        ).lower()
        request.state.staff_pick = request.query_params.get(
            "stpickconfig", "off"
        ).lower()
        request.state.particle = request.query_params.get(
            "defaultparticle", "engine_default"
        ).lower()
        request.state.showresourcebuttons = request.query_params.get(
            "showresourcebuttons", "0"
        )
        request.state.skin = request.query_params.get(
            "defaultskin", "engine_default"
        ).lower()
        skins = await request.app.run_blocking(compile_skins_list, request.app.base_url)
        supported_skins = list(set(theme for skin in skins for theme in skin.themes))
        engines = await request.app.run_blocking(
            compile_engines_list, request.app.base_url, request.state.localization
        )
        request.state.engine = request.query_params.get(
            "defaultengine", engines[0].name
        )
        request.state.loc, request.state.localization = Locale.get_messages(
            request.state.localization
        )

        if not request.state.showresourcebuttons in ["0", "1"]:
            request.state.showresourcebuttons = "0"
        if not request.state.levelbg in [
            "default_or_v3",
            "default_or_v1",
            "v1",
            "v3",
        ]:
            request.state.levelbg = "default_or_v3"
        if not request.state.uwu in ["off", "uwu", "owo", "uvu", "max"]:
            request.state.uwu = "off"
        if not request.state.staff_pick in ["off", "true", "false"]:
            request.state.staff_pick = "off"
        particles = await request.app.run_blocking(
            compile_particles_list, request.app.base_url
        )
        if not request.state.particle in [
            "engine_default",
            *[item.name for item in particles],
        ]:
            request.state.particle = "engine_default"
        if not request.state.engine in [item.name for item in engines]:
            request.state.engine = engines[0].name
        if not request.state.skin in ["engine_default", *supported_skins]:
            request.state.skin = "engine_default"

        query_params = dict(request.query_params)
        for item in request.app.remove_config_queries:
            query_params.pop(item, None)
        request.state.query_params = query_params
        response = await call_next(request)
        response.headers["Sonolus-Version"] = request.app.config[
            "required-client-version"
        ]
        return response
