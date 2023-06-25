from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response


router = APIRouter()


@router.get("/sync", tags=[" "])
async def pong() -> Response:
    # some async operation could happen here
    # example: `data = await get_all_datas()`
    return JSONResponse({"ping": "pong!"})
