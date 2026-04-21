from app.schemas.runway import ModelCatalogResponse, ModelItem


CATALOG = [
    ModelItem(
        id="nano-banana-2",
        name="Nano Banana 2",
        vendor="google",
        media_types=["image"],
        capabilities=["text_to_image", "image_to_image"],
    ),
    ModelItem(
        id="seedream-5",
        name="Seedream 5.0",
        vendor="runway",
        media_types=["image"],
        capabilities=["text_to_image", "image_to_image"],
    ),
    ModelItem(
        id="gen-4",
        name="Gen-4",
        vendor="runway",
        media_types=["image", "video"],
        capabilities=["image_to_image", "text_to_video"],
    ),
]


class RunwayModelService:
    def get_models(self, mode: str) -> ModelCatalogResponse:
        data = [item for item in CATALOG if mode in item.media_types]
        return ModelCatalogResponse(data=data)


model_service = RunwayModelService()
