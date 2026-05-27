from fastapi import APIRouter

attachments_router = APIRouter(prefix="", tags=["Attachments"])

@attachments_router.post("/attachments")
def upload_attachment() -> dict[str, str]:
    return {"detail": "Not implemented"}
