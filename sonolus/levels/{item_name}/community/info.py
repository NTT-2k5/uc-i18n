from fastapi import APIRouter

from core import SonolusRequest
from helpers.models.sonolus.options import ServerForm, ServerTextAreaOption
from helpers.models.sonolus.response import ServerItemCommunityInfo

router = APIRouter()


@router.get("/", response_model=ServerItemCommunityInfo)
async def main(request: SonolusRequest, item_name: str):
    auth = request.headers.get("Sonolus-Session")

    response = await request.app.api.get_comments(item_name).send(auth)

    return ServerItemCommunityInfo(
        actions=(
            [
                ServerForm(
                    type="comment",
                    title="#COMMENT",
                    icon="comment",
                    requireConfirmation=False,
                    options=[
                        ServerTextAreaOption(
                            query="content",
                            name="#COMMENT",
                            required=True,
                            default="",
                            placeholder="#COMMENT_PLACEHOLDER",
                            limit=1500,
                            shortcuts=[],
                        )
                    ],
                )
            ]
            if auth
            else []
        ),
        topComments=await request.app.run_blocking(
            response.data.to_server_item_community_comments, request
        ),
    )
