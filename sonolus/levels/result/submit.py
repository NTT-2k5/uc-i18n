from fastapi import APIRouter, HTTPException, status
from core import SonolusRequest

from helpers.data_compilers import compile_engines_list
from helpers.models.sonolus.response import ServerSubmitLevelResultResponse
from helpers.models.sonolus.submit import ServerSubmitLevelResultRequest
import helpers.replay as replay

router = APIRouter()


@router.post("/", response_model=ServerSubmitLevelResultResponse)
async def main(request: SonolusRequest, data: ServerSubmitLevelResultRequest):
    locale = request.state.loc

    auth = request.headers.get("Sonolus-Session")

    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=locale.not_logged_in,
        )

    response = await request.app.api.get_account().send(auth)

    if response.data.banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=locale.leaderboards.YOU_ARE_BANNED,
        )

    user_engine = data.replay.level.engine

    server_engines = {
        engine.name: engine
        for engine in await request.app.run_blocking(
            compile_engines_list, request.app.base_url, request.state.localization
        )
    }

    server_engine = server_engines[request.state.engine]

    if (
        (user_engine.playData.hash != server_engine.playData.hash)
        or (user_engine.watchData.hash != server_engine.watchData.hash)
        or (user_engine.rom.hash != server_engine.rom.hash)
    ):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are using an outdated engine",
        )

    return ServerSubmitLevelResultResponse(
        key=replay.generate_upload_key(
            response.data.sonolus_id,
            data.replay.level.name,
            data.replay.data.hash,
            data.replay.configuration.hash,
            request.state.engine,
            f"{response.data.sonolus_username}#{response.data.sonolus_handle}",
            request,
        ),
        hashes=[data.replay.data.hash, data.replay.configuration.hash],
    )
